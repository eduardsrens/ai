CONWAY'S GAME OF LIFE
=====================

RUNNING ON WINDOWS
------------------
1. Extract the entire ZIP archive into a single folder.
2. Install Python 3 from https://www.python.org/downloads/windows/
   During installation, enable "Add python.exe to PATH".
   Use the official Windows installer that includes Tkinter.
3. Double-click "Play Game.bat" or run `py -3 game_of_life.py`.
4. On the start screen, choose Singleplayer or Multiplayer.

The game code, including multiplayer and robot modes, is all in one file:
`game_of_life.py`.

SINGLEPLAYER
------------
Click and drag to draw. Press E to toggle the eraser, or hold Shift to erase
briefly. Use the pencil, eraser, and on-screen color wheel. The scrollbars
move the infinite board; the mouse wheel changes the zoom level.

MULTIPLAYER
-----------
This version runs on the local network (same Wi-Fi/LAN), not the internet.
All players must be on the same network and each computer must run its own copy
of the game.

1. The host chooses Solo, Duo, or Test server from the game-mode menu. Solo is
   a 1v1 match and Duo is a 2v2 match. Test server starts a local 1v1 game
   against robot players.
2. Click "Options" to set the starting cell limit (1-100), drawing time
   (5-20 seconds), match length (1-30 minutes), and cells allowed per turn
   (1-20). Click "Host game" to start.
3. The host sends the displayed Host address and Room code to the other players.
4. Each player chooses one of 10 colors. A color cannot repeat within a match.
   Everyone enters their name, host address, and room code, then clicks "Join game".
5. Use the Rules button on the main menu to review the game rules. Once everyone
   joins, each player can draw in their own territory up to the host-selected
   cell limit, and then the host clicks "Start game".
6. Each round, all players draw simultaneously for the host-selected time. Each can
   place up to the host-selected cells-per-turn limit by clicking or dragging,
   either individually or in groups.
   With the eraser (E or hold Shift), you can remove unsubmitted cells; during setup,
   it deletes cells in your own territory. Press "Submit turn" or Space to submit the
   turn. When all players have submitted or the timer ends, the drawings are played.
   You can defend your own territory and attack the opponent's territory (shown in red).
   In Duo mode, teammates cannot attack each other. During the game, you can press the
   happy, sad, or angry reaction buttons; all players see the reactions.
7. After each turn, the game advances 10 generations of Conway's Game of Life. A
   player is eliminated if their starting territory contains no live cells. The last
   surviving player or team wins; the result screen shows a randomized message and one
   random Game of Life fact. If the last cells disappear simultaneously, the player with
   more cells before the last generation wins.
8. If the host-selected match length ends, the player or team with the highest number
   of live cells in their territory wins. In Duo mode, teammate territory cells are
   counted together. If the number is tied, compare the cell count before the last
   generation; if that is also tied, the host wins. There is no draw.
9. If a player disconnects or leaves to the menu, they can rejoin with the same name,
   color, and room code. An inactive connection is marked as disconnected after 10 seconds.

If Windows Firewall asks, allow Python access to Private networks. Only do this on a
trusted network and share the room code only with players you invited.

`game_of_life.py` can be copied to another Windows computer. The other computer must
have Python 3 with Tkinter installed.
