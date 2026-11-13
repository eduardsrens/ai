from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

Position = tuple[int, int]


@dataclass(frozen=True)
class Maze:
    name: str
    rows: tuple[str, ...]
    start: Position
    goal: Position

    @property
    def width(self) -> int:
        return len(self.rows[0])

    @property
    def height(self) -> int:
        return len(self.rows)


@dataclass(frozen=True)
class SearchResult:
    path: tuple[Position, ...] | None
    visited_count: int
    elapsed_ms: float

    @property
    def steps(self) -> int | None:
        return len(self.path) - 1 if self.path is not None else None


def load_maze(path: Path) -> Maze:
    text = path.read_text(encoding="utf-8-sig")
    rows = tuple(text.splitlines())
    if not rows or not rows[0]:
        raise ValueError("karte ir tukša")

    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("visām kartes rindām jābūt vienādā platumā")

    starts: list[Position] = []
    goals: list[Position] = []
    for y, row in enumerate(rows):
        for x, cell in enumerate(row):
            if cell == "A":
                starts.append((x, y))
            elif cell == "B":
                goals.append((x, y))
            elif cell not in ("#", " "):
                raise ValueError(f"neatpazīta rakstzīme {cell!r} ({x + 1}. kolonna, {y + 1}. rinda)")

    if len(starts) != 1 or len(goals) != 1:
        raise ValueError("kartei jāsatur tieši viens sākums A un viens mērķis B")

    return Maze(path.stem, rows, starts[0], goals[0])


def discover_mazes(folder: Path) -> tuple[list[Path], list[str]]:
    files: list[Path] = []
    errors: list[str] = []
    for path in sorted(folder.glob("*.txt")):
        if path.name.lower() == "requirements.txt":
            continue
        try:
            load_maze(path)
        except (OSError, UnicodeError, ValueError) as error:
            errors.append(f"{path.name}: {error}")
        else:
            files.append(path)
    return files, errors


def _make_result(
    maze: Maze,
    previous: dict[Position, Position],
    visited_count: int,
    started_at: float,
) -> SearchResult:
    path = [maze.goal]
    while path[-1] != maze.start:
        path.append(previous[path[-1]])
    path.reverse()
    return SearchResult(tuple(path), visited_count, (perf_counter() - started_at) * 1000)


def breadth_first_search(maze: Maze) -> SearchResult:
    started_at = perf_counter()
    pending = deque([maze.start])
    previous: dict[Position, Position] = {}
    visited = {maze.start}

    while pending:
        current = pending.popleft()
        if current == maze.goal:
            return _make_result(maze, previous, len(visited), started_at)

        x, y = current
        for neighbor in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            nx, ny = neighbor
            if (
                0 <= ny < maze.height
                and 0 <= nx < maze.width
                and maze.rows[ny][nx] != "#"
                and neighbor not in visited
            ):
                visited.add(neighbor)
                previous[neighbor] = current
                pending.append(neighbor)

    return SearchResult(None, len(visited), (perf_counter() - started_at) * 1000)


def depth_first_search(maze: Maze) -> SearchResult:
    started_at = perf_counter()
    pending = [maze.start]
    previous: dict[Position, Position] = {}
    visited = {maze.start}

    while pending:
        current = pending.pop()
        if current == maze.goal:
            return _make_result(maze, previous, len(visited), started_at)

        x, y = current
        for neighbor in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            nx, ny = neighbor
            if (
                0 <= ny < maze.height
                and 0 <= nx < maze.width
                and maze.rows[ny][nx] != "#"
                and neighbor not in visited
            ):
                visited.add(neighbor)
                previous[neighbor] = current
                pending.append(neighbor)

    return SearchResult(None, len(visited), (perf_counter() - started_at) * 1000)


def main() -> int:
    parser = argparse.ArgumentParser(description="Vizuāls labirintu risinātājs (pygame-ce).")
    parser.add_argument(
        "maps",
        nargs="*",
        type=Path,
        help="izvēles ceļi uz .txt kartēm; bez tiem tiek ielādētas visas šīs mapes kartes",
    )
    args = parser.parse_args()

    if args.maps:
        map_files = args.maps
        discovery_errors: list[str] = []
    else:
        map_files, discovery_errors = discover_mazes(Path(__file__).resolve().parent)

    loaded: list[tuple[Path, Maze]] = []
    for path in map_files:
        try:
            loaded.append((path, load_maze(path)))
        except (OSError, UnicodeError, ValueError) as error:
            discovery_errors.append(f"{path}: {error}")

    for error in discovery_errors:
        print(f"Nevar ielādēt karti: {error}")
    if not loaded:
        print("Nav atrasta neviena derīga karte. Pārbaudi .txt kartes formātu.")
        return 1

    try:
        import pygame
    except ImportError as error:
        print("Nav atrasts pygame-ce. Uzinstalē to ar: python -m pip install -r maze/requirements.txt")
        raise error

    pygame.init()
    screen = pygame.display.set_mode((1180, 820))
    pygame.display.set_caption("Labirintu risinātājs")
    clock = pygame.time.Clock()
    title_font = pygame.font.SysFont("arial", 26, bold=True)
    font = pygame.font.SysFont("arial", 19)
    small_font = pygame.font.SysFont("arial", 15)

    colors = {
        "background": (18, 24, 35),
        "panel": (27, 35, 49),
        "floor": (218, 228, 230),
        "wall": (48, 62, 77),
        "path": (34, 178, 160),
        "start": (57, 178, 101),
        "goal": (231, 91, 83),
        "player": (255, 198, 71),
        "text": (239, 244, 246),
        "muted": (164, 180, 193),
    }

    selected = 0
    maze = loaded[selected][1]
    bfs_result = breadth_first_search(maze)
    dfs_result = depth_first_search(maze)
    animation_index = 0
    playing = bfs_result.path is not None
    map_surface: pygame.Surface | None = None

    def prepare_map(current_maze: Maze) -> pygame.Surface:
        surface = pygame.Surface((current_maze.width, current_maze.height))
        surface.fill(colors["floor"])
        for y, row in enumerate(current_maze.rows):
            for x, cell in enumerate(row):
                if cell == "#":
                    surface.set_at((x, y), colors["wall"])
        return surface

    map_rect = pygame.Rect(28, 102, 860, 680)
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    delta = -1 if event.key == pygame.K_LEFT else 1
                    selected = (selected + delta) % len(loaded)
                    maze = loaded[selected][1]
                    bfs_result = breadth_first_search(maze)
                    dfs_result = depth_first_search(maze)
                    animation_index = 0
                    playing = bfs_result.path is not None
                    map_surface = None
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    bfs_result = breadth_first_search(maze)
                    dfs_result = depth_first_search(maze)
                    animation_index = 0
                    playing = bfs_result.path is not None
                elif event.key == pygame.K_SPACE and bfs_result.path is not None:
                    playing = not playing
                elif event.key == pygame.K_r:
                    animation_index = 0
                    playing = bfs_result.path is not None

        if map_surface is None:
            map_surface = prepare_map(maze)

        screen.fill(colors["background"])
        pygame.draw.rect(screen, colors["panel"], (910, 0, 270, 820))
        title = title_font.render("Labirintu risinātājs", True, colors["text"])
        screen.blit(title, (28, 25))
        map_title = font.render(
            f"{selected + 1}/{len(loaded)}  {maze.name}",
            True,
            colors["muted"],
        )
        screen.blit(map_title, (28, 66))

        scale = min(map_rect.width / maze.width, map_rect.height / maze.height)
        draw_width = max(1, round(maze.width * scale))
        draw_height = max(1, round(maze.height * scale))
        draw_x = map_rect.x + (map_rect.width - draw_width) // 2
        draw_y = map_rect.y + (map_rect.height - draw_height) // 2
        scaled_map = pygame.transform.scale(map_surface, (draw_width, draw_height))
        screen.blit(scaled_map, (draw_x, draw_y))

        if bfs_result.path:
            animation_index = min(animation_index, len(bfs_result.path))
            visible_path = bfs_result.path[:animation_index]
            current_position = bfs_result.path[max(0, animation_index - 1)]
            if len(visible_path) > 1:
                points = [
                    (
                        round(draw_x + (x + 0.5) * draw_width / maze.width),
                        round(draw_y + (y + 0.5) * draw_height / maze.height),
                    )
                    for x, y in visible_path
                ]
                pygame.draw.lines(screen, colors["path"], False, points, max(2, round(scale * 0.45)))

            if playing:
                animation_index = min(len(bfs_result.path), animation_index + 12)
                if animation_index >= len(bfs_result.path):
                    playing = False

            current_x, current_y = current_position
            current_center = (
                round(draw_x + (current_x + 0.5) * draw_width / maze.width),
                round(draw_y + (current_y + 0.5) * draw_height / maze.height),
            )
            pygame.draw.circle(screen, colors["player"], current_center, max(3, round(scale * 0.38)))

        for position, color in ((maze.start, colors["start"]), (maze.goal, colors["goal"])):
            x, y = position
            center = (
                round(draw_x + (x + 0.5) * draw_width / maze.width),
                round(draw_y + (y + 0.5) * draw_height / maze.height),
            )
            pygame.draw.circle(screen, color, center, max(3, round(scale * 0.38)))

        panel_x = 930

        def draw_text(text: str, y: int, color: tuple[int, int, int] = colors["text"], big: bool = False) -> None:
            rendered = (title_font if big else font).render(text, True, color)
            screen.blit(rendered, (panel_x, y))

        draw_text("Algoritmu salīdzinājums", 28, big=True)
        draw_text("BFS — īsākais ceļš", 88, colors["path"])
        draw_text(f"Soļi: {bfs_result.steps if bfs_result.steps is not None else 'nav'}", 121)
        draw_text(f"Laiks: {bfs_result.elapsed_ms:.3f} ms", 151)
        draw_text(f"Apskatītas šūnas: {bfs_result.visited_count}", 181, colors["muted"])
        draw_text("DFS — dziļuma meklēšana", 235, colors["player"])
        draw_text(f"Soļi: {dfs_result.steps if dfs_result.steps is not None else 'nav'}", 268)
        draw_text(f"Laiks: {dfs_result.elapsed_ms:.3f} ms", 298)
        draw_text(f"Apskatītas šūnas: {dfs_result.visited_count}", 328, colors["muted"])
        draw_text("Vadība", 400, big=True)
        draw_text("← / →  izvēlēties karti", 448)
        draw_text("Enter  risināt vēlreiz", 478)
        draw_text("Space  pauze / turpināt", 508)
        draw_text("R  atkārtot animāciju", 538)
        draw_text("Esc  iziet", 568)
        draw_text("Zaļš: sākums A", 630, colors["muted"])
        draw_text("Sarkans: mērķis B", 660, colors["muted"])
        status = "Atrisināts" if bfs_result.path else "Ceļš nav atrasts"
        draw_text(status, 720, colors["path"] if bfs_result.path else colors["goal"])
        screen.blit(
            small_font.render("BFS garantē īsāko ceļu; laiks katrā palaišanā var atšķirties.", True, colors["muted"]),
            (panel_x, 758),
        )

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
