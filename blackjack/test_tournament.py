import unittest
from types import SimpleNamespace

from .tournament import BotPlayer, hand_value, is_natural, make_shoe


class HandValueTests(unittest.TestCase):
    def test_face_cards_and_t_are_worth_ten(self):
        self.assertEqual(hand_value(["TH", "JD"]), 20)

    def test_ace_changes_to_one_when_hand_would_bust(self):
        self.assertEqual(hand_value(["AH", "9D", "5C"]), 15)

    def test_multiple_aces_are_adjusted_individually(self):
        self.assertEqual(hand_value(["AS", "AD", "9H"]), 21)

    def test_split_twenty_one_is_not_a_natural(self):
        hand = ["AH", "KD"]
        self.assertTrue(is_natural(hand))
        self.assertFalse(is_natural(hand, was_split=True))

    def test_shoe_has_four_cards_of_each_rank_per_deck(self):
        shoe = make_shoe(2)
        self.assertEqual(len(shoe), 104)
        self.assertEqual(shoe.count("TH"), 2)


class RoundTests(unittest.TestCase):
    class Button:
        def configure(self, **kwargs):
            pass

    class Variable:
        def get(self):
            return True

    def run_round(self, draw_order, decide_action, place_bet=None, bankroll=100):
        from .tournament import BlackjackTournament

        app = BlackjackTournament.__new__(BlackjackTournament)
        bot_module = SimpleNamespace(
            place_bet=place_bet or (lambda bankroll, history, decks_remaining: 10),
            decide_action=decide_action,
        )
        app.bots = [BotPlayer("TestBot", bot_module, bankroll)]
        app.round_number = 0
        app.settings = {
            "rounds": 2,
            "decks": 1,
            "cut_percent": 75,
        }
        filler = ["2S", "3S", "4S", "5S", "7S", "9S", "JS", "QS"]
        app.shoe = filler + list(reversed(draw_order))
        app.history = []
        app.dealer_hand = []
        app.dealer_hole_hidden = False
        app.phase = "ready"
        app.auto_running = False
        app.auto_dealer_var = self.Variable()
        app.hit_button = self.Button()
        app.stand_button = self.Button()
        app._log = lambda line: None
        app._set_status = lambda text: None
        app._refresh_scoreboard = lambda: None
        app._draw_table = lambda: None
        app.play_next_round()
        return app.bots[0], app

    def test_push_returns_the_original_bet(self):
        bot, app = self.run_round(
            ["TH", "6H", "8D", "TD", "2C"],
            lambda hand, upcard, history, can_double, can_split: "STAND",
        )
        self.assertEqual(bot.bankroll, 100)
        self.assertEqual(app.phase, "round_done")
        self.assertEqual(app.dealer_hand, ["6H", "TD", "2C"])

    def test_split_creates_and_plays_both_hands(self):
        def split_then_stand(hand, upcard, history, can_double, can_split):
            if can_split:
                return "SPLIT"
            return "STAND"

        bot, _ = self.run_round(
            ["8H", "6H", "8D", "TD", "3C", "4C", "2H"],
            split_then_stand,
        )
        self.assertEqual(len(bot.hands), 2)
        self.assertEqual([hand["cards"] for hand in bot.hands], [["8H", "3C"], ["8D", "4C"]])
        self.assertEqual(bot.bankroll, 80)

    def test_ten_and_face_card_can_be_split_by_value(self):
        can_split_values = []

        def stand(hand, upcard, history, can_double, can_split):
            can_split_values.append(can_split)
            return "STAND"

        bot, _ = self.run_round(["TH", "6H", "KD", "TD", "2C"], stand)
        self.assertTrue(can_split_values[0])
        self.assertEqual(bot.bankroll, 110)

    def test_natural_blackjack_pays_three_to_two(self):
        bot, _ = self.run_round(
            ["TH", "6H", "AH", "TD", "2C"],
            lambda hand, upcard, history, can_double, can_split: "STAND",
        )
        self.assertEqual(bot.bankroll, 115)

    def test_bets_are_clamped_to_the_rule_limits(self):
        draw_order = ["TH", "TD", "7D", "8S", "2C"]
        stand = lambda hand, upcard, history, can_double, can_split: "STAND"
        cases = ((1000, 1, 10), (1000, 500, 200), (80, 200, 80))
        for bankroll, requested_bet, expected_bet in cases:
            with self.subTest(bankroll=bankroll, requested_bet=requested_bet):
                bot, _ = self.run_round(
                    draw_order,
                    stand,
                    place_bet=lambda current, history, decks: requested_bet,
                    bankroll=bankroll,
                )
                self.assertEqual(bot.hands[0]["bet"], expected_bet)


if __name__ == "__main__":
    unittest.main()
