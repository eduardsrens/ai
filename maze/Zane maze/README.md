# Maze solver

Run [Zane_maze.py](./Zane_maze.py) as the named program entry point. The solver
automatically looks for valid `.txt` mazes in this folder and its subfolders.
It supports `#`/`X` walls, spaces/`.` open cells, `A`/`S` starts, and
`B`/`E`/`G` exits. Shorter rows are padded with walls.

The app opens a window where you can choose a found maze or browse for a new
`.txt` file. The solution opens in a separate animated window. It uses
Matplotlib and Seaborn.

In PowerShell, create an environment if needed and install the dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run the named program without a console window:

```powershell
.\.venv\Scripts\pythonw.exe Zane_maze.py
```

You can also double-click `start_maze_solver.pyw`; when `.venv` exists, it
restarts itself with that environment so the visualization packages are found.

The supplied `zanes_labirints.txt` is an example of a new, custom map. Put
classmates' valid `.txt` maps in this folder or a subfolder; they are picked up
automatically. Use **Salīdzināt soļus un laikus** in the app to compare the
shortest-path step count and BFS search time for every discovered map.
The animated traveler walks the shortest path sadly and turns happy at the exit.
