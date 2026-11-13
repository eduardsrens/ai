import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap, ListedColormap, to_rgb, to_rgba
from matplotlib.patches import Arc, Circle, Ellipse, Polygon
from matplotlib.lines import Line2D
from matplotlib.transforms import Affine2D
from matplotlib.widgets import Button


ROWS = 50
COLS = 70
INITIAL_DENSITY = 0.22
INTERVAL_MS = 100
MAX_CELL_AGE = 20
EXPANSION_CELLS = 10
MONSTER_SPEED = 8
CONFETTI_LIFETIME = 20
CONFETTI_COLORS = ["#f4a6a6", "#f6cf8e", "#a9dfc2", "#9ed8e8", "#c2b6ed", "#e4a8d1"]
PALETTES = [
	("Pastel", ["#f3a6a6", "#f6d5a5", "#f2e7a2", "#a9dfc2", "#9ed8e8", "#b8afe5", "#e4a8d1"]),
	("Sorbet", ["#ffadad", "#ffd6a5", "#fdffb6", "#caffbf", "#9bf6ff", "#a0c4ff", "#ffc6ff"]),
	("Ocean", ["#b8e0e8", "#a8d5e2", "#a6c8e8", "#b5c4ed", "#c8c0eb", "#d8c6e8"]),
	("Garden", ["#f2b5c8", "#f6c99d", "#f0e2a2", "#b2dfb6", "#8fd6bd", "#a7d7e8"]),
	("Dream", ["#ffc8dd", "#e7c6ff", "#c8b6ff", "#b8c0ff", "#bde0fe", "#a2d2ff"]),
]
EMPTY_COLOR = "#17262d"
FIGURE_COLOR = "#10191f"
GRID_COLOR = "#263940"
ACCENT_COLOR = "#e8c99a"


def make_board(shape=(ROWS, COLS)):
	alive = np.random.random(shape) < INITIAL_DENSITY
	board = np.zeros(shape, dtype=np.uint8)
	board[alive] = 1
	return board


def next_generation(board):
	rows, cols = board.shape
	alive = board > 0
	padded = np.pad(alive, 1, mode="constant")
	neighbors = sum(
		padded[row:row + rows, col:col + cols]
		for row in range(3)
		for col in range(3)
		if (row, col) != (1, 1)
	)
	survives = alive & ((neighbors == 2) | (neighbors == 3))
	born = ~alive & (neighbors == 3)
	next_board = np.zeros_like(board)
	next_board[survives] = np.minimum(board[survives] + 1, MAX_CELL_AGE)
	next_board[born] = 1
	return next_board, born


def expand_at_walls(board):
	top = np.any(board[0, :])
	bottom = np.any(board[-1, :])
	left = np.any(board[:, 0])
	right = np.any(board[:, -1])
	if not (top or bottom or left or right):
		return board, False
	padding = (
		(EXPANSION_CELLS if top else 0, EXPANSION_CELLS if bottom else 0),
		(EXPANSION_CELLS if left else 0, EXPANSION_CELLS if right else 0),
	)
	return np.pad(board, padding), True


board = make_board()
running = True
drawing = None
last_drawn_cell = None
current_palette = 0
custom_color = None
monster_active = False
monster_column = 0
monster_resume = False
monster_artists = []
confetti_x = np.empty(0)
confetti_y = np.empty(0)
confetti_vx = np.empty(0)
confetti_vy = np.empty(0)
confetti_life = np.empty(0)
confetti_rgba = np.empty((0, 4))
celebration_frames = 0
celebration_phase = 0.0
celebration_x = COLS / 2
celebration_y = ROWS / 2

fig, ax = plt.subplots(figsize=(11, 7))
fig.patch.set_facecolor(FIGURE_COLOR)
fig.canvas.manager.set_window_title("Conway's Game of Life")


def make_age_colormap():
	if custom_color is None:
		palette_name, palette_colors = PALETTES[current_palette]
	else:
		palette_name = "Custom"
		base = np.array(to_rgb(custom_color))
		palette_colors = [
			base * 0.55,
			base * 0.8,
			base,
			base + (1 - base) * 0.35,
			base + (1 - base) * 0.7,
		]
	age_map = LinearSegmentedColormap.from_list(f"age_{palette_name.lower()}", palette_colors)
	age_colors = age_map(np.linspace(0, 1, MAX_CELL_AGE))
	return ListedColormap([EMPTY_COLOR, *age_colors])


colors = make_age_colormap()
age_bounds = np.arange(-0.5, MAX_CELL_AGE + 1.5)
age_norm = BoundaryNorm(age_bounds, colors.N)
image = ax.imshow(board, cmap=colors, norm=age_norm, interpolation="nearest")
colorbar = fig.colorbar(image, ax=ax, ticks=[0, 1, 5, 10, 15, MAX_CELL_AGE], pad=0.02)
colorbar.ax.set_yticklabels(["Empty", "1", "5", "10", "15", f"{MAX_CELL_AGE}+"])
colorbar.set_label("CELL AGE / GENERATIONS", color=ACCENT_COLOR, fontsize=8, labelpad=10)
colorbar.ax.tick_params(colors="#d3dadd", labelsize=8, length=0, pad=5)
colorbar.outline.set_edgecolor("#344850")
ax.set_facecolor(EMPTY_COLOR)
fig.suptitle("CONWAY'S GAME OF LIFE", y=0.965, color="#f0eee7", fontsize=14, fontweight="bold")
ax.set_title("SPACE  pause     R  randomize     C  clear", color="#99a9ad", fontsize=8, pad=12)
ax.set_xticks([])
ax.set_yticks([])
ax.set_xticks(np.arange(-0.5, COLS, 1), minor=True)
ax.set_yticks(np.arange(-0.5, ROWS, 1), minor=True)
ax.grid(which="minor", color=GRID_COLOR, linewidth=0.25)
ax.tick_params(which="minor", bottom=False, left=False)


def add_monster_patch(patch):
	patch.set_transform(Affine2D() + ax.transData)
	patch.set_zorder(5)
	patch.set_visible(False)
	ax.add_patch(patch)
	monster_artists.append(patch)


add_monster_patch(Ellipse((0, 0), 7.2, 6.7, facecolor="#75b99a", edgecolor="#244a43", linewidth=1.5))
add_monster_patch(Polygon([(-2.2, 2.45), (-2.8, 4.2), (-0.9, 3.35)], closed=True, facecolor="#e3ae79", edgecolor="#604d48", linewidth=1.1))
add_monster_patch(Polygon([(2.2, 2.45), (2.8, 4.2), (0.9, 3.35)], closed=True, facecolor="#e3ae79", edgecolor="#604d48", linewidth=1.1))
add_monster_patch(Ellipse((0, 0.7), 3.5, 3.6, facecolor="#fff3d8", edgecolor="#31554e", linewidth=1.0))
add_monster_patch(Ellipse((0.45, 0.65), 1.65, 1.95, facecolor="#80c7db", edgecolor="#345b64", linewidth=0.8))
add_monster_patch(Ellipse((0.62, 0.65), 0.78, 1.25, facecolor="#182832", edgecolor="none"))
add_monster_patch(Circle((0.34, 1.25), 0.24, facecolor="#ffffff", edgecolor="none"))
add_monster_patch(Ellipse((0, -1.65), 2.65, 1.0, facecolor="#513c48", edgecolor="#31554e", linewidth=0.8))
add_monster_patch(Polygon([(-0.88, -1.24), (-0.38, -1.24), (-0.62, -1.7)], closed=True, facecolor="#fff3d8", edgecolor="none"))
add_monster_patch(Polygon([(0.38, -1.24), (0.88, -1.24), (0.62, -1.7)], closed=True, facecolor="#fff3d8", edgecolor="none"))
add_monster_patch(Polygon([(-0.18, -2.05), (0.18, -2.05), (0, -1.72)], closed=True, facecolor="#fff3d8", edgecolor="none"))
add_monster_patch(Ellipse((-3.25, -0.5), 1.5, 2.3, angle=22, facecolor="#75b99a", edgecolor="#244a43", linewidth=1.2))
add_monster_patch(Ellipse((3.25, -0.5), 1.5, 2.3, angle=-22, facecolor="#75b99a", edgecolor="#244a43", linewidth=1.2))
add_monster_patch(Ellipse((-1.7, -3.2), 2.0, 0.85, angle=-12, facecolor="#75b99a", edgecolor="#244a43", linewidth=1.2))
add_monster_patch(Ellipse((1.7, -3.2), 2.0, 0.85, angle=12, facecolor="#75b99a", edgecolor="#244a43", linewidth=1.2))

confetti_artist = ax.scatter([], [], s=[], marker="s", edgecolors="none", zorder=7)
celebration_artists = []


def add_celebration_artist(artist):
	artist.set_transform(Affine2D() + ax.transData)
	artist.set_zorder(8)
	artist.set_visible(False)
	if isinstance(artist, Line2D):
		ax.add_line(artist)
	else:
		ax.add_patch(artist)
	celebration_artists.append(artist)


add_celebration_artist(Ellipse((0, 2.35), 2.0, 2.3, facecolor="#bd8c78", edgecolor="#3b3439", linewidth=1.0))
add_celebration_artist(Polygon([(-1.0, 2.8), (1.0, 2.8), (1.35, 4.5), (-1.35, 4.5)], closed=True, facecolor="#a8c6b5", edgecolor="#43534d", linewidth=1.0))
add_celebration_artist(Line2D([-0.45, -0.62], [4.35, 5.45], color="#bd8c78", linewidth=3.0, solid_capstyle="round"))
add_celebration_artist(Line2D([0.45, 0.62], [4.35, 5.45], color="#bd8c78", linewidth=3.0, solid_capstyle="round"))
add_celebration_artist(Line2D([-0.85, -1.45, -1.65], [2.15, 1.15, 0.35], color="#bd8c78", linewidth=3.0, solid_capstyle="round"))
add_celebration_artist(Line2D([0.85, 1.45, 1.65], [2.15, 1.15, 0.35], color="#bd8c78", linewidth=3.0, solid_capstyle="round"))
add_celebration_artist(Ellipse((0, 0.55), 1.9, 2.1, facecolor="#e8b99a", edgecolor="#5a4943", linewidth=1.0))
add_celebration_artist(Ellipse((0, -0.3), 2.0, 0.95, facecolor="#d8d6ca", edgecolor="#777872", linewidth=0.8))
add_celebration_artist(Circle((-0.92, -0.28), 0.36, facecolor="#d8d6ca", edgecolor="#777872", linewidth=0.8))
add_celebration_artist(Circle((-0.94, 0.65), 0.12, facecolor="#fff4df", edgecolor="#655550", linewidth=1.0))
add_celebration_artist(Circle((0.94, 0.65), 0.12, facecolor="#fff4df", edgecolor="#655550", linewidth=1.0))
add_celebration_artist(Circle((-0.94, 0.65), 0.045, facecolor="#343036", edgecolor="none"))
add_celebration_artist(Circle((0.94, 0.65), 0.045, facecolor="#343036", edgecolor="none"))
add_celebration_artist(Arc((0, 0.1), 0.75, 0.55, theta1=200, theta2=340, color="#8d514d", linewidth=1.2))
add_celebration_artist(Circle((0, 1.5), 0.11, facecolor="#bd8c78", edgecolor="none"))

plt.tight_layout(rect=(0, 0.23, 1, 0.93))


def update(_frame):
	global board, celebration_frames, celebration_phase
	if running:
		board, expanded = expand_at_walls(board)
		board, born = next_generation(board)
		if np.any(born):
			emit_confetti(born)
			celebration_frames = 24
		update_board_view(expanded)
	if monster_active:
		advance_monster()
	update_confetti()
	update_celebration()
	return (image, confetti_artist, *monster_artists, *celebration_artists)


def emit_confetti(born):
	global confetti_x, confetti_y, confetti_vx, confetti_vy, confetti_life, confetti_rgba
	global celebration_x, celebration_y
	rows, cols = np.nonzero(born)
	if rows.size == 0:
		return
	if rows.size > 12:
		selected = np.random.choice(rows.size, 12, replace=False)
		rows, cols = rows[selected], cols[selected]
	celebration_x = float(np.mean(cols))
	celebration_y = max(0.0, float(np.mean(rows)) - 6.0)
	count = rows.size * 3
	confetti_x = np.concatenate((confetti_x, np.repeat(cols.astype(float), 3) + np.random.uniform(-0.4, 0.4, count)))
	confetti_y = np.concatenate((confetti_y, np.repeat(rows.astype(float), 3) + np.random.uniform(-0.4, 0.4, count)))
	confetti_vx = np.concatenate((confetti_vx, np.random.uniform(-0.35, 0.35, count)))
	confetti_vy = np.concatenate((confetti_vy, np.random.uniform(-0.8, -0.15, count)))
	confetti_life = np.concatenate((confetti_life, np.full(count, CONFETTI_LIFETIME, dtype=float)))
	palette_indices = np.random.randint(0, len(CONFETTI_COLORS), count)
	new_rgba = np.array([to_rgba(CONFETTI_COLORS[index]) for index in palette_indices])
	confetti_rgba = np.concatenate((confetti_rgba, new_rgba))
	if confetti_life.size > 500:
		confetti_x = confetti_x[-500:]
		confetti_y = confetti_y[-500:]
		confetti_vx = confetti_vx[-500:]
		confetti_vy = confetti_vy[-500:]
		confetti_life = confetti_life[-500:]
		confetti_rgba = confetti_rgba[-500:]


def update_confetti():
	global confetti_x, confetti_y, confetti_vx, confetti_vy, confetti_life, confetti_rgba
	if confetti_life.size:
		confetti_x += confetti_vx
		confetti_y += confetti_vy
		confetti_vy += 0.06
		confetti_life -= 1
		active = confetti_life > 0
		confetti_x = confetti_x[active]
		confetti_y = confetti_y[active]
		confetti_vx = confetti_vx[active]
		confetti_vy = confetti_vy[active]
		confetti_life = confetti_life[active]
		confetti_rgba = confetti_rgba[active]
	if confetti_life.size:
		colors = confetti_rgba.copy()
		colors[:, 3] *= confetti_life / CONFETTI_LIFETIME
		confetti_artist.set_offsets(np.column_stack((confetti_x, confetti_y)))
		confetti_artist.set_sizes(16 + 10 * np.sin(confetti_life * 0.7) ** 2)
		confetti_artist.set_facecolors(colors)
	else:
		confetti_artist.set_offsets(np.empty((0, 2)))


def update_celebration():
	global celebration_frames, celebration_phase
	if celebration_frames > 0:
		bounce = abs(np.sin(celebration_phase)) * 1.3
		transform = Affine2D().translate(celebration_x, celebration_y - bounce) + ax.transData
		for artist in celebration_artists:
			artist.set_transform(transform)
			artist.set_visible(True)
		celebration_frames -= 1
		celebration_phase += 0.75
	else:
		for artist in celebration_artists:
			artist.set_visible(False)


def update_board_view(resize=False):
	image.set_data(board)
	if resize:
		rows, cols = board.shape
		image.set_extent((-0.5, cols - 0.5, rows - 0.5, -0.5))
		ax.set_xticks(np.arange(-0.5, cols, 1), minor=True)
		ax.set_yticks(np.arange(-0.5, rows, 1), minor=True)
		ax.set_xlim(-0.5, cols - 0.5)
		ax.set_ylim(rows - 0.5, -0.5)


def refresh_palette():
	image.set_cmap(make_age_colormap())
	colorbar.update_normal(image)
	colorbar.set_ticks([0, 1, 5, 10, 15, MAX_CELL_AGE])
	colorbar.ax.set_yticklabels(["Empty", "1", "5", "10", "15", f"{MAX_CELL_AGE}+"])
	name = "Custom" if custom_color else PALETTES[current_palette][0]
	palette_button.label.set_text(f"Palette: {name}")
	fig.canvas.draw_idle()


def cycle_palette(_event=None):
	global current_palette, custom_color
	current_palette = (current_palette + 1) % len(PALETTES)
	custom_color = None
	refresh_palette()


def choose_custom_color(_event=None):
	global custom_color
	try:
		import tkinter as tk
		from tkinter import colorchooser

		root = tk.Tk()
		root.withdraw()
		try:
			_, selected_color = colorchooser.askcolor(title="Choose cell color", parent=root)
		finally:
			root.destroy()
	except Exception as error:
		print(f"Could not open the color picker: {error}")
		return
	if selected_color:
		custom_color = selected_color
		refresh_palette()


def on_key_press(event):
	global board, running
	if event.key == " ":
		toggle_pause()
	elif event.key and event.key.lower() == "r":
		board = make_board(board.shape)
		update_board_view()
	elif event.key and event.key.lower() == "c":
		clear_all()
	fig.canvas.draw_idle()


def toggle_pause(_event=None):
	global running
	if monster_active:
		return
	running = not running
	pause_button.label.set_text("Pause" if running else "Resume")
	fig.canvas.draw_idle()


def play_simulation(_event=None):
	global running
	if monster_active:
		return
	running = True
	pause_button.label.set_text("Pause")
	fig.canvas.draw_idle()


def clear_all(_event=None):
	global board, monster_active, running
	board = np.zeros_like(board)
	if monster_active:
		monster_active = False
		for artist in monster_artists:
			artist.set_visible(False)
		running = monster_resume
		pause_button.set_active(True)
		pause_button.label.set_text("Pause" if running else "Resume")
	update_board_view()
	fig.canvas.draw_idle()


def paint_at(event):
	global board, last_drawn_cell
	if drawing is None or event.inaxes is not ax or event.xdata is None or event.ydata is None:
		return
	col = int(event.xdata + 0.5)
	row = int(event.ydata + 0.5)
	rows, cols = board.shape
	if 0 <= row < rows and 0 <= col < cols and (row, col) != last_drawn_cell:
		last_drawn_cell = (row, col)
		board[row, col] = 1 if drawing else 0
		image.set_data(board)


def stamp_pattern(pattern_rows):
	global board
	pattern_width = max(map(len, pattern_rows))
	pattern = np.array([
		[character == "#" for character in line.ljust(pattern_width)]
		for line in pattern_rows
	], dtype=bool)
	rows, cols = board.shape
	top = (rows - pattern.shape[0]) // 2
	left = (cols - pattern.shape[1]) // 2
	region = board[top:top + pattern.shape[0], left:left + pattern.shape[1]]
	region[pattern] = 1
	image.set_data(board)
	fig.canvas.draw_idle()


def add_spaceship(_event=None):
	stamp_pattern([".##.#", "#....", "#...#", "####."])


def add_frog(_event=None):
	stamp_pattern([".###", "###."])


def start_monster(_event=None):
	global monster_active, monster_column, monster_resume, running
	if not monster_active:
		monster_resume = running
	monster_active = True
	monster_column = 0
	running = False
	pause_button.label.set_text("Eating...")
	pause_button.set_active(False)
	for artist in monster_artists:
		artist.set_visible(True)


def advance_monster():
	global board, monster_active, monster_column, running
	rows, cols = board.shape
	start = monster_column
	end = min(start + MONSTER_SPEED, cols)
	board[:, start:end] = 0
	center_x = (start + end - 1) / 2
	center_y = (rows - 1) / 2
	for artist in monster_artists:
		artist.set_transform(Affine2D().translate(center_x, center_y) + ax.transData)
	image.set_data(board)
	monster_column = end
	if end >= cols:
		monster_active = False
		for artist in monster_artists:
			artist.set_visible(False)
		running = monster_resume
		pause_button.set_active(True)
		pause_button.label.set_text("Pause" if running else "Resume")


def import_picture(_event=None, start_playing=False):
	global board
	try:
		import tkinter as tk
		from tkinter import filedialog

		root = tk.Tk()
		root.withdraw()
		try:
			filename = filedialog.askopenfilename(
				parent=root,
				title="Import a picture as Life cells",
				filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"), ("All files", "*.*")],
			)
		finally:
			root.destroy()
	except Exception as error:
		print(f"Could not open the image picker: {error}")
		return
	if not filename:
		return

	try:
		pixels = np.asarray(plt.imread(filename), dtype=float)
		if np.nanmax(pixels) > 1:
			pixels /= 255
		if pixels.ndim == 2:
			luminance = pixels
			alpha = np.ones_like(luminance)
		else:
			channels = pixels.shape[2]
			if channels >= 3:
				rgb = pixels[..., :3]
			else:
				rgb = np.repeat(pixels[..., :1], 3, axis=2)
			luminance = rgb @ np.array([0.2126, 0.7152, 0.0722])
			if channels == 4:
				alpha = pixels[..., 3]
			elif channels == 2:
				alpha = pixels[..., 1]
			else:
				alpha = np.ones_like(luminance)
	except Exception as error:
		print(f"Could not read the selected picture: {error}")
		return

	mask = (luminance < 0.5) & (alpha > 0.1)
	if not np.any(mask):
		print("No dark, visible pixels were found in that picture.")
		return
	rows, cols = board.shape
	image_rows, image_cols = mask.shape
	scale = min((rows - 2) / image_rows, (cols - 2) / image_cols, 1)
	new_rows = max(1, round(image_rows * scale))
	new_cols = max(1, round(image_cols * scale))
	row_indices = np.linspace(0, image_rows - 1, new_rows).astype(int)
	col_indices = np.linspace(0, image_cols - 1, new_cols).astype(int)
	mask = mask[np.ix_(row_indices, col_indices)]
	board = np.zeros_like(board)
	top = (rows - new_rows) // 2
	left = (cols - new_cols) // 2
	board[top:top + new_rows, left:left + new_cols] = mask.astype(np.uint8)
	image.set_data(board)
	if start_playing:
		play_simulation()
	fig.canvas.draw_idle()


def import_and_play(_event=None):
	import_picture(start_playing=True)


def on_mouse_press(event):
	global drawing, last_drawn_cell
	if event.inaxes is not ax:
		return
	if event.button == 1:
		drawing = True
	elif event.button == 3:
		drawing = False
	else:
		return
	last_drawn_cell = None
	paint_at(event)


def on_mouse_release(_event):
	global drawing, last_drawn_cell
	drawing = None
	last_drawn_cell = None


button_axes = [
	fig.add_axes([0.035 + col * 0.19, 0.15 - row * 0.075, 0.17, 0.052])
	for row in range(2)
	for col in range(5)
]
play_button = Button(button_axes[0], "Play", color="#294c42", hovercolor="#3b6858")
pause_button = Button(button_axes[1], "Pause", color="#29363c", hovercolor="#3a4b52")
palette_button = Button(button_axes[2], "Palette: Pastel", color="#29363c", hovercolor="#3a4b52")
color_button = Button(button_axes[3], "Cell Color", color="#29363c", hovercolor="#3a4b52")
import_button = Button(button_axes[4], "Import Image", color="#29363c", hovercolor="#3a4b52")
spaceship_button = Button(button_axes[5], "Spaceship", color="#29363c", hovercolor="#3a4b52")
frog_button = Button(button_axes[6], "Frog", color="#29363c", hovercolor="#3a4b52")
clear_button = Button(button_axes[7], "Clear All", color="#29363c", hovercolor="#3a4b52")
monster_button = Button(button_axes[8], "Monster", color="#4c3938", hovercolor="#70504a")
play_image_button = Button(button_axes[9], "Play Image", color="#294c42", hovercolor="#3b6858")
for button in (
	play_button,
	pause_button,
	palette_button,
	color_button,
	import_button,
	spaceship_button,
	frog_button,
	clear_button,
	monster_button,
	play_image_button,
):
	button.label.set_color("#e8e4d9")
	button.label.set_fontsize(7.5)


play_button.on_clicked(play_simulation)
pause_button.on_clicked(toggle_pause)
palette_button.on_clicked(cycle_palette)
color_button.on_clicked(choose_custom_color)
spaceship_button.on_clicked(add_spaceship)
frog_button.on_clicked(add_frog)
import_button.on_clicked(import_picture)
play_image_button.on_clicked(import_and_play)
clear_button.on_clicked(clear_all)
monster_button.on_clicked(start_monster)
fig.canvas.mpl_connect("key_press_event", on_key_press)
fig.canvas.mpl_connect("button_press_event", on_mouse_press)
fig.canvas.mpl_connect("button_release_event", on_mouse_release)
fig.canvas.mpl_connect("motion_notify_event", paint_at)
animation = FuncAnimation(fig, update, interval=INTERVAL_MS, blit=True, cache_frame_data=False)

plt.show()
