import random
import runpy
import tempfile
import unittest
from pathlib import Path

from blackjack_bot import (
    STARTING_BANKROLL,
    SPEED_DELAYS,
    BlackjackGame,
    BlackjackWindow,
    Card,
    Shoe,
    StrategyProfile,
    StrategyTrainer,
    TrainingData,
    basic_strategy,
    choose_action,
    hand_value,
    wager_units,
)


class FakeRoot:
    def __init__(self):
        self.jobs = {}
        self.cancelled = []
        self.next_job = 0
        self.delays = []

    def after(self, delay, callback):
        self.next_job += 1
        job = str(self.next_job)
        self.jobs[job] = callback
        self.delays.append(delay)
        return job

    def after_cancel(self, job):
        self.cancelled.append(job)
        self.jobs.pop(job, None)


class FakeButton:
    def __init__(self):
        self.text = ""

    def configure(self, text):
        self.text = text


class FakeEntry:
    def __init__(self):
        self.state = "normal"

    def configure(self, state):
        self.state = state


class FakeVariable:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class FakeLabel:
    def __init__(self):
        self.text = ""

    def configure(self, text):
        self.text = text


class AutoGame:
    def __init__(self):
        self.phase = "idle"
        self.deals = 0
        self.moves = 0
        self.bankroll = STARTING_BANKROLL
        self.base_bet = 10
        self.last_message = ""

    def deal(self):
        self.deals += 1
        self.phase = "player"
        return True

    def bot_step(self):
        self.moves += 1
        self.phase = "complete"
        return True


def auto_window() -> BlackjackWindow:
    window = BlackjackWindow.__new__(BlackjackWindow)
    window.root = FakeRoot()
    window.game = AutoGame()
    window.starting_amount_var = FakeVariable(str(STARTING_BANKROLL))
    window.speed_var = FakeVariable(3)
    window.starting_amount_entry = FakeEntry()
    window.speed_label = FakeLabel()
    window.auto_playing = False
    window._auto_job = None
    window.auto_button = FakeButton()
    window._render = lambda: None
    return window


def hand(*ranks: str) -> list[Card]:
    return [Card(rank, "S") for rank in ranks]


def rigged_game(*ranks: str, risk_level: int = 2) -> BlackjackGame:
    """A game whose next cards are `ranks`, in the order they will be drawn.

    Deal order is: player, dealer up-card, player, dealer hole card; after that,
    cards are drawn as the bot (and then the dealer) needs them. Anything past
    the rigged cards is a 7, and nothing is written to disk.
    """
    game = BlackjackGame(rng=random.Random(0), training_path=None)
    game.risk_level = risk_level
    game.shoe.cards = [Card("7", "S")] * 100 + [Card(rank, "S") for rank in reversed(ranks)]
    return game


def play_out(game: BlackjackGame) -> None:
    while game.phase == "player":
        game.bot_step()


class HandValueTests(unittest.TestCase):
    def test_ace_softens_when_total_would_bust(self):
        self.assertEqual(hand_value(hand("A", "9", "5")), (15, False))

    def test_multiple_aces_are_counted_safely(self):
        self.assertEqual(hand_value(hand("A", "A", "9")), (21, True))


class StrategyTests(unittest.TestCase):
    def test_basic_strategy_pairs_and_soft_totals(self):
        self.assertEqual(basic_strategy(hand("8", "8"), Card("10", "H")), "split")
        self.assertEqual(basic_strategy(hand("A", "7"), Card("9", "H")), "hit")
        self.assertEqual(basic_strategy(hand("10", "6"), Card("6", "H")), "stand")

    def test_count_deviation_is_enabled_only_at_higher_risk(self):
        cards = hand("10", "6")
        dealer = Card("10", "H")
        self.assertEqual(choose_action(cards, dealer, 4, 1)[0], "hit")
        action, reason = choose_action(cards, dealer, 4, 2)
        self.assertEqual(action, "stand")
        self.assertIn("Hi-Lo", reason)

    def test_strategy_profile_controls_bet_spread_and_deviation_threshold(self):
        profile = StrategyProfile(bet_trigger=1, max_bet_units=5, deviation_threshold=1)
        self.assertEqual(wager_units(4, 2, profile), 5)
        action, reason = choose_action(
            hand("10", "6"),
            Card("10", "H"),
            true_count=1,
            risk_level=2,
            deviation_threshold=profile.deviation_threshold,
        )
        self.assertEqual(action, "stand")
        self.assertIn("Hi-Lo", reason)

    def test_learned_profile_can_enable_a_validated_split_deviation(self):
        pair = hand("10", "10")
        dealer = Card("6", "H")
        self.assertEqual(choose_action(pair, dealer, 5, 2)[0], "stand")
        action, reason = choose_action(
            pair,
            dealer,
            true_count=5,
            risk_level=2,
            split_tens_threshold=5,
        )
        self.assertEqual(action, "split")
        self.assertIn("Hi-Lo", reason)

    def test_risk_changes_bet_spread_only_at_favorable_counts(self):
        self.assertEqual([wager_units(-2, level) for level in (1, 2, 3)], [1, 1, 1])
        self.assertEqual([wager_units(4, level) for level in (1, 2, 3)], [2, 3, 5])


class StrategyRegressionTests(unittest.TestCase):
    def test_soft_18_stands_when_it_cannot_double(self):
        for up in ("3", "4", "5", "6"):
            self.assertEqual(basic_strategy(hand("A", "7"), Card(up, "H")), "double")
            self.assertEqual(basic_strategy(hand("A", "7"), Card(up, "H"), can_double=False), "stand")

    def test_hard_11_hits_against_an_ace_when_dealer_stands_on_soft_17(self):
        self.assertEqual(basic_strategy(hand("9", "2"), Card("A", "H")), "hit")
        self.assertEqual(basic_strategy(hand("9", "2"), Card("10", "H")), "double")

    def test_count_deviations_never_override_a_split(self):
        for ranks, up in ((("8", "8"), "10"), (("6", "6"), "2"), (("6", "6"), "3")):
            action, reason = choose_action(hand(*ranks), Card(up, "H"), 8, 3)
            self.assertEqual((action, reason), ("split", "basic strategy"))

    def test_count_deviation_still_applies_to_unsplittable_pairs(self):
        # With no split available, 6,6 is just a hard 12.
        action, _ = choose_action(hand("6", "6"), Card("3", "H"), 8, 3, can_split=False)
        self.assertEqual(action, "stand")


class BettingTests(unittest.TestCase):
    def test_bets_are_whole_units_even_with_an_odd_bankroll(self):
        game = rigged_game("10", "9", "8", "7", risk_level=3)
        game.shoe.running_count = 40  # very high true count -> max spread
        game.bankroll = 25
        self.assertEqual(game.next_bet, 20)
        game.deal()
        self.assertEqual(game.player_hands[0].bet, 20)
        self.assertEqual(game.bankroll, 5)

    def test_next_bet_is_zero_below_the_minimum(self):
        game = BlackjackGame(training_path=None)
        game.bankroll = game.base_bet - 1
        self.assertEqual(game.next_bet, 0)

    def test_game_uses_profile_for_betting(self):
        profile = StrategyProfile(bet_trigger=1, max_bet_units=5)
        game = BlackjackGame(
            rng=random.Random(3),
            training_path=None,
            strategy_profile=profile,
        )
        game.shoe.running_count = 40
        game.bankroll = 100
        self.assertEqual(game.next_bet, 50)
        game.deal()
        self.assertEqual(game.player_hands[0].bet, 50)


class RoundTests(unittest.TestCase):
    def test_player_blackjack_pays_three_to_two(self):
        game = rigged_game("A", "9", "K", "7")
        game.deal()
        self.assertEqual(game.phase, "complete")
        self.assertEqual(game.bankroll, STARTING_BANKROLL + 15)
        self.assertEqual(game.training.total_profit, 15)

    def test_dealer_blackjack_with_insurance_breaks_even(self):
        game = rigged_game("10", "A", "9", "K", risk_level=1)
        game.shoe.running_count = 20
        game.deal()
        self.assertEqual(game.phase, "complete")
        self.assertEqual(game.insurance_bet, game.player_hands[0].bet // 2)
        self.assertEqual(game.bankroll, STARTING_BANKROLL)
        self.assertEqual(game.training.pushes, 1)

    def test_no_insurance_without_a_high_count(self):
        game = rigged_game("10", "A", "9", "6")
        game.deal()
        self.assertEqual(game.insurance_bet, 0)

    def test_double_down_wins_double_stake(self):
        game = rigged_game("6", "6", "5", "10", "10", "10")  # 11 v 6, draw 10; dealer busts
        game.deal()
        play_out(game)
        self.assertTrue(game.player_hands[0].doubled)
        self.assertEqual(game.bankroll, STARTING_BANKROLL + 20)

    def test_dealer_stands_on_soft_17(self):
        game = rigged_game("10", "A", "9", "6")
        game.deal()
        play_out(game)
        self.assertEqual(len(game.dealer), 2)
        self.assertEqual(game.bankroll, STARTING_BANKROLL + 10)

    def test_split_aces_get_one_card_and_21_after_split_is_not_blackjack(self):
        game = rigged_game("A", "6", "A", "10", "K", "9")
        game.deal()
        play_out(game)
        self.assertEqual(len(game.player_hands), 2)
        self.assertTrue(all(h.finished and h.split_aces for h in game.player_hands))
        self.assertEqual([len(h.cards) for h in game.player_hands], [2, 2])
        # Both hands beat a busted dealer at 1:1 (A+K after a split is not a 3:2 blackjack).
        self.assertEqual(game.bankroll, STARTING_BANKROLL + 20)

    def test_reshuffle_notice_survives_the_deal(self):
        game = BlackjackGame(rng=random.Random(1), training_path=None)
        game.shoe.cards = game.shoe.cards[:20]
        game.deal()
        self.assertIn("reshuffled", game.last_message)

    def test_many_random_rounds_keep_the_books_balanced(self):
        game = BlackjackGame(rng=random.Random(42), training_path=None)
        game.risk_level = 3
        for _ in range(400):
            if game.bankroll < game.base_bet:
                game.bankroll = STARTING_BANKROLL
            before = game.bankroll
            self.assertTrue(game.deal())
            play_out(game)
            self.assertEqual(game.phase, "complete")
            self.assertGreaterEqual(game.bankroll, 0)
            self.assertIsInstance(game.bankroll, int)
            self.assertLessEqual(len(game.player_hands), 4)
            self.assertTrue(game.hole_revealed)
            net = game.bankroll - before
            self.assertIn(f"Net {'-' if net < 0 else '+'}${abs(net)}.", game.last_message)
        t = game.training
        self.assertEqual(t.rounds, 400)
        self.assertEqual(t.wins + t.losses + t.pushes, 400)


class ShoeAndTrainingTests(unittest.TestCase):
    def test_hi_lo_count_and_true_count(self):
        shoe = Shoe(decks=1, rng=random.Random(3))
        shoe.count(Card("5", "S"))
        shoe.count(Card("A", "H"))
        self.assertEqual(shoe.running_count, 0)
        self.assertAlmostEqual(shoe.true_count, 0)

    def test_training_data_round_trips(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "training.json"
            record = TrainingData(rounds=3, wins=1, losses=2, actions=8, total_profit=-10)
            record.save(path)
            self.assertEqual(TrainingData.load(path), record)

    def test_strategy_profile_round_trips(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "strategy.json"
            profile = StrategyProfile(1, 5, 3, 5)
            profile.save(path)
            self.assertEqual(StrategyProfile.load(path), profile)

    def test_strategy_trainer_validates_on_separate_seeds(self):
        baseline = StrategyProfile()
        challenger = StrategyProfile(1, 5, 1)
        trainer = StrategyTrainer(
            rounds_per_seed=20,
            training_seeds=(11, 12),
            validation_seeds=(21, 22),
            candidates=(baseline, challenger),
        )
        result = trainer.train(baseline)
        self.assertIn(result.profile, (baseline, challenger))
        self.assertIn(result.simulated_rounds, (80, 160))

    def test_corrupt_training_file_is_set_aside_not_fatal(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "training.json"
            path.write_text("{not json", encoding="utf-8")
            self.assertEqual(TrainingData.load(path), TrainingData())
            self.assertTrue(path.with_suffix(".json.corrupt").exists())

    def test_wrong_typed_training_values_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "training.json"
            path.write_text('{"rounds": "many"}', encoding="utf-8")
            self.assertEqual(TrainingData.load(path), TrainingData())

    def test_game_saves_to_its_own_path_and_survives_save_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "training.json"
            game = BlackjackGame(rng=random.Random(5), training_path=path)
            game.deal()
            play_out(game)
            self.assertEqual(TrainingData.load(path).rounds, 1)

            broken = BlackjackGame(rng=random.Random(5), training_path=Path(directory) / "no" / "dir.json")
            broken.deal()
            play_out(broken)
            self.assertEqual(broken.phase, "complete")
            self.assertIn("could not save", broken.save_error)


class AutoPlayTests(unittest.TestCase):
    def test_start_uses_validated_starting_amount(self):
        window = auto_window()
        window.starting_amount_var.value = "250"
        window._toggle_auto()
        self.assertEqual(window.game.bankroll, 250)
        self.assertEqual(window.game.deals, 1)
        self.assertEqual(window.starting_amount_entry.state, "disabled")

    def test_invalid_starting_amount_does_not_start(self):
        window = auto_window()
        window.starting_amount_var.value = "not an amount"
        window._toggle_auto()
        self.assertFalse(window.auto_playing)
        self.assertEqual(window.game.deals, 0)
        self.assertIn("whole number", window.game.last_message)

    def test_start_does_not_reset_a_paused_hand(self):
        window = auto_window()
        window.game.phase = "player"
        window.game.bankroll = 425
        window.starting_amount_var.value = "900"
        window._toggle_auto()
        self.assertEqual(window.game.bankroll, 425)
        self.assertEqual(window.game.deals, 0)

    def test_start_runs_consecutive_hands_and_stop_cancels_next_step(self):
        window = auto_window()
        window._toggle_auto()
        self.assertEqual((window.game.deals, window.game.moves), (1, 0))
        self.assertEqual(window.auto_button.text, "Stop")
        self.assertEqual(len(window.root.jobs), 1)
        self.assertEqual(window.root.delays[-1], int(SPEED_DELAYS[2] * 1000))

        next_job = next(iter(window.root.jobs))
        next_step = window.root.jobs.pop(next_job)
        next_step()
        self.assertEqual((window.game.deals, window.game.moves), (1, 1))
        next_job = next(iter(window.root.jobs))
        next_step = window.root.jobs.pop(next_job)
        next_step()
        self.assertEqual((window.game.deals, window.game.moves), (2, 1))
        self.assertEqual(len(window.root.jobs), 1)

        window._toggle_auto()
        self.assertFalse(window.auto_playing)
        self.assertEqual(window.auto_button.text, "Start")
        self.assertEqual(window.starting_amount_entry.state, "normal")
        self.assertEqual(window.root.cancelled, ["3"])
        self.assertEqual(window.root.jobs, {})

    def test_speed_options_use_requested_slow_and_fast_endpoints(self):
        for selected_speed, expected_delay in ((1, 1000), (5, 250)):
            window = auto_window()
            window.speed_var.value = selected_speed
            window._toggle_auto()
            self.assertEqual(window.root.delays, [expected_delay])


class FinalBotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bot = runpy.run_path(str(Path(__file__).with_name("final bot.py")))

    def test_tournament_action_uses_count_and_obeys_legal_actions(self):
        action = self.bot["choose_action"](
            {
                "player_hand": ["10S", "6H"],
                "dealer_upcard": "10D",
                "true_count": 2,
                "legal_actions": ["hit", "stand"],
            }
        )
        self.assertEqual(action, "stand")

    def test_tournament_bet_uses_embedded_profile_and_bankroll(self):
        bet = self.bot["choose_bet"](
            {"bankroll": 1000, "base_bet": 10, "true_count": 4}
        )
        self.assertEqual(bet, 30)

    def test_final_bot_embeds_four_deck_profile_and_stats_snapshot(self):
        self.assertEqual(self.bot["DECKS"], 4)
        self.assertEqual(self.bot["HISTORICAL_STATS"]["rounds"], 644)
        self.assertEqual(self.bot["STRATEGY_SETTINGS"]["split_tens_threshold"], 99)


if __name__ == "__main__":
    unittest.main()
