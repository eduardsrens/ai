"""
Maze solver visualiser.
Methods: A*, BFS, DFS, dead-end filling, flood fill, Trémaux, wall follower.

Requires: matplotlib (numpy comes with it)
Run:
    python maze_solver.py               # starts with the built-in maze
    python maze_solver.py my_maze.txt   # starts with a text file

Maze format: '#' = wall, ' ' = open, 'A' = start, 'B' = goal.
Rows can be ragged; short rows are padded with walls.
Load a different maze at any time with "Browse..." or by typing a path.
"""
import heapq
import os
import sys
from collections import Counter, deque
from math import cos, pi, sin

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.widgets import Button, CheckButtons, Slider, TextBox

MAZE = """
#########################
#A  #       #           #
# # # ##### # ######### #
# #   #   #   #       # #
# ##### # ##### ##### # #
#     # #     #     #   #
##### # ##### ##### ### #
#   # #     #     #   # #
# # # ##### ##### # # # #
# #       #     #   #   #
# ####### ##### ####### #
#       #     #       # #
# ##### ##### # ##### # #
#     #       #     #  B#
#########################
"""

DIRS = [(-1, 0), (0, 1), (1, 0), (0, -1)]  # N, E, S, W
COLORS = ["#e6194B", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#42d4f4", "#f032e6"]
GREY = "#9e9e9e"
WALL_RGB = (0.13, 0.13, 0.15)
OPEN_RGB = (1.0, 1.0, 1.0)
START_RGB = (0.2, 0.8, 0.3)
GOAL_RGB = (0.9, 0.2, 0.2)
ALLOWED = set("# AB")


# ---------------------------------------------------------------- parsing

def parse_maze(text):
    lines = [line.replace("\t", "    ") for line in text.splitlines()]
    while lines and not lines[0].strip():   # drop blank lines at the top...
        lines.pop(0)
    while lines and not lines[-1].strip():  # ...and at the bottom
        lines.pop()
    if not lines:
        raise ValueError("the file is empty")

    width = max(len(line) for line in lines)
    grid = [list(line.ljust(width, "#")) for line in lines]
    start = goal = None
    starts = goals = 0
    for r, row in enumerate(grid):
        for c, ch in enumerate(row):
            if ch not in ALLOWED:
                raise ValueError(f"unexpected character {ch!r} on row {r + 1}")
            if ch == "A":
                start, starts = (r, c), starts + 1
            elif ch == "B":
                goal, goals = (r, c), goals + 1
    if starts != 1 or goals != 1:
        raise ValueError(f"need exactly one A and one B (found {starts} A, {goals} B)")
    return grid, start, goal


def is_open(grid, r, c):
    return 0 <= r < len(grid) and 0 <= c < len(grid[0]) and grid[r][c] != "#"


def neighbors(grid, cell):
    r, c = cell
    for dr, dc in DIRS:
        if is_open(grid, r + dr, c + dc):
            yield (r + dr, c + dc)


def trace(parent, start, goal):
    """Rebuild a path from a parent dictionary."""
    if goal != start and goal not in parent:
        return None
    path = [goal]
    while path[-1] != start:
        path.append(parent[path[-1]])
    return path[::-1]


def push_route(route, nxt):
    """Keep `route` a simple path. Stepping back onto the route trims it."""
    if nxt in route:
        del route[route.index(nxt) + 1:]
    else:
        route.append(nxt)


# ---------------------------------------------------------------- algorithms
# Each one is a generator. It yields ('visit', cell), ('fill', cell), and
# finally ('path', list_of_cells_or_None).

def bfs(grid, start, goal):
    parent, seen, queue = {}, {start}, deque([start])
    while queue:
        cur = queue.popleft()
        yield ("visit", cur)
        if cur == goal:
            break
        for n in neighbors(grid, cur):
            if n not in seen:
                seen.add(n)
                parent[n] = cur
                queue.append(n)
    yield ("path", trace(parent, start, goal))


def dfs(grid, start, goal):
    parent, seen, stack = {}, set(), [start]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        yield ("visit", cur)
        if cur == goal:
            break
        for n in neighbors(grid, cur):
            if n not in seen:
                parent[n] = cur
                stack.append(n)
    yield ("path", trace(parent, start, goal))


def astar(grid, start, goal):
    def h(cell):
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])

    g = {start: 0}
    parent, closed = {}, set()
    heap = [(h(start), 0, start)]
    while heap:
        _, gc, cur = heapq.heappop(heap)
        if cur in closed:
            continue
        closed.add(cur)
        yield ("visit", cur)
        if cur == goal:
            break
        for n in neighbors(grid, cur):
            ng = gc + 1
            if n not in closed and ng < g.get(n, float("inf")):
                g[n] = ng
                parent[n] = cur
                heapq.heappush(heap, (ng + h(n), ng, n))
    yield ("path", trace(parent, start, goal))


def flood_fill(grid, start, goal):
    """Flood outward in waves, then trace back down the distance gradient."""
    dist = {start: 0}
    wave = [start]
    while wave and goal not in dist:
        next_wave = []
        for cell in wave:
            yield ("visit", cell)
            for n in neighbors(grid, cell):
                if n not in dist:
                    dist[n] = dist[cell] + 1
                    next_wave.append(n)
        wave = next_wave

    path = None
    if goal in dist:
        path, cur = [goal], goal
        while cur != start:
            cur = next(n for n in neighbors(grid, cur)
                       if n in dist and dist[n] == dist[cur] - 1)
            path.append(cur)
        path.reverse()
    yield ("path", path)


def dead_end_fill(grid, start, goal):
    """Repeatedly remove dead ends. What remains is the solution."""
    open_cells = {(r, c) for r in range(len(grid)) for c in range(len(grid[0]))
                  if grid[r][c] != "#"}
    protected = (start, goal)

    def degree(cell):
        r, c = cell
        return sum((r + dr, c + dc) in open_cells for dr, dc in DIRS)

    queue = deque(c for c in open_cells if degree(c) <= 1 and c not in protected)
    while queue:
        cell = queue.popleft()
        if cell not in open_cells or cell in protected or degree(cell) > 1:
            continue
        open_cells.remove(cell)
        yield ("fill", cell)
        r, c = cell
        for dr, dc in DIRS:
            n = (r + dr, c + dc)
            if n in open_cells and n not in protected and degree(n) <= 1:
                queue.append(n)

    # Walk the remaining corridor from A to B
    parent, seen, queue = {}, {start}, deque([start])
    while queue:
        cur = queue.popleft()
        if cur == goal:
            break
        r, c = cur
        for dr, dc in DIRS:
            n = (r + dr, c + dc)
            if n in open_cells and n not in seen:
                seen.add(n)
                parent[n] = cur
                queue.append(n)
    yield ("path", trace(parent, start, goal))


def tremaux(grid, start, goal, max_steps=None):
    """Trémaux's algorithm: mark passages, never enter one marked twice."""
    if max_steps is None:
        max_steps = 20 * len(grid) * len(grid[0])
    passes = Counter()  # directed traversal counts
    cur, prev = start, None
    route = [start]
    yield ("visit", cur)
    for _ in range(max_steps):
        if cur == goal:
            break
        options = []
        for n in neighbors(grid, cur):
            marks = passes[(cur, n)] + passes[(n, cur)]
            if marks < 2:  # fully explored passages are skipped
                options.append((marks, n == prev, n))
        if not options:
            break
        _, _, nxt = min(options)  # fewest marks first, going back last
        passes[(cur, nxt)] += 1
        push_route(route, nxt)
        prev, cur = cur, nxt
        yield ("visit", cur)
    yield ("path", route if cur == goal else None)


def wall_follower(grid, start, goal, max_steps=None):
    """Left-hand rule. Only reliable when walls connect to the outer border."""
    if max_steps is None:
        max_steps = 20 * len(grid) * len(grid[0])
    heading = 1  # start facing east (N=0, E=1, S=2, W=3)
    cur = start
    route = [start]
    yield ("visit", cur)
    for _ in range(max_steps):
        if cur == goal:
            break
        for turn in (-1, 0, 1, 2):  # left, straight, right, back
            d = (heading + turn) % 4
            nxt = (cur[0] + DIRS[d][0], cur[1] + DIRS[d][1])
            if is_open(grid, *nxt):
                heading, cur = d, nxt
                push_route(route, cur)
                yield ("visit", cur)
                break
    yield ("path", route if cur == goal else None)


METHODS = [
    ("A*", astar),
    ("BFS", bfs),
    ("DFS", dfs),
    ("Dead-end filling", dead_end_fill),
    ("Flood fill", flood_fill),
    ("Trémaux", tremaux),
    ("Wall follower", wall_follower),
]


# ---------------------------------------------------------------- viewer

class MazeViewer:
    TICK_MS = 30
    MAX_SPEED = 200

    def __init__(self, text, name="built-in maze"):
        self.grid = None
        self.runs = []
        self.total = 0
        self.t = 0
        self.acc = 0.0
        self.playing = False
        self.artists = []
        self.name = name

        self._build_figure()
        self.timer = self.fig.canvas.new_timer(interval=self.TICK_MS)
        self.timer.add_callback(self._tick)
        self.timer.start()
        self.load_text(text, name)

    # ---- loading

    def load_text(self, text, name="maze"):
        """Parse a maze, run every method, and redraw. Keeps the old maze on error."""
        self._say(f"Loading {name}...")
        try:
            grid, start, goal = parse_maze(text)
            runs = [(label, list(fn(grid, start, goal))) for label, fn in METHODS]
        except Exception as e:
            self._say(f"Could not load {name}: {e}")
            return False

        self.grid, self.start, self.goal = grid, start, goal
        self.H, self.W = len(grid), len(grid[0])
        self.runs = runs
        self.total = max(len(evs) for _, evs in runs)

        n = len(METHODS)
        # Small offsets keep overlapping routes visible
        self.offsets = [(0.16 * cos(2 * pi * i / n), 0.16 * sin(2 * pi * i / n))
                        for i in range(n)]

        self.name = name
        self.t = 0
        self.acc = 0.0
        self.playing = False
        self.btn_play.label.set_text("Play")
        self._draw_background()
        self.draw()
        return True

    def load_file(self, path):
        path = path.strip().strip('"').strip("'")
        if not path:
            self._say("Type or browse to a .txt file first.")
            return
        try:
            # utf-8-sig also handles files saved with a BOM (common on Windows)
            with open(path, encoding="utf-8-sig") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError) as e:
            self._say(f"Could not open file: {e}")
            return
        self.path_box.set_val(path)
        self.load_text(text, os.path.basename(path))

    def browse(self, _event=None):
        try:
            import tkinter as tk
            from tkinter import filedialog
        except ImportError:
            self._say("tkinter isn't available here. Type the file path in the box instead.")
            return
        try:
            root = tk.Tk()
        except tk.TclError as e:
            self._say(f"Could not open the file dialog: {e}. Use the path box instead.")
            return
        root.withdraw()
        root.attributes("-topmost", True)
        try:
            path = filedialog.askopenfilename(
                title="Choose a maze file",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        finally:
            root.destroy()
        if path:
            self.load_file(path)

    # ---- layout

    def _build_figure(self):
        self.fig = plt.figure(figsize=(15, 9), facecolor="white")
        try:
            self.fig.canvas.manager.set_window_title("Maze solver")
        except AttributeError:
            pass  # some backends have no window title

        self.ax = self.fig.add_axes([0.03, 0.06, 0.6, 0.86])

        # Right-hand panel
        self.fig.text(0.68, 0.955, "Maze solver", fontsize=16, weight="bold", color="#222")
        self.fig.text(0.68, 0.905, "Show methods", fontsize=10, weight="bold", color="#555")

        names = [name for name, _ in METHODS]
        self.ax_checks = self.fig.add_axes([0.68, 0.50, 0.28, 0.39])
        try:
            # Matplotlib 3.7+ lets us enlarge the boxes and the check marks
            self.checks = CheckButtons(
                self.ax_checks, names, [True] * len(names),
                label_props={"fontsize": 14},
                frame_props={"s": 260, "linewidth": 1.6},
                check_props={"s": 180, "linewidth": 2.4})
        except TypeError:
            # Older matplotlib: fall back to a larger label font only
            self.checks = CheckButtons(self.ax_checks, names, [True] * len(names))
            for label in self.checks.labels:
                label.set_fontsize(14)
        for label, color in zip(self.checks.labels, COLORS):
            label.set_color(color)
            label.set_fontweight("bold")
        self.checks.on_clicked(lambda _label: self.draw())

        # Playback
        self.fig.text(0.68, 0.455, "Playback", fontsize=10, weight="bold", color="#555")
        btn_y, btn_h, btn_w = 0.405, 0.045, 0.065
        self.btn_reset = Button(self.fig.add_axes([0.68, btn_y, btn_w, btn_h]), "Reset")
        self.btn_back = Button(self.fig.add_axes([0.7525, btn_y, btn_w, btn_h]), "<< Back")
        self.btn_play = Button(self.fig.add_axes([0.825, btn_y, btn_w, btn_h]), "Play")
        self.btn_fwd = Button(self.fig.add_axes([0.8975, btn_y, btn_w, btn_h]), "Fwd >>")
        self.btn_reset.on_clicked(lambda _: self.reset())
        self.btn_back.on_clicked(lambda _: self.step(-1))
        self.btn_play.on_clicked(lambda _: self.toggle_play())
        self.btn_fwd.on_clicked(lambda _: self.step(1))

        self.speed = Slider(self.fig.add_axes([0.68, 0.355, 0.28, 0.025]),
                            "Steps/sec", 1, self.MAX_SPEED, valinit=8,
                            valstep=1, valfmt="%d")

        # Maze loading
        self.fig.text(0.68, 0.31, "Maze file", fontsize=10, weight="bold", color="#555")
        self.path_box = TextBox(self.fig.add_axes([0.68, 0.265, 0.28, 0.035]),
                                "Path: ", initial="")
        self.path_box.on_submit(self.load_file)
        self.btn_load = Button(self.fig.add_axes([0.68, 0.215, 0.135, 0.04]), "Load path")
        self.btn_browse = Button(self.fig.add_axes([0.825, 0.215, 0.135, 0.04]), "Browse...")
        self.btn_load.on_clicked(lambda _: self.load_file(self.path_box.text))
        self.btn_browse.on_clicked(self.browse)

        self.status = self.fig.text(0.68, 0.165, "", fontsize=8.5, family="monospace",
                                    va="top", linespacing=1.3, color="#222")
        self.fig.canvas.mpl_connect("key_press_event", self._on_key)

    def _draw_background(self):
        self.ax.clear()
        self.artists = []
        img = np.empty((self.H, self.W, 3))
        img[:] = OPEN_RGB
        walls = np.array([[ch == "#" for ch in row] for row in self.grid])
        img[walls] = WALL_RGB
        img[self.start] = START_RGB
        img[self.goal] = GOAL_RGB
        self.ax.imshow(img, interpolation="nearest")
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        for spine in self.ax.spines.values():
            spine.set_visible(False)
        self.ax.set_title(self.name, fontsize=11, color="#333", pad=8)

    def _say(self, msg):
        """Show a message in the status panel without touching the maze."""
        self.status.set_text(msg)
        self.fig.canvas.draw_idle()

    # ---- playback

    def set_t(self, t):
        self.t = max(0, min(t, self.total))
        self.draw()

    def step(self, n):
        self.playing = False
        self.btn_play.label.set_text("Play")
        self.set_t(self.t + n)

    def reset(self):
        self.playing = False
        self.btn_play.label.set_text("Play")
        self.set_t(0)

    def toggle_play(self):
        if not self.playing and self.t >= self.total:
            self.t = 0
        self.playing = not self.playing
        self.btn_play.label.set_text("Pause" if self.playing else "Play")
        self.acc = 0.0
        self.set_t(self.t)

    def _tick(self):
        if not self.playing:
            return
        self.acc += self.speed.val * self.TICK_MS / 1000
        n = int(self.acc)
        self.acc -= n
        if n:
            self.set_t(self.t + n)
        if self.t >= self.total:
            self.playing = False
            self.btn_play.label.set_text("Play")
            self.draw()

    def _on_key(self, event):
        # Don't steal keystrokes while the path box is being typed into
        if getattr(self.path_box, "capturekeystrokes", False):
            return
        if event.key == "right":
            self.step(1)
        elif event.key == "left":
            self.step(-1)
        elif event.key == " ":
            self.toggle_play()

    # ---- drawing

    def draw(self):
        if not self.runs:
            return
        for artist in self.artists:
            artist.remove()
        self.artists.clear()

        shown = self.checks.get_status()
        rows = []

        for i, ((name, evs), color, (dx, dy)) in enumerate(
                zip(self.runs, COLORS, self.offsets)):
            on = shown[i]
            if on:
                col, a_trail, a_path = color, 0.8, 0.95
            else:
                col, a_trail, a_path = GREY, 0.25, 0.3

            done = evs[:self.t]
            visits = [e[1] for e in done if e[0] == "visit"]
            fills = [e[1] for e in done if e[0] == "fill"]

            # Trail between consecutive adjacent cells
            segs = []
            for a, b in zip(visits, visits[1:]):
                if abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1:
                    segs.append([(a[1] + dx, a[0] + dy), (b[1] + dx, b[0] + dy)])
            if segs:
                lc = LineCollection(segs, colors=[col], linewidths=3.5,
                                    alpha=a_trail, zorder=3, capstyle="round")
                self.ax.add_collection(lc)
                self.artists.append(lc)

            # Dead-end filling markers
            if fills:
                sc = self.ax.scatter([c + dx for r, c in fills],
                                     [r + dy for r, c in fills],
                                     marker="x", s=18, color=col,
                                     alpha=a_trail, zorder=4)
                self.artists.append(sc)

            # Final solution as a thicker line once the method has finished
            result = "running"
            if self.t >= len(evs):
                path = evs[-1][1]
                if path:
                    xs = [c + dx for r, c in path]
                    ys = [r + dy for r, c in path]
                    ln, = self.ax.plot(xs, ys, color=col, lw=6, alpha=a_path,
                                       solid_capstyle="round",
                                       solid_joinstyle="round", zorder=5)
                    self.artists.append(ln)
                    result = f"path, {len(path) - 1} steps"
                else:
                    result = "no path"
            rows.append(f"{name:<17} {result}")

        state = "playing" if self.playing else "paused"
        self.status.set_text(
            f"step {self.t} / {self.total}\n"
            f"{state}, {int(self.speed.val)} steps/s\n\n" + "\n".join(rows))
        self.fig.canvas.draw_idle()


if __name__ == "__main__":
    viewer = MazeViewer(MAZE)  # keep a reference so widgets stay alive
    if len(sys.argv) > 1:
        viewer.load_file(sys.argv[1])
    plt.show()