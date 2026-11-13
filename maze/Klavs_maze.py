"""Uzdevums:
Izveidot programmu, kas atrisina labirintu
Programmu nosaukt Klavs_maze.py, un saglabāt šajā mapē
Parādīt atrisinājumu vizuāli, piemēram, bet ne obligāti, kā PacMan
Salīdzināt soļu laikus
Programma var analizēt dažādas kartes. Izveidojam arī paši savu karti,
un programma māk automātiski atpazīt teksta failus ar kursa biedru kartēm.
Interfeisā redzama divvirzienu meklēšana, atrastais ceļš un BFS/DFS salīdzinājums.
Pieejama arī nejaušu, atrisināmu labirintu ģenerēšana un saglabāšana.

Kartes formāts: # ir siena, punkts vai tukšums ir eja, A/S ir sākums un B/E ir
izeja. Programma automātiski atrod derīgas .txt kartes šajā pašā mapē.
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


START_MARKERS = {"S", "P", "@", "A"}
EXIT_MARKERS = {"E", "G", "B"}
WALL_MARKERS = {"#", "X", "█"}
FLOOR_MARKERS = {" ", ".", "_", "0"}
NEIGHBOR_OFFSETS = ((-1, 0), (0, 1), (1, 0), (0, -1))


@dataclass(frozen=True)
class Maze:
    rows: tuple[str, ...]
    start: tuple[int, int]
    exit: tuple[int, int]


@dataclass(frozen=True)
class SearchResult:
    path: tuple[tuple[int, int], ...] | None
    visited_count: int
    elapsed_ms: float
    start_visited: frozenset[tuple[int, int]] = frozenset()
    exit_visited: frozenset[tuple[int, int]] = frozenset()
    frames: tuple[
        tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]], ...
    ] = ()


def parse_maze(text: str, source: str = "karte") -> Maze:
    """Nolasa taisnstūrveida labirintu un atrod tā sākumu un izeju."""
    rows = tuple(line for line in text.splitlines() if line != "")
    if not rows:
        raise ValueError(f"{source}: karte ir tukša.")

    width = len(rows[0])
    if width == 0 or any(len(row) != width for row in rows):
        raise ValueError(f"{source}: visām kartes rindām jābūt vienāda platuma.")

    starts: list[tuple[int, int]] = []
    exits: list[tuple[int, int]] = []
    for row_index, row in enumerate(rows):
        for column_index, cell in enumerate(row):
            if cell in START_MARKERS:
                starts.append((row_index, column_index))
            elif cell in EXIT_MARKERS:
                exits.append((row_index, column_index))
            elif cell not in WALL_MARKERS and cell not in FLOOR_MARKERS:
                raise ValueError(
                    f"{source}: neatpazīts simbols {cell!r} "
                    f"({row_index + 1}. rinda, {column_index + 1}. kolonna)."
                )

    if len(starts) != 1 or len(exits) != 1:
        raise ValueError(
            f"{source}: nepieciešams tieši viens sākums (S/P/@/A) "
            "un viena izeja (E/G/B)."
        )
    return Maze(rows, starts[0], exits[0])


def load_maze(path: Path) -> Maze:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as error:
        raise ValueError(f"Nevar nolasīt karti {path.name}: {error}") from error
    return parse_maze(text, path.name)


def find_maps(folder: Path) -> list[Path]:
    """Atgriež mapē esošās .txt datnes, kurās ir derīga karte."""
    maps: list[Path] = []
    for path in sorted(folder.glob("*.txt"), key=lambda item: item.name.casefold()):
        try:
            load_maze(path)
        except ValueError:
            continue
        maps.append(path)
    return maps


def _solve(maze: Maze, breadth_first: bool) -> tuple[
    tuple[tuple[int, int], ...] | None, int
]:
    pending = deque([maze.start])
    parent: dict[tuple[int, int], tuple[int, int] | None] = {
        maze.start: None
    }

    while pending:
        current = pending.popleft() if breadth_first else pending.pop()
        if current == maze.exit:
            path = []
            position: tuple[int, int] | None = current
            while position is not None:
                path.append(position)
                position = parent[position]
            return tuple(reversed(path)), len(parent)

        row, column = current
        for row_offset, column_offset in NEIGHBOR_OFFSETS:
            neighbor = (row + row_offset, column + column_offset)
            next_row, next_column = neighbor
            if (
                neighbor not in parent
                and 0 <= next_row < len(maze.rows)
                and 0 <= next_column < len(maze.rows[0])
                and maze.rows[next_row][next_column] not in WALL_MARKERS
            ):
                parent[neighbor] = current
                pending.append(neighbor)

    return None, len(parent)


def solve(maze: Maze, breadth_first: bool) -> SearchResult:
    started_at = time.perf_counter_ns()
    path, visited_count = _solve(maze, breadth_first)
    elapsed_ms = (time.perf_counter_ns() - started_at) / 1_000_000
    return SearchResult(path, visited_count, elapsed_ms)


def generate_maze(height: int = 71, width: int = 105) -> Maze:
    """Izveido sarežģītu, savienotu labirintu ar dažiem alternatīviem ceļiem."""
    height = max(7, height if height % 2 else height + 1)
    width = max(7, width if width % 2 else width + 1)
    cells = [["#" for _ in range(width)] for _ in range(height)]
    start = (1, 1)
    cells[start[0]][start[1]] = "."
    stack = [start]

    while stack:
        row, column = stack[-1]
        options = [
            (row + row_step * 2, column + column_step * 2, row_step, column_step)
            for row_step, column_step in NEIGHBOR_OFFSETS
            if 1 <= row + row_step * 2 < height - 1
            and 1 <= column + column_step * 2 < width - 1
            and cells[row + row_step * 2][column + column_step * 2] == "#"
        ]
        if not options:
            stack.pop()
            continue
        next_row, next_column, row_step, column_step = random.choice(options)
        cells[row + row_step][column + column_step] = "."
        cells[next_row][next_column] = "."
        stack.append((next_row, next_column))

    for row in range(1, height - 1):
        for column in range(1, width - 1):
            if cells[row][column] != "#" or random.random() >= 0.12:
                continue
            vertical_open = (
                cells[row - 1][column] != "#" and cells[row + 1][column] != "#"
            )
            horizontal_open = (
                cells[row][column - 1] != "#" and cells[row][column + 1] != "#"
            )
            if vertical_open or horizontal_open:
                cells[row][column] = "."

    start = (1, 1)
    exit_cell = (height - 2, width - 2)
    cells[start[0]][start[1]] = "S"
    cells[exit_cell[0]][exit_cell[1]] = "E"
    return Maze(tuple("".join(row) for row in cells), start, exit_cell)


def solve_bidirectional(maze: Maze) -> SearchResult:
    """Atrod īsāko ceļu, vienādi izplešot BFS slāņus no abiem galiem."""
    started_at = time.perf_counter_ns()
    start_frontier = {maze.start}
    exit_frontier = {maze.exit}
    start_parent: dict[tuple[int, int], tuple[int, int] | None] = {
        maze.start: None
    }
    exit_parent: dict[tuple[int, int], tuple[int, int] | None] = {
        maze.exit: None
    }
    start_distance = {maze.start: 0}
    exit_distance = {maze.exit: 0}
    frames: list[
        tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]
    ] = []
    meeting: tuple[int, int] | None = None

    while start_frontier and exit_frontier and meeting is None:
        start_layer: list[tuple[int, int]] = []
        exit_layer: list[tuple[int, int]] = []
        meetings: list[tuple[int, int]] = []

        for frontier, own_parent, other_parent, own_distance, discoveries in (
            (start_frontier, start_parent, exit_parent, start_distance, start_layer),
            (exit_frontier, exit_parent, start_parent, exit_distance, exit_layer),
        ):
            next_frontier: set[tuple[int, int]] = set()
            for current in sorted(frontier):
                row, column = current
                for row_step, column_step in NEIGHBOR_OFFSETS:
                    neighbor = (row + row_step, column + column_step)
                    next_row, next_column = neighbor
                    if (
                        neighbor not in own_parent
                        and 0 <= next_row < len(maze.rows)
                        and 0 <= next_column < len(maze.rows[0])
                        and maze.rows[next_row][next_column] not in WALL_MARKERS
                    ):
                        own_parent[neighbor] = current
                        own_distance[neighbor] = own_distance[current] + 1
                        next_frontier.add(neighbor)
                        discoveries.append(neighbor)
                        if neighbor in other_parent:
                            meetings.append(neighbor)
            if own_parent is start_parent:
                start_frontier = next_frontier
            else:
                exit_frontier = next_frontier

        frames.append((tuple(start_layer), tuple(exit_layer)))
        if meetings:
            meeting = min(
                meetings,
                key=lambda point: start_distance[point] + exit_distance[point],
            )

    path: tuple[tuple[int, int], ...] | None = None
    if meeting is not None:
        from_start: list[tuple[int, int]] = []
        position: tuple[int, int] | None = meeting
        while position is not None:
            from_start.append(position)
            position = start_parent[position]
        from_start.reverse()

        to_exit: list[tuple[int, int]] = []
        position = exit_parent[meeting]
        while position is not None:
            to_exit.append(position)
            position = exit_parent[position]
        path = tuple(from_start + to_exit)

    elapsed_ms = (time.perf_counter_ns() - started_at) / 1_000_000
    return SearchResult(
        path=path,
        visited_count=len(set(start_parent) | set(exit_parent)),
        elapsed_ms=elapsed_ms,
        start_visited=frozenset(start_parent),
        exit_visited=frozenset(exit_parent),
        frames=tuple(frames),
    )
def render_solution(maze: Maze, path: tuple[tuple[int, int], ...] | None) -> str:
    if path is None:
        return "\n".join(maze.rows)

    cells = [list(row) for row in maze.rows]
    for row, column in path[1:-1]:
        cells[row][column] = "*"
    return "\n".join("".join(row) for row in cells)


class MazeApp:
    """Grafiska saskarne karšu izvēlei, risināšanai un rezultātu salīdzināšanai."""

    BACKGROUND = "#f3f6fb"
    WALL_COLOR = "#26354a"
    FLOOR_COLOR = "#ffffff"
    PATH_COLOR = "#8be0cf"
    START_COLOR = "#43b581"
    EXIT_COLOR = "#ed647c"
    PACMAN_COLOR = "#ffd166"

    def __init__(self, root: tk.Tk, folder: Path, initial_map: Path | None = None):
        self.root = root
        self.folder = folder
        self.maze: Maze | None = None
        self.map_path: Path | None = None
        self.bfs_result: SearchResult | None = None
        self.dfs_result: SearchResult | None = None
        self.map_paths: list[Path] = []

        root.title("Labirinta risinātājs — BFS un DFS")
        root.geometry("1000x720")
        root.minsize(680, 480)
        root.configure(bg=self.BACKGROUND)
        self._configure_styles()
        self._build_interface()
        self.refresh_maps()

        if initial_map is not None:
            self.load_map(initial_map)
        elif self.map_paths:
            self.load_map(self.map_paths[0])

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.configure("TFrame", background=self.BACKGROUND)
        style.configure("TLabel", background=self.BACKGROUND, foreground="#233044")
        style.configure("Title.TLabel", font=("Segoe UI", 19, "bold"))
        style.configure("Info.TLabel", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10), padding=(10, 6))
        style.configure("TCombobox", padding=5)

    def _build_interface(self) -> None:
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(2, weight=1)

        ttk.Label(
            outer, text="LABIRINTA RISINĀTĀJS", style="Title.TLabel"
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            outer,
            text="Izvēlies karti, atrodi ceļu un salīdzini BFS ar DFS.",
            style="Info.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 12))

        controls = ttk.Frame(outer)
        controls.grid(row=2, column=0, sticky="nsew")
        controls.columnconfigure(0, weight=1)
        controls.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(controls)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        toolbar.columnconfigure(1, weight=1)
        ttk.Label(toolbar, text="Karte:").grid(row=0, column=0, padx=(0, 8))
        self.map_selector = ttk.Combobox(toolbar, state="readonly")
        self.map_selector.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.map_selector.bind("<<ComboboxSelected>>", self._selection_changed)
        ttk.Button(
            toolbar, text="Atjaunot kartes", command=self.refresh_maps
        ).grid(row=0, column=2, padx=(0, 8))
        ttk.Button(
            toolbar, text="Atvērt failu…", command=self.open_map
        ).grid(row=0, column=3, padx=(0, 8))
        ttk.Button(toolbar, text="Atrisināt", command=self.solve_current).grid(
            row=0, column=4
        )

        board_frame = ttk.Frame(controls)
        board_frame.grid(row=1, column=0, sticky="nsew")
        board_frame.columnconfigure(0, weight=1)
        board_frame.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(
            board_frame,
            background="#e8edf4",
            highlightthickness=1,
            highlightbackground="#d3dce8",
        )
        horizontal = ttk.Scrollbar(
            board_frame, orient="horizontal", command=self.canvas.xview
        )
        vertical = ttk.Scrollbar(
            board_frame, orient="vertical", command=self.canvas.yview
        )
        self.canvas.configure(
            xscrollcommand=horizontal.set, yscrollcommand=vertical.set
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.canvas.bind("<Configure>", self._draw_maze)

        footer = ttk.Frame(outer)
        footer.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        footer.columnconfigure(0, weight=1)
        self.status_label = ttk.Label(
            footer, text="Izvēlies karti vai atver .txt failu.", style="Info.TLabel"
        )
        self.status_label.grid(row=0, column=0, sticky="w", pady=(0, 7))
        self.results_label = ttk.Label(
            footer,
            text="BFS: —     DFS: —",
            style="Info.TLabel",
            justify="left",
        )
        self.results_label.grid(row=1, column=0, sticky="w")
        ttk.Label(
            footer,
            text="Leģenda: siena · tumša | ceļš · zaļš | Pac-Man · dzeltens | izeja · sarkana",
            style="Info.TLabel",
        ).grid(row=2, column=0, sticky="w", pady=(7, 0))

    def refresh_maps(self) -> None:
        self.map_paths = find_maps(self.folder)
        names = [path.name for path in self.map_paths]
        self.map_selector.configure(values=names)
        if self.map_path in self.map_paths:
            self.map_selector.set(self.map_path.name)
        elif names:
            self.map_selector.set(names[0])
        else:
            self.map_selector.set("")
            self.status_label.configure(
                text="Mapē nav derīgu .txt karšu. Izveido karti vai atver failu."
            )

    def _selection_changed(self, _event: tk.Event) -> None:
        selected_name = self.map_selector.get()
        selected = next(
            (path for path in self.map_paths if path.name == selected_name), None
        )
        if selected is not None:
            self.load_map(selected)

    def open_map(self) -> None:
        filename = filedialog.askopenfilename(
            title="Atvērt labirinta karti",
            initialdir=self.folder,
            filetypes=(("Teksta kartes", "*.txt"), ("Visi faili", "*.*")),
            parent=self.root,
        )
        if filename:
            self.load_map(Path(filename))

    def load_map(self, path: Path) -> None:
        try:
            maze = load_maze(path)
        except ValueError as error:
            messagebox.showerror("Nevar atvērt karti", str(error), parent=self.root)
            return

        self.maze = maze
        self.map_path = path
        self.bfs_result = None
        self.dfs_result = None
        if path not in self.map_paths:
            self.map_paths.append(path)
            self.map_paths.sort(key=lambda item: item.name.casefold())
            self.map_selector.configure(values=[item.name for item in self.map_paths])
        self.map_selector.set(path.name)
        self.status_label.configure(
            text=f"{path.name}  ·  {len(maze.rows[0])} × {len(maze.rows)} rūtiņas"
        )
        self.results_label.configure(text="BFS: —     DFS: —")
        self._draw_maze()

    def solve_current(self) -> None:
        if self.maze is None:
            messagebox.showinfo(
                "Karte nav izvēlēta",
                "Vispirms izvēlies vai atver labirinta karti.",
                parent=self.root,
            )
            return
        self.bfs_result = solve(self.maze, breadth_first=True)
        self.dfs_result = solve(self.maze, breadth_first=False)
        self.results_label.configure(
            text=(
                f"BFS — {self._result_text(self.bfs_result)}\n"
                f"DFS — {self._result_text(self.dfs_result)}"
            )
        )
        if self.bfs_result.path is None:
            self.status_label.configure(text="Izeju sasniegt nevar — ceļš nav atrasts.")
        else:
            self.status_label.configure(
                text=f"BFS īsākais ceļš: {len(self.bfs_result.path) - 1} soļi."
            )
        self._draw_maze()

    @staticmethod
    def _result_text(result: SearchResult) -> str:
        if result.path is None:
            return (
                f"ceļš nav atrasts; apskatītas {result.visited_count} rūtiņas; "
                f"{result.elapsed_ms:.3f} ms"
            )
        return (
            f"{len(result.path) - 1} soļi; apskatītas {result.visited_count} rūtiņas; "
            f"{result.elapsed_ms:.3f} ms"
        )

    def _draw_maze(self, _event: tk.Event | None = None) -> None:
        self.canvas.delete("all")
        if self.maze is None:
            self.canvas.configure(scrollregion=(0, 0, 1, 1))
            return

        available_width = max(self.canvas.winfo_width() - 24, 1)
        available_height = max(self.canvas.winfo_height() - 24, 1)
        columns = len(self.maze.rows[0])
        rows = len(self.maze.rows)
        cell_size = max(4, min(30, available_width // columns, available_height // rows))
        board_width = columns * cell_size
        board_height = rows * cell_size
        origin_x = max((available_width - board_width) // 2, 12)
        origin_y = max((available_height - board_height) // 2, 12)

        path_cells: set[tuple[int, int]] = set()
        if self.bfs_result is not None and self.bfs_result.path is not None:
            path_cells.update(self.bfs_result.path[1:-1])

        for row_index, line in enumerate(self.maze.rows):
            for column_index, cell in enumerate(line):
                x1 = origin_x + column_index * cell_size
                y1 = origin_y + row_index * cell_size
                x2, y2 = x1 + cell_size, y1 + cell_size
                if cell in WALL_MARKERS:
                    color = self.WALL_COLOR
                elif (row_index, column_index) in path_cells:
                    color = self.PATH_COLOR
                else:
                    color = self.FLOOR_COLOR
                self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill=color, outline="#dce3ec", width=1
                )

                if (row_index, column_index) == self.maze.start:
                    self.canvas.create_oval(
                        x1 + cell_size * 0.12,
                        y1 + cell_size * 0.12,
                        x2 - cell_size * 0.12,
                        y2 - cell_size * 0.12,
                        fill=self.PACMAN_COLOR,
                        outline="#b77c00",
                        width=1,
                    )
                    if cell_size >= 14:
                        self.canvas.create_arc(
                            x1 + cell_size * 0.12,
                            y1 + cell_size * 0.12,
                            x2 - cell_size * 0.12,
                            y2 - cell_size * 0.12,
                            start=35,
                            extent=290,
                            style="pieslice",
                            fill=self.BACKGROUND,
                            outline=self.BACKGROUND,
                        )
                elif (row_index, column_index) == self.maze.exit:
                    inset = cell_size * 0.2
                    self.canvas.create_oval(
                        x1 + inset,
                        y1 + inset,
                        x2 - inset,
                        y2 - inset,
                        fill=self.EXIT_COLOR,
                        outline="",
                    )

        self.canvas.configure(
            scrollregion=(
                0,
                0,
                max(board_width + 24, available_width),
                max(board_height + 24, available_height),
            )
        )


class MazeDashboard(MazeApp):
    """Tumša informācijas paneļa saskarne ar divvirzienu meklēšanas animāciju."""

    BG = "#171020"
    PANEL = "#241631"
    PANEL_ALT = "#301b3d"
    PURPLE = "#a64de0"
    ORANGE = "#ff6b35"
    TEXT = "#f4edf8"
    MUTED = "#b49bbd"
    WALL = "#261531"
    FLOOR = "#382144"
    FROM_START = "#1eb8ac"
    FROM_EXIT = "#f08c56"
    PATH = "#ffc857"

    def __init__(self, root: tk.Tk, folder: Path, initial_map: Path | None = None):
        self.root = root
        self.folder = folder
        self.maze: Maze | None = None
        self.map_path: Path | None = None
        self.map_paths: list[Path] = []
        self.search_result: SearchResult | None = None
        self.animation_result: SearchResult | None = None
        self.bfs_result: SearchResult | None = None
        self.dfs_result: SearchResult | None = None
        self.path_revealed = False
        self.animation_id: str | None = None
        self.trace_index = 0
        self.path_index = 0
        self.cell_geometry: tuple[int, int, int] | None = None
        self.cell_colors: list[list[str]] = []
        self.maze_image: tk.PhotoImage | None = None
        self.display_image: tk.PhotoImage | None = None
        self.maze_image_item: int | None = None
        self.animation_start_seen: set[tuple[int, int]] = set()
        self.animation_exit_seen: set[tuple[int, int]] = set()
        self.animation_path_seen: set[tuple[int, int]] = set()
        self.searching = False

        root.title("MAZE LAB  /  Labirinta analītika")
        root.geometry("1320x840")
        root.minsize(1000, 680)
        root.configure(bg=self.BG)
        root.protocol("WM_DELETE_WINDOW", self._close)
        self._build_dashboard()
        self.refresh_maps()
        if initial_map is not None:
            self.load_map(initial_map)
        elif self.map_paths:
            self.load_map(self.map_paths[0])

    def _label(
        self,
        parent: tk.Widget,
        text: str,
        *,
        size: int = 10,
        color: str | None = None,
        weight: str = "normal",
        **options: object,
    ) -> tk.Label:
        return tk.Label(
            parent,
            text=text,
            bg=options.pop("bg", self.PANEL),
            fg=color or self.TEXT,
            font=("Segoe UI", size, weight),
            **options,
        )

    def _button(
        self,
        parent: tk.Widget,
        text: str,
        command: object,
        *,
        accent: bool = False,
        secondary: bool = False,
    ) -> tk.Button:
        background = self.ORANGE if accent else self.PANEL_ALT
        foreground = "#241631" if accent else self.TEXT
        if secondary:
            background, foreground = self.PURPLE, self.TEXT
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=background,
            fg=foreground,
            activebackground=self.PURPLE if not accent else "#ff8558",
            activeforeground=self.TEXT,
            disabledforeground="#806e88",
            relief="flat",
            bd=0,
            padx=12,
            pady=9,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        )

    def _build_dashboard(self) -> None:
        shell = tk.Frame(self.root, bg=self.BG, padx=22, pady=18)
        shell.pack(fill="both", expand=True)
        shell.rowconfigure(2, weight=1)
        shell.columnconfigure(0, weight=1)

        header = tk.Frame(shell, bg=self.BG)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.columnconfigure(0, weight=1)
        self._label(
            header, "MAZE LAB", size=22, weight="bold", bg=self.BG
        ).grid(row=0, column=0, sticky="w")
        self._label(
            header,
            "LABIRINTU ANALĪTIKA  /  BFS · DFS · RANDOM GENERATOR",
            size=9,
            color=self.MUTED,
            bg=self.BG,
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))
        self.header_status = self._label(
            header,
            "●  SISTĒMA GATAVA",
            size=9,
            color="#68dfbd",
            bg=self.BG,
            weight="bold",
        )
        self.header_status.grid(row=0, column=1, rowspan=2, sticky="e")

        nav = tk.Frame(shell, bg=self.PANEL, padx=14, pady=10)
        nav.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        self._label(
            nav, "DASHBOARD", size=9, color=self.ORANGE, weight="bold"
        ).pack(side="left", padx=(4, 20))
        self._label(nav, "MEKLĒŠANA", size=9, color=self.MUTED).pack(
            side="left", padx=12
        )
        self._label(nav, "KARTES", size=9, color=self.MUTED).pack(
            side="left", padx=12
        )
        self._label(
            nav, "DIVVIRZIENU BFS", size=9, color=self.MUTED
        ).pack(side="right", padx=4)

        content = tk.Frame(shell, bg=self.BG)
        content.grid(row=2, column=0, sticky="nsew")
        content.rowconfigure(0, weight=1)
        content.columnconfigure(0, minsize=218)
        content.columnconfigure(1, weight=1, minsize=440)
        content.columnconfigure(2, minsize=245)

        self._build_sidebar(content)
        self._build_maze_panel(content)
        self._build_metrics_panel(content)

        footer = tk.Frame(shell, bg=self.BG)
        footer.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        footer.columnconfigure(0, weight=1)
        self.status_label = self._label(
            footer, "Izvēlies karti vai izveido jaunu labirintu.",
            size=9, color=self.MUTED, bg=self.BG,
        )
        self.status_label.grid(row=0, column=0, sticky="w")
        self._label(
            footer, "SĀKUMS  ●      MEKLĒŠANA  ◉      IZEJA  ◉      CEĻŠ  ━",
            size=9, color=self.MUTED, bg=self.BG,
        ).grid(row=0, column=1, sticky="e")

    def _build_sidebar(self, parent: tk.Frame) -> None:
        panel = tk.Frame(parent, bg=self.PANEL, padx=15, pady=16)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        panel.columnconfigure(0, weight=1)

        self._label(panel, "KARTES VADĪBA", size=10, weight="bold").grid(
            row=0, column=0, sticky="w"
        )
        self._label(
            panel, "Izvēlies vai ielādē labirintu", size=8, color=self.MUTED
        ).grid(row=1, column=0, sticky="w", pady=(4, 10))

        style = ttk.Style(self.root)
        style.configure(
            "Maze.TCombobox",
            fieldbackground=self.PANEL_ALT,
            background=self.PANEL_ALT,
            foreground=self.TEXT,
            arrowcolor=self.TEXT,
            padding=7,
        )
        style.map(
            "Maze.TCombobox",
            fieldbackground=[("readonly", self.PANEL_ALT)],
            foreground=[("readonly", self.TEXT)],
        )
        self.map_selector = ttk.Combobox(
            panel, state="readonly", style="Maze.TCombobox", font=("Segoe UI", 9)
        )
        self.map_selector.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        self.map_selector.bind("<<ComboboxSelected>>", self._selection_changed)

        self._button(panel, "Atvērt karti…", self.open_map).grid(
            row=3, column=0, sticky="ew", pady=4
        )
        self._button(panel, "Atjaunot karšu sarakstu", self.refresh_maps).grid(
            row=4, column=0, sticky="ew", pady=4
        )
        self._divider(panel, 5)
        self._label(panel, "JAUNS LABIRINTS", size=9, weight="bold").grid(
            row=6, column=0, sticky="w", pady=(12, 7)
        )

        size_row = tk.Frame(panel, bg=self.PANEL)
        size_row.grid(row=7, column=0, sticky="ew")
        self._label(size_row, "Izmērs", size=8, color=self.MUTED).pack(side="left")
        self.size_selector = ttk.Combobox(
            size_row,
            state="readonly",
            style="Maze.TCombobox",
            values=(
                "Izaicinošs · 41 × 61",
                "Liels · 71 × 105",
                "Ekstrēms · 101 × 151",
            ),
            width=17,
            font=("Segoe UI", 8),
        )
        self.size_selector.current(1)
        self.size_selector.pack(side="right")
        self._button(
            panel, "✦  Ģenerēt nejaušu", self.create_random_maze, accent=True
        ).grid(row=8, column=0, sticky="ew", pady=(9, 4))
        self._button(panel, "Saglabāt karti…", self.save_map).grid(
            row=9, column=0, sticky="ew", pady=4
        )

        self._divider(panel, 10)
        self._label(panel, "RISINĀŠANA", size=9, weight="bold").grid(
            row=11, column=0, sticky="w", pady=(12, 7)
        )
        self.solve_button = self._button(
            panel, "▶  Sākt animāciju", self.start_animation, accent=True
        )
        self.solve_button.grid(row=12, column=0, sticky="ew", pady=4)
        self.instant_button = self._button(
            panel, "Atrisināt uzreiz", self.solve_instant, secondary=True
        )
        self.instant_button.grid(row=13, column=0, sticky="ew", pady=4)
        self.stop_button = self._button(panel, "■  Apturēt", self.stop_animation)
        self.stop_button.grid(row=14, column=0, sticky="ew", pady=4)

        self._label(panel, "Animācijas ātrums", size=8, color=self.MUTED).grid(
            row=15, column=0, sticky="w", pady=(12, 3)
        )
        self.speed_scale = tk.Scale(
            panel,
            from_=1,
            to=10,
            orient="horizontal",
            showvalue=False,
            resolution=1,
            bg=self.PANEL,
            fg=self.TEXT,
            troughcolor=self.PANEL_ALT,
            activebackground=self.PURPLE,
            highlightthickness=0,
            bd=0,
        )
        self.speed_scale.set(10)
        self.speed_scale.grid(row=16, column=0, sticky="ew")
        self.stop_button.configure(state="disabled")

    def _build_maze_panel(self, parent: tk.Frame) -> None:
        panel = tk.Frame(parent, bg=self.PANEL, padx=16, pady=14)
        panel.grid(row=0, column=1, sticky="nsew", padx=(0, 12))
        panel.rowconfigure(2, weight=1)
        panel.columnconfigure(0, weight=1)
        top = tk.Frame(panel, bg=self.PANEL)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        top.columnconfigure(0, weight=1)
        self._label(top, "LABIRINTA KARTE", size=11, weight="bold").grid(
            row=0, column=0, sticky="w"
        )
        self.map_dimensions = self._label(
            top, "— × —", size=8, color=self.MUTED
        )
        self.map_dimensions.grid(row=0, column=1, sticky="e")
        self._label(
            panel, "Divi meklētāji virzās pretī viens otram.",
            size=8, color=self.MUTED,
        ).grid(row=1, column=0, sticky="w", pady=(2, 10))

        self.canvas = tk.Canvas(
            panel,
            bg="#1c1227",
            highlightthickness=1,
            highlightbackground="#432952",
        )
        self.canvas.grid(row=2, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", self._draw_maze)

        self._label(
            panel, "SĀKUMS →  IZEJA   ·   ĪSĀKAIS CEĻŠ TIEK IZCELTS",
            size=8, color=self.MUTED,
        ).grid(row=3, column=0, sticky="w", pady=(9, 0))

    def _build_metrics_panel(self, parent: tk.Frame) -> None:
        panel = tk.Frame(parent, bg=self.PANEL, padx=14, pady=16)
        panel.grid(row=0, column=2, sticky="nsew")
        panel.columnconfigure(0, weight=1)
        self._label(panel, "ANALĪTIKA", size=10, weight="bold").grid(
            row=0, column=0, sticky="w"
        )
        self._label(
            panel, "MEKLĒŠANAS REZULTĀTI", size=8, color=self.MUTED
        ).grid(row=1, column=0, sticky="w", pady=(3, 12))

        self.path_value = self._metric_card(panel, 2, "ĪSĀKAIS CEĻŠ", "—", "soļi")
        self.visited_value = self._metric_card(
            panel, 3, "APMEKLĒTĀS RŪTIŅAS", "—", "rūtiņas"
        )
        self.time_value = self._metric_card(panel, 4, "DIVVIRZIENU BFS", "—", "ms")

        self._divider(panel, 5)
        self._label(panel, "ALGORITMU SALĪDZINĀJUMS", size=8, weight="bold").grid(
            row=6, column=0, sticky="w", pady=(12, 8)
        )
        self.bfs_value = self._comparison_row(panel, 7, "BFS", self.PURPLE)
        self.dfs_value = self._comparison_row(panel, 8, "DFS", self.ORANGE)
        self._label(
            panel,
            "BFS atrod īsāko ceļu.\nDFS ceļš var būt garāks.",
            size=8,
            color=self.MUTED,
            justify="left",
        ).grid(row=9, column=0, sticky="w", pady=(12, 0))

    def _metric_card(
        self, parent: tk.Frame, row: int, title: str, value: str, unit: str
    ) -> tk.Label:
        card = tk.Frame(parent, bg=self.PANEL_ALT, padx=11, pady=9)
        card.grid(row=row, column=0, sticky="ew", pady=4)
        card.columnconfigure(0, weight=1)
        self._label(card, title, size=7, color=self.MUTED, bg=self.PANEL_ALT).grid(
            row=0, column=0, sticky="w"
        )
        value_label = self._label(
            card, value, size=20, weight="bold", bg=self.PANEL_ALT
        )
        value_label.grid(row=1, column=0, sticky="w", pady=(3, 0))
        self._label(card, unit, size=8, color=self.MUTED, bg=self.PANEL_ALT).grid(
            row=1, column=1, sticky="e", padx=(4, 0)
        )
        return value_label

    def _comparison_row(
        self, parent: tk.Frame, row: int, title: str, color: str
    ) -> tk.Label:
        frame = tk.Frame(parent, bg=self.PANEL)
        frame.grid(row=row, column=0, sticky="ew", pady=3)
        frame.columnconfigure(1, weight=1)
        self._label(frame, "●", size=10, color=color).grid(
            row=0, column=0, padx=(0, 6)
        )
        self._label(frame, title, size=8, weight="bold").grid(
            row=0, column=1, sticky="w"
        )
        result = self._label(frame, "—", size=8, color=self.MUTED)
        result.grid(row=1, column=1, columnspan=2, sticky="w", pady=(2, 0))
        return result

    def _divider(self, parent: tk.Frame, row: int) -> None:
        tk.Frame(parent, bg="#432952", height=1).grid(
            row=row, column=0, sticky="ew", pady=(12, 0)
        )

    def refresh_maps(self) -> None:
        self.map_paths = find_maps(self.folder)
        if (
            self.map_path is not None
            and self.map_path.is_file()
            and self.map_path not in self.map_paths
        ):
            self.map_paths.append(self.map_path)
            self.map_paths.sort(key=lambda item: item.name.casefold())
        self.map_selector.configure(values=[path.name for path in self.map_paths])
        if self.map_path in self.map_paths:
            self.map_selector.set(self.map_path.name)
        elif self.map_path is None and self.maze is not None:
            self.map_selector.set("Nejaušs labirints · nav saglabāts")
        elif self.map_paths:
            self.map_selector.set(self.map_paths[0].name)
            self.load_map(self.map_paths[0])
        elif not self.map_paths:
            self.map_selector.set("")

    def _selection_changed(self, _event: tk.Event) -> None:
        selected = next(
            (path for path in self.map_paths if path.name == self.map_selector.get()),
            None,
        )
        if selected is not None:
            self.load_map(selected)

    def open_map(self) -> None:
        filename = filedialog.askopenfilename(
            title="Atvērt labirinta karti",
            initialdir=self.folder,
            filetypes=(("Teksta kartes", "*.txt"), ("Visi faili", "*.*")),
            parent=self.root,
        )
        if filename:
            self.load_map(Path(filename))

    def load_map(self, path: Path) -> None:
        try:
            maze = load_maze(path)
        except ValueError as error:
            messagebox.showerror("Nevar atvērt karti", str(error), parent=self.root)
            return
        self._cancel_animation()
        self.maze = maze
        self.map_path = path
        self.search_result = None
        self.bfs_result = None
        self.dfs_result = None
        self.path_revealed = False
        self.map_selector.set(path.name)
        if path not in self.map_paths:
            self.map_paths.append(path)
            self.map_paths.sort(key=lambda item: item.name.casefold())
            self.map_selector.configure(values=[item.name for item in self.map_paths])
        self._reset_metrics()
        self._set_status(f"Karte ielādēta: {path.name}")
        self._draw_maze()

    def create_random_maze(self) -> None:
        dimensions = {
            "Izaicinošs · 41 × 61": (41, 61),
            "Liels · 71 × 105": (71, 105),
            "Ekstrēms · 101 × 151": (101, 151),
        }
        height, width = dimensions.get(self.size_selector.get(), (71, 105))
        self._cancel_animation()
        self.maze = generate_maze(height, width)
        self.map_path = None
        self.search_result = None
        self.bfs_result = None
        self.dfs_result = None
        self.path_revealed = False
        self.map_selector.set("Nejaušs labirints · nav saglabāts")
        self._reset_metrics()
        self.map_dimensions.configure(text=f"{width} × {height}")
        self._set_status("Izveidots jauns atrisināms nejaušais labirints.")
        self._draw_maze()

    def save_map(self) -> None:
        if self.maze is None:
            messagebox.showinfo(
                "Nav kartes", "Vispirms izvēlies vai izveido karti.", parent=self.root
            )
            return
        filename = filedialog.asksaveasfilename(
            title="Saglabāt labirinta karti",
            initialdir=self.folder,
            initialfile="nejaušs_labirints.txt",
            defaultextension=".txt",
            filetypes=(("Teksta karte", "*.txt"),),
            parent=self.root,
        )
        if not filename:
            return
        path = Path(filename)
        try:
            path.write_text("\n".join(self.maze.rows) + "\n", encoding="utf-8")
        except OSError as error:
            messagebox.showerror(
                "Nevar saglabāt karti", str(error), parent=self.root
            )
            return
        self.map_path = path
        self.map_selector.set(path.name)
        if path not in self.map_paths:
            self.map_paths.append(path)
            self.map_paths.sort(key=lambda item: item.name.casefold())
            self.map_selector.configure(values=[item.name for item in self.map_paths])
        self._set_status(f"Karte saglabāta: {path.name}")

    def _reset_metrics(self) -> None:
        self.path_value.configure(text="—")
        self.visited_value.configure(text="—")
        self.time_value.configure(text="—")
        self.bfs_value.configure(text="—")
        self.dfs_value.configure(text="—")

    def _set_status(self, text: str) -> None:
        self.status_label.configure(text=text)
        active = self.searching
        self.header_status.configure(
            text="●  " + ("MEKLĒŠANA" if active else "SISTĒMA GATAVA"),
            fg=self.ORANGE if active else "#68dfbd",
        )

    def _benchmark(self) -> None:
        if self.maze is None:
            return
        self.search_result = solve_bidirectional(self.maze)
        self.bfs_result = solve(self.maze, breadth_first=True)
        self.dfs_result = solve(self.maze, breadth_first=False)
        result = self.search_result
        self.path_value.configure(
            text=str(len(result.path) - 1) if result.path else "Nav"
        )
        self.visited_value.configure(text=str(result.visited_count))
        self.time_value.configure(text=f"{result.elapsed_ms:.3f}")
        self.bfs_value.configure(
            text=self._short_result(self.bfs_result), fg=self.MUTED
        )
        self.dfs_value.configure(
            text=self._short_result(self.dfs_result), fg=self.MUTED
        )

    @staticmethod
    def _short_result(result: SearchResult) -> str:
        if result.path is None:
            return f"Nav ceļa  ·  {result.elapsed_ms:.3f} ms"
        return f"{len(result.path) - 1} soļi  ·  {result.elapsed_ms:.3f} ms"

    def start_animation(self) -> None:
        if self.maze is None:
            messagebox.showinfo(
                "Karte nav izvēlēta",
                "Vispirms izvēlies karti vai ģenerē nejaušu labirintu.",
                parent=self.root,
            )
            return
        needs_reset = self.search_result is not None
        self._cancel_animation()
        if needs_reset:
            self.search_result = None
            self.path_revealed = False
            self._draw_maze()
        self._benchmark()
        self.animation_result = self.search_result
        self.path_revealed = False
        self.trace_index = 0
        self.path_index = 0
        self.animation_start_seen.clear()
        self.animation_exit_seen.clear()
        self.animation_path_seen.clear()
        self.searching = True
        self.stop_button.configure(state="normal")
        self.solve_button.configure(state="disabled")
        self._set_status("No abiem galiem tiek meklēts ceļš…")
        self._animate_search()

    def _animate_search(self) -> None:
        if not self.searching or self.animation_result is None:
            return
        frames = self.animation_result.frames
        path = self.animation_result.path
        half_length = (len(path) + 1) // 2 if path is not None else 0
        animation_steps = max(len(frames), half_length)
        batch = int(self.speed_scale.get())
        stop_at = min(self.trace_index + batch, animation_steps)
        colored_cells: list[tuple[tuple[int, int], str]] = []
        while self.trace_index < stop_at and self.trace_index < len(frames):
            start_layer, exit_layer = frames[self.trace_index]
            self.trace_index += 1
            for cell in start_layer:
                self.animation_start_seen.add(cell)
                if cell not in (self.maze.start, self.maze.exit):
                    color = (
                        self.PURPLE
                        if cell in self.animation_exit_seen
                        else self.FROM_START
                    )
                    colored_cells.append((cell, color))
            for cell in exit_layer:
                self.animation_exit_seen.add(cell)
                if cell not in (self.maze.start, self.maze.exit):
                    color = (
                        self.PURPLE
                        if cell in self.animation_start_seen
                        else self.FROM_EXIT
                    )
                    colored_cells.append((cell, color))
        if self.trace_index < stop_at:
            self.trace_index = stop_at
        self._color_cells(colored_cells)
        if self.trace_index < animation_steps:
            self.animation_id = self.root.after(
                max(1, 20 - int(self.speed_scale.get()) * 2),
                self._animate_search,
            )
            return
        if self.animation_result.path is None:
            self._finish_animation("Ceļš nav atrasts — pārbaudi, vai karte ir savienota.")
        else:
            self._set_status("Meklētāji satikās. Tiek izgaismots īsākais ceļš…")
            self._animate_path()

    def _animate_path(self) -> None:
        if not self.searching or self.animation_result is None:
            return
        path = self.animation_result.path
        if path is None:
            self._finish_animation("Ceļš nav atrasts.")
            return
        half_length = (len(path) + 1) // 2
        if self.path_index >= half_length:
            self._finish_animation(
                f"Īsākais ceļš atrasts — {len(path) - 1} soļi."
            )
            return
        batch = max(1, int(self.speed_scale.get()) * 2)
        stop_at = min(self.path_index + batch, half_length)
        path_cells: list[tuple[int, int]] = []
        while self.path_index < stop_at:
            left = path[(len(path) - 1) // 2 - self.path_index]
            right = path[len(path) // 2 + self.path_index]
            self.path_index += 1
            for cell in (left, right):
                self.animation_path_seen.add(cell)
                if cell not in (self.maze.start, self.maze.exit):
                    path_cells.append(cell)
        self._color_cells([(cell, self.PATH) for cell in path_cells])
        self.animation_id = self.root.after(
            max(1, 20 - int(self.speed_scale.get()) * 2), self._animate_path
        )

    def solve_instant(self) -> None:
        if self.maze is None:
            messagebox.showinfo(
                "Karte nav izvēlēta", "Vispirms izvēlies vai izveido karti.",
                parent=self.root,
            )
            return
        self._cancel_animation()
        self._benchmark()
        self.path_revealed = True
        self._draw_maze()
        if self.search_result is not None and self.search_result.path is not None:
            self._move_pacman(self.search_result.path[0])
            self._move_exit_agent(self.search_result.path[-1])
            self._set_status(
                f"Īsākais ceļš atrasts — {len(self.search_result.path) - 1} soļi."
            )
        else:
            self._set_status("Ceļš nav atrasts — karte nav savienota.")

    def stop_animation(self) -> None:
        if self.searching:
            self._cancel_animation()
            self._set_status("Animācija apturēta.")

    def _finish_animation(self, message: str) -> None:
        self.searching = False
        self.animation_id = None
        self.solve_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.search_result = self.animation_result
        self.animation_result = None
        if self.search_result is not None:
            self.path_revealed = self.search_result.path is not None
            overlap = (self.search_result.start_visited & self.search_result.exit_visited)
            path = set(self.search_result.path or ())
            self._color_cells(
                [(cell, self.PURPLE) for cell in overlap - path]
            )
        self._set_status(message)

    def _cancel_animation(self) -> None:
        if self.animation_id is not None:
            self.root.after_cancel(self.animation_id)
            self.animation_id = None
        self.searching = False
        self.animation_result = None
        self.animation_start_seen.clear()
        self.animation_exit_seen.clear()
        self.animation_path_seen.clear()
        if hasattr(self, "solve_button"):
            self.solve_button.configure(state="normal")
            self.stop_button.configure(state="disabled")

    def _close(self) -> None:
        self._cancel_animation()
        self.root.destroy()

    def _draw_maze(self, _event: tk.Event | None = None) -> None:
        self.canvas.delete("all")
        self.cell_geometry = None
        self.maze_image = None
        self.display_image = None
        self.maze_image_item = None
        if self.maze is None:
            return

        rows, columns = len(self.maze.rows), len(self.maze.rows[0])
        available_width = max(self.canvas.winfo_width() - 28, 1)
        available_height = max(self.canvas.winfo_height() - 28, 1)
        cell_size = max(
            1, min(25, available_width // columns, available_height // rows)
        )
        board_width, board_height = columns * cell_size, rows * cell_size
        origin_x = max((available_width - board_width) // 2, 14)
        origin_y = max((available_height - board_height) // 2, 14)
        self.cell_geometry = (cell_size, origin_x, origin_y)
        self.map_dimensions.configure(text=f"{columns} × {rows}")

        result = self.search_result
        start_visited = result.start_visited if result else frozenset()
        exit_visited = result.exit_visited if result else frozenset()
        path = set(result.path or ()) if result and self.path_revealed else set()
        start_visited = start_visited | self.animation_start_seen
        exit_visited = exit_visited | self.animation_exit_seen
        path.update(self.animation_path_seen)
        self.cell_colors = []
        for row, line in enumerate(self.maze.rows):
            color_row = []
            for column, symbol in enumerate(line):
                point = (row, column)
                if symbol in WALL_MARKERS:
                    fill = self.WALL
                elif point in path:
                    fill = self.PATH
                elif point in start_visited and point in exit_visited:
                    fill = self.PURPLE
                elif point in start_visited:
                    fill = self.FROM_START
                elif point in exit_visited:
                    fill = self.FROM_EXIT
                else:
                    fill = self.FLOOR
                color_row.append(fill)
            self.cell_colors.append(color_row)

        self.maze_image = tk.PhotoImage(
            master=self.canvas, width=columns, height=rows
        )
        self._refresh_maze_image()
        self.maze_image_item = self.canvas.create_image(
            origin_x,
            origin_y,
            anchor="nw",
            image=self.display_image,
            tags=("maze_image",),
        )

        for row, line in enumerate(self.maze.rows):
            for column, _symbol in enumerate(line):
                point = (row, column)
                x1, y1 = origin_x + column * cell_size, origin_y + row * cell_size
                x2, y2 = x1 + cell_size, y1 + cell_size
                if point == self.maze.start:
                    self.canvas.create_oval(
                        x1 + cell_size * 0.18,
                        y1 + cell_size * 0.18,
                        x2 - cell_size * 0.18,
                        y2 - cell_size * 0.18,
                        fill="#ffd166",
                        outline="#fff0b5",
                        width=1,
                        tags=("pacman",),
                    )
                elif point == self.maze.exit:
                    inset = cell_size * 0.22
                    self.canvas.create_oval(
                        x1 + inset, y1 + inset, x2 - inset, y2 - inset,
                        fill="#ff6384", outline="#ffb5c5", width=1,
                    )
                    self.canvas.create_oval(
                        x1 + cell_size * 0.28,
                        y1 + cell_size * 0.28,
                        x2 - cell_size * 0.28,
                        y2 - cell_size * 0.28,
                        fill="#f3a5ff",
                        outline="#ffffff",
                        width=1,
                        tags=("exit_agent",),
                    )
        self.canvas.configure(
            scrollregion=(0, 0, board_width + 28, board_height + 28)
        )

    def _color_cell(self, point: tuple[int, int], color: str) -> None:
        self._color_cells([(point, color)])

    def _color_cells(
        self, cells: list[tuple[tuple[int, int], str]]
    ) -> None:
        for point, color in cells:
            row, column = point
            if 0 <= row < len(self.cell_colors) and 0 <= column < len(self.cell_colors[row]):
                self.cell_colors[row][column] = color
        self._refresh_maze_image()

    def _refresh_maze_image(self) -> None:
        if (
            self.maze_image is None
            or self.cell_geometry is None
        ):
            return
        data = "{" + "} {".join(" ".join(row) for row in self.cell_colors) + "}"
        self.maze_image.put(data, to=(0, 0))
        cell_size = self.cell_geometry[0]
        self.display_image = (
            self.maze_image.zoom(cell_size, cell_size)
            if cell_size > 1
            else self.maze_image
        )
        if self.maze_image_item is not None:
            self.canvas.itemconfigure(self.maze_image_item, image=self.display_image)

    def _move_pacman(self, point: tuple[int, int]) -> None:
        if self.cell_geometry is None:
            return
        cell_size, origin_x, origin_y = self.cell_geometry
        row, column = point
        center_x = origin_x + column * cell_size + cell_size / 2
        center_y = origin_y + row * cell_size + cell_size / 2
        radius = max(1, cell_size * 0.34)
        self.canvas.delete("pacman")
        self.canvas.create_oval(
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
            fill="#ffd166",
            outline="#fff0b5",
            width=1,
            tags=("pacman",),
        )

    def _move_exit_agent(self, point: tuple[int, int]) -> None:
        if self.cell_geometry is None:
            return
        cell_size, origin_x, origin_y = self.cell_geometry
        row, column = point
        center_x = origin_x + column * cell_size + cell_size / 2
        center_y = origin_y + row * cell_size + cell_size / 2
        radius = max(1, cell_size * 0.3)
        self.canvas.delete("exit_agent")
        self.canvas.create_oval(
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
            fill="#f3a5ff",
            outline="#ffffff",
            width=1,
            tags=("exit_agent",),
        )

def choose_map(maps: list[Path]) -> Path:
    if not maps:
        raise ValueError(
            "Šajā mapē neatradu derīgu .txt karti. "
            "Pārbaudi savas_karte.txt vai ievieto šeit kursa biedra karti."
        )
    if len(maps) == 1:
        return maps[0]

    print("Atrastas kartes:")
    for index, path in enumerate(maps, start=1):
        print(f"  {index}. {path.name}")
    while True:
        answer = input("Izvēlies kartes numuru: ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(maps):
            return maps[int(answer) - 1]
        print(f"Ievadi skaitli no 1 līdz {len(maps)}.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Grafiski atrisina labirintu un salīdzina BFS un DFS."
    )
    parser.add_argument(
        "karte",
        nargs="?",
        help="sākumā atveramais kartes .txt fails",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="izmantot komandrindas saskarni, nevis grafisko logu",
    )
    args = parser.parse_args()

    folder = Path(__file__).resolve().parent
    initial_map: Path | None = None
    if args.karte:
        initial_map = Path(args.karte)
        if not initial_map.is_absolute():
            initial_map = folder / initial_map
        if not initial_map.is_file():
            print(f"Kļūda: kartes fails nav atrasts: {initial_map}", file=sys.stderr)
            return 1

    if not args.cli:
        root = tk.Tk()
        MazeDashboard(root, folder, initial_map)
        root.mainloop()
        return 0

    try:
        map_path = initial_map or choose_map(find_maps(folder))
        maze = load_maze(map_path)
    except (ValueError, EOFError, KeyboardInterrupt) as error:
        print(f"Kļūda: {error}", file=sys.stderr)
        return 1

    bfs_result = solve(maze, breadth_first=True)
    dfs_result = solve(maze, breadth_first=False)

    print(f"\nKarte: {map_path.name}")
    print("BFS — atrisinājums ( * ir ceļš ):")
    print(render_solution(maze, bfs_result.path))
    print("\nRezultāti:")
    for name, result in (("BFS", bfs_result), ("DFS", dfs_result)):
        if result.path is None:
            print(
                f"  {name}: ceļš nav atrasts; apskatītas "
                f"{result.visited_count} rūtiņas; {result.elapsed_ms:.3f} ms"
            )
        else:
            steps = len(result.path) - 1
            print(
                f"  {name}: {steps} soļi; apskatītas "
                f"{result.visited_count} rūtiņas; {result.elapsed_ms:.3f} ms"
            )
    print("\nBFS atrod īsāko ceļu; izpildes laiks var mainīties katrā palaišanas reizē.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
