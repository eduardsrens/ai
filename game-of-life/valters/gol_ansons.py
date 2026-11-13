# Version history: Conway's Game of Life simulation core.
# Cell states are updated according to birth and survival rules.
# Initial conditions can be reproduced with a fixed random seed.
# Adjustable rules and neighbor counting.
# You can enter birth/survival rules, choose Moore or Von Neumann neighborhoods, and enable edge connectivity.
# Expandable board.
# When patterns approach the board edge, the grid expands automatically while preserving cell positions and view.
# Pattern palette.
# Eight starting patterns are included: Glider, LWSS, Blinker, Toad, Beehive, Block, R-pentomino, and Acorn.
# They can be dragged onto the grid.
# Pattern effects.
# Pattern placement supports "Still" and "Pulse" modes; pulsing patterns are periodically added and removed.
# Simulation controls.
# You can pause and resume the simulation, step once, reset, or generate a new random start.
# Adjustable settings.
# Sliders control the simulation speed, starting cell density, and board expansion reserve.
# Visual summaries.
# The interface shows generation, population, emitter count, board size, and a population history graph.
# Five color themes are available.
# Zoom and navigation. Includes mouse-wheel zoom, drag panning, arrow keys, keyboard zoom, and view reset.



"""An interactive, expandable Conway's Game of Life visualizer.

Run with: python life.py
Requires: numpy, matplotlib, seaborn

Controls:
  Drag a shape from the palette onto the grid to place it
  E                 cycle the effect for new drops (Still / Pulse)
  Scroll wheel      zoom toward the cursor
  Left-drag         pan (on the grid)
  + / -             zoom in / out at the center
  Arrow keys        pan
  0                 fit the whole grid
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.colors import ListedColormap
from matplotlib.widgets import Button, Slider, TextBox
import numpy as np
import seaborn as sns


SHAPES = {
    "Glider": [[0, 1, 0],
               [0, 0, 1],
               [1, 1, 1]],
    "LWSS": [[0, 1, 1, 1, 1],
             [1, 0, 0, 0, 1],
             [0, 0, 0, 0, 1],
             [1, 0, 0, 1, 0]],
    "Blinker": [[1, 1, 1]],
    "Toad": [[0, 1, 1, 1],
             [1, 1, 1, 0]],
    "Beehive": [[0, 1, 1, 0],
                [1, 0, 0, 1],
                [0, 1, 1, 0]],
    "Block": [[1, 1],
              [1, 1]],
    "R-pentomino": [[0, 1, 1],
                    [1, 1, 0],
                    [0, 1, 0]],
    "Acorn": [[0, 1, 0, 0, 0, 0, 0],
              [0, 0, 0, 1, 0, 0, 0],
              [1, 1, 0, 0, 1, 1, 1]],
}

EFFECTS = ["Still", "Pulse"]
PULSE_PERIOD = 12  # generations per pulse cycle


@dataclass
class Settings:
    seed: int = 17
    density: float = 0.22
    interval: int = 100
    birth: tuple[int, ...] = (3,)
    survive: tuple[int, ...] = (2, 3)
    edge: int = 4
    wrap: bool = False
    neighborhood: str = "Moore"


class Life:
    """Unbounded Life board stored as a NumPy array, plus shape emitters."""

    def __init__(self, height=45, width=70, settings=None):
        self.settings = settings or Settings()
        self.height, self.width = height, width
        self.rng = np.random.default_rng(self.settings.seed)
        self.grid = (self.rng.random((height, width)) < self.settings.density).astype(np.uint8)
        self.generation = 0
        self.origin = [0, 0]  # absolute position of the grid's (0, 0) cell
        self.population_history = [int(self.grid.sum())]
        self.emitters = []

    def _offsets(self):
        offsets = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]
        if self.settings.neighborhood == "Von Neumann":
            offsets = [(dy, dx) for dy, dx in offsets if abs(dy) + abs(dx) == 1]
        return offsets

    def _count_neighbors(self):
        g = self.grid
        neighbors = np.zeros(g.shape, dtype=np.uint8)
        if self.settings.wrap:
            for dy, dx in self._offsets():
                neighbors += np.roll(np.roll(g, dy, axis=0), dx, axis=1)
        else:
            p = np.pad(g, 1)
            h, w = g.shape
            for dy, dx in self._offsets():
                neighbors += p[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
        return neighbors

    def step(self):
        neighbors = self._count_neighbors()
        g = self.grid
        born = np.isin(neighbors, self.settings.birth) & (g == 0)
        lives = np.isin(neighbors, self.settings.survive) & (g == 1)
        self.grid = (born | lives).astype(np.uint8)
        self.generation += 1
        if not self.settings.wrap:
            self._expand_if_needed()
        self.population_history.append(int(self.grid.sum()))

    def _expand_if_needed(self):
        margin = max(2, self.settings.edge)
        h, w = self.grid.shape
        live = np.argwhere(self.grid)
        if not len(live):
            return
        top, left = live.min(axis=0)
        bottom, right = live.max(axis=0)
        add_top = max(0, margin - int(top))
        add_left = max(0, margin - int(left))
        add_bottom = max(0, int(bottom) - (h - margin - 1))
        add_right = max(0, int(right) - (w - margin - 1))
        if add_top or add_bottom or add_left or add_right:
            self.grid = np.pad(self.grid, ((add_top, add_bottom), (add_left, add_right)))
            self.origin[0] -= add_top
            self.origin[1] -= add_left

    def seed_pattern(self, pattern, row=None, col=None):
        pattern = np.asarray(pattern, dtype=np.uint8)
        ph, pw = pattern.shape
        h, w = self.grid.shape
        if row is None:
            row = h // 2 - ph // 2
            col = w // 2 - pw // 2

        # Pad whatever part of the pattern falls outside the current grid.
        pad_top = max(0, -row)
        pad_left = max(0, -col)
        pad_bottom = max(0, row + ph - h)
        pad_right = max(0, col + pw - w)
        if pad_top or pad_left or pad_bottom or pad_right:
            self.grid = np.pad(self.grid, ((pad_top, pad_bottom), (pad_left, pad_right)))
            self.origin[0] -= pad_top
            self.origin[1] -= pad_left
            row += pad_top
            col += pad_left

        self.grid[row:row + ph, col:col + pw] |= pattern

    # ----- shape emitters -----------------------------------------------
    # Emitters store positions in absolute coordinates, so they stay in the
    # right place when the grid grows on the top or left edges.

    def _to_index(self, abs_row, abs_col):
        return abs_row - self.origin[0], abs_col - self.origin[1]

    def _stamp_abs(self, pattern, abs_row, abs_col):
        r, c = self._to_index(abs_row, abs_col)
        self.seed_pattern(pattern, r, c)

    def _erase(self, pattern, row, col):
        ph, pw = pattern.shape
        h, w = self.grid.shape
        r0, c0 = max(0, row), max(0, col)
        r1, c1 = min(h, row + ph), min(w, col + pw)
        if r1 > r0 and c1 > c0:
            self.grid[r0:r1, c0:c1] = 0

    def add_emitter(self, pattern, abs_row, abs_col, effect):
        """Place a shape with its top-left corner at (abs_row, abs_col)."""
        self._stamp_abs(pattern, abs_row, abs_col)
        if effect != "Still":
            self.emitters.append({
                "pattern": pattern, "row": abs_row, "col": abs_col,
                "effect": effect, "birth": self.generation,
            })
        self.population_history[-1] = int(self.grid.sum())

    def update_emitters(self):
        for e in self.emitters:
            if e["effect"] == "Pulse":
                age = self.generation - e["birth"]
                phase = age % PULSE_PERIOD
                if phase == 0:
                    self._stamp_abs(e["pattern"], e["row"], e["col"])
                elif phase == PULSE_PERIOD // 2:
                    r, c = self._to_index(e["row"], e["col"])
                    self._erase(e["pattern"], r, c)
        self.population_history[-1] = int(self.grid.sum())

    def reset(self, density=None):
        if density is not None:
            self.settings.density = density
        self.rng = np.random.default_rng(self.settings.seed)
        self.grid = (self.rng.random((self.height, self.width)) < self.settings.density).astype(np.uint8)
        self.generation, self.origin = 0, [0, 0]
        self.population_history = [int(self.grid.sum())]
        self.emitters = []


def parse_counts(text, fallback):
    try:
        values = tuple(sorted({int(x.strip()) for x in text.split(",") if x.strip()}))
        if values and all(0 <= n <= 8 for n in values):
            return values
    except ValueError:
        pass
    return fallback


def main():
    # Seaborn first, so our font settings aren't overwritten afterwards.
    sns.set_theme(style="dark", context="notebook")
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.sans-serif": ["DejaVu Sans", "Arial", "sans-serif"],
        "axes.unicode_minus": False,
    })

    settings = Settings()
    life = Life(settings=settings)
    palette = {"Midnight": ("#101827", "#77f2c3"), "Neon": ("#100b26", "#ff4fd8"),
               "Ocean": ("#071d2b", "#51c7ec"), "Ember": ("#21110c", "#ffb454"),
               "Paper": ("#f0eee7", "#1c3440")}
    theme_names = list(palette)
    state = {"theme": 0, "playing": True, "effect": 0}

    # View state: xlim/ylim are None to mean "fit the whole grid".
    view = {"xlim": None, "ylim": None}
    drag = {"active": False}
    shape_drag = {"pattern": None}
    ghost = {"artist": None, "color": None}
    ZOOM_STEP = 1.25
    MIN_SPAN = 3

    fig = plt.figure(figsize=(14, 9), facecolor="#0b1120")
    ax = fig.add_axes([.055, .19, .65, .73], facecolor="#101827")
    info = fig.add_axes([.74, .53, .23, .27], facecolor="#101827")
    for spine in info.spines.values():
        spine.set_color("#26334a")
    info.tick_params(colors="#bdc8dc")
    info.set_title("POPULATION / HISTORY", color="#a6b5cd", fontsize=10, loc="left", pad=12)
    line, = info.plot(life.population_history, color="#77f2c3", lw=2)
    info.set_xlabel("Generation", color="#8392aa")
    info.set_ylabel("Cells", color="#8392aa")

    img = ax.imshow(life.grid, interpolation="nearest", aspect="equal",
                    cmap=ListedColormap(palette[theme_names[0]]), vmin=0, vmax=1)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("CONWAY'S GAME OF LIFE", loc="left", color="#e7efff",
                 fontsize=17, weight="bold", pad=15)
    subtitle = ax.text(1, 1.015, "", transform=ax.transAxes,
                       ha="right", color="#77f2c3", fontsize=9)
    status = fig.text(.74, .95, "", color="#dce7f7", fontsize=10, linespacing=1.6, va="top")
    fig.text(.055, .965, "CELLULAR AUTOMATA  /  LIVE SIMULATION",
             color="#77f2c3", fontsize=9, weight="bold")
    rules_text = fig.text(.055, .165, "", color="#8392aa", fontsize=9)
    fig.text(.74, .03, "Scroll: zoom  •  Drag: pan  •  +/−: zoom  •  Arrows: pan  •  0: fit  •  E: effect",
             color="#8392aa", fontsize=8)

    axcolor = "#172238"

    def slider(y, label, lo, hi, val, step=None):
        a = fig.add_axes([.75, y, .21, .025], facecolor=axcolor)
        return Slider(a, label, lo, hi, valinit=val, valstep=step, color="#77f2c3")

    speed = slider(.47, "Speed (ms)", 20, 500, settings.interval, 10)
    density = slider(.41, "Reset density", .02, .65, settings.density)
    edge = slider(.35, "Expansion margin", 1, 16, settings.edge, 1)

    buttons = []

    def button(x, y, w, text, callback):
        b_ax = fig.add_axes([x, y, w, .045], facecolor=axcolor)
        b = Button(b_ax, text, color=axcolor, hovercolor="#263b55")
        b.label.set_color("#dce7f7")
        b.label.set_fontsize(9)
        b.on_clicked(callback)
        buttons.append(b)  # keep a reference so the widget isn't garbage-collected
        return b

    # ----- shape palette (drag source) ----------------------------------

    thumb_axes = {}
    x = .055
    for name, pat in SHAPES.items():
        a = fig.add_axes([x, .05, .07, .075], facecolor=axcolor)
        p = np.array(pat, dtype=np.uint8)
        a.imshow(np.ma.masked_equal(p, 0), cmap=ListedColormap([palette["Midnight"][1]]),
                 vmin=0, vmax=1, interpolation="nearest")
        a.set_xticks([])
        a.set_yticks([])
        a.set_xlabel(name, color="#bdc8dc", fontsize=8, labelpad=3)
        for s in a.spines.values():
            s.set_color("#26334a")
        thumb_axes[a] = name
        x += .08

    # ----- view helpers -------------------------------------------------

    def current_limits():
        if view["xlim"] is None:
            h, w = life.grid.shape
            return (-.5, w - .5), (h - .5, -.5)
        return view["xlim"], view["ylim"]

    def apply_limits():
        (x0, x1), (y0, y1) = current_limits()
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)

    def set_view(xlim, ylim):
        view["xlim"], view["ylim"] = xlim, ylim

    def shift_view(before_origin):
        # Expansion pads the top/left edges, so move the view with the cells.
        dy = before_origin[0] - life.origin[0]
        dx = before_origin[1] - life.origin[1]
        if not (dx or dy):
            return
        if view["xlim"] is not None:
            (x0, x1), (y0, y1) = view["xlim"], view["ylim"]
            set_view((x0 + dx, x1 + dx), (y0 + dy, y1 + dy))
        # Keep an in-progress pan anchored to the cells.
        if drag["active"]:
            (x0, x1), (y0, y1) = drag["xlim"], drag["ylim"]
            drag["xlim"] = (x0 + dx, x1 + dx)
            drag["ylim"] = (y0 + dy, y1 + dy)

    def zoom(factor, cx=None, cy=None):
        (x0, x1), (y0, y1) = current_limits()
        h, w = life.grid.shape
        new_span = abs(x1 - x0) * factor
        if not MIN_SPAN <= new_span <= 10 * max(h, w):
            return
        if cx is None:
            cx = (x0 + x1) / 2
        if cy is None:
            cy = (y0 + y1) / 2
        set_view((cx + (x0 - cx) * factor, cx + (x1 - cx) * factor),
                 (cy + (y0 - cy) * factor, cy + (y1 - cy) * factor))
        redraw()

    # ----- drawing ------------------------------------------------------

    def redraw():
        theme = palette[theme_names[state["theme"]]]
        img.set_data(life.grid)
        img.set_cmap(ListedColormap(theme))
        h, w = life.grid.shape
        img.set_extent((-.5, w - .5, h - .5, -.5))
        apply_limits()

        line.set_data(np.arange(len(life.population_history)), life.population_history)
        info.set_xlim(0, max(10, len(life.population_history)))
        info.set_ylim(0, max(5, max(life.population_history) * 1.12))

        mode = "WRAP TORUS" if settings.wrap else "UNBOUNDED CANVAS"
        subtitle.set_text(f"{mode}  •  {settings.neighborhood.upper()} NEIGHBORHOOD")
        rules_text.set_text(
            f"RULES: B{''.join(map(str, settings.birth))}/S{''.join(map(str, settings.survive))}"
            "   •   Expandable edges preserve every drifting pattern")
        status.set_text(
            f"GENERATION   {life.generation:>7}\n"
            f"POPULATION   {int(life.grid.sum()):>7}\n"
            f"SHAPES       {len(life.emitters):>7}\n"
            f"CANVAS       {w} × {h}\n"
            f"ORIGIN       ({life.origin[1]}, {life.origin[0]})")
        fig.canvas.draw_idle()

    # ----- simulation actions -------------------------------------------

    def advance():
        life.settings.edge = int(edge.val)
        before = list(life.origin)
        life.step()
        life.update_emitters()
        shift_view(before)
        redraw()

    def tick(_):
        if state["playing"]:
            advance()
        return img, line

    def toggle(_):
        state["playing"] = not state["playing"]
        play.label.set_text("Pause" if state["playing"] else "Play")

    def reset(_):
        life.reset(float(density.val))
        set_view(None, None)
        redraw()

    def single(_):
        state["playing"] = False
        play.label.set_text("Play")
        advance()

    def randomize(_):
        settings.seed = random.randrange(1_000_000)
        life.reset(float(density.val))
        set_view(None, None)
        redraw()

    def cycle_effect(_):
        state["effect"] = (state["effect"] + 1) % len(EFFECTS)
        effect_btn.label.set_text(f"Effect: {EFFECTS[state['effect']]}")
        fig.canvas.draw_idle()

    def cycle_palette(_):
        state["theme"] = (state["theme"] + 1) % len(theme_names)
        redraw()

    def on_speed(value):
        anim.event_source.interval = int(value)

    def on_birth(text):
        settings.birth = parse_counts(text, settings.birth)
        redraw()

    def on_survive(text):
        settings.survive = parse_counts(text, settings.survive)
        redraw()

    # ----- shape drag and drop ------------------------------------------

    def remove_ghost():
        if ghost["artist"] is not None:
            ghost["artist"].remove()
            ghost["artist"] = None

    def update_ghost(event):
        pat = shape_drag["pattern"]
        ph, pw = pat.shape
        if event.inaxes is not ax or event.xdata is None:
            if ghost["artist"] is not None:
                ghost["artist"].set_visible(False)
                fig.canvas.draw_idle()
            return
        r = int(round(event.ydata)) - ph // 2
        c = int(round(event.xdata)) - pw // 2
        extent = (c - .5, c + pw - .5, r + ph - .5, r - .5)
        if ghost["artist"] is None:
            ghost["artist"] = ax.imshow(np.ma.masked_equal(pat, 0),
                                        cmap=ListedColormap([ghost["color"]]),
                                        vmin=0, vmax=1, interpolation="nearest",
                                        alpha=.55, extent=extent, zorder=5)
        else:
            ghost["artist"].set_extent(extent)
            ghost["artist"].set_visible(True)
        apply_limits()  # imshow and set_extent both move the limits
        fig.canvas.draw_idle()

    def finish_drop(event):
        remove_ghost()
        pat = shape_drag["pattern"]
        if event.inaxes is ax and event.xdata is not None:
            ph, pw = pat.shape
            r = int(round(event.ydata)) - ph // 2   # grid index of top-left
            c = int(round(event.xdata)) - pw // 2
            before = list(life.origin)
            life.add_emitter(pat, r + life.origin[0], c + life.origin[1],
                             EFFECTS[state["effect"]])
            shift_view(before)
            redraw()
        shape_drag["pattern"] = None
        fig.canvas.draw_idle()

    # ----- zoom and pan handlers ----------------------------------------

    def on_scroll(event):
        if event.inaxes is not ax or event.xdata is None:
            return
        factor = 1 / ZOOM_STEP if event.button == "up" else ZOOM_STEP
        zoom(factor, event.xdata, event.ydata)

    def on_press(event):
        if event.button != 1:
            return
        if event.inaxes in thumb_axes:
            name = thumb_axes[event.inaxes]
            shape_drag["pattern"] = np.array(SHAPES[name], dtype=np.uint8)
            ghost["color"] = palette[theme_names[state["theme"]]][1]
            return
        if event.inaxes is not ax:
            return
        (x0, x1), (y0, y1) = current_limits()
        drag.update(active=True, px=event.x, py=event.y, xlim=(x0, x1), ylim=(y0, y1))

    def on_motion(event):
        if shape_drag["pattern"] is not None:
            update_ghost(event)
            return
        if not drag["active"] or event.x is None:
            return
        fx = (event.x - drag["px"]) / ax.bbox.width
        fy = (event.y - drag["py"]) / ax.bbox.height
        (x0, x1), (y0, y1) = drag["xlim"], drag["ylim"]
        sx, sy = x1 - x0, y1 - y0
        # X is normal. Y is inverted (row 0 at top), so the sign flips.
        set_view((x0 - fx * sx, x1 - fx * sx),
                 (y0 + fy * sy, y1 + fy * sy))
        redraw()

    def on_release(event):
        if shape_drag["pattern"] is not None:
            finish_drop(event)
        drag["active"] = False

    def on_key(event):
        (x0, x1), (y0, y1) = current_limits()
        if event.key in ("+", "="):
            zoom(1 / ZOOM_STEP)
        elif event.key in ("-", "_"):
            zoom(ZOOM_STEP)
        elif event.key == "0":
            set_view(None, None)
            redraw()
        elif event.key == "e":
            cycle_effect(None)
        elif event.key in ("left", "right", "up", "down"):
            sx = 0.1 * (x1 - x0)
            sy = 0.1 * (y1 - y0)
            dx, dy = {"left": (-sx, 0), "right": (sx, 0),
                      "up": (0, -sy), "down": (0, sy)}[event.key]
            set_view((x0 + dx, x1 + dx), (y0 + dy, y1 + dy))
            redraw()

    # ----- widgets ------------------------------------------------------

    play = button(.75, .27, .10, "Pause", toggle)
    button(.86, .27, .10, "Step", single)
    button(.75, .21, .10, "Reset", reset)
    button(.86, .21, .10, "Random", randomize)
    effect_btn = button(.75, .15, .10, f"Effect: {EFFECTS[0]}", cycle_effect)
    button(.86, .15, .10, "Theme", cycle_palette)

    birth_ax = fig.add_axes([.75, .075, .095, .04], facecolor=axcolor)
    survive_ax = fig.add_axes([.865, .075, .095, .04], facecolor=axcolor)
    birth_box = TextBox(birth_ax, "Born", initial="3", color=axcolor, hovercolor="#263b55")
    survive_box = TextBox(survive_ax, "Survive", initial="2,3", color=axcolor, hovercolor="#263b55")
    for box in (birth_box, survive_box):
        box.label.set_color("#a6b5cd")
        box.text_disp.set_color("#e7efff")
    birth_box.on_submit(on_birth)
    survive_box.on_submit(on_survive)

    speed.on_changed(on_speed)

    fig.canvas.mpl_connect("scroll_event", on_scroll)
    fig.canvas.mpl_connect("button_press_event", on_press)
    fig.canvas.mpl_connect("motion_notify_event", on_motion)
    fig.canvas.mpl_connect("button_release_event", on_release)
    fig.canvas.mpl_connect("key_press_event", on_key)

    anim = FuncAnimation(fig, tick, interval=settings.interval, blit=False, cache_frame_data=False)
    redraw()
    plt.show()


if __name__ == "__main__":
    main()