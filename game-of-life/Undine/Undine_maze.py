"""Solve text mazes and compare common path-finding algorithms."""

from __future__ import annotations

import argparse
import heapq
import itertools
import math
import random
import statistics
import sys
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import arcade
from PIL import Image, ImageDraw

Position = tuple[int, int]
WALLS = {"#", "X", "1"}
FLOORS = {" ", ".", "0"}
START_MARKS = {"A", "S"}
GOAL_MARKS = {"B", "E", "G"}
VALID_MARKS = WALLS | FLOORS | START_MARKS | GOAL_MARKS
ALGORITHMS = ("BFS", "DFS", "A*")
BENCHMARK_RUNS = 11


@dataclass
class Maze:
    rows: tuple[str, ...]
    start: Position
    goal: Position

    @property
    def height(self) -> int:
        return len(self.rows)

    @property
    def width(self) -> int:
        return len(self.rows[0])

    def is_open(self, position: Position) -> bool:
        row, column = position
        return self.rows[row][column] not in WALLS


def parse_maze(text: str) -> Maze:
    """Parse a rectangular maze, preserving spaces because they are paths."""
    lines = text.lstrip("\ufeff").splitlines()
    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()
    if not lines:
        raise ValueError("fails ir tukšs")

    width = len(lines[0])
    if width == 0 or any(len(line) != width for line in lines):
        raise ValueError("kartes rindām jābūt vienāda platuma")

    rows = tuple(line.upper() for line in lines)
    invalid = sorted({mark for line in rows for mark in line if mark not in VALID_MARKS})
    if invalid:
        raise ValueError(f"neatpazītas kartes rakstzīmes: {' '.join(invalid)}")

    starts = [(r, c) for r, line in enumerate(rows) for c, mark in enumerate(line) if mark in START_MARKS]
    goals = [(r, c) for r, line in enumerate(rows) for c, mark in enumerate(line) if mark in GOAL_MARKS]
    if len(starts) != 1 or len(goals) != 1:
        raise ValueError("kartē jābūt tieši vienam sākumam (A/S) un mērķim (B/E/G)")

    return Maze(rows, starts[0], goals[0])


def load_maze(path: Path) -> Maze:
    return parse_maze(path.read_text(encoding="utf-8-sig"))


def discover_mazes(folder: Path) -> list[Path]:
    """Find text files that contain a valid maze, regardless of filename."""
    found = []
    for path in sorted(folder.glob("*.txt")):
        try:
            load_maze(path)
        except (OSError, UnicodeError, ValueError):
            continue
        found.append(path)
    return found


def neighbors(maze: Maze, position: Position):
    row, column = position
    for next_position in (
        (row, column + 1),
        (row + 1, column),
        (row, column - 1),
        (row - 1, column),
    ):
        next_row, next_column = next_position
        if (
            0 <= next_row < maze.height
            and 0 <= next_column < maze.width
            and maze.is_open(next_position)
        ):
            yield next_position


def build_path(parent: dict[Position, Position | None], goal: Position) -> list[Position]:
    path = []
    position: Position | None = goal
    while position is not None:
        path.append(position)
        position = parent[position]
    path.reverse()
    return path


def find_path(maze: Maze, algorithm: str) -> tuple[list[Position] | None, int]:
    parent: dict[Position, Position | None] = {maze.start: None}
    expanded = 0

    if algorithm == "BFS":
        frontier = deque([maze.start])
        while frontier:
            position = frontier.popleft()
            expanded += 1
            if position == maze.goal:
                return build_path(parent, maze.goal), expanded
            for next_position in neighbors(maze, position):
                if next_position not in parent:
                    parent[next_position] = position
                    frontier.append(next_position)

    elif algorithm == "DFS":
        frontier = [maze.start]
        while frontier:
            position = frontier.pop()
            expanded += 1
            if position == maze.goal:
                return build_path(parent, maze.goal), expanded
            for next_position in reversed(tuple(neighbors(maze, position))):
                if next_position not in parent:
                    parent[next_position] = position
                    frontier.append(next_position)

    elif algorithm == "A*":
        sequence = itertools.count()
        distance = {maze.start: 0}

        def heuristic(position: Position) -> int:
            return abs(position[0] - maze.goal[0]) + abs(position[1] - maze.goal[1])

        frontier = [(heuristic(maze.start), next(sequence), 0, maze.start)]
        closed = set()
        while frontier:
            _, _, cost, position = heapq.heappop(frontier)
            if position in closed:
                continue
            closed.add(position)
            expanded += 1
            if position == maze.goal:
                return build_path(parent, maze.goal), expanded
            for next_position in neighbors(maze, position):
                next_cost = cost + 1
                if next_cost < distance.get(next_position, sys.maxsize):
                    distance[next_position] = next_cost
                    parent[next_position] = position
                    priority = next_cost + heuristic(next_position)
                    heapq.heappush(
                        frontier,
                        (priority, next(sequence), next_cost, next_position),
                    )
    else:
        raise ValueError(f"nezināms algoritms: {algorithm}")

    return None, expanded


def benchmark(maze: Maze, algorithm: str) -> tuple[list[Position] | None, int, int]:
    durations = []
    path = None
    expanded = 0
    for _ in range(BENCHMARK_RUNS):
        started = time.perf_counter_ns()
        path, expanded = find_path(maze, algorithm)
        durations.append(time.perf_counter_ns() - started)
    return path, expanded, int(statistics.median(durations))


def print_solution(maze: Maze, path: list[Position]) -> None:
    rendered = [list(row) for row in maze.rows]
    for row, column in path[1:-1]:
        rendered[row][column] = "o"
    print("\nAtrisinātā karte (o = ceļš):")
    print("\n".join("".join(row) for row in rendered))


class MazeAnalysisWindow(arcade.Window):
    """Arcade viewer for map selection, algorithm timings, and route animation."""

    WIDTH = 1280
    HEIGHT = 840
    BACKGROUND = (14, 21, 25)
    PANEL = (23, 33, 37)
    MAP_BACK = (11, 18, 21)
    WALL = (44, 71, 72)
    FLOOR = (18, 31, 33)
    GRID = (34, 50, 51)
    TEXT = (226, 238, 231)
    MUTED = (133, 158, 151)
    TEAL = (87, 218, 183)
    YELLOW = (255, 202, 76)
    CORAL = (247, 118, 100)

    def __init__(self, paths: list[Path], initial_path: Path | None = None):
        super().__init__(self.WIDTH, self.HEIGHT, "Undīnes labirintu laboratorija", resizable=True, vsync=True)
        self.paths = paths
        self.map_index = paths.index(initial_path) if initial_path in paths else 0
        self.algorithm = "BFS"
        self.speed = 12.0
        self.progress = 0.0
        self.playing = False
        self.buttons: list[tuple[float, float, float, float, str, object]] = []
        self.maze: Maze
        self.results: dict[str, tuple[list[Position] | None, int, int]] = {}
        self.maze_texture: arcade.Texture
        self.route_texture: arcade.Texture | None = None
        self.load_current_map()

    @property
    def map_path(self) -> Path:
        return self.paths[self.map_index]

    def load_current_map(self) -> None:
        self.maze = load_maze(self.map_path)
        self.results = {name: benchmark(self.maze, name) for name in ALGORITHMS}
        self.progress = 0.0
        self.playing = False
        self.make_textures()

    def make_textures(self) -> None:
        image = Image.new("RGBA", (self.maze.width, self.maze.height), (*self.FLOOR, 255))
        pixels = image.load()
        for row_index, row in enumerate(self.maze.rows):
            for column, mark in enumerate(row):
                if mark in WALLS:
                    pixels[column, row_index] = (*self.WALL, 255)
        self.maze_texture = arcade.Texture(image)

        path = self.results[self.algorithm][0]
        if path:
            route = Image.new("RGBA", (self.maze.width, self.maze.height), (0, 0, 0, 0))
            drawing = ImageDraw.Draw(route)
            if len(path) > 1:
                drawing.line([(column, row) for row, column in path], fill=(*self.TEAL, 230), width=1)
            self.route_texture = arcade.Texture(route)
        else:
            self.route_texture = None

    def select_algorithm(self, algorithm: str) -> None:
        if self.algorithm == algorithm:
            return
        self.algorithm = algorithm
        self.progress = 0.0
        self.playing = False
        self.make_textures()

    def on_draw(self) -> None:
        self.clear(self.BACKGROUND)
        self.buttons = []
        width, height = self.width, self.height
        panel_x = width - 350
        arcade.draw_rect_filled(arcade.XYWH(panel_x + 175, height / 2, 350, height), self.PANEL)

        arcade.draw_text("LABIRINTU LABORATORIJA", 28, height - 46, self.MUTED, 12, bold=True)
        arcade.draw_text("Atrodi ceļu. Salīdzini metodes.", 28, height - 80, self.TEXT, 23, bold=True)

        map_left, map_bottom = 30, 72
        map_right, map_top = panel_x - 20, height - 112
        map_width, map_height = map_right - map_left, map_top - map_bottom
        scale = min(map_width / self.maze.width, map_height / self.maze.height)
        rendered_width = scale * self.maze.width
        rendered_height = scale * self.maze.height
        origin_x = map_left + (map_width - rendered_width) / 2
        origin_y = map_bottom + (map_height - rendered_height) / 2

        arcade.draw_rect_filled(
            arcade.XYWH(map_left + map_width / 2, map_bottom + map_height / 2, map_width, map_height),
            self.MAP_BACK,
        )
        maze_rect = arcade.XYWH(origin_x + rendered_width / 2, origin_y + rendered_height / 2, rendered_width, rendered_height)
        arcade.draw_texture_rect(self.maze_texture, maze_rect, pixelated=True)
        if self.route_texture:
            arcade.draw_texture_rect(self.route_texture, maze_rect, pixelated=True)
        arcade.draw_rect_outline(maze_rect, self.GRID, 1)

        def cell_center(position: Position) -> tuple[float, float]:
            row, column = position
            return origin_x + (column + 0.5) * scale, origin_y + rendered_height - (row + 0.5) * scale

        start_x, start_y = cell_center(self.maze.start)
        goal_x, goal_y = cell_center(self.maze.goal)
        marker_radius = max(3, min(9, scale * 0.3))
        arcade.draw_circle_filled(start_x, start_y, marker_radius, self.TEAL)
        arcade.draw_circle_filled(goal_x, goal_y, marker_radius, self.CORAL)

        current_path = self.results[self.algorithm][0]
        if current_path:
            segment = min(int(self.progress), len(current_path) - 1)
            fraction = min(self.progress - segment, 1.0) if segment < len(current_path) - 1 else 0.0
            row, column = current_path[segment]
            if segment < len(current_path) - 1:
                next_row, next_column = current_path[segment + 1]
                row += (next_row - row) * fraction
                column += (next_column - column) * fraction
            player_x = origin_x + (column + 0.5) * scale
            player_y = origin_y + rendered_height - (row + 0.5) * scale
            radius = max(4, min(11, scale * 0.37))
            arcade.draw_circle_filled(player_x, player_y, radius, self.YELLOW)
            mouth = radius * 1.25
            arcade.draw_triangle_filled(
                player_x, player_y,
                player_x + mouth, player_y + mouth * 0.42,
                player_x + mouth, player_y - mouth * 0.42,
                self.MAP_BACK,
            )

        self.draw_sidebar(panel_x, height)

    def draw_sidebar(self, panel_x: float, height: float) -> None:
        left = panel_x + 22
        right = self.width - 22
        content_width = right - left
        self.draw_label("KARTE", left, height - 48)
        name = self.map_path.name
        if len(name) > 27:
            name = name[:24] + "..."
        arcade.draw_text(name, left, height - 78, self.TEXT, 15, bold=True)
        self.add_button(left, height - 123, content_width, 32, "NĀKAMĀ KARTE     ›", "map", (self.map_index + 1) % len(self.paths))

        self.draw_label("ALGORITMS", left, height - 170)
        gap = 7
        button_width = (content_width - 2 * gap) / 3
        for index, algorithm in enumerate(ALGORITHMS):
            x = left + index * (button_width + gap)
            self.add_button(x, height - 210, button_width, 34, algorithm, "algorithm", algorithm, algorithm == self.algorithm)

        self.draw_label("ATRASTAIS CEĻŠ", left, height - 254)
        self.add_button(left, height - 302, content_width, 38, "ATRISINĀT  ↻", "solve", None, accent=True)
        play_label = "PAUZE Ⅱ" if self.playing else "CEĻO  ▶"
        self.add_button(left, height - 348, content_width, 34, play_label, "play", None)

        self.draw_label("ANIMĀCIJAS ĀTRUMS", left, height - 390)
        self.add_button(left, height - 432, 40, 30, "−", "speed", -1)
        arcade.draw_text(f"{self.speed:.0f} soļi/s", left + 52, height - 424, self.TEXT, 14)
        self.add_button(right - 40, height - 432, 40, 30, "+", "speed", 1)

        stats_y = height - 486
        self.draw_label("MĒRĪJUMI  ·  11 PALAIŠANAS", left, stats_y)
        elapsed_values = [self.results[name][2] for name in ALGORITHMS]
        maximum = max(elapsed_values) if elapsed_values else 1
        for index, algorithm in enumerate(ALGORITHMS):
            y = stats_y - 40 - index * 52
            path, expanded, elapsed = self.results[algorithm]
            selected = algorithm == self.algorithm
            color = self.TEAL if selected else self.MUTED
            arcade.draw_text(algorithm, left, y + 15, color, 13, bold=selected)
            time_label = self.format_time(elapsed)
            arcade.draw_text(time_label, right, y + 15, self.TEXT, 13, anchor_x="right")
            bar_width = content_width * elapsed / max(maximum, 1)
            arcade.draw_rect_filled(arcade.XYWH(left + content_width / 2, y + 3, content_width, 4), (42, 60, 61))
            arcade.draw_rect_filled(arcade.XYWH(left + bar_width / 2, y + 3, max(2, bar_width), 4), color)
            steps = len(path) - 1 if path else 0
            detail = f"{steps} soļi   ·   {expanded} apmeklētas šūnas" if path else "Ceļš nav atrasts"
            arcade.draw_text(detail, left, y - 10, self.MUTED, 10)

        arcade.draw_line(left, 74, right, 74, (49, 67, 67), 1)
        arcade.draw_text("SPACE  atskaņot / pauzēt", left, 48, self.MUTED, 10)

    def draw_label(self, text: str, x: float, y: float) -> None:
        arcade.draw_text(text, x, y, self.MUTED, 10, bold=True)

    def add_button(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        label: str,
        action: str,
        value: object,
        active: bool = False,
        accent: bool = False,
    ) -> None:
        bounds = (x, y, width, height, action, value)
        self.buttons.append(bounds)
        fill = self.TEAL if accent else ((42, 67, 65) if active else (30, 45, 48))
        color = self.BACKGROUND if accent or active else self.TEXT
        rect = arcade.XYWH(x + width / 2, y + height / 2, width, height)
        arcade.draw_rect_filled(rect, fill)
        if not accent and not active:
            arcade.draw_rect_outline(rect, (55, 75, 74), 1)
        arcade.draw_text(label, x + width / 2, y + height / 2, color, 12, bold=True, anchor_x="center", anchor_y="center")

    @staticmethod
    def format_time(nanoseconds: int) -> str:
        if nanoseconds < 1_000_000:
            return f"{nanoseconds / 1_000:.1f} µs"
        return f"{nanoseconds / 1_000_000:.3f} ms"

    def on_update(self, delta_time: float) -> None:
        path = self.results[self.algorithm][0]
        if self.playing and path:
            self.progress += delta_time * self.speed
            if self.progress >= len(path) - 1:
                self.progress = float(len(path) - 1)
                self.playing = False

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int) -> None:
        for left, bottom, width, height, action, value in reversed(self.buttons):
            if left <= x <= left + width and bottom <= y <= bottom + height:
                if action == "map":
                    self.map_index = int(value)
                    self.load_current_map()
                elif action == "algorithm":
                    self.select_algorithm(str(value))
                elif action == "solve":
                    self.load_current_map()
                    self.playing = True
                elif action == "play":
                    path = self.results[self.algorithm][0]
                    if path:
                        if self.progress >= len(path) - 1:
                            self.progress = 0.0
                        self.playing = not self.playing
                elif action == "speed":
                    self.speed = max(1.0, min(40.0, self.speed + int(value) * 2))
                return

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.SPACE:
            path = self.results[self.algorithm][0]
            if path:
                if self.progress >= len(path) - 1:
                    self.progress = 0.0
                self.playing = not self.playing
        elif symbol in (arcade.key.RIGHT, arcade.key.N):
            self.map_index = (self.map_index + 1) % len(self.paths)
            self.load_current_map()
        elif symbol == arcade.key.LEFT:
            self.map_index = (self.map_index - 1) % len(self.paths)
            self.load_current_map()
        elif symbol in (arcade.key.ENTER, arcade.key.R):
            self.load_current_map()
            self.playing = True


def generate_level(level: int, seed: int | None = None, _attempt: int = 0) -> Maze:
    """Generate a connected, branching maze whose size grows with each level."""
    level = max(1, level)
    height = min(15 + (level - 1) * 2, 45)
    width = min(23 + (level - 1) * 4, 67)
    rng = random.Random(seed)
    cells = [["#"] * width for _ in range(height)]
    start = (1, 1)
    cells[start[0]][start[1]] = " "
    stack = [start]

    while stack:
        row, column = stack[-1]
        choices = [
            (row + row_step, column + column_step)
            for row_step, column_step in ((-2, 0), (2, 0), (0, -2), (0, 2))
            if 1 <= row + row_step < height - 1
            and 1 <= column + column_step < width - 1
            and cells[row + row_step][column + column_step] == "#"
        ]
        if not choices:
            stack.pop()
            continue
        next_row, next_column = rng.choice(choices)
        cells[(row + next_row) // 2][(column + next_column) // 2] = " "
        cells[next_row][next_column] = " "
        stack.append((next_row, next_column))

    possible_loops = []
    for row in range(1, height - 1):
        for column in range(1, width - 1):
            if cells[row][column] != "#":
                continue
            joins_horizontal = cells[row][column - 1] == " " and cells[row][column + 1] == " "
            joins_vertical = cells[row - 1][column] == " " and cells[row + 1][column] == " "
            if joins_horizontal or joins_vertical:
                possible_loops.append((row, column))
    rng.shuffle(possible_loops)
    loop_count = min(len(possible_loops), max(2, height * width // 110) + min(level // 2, 14))
    for row, column in possible_loops[:loop_count]:
        cells[row][column] = " "

    temporary = Maze(tuple("".join(row) for row in cells), start, start)
    distances = {start: 0}
    frontier = deque([start])
    while frontier:
        position = frontier.popleft()
        for next_position in neighbors(temporary, position):
            if next_position not in distances:
                distances[next_position] = distances[position] + 1
                frontier.append(next_position)
    minimum_route_steps = min(22 + (level - 1) * 8, int((height - 2) * (width - 2) * 0.22))
    goal_candidates = [
        position
        for position, distance in distances.items()
        if minimum_route_steps <= distance <= minimum_route_steps + 7
    ]
    if not goal_candidates:
        goal_candidates = [position for position, distance in distances.items() if distance >= minimum_route_steps]
    goal = rng.choice(goal_candidates) if goal_candidates else max(distances, key=distances.get)
    cells[goal[0]][goal[1]] = "B"
    cells[start[0]][start[1]] = "A"
    return Maze(tuple("".join(row) for row in cells), start, goal)


def place_key_and_gate(maze: Maze) -> tuple[Position, Position]:
    """Put the key in a side branch and make the gate separate it from the goal."""
    route, _ = find_path(maze, "BFS")
    if route is None or len(route) < 5:
        raise ValueError("labirints ir par īsu atslēgai un vārtiem")

    preferred = int((len(route) - 1) * 0.72)
    candidates = sorted(
        range(2, len(route) - 1),
        key=lambda index: (abs(index - preferred), -index),
    )
    original_rows = maze.rows
    route_cells = set(route)
    for candidate_index in candidates:
        maze.rows = original_rows
        gate = route[candidate_index]
        for _ in range(maze.height * maze.width):
            parent: dict[Position, Position | None] = {maze.start: None}
            frontier = deque([maze.start])
            while frontier and maze.goal not in parent:
                position = frontier.popleft()
                for next_position in neighbors(maze, position):
                    if next_position != gate and next_position not in parent:
                        parent[next_position] = position
                        frontier.append(next_position)
            if maze.goal not in parent:
                break

            bypass = build_path(parent, maze.goal)
            bypass_cells = [position for position in bypass[1:-1] if position not in route_cells]
            if not bypass_cells:
                break
            row, column = bypass_cells[len(bypass_cells) // 2]
            rows = [list(line) for line in maze.rows]
            rows[row][column] = "#"
            maze.rows = tuple("".join(line) for line in rows)

        reachable = {maze.start: 0}
        frontier = deque([maze.start])
        while frontier:
            position = frontier.popleft()
            for next_position in neighbors(maze, position):
                if next_position != gate and next_position not in reachable:
                    reachable[next_position] = reachable[position] + 1
                    frontier.append(next_position)
        if maze.goal in reachable:
            continue

        route_prefix = set(route[:candidate_index])
        side_branches = [position for position in reachable if position not in set(route)]
        if not side_branches:
            base_indices = sorted(
                range(1, candidate_index),
                key=lambda index: (abs(index - candidate_index * 0.55), index),
            )
            original_rows = maze.rows
            for branch_length in (2, 1):
                for base_index in base_indices:
                    base_row, base_column = route[base_index]
                    for row_step, column_step in ((-1, 0), (0, 1), (1, 0), (0, -1)):
                        branch = [
                            (base_row + row_step * distance, base_column + column_step * distance)
                            for distance in range(1, branch_length + 1)
                        ]
                        if any(
                            not (1 <= row < maze.height - 1 and 1 <= column < maze.width - 1)
                            or (row, column) in (maze.start, maze.goal, gate)
                            for row, column in branch
                        ):
                            continue

                        rows = [list(line) for line in original_rows]
                        for row, column in branch:
                            rows[row][column] = " "
                        branch_set = set(branch)
                        protected = branch_set | {route[base_index], maze.start, maze.goal, gate}
                        side_cells = set()
                        for branch_cell in branch:
                            for side_cell in neighbors(maze, branch_cell):
                                if side_cell not in protected:
                                    side_cells.add(side_cell)
                        for row, column in side_cells:
                            rows[row][column] = "#"
                        maze.rows = tuple("".join(line) for line in rows)
                        new_route, _ = find_path(maze, "BFS")
                        start_distances = {maze.start: 0}
                        frontier = deque([maze.start])
                        while frontier:
                            position = frontier.popleft()
                            for next_position in neighbors(maze, position):
                                if next_position not in start_distances:
                                    start_distances[next_position] = start_distances[position] + 1
                                    frontier.append(next_position)
                        key = branch[-1]
                        if new_route is None:
                            maze.rows = original_rows
                            continue
                        goal_distances = {maze.goal: 0}
                        frontier = deque([maze.goal])
                        while frontier:
                            position = frontier.popleft()
                            for next_position in neighbors(maze, position):
                                if next_position not in goal_distances:
                                    goal_distances[next_position] = goal_distances[position] + 1
                                    frontier.append(next_position)

                        locked_reachable = {maze.start}
                        frontier = deque([maze.start])
                        while frontier:
                            position = frontier.popleft()
                            for next_position in neighbors(maze, position):
                                if next_position != gate and next_position not in locked_reachable:
                                    locked_reachable.add(next_position)
                                    frontier.append(next_position)

                        if (
                            key in locked_reachable
                            and maze.goal not in locked_reachable
                            and start_distances.get(key, 0) + goal_distances.get(key, 0) > len(new_route) - 1
                        ):
                            return key, gate
                        maze.rows = original_rows
            continue

        branch_depth = {position: 0 for position in route_prefix if position in reachable}
        frontier = deque(branch_depth)
        while frontier:
            position = frontier.popleft()
            for next_position in neighbors(maze, position):
                if next_position != gate and next_position in reachable and next_position not in branch_depth:
                    branch_depth[next_position] = branch_depth[position] + 1
                    frontier.append(next_position)

        key = max(
            side_branches,
            key=lambda position: (
                sum(1 for neighbor in neighbors(maze, position) if neighbor != gate) == 1,
                branch_depth.get(position, 0),
                min(reachable[position], candidate_index),
            ),
        )
        return key, gate

    raise ValueError("labirintā nav atrasts vārtu priekšā esošs atslēgas sānu atzars")


@dataclass
class StarParticle:
    x: float
    y: float
    velocity_x: float
    velocity_y: float
    size: float
    rotation: float
    spin: float
    lifetime: float
    age: float
    color: tuple[int, int, int, int]


@dataclass(frozen=True)
class WorldTheme:
    name: str
    floor_colors: tuple[tuple[int, int, int], ...]
    wall_colors: tuple[tuple[int, int, int], ...]
    detail: tuple[int, int, int]
    accent: tuple[int, int, int]


WORLD_THEMES = (
    WorldTheme("Candy Land", ((224, 172, 171), (239, 194, 183), (204, 157, 167)), ((112, 66, 75), (132, 79, 85), (91, 62, 78)), (255, 222, 190), (244, 125, 141)),
    WorldTheme("Volcano Land", ((88, 78, 76), (105, 88, 78), (74, 73, 76)), ((46, 48, 53), (62, 56, 55), (77, 56, 50)), (224, 104, 61), (255, 126, 48)),
    WorldTheme("Underwater World", ((107, 175, 177), (127, 192, 184), (91, 157, 174)), ((40, 85, 105), (54, 105, 119), (57, 78, 102)), (185, 225, 203), (240, 129, 128)),
    WorldTheme("Enchanted Forest", ((147, 132, 100), (162, 145, 105), (129, 122, 91)), ((50, 66, 52), (66, 77, 53), (77, 68, 51)), (202, 183, 125), (180, 203, 117)),
    WorldTheme("Moon Base", ((151, 154, 158), (169, 169, 166), (135, 143, 151)), ((67, 74, 84), (82, 88, 96), (62, 68, 78)), (215, 216, 205), (126, 205, 230)),
    WorldTheme("Desert Ruins", ((205, 168, 111), (218, 183, 126), (190, 151, 101)), ((112, 82, 58), (132, 96, 63), (99, 78, 61)), (241, 209, 157), (207, 123, 76)),
)


class HamsterGameWindow(arcade.Window):
    """A small maze adventure controlled with the keyboard arrow keys."""

    WIDTH = 1280
    HEIGHT = 850
    ART_TILE = 56
    MUTED = (214, 203, 174)
    CREAM = (255, 242, 210)
    GOLD = (255, 205, 91)
    GURKIS = (104, 170, 81)

    def __init__(self) -> None:
        super().__init__(self.WIDTH, self.HEIGHT, "Kāmis un gurķis", resizable=True, vsync=True)
        self.level = 1
        self.collected = 0
        self.run_seed = random.randrange(1 << 30)
        self.move_duration = 0.095
        self.move_progress = 0.0
        self.player: Position = (1, 1)
        self.move_target: Position | None = None
        self.queued_direction: Position | None = None
        self.held_directions: list[Position] = []
        self.facing: Position = (0, 1)
        self.transition_timer = 0.0
        self.paused = False
        self.game_over = False
        self.energy = 100.0
        self.max_energy = 100.0
        self.has_key = False
        self.gate_open = False
        self.awaiting_space = False
        self.star_particles: list[StarParticle] = []
        self.text_labels: dict[str, arcade.Text] = {}
        self.maze_texture: arcade.Texture
        self.setup_level(self.run_seed)

    @property
    def theme(self) -> WorldTheme:
        return WORLD_THEMES[(self.level - 1) % len(WORLD_THEMES)]

    def setup_level(self, seed: int | None = None) -> None:
        self.run_seed = seed if seed is not None else random.randrange(1 << 30)
        self.maze = generate_level(self.level, self.run_seed)
        self.key_position, self.gate_position = place_key_and_gate(self.maze)
        self.player = self.maze.start
        self.move_target = None
        self.queued_direction = None
        self.held_directions.clear()
        self.move_progress = 0.0
        self.energy = self.max_energy
        self.has_key = False
        self.gate_open = False
        self.awaiting_space = False
        self.game_over = False
        self.transition_timer = 0.0
        self.make_terrain()

    def make_terrain(self) -> None:
        rng = random.Random(self.run_seed + self.level * 7919)
        tile_size = self.ART_TILE
        theme = self.theme
        world_index = (self.level - 1) % len(WORLD_THEMES)
        image = Image.new("RGBA", (self.maze.width * tile_size, self.maze.height * tile_size), (*theme.floor_colors[0], 255))
        drawing = ImageDraw.Draw(image)
        for row, line in enumerate(self.maze.rows):
            for column, mark in enumerate(line):
                left, top = column * tile_size, row * tile_size
                right, bottom = left + tile_size - 1, top + tile_size - 1
                if mark not in WALLS:
                    floor = rng.choice(theme.floor_colors)
                    drawing.rectangle((left, top, right, bottom), fill=(*floor, 255))
                    for _ in range(rng.randint(10, 18)):
                        px = rng.randint(left + 4, right - 6)
                        py = rng.randint(top + 4, bottom - 6)
                        pebble_width = rng.randint(2, 6)
                        pebble_height = rng.randint(2, 4)
                        detail = tuple(max(0, min(255, channel + rng.randint(-24, 24))) for channel in theme.detail)
                        shade = (*detail, 255)
                        drawing.ellipse((px, py, px + pebble_width, py + pebble_height), fill=shade)
                    for _ in range(rng.randint(3, 6)):
                        px = rng.randint(left + 5, right - 7)
                        py = rng.randint(top + 7, bottom - 8)
                        detail = tuple(max(0, min(255, channel + rng.randint(-30, 30))) for channel in theme.detail)
                        drawing.line((px, py + 7, px + rng.choice((-4, 4)), py), fill=(*detail, 255), width=2)
                    if world_index == 0:
                        for _ in range(3):
                            px = rng.randint(left + 12, right - 17)
                            py = rng.randint(top + 12, bottom - 17)
                            sprinkle = rng.choice(((255, 242, 202, 255), (237, 114, 139, 255), (140, 191, 210, 255)))
                            drawing.line((px, py, px + 8, py - 4), fill=sprinkle, width=4)
                    elif world_index == 1:
                        crack = (*theme.accent, 255)
                        drawing.line((left + 14, top + 16, left + 27, top + 27, left + 23, top + 38), fill=crack, width=3)
                    elif world_index == 2:
                        for _ in range(2):
                            px = rng.randint(left + 14, right - 15)
                            py = rng.randint(top + 14, bottom - 15)
                            bubble = (*theme.detail, 220)
                            drawing.ellipse((px, py, px + 8, py + 8), outline=bubble, width=2)
                    elif world_index == 3:
                        px = rng.randint(left + 12, right - 15)
                        py = rng.randint(top + 20, bottom - 12)
                        drawing.line((px + 4, py, px + 4, py + 9), fill=(*theme.accent, 255), width=3)
                        drawing.ellipse((px, py - 5, px + 9, py + 3), fill=(*theme.accent, 255))
                    elif world_index == 4:
                        px = rng.randint(left + 12, right - 20)
                        py = rng.randint(top + 12, bottom - 20)
                        drawing.ellipse((px, py, px + 17, py + 12), outline=(*theme.detail, 210), width=2)
                        drawing.ellipse((px + 4, py + 3, px + 13, py + 9), fill=(*floor, 255))
                    else:
                        crack = (*theme.detail, 255)
                        drawing.line((left + 11, top + 15, left + 22, top + 21, left + 34, top + 16), fill=crack, width=2)

        for row, line in enumerate(self.maze.rows):
            for column, mark in enumerate(line):
                if mark not in WALLS:
                    continue
                left, top = column * tile_size, row * tile_size
                right, bottom = left + tile_size - 1, top + tile_size - 1
                base = rng.choice(theme.wall_colors)
                drawing.rounded_rectangle((left, top, right, bottom), radius=tile_size // 3, fill=(*base, 255))
                for _ in range(rng.randint(6, 10)):
                    px = rng.randint(left - 5, right - 12)
                    py = rng.randint(top - 5, bottom - 12)
                    leaf_width = rng.randint(10, 20)
                    leaf_height = rng.randint(8, 17)
                    leaf = rng.choice(
                        (
                            (*theme.accent, 255),
                            (*theme.detail, 255),
                            (*(max(0, channel - 35) for channel in theme.accent), 255),
                            (*theme.wall_colors[0], 255),
                            (*theme.wall_colors[-1], 255),
                        )
                    )
                    drawing.ellipse((px, py, px + leaf_width, py + leaf_height), fill=leaf)
                drawing.line((left + 12, top + 17, left + 25, top + 12), fill=(*theme.detail, 255), width=2)

        self.maze_texture = arcade.Texture(image)

    def on_draw(self) -> None:
        theme = self.theme
        self.clear(tuple(max(0, channel - 35) for channel in theme.wall_colors[0]))
        width, height = self.width, self.height
        arcade.draw_rect_filled(arcade.XYWH(width / 2, height - 54, width, 108), theme.wall_colors[0])
        self.draw_label_text("title", "KĀMIS UN GURĶIS", 30, height - 37, self.CREAM, 14, bold=True)
        self.draw_label_text("subtitle", theme.name.upper(), 30, height - 68, theme.detail, 10, bold=True)
        self.draw_label_text("level", f"LĪMENIS {self.level:02d}  ·  {theme.name.upper()}", width / 2, height - 52, self.CREAM, 17, bold=True, anchor_x="center")
        self.draw_label_text("score", f"GURĶI  {self.collected:02d}", width - 32, height - 49, (191, 218, 147), 13, bold=True, anchor_x="right")
        self.draw_energy_bar(width, height)
        key_status = "VĀRTI ATVĒRTI" if self.gate_open else "ATSLĒGA ATRASTA" if self.has_key else "ATRODI ATSLĒGU"
        status_color = (154, 224, 135) if self.has_key else self.GOLD
        self.draw_label_text("key-status", key_status, width / 2, height - 78, status_color, 10, bold=True, anchor_x="center")
        arcade.draw_line(30, height - 96, width - 30, height - 96, (72, 94, 72), 1)

        map_left, map_bottom = 30, 34
        map_width, map_height = width - 60, height - 160
        scale = min(map_width / self.maze.width, map_height / self.maze.height, 24)
        rendered_width = scale * self.maze.width
        rendered_height = scale * self.maze.height
        origin_x = map_left + (map_width - rendered_width) / 2
        origin_y = map_bottom + (map_height - rendered_height) / 2
        map_rect = arcade.XYWH(origin_x + rendered_width / 2, origin_y + rendered_height / 2, rendered_width, rendered_height)
        arcade.draw_rect_filled(arcade.XYWH(width / 2, (map_bottom + height - 120) / 2, width, height - 120), theme.floor_colors[0])
        arcade.draw_texture_rect(self.maze_texture, map_rect, pixelated=False)

        if not self.has_key:
            key_x = origin_x + (self.key_position[1] + 0.5) * scale
            key_y = origin_y + rendered_height - (self.key_position[0] + 0.5) * scale
            self.draw_key(key_x, key_y, scale)
        if not self.gate_open:
            gate_x = origin_x + (self.gate_position[1] + 0.5) * scale
            gate_y = origin_y + rendered_height - (self.gate_position[0] + 0.5) * scale
            self.draw_gate(gate_x, gate_y, scale)

        cucumber_x = origin_x + (self.maze.goal[1] + 0.5) * scale
        cucumber_y = origin_y + rendered_height - (self.maze.goal[0] + 0.5) * scale
        self.draw_cucumber(cucumber_x, cucumber_y, scale)

        row, column = self.player
        if self.move_target is not None:
            blend = min(1.0, self.move_progress)
            row += (self.move_target[0] - row) * blend
            column += (self.move_target[1] - column) * blend
        player_x = origin_x + (column + 0.5) * scale
        player_y = origin_y + rendered_height - (row + 0.5) * scale
        hop = math.sin(min(1.0, self.move_progress) * math.pi) * scale * 0.07 if self.move_target else 0
        self.draw_hamster(player_x, player_y + hop, scale)

        self.draw_label_text("controls", "BULTIŅAS  ·  P / ESC PAUZE", 38, 13, (183, 199, 171), 10, bold=True)
        if self.awaiting_space:
            self.draw_label_text("collected", "GURĶIS ATRASTS!", width / 2, height / 2 + 22, self.CREAM, 26, bold=True, anchor_x="center")
            self.draw_label_text("next", "Nospied SPACE, lai dotos tālāk", width / 2, height / 2 - 14, (183, 211, 157), 14, anchor_x="center")
        if self.game_over:
            arcade.draw_rect_filled(arcade.XYWH(width / 2, height / 2, width, height), (14, 17, 18, 220))
            self.draw_label_text("game-over", "ENERĢIJA BEIDZĀS", width / 2, height / 2 + 22, (255, 166, 135), 26, bold=True, anchor_x="center")
            self.draw_label_text("restart", "Nospied R, lai mēģinātu vēlreiz", width / 2, height / 2 - 14, self.CREAM, 14, anchor_x="center")
        if self.transition_timer > 0 and not self.awaiting_space:
            overlay = arcade.XYWH(width / 2, height / 2, width, height)
            arcade.draw_rect_filled(overlay, (16, 29, 22, 195))
            self.draw_label_text("collected", "GURĶIS ATRASTS!", width / 2, height / 2 + 22, self.CREAM, 26, bold=True, anchor_x="center")
            self.draw_label_text("next", "Tālāk ved nākamais labirints...", width / 2, height / 2 - 14, (183, 211, 157), 14, anchor_x="center")
        self.draw_star_particles()
        if self.paused:
            arcade.draw_rect_filled(arcade.XYWH(width / 2, height / 2, width, height), (14, 19, 20, 205))
            self.draw_label_text("pause-title", "PAUZE", width / 2, height / 2 + 13, self.CREAM, 30, bold=True, anchor_x="center")
            self.draw_label_text("pause-hint", "Nospied P vai Esc, lai turpinātu", width / 2, height / 2 - 24, self.MUTED, 14, anchor_x="center")

    def draw_energy_bar(self, width: float, height: float) -> None:
        left, bottom = width - 250, height - 85
        bar_width = 148
        fraction = max(0.0, min(1.0, self.energy / self.max_energy))
        color = (116, 202, 125) if fraction > 0.5 else (236, 177, 82) if fraction > 0.23 else (229, 105, 85)
        self.draw_label_text("energy-label", f"ENERĢIJA  {int(self.energy)}%", left, bottom + 12, self.CREAM, 9, bold=True)
        arcade.draw_rect_filled(arcade.XYWH(left + bar_width / 2, bottom + 3, bar_width, 8), (31, 37, 37))
        if fraction:
            arcade.draw_rect_filled(arcade.XYWH(left + bar_width * fraction / 2, bottom + 3, bar_width * fraction, 8), color)

    def draw_key(self, x: float, y: float, scale: float) -> None:
        size = max(5.5, scale * 0.42)
        arcade.draw_circle_filled(x, y, size * 2.0, (25, 27, 31, 220))
        arcade.draw_circle_outline(x, y, size * 1.88, (255, 218, 126), max(1.2, size * 0.09))
        arcade.draw_circle_filled(x, y, size * 1.58, (121, 82, 43))

        bow_x, bow_y = x - size * 0.35, y + size * 0.34
        arcade.draw_circle_outline(bow_x, bow_y, size * 0.72, (76, 49, 29), max(3, size * 0.32))
        arcade.draw_circle_outline(bow_x, bow_y, size * 0.68, (255, 213, 105), max(2.5, size * 0.23))
        arcade.draw_circle_outline(bow_x, bow_y, size * 0.38, (255, 241, 188), max(1, size * 0.07))

        shaft_start = (x + size * 0.12, y - size * 0.13)
        shaft_end = (x + size * 1.36, y - size * 1.18)
        arcade.draw_line(*shaft_start, *shaft_end, (67, 45, 28), size * 0.38)
        arcade.draw_line(*shaft_start, *shaft_end, (223, 157, 56), size * 0.25)
        arcade.draw_line(x + size * 0.12, y - size * 0.02, x + size * 1.27, y - size * 0.99, (255, 225, 133), max(1.5, size * 0.07))

        for offset in (0.72, 1.08):
            tooth_x = x + size * offset
            tooth_y = y - size * (offset - 0.13)
            arcade.draw_line(tooth_x, tooth_y, tooth_x + size * 0.2, tooth_y - size * 0.27, (67, 45, 28), size * 0.3)
            arcade.draw_line(tooth_x, tooth_y, tooth_x + size * 0.2, tooth_y - size * 0.27, (240, 181, 73), size * 0.18)

        arcade.draw_circle_filled(shaft_end[0], shaft_end[1], size * 0.2, (255, 226, 145))
        sparkle_x, sparkle_y = x - size * 1.28, y + size * 1.25
        arcade.draw_line(sparkle_x - size * 0.18, sparkle_y, sparkle_x + size * 0.18, sparkle_y, (255, 248, 214), max(1.2, size * 0.08))
        arcade.draw_line(sparkle_x, sparkle_y - size * 0.18, sparkle_x, sparkle_y + size * 0.18, (255, 248, 214), max(1.2, size * 0.08))

    def draw_gate(self, x: float, y: float, scale: float) -> None:
        half = scale * 0.4
        post_width = max(2, scale * 0.11)
        arcade.draw_rect_filled(arcade.XYWH(x - half * 0.72, y, post_width, scale * 0.84), (87, 54, 39))
        arcade.draw_rect_filled(arcade.XYWH(x + half * 0.72, y, post_width, scale * 0.84), (87, 54, 39))
        arcade.draw_rect_filled(arcade.XYWH(x, y + scale * 0.33, scale * 0.92, post_width), (128, 83, 49))
        arcade.draw_rect_filled(arcade.XYWH(x, y - scale * 0.05, scale * 0.92, post_width), (128, 83, 49))
        arcade.draw_rect_filled(arcade.XYWH(x, y, scale * 0.07, scale * 0.62), (163, 111, 63))
        lock_y = y + scale * 0.02
        lock_size = max(2.5, scale * 0.13)
        arcade.draw_circle_outline(x, lock_y + lock_size * 0.22, lock_size * 0.42, self.GOLD, max(1.5, lock_size * 0.18))
        arcade.draw_rect_filled(arcade.XYWH(x, lock_y - lock_size * 0.3, lock_size * 0.8, lock_size * 0.72), self.GOLD)

    def draw_label_text(
        self,
        key: str,
        text: str,
        x: float,
        y: float,
        color: tuple[int, int, int] | tuple[int, int, int, int],
        font_size: int,
        bold: bool = False,
        anchor_x: str = "left",
    ) -> None:
        label = self.text_labels.get(key)
        if label is None:
            label = arcade.Text(
                text,
                x,
                y,
                color,
                font_size,
                bold=bold,
                anchor_x=anchor_x,
                anchor_y="baseline",
            )
            self.text_labels[key] = label
        else:
            label.text = text
            label.x = x
            label.y = y
            label.color = color
        label.draw()

    def draw_cucumber(self, x: float, y: float, scale: float) -> None:
        size = max(4, scale * 0.43)
        arcade.draw_circle_filled(x, y, size * 1.5, (238, 204, 117, 55))
        arcade.draw_circle_outline(x, y, size * 1.5, (242, 219, 154, 110), 1.5)
        arcade.draw_line(x, y - size, x, y + size, (31, 74, 39), size * 1.75)
        arcade.draw_circle_filled(x, y - size, size * 0.84, (45, 99, 50))
        arcade.draw_circle_filled(x, y + size, size * 0.84, (45, 99, 50))
        arcade.draw_line(x - size * 0.12, y - size * 0.74, x - size * 0.12, y + size * 0.72, self.GURKIS, size * 0.95)
        arcade.draw_line(x - size * 0.25, y - size * 0.48, x - size * 0.25, y + size * 0.48, (167, 203, 111), max(1, size * 0.12))
        for offset in (-0.62, -0.3, 0.08, 0.43, 0.72):
            arcade.draw_circle_filled(x + size * 0.22, y + size * offset, max(1.2, size * 0.075), (215, 223, 148))
        arcade.draw_triangle_filled(
            x - size * 0.34, y + size * 0.85,
            x + size * 0.38, y + size * 1.18,
            x + size * 0.36, y + size * 0.68,
            (132, 177, 83),
        )

    def draw_hamster(self, x: float, y: float, scale: float) -> None:
        radius = max(7, scale * 0.42)
        row_step, column_step = self.facing
        face_x, face_y = column_step, -row_step
        side_x, side_y = -face_y, face_x
        body_x = x - face_x * radius * 0.36
        body_y = y - face_y * radius * 0.2
        head_x = x + face_x * radius * 0.38
        head_y = y + face_y * radius * 0.24

        arcade.draw_circle_filled(x, y - radius * 0.75, radius * 1.02, (39, 38, 31, 170))
        arcade.draw_circle_filled(body_x, body_y, radius * 1.01, (108, 72, 48))
        arcade.draw_circle_filled(body_x, body_y + radius * 0.04, radius * 0.91, (229, 215, 184))
        arcade.draw_circle_filled(body_x - face_x * radius * 0.25 + side_x * radius * 0.29, body_y + side_y * radius * 0.29, radius * 0.38, (184, 126, 78))
        arcade.draw_circle_filled(body_x + face_x * radius * 0.18, body_y - face_y * radius * 0.18, radius * 0.43, (244, 235, 211))
        arcade.draw_circle_filled(head_x, head_y, radius * 0.78, (110, 75, 50))
        arcade.draw_circle_filled(head_x, head_y, radius * 0.69, (239, 225, 197))

        for side in (-1, 1):
            ear_x = head_x - face_x * radius * 0.38 + side * side_x * radius * 0.43
            ear_y = head_y - face_y * radius * 0.38 + side * side_y * radius * 0.43
            arcade.draw_circle_filled(ear_x, ear_y, radius * 0.29, (125, 78, 60))
            arcade.draw_circle_filled(ear_x, ear_y, radius * 0.18, (220, 151, 137))
            eye_x = head_x + face_x * radius * 0.29 + side * side_x * radius * 0.22
            eye_y = head_y + face_y * radius * 0.29 + side * side_y * radius * 0.22
            arcade.draw_circle_filled(eye_x, eye_y, max(1.5, radius * 0.09), (35, 31, 25))
            arcade.draw_circle_filled(eye_x + face_x * radius * 0.025, eye_y + face_y * radius * 0.025, max(0.7, radius * 0.03), (255, 247, 224))

        nose_x = head_x + face_x * radius * 0.58
        nose_y = head_y + face_y * radius * 0.58
        arcade.draw_circle_filled(nose_x, nose_y, max(1.6, radius * 0.11), (123, 66, 65))
        for side in (-1, 1):
            for whisker in (0.12, 0.28):
                start_x = nose_x - face_x * radius * 0.08 + side * side_x * radius * 0.12
                start_y = nose_y - face_y * radius * 0.08 + side * side_y * radius * 0.12
                end_x = start_x + face_x * radius * 0.17 + side * side_x * radius * whisker
                end_y = start_y + face_y * radius * 0.17 + side * side_y * radius * whisker
                arcade.draw_line(start_x, start_y, end_x, end_y, (250, 245, 229), 1.2)

        for side in (-1, 1):
            paw_x = body_x - face_x * radius * 0.18 + side * side_x * radius * 0.48
            paw_y = body_y - face_y * radius * 0.18 + side * side_y * radius * 0.48
            arcade.draw_circle_filled(paw_x, paw_y, radius * 0.14, (195, 143, 111))

    def spawn_stars(self) -> None:
        colors = ((255, 227, 139, 255), (255, 245, 212, 255), (237, 199, 110, 255), (239, 230, 177, 255))
        for _ in range(64):
            self.star_particles.append(
                StarParticle(
                    random.uniform(24, self.width - 24),
                    random.uniform(112, self.height - 18),
                    0.0,
                    0.0,
                    random.uniform(5, 11),
                    random.uniform(0, math.tau),
                    random.uniform(-2.8, 2.8),
                    math.inf,
                    0.0,
                    random.choice(colors),
                )
            )

        map_width, map_height = self.width - 60, self.height - 160
        scale = min(map_width / self.maze.width, map_height / self.maze.height, 24)
        rendered_width = scale * self.maze.width
        rendered_height = scale * self.maze.height
        origin_x = 30 + (map_width - rendered_width) / 2
        origin_y = 34 + (map_height - rendered_height) / 2
        center_x = origin_x + (self.player[1] + 0.5) * scale
        center_y = origin_y + rendered_height - (self.player[0] + 0.5) * scale
        for _ in range(24):
            angle = random.uniform(0, math.tau)
            self.star_particles.append(
                StarParticle(
                    center_x,
                    center_y,
                    0.0,
                    0.0,
                    random.uniform(7, 14),
                    angle,
                    random.uniform(-4, 4),
                    math.inf,
                    0.0,
                    random.choice(colors),
                )
            )

    def draw_star_particles(self) -> None:
        for particle in self.star_particles:
            fade = 0.78 + 0.22 * math.sin(particle.age * 4 + particle.rotation)
            outer_radius = particle.size * (0.72 + 0.28 * fade)
            points = []
            for index in range(10):
                radius = outer_radius if index % 2 == 0 else outer_radius * 0.42
                angle = particle.rotation + index * math.pi / 5 - math.pi / 2
                points.append((particle.x + math.cos(angle) * radius, particle.y + math.sin(angle) * radius))
            red, green, blue, _ = particle.color
            arcade.draw_polygon_filled(points, (red, green, blue, int(245 * fade)))

    def request_move(self, direction: Position) -> None:
        if self.transition_timer > 0 or self.awaiting_space or self.game_over or self.paused:
            return
        if self.move_target is not None:
            self.queued_direction = direction
            return
        row, column = self.player
        next_position = (row + direction[0], column + direction[1])
        if next_position == self.gate_position and not self.gate_open:
            return
        if next_position == self.maze.goal and not self.gate_open:
            return
        if self.maze.is_open(next_position):
            self.facing = direction
            self.move_target = next_position
            self.move_progress = 0.0

    def on_update(self, delta_time: float) -> None:
        if self.paused or self.game_over:
            return
        for particle in self.star_particles:
            particle.age += delta_time
            particle.rotation += particle.spin * delta_time * 0.2

        if self.awaiting_space:
            return

        if self.transition_timer > 0:
            self.transition_timer -= delta_time
            if self.transition_timer <= 0:
                self.level += 1
                self.maze = generate_level(self.level, random.randrange(1 << 30))
                self.player = self.maze.start
                self.move_target = None
                self.queued_direction = None
                self.move_progress = 0.0
                self.make_terrain()
            return

        if self.move_target is None:
            if self.held_directions:
                self.request_move(self.held_directions[-1])
            elif self.queued_direction is not None:
                direction = self.queued_direction
                self.queued_direction = None
                self.request_move(direction)
            return
        energy_drain = 1.5 + min(self.level - 1, 25) * 0.01
        self.energy = max(0.0, self.energy - delta_time * energy_drain)
        if self.energy <= 0:
            self.game_over = True
            self.move_target = None
            self.held_directions.clear()
            self.queued_direction = None
            return

        self.move_progress += delta_time / self.move_duration
        if self.move_progress < 1:
            return
        self.player = self.move_target
        self.move_target = None
        self.move_progress = 0.0
        if self.player == self.key_position:
            self.has_key = True
            self.gate_open = True
        if self.player == self.maze.goal:
            self.collected += 1
            self.queued_direction = None
            self.held_directions.clear()
            self.awaiting_space = True
            self.spawn_stars()
            return
        direction = self.held_directions[-1] if self.held_directions else self.queued_direction
        self.queued_direction = None
        if direction is not None:
            self.request_move(direction)

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol in (arcade.key.P, arcade.key.ESCAPE):
            self.paused = not self.paused
            self.held_directions.clear()
            return
        if self.paused:
            return
        if symbol == arcade.key.SPACE and self.awaiting_space:
            self.star_particles.clear()
            self.level += 1
            self.setup_level()
            return
        directions = {
            arcade.key.UP: (-1, 0),
            arcade.key.DOWN: (1, 0),
            arcade.key.LEFT: (0, -1),
            arcade.key.RIGHT: (0, 1),
        }
        if symbol in directions:
            direction = directions[symbol]
            if direction in self.held_directions:
                self.held_directions.remove(direction)
            self.held_directions.append(direction)
            if self.move_target is None:
                self.request_move(direction)
        elif symbol == arcade.key.R:
            self.star_particles.clear()
            self.setup_level()

    def on_key_release(self, symbol: int, modifiers: int) -> None:
        directions = {
            arcade.key.UP: (-1, 0),
            arcade.key.DOWN: (1, 0),
            arcade.key.LEFT: (0, -1),
            arcade.key.RIGHT: (0, 1),
        }
        direction = directions.get(symbol)
        if direction in self.held_directions:
            self.held_directions.remove(direction)
        if self.queued_direction == direction:
            self.queued_direction = None


def choose_maze(paths: list[Path]) -> Path:
    if len(paths) == 1:
        return paths[0]
    print("Atrastas kartes:")
    for index, path in enumerate(paths, start=1):
        print(f"  {index}. {path.name}")
    if not sys.stdin.isatty():
        print("Nav interaktīvas ievades; izvēlēta pirmā karte.")
        return paths[0]
    while True:
        answer = input(f"Izvēlies karti (1-{len(paths)}): ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(paths):
            return paths[int(answer) - 1]
        print("Ievadi vienu no sarakstā norādītajiem numuriem.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Atrisini teksta labirintu un salīdzini algoritmu laikus.")
    parser.add_argument("karte", nargs="?", type=Path, help="kartes .txt fails analīzes vai termināļa režīmam")
    parser.add_argument("--list", action="store_true", help="parāda automātiski atrastās kartes")
    parser.add_argument("--cli", action="store_true", help="palaid termināļa versiju bez grafiskā loga")
    parser.add_argument("--analyze", action="store_true", help="atver algoritmu un karšu analizatoru, nevis spēli")
    args = parser.parse_args()

    folder = Path(__file__).resolve().parent
    paths = discover_mazes(folder)
    if args.list:
        for maze_path in paths:
            print(maze_path.name)
        return 0

    if not args.cli and not args.analyze and args.karte is None:
        HamsterGameWindow()
        arcade.run()
        return 0

    if not paths:
        print(f"Mapē {folder} nav atrasta derīga .txt karte.")
        return 2

    selected_path = args.karte
    if selected_path is not None:
        if not selected_path.is_absolute():
            selected_path = Path.cwd() / selected_path
        try:
            load_maze(selected_path)
        except (OSError, UnicodeError, ValueError) as error:
            print(f"Nevar nolasīt karti {selected_path}: {error}")
            return 2
        if selected_path not in paths:
            paths.append(selected_path)

    if args.analyze:
        MazeAnalysisWindow(paths, selected_path)
        arcade.run()
        return 0

    path = selected_path or choose_maze(paths)

    try:
        maze = load_maze(path)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"Nevar nolasīt karti {path}: {error}")
        return 2

    print(f"Karte: {path.name} ({maze.height} x {maze.width})")
    results = {}
    for algorithm in ALGORITHMS:
        path_result, expanded, elapsed = benchmark(maze, algorithm)
        results[algorithm] = path_result
        steps = len(path_result) - 1 if path_result else "nav ceļa"
        print(
            f"{algorithm:>3}: soļi={steps}, apmeklētas šūnas={expanded}, "
            f"laiks={elapsed / 1_000_000:.3f} ms (mediāna no {BENCHMARK_RUNS} reizēm)"
        )

    solution = results["A*"]
    if solution is None:
        print("No sākuma līdz mērķim ceļa nav.")
        return 1
    print_solution(maze, solution)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())