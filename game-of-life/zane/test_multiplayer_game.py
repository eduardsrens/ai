import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from game_of_life import (
    GameOfLife,
    MULTIPLAYER_FACTS,
    MULTIPLAYER_LOSS_MESSAGES,
    MULTIPLAYER_WIN_MESSAGES,
    PLAYER_COLORS,
    REACTION_EMOJIS,
    RECONNECT_TIMEOUT_SECONDS,
    GameRoom,
)


class EraserShortcutTests(unittest.TestCase):
    class Variable:
        def __init__(self, value):
            self.value = value

        def get(self):
            return self.value

        def set(self, value):
            self.value = value

    def test_e_toggles_the_eraser_for_solo_and_multiplayer(self):
        solo = SimpleNamespace(
            current_screen="game",
            tool_var=self.Variable("pencil"),
            _set_tool=lambda: None,
        )
        self.assertEqual(GameOfLife._toggle_eraser(solo), "break")
        self.assertEqual(solo.tool_var.get(), "eraser")
        GameOfLife._toggle_eraser(solo)
        self.assertEqual(solo.tool_var.get(), "pencil")

        multiplayer = SimpleNamespace(
            current_screen="multiplayer_game",
            mp_erase_var=self.Variable(False),
            _draw_multiplayer_board=lambda: None,
        )
        GameOfLife._toggle_eraser(multiplayer)
        self.assertTrue(multiplayer.mp_erase_var.get())

    def test_shift_modifier_temporarily_erases_solo_cells(self):
        event = SimpleNamespace(state=0x0001)
        self.assertTrue(GameOfLife._shift_held(event))

        game = SimpleNamespace(
            tool_var=self.Variable("pencil"),
            live_cells={(3, 4)},
            cell_colors={(3, 4): "#ffffff"},
        )
        GameOfLife._paint_cell(game, (3, 4), shift_held=True)

        self.assertNotIn((3, 4), game.live_cells)
        self.assertNotIn((3, 4), game.cell_colors)


class ReactionTests(unittest.TestCase):
    def test_reaction_is_shared_and_expires(self):
        room = GameRoom("1v1", 10, "123456")
        host = room.join("Host", "123456", PLAYER_COLORS[0])
        room.join("Guest", "123456", PLAYER_COLORS[1])

        room.react(host["token"], "happy")
        self.assertEqual(
            room.state()["reactions"],
            [{"player_index": host["player_index"], "emoji": REACTION_EMOJIS["happy"]}],
        )

        room.reactions[host["player_index"]]["expires_at"] = 0
        self.assertEqual(room.state()["reactions"], [])

    def test_reaction_rejects_unknown_emotions(self):
        room = GameRoom("1v1", 10, "123456")
        host = room.join("Host", "123456", PLAYER_COLORS[0])
        room.join("Guest", "123456", PLAYER_COLORS[1])

        with self.assertRaisesRegex(ValueError, "supported reaction"):
            room.react(host["token"], "surprised")


class MultiplayerResultPresentationTests(unittest.TestCase):
    def test_result_uses_randomized_outcome_text_and_fact_once(self):
        state = {
            "winner": 0,
            "players": [
                {"team": 0, "index": 0},
                {"team": 1, "index": 1},
            ],
        }
        cases = (
            (0, MULTIPLAYER_WIN_MESSAGES),
            (1, MULTIPLAYER_LOSS_MESSAGES),
        )

        for player_index, messages in cases:
            with self.subTest(player_index=player_index):
                chosen_message = messages[0]
                chosen_fact = MULTIPLAYER_FACTS[0]
                game = SimpleNamespace(
                    current_screen="multiplayer_game",
                    multiplayer_client=SimpleNamespace(
                        player_index=player_index
                    ),
                    multiplayer_result_frame=object(),
                    _next_multiplayer_fact=Mock(return_value=chosen_fact),
                    mp_result_outcome=Mock(),
                    mp_result_heading=Mock(),
                    mp_result_fact=Mock(),
                )

                def show_screen(frame, screen):
                    game.current_screen = screen
                    game.shown_screen = (frame, screen)

                game._show_screen = show_screen
                with patch(
                    "game_of_life.random.choice",
                    return_value=chosen_message,
                ) as choose:
                    GameOfLife._show_multiplayer_result(game, state)
                    GameOfLife._show_multiplayer_result(game, state)

                self.assertEqual(
                    game.mp_result_outcome.configure.call_args.kwargs,
                    {
                        "text": (
                            "YOU WIN!"
                            if player_index == 0
                            else "YOU LOSE!"
                        )
                    },
                )
                self.assertEqual(
                    game.mp_result_heading.configure.call_args.kwargs,
                    {"text": chosen_message},
                )
                self.assertEqual(
                    game.mp_result_fact.configure.call_args.kwargs,
                    {"text": f"Random fact: {chosen_fact}"},
                )
                choose.assert_called_once_with(messages)
                game._next_multiplayer_fact.assert_called_once_with()
                self.assertEqual(
                    game.shown_screen,
                    (game.multiplayer_result_frame, "multiplayer_result"),
                )

    def test_fact_bag_uses_each_fact_before_reshuffling(self):
        self.assertEqual(len(MULTIPLAYER_FACTS), 105)
        game = SimpleNamespace(mp_fact_bag=[])
        with patch(
            "game_of_life.random.sample",
            side_effect=[list(MULTIPLAYER_FACTS), list(MULTIPLAYER_FACTS)],
        ) as shuffle:
            facts = [
                GameOfLife._next_multiplayer_fact(game)
                for _ in MULTIPLAYER_FACTS
            ]
            self.assertEqual(len(set(facts)), 105)
            self.assertEqual(set(facts), set(MULTIPLAYER_FACTS))
            self.assertEqual(shuffle.call_count, 1)

            GameOfLife._next_multiplayer_fact(game)
            self.assertEqual(shuffle.call_count, 2)


class GameEndScoringTests(unittest.TestCase):
    def create_room(self, mode="1v1"):
        room = GameRoom(mode, 1, "123456")
        player_count = 2 if mode == "1v1" else 4
        for index in range(player_count):
            room.join(f"Player {index + 1}", "123456", PLAYER_COLORS[index])
        room.phase = "action"
        return room

    def test_timeout_winner_has_most_cells_in_owned_territory(self):
        room = self.create_room()
        room.cells = {
            (5, 5): PLAYER_COLORS[0],
            (40, 5): PLAYER_COLORS[1],
            (41, 5): PLAYER_COLORS[1],
        }
        room.started_at = 0

        state = room.state()

        self.assertEqual(state["phase"], "finished")
        self.assertEqual(state["winner"], 1)
        self.assertIn("wins by cell count.", state["message"])

    def test_timeout_tie_uses_previous_generation_then_host(self):
        room = self.create_room()
        room.cells = {
            (5, 5): PLAYER_COLORS[0],
            (6, 5): PLAYER_COLORS[0],
            (40, 5): PLAYER_COLORS[1],
            (41, 5): PLAYER_COLORS[1],
        }
        room.previous_generation_scores = {0: 1, 1: 2}
        room.started_at = 0

        self.assertEqual(room.state()["winner"], 1)

        host_tie_room = self.create_room()
        host_tie_room.cells = {
            (5, 5): PLAYER_COLORS[0],
            (6, 5): PLAYER_COLORS[0],
            (40, 5): PLAYER_COLORS[1],
            (41, 5): PLAYER_COLORS[1],
        }
        host_tie_room.previous_generation_scores = {0: 2, 1: 2}
        host_tie_room.started_at = 0
        self.assertEqual(host_tie_room.state()["winner"], 0)

    def test_simultaneous_elimination_uses_previous_generation_score(self):
        room = self.create_room()
        room.cells = {
            (5, 5): PLAYER_COLORS[0],
            (40, 5): PLAYER_COLORS[1],
            (41, 5): PLAYER_COLORS[1],
        }

        room._advance_life()

        self.assertEqual(room.phase, "finished")
        self.assertEqual(room.winner, 1)
        self.assertNotIn("draw", room.message.lower())

    def test_two_on_two_cell_score_sums_teammate_territories(self):
        room = self.create_room("2v2")
        room.cells = {
            (1, 1): PLAYER_COLORS[0],
            (2, 1): PLAYER_COLORS[0],
            (40, 1): PLAYER_COLORS[1],
            (1, 40): PLAYER_COLORS[2],
            (2, 40): PLAYER_COLORS[2],
            (40, 40): PLAYER_COLORS[3],
        }

        self.assertEqual(room._team_cell_counts(), {0: 4, 1: 2})
        room.started_at = 0
        self.assertEqual(room.state()["winner"], 0)


class GameRoomBotTests(unittest.TestCase):
    def test_expanded_cells_per_turn_cap(self):
        room = GameRoom("1v1", 10, "123456", max_turn_cells=20)
        self.assertEqual(room.state()["max_turn_cells"], 20)
        with self.assertRaisesRegex(ValueError, "between 1 and 20"):
            GameRoom("1v1", 10, "123456", max_turn_cells=21)

    def test_host_selected_cells_per_turn_limit_is_enforced_and_shared(self):
        room = GameRoom("1v1", 10, "123456", max_turn_cells=2)
        host = room.join("Host", "123456", PLAYER_COLORS[0])
        room.join("Guest", "123456", PLAYER_COLORS[1])
        room.phase = "action"

        self.assertEqual(room.state()["max_turn_cells"], 2)
        with self.assertRaisesRegex(ValueError, "at most 2 cells"):
            room.submit_stroke(
                host["token"],
                [[5, 5], [6, 5], [7, 5]],
                round_number=0,
            )

        room.submit_stroke(
            host["token"], [[5, 5], [6, 5]], round_number=0
        )
        self.assertEqual(len(room.round_submissions[host["player_index"]]["cells"]), 2)

    def test_test_server_adds_robot_and_advances_after_player_turn(self):
        room = GameRoom("1v1", 10, "123456", bot_enabled=True)
        joined = room.join("Player", "123456")

        self.assertEqual(joined["state"]["phase"], "setup")
        self.assertEqual(
            [player["name"] for player in joined["state"]["players"]],
            ["Player", "Robot 1"],
        )

        token = joined["token"]
        room.submit_stroke(
            token,
            [[5, 5], [6, 5], [5, 6], [6, 6]],
            round_number=0,
        )
        room.start(token)
        self.assertTrue(any(x >= room.width // 2 for x, _y in room.cells))

        with patch("game_of_life.random.random", return_value=1.0):
            with patch("game_of_life.random.sample", return_value=[]):
                room.submit_stroke(token, [], round_number=1)
        state = room.state()

        self.assertEqual(state["phase"], "action")
        self.assertEqual(state["round"], 2)
        self.assertEqual(state["submitted_players"], [])
        self.assertTrue(all(player["alive"] for player in state["players"]))

    def test_test_server_fills_both_teams_in_two_on_two(self):
        room = GameRoom("2v2", 10, "123456", bot_enabled=True)

        joined = room.join("Player", "123456")
        self.assertEqual(joined["state"]["phase"], "setup")
        self.assertEqual(
            [player["name"] for player in joined["state"]["players"]],
            ["Player", "Robot 1", "Robot 2", "Robot 3"],
        )
        self.assertEqual(
            {player["team"] for player in joined["state"]["players"]}, {0, 1}
        )
        self.assertEqual(
            len({player["color"] for player in joined["state"]["players"]}), 4
        )
        room.start(joined["token"])
        cells_by_area = {
            area: sum(
                room._territory(*point) == area
                for point in room.cells
            )
            for area in range(4)
        }
        self.assertEqual(cells_by_area, {0: 0, 1: 5, 2: 5, 3: 5})

    def test_room_uses_host_selected_setup_and_time_limits(self):
        room = GameRoom(
            "1v1",
            10,
            "123456",
            bot_enabled=True,
            max_setup_cells=2,
            round_time_limit_seconds=8,
            game_time_limit_seconds=120,
        )
        joined = room.join("Player", "123456")

        self.assertEqual(joined["state"]["max_setup_cells"], 2)
        self.assertEqual(joined["state"]["round_time_limit_seconds"], 8)
        self.assertEqual(joined["state"]["game_time_limit_seconds"], 120)
        room.submit_stroke(
            joined["token"], [[5, 5], [6, 5]], round_number=0
        )
        with self.assertRaisesRegex(ValueError, "at most 2 cells"):
            room.submit_stroke(
                joined["token"],
                [[5, 6]],
                round_number=0,
            )

    def test_setup_eraser_only_removes_cells_from_players_own_area(self):
        room = GameRoom("1v1", 10, "123456", bot_enabled=True)
        joined = room.join("Player", "123456", PLAYER_COLORS[0])
        token = joined["token"]
        room.submit_stroke(token, [[5, 5], [6, 5]], round_number=0)

        room.erase_cells(token, [[5, 5]], round_number=0)

        self.assertEqual(set(room.cells), {(6, 5)})
        with self.assertRaisesRegex(ValueError, "own territory"):
            room.erase_cells(token, [[40, 5]], round_number=0)

    def test_disconnected_player_can_rejoin_the_same_slot(self):
        room = GameRoom("1v1", 10, "123456")
        host = room.join("Host", "123456", PLAYER_COLORS[0])
        guest = room.join("Guest", "123456", PLAYER_COLORS[1])
        room.submit_stroke(
            host["token"], [[5, 5], [6, 5], [5, 6], [6, 6]], round_number=0
        )
        room.submit_stroke(
            guest["token"], [[45, 5], [46, 5], [45, 6], [46, 6]], round_number=0
        )
        room.start(host["token"])
        room.leave(guest["token"])

        rejoined = room.join("Guest", "123456", PLAYER_COLORS[1])

        self.assertEqual(rejoined["player_index"], guest["player_index"])
        self.assertNotEqual(rejoined["token"], guest["token"])
        self.assertTrue(
            rejoined["state"]["players"][guest["player_index"]]["alive"]
        )
        self.assertTrue(
            rejoined["state"]["players"][guest["player_index"]]["connected"]
        )
        room.submit_stroke(rejoined["token"], [], round_number=1)
        room.submit_stroke(host["token"], [], round_number=1)
        state = room.state()

        self.assertEqual(state["round"], 2)

    def test_inactive_player_is_disconnected_and_can_rejoin(self):
        room = GameRoom("1v1", 10, "123456")
        host = room.join("Host", "123456", PLAYER_COLORS[0])
        guest = room.join("Guest", "123456", PLAYER_COLORS[1])
        guest_player = room.players[guest["player_index"]]
        guest_player["last_seen"] -= RECONNECT_TIMEOUT_SECONDS + 1

        state = room.state()
        self.assertFalse(state["players"][guest["player_index"]]["connected"])

        rejoined = room.join("Guest", "123456", PLAYER_COLORS[1])

        self.assertEqual(rejoined["player_index"], guest["player_index"])
        self.assertTrue(
            rejoined["state"]["players"][guest["player_index"]]["connected"]
        )
        self.assertNotEqual(rejoined["token"], guest["token"])
        self.assertTrue(room.state()["players"][host["player_index"]]["connected"])

    def test_player_colors_must_be_unique(self):
        self.assertEqual(len(PLAYER_COLORS), 10)
        self.assertEqual(len(set(PLAYER_COLORS)), 10)
        room = GameRoom("1v1", 10, "123456")
        room.join("Host", "123456", PLAYER_COLORS[0])

        with self.assertRaisesRegex(ValueError, "already taken"):
            room.join("Guest", "123456", PLAYER_COLORS[0])

    def test_regular_room_still_waits_for_another_player(self):
        room = GameRoom("1v1", 10, "123456")

        state = room.join("Player", "123456")["state"]

        self.assertEqual(state["phase"], "lobby")
        self.assertEqual([player["name"] for player in state["players"]], ["Player"])

if __name__ == "__main__":
    unittest.main()
