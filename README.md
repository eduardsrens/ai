# AI game projects

A collection of Python-powered interactive games and simulations inside [`game-of-life/`](game-of-life/):

- [**GOL (`game-of-life/GOL/`)**](game-of-life/GOL/gol_ansons.py) — Expandable Conway's Game of Life visualizer (`numpy`, `matplotlib`, `seaborn`).
- [**Ance (`game-of-life/ance/`)**](game-of-life/ance/) — Pygame + Tkinter Game of Life with central symmetry, color blending, and saved drawings.
- [**Zane (`game-of-life/zane/`)**](game-of-life/zane/) — Tkinter Solo & LAN Multiplayer Game of Life with `Play Game.bat` launcher.
- [**Pocket Party (`game-of-life/pocket-party/`)**](game-of-life/pocket-party/) — Lightweight 3D pass-and-play party board game for 2–4 local players, powered by Python (stdlib) + Three.js WebGL2.
- [`hello.py`](hello.py) — Starter Python script.

## Play Pocket Party

Requires Python 3.10+ and a current browser with WebGL2. No pip or npm installation is needed.

```sh
cd game-of-life/pocket-party
python server.py --open
```

Use `python3` on macOS/Linux if that is your Python 3 command. On Windows, double-click [`Play Game.bat`](game-of-life/pocket-party/Play%20Game.bat). The launcher opens the browser; keep its console running while playing.

Pocket Party uses its own game rules and save file. The existing Conway simulations and their launchers continue to run independently.
