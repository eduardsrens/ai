# AI game projects

- Existing Conway's Game of Life implementations are in [`game-of-life/`](game-of-life/).
- [**Pocket Party**](game-of-life/pocket-party/) is a separate 3D party board game for 2–4 local players, with Python rules, a Three.js browser view, and third-person action animations.

## Play Pocket Party

Requires Python 3.10+ and a current browser with WebGL2. No pip or npm installation is needed.

```sh
cd game-of-life/pocket-party
python server.py --open
```

Use `python3` on macOS/Linux if that is your Python 3 command. On Windows, double-click [`Play Game.bat`](game-of-life/pocket-party/Play%20Game.bat). The launcher opens the browser; keep its console running while playing.

Pocket Party uses its own game rules and save file. The existing Conway simulations and their launchers continue to run independently.
