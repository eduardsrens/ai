import json
import secrets
import socket
import socketserver
import threading


PORT = 50505
MAX_STROKE_CELLS = 300
ATTACK_COLOR = "#ff4545"
PLAYER_COLORS = ("#59e1a5", "#5aa9ff", "#ffd166", "#c792ea")


class GameRoom:
    def __init__(self, mode, generations_per_round, room_code):
        if mode not in ("1v1", "2v2"):
            raise ValueError("Game mode must be 1v1 or 2v2.")
        if not 1 <= generations_per_round <= 100:
            raise ValueError("Generations per round must be between 1 and 100.")
        self.mode = mode
        self.player_count = 2 if mode == "1v1" else 4
        self.width = 64
        self.height = 40 if mode == "1v1" else 64
        self.generations_per_round = generations_per_round
        self.room_code = room_code
        self.lock = threading.RLock()
        self.players = []
        self.tokens = {}
        self.cells = {}
        self.phase = "lobby"
        self.current_turn = None
        self.round_number = 0
        self.generation = 0
        self.winner = None
        self.message = "Waiting for players to join."

    def _territory(self, x, y):
        if self.mode == "1v1":
            return 0 if x < self.width // 2 else 1
        column = 0 if x < self.width // 2 else 1
        row = 0 if y < self.height // 2 else 1
        return row * 2 + column

    def _team(self, player_index):
        if self.mode == "1v1":
            return player_index
        return player_index % 2

    def join(self, name, room_code):
        with self.lock:
            if room_code != self.room_code:
                raise ValueError("That room code is incorrect.")
            if len(self.players) >= self.player_count:
                raise ValueError("This game is full.")
            if self.phase != "lobby":
                raise ValueError("This game has already started.")

            index = len(self.players)
            clean_name = " ".join(str(name).split())[:20] or f"Player {index + 1}"
            token = secrets.token_urlsafe(24)
            self.players.append(
                {
                    "index": index,
                    "name": clean_name,
                    "team": self._team(index),
                    "color": PLAYER_COLORS[index],
                    "alive": True,
                }
            )
            self.tokens[token] = index

            if len(self.players) == self.player_count:
                self.phase = "setup"
                self.message = "Draw your starting pattern in your own territory."
            else:
                self.message = (
                    f"Waiting for players ({len(self.players)}/{self.player_count})."
                )
            return {"token": token, "player_index": index, "state": self.state()}

    def _authenticated_player(self, token):
        player_index = self.tokens.get(token)
        if player_index is None:
            raise ValueError("The game connection is not authorized.")
        return player_index

    def start(self, token):
        with self.lock:
            player_index = self._authenticated_player(token)
            if player_index != 0:
                raise ValueError("Only the host can start the game.")
            if self.phase != "setup":
                raise ValueError("Wait until all players have joined.")
            self.phase = "action"
            self.round_number = 1
            order = self._turn_order()
            self.current_turn = order[0] if order else None
            self.message = self._turn_message()

    def leave(self, token):
        with self.lock:
            player_index = self._authenticated_player(token)
            player = self.players[player_index]
            if not player["alive"]:
                return
            player["alive"] = False
            if self.phase == "action" and self.current_turn == player_index:
                self._advance_turn(player_index)
            else:
                self.message = f"{player['name']} left the game."

    def submit_stroke(self, token, cells):
        with self.lock:
            player_index = self._authenticated_player(token)
            player = self.players[player_index]
            if not player["alive"]:
                raise ValueError("You have been eliminated.")
            if not isinstance(cells, list) or not cells or len(cells) > MAX_STROKE_CELLS:
                raise ValueError(
                    f"A stroke must contain between 1 and {MAX_STROKE_CELLS} cells."
                )

            checked_cells = []
            seen = set()
            for point in cells:
                if (
                    not isinstance(point, list)
                    or len(point) != 2
                    or type(point[0]) is not int
                    or type(point[1]) is not int
                ):
                    raise ValueError("The drawing contains an invalid cell.")
                x, y = point
                if not (0 <= x < self.width and 0 <= y < self.height):
                    raise ValueError("You can only draw inside the game board.")
                seen.add((x, y))
                checked_cells.append((x, y))

            if self.phase == "setup":
                target_area = player_index
                color = player["color"]
            elif self.phase == "action":
                if self.current_turn != player_index:
                    raise ValueError("Wait for your turn.")
                if not checked_cells:
                    raise ValueError("Draw a stroke before submitting.")
                target_area = self._territory(*checked_cells[0])
                if any(self._territory(*point) != target_area for point in seen):
                    raise ValueError("One turn's stroke must stay in one territory.")
                if target_area != player_index:
                    if self._team(target_area) == self._team(player_index):
                        raise ValueError("You can attack opponents, not a teammate.")
                    color = ATTACK_COLOR
                else:
                    color = player["color"]
            else:
                raise ValueError("The game is not accepting drawings right now.")

            if any(self._territory(x, y) != target_area for x, y in checked_cells):
                raise ValueError("Drawings must stay inside the selected territory.")

            for point in seen:
                self.cells[point] = color

            if self.phase == "action":
                self._advance_turn(player_index)

    def _turn_order(self):
        return [player["index"] for player in self.players if player["alive"]]

    def _turn_message(self):
        if self.current_turn is None:
            return "Waiting for the next round."
        player = self.players[self.current_turn]
        return f"Round {self.round_number}: {player['name']}'s turn. Draw one stroke."

    def _advance_turn(self, player_index):
        order = self._turn_order()
        next_players = [index for index in order if index > player_index]
        if next_players:
            self.current_turn = next_players[0]
            self.message = self._turn_message()
            return

        self._advance_life()
        if self.phase == "finished":
            return
        self.round_number += 1
        order = self._turn_order()
        self.current_turn = order[0] if order else None
        if self.phase != "finished":
            self.message = self._turn_message()

    def _advance_life(self):
        for _ in range(self.generations_per_round):
            neighbor_counts = {}
            for x, y in self.cells:
                area = self._territory(x, y)
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        neighbor = (x + dx, y + dy)
                        if (
                            0 <= neighbor[0] < self.width
                            and 0 <= neighbor[1] < self.height
                            and self._territory(*neighbor) == area
                        ):
                            neighbor_counts[neighbor] = (
                                neighbor_counts.get(neighbor, 0) + 1
                            )

            next_cells = {
                point
                for point, count in neighbor_counts.items()
                if count == 3 or (count == 2 and point in self.cells)
            }
            self.cells = {
                point: self.cells.get(point, self.players[self._territory(*point)]["color"])
                for point in next_cells
            }
            self.generation += 1

        for player in self.players:
            if player["alive"] and not any(
                self._territory(x, y) == player["index"] for x, y in self.cells
            ):
                player["alive"] = False

        alive_teams = {player["team"] for player in self.players if player["alive"]}
        if len(alive_teams) <= 1:
            self.phase = "finished"
            self.current_turn = None
            self.winner = next(iter(alive_teams), None)
            if self.winner is None:
                self.message = "No players survived. The game is a draw."
            elif self.mode == "1v1":
                winner = next(p["name"] for p in self.players if p["alive"])
                self.message = f"{winner} wins!"
            else:
                self.message = f"Team {self.winner + 1} wins!"

    def state(self):
        with self.lock:
            return {
                "mode": self.mode,
                "width": self.width,
                "height": self.height,
                "phase": self.phase,
                "players": [dict(player) for player in self.players],
                "cells": [
                    [x, y, color] for (x, y), color in self.cells.items()
                ],
                "current_turn": self.current_turn,
                "round": self.round_number,
                "generation": self.generation,
                "winner": self.winner,
                "message": self.message,
                "generations_per_round": self.generations_per_round,
            }


class _GameRequestHandler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            self.request.settimeout(10.0)
            raw_request = self.rfile.readline(65537)
            if len(raw_request) > 65536:
                raise ValueError("The request is too large.")
            request = json.loads(raw_request.decode("utf-8"))
            response = self.server.dispatch(request)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            response = {"error": str(error)}
        except (ConnectionError, OSError):
            return

        try:
            self.wfile.write(json.dumps(response).encode("utf-8") + b"\n")
        except (ConnectionError, OSError):
            return


class _GameTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, room):
        self.room = room
        super().__init__(address, _GameRequestHandler)

    def dispatch(self, request):
        if not isinstance(request, dict):
            raise ValueError("Invalid game request.")
        action = request.get("action")
        if action == "join":
            return self.room.join(request.get("name", ""), request.get("code", ""))
        token = request.get("token", "")
        if action == "state":
            self.room._authenticated_player(token)
            return {"state": self.room.state()}
        if action == "start":
            self.room.start(token)
            return {"state": self.room.state()}
        if action == "leave":
            self.room.leave(token)
            return {"state": self.room.state()}
        if action == "stroke":
            self.room.submit_stroke(token, request.get("cells"))
            return {"state": self.room.state()}
        raise ValueError("Unknown game request.")


class GameServer:
    def __init__(
        self, mode, generations_per_round=10, bind_address="0.0.0.0"
    ):
        self.room_code = f"{secrets.randbelow(1_000_000):06d}"
        self.room = GameRoom(mode, generations_per_round, self.room_code)
        self.server = _GameTCPServer((bind_address, PORT), self.room)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()

    def close(self):
        if self.thread.is_alive():
            self.server.shutdown()
        self.server.server_close()


class GameClient:
    def __init__(self, host, name, room_code):
        self.host = host
        self.name = name
        self.room_code = room_code
        self.token = None
        self.player_index = None

    def _request(self, payload):
        with socket.create_connection((self.host, PORT), timeout=2.0) as connection:
            connection.settimeout(2.0)
            with connection.makefile("rwb") as stream:
                stream.write(json.dumps(payload).encode("utf-8") + b"\n")
                stream.flush()
                line = stream.readline(1_000_001)
        if not line:
            raise ConnectionError("The host closed the connection.")
        response = json.loads(line.decode("utf-8"))
        if "error" in response:
            raise ValueError(response["error"])
        return response

    def join(self):
        response = self._request(
            {"action": "join", "name": self.name, "code": self.room_code}
        )
        self.token = response["token"]
        self.player_index = response["player_index"]
        return response["state"]

    def get_state(self):
        return self._request({"action": "state", "token": self.token})["state"]

    def start_game(self):
        return self._request({"action": "start", "token": self.token})["state"]

    def leave_game(self):
        return self._request({"action": "leave", "token": self.token})["state"]

    def submit_stroke(self, cells):
        return self._request(
            {"action": "stroke", "token": self.token, "cells": cells}
        )["state"]


def local_ipv4_address():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect(("192.0.2.1", 80))
            return probe.getsockname()[0]
        except OSError:
            return "127.0.0.1"
