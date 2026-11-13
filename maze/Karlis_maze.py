"""Labirintu meklešana, salīdzināšana un vizualizēšana."""

from __future__ import annotations

import argparse
import heapq
import itertools
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


Position = tuple[int, int]
ALGORITHMS = ("BFS", "DFS", "Dijkstra", "A*")
WALLS = set("#X1%+|-█▓")
FLOORS = set(" .0_")
STARTS = set("SP@")
GOALS = set("EGFT")


@dataclass(frozen=True)
class Maze:
    rows: tuple[str, ...]
    start: Position
    goal: Position
    source: Path | None = None

    @property
    def height(self) -> int:
        return len(self.rows)

    @property
    def width(self) -> int:
        return len(self.rows[0])

    def neighbors(self, position: Position) -> Iterable[Position]:
        row, column = position
        for next_row, next_column in (
            (row - 1, column),
            (row, column + 1),
            (row + 1, column),
            (row, column - 1),
        ):
            if (
                0 <= next_row < self.height
                and 0 <= next_column < self.width
                and self.rows[next_row][next_column] not in WALLS
            ):
                yield next_row, next_column


@dataclass(frozen=True)
class SearchResult:
    algorithm: str
    path: tuple[Position, ...]
    expanded: int
    elapsed: float

    @property
    def steps(self) -> int | None:
        return len(self.path) - 1 if self.path else None


def parse_map(text: str, source: Path | None = None) -> Maze:
    lines = [
        line
        for line in text.lstrip("\ufeff").splitlines()
        if not line.lstrip().startswith((";", "//"))
    ]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        raise ValueError("fails ir tukšs")

    width = len(lines[0])
    if width == 0 or any(len(line) != width for line in lines):
        raise ValueError("visām kartes rindām jābūt vienādā platumā")

    starts: list[Position] = []
    goals: list[Position] = []
    for row_index, line in enumerate(lines):
        for column_index, character in enumerate(line):
            marker = character.upper()
            if character in WALLS or character in FLOORS:
                continue
            if marker in STARTS:
                starts.append((row_index, column_index))
            elif marker in GOALS:
                goals.append((row_index, column_index))
            else:
                raise ValueError(
                    f"neatpazīts simbols {character!r} "
                    f"{row_index + 1}. rindā, {column_index + 1}. kolonnā"
                )

    if len(starts) != 1:
        raise ValueError(f"kartē jābūt vienam sākumam (S/P/@); atrasti {len(starts)}")
    if len(goals) != 1:
        raise ValueError(f"kartē jābūt vienam galam (E/G/F/T); atrasti {len(goals)}")
    return Maze(tuple(lines), starts[0], goals[0], source)


def load_map(path: Path) -> Maze:
    try:
        return parse_map(path.read_text(encoding="utf-8-sig"), path.resolve())
    except UnicodeDecodeError as error:
        raise ValueError("kartes failam jābūt UTF-8 teksta formātā") from error


def discover_maps(folder: Path) -> tuple[list[Maze], list[tuple[Path, str]]]:
    candidates = set(folder.glob("*.txt"))
    maps_folder = folder / "maps"
    if maps_folder.is_dir():
        candidates.update(maps_folder.glob("*.txt"))

    recognized: list[Maze] = []
    rejected: list[tuple[Path, str]] = []
    for path in sorted(candidates, key=lambda item: item.name.casefold()):
        try:
            recognized.append(load_map(path))
        except (OSError, ValueError) as error:
            rejected.append((path, str(error)))
    return recognized, rejected


def reconstruct_path(
    parents: dict[Position, Position | None], goal: Position
) -> tuple[Position, ...]:
    path = []
    position: Position | None = goal
    while position is not None:
        path.append(position)
        position = parents[position]
    path.reverse()
    return tuple(path)


def solve(maze: Maze, algorithm: str = "BFS") -> SearchResult:
    algorithm_key = algorithm.casefold()
    algorithm_name = next(
        (name for name in ALGORITHMS if name.casefold() == algorithm_key),
        None,
    )
    if algorithm_name is None:
        raise ValueError(f"nezināms algoritms: {algorithm}")

    started = time.perf_counter()
    parents: dict[Position, Position | None] = {maze.start: None}
    expanded = 0

    if algorithm_key == "dfs":
        frontier: list[Position] = [maze.start]
        while frontier:
            current = frontier.pop()
            expanded += 1
            if current == maze.goal:
                break
            for neighbor in maze.neighbors(current):
                if neighbor not in parents:
                    parents[neighbor] = current
                    frontier.append(neighbor)
    elif algorithm_key == "bfs":
        frontier_queue = deque([maze.start])
        while frontier_queue:
            current = frontier_queue.popleft()
            expanded += 1
            if current == maze.goal:
                break
            for neighbor in maze.neighbors(current):
                if neighbor not in parents:
                    parents[neighbor] = current
                    frontier_queue.append(neighbor)
    else:
        counter = itertools.count()
        initial_heuristic = (
            0
            if algorithm_key == "dijkstra"
            else abs(maze.start[0] - maze.goal[0])
            + abs(maze.start[1] - maze.goal[1])
        )
        frontier_heap: list[tuple[int, int, int, Position]] = []
        heapq.heappush(
            frontier_heap,
            (initial_heuristic, 0, next(counter), maze.start),
        )
        costs = {maze.start: 0}
        while frontier_heap:
            _, cost, _, current = heapq.heappop(frontier_heap)
            if cost != costs[current]:
                continue
            expanded += 1
            if current == maze.goal:
                break
            for neighbor in maze.neighbors(current):
                new_cost = costs[current] + 1
                if new_cost < costs.get(neighbor, float("inf")):
                    costs[neighbor] = new_cost
                    parents[neighbor] = current
                    heuristic = (
                        0
                        if algorithm_key == "dijkstra"
                        else abs(neighbor[0] - maze.goal[0])
                        + abs(neighbor[1] - maze.goal[1])
                    )
                    heapq.heappush(
                        frontier_heap,
                        (new_cost + heuristic, new_cost, next(counter), neighbor),
                    )

    path = (
        reconstruct_path(parents, maze.goal)
        if maze.goal in parents
        else ()
    )
    return SearchResult(algorithm_name, path, expanded, time.perf_counter() - started)


def format_map(maze: Maze, path: Iterable[Position] = ()) -> str:
    cells = [list(row) for row in maze.rows]
    for row, column in path:
        if (row, column) not in (maze.start, maze.goal):
            cells[row][column] = "*"
    return "\n".join("".join(row) for row in cells)


def format_result(result: SearchResult) -> str:
    elapsed_ms = result.elapsed * 1000
    steps = "nav atrasts" if result.steps is None else str(result.steps)
    return (
        f"{result.algorithm:8} | soļi: {steps:>10} | "
        f"laiks: {elapsed_ms:9.3f} ms | izpētītās šūnas: {result.expanded}"
    )


def run_cli(args: argparse.Namespace) -> int:
    folder = Path(__file__).resolve().parent
    if args.list:
        maps, rejected = discover_maps(folder)
        print("Atpazītās kartes:")
        for maze in maps:
            print(f"  {maze.source}")
        if not maps:
            print("  Nav atrasta neviena derīga karte.")
        if rejected:
            print("\nIzlaistie .txt faili (nav atpazīta karte):")
            for path, reason in rejected:
                print(f"  {path.name}: {reason}")
        return 0

    if args.map:
        try:
            maze = load_map(Path(args.map))
        except (OSError, ValueError) as error:
            print(f"Kļūda, ielādējot karti: {error}")
            return 2
    else:
        maps, _ = discover_maps(folder)
        if not maps:
            print("Mapē nav atrasta derīga .txt karte. Pievieno karti vai norādi --map.")
            return 2
        maze = maps[0]

    if args.compare:
        results = [solve(maze, algorithm) for algorithm in ALGORITHMS]
        print(f"Karte: {maze.source or args.map} ({maze.width} x {maze.height})")
        print("\n".join(format_result(result) for result in results))
        best_path = next((item for item in results if item.algorithm == "BFS"), results[0])
        if best_path.path:
            print("\nBFS atrisinājums (* apzīmē ceļu):")
            print(format_map(maze, best_path.path))
        return 0

    result = solve(maze, args.algorithm)
    print(f"Karte: {maze.source or args.map} ({maze.width} x {maze.height})")
    print(format_result(result))
    if result.path:
        print("\nAtrisinājums (* apzīmē ceļu):")
        print(format_map(maze, result.path))
    else:
        print("Līdz mērķim nav iespējams nokļūt.")
    return 0


def launch_gui(folder: Path) -> int:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    maps, rejected = discover_maps(folder)
    if not maps:
        messagebox.showerror(
            "Labirinta meklētājs",
            "Mapē nav atrasta derīga .txt karte.\n"
            "Pievieno karti vai atver kartes failu ar pogu.",
        )

    root = tk.Tk()
    root.title("Labirinta meklētājs")
    root.geometry("1000x760")
    root.minsize(680, 480)

    top = ttk.Frame(root, padding=8)
    top.pack(fill="x")
    ttk.Label(top, text="Karte:").pack(side="left")
    map_names = [maze.source.name for maze in maps if maze.source]
    map_by_name = {
        maze.source.name: maze for maze in maps if maze.source
    }
    selected_map = tk.StringVar(value=map_names[0] if map_names else "")
    map_picker = ttk.Combobox(
        top, textvariable=selected_map, values=map_names, state="readonly", width=34
    )
    map_picker.pack(side="left", padx=(6, 8))

    controls = ttk.Frame(root, padding=(8, 0, 8, 6))
    controls.pack(fill="x")
    ttk.Label(controls, text="Algoritms:").pack(side="left")
    selected_algorithm = tk.StringVar(value="BFS")
    ttk.Combobox(
        controls,
        textvariable=selected_algorithm,
        values=ALGORITHMS,
        state="readonly",
        width=12,
    ).pack(side="left", padx=(6, 8))
    status = tk.StringVar(value="Izvēlies karti un algoritmu.")
    ttk.Label(controls, textvariable=status).pack(side="left", padx=8)

    board = ttk.Frame(root)
    board.pack(fill="both", expand=True, padx=8)
    canvas = tk.Canvas(board, background="#f7f3e8", highlightthickness=0)
    vertical = ttk.Scrollbar(board, orient="vertical", command=canvas.yview)
    horizontal = ttk.Scrollbar(board, orient="horizontal", command=canvas.xview)
    canvas.configure(
        yscrollcommand=vertical.set,
        xscrollcommand=horizontal.set,
    )
    canvas.grid(row=0, column=0, sticky="nsew")
    vertical.grid(row=0, column=1, sticky="ns")
    horizontal.grid(row=1, column=0, sticky="ew")
    board.rowconfigure(0, weight=1)
    board.columnconfigure(0, weight=1)

    report = tk.StringVar(value="")
    ttk.Label(root, textvariable=report, padding=8, justify="left").pack(fill="x")
    cell_size = 24
    animation_id: str | None = None

    def stop_animation() -> None:
        nonlocal animation_id
        if animation_id is not None:
            root.after_cancel(animation_id)
            animation_id = None

    def selected_maze() -> Maze | None:
        return map_by_name.get(selected_map.get())

    def draw_maze(maze: Maze, path: Iterable[Position] = ()) -> None:
        canvas.delete("all")
        path_cells = set(path)
        canvas.configure(
            scrollregion=(0, 0, maze.width * cell_size, maze.height * cell_size)
        )
        for row_index, line in enumerate(maze.rows):
            for column_index, character in enumerate(line):
                x1 = column_index * cell_size
                y1 = row_index * cell_size
                x2 = x1 + cell_size
                y2 = y1 + cell_size
                position = (row_index, column_index)
                if position == maze.start:
                    color = "#40a96b"
                elif position == maze.goal:
                    color = "#e34f4f"
                elif character in WALLS:
                    color = "#263b53"
                elif position in path_cells:
                    color = "#b9e8d2"
                else:
                    color = "#fffdf5"
                canvas.create_rectangle(
                    x1, y1, x2, y2, fill=color, outline="#ddd8ca"
                )
                if position in (maze.start, maze.goal):
                    canvas.create_text(
                        (x1 + x2) / 2,
                        (y1 + y2) / 2,
                        text="S" if position == maze.start else "G",
                        fill="white",
                        font=("Segoe UI", 10, "bold"),
                    )

    def show_map(*_event: object) -> None:
        stop_animation()
        maze = selected_maze()
        if maze:
            draw_maze(maze)
            report.set("")
            status.set(f"{maze.width} x {maze.height} šūnas")

    def solve_selected() -> SearchResult | None:
        stop_animation()
        maze = selected_maze()
        if maze is None:
            messagebox.showwarning("Nav kartes", "Vispirms atver derīgu kartes failu.")
            return None
        result = solve(maze, selected_algorithm.get())
        draw_maze(maze, result.path)
        status.set(format_result(result))
        report.set(
            f"Atrasts ceļš ar {result.steps} soļiem."
            if result.path
            else "Ceļš līdz mērķim nav atrasts."
        )
        return result

    def animate() -> None:
        result = solve_selected()
        maze = selected_maze()
        if result is None or not result.path or maze is None:
            return
        draw_maze(maze, result.path)
        path = result.path
        marker = canvas.create_oval(0, 0, 0, 0, fill="#ffd43b", outline="#ad7600", width=2)
        index = 0

        def move_next() -> None:
            nonlocal animation_id, index
            row, column = path[index]
            padding = 4
            x1 = column * cell_size + padding
            y1 = row * cell_size + padding
            canvas.coords(marker, x1, y1, x1 + cell_size - 2 * padding, y1 + cell_size - 2 * padding)
            index += 1
            if index < len(path):
                animation_id = root.after(100, move_next)
            else:
                animation_id = None

        move_next()

    def compare() -> None:
        maze = selected_maze()
        if maze is None:
            messagebox.showwarning("Nav kartes", "Vispirms atver derīgu kartes failu.")
            return
        results = [solve(maze, algorithm) for algorithm in ALGORITHMS]
        draw_maze(maze, next((result.path for result in results if result.algorithm == "BFS"), ()))
        status.set("Algoritmu salīdzinājums (laiks katram meklējumam):")
        report.set("\n".join(format_result(result) for result in results))

    def open_map() -> None:
        path = filedialog.askopenfilename(
            title="Atvērt labirinta karti",
            initialdir=folder,
            filetypes=(("Teksta kartes", "*.txt"), ("Visi faili", "*.*")),
        )
        if not path:
            return
        try:
            maze = load_map(Path(path))
        except (OSError, ValueError) as error:
            messagebox.showerror("Nederīga karte", str(error))
            return
        map_by_name[maze.source.name] = maze
        if maze.source.name not in map_picker["values"]:
            map_picker["values"] = (*map_picker["values"], maze.source.name)
        selected_map.set(maze.source.name)
        show_map()

    ttk.Button(controls, text="Atrisināt", command=solve_selected).pack(side="left", padx=3)
    ttk.Button(controls, text="Salīdzināt laikus", command=compare).pack(side="left", padx=3)
    ttk.Button(controls, text="Animēt Pac-Man", command=animate).pack(side="left", padx=3)
    ttk.Button(top, text="Atvērt .txt karti", command=open_map).pack(side="left")
    map_picker.bind("<<ComboboxSelected>>", show_map)

    if map_names:
        show_map()
    if rejected:
        status.set(f"Ielādētas {len(maps)} kartes; nederīgi .txt faili izlaisti.")
    elif not maps:
        status.set("Atver .txt karti vai pievieno karti mapē.")
    root.mainloop()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Atrisini un vizuāli izpēti teksta failā saglabātus labirintus.",
        epilog=(
            "Kartes formāts: taisnstūrveida simbolu režģis; sienas #/X/1, "
            "brīvas vietas atstarpe/./0, sākums S/P/@, mērķis E/G/F/T. "
            "Derīgus .txt failus programma atrod šajā mapē un maps apakšmapē."
        ),
    )
    parser.add_argument("--map", help="kartes .txt faila ceļš")
    parser.add_argument(
        "--algorithm", choices=ALGORITHMS, default="BFS", help="meklēšanas algoritms"
    )
    parser.add_argument(
        "--compare", action="store_true", help="salīdzina visu algoritmu soļus un laikus"
    )
    parser.add_argument(
        "--list", action="store_true", help="parāda mapē automātiski atpazītās kartes"
    )
    parser.add_argument(
        "--no-gui", action="store_true", help="izpilda risināšanu terminālī"
    )
    args = parser.parse_args()
    if args.list or args.no_gui or args.map:
        return run_cli(args)
    return launch_gui(Path(__file__).resolve().parent)


if __name__ == "__main__":
    raise SystemExit(main())
