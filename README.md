# AI game projects

- Existing Conway's Game of Life implementations are in [`game-of-life/`](game-of-life/).
- [**Pocket Party**](game-of-life/pocket-party/) is a separate 3D party board game for 2–4 local players, with Python rules, a Three.js browser view, and third-person action animations.
- [**Maze solver**](maze/Klavs_maze.py) visualizes two-way search, compares BFS/DFS, and generates random mazes.

## Run the maze solver

```sh
cd maze
python Klavs_maze.py
```

No additional packages are needed. Maze maps are `.txt` files: `#` is a wall,
spaces or `.` are passages, `A`/`S` marks the start, and `B`/`E` marks the exit.
The included [`maze_Klavs_101x151.txt`](maze/maze_Klavs_101x151.txt) is a
large generated example. Use the GUI to select maps, animate the search, or
create and save a new maze.

## Play Pocket Party

Requires Python 3.10+ and a current browser with WebGL2. No pip or npm installation is needed.

```sh
cd game-of-life/pocket-party
python server.py --open
```

Use `python3` on macOS/Linux if that is your Python 3 command. On Windows, double-click [`Play Game.bat`](game-of-life/pocket-party/Play%20Game.bat). The launcher opens the browser; keep its console running while playing.

Pocket Party uses its own game rules and save file. The existing Conway simulations and their launchers continue to run independently.
