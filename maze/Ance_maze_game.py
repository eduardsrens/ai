from __future__ import annotations

import json
import queue
import random
import socket
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

Position = tuple[int, int]
LEVEL_COUNT = 20
PORT = 53124
FIRST_LEVEL_MINIMUM_SECONDS = 60.0
REWARD_SECONDS = 5.0
HELD_MOVE_INTERVAL = 0.15
STATE_BROADCAST_INTERVAL = 0.04
AVATARS = ("🥕", "🥦", "🍅", "🌽", "🥒", "🍆", "🥔", "🌶️")
DIRECTIONS = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}
SCORES_FILE = Path(__file__).resolve().with_name("maze_scores.json")


@dataclass(frozen=True)
class Level:
    rows: tuple[str, ...]
    start: Position
    exit: Position
    rewards: set[Position]


def _distance_map(
    rows: tuple[str, ...],
    start: Position,
    blocked: set[Position] | None = None,
) -> dict[Position, int]:
    excluded = blocked if blocked is not None else set()
    distances = {start: 0}
    pending = deque([start])
    while pending:
        x, y = pending.popleft()
        for dx, dy in DIRECTIONS.values():
            neighbor = (x + dx, y + dy)
            nx, ny = neighbor
            if (
                neighbor not in excluded
                and neighbor not in distances
                and 0 <= ny < len(rows)
                and 0 <= nx < len(rows[0])
                and rows[ny][nx] != "#"
            ):
                distances[neighbor] = distances[(x, y)] + 1
                pending.append(neighbor)
    return distances


def generate_level(number: int, seed: int) -> Level:
    if not 1 <= number <= LEVEL_COUNT:
        raise ValueError(f"līmenim jābūt no 1 līdz {LEVEL_COUNT}")

    cells_per_side = 10 + number
    width = cells_per_side * 2 + 1
    height = width
    grid = [["#"] * width for _ in range(height)]
    rng = random.Random(seed + number * 7919)
    start = (1, 1)
    stack = [start]
    grid[start[1]][start[0]] = " "

    while stack:
        x, y = stack[-1]
        choices = [
            (x + dx, y + dy, x + dx // 2, y + dy // 2)
            for dx, dy in ((0, -2), (2, 0), (0, 2), (-2, 0))
            if 1 <= x + dx < width - 1
            and 1 <= y + dy < height - 1
            and grid[y + dy][x + dx] == "#"
        ]
        if not choices:
            stack.pop()
            continue
        nx, ny, wall_x, wall_y = rng.choice(choices)
        grid[wall_y][wall_x] = " "
        grid[ny][nx] = " "
        stack.append((nx, ny))

    rows = tuple("".join(row) for row in grid)
    distances = _distance_map(rows, start)
    furthest_distance = max(distances.values())
    exit_candidates = [
        position
        for position, distance in distances.items()
        if position != start
        and distance >= furthest_distance - max(2, number // 3)
        and sum(
            (position[0] + dx, position[1] + dy) in distances
            for dx, dy in DIRECTIONS.values()
        )
        == 1
    ]
    exit_position = rng.choice(exit_candidates)
    reachable_without_exit = _distance_map(rows, start, {exit_position})
    reward_candidates = [
        position
        for position in reachable_without_exit
        if position != start and position != exit_position
    ]
    reward_count = min(3 + number // 2, max(1, len(reward_candidates) // 24))
    rewards = set(rng.sample(reward_candidates, reward_count))
    return Level(rows, start, exit_position, rewards)


def shortest_path(level: Level, destination: Position) -> tuple[Position, ...] | None:
    pending = deque([level.start])
    previous: dict[Position, Position] = {}
    visited = {level.start}
    while pending:
        x, y = pending.popleft()
        if (x, y) == destination:
            path = [(x, y)]
            while path[-1] != level.start:
                path.append(previous[path[-1]])
            path.reverse()
            return tuple(path)
        for dx, dy in DIRECTIONS.values():
            neighbor = (x + dx, y + dy)
            nx, ny = neighbor
            if (
                0 <= ny < len(level.rows)
                and 0 <= nx < len(level.rows[0])
                and level.rows[ny][nx] != "#"
                and neighbor not in visited
            ):
                visited.add(neighbor)
                previous[neighbor] = (x, y)
                pending.append(neighbor)
    return None


class RaceGame:
    def __init__(
        self,
        players: list[dict[str, Any]],
        seed: int | None = None,
        started_at: float | None = None,
    ) -> None:
        if not 1 <= len(players) <= 2:
            raise ValueError("spēlē var piedalīties viens vai divi spēlētāji")
        self.seed = seed if seed is not None else random.randrange(1_000_000_000)
        self.started_at = perf_counter() if started_at is None else started_at
        self.level_started_at = self.started_at
        self.level_number = 1
        self.players: dict[int, dict[str, Any]] = {}
        for player in players:
            player_id = int(player["id"])
            name = str(player["name"]).strip()[:18] or f"Spēlētājs {player_id}"
            avatar = str(player["avatar"])
            if avatar not in AVATARS:
                raise ValueError("izvēlēts neatbalstīts avatārs")
            self.players[player_id] = {
                "id": player_id,
                "name": name,
                "avatar": avatar,
                "x": 1,
                "y": 1,
                "from_x": 1,
                "from_y": 1,
                "move_started_at": self.started_at,
                "score": 0,
                "wins": 0,
                "completed_levels": 0,
                "time_credit": 0.0,
                "finished": False,
                "waiting_at_exit": False,
                "last_move_at": float("-inf"),
            }
        self.level = generate_level(self.level_number, self.seed)
        self.first_finisher: int | None = None
        self.race_winner: int | None = None
        self.game_over = False
        self.awaiting_next_level = False
        self.bonus_message = ""
        self.bonus_message_until = 0.0

    def move(self, player_id: int, direction: str, now: float | None = None) -> bool:
        if direction not in DIRECTIONS:
            raise ValueError(f"nezināms virziens: {direction}")
        if player_id not in self.players:
            raise KeyError(f"spēlē nav spēlētāja ar ID {player_id}")
        current_time = perf_counter() if now is None else now
        self.tick(current_time)
        player = self.players[player_id]
        if self.game_over or player["finished"]:
            return False
        if player["waiting_at_exit"]:
            return False
        if current_time - player["last_move_at"] < 0.095:
            return False

        dx, dy = DIRECTIONS[direction]
        next_position = (player["x"] + dx, player["y"] + dy)
        nx, ny = next_position
        if (
            not 0 <= ny < len(self.level.rows)
            or not 0 <= nx < len(self.level.rows[0])
            or self.level.rows[ny][nx] == "#"
        ):
            return False

        player["from_x"], player["from_y"] = player["x"], player["y"]
        player["x"], player["y"] = next_position
        player["move_started_at"] = current_time
        player["last_move_at"] = current_time
        if (
            next_position == self.level.exit
            and self.level_number == 1
            and current_time - self.level_started_at < FIRST_LEVEL_MINIMUM_SECONDS
        ):
            player["waiting_at_exit"] = True
        if next_position in self.level.rewards:
            self.level.rewards.remove(next_position)
            player["time_credit"] += REWARD_SECONDS
            self.bonus_message = f"{player['name']} savāca balvu: -5 sekundes!"
            self.bonus_message_until = current_time + 2.5
        self.tick(current_time)
        return True

    def tick(self, now: float | None = None) -> None:
        current_time = perf_counter() if now is None else now
        if self.game_over:
            return
        if self.awaiting_next_level:
            return
        gate_open = (
            self.level_number > 1
            or current_time - self.level_started_at >= FIRST_LEVEL_MINIMUM_SECONDS
        )
        for player_id, player in self.players.items():
            if not player["finished"] and (player["x"], player["y"]) == self.level.exit:
                if gate_open:
                    self._finish_level(player_id)
                else:
                    player["waiting_at_exit"] = True

        if all(player["finished"] for player in self.players.values()):
            if self.level_number == LEVEL_COUNT:
                self.game_over = True
                self.race_winner = self.first_finisher
                return
            if len(self.players) == 1:
                self.awaiting_next_level = True
                return
            self._advance_level(current_time)

    def advance_level(self, now: float | None = None) -> bool:
        if (
            len(self.players) != 1
            or not self.awaiting_next_level
            or self.game_over
            or self.level_number >= LEVEL_COUNT
        ):
            return False
        current_time = perf_counter() if now is None else now
        self._advance_level(current_time)
        return True

    def _advance_level(self, current_time: float) -> None:
        self.level_number += 1
        self.level = generate_level(self.level_number, self.seed)
        self.level_started_at = current_time
        self.first_finisher = None
        self.awaiting_next_level = False
        for player in self.players.values():
            player["x"], player["y"] = self.level.start
            player["from_x"], player["from_y"] = self.level.start
            player["move_started_at"] = current_time
            player["finished"] = False
            player["waiting_at_exit"] = False
            player["last_move_at"] = float("-inf")

    def _finish_level(self, player_id: int) -> None:
        player = self.players[player_id]
        player["finished"] = True
        player["waiting_at_exit"] = False
        player["completed_levels"] += 1
        player["score"] += 100
        if self.first_finisher is None:
            self.first_finisher = player_id
            if len(self.players) == 2:
                player["score"] += 50
                player["wins"] += 1

    def elapsed_seconds(self, player_id: int, now: float | None = None) -> float:
        current_time = perf_counter() if now is None else now
        player = self.players[player_id]
        return max(0.0, current_time - self.started_at - player["time_credit"])

    def snapshot(self, now: float | None = None) -> dict[str, Any]:
        current_time = perf_counter() if now is None else now
        self.tick(current_time)
        return {
            "level": self.level_number,
            "rows": list(self.level.rows),
            "start": list(self.level.start),
            "exit": list(self.level.exit),
            "rewards": [list(position) for position in sorted(self.level.rewards)],
            "level_elapsed": max(0.0, current_time - self.level_started_at),
            "first_finisher": self.first_finisher,
            "race_winner": self.race_winner,
            "game_over": self.game_over,
            "awaiting_next_level": self.awaiting_next_level,
            "players": {
                str(player_id): {
                    "id": player_id,
                    "name": player["name"],
                    "avatar": player["avatar"],
                    "x": player["x"],
                    "y": player["y"],
                    "visual_x": player["from_x"]
                    + (player["x"] - player["from_x"])
                    * min(1.0, max(0.0, (current_time - player["move_started_at"]) / HELD_MOVE_INTERVAL)),
                    "visual_y": player["from_y"]
                    + (player["y"] - player["from_y"])
                    * min(1.0, max(0.0, (current_time - player["move_started_at"]) / HELD_MOVE_INTERVAL)),
                    "score": player["score"],
                    "wins": player["wins"],
                    "completed_levels": player["completed_levels"],
                    "time": self.elapsed_seconds(player_id, current_time),
                    "finished": player["finished"],
                    "waiting_at_exit": player["waiting_at_exit"],
                }
                for player_id, player in self.players.items()
            },
            "bonus_message": self.bonus_message if current_time < self.bonus_message_until else "",
        }

    def completed_records(self, mode: str, now: float | None = None) -> list[dict[str, Any]]:
        current_time = perf_counter() if now is None else now
        records = []
        for player_id, player in self.players.items():
            if player["completed_levels"] != LEVEL_COUNT:
                continue
            records.append(
                {
                    "name": player["name"],
                    "avatar": player["avatar"],
                    "score": player["score"],
                    "wins": player["wins"],
                    "time_seconds": round(self.elapsed_seconds(player_id, current_time), 2),
                    "levels_completed": player["completed_levels"],
                    "mode": mode,
                    "completed_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
        return records


def load_scores(path: Path = SCORES_FILE) -> list[dict[str, Any]]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"rezultātu fails nav derīgs JSON: {path}") from error
    if not isinstance(data, list) or any(not isinstance(record, dict) for record in data):
        raise ValueError(f"rezultātu failam jābūt JSON objektu sarakstam: {path}")
    return data


def save_scores(records: list[dict[str, Any]], path: Path = SCORES_FILE) -> None:
    existing = load_scores(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(existing + records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(path)


def ranked_scores(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        records,
        key=lambda record: (
            -int(record.get("score", 0)),
            float(record.get("time_seconds", float("inf"))),
        ),
    )


def format_time(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    minutes, remainder = divmod(total_seconds, 60)
    return f"{minutes:02d}:{remainder:02d}"


def _encode_message(message: dict[str, Any]) -> bytes:
    return (json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


class LanServer:
    def __init__(self) -> None:
        self.incoming: queue.Queue[dict[str, Any]] = queue.Queue()
        self.outgoing: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1)
        self._closed = threading.Event()
        self._server_socket: socket.socket | None = None
        self._client_socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self.connected = False

    def start(self) -> None:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server_socket.bind(("0.0.0.0", PORT))
            server_socket.listen(1)
        except OSError:
            server_socket.close()
            raise
        server_socket.settimeout(0.5)
        self._server_socket = server_socket
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def _accept_loop(self) -> None:
        assert self._server_socket is not None
        while not self._closed.is_set():
            try:
                client_socket, address = self._server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            if self.connected:
                client_socket.close()
                continue
            self._client_socket = client_socket
            self.connected = True
            self.incoming.put({"type": "connected", "address": address[0]})
            self._client_loop(client_socket)
            self.connected = False
            self._client_socket = None
            self.incoming.put({"type": "disconnected"})

    def _client_loop(self, client_socket: socket.socket) -> None:
        client_socket.settimeout(0.08)
        buffer = b""
        while not self._closed.is_set():
            try:
                data = client_socket.recv(65536)
            except socket.timeout:
                data = None
            except OSError:
                return
            if data == b"":
                return
            if data:
                buffer += data
                if len(buffer) > 1_000_000:
                    self.incoming.put({"type": "protocol_error", "message": "Pārāk liels tīkla ziņojums"})
                    return
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    try:
                        message = json.loads(line.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        self.incoming.put({"type": "protocol_error", "message": "Nederīgs tīkla ziņojums"})
                        return
                    if isinstance(message, dict):
                        self.incoming.put(message)
            try:
                outgoing = self.outgoing.get_nowait()
            except queue.Empty:
                continue
            try:
                client_socket.sendall(_encode_message(outgoing))
            except OSError:
                return

    def broadcast(self, message: dict[str, Any]) -> None:
        try:
            self.outgoing.put_nowait(message)
        except queue.Full:
            try:
                self.outgoing.get_nowait()
            except queue.Empty:
                pass
            self.outgoing.put_nowait(message)

    def close(self) -> None:
        self._closed.set()
        for connection in (self._client_socket, self._server_socket):
            if connection is not None:
                try:
                    connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                connection.close()


class LanClient:
    def __init__(self) -> None:
        self.incoming: queue.Queue[dict[str, Any]] = queue.Queue()
        self.outgoing: queue.Queue[dict[str, Any]] = queue.Queue()
        self._closed = threading.Event()
        self._socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self.latest_state: dict[str, Any] | None = None
        self.error = ""

    def connect(self, address: str) -> None:
        connection = socket.create_connection((address, PORT), timeout=5)
        connection.settimeout(0.08)
        self._socket = connection
        self._thread = threading.Thread(target=self._network_loop, daemon=True)
        self._thread.start()

    def send(self, message: dict[str, Any]) -> None:
        self.outgoing.put(message)

    def _network_loop(self) -> None:
        assert self._socket is not None
        buffer = b""
        while not self._closed.is_set():
            try:
                outgoing = self.outgoing.get_nowait()
            except queue.Empty:
                outgoing = None
            if outgoing is not None:
                try:
                    self._socket.sendall(_encode_message(outgoing))
                except OSError as error:
                    self.error = f"Tīkla savienojums pārtrūka: {error}"
                    return
            try:
                data = self._socket.recv(65536)
            except socket.timeout:
                continue
            except OSError as error:
                self.error = f"Tīkla savienojums pārtrūka: {error}"
                return
            if data == b"":
                self.error = "Tīkla savienojums ar saimnieku ir pārtrūcis."
                return
            buffer += data
            if len(buffer) > 1_000_000:
                self.error = "Saņemts pārāk liels tīkla ziņojums."
                return
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                try:
                    message = json.loads(line.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self.error = "Saņemts nederīgs tīkla ziņojums."
                    return
                if isinstance(message, dict):
                    self.incoming.put(message)
                    if message.get("type") == "game":
                        self.latest_state = message

    def close(self) -> None:
        self._closed.set()
        if self._socket is not None:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self._socket.close()


def _local_address() -> str:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("192.0.2.1", 1))
        address = probe.getsockname()[0]
        if not address.startswith("127."):
            return address
    except OSError:
        pass
    finally:
        probe.close()
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "noskaidro ar ipconfig"


def main() -> int:
    try:
        import pygame
    except ImportError as error:
        print("Nav atrasts pygame-ce. Uzinstalē to ar: python -m pip install -r maze/requirements.txt")
        raise error

    pygame.init()
    screen = pygame.display.set_mode((1240, 820))
    pygame.display.set_caption("Dārzeņu labirints — LAN sacīkste")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 22)
    small_font = pygame.font.SysFont("arial", 17)
    title_font = pygame.font.SysFont("arial", 34, bold=True)
    emoji_font = pygame.font.SysFont("Segoe UI Emoji", 30)

    colors = {
        "background": (18, 26, 35),
        "panel": (29, 42, 54),
        "floor": (222, 231, 220),
        "wall": (49, 73, 68),
        "text": (244, 246, 239),
        "muted": (174, 193, 184),
        "accent": (247, 190, 82),
        "green": (100, 206, 126),
        "blue": (94, 176, 236),
        "red": (232, 109, 96),
    }

    screen_state = "profile"
    player_name = ""
    avatar_index = 0
    ip_text = "127.0.0.1"
    mode = ""
    message = ""
    server: LanServer | None = None
    client: LanClient | None = None
    remote_profile: dict[str, str] | None = None
    game: RaceGame | None = None
    latest_snapshot: dict[str, Any] | None = None
    local_player_id = 1
    saved_results = False
    save_error = ""
    score_error = ""
    scores: list[dict[str, Any]] = []
    map_surface: pygame.Surface | None = None
    map_surface_rows: tuple[str, ...] | None = None
    last_broadcast_at = 0.0
    next_move_at = 0.0
    map_rect = pygame.Rect(24, 90, 860, 700)
    button_rects: dict[str, pygame.Rect] = {}
    pygame.key.start_text_input()

    def draw_line(text: str, x: int, y: int, color: tuple[int, int, int] = colors["text"], big: bool = False) -> None:
        active_font = title_font if big else font
        screen.blit(active_font.render(text, True, color), (x, y))

    def reload_scores() -> None:
        nonlocal scores, score_error
        try:
            scores = ranked_scores(load_scores())
            score_error = ""
        except (OSError, ValueError) as error:
            scores = []
            score_error = str(error)

    def return_to_profile() -> None:
        nonlocal screen_state, server, client, game, latest_snapshot, saved_results
        if server is not None:
            server.close()
            server = None
        if client is not None:
            client.close()
            client = None
        game = None
        latest_snapshot = None
        saved_results = False
        screen_state = "profile"

    def return_to_menu() -> None:
        nonlocal screen_state, server, client, game, latest_snapshot, saved_results, mode
        if server is not None:
            server.close()
            server = None
        if client is not None:
            client.close()
            client = None
        game = None
        latest_snapshot = None
        saved_results = False
        mode = ""
        screen_state = "menu"

    def save_finished_game(current_game: RaceGame, current_mode: str) -> None:
        nonlocal saved_results, save_error
        if saved_results:
            return
        records = current_game.completed_records(current_mode)
        if records:
            try:
                save_scores(records)
            except (OSError, ValueError) as error:
                save_error = f"Neizdevās saglabāt rezultātus: {error}"
            else:
                save_error = ""
        saved_results = True
        reload_scores()

    def player_profile(player_id: int, name: str, avatar: str) -> dict[str, Any]:
        return {"id": player_id, "name": name, "avatar": avatar}

    def draw_button(
        name: str,
        label: str,
        rect: pygame.Rect,
        enabled: bool = True,
    ) -> None:
        button_rects[name] = rect
        hovered = enabled and rect.collidepoint(pygame.mouse.get_pos())
        fill = colors["accent"] if hovered else colors["panel"]
        text_color = colors["background"] if hovered else colors["text"]
        if not enabled:
            text_color = colors["muted"]
        pygame.draw.rect(screen, fill, rect, border_radius=9)
        pygame.draw.rect(screen, colors["muted"], rect, width=1, border_radius=9)
        label_image = font.render(label, True, text_color)
        screen.blit(label_image, label_image.get_rect(center=rect.center))

    def start_solo() -> None:
        nonlocal mode, game, saved_results, screen_state, latest_snapshot
        nonlocal map_surface, map_surface_rows, next_move_at
        mode = "solo"
        game = RaceGame([player_profile(1, player_name, AVATARS[avatar_index])])
        saved_results = False
        screen_state = "game"
        latest_snapshot = game.snapshot()
        map_surface = None
        map_surface_rows = None
        next_move_at = 0.0

    def start_host() -> None:
        nonlocal server, mode, remote_profile, screen_state, message
        try:
            new_server = LanServer()
            new_server.start()
        except OSError as error:
            server = None
            message = f"Neizdevās palaist LAN serveri: {error}"
            return
        server = new_server
        mode = "host"
        remote_profile = None
        screen_state = "host_lobby"
        message = ""

    def connect_to_host() -> None:
        nonlocal client, screen_state, message
        if not ip_text.strip():
            return
        new_client = LanClient()
        try:
            new_client.connect(ip_text.strip())
        except OSError as error:
            new_client.close()
            client = None
            message = f"Neizdevās pieslēgties: {error}"
            return
        client = new_client
        client.send(
            {
                "type": "hello",
                "name": player_name,
                "avatar": AVATARS[avatar_index],
            }
        )
        screen_state = "client_lobby"
        message = ""

    def start_host_race() -> None:
        nonlocal game, mode, saved_results, screen_state, latest_snapshot
        nonlocal last_broadcast_at, map_surface, map_surface_rows, next_move_at
        if remote_profile is None:
            return
        mode = "host"
        game = RaceGame(
            [
                player_profile(1, player_name, AVATARS[avatar_index]),
                player_profile(2, remote_profile["name"], remote_profile["avatar"]),
            ]
        )
        saved_results = False
        screen_state = "game"
        latest_snapshot = game.snapshot()
        last_broadcast_at = 0.0
        map_surface = None
        map_surface_rows = None
        next_move_at = 0.0

    def open_scores() -> None:
        nonlocal screen_state
        reload_scores()
        screen_state = "scores"

    def activate_button(name: str) -> None:
        nonlocal avatar_index, screen_state, ip_text, message
        nonlocal latest_snapshot, map_surface, map_surface_rows, next_move_at
        if name == "avatar-prev":
            avatar_index = (avatar_index - 1) % len(AVATARS)
        elif name == "avatar-next":
            avatar_index = (avatar_index + 1) % len(AVATARS)
        elif name.startswith("avatar-"):
            avatar_index = int(name.removeprefix("avatar-"))
        elif name == "profile-continue" and player_name.strip():
            screen_state = "menu"
            message = ""
        elif name == "menu-solo":
            start_solo()
        elif name == "menu-host":
            start_host()
        elif name == "menu-join":
            ip_text = ""
            screen_state = "join"
        elif name == "menu-scores":
            open_scores()
        elif name == "host-start":
            start_host_race()
        elif name == "host-back":
            return_to_profile()
        elif name == "join-connect":
            connect_to_host()
        elif name == "join-back":
            screen_state = "menu"
        elif name == "client-back":
            return_to_profile()
        elif name == "scores-back":
            screen_state = "menu"
        elif name == "game-new":
            return_to_profile()
        elif name == "game-scores":
            open_scores()
        elif name == "level-next" and game is not None and game.advance_level():
            latest_snapshot = game.snapshot()
            map_surface = None
            map_surface_rows = None
            next_move_at = 0.0
        elif name == "level-menu":
            return_to_menu()
        elif name == "solo-finish-menu":
            return_to_menu()
        elif name == "solo-finish-scores":
            open_scores()

    running = True
    while running:
        now = perf_counter()
        if screen_state == "game":
            pressed = pygame.key.get_pressed()
            held_directions = (
                ("up", (pygame.K_w, pygame.K_UP)),
                ("down", (pygame.K_s, pygame.K_DOWN)),
                ("left", (pygame.K_a, pygame.K_LEFT)),
                ("right", (pygame.K_d, pygame.K_RIGHT)),
            )
            held_direction = next(
                (
                    direction
                    for direction, keys in held_directions
                    if any(pressed[key] for key in keys)
                ),
                None,
            )
            if held_direction is None:
                next_move_at = 0.0
            elif now >= next_move_at and not (
                latest_snapshot
                and (
                    latest_snapshot.get("game_over")
                    or latest_snapshot.get("awaiting_next_level")
                )
            ):
                if mode == "client" and client is not None:
                    client.send({"type": "move", "direction": held_direction})
                elif game is not None and not game.game_over:
                    game.move(1, held_direction, now)
                next_move_at = now + HELD_MOVE_INTERVAL

        if screen_state == "game" and mode in ("solo", "host") and game is not None:
            if server is not None:
                while True:
                    try:
                        network_message = server.incoming.get_nowait()
                    except queue.Empty:
                        break
                    if network_message.get("type") == "move" and 2 in game.players:
                        direction = network_message.get("direction")
                        if direction in DIRECTIONS:
                            game.move(2, direction, now)
                game.tick(now)
                if game.game_over:
                    save_finished_game(game, "lan")
                if now - last_broadcast_at >= STATE_BROADCAST_INTERVAL:
                    server.broadcast({"type": "game", "state": game.snapshot(now)})
                    last_broadcast_at = now
                latest_snapshot = game.snapshot(now)
            else:
                game.tick(now)
                latest_snapshot = game.snapshot(now)
                if game.game_over:
                    save_finished_game(game, "solo")

        if screen_state == "game" and mode == "client" and client is not None:
            if client.latest_state is not None:
                latest_snapshot = client.latest_state.get("state")

        if screen_state == "host_lobby" and server is not None:
            while True:
                try:
                    network_message = server.incoming.get_nowait()
                except queue.Empty:
                    break
                if network_message.get("type") == "hello":
                    remote_name = str(network_message.get("name", "")).strip()[:18]
                    remote_avatar = str(network_message.get("avatar", ""))
                    if remote_avatar in AVATARS:
                        remote_profile = {
                            "name": remote_name or "Pretinieks",
                            "avatar": remote_avatar,
                        }

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.TEXTINPUT:
                if screen_state == "profile" and len(player_name) < 18:
                    player_name += event.text
                elif screen_state == "join":
                    ip_text = (ip_text + event.text)[:64]
            elif event.type == pygame.KEYDOWN:
                if screen_state == "profile":
                    if event.key == pygame.K_BACKSPACE:
                        player_name = player_name[:-1]
                    elif event.key == pygame.K_LEFT:
                        avatar_index = (avatar_index - 1) % len(AVATARS)
                    elif event.key == pygame.K_RIGHT:
                        avatar_index = (avatar_index + 1) % len(AVATARS)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        activate_button("profile-continue")
                elif screen_state == "menu":
                    menu_actions = {
                        pygame.K_1: "menu-solo",
                        pygame.K_2: "menu-host",
                        pygame.K_3: "menu-join",
                        pygame.K_4: "menu-scores",
                    }
                    action = menu_actions.get(event.key)
                    if action is not None:
                        activate_button(action)
                elif screen_state == "host_lobby":
                    if event.key == pygame.K_ESCAPE:
                        activate_button("host-back")
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        activate_button("host-start")
                elif screen_state == "join":
                    if event.key == pygame.K_ESCAPE:
                        activate_button("join-back")
                    elif event.key == pygame.K_BACKSPACE:
                        ip_text = ip_text[:-1]
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        activate_button("join-connect")
                elif screen_state == "client_lobby":
                    if event.key == pygame.K_ESCAPE:
                        activate_button("client-back")
                elif screen_state == "scores":
                    if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
                        activate_button("scores-back")
                elif screen_state == "game":
                    if (
                        mode == "solo"
                        and latest_snapshot
                        and latest_snapshot.get("awaiting_next_level")
                    ):
                        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_n):
                            activate_button("level-next")
                        elif event.key in (pygame.K_ESCAPE, pygame.K_m):
                            activate_button("level-menu")
                    elif (
                        mode == "solo"
                        and latest_snapshot
                        and latest_snapshot.get("game_over")
                    ):
                        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_m, pygame.K_ESCAPE):
                            activate_button("solo-finish-menu")
                        elif event.key == pygame.K_l:
                            activate_button("solo-finish-scores")
                    elif event.key == pygame.K_ESCAPE:
                        return_to_profile()
                    elif latest_snapshot and latest_snapshot.get("game_over"):
                        if event.key == pygame.K_l:
                            activate_button("game-scores")
                        elif event.key in (pygame.K_r, pygame.K_RETURN, pygame.K_KP_ENTER):
                            activate_button("game-new")
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for button_name, rect in tuple(button_rects.items()):
                    if rect.collidepoint(event.pos):
                        activate_button(button_name)
                        break

        if screen_state == "client_lobby" and client is not None:
            if client.latest_state is not None:
                latest_snapshot = client.latest_state.get("state")
                screen_state = "game"
                mode = "client"
                local_player_id = 2
            elif client.error:
                message = client.error

        if screen_state == "game" and mode == "client" and latest_snapshot:
            if latest_snapshot.get("game_over") and not saved_results:
                client_players = latest_snapshot.get("players", {})
                local = client_players.get(str(local_player_id))
                if local and int(local.get("completed_levels", 0)) == LEVEL_COUNT:
                    record = {
                        "name": local["name"],
                        "avatar": local["avatar"],
                        "score": local["score"],
                        "wins": local["wins"],
                        "time_seconds": round(float(local["time"]), 2),
                        "levels_completed": local["completed_levels"],
                        "mode": "lan",
                        "completed_at": datetime.now().isoformat(timespec="seconds"),
                    }
                    try:
                        save_scores([record])
                    except (OSError, ValueError) as error:
                        save_error = f"Neizdevās saglabāt rezultātu: {error}"
                    saved_results = True

        button_rects.clear()
        screen.fill(colors["background"])
        if screen_state == "profile":
            draw_line("Dārzeņu labirints", 80, 65, big=True)
            draw_line("Sacīkste ar 20 arvien grūtākiem līmeņiem", 80, 120, colors["muted"])
            draw_line("Ievadi savu vārdu:", 80, 205)
            pygame.draw.rect(screen, colors["panel"], (80, 245, 500, 54), border_radius=8)
            draw_line(player_name + ("|" if int(now * 2) % 2 == 0 else ""), 98, 256)
            draw_line("Izvēlies dārzeņa avatāru (← / → vai klikšķini):", 80, 355)
            for index, avatar in enumerate(AVATARS):
                avatar_rect = pygame.Rect(80 + index % 4 * 82, 410 + index // 4 * 72, 64, 56)
                button_rects[f"avatar-{index}"] = avatar_rect
                pygame.draw.rect(screen, colors["panel"], avatar_rect, border_radius=8)
                pygame.draw.rect(
                    screen,
                    colors["accent"] if index == avatar_index else colors["muted"],
                    avatar_rect,
                    width=3 if index == avatar_index else 1,
                    border_radius=8,
                )
                avatar_image = emoji_font.render(avatar, True, colors["text"])
                screen.blit(avatar_image, avatar_image.get_rect(center=avatar_rect.center))
            draw_button(
                "profile-continue",
                "Turpināt  [Enter]",
                pygame.Rect(80, 600, 270, 54),
                enabled=bool(player_name.strip()),
            )
            draw_line("Katrs savāktais ⭐ samazina Tavu kopējo laiku par 5 sekundēm.", 80, 690, colors["muted"])
        elif screen_state == "menu":
            draw_line("Izvēlies spēles režīmu", 80, 65, big=True)
            draw_button("menu-solo", "1  Viens spēlētājs", pygame.Rect(100, 150, 420, 54))
            draw_button("menu-host", "2  Izveidot LAN sacīksti", pygame.Rect(100, 218, 420, 54))
            draw_button("menu-join", "3  Pievienoties LAN sacīkstei", pygame.Rect(100, 286, 420, 54))
            draw_button("menu-scores", "4  Rezultātu tabula / score rank", pygame.Rect(100, 354, 420, 54))
            draw_line("Saimnieks un pretinieks vienlaikus spēlē vienu līmeni.", 100, 455, colors["muted"])
            draw_line("Turi WASD vai bultiņu taustiņu, lai turpinātu kustību.", 100, 490, colors["muted"])
            draw_line("Pirmajā līmenī izeja atveras pēc 60 sekundēm.", 100, 525, colors["accent"])
            if message:
                draw_line(message, 100, 580, colors["red"])
        elif screen_state == "host_lobby":
            draw_line("LAN sacīkste — gaidu pretinieku", 80, 65, big=True)
            draw_line(f"Tava lokālā IP adrese: {_local_address()}", 100, 175, colors["accent"])
            draw_line(f"Ports: {PORT}", 100, 212)
            draw_line("Pretinieks savā datorā izvēlas 3 un ievada šo IP.", 100, 270, colors["muted"])
            draw_line("Atļauj spēlei piekļuvi privātajam tīklam, ja to prasa ugunsmūris.", 100, 310, colors["muted"])
            if server is not None and server.connected:
                if remote_profile:
                    screen.blit(emoji_font.render(remote_profile["avatar"], True, colors["text"]), (100, 395))
                    draw_line(f"{remote_profile['name']} ir pievienojies!", 150, 405, colors["green"])
                    draw_button("host-start", "Sākt sacīksti  [Enter]", pygame.Rect(100, 465, 300, 54))
                else:
                    draw_line("Pretinieks pieslēdzies; ielādē profilu...", 100, 400, colors["muted"])
            else:
                draw_line("Savienojums vēl nav izveidots.", 100, 395, colors["muted"])
            if not remote_profile:
                draw_button("host-start", "Gaida pretinieku", pygame.Rect(100, 465, 300, 54), enabled=False)
            draw_button("host-back", "Atpakaļ  [Esc]", pygame.Rect(100, 690, 240, 50))
        elif screen_state == "join":
            draw_line("Pievienoties sacīkstei", 80, 65, big=True)
            draw_line("Ievadi saimnieka datora lokālo IP adresi:", 100, 185)
            pygame.draw.rect(screen, colors["panel"], (100, 230, 500, 58), border_radius=8)
            draw_line(ip_text + ("|" if int(now * 2) % 2 == 0 else ""), 118, 245)
            draw_button("join-connect", "Pieslēgties  [Enter]", pygame.Rect(100, 325, 280, 54))
            draw_button("join-back", "Atpakaļ  [Esc]", pygame.Rect(100, 395, 240, 50))
            draw_line("Saimniekam jābūt vienā lokālajā tīklā un spēlei jābūt palaistai.", 100, 475, colors["muted"])
            if message:
                draw_line(message[:100], 100, 525, colors["red"])
        elif screen_state == "client_lobby":
            draw_line("Savienojums izveidots", 80, 65, big=True)
            draw_line("Gaidi, kamēr saimnieks sāk sacīksti...", 100, 180, colors["muted"])
            if client is not None and client.error:
                draw_line(client.error[:100], 100, 250, colors["red"])
            draw_button("client-back", "Atcelt  [Esc]", pygame.Rect(100, 330, 240, 50))
        elif screen_state == "scores":
            draw_line("Rezultātu tabula — score rank", 80, 45, big=True)
            draw_line("Vieta   Spēlētājs            Punkti   Uzvaras   Laiks", 90, 115, colors["accent"])
            if score_error:
                draw_line(score_error[:100], 90, 165, colors["red"])
            elif not scores:
                draw_line("Vēl nav saglabātu rezultātu.", 90, 165, colors["muted"])
            for rank, record in enumerate(scores[:15], start=1):
                y = 160 + (rank - 1) * 37
                name = str(record.get("name", "Spēlētājs"))[:18]
                avatar = str(record.get("avatar", ""))
                line = (
                    f"{rank:>2}.   {avatar} {name:<18} "
                    f"{int(record.get('score', 0)):>5}      "
                    f"{int(record.get('wins', 0)):>2}      "
                    f"{format_time(float(record.get('time_seconds', 0)))}"
                )
                screen.blit(small_font.render(line, True, colors["text"]), (90, y))
            draw_button("scores-back", "Atpakaļ  [Esc]", pygame.Rect(90, 750, 240, 50))
        elif screen_state == "game":
            snapshot = latest_snapshot
            if snapshot is None:
                draw_line("Gaida spēles stāvokli no saimnieka...", 80, 100, colors["muted"])
            else:
                rows = tuple(snapshot["rows"])
                if rows != map_surface_rows:
                    map_surface_rows = rows
                    unit = 5
                    map_surface = pygame.Surface((len(rows[0]) * unit, len(rows) * unit))
                    map_surface.fill(colors["floor"])
                    for y, row in enumerate(rows):
                        for x, cell in enumerate(row):
                            if cell == "#":
                                pygame.draw.rect(
                                    map_surface,
                                    colors["wall"],
                                    (x * unit, y * unit, unit, unit),
                                )
                assert map_surface is not None
                scale = min(map_rect.width / len(rows[0]), map_rect.height / len(rows))
                draw_width = max(1, round(len(rows[0]) * scale))
                draw_height = max(1, round(len(rows) * scale))
                draw_x = map_rect.x + (map_rect.width - draw_width) // 2
                draw_y = map_rect.y + (map_rect.height - draw_height) // 2
                screen.blit(pygame.transform.scale(map_surface, (draw_width, draw_height)), (draw_x, draw_y))

                def center(position: list[int] | tuple[float, float]) -> tuple[int, int]:
                    return (
                        round(draw_x + (position[0] + 0.5) * draw_width / len(rows[0])),
                        round(draw_y + (position[1] + 0.5) * draw_height / len(rows)),
                    )

                cell_size = scale
                star_font = pygame.font.SysFont("Segoe UI Emoji", max(14, min(30, round(cell_size * 1.15))))
                for reward in snapshot["rewards"]:
                    reward_image = star_font.render("⭐", True, colors["accent"])
                    screen.blit(reward_image, reward_image.get_rect(center=center(reward)))
                exit_center = center(snapshot["exit"])
                exit_font = pygame.font.SysFont("Segoe UI Emoji", max(16, min(32, round(cell_size * 1.3))))
                exit_image = exit_font.render("🏁", True, colors["text"])
                screen.blit(exit_image, exit_image.get_rect(center=exit_center))

                player_rows = list(snapshot["players"].values())
                positions: dict[tuple[float, float], list[dict[str, Any]]] = {}
                for player in player_rows:
                    position = (
                        round(float(player["visual_x"]), 3),
                        round(float(player["visual_y"]), 3),
                    )
                    positions.setdefault(position, []).append(player)
                avatar_font = pygame.font.SysFont("Segoe UI Emoji", max(16, min(34, round(cell_size * 1.45))))
                for position, occupants in positions.items():
                    base_center = center(position)
                    for index, player in enumerate(occupants):
                        x_offset = round((index - (len(occupants) - 1) / 2) * cell_size * 0.48)
                        image = avatar_font.render(player["avatar"], True, colors["text"])
                        screen.blit(image, image.get_rect(center=(base_center[0] + x_offset, base_center[1])))

                pygame.draw.rect(screen, colors["panel"], (910, 0, 330, 820))
                draw_line(f"{snapshot['level']} / {LEVEL_COUNT}. līmenis", 930, 30, colors["accent"], big=True)
                for index, player in enumerate(player_rows):
                    y = 100 + index * 138
                    screen.blit(emoji_font.render(player["avatar"], True, colors["text"]), (930, y))
                    draw_line(str(player["name"])[:17], 978, y + 4)
                    draw_line(f"Punkti: {player['score']}   Uzvaras: {player['wins']}", 930, y + 45, colors["muted"])
                    draw_line(f"Laiks: {format_time(float(player['time']))}", 930, y + 76)
                    if player["finished"]:
                        draw_line("Līmenis pabeigts — gaidi pretinieku", 930, y + 105, colors["green"])
                    elif player["waiting_at_exit"]:
                        draw_line("Finišs sasniegts — gaidi atvēršanos", 930, y + 105, colors["accent"])
                draw_line("⭐ Balva: −5 s kopējam laikam", 930, 405, colors["accent"])
                if int(snapshot["level"]) == 1:
                    remaining = max(0, int(FIRST_LEVEL_MINIMUM_SECONDS - float(snapshot["level_elapsed"]) + 0.99))
                    draw_line(f"Pirmā līmeņa izeja: {remaining} s", 930, 445, colors["muted"])
                if snapshot.get("bonus_message"):
                    draw_line(str(snapshot["bonus_message"]), 930, 490, colors["green"])
                if len(player_rows) == 2:
                    draw_line("WASD vai bultiņas — kustība", 930, 560, colors["muted"])
                    draw_line("Pirmais pie izejas iegūst +50", 930, 590, colors["muted"])
                if snapshot.get("game_over"):
                    winner_id = snapshot.get("race_winner")
                    winner = snapshot["players"].get(str(winner_id)) if winner_id is not None else None
                    if winner:
                        draw_line(f"Uzvarētājs: {winner['name']}!", 930, 650, colors["green"])
                    draw_button("game-new", "Jauna spēle  [R]", pygame.Rect(930, 690, 280, 42))
                    draw_button("game-scores", "Rezultātu tabula  [L]", pygame.Rect(930, 742, 280, 42))
                    if save_error:
                        draw_line(save_error[:45], 930, 780, colors["red"])
                if mode == "client" and client is not None and client.error:
                    draw_line(client.error[:45], 930, 780, colors["red"])

        if (
            screen_state == "game"
            and mode == "solo"
            and latest_snapshot is not None
            and (latest_snapshot.get("awaiting_next_level") or latest_snapshot.get("game_over"))
        ):
            button_rects.clear()
            overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            overlay.fill((8, 14, 20, 205))
            screen.blit(overlay, (0, 0))
            dialog = pygame.Rect(245, 220, 750, 380)
            pygame.draw.rect(screen, colors["panel"], dialog, border_radius=18)
            pygame.draw.rect(screen, colors["accent"], dialog, width=3, border_radius=18)

            if latest_snapshot.get("awaiting_next_level"):
                heading = f"{latest_snapshot['level']}. līmenis pabeigts!"
                detail = "Vari turpināt nākamo labirintu vai atgriezties izvēlnē."
                next_button = ("level-next", "Nākamais līmenis  [Enter]")
                menu_button = ("level-menu", "Atgriezties izvēlnē  [Esc]")
            else:
                heading = "Apsveicu! Visi līmeņi pabeigti!"
                detail = "Tavs rezultāts ir saglabāts score rank tabulā."
                next_button = ("solo-finish-scores", "Rezultātu tabula  [L]")
                menu_button = ("solo-finish-menu", "Atgriezties izvēlnē  [Enter]")

            heading_image = title_font.render(heading, True, colors["text"])
            screen.blit(heading_image, heading_image.get_rect(center=(620, 300)))
            detail_image = font.render(detail, True, colors["muted"])
            screen.blit(detail_image, detail_image.get_rect(center=(620, 360)))
            player_result = latest_snapshot["players"]["1"]
            result_image = font.render(
                f"Punkti: {player_result['score']}    Laiks: {format_time(float(player_result['time']))}",
                True,
                colors["accent"],
            )
            screen.blit(result_image, result_image.get_rect(center=(620, 410)))
            draw_button(next_button[0], next_button[1], pygame.Rect(300, 480, 300, 58))
            draw_button(menu_button[0], menu_button[1], pygame.Rect(640, 480, 300, 58))

        pygame.display.flip()
        clock.tick(60)

    if server is not None:
        server.close()
    if client is not None:
        client.close()
    pygame.key.stop_text_input()
    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
