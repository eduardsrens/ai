import tempfile
import unittest
from pathlib import Path

from Ance_maze_game import (
    LEVEL_COUNT,
    RaceGame,
    generate_level,
    load_scores,
    ranked_scores,
    save_scores,
    shortest_path,
)


def direction_between(first, second):
    dx = second[0] - first[0]
    dy = second[1] - first[1]
    return {(0, -1): "up", (0, 1): "down", (-1, 0): "left", (1, 0): "right"}[(dx, dy)]


class MazeGameTests(unittest.TestCase):
    def test_twenty_levels_grow_and_have_reachable_exits(self):
        sizes = []
        for number in range(1, LEVEL_COUNT + 1):
            level = generate_level(number, seed=4)
            sizes.append(len(level.rows))
            self.assertIsNotNone(shortest_path(level, level.exit))
            self.assertGreaterEqual(len(level.rewards), 1)
            for reward in level.rewards:
                path = shortest_path(level, reward)
                self.assertIsNotNone(path)
                self.assertNotIn(level.exit, path)

        self.assertEqual(sizes, sorted(set(sizes)))

    def test_first_level_cannot_finish_before_one_minute(self):
        game = RaceGame(
            [{"id": 1, "name": "Ance", "avatar": "🥕"}],
            seed=8,
            started_at=0,
        )
        path = shortest_path(game.level, game.level.exit)
        self.assertIsNotNone(path)

        for step, (first, second) in enumerate(zip(path, path[1:]), start=1):
            moved = game.move(1, direction_between(first, second), now=step * 0.2)
            self.assertTrue(moved)

        game.tick(59.99)
        self.assertEqual(game.level_number, 1)
        self.assertFalse(game.players[1]["finished"])
        self.assertTrue(game.players[1]["waiting_at_exit"])

        game.tick(60)
        self.assertEqual(game.level_number, 1)
        self.assertTrue(game.awaiting_next_level)
        self.assertTrue(game.advance_level(now=60))
        self.assertEqual(game.level_number, 2)

    def test_exit_does_not_require_collecting_every_star(self):
        game = RaceGame(
            [{"id": 1, "name": "Ance", "avatar": "🥕"}],
            seed=9,
            started_at=0,
        )
        path = shortest_path(game.level, game.level.exit)
        self.assertIsNotNone(path)
        path_positions = set(path)
        uncollected_star = next(
            (x, y)
            for y, row in enumerate(game.level.rows)
            for x, cell in enumerate(row)
            if cell == " " and (x, y) not in path_positions and (x, y) != game.level.start
        )
        game.level.rewards.clear()
        game.level.rewards.add(uncollected_star)

        for step, (first, second) in enumerate(zip(path, path[1:]), start=1):
            moved = game.move(1, direction_between(first, second), now=60 + step * 0.2)
            self.assertTrue(moved)

        self.assertEqual(game.level_number, 1)
        self.assertTrue(game.awaiting_next_level)
        self.assertTrue(game.advance_level(now=60 + len(path) * 0.2))
        self.assertEqual(game.level_number, 2)
        self.assertEqual(game.players[1]["time_credit"], 0)

    def test_player_snapshot_interpolates_between_steps(self):
        game = RaceGame(
            [{"id": 1, "name": "Ance", "avatar": "🥕"}],
            seed=15,
            started_at=0,
        )
        path = shortest_path(game.level, game.level.exit)
        self.assertIsNotNone(path)
        first, second = path[0], path[1]

        self.assertTrue(game.move(1, direction_between(first, second), now=1))
        snapshot = game.snapshot(now=1.075)
        player = snapshot["players"]["1"]

        self.assertAlmostEqual(player["visual_x"], (first[0] + second[0]) / 2)
        self.assertAlmostEqual(player["visual_y"], (first[1] + second[1]) / 2)

    def test_first_finisher_gets_competition_points(self):
        game = RaceGame(
            [
                {"id": 1, "name": "Ance", "avatar": "🥕"},
                {"id": 2, "name": "Otrs", "avatar": "🥦"},
            ],
            seed=12,
            started_at=0,
        )
        path = shortest_path(game.level, game.level.exit)
        self.assertIsNotNone(path)

        for step, (first, second) in enumerate(zip(path, path[1:]), start=1):
            moved = game.move(1, direction_between(first, second), now=60 + step * 0.2)
            self.assertTrue(moved)

        self.assertEqual(game.players[1]["score"], 150)
        self.assertEqual(game.players[1]["wins"], 1)
        self.assertFalse(game.players[2]["finished"])

    def test_level_advances_after_both_competitors_finish(self):
        game = RaceGame(
            [
                {"id": 1, "name": "Ance", "avatar": "🥕"},
                {"id": 2, "name": "Otrs", "avatar": "🥦"},
            ],
            seed=14,
            started_at=0,
        )
        path = shortest_path(game.level, game.level.exit)
        self.assertIsNotNone(path)

        for player_id, start_time in ((1, 60), (2, 80)):
            for step, (first, second) in enumerate(zip(path, path[1:]), start=1):
                moved = game.move(
                    player_id,
                    direction_between(first, second),
                    now=start_time + step * 0.2,
                )
                self.assertTrue(moved)

        self.assertEqual(game.level_number, 2)
        self.assertEqual(game.players[1]["score"], 150)
        self.assertEqual(game.players[2]["score"], 100)

    def test_collecting_a_reward_subtracts_five_seconds(self):
        game = RaceGame(
            [{"id": 1, "name": "Ance", "avatar": "🥕"}],
            seed=6,
            started_at=0,
        )
        reward = next(iter(game.level.rewards))
        path = shortest_path(game.level, reward)
        self.assertIsNotNone(path)

        for step, (first, second) in enumerate(zip(path, path[1:]), start=1):
            moved = game.move(1, direction_between(first, second), now=10 + step * 0.2)
            self.assertTrue(moved)

        self.assertGreaterEqual(game.players[1]["time_credit"], 5)
        self.assertNotIn(reward, game.level.rewards)
        self.assertAlmostEqual(game.elapsed_seconds(1, now=30), 30 - game.players[1]["time_credit"])

    def test_score_results_are_saved_and_loaded(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "scores.json"
            record = {
                "name": "Ance",
                "avatar": "🥕",
                "score": 3000,
                "wins": 20,
                "time_seconds": 900.0,
                "levels_completed": LEVEL_COUNT,
            }

            save_scores([record], path)

            self.assertEqual(load_scores(path), [record])

    def test_score_rank_orders_points_then_time(self):
        records = [
            {"name": "Lēnāks", "score": 3000, "time_seconds": 400},
            {"name": "Uzvarētājs", "score": 3050, "time_seconds": 500},
            {"name": "Ātrāks", "score": 3000, "time_seconds": 350},
        ]

        self.assertEqual(
            [record["name"] for record in ranked_scores(records)],
            ["Uzvarētājs", "Ātrāks", "Lēnāks"],
        )


if __name__ == "__main__":
    unittest.main()
