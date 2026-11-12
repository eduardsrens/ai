# Pocket Party

A lightweight, high-detail local pass-and-play 3D party board game for **2–4 friends**, inspired by classic party board games. Explore a sunlit island diorama with an animated ocean, waterfall, lighthouse, swirling portal, 3D tumbling dice, expressive characters, tactical items, and four interactive skill minigames.

Python runs all rules, turns, item effects, rolls, scores, rewards, and SQLite saves using only the standard library. Three.js WebGL2 + custom GLSL shaders render the browser world. Web Audio synthesizes tactile sound effects with zero external media files.

## Run

Requires Python 3.10+ and a browser with WebGL2. No `pip` or `npm` installation required.

```sh
python server.py --port 3000 --open
```

Run from this directory or pass the path to `server.py` from anywhere. On Windows, double-click **Play Game.bat** (use `python3` on macOS/Linux if needed). Keep the server console open while playing, and open `http://127.0.0.1:3000` if your browser does not launch automatically.

Options:
- `--port 3001` — choose another port if 3000 is busy
- `--data-dir /path/to/saves` — store `saves.sqlite3` in a custom directory
- `--host 127.0.0.1` — bind address (defaults to localhost only)

![Board overview](docs/screenshots/board.png)

![Third-person action camera](docs/screenshots/third-person.png)

## Rules & Features

- **Configurable length:** Choose **5, 8, or 12 rounds** on setup. Each round gives every player one turn, followed by a private skill minigame.
- **Trophies win:** Most trophies (`★`) wins; keys (`◆`) break ties. Exact ties share the crown, plus post-game superlative awards.
- **Items before rolling:**
  - **Pocket Rocket:** Deal 7 damage to a rival (or pop their shield).
  - **Key Magnet:** Steal up to 8 keys from a rival.
  - **Bubble Shield:** Iridescent shield blocking one rival attack or board trap.
  - **Switcheroo:** Swap board positions with a rival.
  - **Turbo Dice:** Roll two dice (`2d6`, 2–12 spaces) on your turn.
- **Trophy Shrines:** Passing or landing on spaces 7, 21, or 35 offers a trophy for **20 keys**.
- **Portal Wrap:** Reaching the end of the 49-space trail warps through the glowing Portal Gate back to Space 00.
- **Knockouts:** At 0 HP, drop up to 8 keys and respawn at Space 00 with 20 HP. Trophies stay safe.

## Minigames

1. **Sweet Spot:** Stop the oscillating spark as close to the golden center as possible (`Click` or `Space`).
2. **Gem Scramble:** Memorize the gold crystals on the tray in 3 seconds, then pick the exact count.
3. **Pocket Rush:** Tap or press `Space` as fast as possible for 5 seconds (key-repeat is ignored).
4. **Star Snatch:** Tap popping golden stars (`+10`) across a 3×3 meadow grid while avoiding coral bombs (`−10`) in 6 seconds (`Click`, `Tap`, or keys `1–9`).

## 3D World & Controls

- **Orbit & Zoom:** Drag to orbit with smooth inertia, scroll to zoom, or switch camera presets (**Diorama**, **Scenic**, **Map**).
- **Tile Inspector:** Hover any tile on the island to inspect its space number and effect.
- **Third-Person Action Cam:** Follows hops, 3D dice tumbles, portal warps, chest openings, and item attacks. Toggle **Action Cam** in the header for fast turns, or press **Esc** / **Back to board** anytime. Reduced-motion settings are honored automatically.

## Verification

```sh
python -m unittest discover -s tests -v
```

Also runs cleanly from the repository root:

```sh
python -m unittest discover -s game-of-life/pocket-party/tests -v
```
