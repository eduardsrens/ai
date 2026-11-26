# Blackjack Expert Bot

A self-contained Python/Tkinter blackjack game. The bot plays one hand against a
dealer using six decks, dealer-stands-on-soft-17 rules, 3:2 blackjack payout,
basic strategy, and Hi-Lo card counting of cards that have been exposed.

Rules in play: double on any two cards (including after a split), split up to
four hands, split aces receive one card each and cannot be re-split, insurance
pays 2:1, no surrender, and the shoe is reshuffled at 75% penetration. Bets are
whole multiples of the $10 base bet. Tkinter ships with the standard Python
installers for Windows and macOS; on Debian/Ubuntu install it with
`sudo apt install python3-tk`.

## Run

From the repository root:

```powershell
python blackjack\valters\blackjack_bot.py
```

`final bot.py` is the standalone tournament strategy module. It has no import
dependency on the GUI/game script, uses the current JSON settings embedded in
the file, and assumes four decks. A tournament adapter can import and call
`choose_action(state)` and `choose_bet(state)`. The state contract and example
fields are documented in the module docstring. This is a strategy module, not
the GUI game, and the historical statistics are included for reference only.

Set the **Starting amount**, then use **Start** to have the bot play
continuously, or **Stop** to pause it. The amount must be a whole number of at
least $10. There are no manual deal or move controls. The GUI runs at balanced
risk level 2. Stopping mid-hand and starting again resumes that hand without
resetting the bankroll.

The GUI shows the next count-based bet before a hand and the active/last hand
stakes at the table. Use the five **Bot speed** buttons to set the delay between
deal/action steps: speed 1 is 1 second, and speed 5 is 0.25 seconds.
The bot takes insurance only when the count meets its threshold. Play stops
automatically if the bankroll cannot cover the minimum bet.

When the app opens, it automatically runs strategy simulations in a background
thread. It compares a bounded set of count-based bet spreads and deviations
from basic strategy, including a possible high-count split of tens against a
dealer 5 or 6, then validates the best candidate on separate random shoes. It
only saves a candidate when held-out results show a positive 95% lower
confidence bound; otherwise it keeps the current profile. It does not rewrite
source code or learn a complete strategy from scratch: basic strategy remains
the baseline, and the simulator tests only those predefined variations.
Simulation results are estimates, not a guarantee of better results at a real
table.

The selected profile is saved in `blackjack_strategy.json`; played-game
statistics are saved in `blackjack_training.json`. If the statistics file is
unreadable it is renamed to `blackjack_training.json.corrupt` and a fresh
record is started.

The simulation is for learning and entertainment. Card counting does not
guarantee winnings; real casinos may use different rules or restrict play.

## Tests

The tests exercise the game logic only, so they run without a display or Tkinter.

```powershell
python -m unittest discover -s blackjack\valters -p "test_*.py" -v
```
