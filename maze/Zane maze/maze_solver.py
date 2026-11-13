"""Find and animate solutions for text-based mazes in this folder."""

from __future__ import annotations

import os
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import TypeAlias

Position: TypeAlias = tuple[int, int]
START_MARKERS = {"A", "S"}
GOAL_MARKERS = {"B", "E", "G"}
WALL_MARKERS = {"#", "X", "1"}
OPEN_MARKERS = {" ", ".", "0"}
WALKABLE_MARKERS = START_MARKERS | GOAL_MARKERS | OPEN_MARKERS
DIRECTIONS: tuple[Position, ...] = ((-1, 0), (1, 0), (0, -1), (0, 1))
MAZE_DIRECTORY = Path(__file__).resolve().parent


@dataclass(frozen=True)
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

    def is_walkable(self, position: Position) -> bool:
        row, column = position
        return (
            0 <= row < self.height
            and 0 <= column < self.width
            and self.rows[row][column] not in WALL_MARKERS
        )


@dataclass(frozen=True)
class MazeComparison:
    path: Path
    steps: int | None
    elapsed_ms: float | None
    error: str | None = None


def parse_maze_text(text: str) -> Maze:
    """Parse an ASCII maze; shorter rows are padded with walls."""
    rows = text.splitlines()
    while rows and rows[0] == "":
        rows.pop(0)
    while rows and rows[-1] == "":
        rows.pop()
    if not rows:
        raise ValueError("Labirints ir tukšs.")

    width = max(map(len, rows))
    if width == 0:
        raise ValueError("Labirinta rindas ir tukšas.")
    padded_rows = tuple(row.ljust(width, "#") for row in rows)

    starts: list[Position] = []
    goals: list[Position] = []
    for row_index, row in enumerate(padded_rows):
        for column_index, marker in enumerate(row):
            position = (row_index, column_index)
            if marker in START_MARKERS:
                starts.append(position)
            elif marker in GOAL_MARKERS:
                goals.append(position)
            elif marker not in WALL_MARKERS | OPEN_MARKERS:
                raise ValueError(
                    f"Nepazīme simbols {marker!r} "
                    f"{row_index + 1}. rindā, {column_index + 1}. kolonnā."
                )

    if len(starts) != 1:
        raise ValueError(f"Jābūt tieši vienam sākumam (A vai S), atrasti {len(starts)}.")
    if len(goals) != 1:
        raise ValueError(f"Jābūt tieši vienam galamērķim (B, E vai G), atrasti {len(goals)}.")
    return Maze(padded_rows, starts[0], goals[0])


def load_maze(path: Path) -> Maze:
    return parse_maze_text(path.read_text(encoding="utf-8"))


def solve_maze(maze: Maze) -> list[Position]:
    """Return a shortest path from start to goal using breadth-first search."""
    queue = deque([maze.start])
    previous: dict[Position, Position | None] = {maze.start: None}

    while queue:
        current = queue.popleft()
        if current == maze.goal:
            path = []
            while current is not None:
                path.append(current)
                current = previous[current]
            return list(reversed(path))

        for row_step, column_step in DIRECTIONS:
            neighbor = (current[0] + row_step, current[1] + column_step)
            if maze.is_walkable(neighbor) and neighbor not in previous:
                previous[neighbor] = current
                queue.append(neighbor)

    raise ValueError("Labirintā nav iespējams nokļūt līdz galamērķim.")


def compare_maze_files(paths: list[Path]) -> list[MazeComparison]:
    """Measure shortest-path steps and BFS search time for each maze file."""
    comparisons: list[MazeComparison] = []
    for path in paths:
        try:
            maze = load_maze(path)
        except (OSError, UnicodeError, ValueError) as error:
            comparisons.append(MazeComparison(path, None, None, str(error)))
            continue

        started = perf_counter()
        try:
            solution = solve_maze(maze)
        except ValueError as error:
            elapsed_ms = (perf_counter() - started) * 1000
            comparisons.append(
                MazeComparison(path, None, elapsed_ms, str(error))
            )
        else:
            elapsed_ms = (perf_counter() - started) * 1000
            comparisons.append(
                MazeComparison(path, len(solution) - 1, elapsed_ms)
            )
    return comparisons


def discover_maze_files(directory: Path = MAZE_DIRECTORY) -> list[Path]:
    """Find parseable text mazes recursively, including newly added maps."""
    mazes: list[Path] = []
    for current_directory, subdirectories, filenames in os.walk(directory):
        subdirectories[:] = sorted(
            name for name in subdirectories if name not in {".venv", "__pycache__"}
        )
        for filename in sorted(filenames):
            if Path(filename).suffix.lower() != ".txt":
                continue
            path = Path(current_directory) / filename
            try:
                load_maze(path)
            except (OSError, UnicodeError, ValueError):
                continue
            mazes.append(path)
    return sorted(mazes)


def animate_solution(
    parent: tk.Misc, maze: Maze, path: list[Position], interval: int
) -> None:
    import seaborn as sns
    from matplotlib.animation import FuncAnimation
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.colors import ListedColormap
    from matplotlib.figure import Figure

    cells = [
        [0 if marker in WALL_MARKERS else 1 for marker in row]
        for row in maze.rows
    ]
    palette = sns.color_palette(["#263238", "#f2ead3"])
    popup = tk.Toplevel(parent)
    popup.title("Atrisinātais labirints")
    popup.geometry("1000x720")
    figure = Figure(
        figsize=(min(12, maze.width / 12 + 3), min(9, maze.height / 12 + 3))
    )
    axis = figure.add_subplot(111)
    axis.imshow(cells, cmap=ListedColormap(palette), interpolation="nearest")
    axis.set_xticks([])
    axis.set_yticks([])
    axis.set_title("Labirinta ceļš")

    rows, columns = zip(*path)
    axis.plot(columns, rows, color="#e5a63b", linewidth=1.5, alpha=0.85)
    axis.scatter(
        [maze.start[1], maze.goal[1]],
        [maze.start[0], maze.goal[0]],
        c=["#4b9b68", "#477ac0"],
        s=22,
        zorder=3,
    )
    walker = axis.text(
        path[0][1],
        path[0][0],
        "😢",
        ha="center",
        va="center",
        fontsize=max(8, min(18, 600 // max(maze.height, maze.width))),
        fontfamily="Segoe UI Emoji",
        zorder=4,
    )
    title = axis.set_title("😢 Skumjais ceļotājs meklē izeju...")

    def update(frame: int):
        if frame < len(path):
            row, column = path[frame]
            walker.set_position((column, row))
            walker.set_text("😢")
        else:
            row, column = maze.goal
            walker.set_position((column, row))
            walker.set_text("😄")
            title.set_text("😄 Labirints atrisināts!")
        return walker, title

    canvas = FigureCanvasTkAgg(figure, master=popup)
    _animation = FuncAnimation(
        figure,
        update,
        frames=len(path) + 1,
        interval=interval,
        blit=False,
        repeat=False,
    )
    figure.tight_layout()
    popup._maze_animation = _animation
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def close_popup() -> None:
        if _animation.event_source is not None:
            _animation.event_source.stop()
        popup.destroy()

    popup.protocol("WM_DELETE_WINDOW", close_popup)


def main() -> None:
    root = tk.Tk()
    root.title("Labirinta atrisinātājs")
    root.geometry("640x480")
    root.minsize(520, 380)

    title = ttk.Label(
        root,
        text="Labirinta atrisinātājs",
        font=("Segoe UI", 18, "bold"),
    )
    title.pack(pady=(22, 6))
    ttk.Label(
        root,
        text="Izvēlies labirintu vai atver jaunu .txt failu.",
        font=("Segoe UI", 10),
    ).pack(pady=(0, 14))

    list_frame = ttk.Frame(root, padding=(24, 0, 24, 0))
    list_frame.pack(fill=tk.BOTH, expand=True)
    scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
    maze_list = tk.Listbox(
        list_frame,
        yscrollcommand=scrollbar.set,
        font=("Segoe UI", 11),
        activestyle="dotbox",
        exportselection=False,
    )
    scrollbar.config(command=maze_list.yview)
    maze_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    maze_paths = discover_maze_files()

    def display_path(path: Path) -> str:
        try:
            return str(path.relative_to(MAZE_DIRECTORY))
        except ValueError:
            return str(path)

    def add_maze(path: Path) -> None:
        if path not in maze_paths:
            maze_paths.append(path)
            maze_list.insert(tk.END, display_path(path))
        index = maze_paths.index(path)
        maze_list.selection_clear(0, tk.END)
        maze_list.selection_set(index)
        maze_list.activate(index)

    for maze_path in maze_paths:
        maze_list.insert(tk.END, display_path(maze_path))
    if maze_paths:
        maze_list.selection_set(0)
        maze_list.activate(0)

    initial_status = (
        "Izvēlies labirintu, lai sāktu."
        if maze_paths
        else "Nav atrasts neviens labirints. Atver .txt failu."
    )
    status = tk.StringVar(value=initial_status)
    ttk.Label(root, textvariable=status, anchor=tk.W).pack(
        fill=tk.X, padx=24, pady=(12, 4)
    )

    def open_maze_file() -> None:
        filename = filedialog.askopenfilename(
            parent=root,
            title="Atvērt labirinta failu",
            initialdir=str(MAZE_DIRECTORY),
            filetypes=(("Teksta labirinti", "*.txt"), ("Visi faili", "*.*")),
        )
        if filename:
            add_maze(Path(filename))

    def start_solving() -> None:
        selection = maze_list.curselection()
        if not selection or selection[0] >= len(maze_paths):
            messagebox.showwarning(
                "Nav izvēlēts labirints",
                "Izvēlies labirintu sarakstā vai atver .txt failu.",
                parent=root,
            )
            return

        maze_path = maze_paths[selection[0]]
        try:
            maze = load_maze(maze_path)
            solution = solve_maze(maze)
        except (OSError, UnicodeError, ValueError) as error:
            messagebox.showerror("Nevar atrisināt labirintu", str(error), parent=root)
            return

        status.set(f"Risinājums atrasts: {len(solution) - 1} soļi.")
        try:
            animate_solution(root, maze, solution, interval=45)
        except ImportError as error:
            messagebox.showerror(
                "Trūkst bibliotēkas",
                "PowerShell logā šajā mapē palaid:\n"
                ".\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt\n\n"
                f"{error}",
                parent=root,
            )

    def compare_maps() -> None:
        comparisons = compare_maze_files(maze_paths)
        popup = tk.Toplevel(root)
        popup.title("Labirintu salīdzinājums")
        popup.geometry("900x420")

        columns = ("maze", "steps", "time", "result")
        table = ttk.Treeview(popup, columns=columns, show="headings")
        table.heading("maze", text="Labirints")
        table.heading("steps", text="Soļi")
        table.heading("time", text="Risināšanas laiks (ms)")
        table.heading("result", text="Statuss")
        table.column("maze", width=260, anchor=tk.W)
        table.column("steps", width=90, anchor=tk.CENTER)
        table.column("time", width=170, anchor=tk.CENTER)
        table.column("result", width=340, anchor=tk.W)

        for comparison in comparisons:
            steps = "—" if comparison.steps is None else str(comparison.steps)
            elapsed = (
                "—"
                if comparison.elapsed_ms is None
                else f"{comparison.elapsed_ms:.3f}"
            )
            result = comparison.error or "Atrisināts"
            table.insert(
                "",
                tk.END,
                values=(display_path(comparison.path), steps, elapsed, result),
            )

        scrollbar = ttk.Scrollbar(
            popup, orient=tk.VERTICAL, command=table.yview
        )
        table.configure(yscrollcommand=scrollbar.set)
        table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 0), pady=12)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 12), pady=12)

    button_frame = ttk.Frame(root, padding=(24, 10, 24, 20))
    button_frame.pack(fill=tk.X)
    ttk.Button(
        button_frame,
        text="Atvērt citu labirintu...",
        command=open_maze_file,
    ).pack(side=tk.LEFT)
    ttk.Button(
        button_frame,
        text="Salīdzināt soļus un laikus",
        command=compare_maps,
    ).pack(side=tk.LEFT, padx=(10, 0))
    ttk.Button(
        button_frame,
        text="Atrisināt",
        command=start_solving,
    ).pack(side=tk.RIGHT)

    def on_maze_double_click(event: tk.Event) -> None:
        if event.widget is maze_list:
            start_solving()

    maze_list.bind("<Double-Button-1>", on_maze_double_click)
    root.mainloop()


if __name__ == "__main__":
    main()
