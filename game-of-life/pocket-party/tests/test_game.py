from pathlib import Path
import random
import sys
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import game  # noqa: E402


class PartyTests(unittest.TestCase):
    def party(self, names=None, rounds=8):
        g = game.new_game()
        game.start(g, names or ["Sunny", "River", "Clover", "Plum"], rounds=rounds)
        return game.ready(g)

    def test_setup_and_handoff(self):
        g = game.new_game()
        with self.assertRaises(ValueError):
            game.start(g, ["A", "a"])
        with self.assertRaises(ValueError):
            game.start(g, ["A", "B"], rounds=99)
        game.start(g, ["A", "B"], rounds=5)
        self.assertEqual(g["phase"], "handoff")
        self.assertEqual(g["max_rounds"], 5)
        with self.assertRaises(ValueError):
            game.spin(g)
        game.ready(g)
        self.assertEqual(g["phase"], "playing")

    def test_one_roll_per_turn(self):
        g = self.party()
        game.spin(g, random.Random(1))
        if g["pending"]:
            game.choose(g, "skip")
        with self.assertRaises(ValueError):
            game.spin(g)
        game.end_turn(g)
        self.assertEqual(g["current"], 1)
        self.assertEqual(g["phase"], "handoff")

    def test_item_damage_shield_and_once_per_turn(self):
        g = self.party()
        g["players"][1]["shield"] = True
        game.use_item(g, "rocket", 1)
        self.assertEqual(g["players"][1]["hp"], 20)
        self.assertFalse(g["players"][1]["shield"])
        self.assertTrue(g["last_action"]["blocked"])
        with self.assertRaises(ValueError):
            game.use_item(g, "shield")

    def test_knockout_and_magnet(self):
        g = self.party()
        p = g["players"][1]
        p.update(hp=3, position=18, keys=12)
        game.use_item(g, "rocket", 1)
        self.assertEqual((p["hp"], p["position"], p["keys"]), (20, 0, 4))
        self.assertTrue(g["last_action"]["knocked_out"])
        g["used_item"] = False
        g["players"][0]["items"].append("magnet")
        game.use_item(g, "magnet", 1)
        self.assertEqual(p["keys"], 0)
        self.assertEqual(g["players"][0]["keys"], 14)

    def test_turbo_dice_rolls_two_dice(self):
        g = self.party()
        g["players"][0]["items"].append("turbo")
        game.use_item(g, "turbo")
        self.assertTrue(g["turbo"])
        rng = Mock()
        rng.randint.side_effect = [5, 6]
        game.spin(g, rng)
        self.assertEqual(g["roll"], 11)
        self.assertEqual(g["roll_dice"], [5, 6])
        self.assertEqual(g["players"][0]["position"], 11)
        self.assertFalse(g["turbo"])

    def test_chest_pass_and_purchase(self):
        g = self.party()
        g["players"][0].update(position=6, keys=20)
        rng = Mock()
        rng.randint.return_value = 2
        game.spin(g, rng)
        self.assertIsNotNone(g["pending"])
        game.choose(g, "buy")
        self.assertEqual(g["players"][0]["trophies"], 1)
        self.assertEqual(g["players"][0]["keys"], 8)

    def test_cannot_buy_without_keys(self):
        g = self.party()
        g["players"][0].update(position=6, keys=0)
        rng = Mock()
        rng.randint.return_value = 1
        game.spin(g, rng)
        with self.assertRaises(ValueError):
            game.choose(g, "buy")

    def test_roll_wraps_portal(self):
        g = self.party()
        g["players"][0]["position"] = 47
        rng = Mock()
        rng.randint.return_value = 3
        game.spin(g, rng)
        self.assertEqual(g["players"][0]["position"], 1)
        self.assertTrue(g["last_move"]["wrapped"])

    def test_reflex_minigame_scoring(self):
        g = self.party(names=["Sunny", "River"], rounds=5)
        g["round"] = 4
        g["current"] = 1
        g["rolled"] = True
        game.end_turn(g)
        self.assertEqual(g["mini"]["kind"], "reflex")
        game.ready(g)
        g["mini"]["started"] -= 6.0
        star_ids = [e["id"] for e in g["mini"]["events"] if e["kind"] == "star"][:5]
        bomb_ids = [e["id"] for e in g["mini"]["events"] if e["kind"] == "bomb"][:1]
        game.minigame(g, {"hits": star_ids + bomb_ids})
        self.assertEqual(g["mini"]["scores"][0]["score"], 40)

    def test_five_complete_parties(self):
        for seed in range(5):
            rng = random.Random(seed)
            rounds = [5, 8, 12, 8, 5][seed]
            g = self.party(rounds=rounds)
            while g["phase"] != "finished":
                if g["phase"] in ("handoff", "minigame_handoff"):
                    game.ready(g)
                elif g["phase"] == "playing":
                    game.spin(g, rng)
                    if g["pending"]:
                        game.choose(
                            g,
                            "buy" if g["players"][g["current"]]["keys"] >= 20 else "skip",
                        )
                    game.end_turn(g)
                elif g["phase"] == "minigame":
                    g["mini"]["started"] -= 6.5
                    kind = g["mini"]["kind"]
                    if kind == "memory":
                        payload = {"answer": g["mini"]["gems"].count("gold")}
                    elif kind == "reaction":
                        payload = {"elapsed": 460}
                    elif kind == "reflex":
                        stars = [e["id"] for e in g["mini"]["events"] if e["kind"] == "star"][:6]
                        payload = {"hits": stars}
                    else:
                        payload = {"taps": rng.randint(10, 40)}
                    game.minigame(g, payload)
                elif g["phase"] == "round_results":
                    game.next_round(g)
            self.assertEqual(g["round"], rounds)
            self.assertTrue(all(p["hp"] > 0 and p["keys"] >= 0 for p in g["players"]))
            self.assertGreaterEqual(sum(p["trophies"] for p in g["players"]), rounds)
            self.assertTrue(isinstance(g["awards"], list))


if __name__ == "__main__":
    unittest.main()
