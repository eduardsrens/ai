import unittest
from collections import Counter
from unittest.mock import Mock

from blackjack import (
    AUTOPLAY_BASE_BET,
    AUTOPLAY_MAX_BET,
    AUTOPLAY_ROUND_DELAY_MS,
    DECK_COUNTS,
    SHUFFLE_AFTER_CARDS,
    STARTING_TOKENS,
    TOTAL_CARDS,
    BlackjackGame,
    CardCountingBot,
    RANKS,
    build_shoe,
    needs_shuffle,
    payout_return,
    should_split_pair,
)


class CardCountingBotTests(unittest.TestCase):
    def test_accounts_for_a_hidden_dealer_card(self):
        unseen = [0] * len(RANKS)
        unseen[1] = 1
        unseen[9] = 1

        action, hit_value, stand_value, double_value = CardCountingBot(
            unseen, dealer_upcard=1
        ).analyze((9, 8))

        self.assertEqual(action, "stay")
        self.assertAlmostEqual(hit_value, 0.5)
        self.assertAlmostEqual(stand_value, 1.0)
        self.assertIsNone(double_value)

    def test_values_a_draw_from_the_remaining_shoe(self):
        unseen = [0] * len(RANKS)
        unseen[1] = 1
        unseen[2] = 1
        unseen[9] = 1

        action, hit_value, stand_value, _ = CardCountingBot(
            unseen, dealer_upcard=1
        ).analyze((9, 5))

        self.assertEqual(action, "hit")
        self.assertAlmostEqual(hit_value, 2 / 3)
        self.assertAlmostEqual(stand_value, 0.0)

    def test_analyzes_a_four_deck_shoe(self):
        unseen = list(DECK_COUNTS)
        unseen[4] -= 1
        unseen[5] -= 2

        bot = CardCountingBot(unseen, dealer_upcard=5)
        action, hit_value, stand_value, _ = bot.analyze((4, 5))

        self.assertEqual(action, "hit")
        self.assertGreaterEqual(hit_value, 0)
        self.assertLessEqual(hit_value, 1)
        self.assertGreaterEqual(stand_value, 0)
        self.assertLessEqual(stand_value, 1)
        for cached_method in (
            CardCountingBot._best_value,
            CardCountingBot._stand_value,
            CardCountingBot._dealer_outcomes,
        ):
            cache_info = cached_method.cache_info()
            self.assertEqual(cache_info.currsize, 0)

    def test_doubles_when_one_card_has_a_higher_expected_return(self):
        unseen = [0] * len(RANKS)
        unseen[9] = 2

        action, _, _, double_value = CardCountingBot(
            unseen, dealer_upcard=5
        ).analyze((4, 5), can_double=True)

        self.assertEqual(action, "double")
        self.assertGreater(double_value, 0)

    def test_selects_splitting_for_a_pair_of_eights(self):
        unseen = [0] * len(RANKS)
        unseen[9] = 2

        action, _, _, _ = CardCountingBot(
            unseen, dealer_upcard=9
        ).analyze((7, 7), can_split=True)

        self.assertEqual(action, "split")

    def test_uses_standard_pair_splitting_rules(self):
        self.assertTrue(should_split_pair((0, 0), dealer_upcard=9))
        self.assertTrue(should_split_pair((7, 7), dealer_upcard=9))
        self.assertTrue(should_split_pair((1, 1), dealer_upcard=6))
        self.assertFalse(should_split_pair((1, 1), dealer_upcard=7))
        self.assertFalse(should_split_pair((4, 4), dealer_upcard=5))


class ShoeAndTokenTests(unittest.TestCase):
    def test_builds_four_full_decks_with_expected_rank_counts(self):
        shoe = build_shoe()

        self.assertEqual(len(shoe), TOTAL_CARDS)
        self.assertEqual(
            tuple(Counter(card[0] for card in shoe)[rank] for rank in range(len(RANKS))),
            DECK_COUNTS,
        )
        self.assertEqual(SHUFFLE_AFTER_CARDS, 52)

    def test_shuffles_after_one_quarter_of_the_shoe_is_dealt(self):
        self.assertFalse(needs_shuffle(TOTAL_CARDS))
        self.assertFalse(needs_shuffle(TOTAL_CARDS - SHUFFLE_AFTER_CARDS + 1))
        self.assertTrue(needs_shuffle(TOTAL_CARDS - SHUFFLE_AFTER_CARDS))

    def test_token_returns_follow_blackjack_payouts(self):
        self.assertEqual(payout_return(10, "win"), 20)
        self.assertEqual(payout_return(10, "win", blackjack=True), 25)
        self.assertEqual(payout_return(10, "push"), 10)
        self.assertEqual(payout_return(10, "loss"), 0)


class AutoPlayTests(unittest.TestCase):
    def test_starts_a_round_with_the_default_bet_and_plays_the_bot(self):
        game = BlackjackGame.__new__(BlackjackGame)
        game.autoplay_enabled = True
        game.active = False
        game.bankroll = 1000
        game.bet_var = Mock()
        game._autoplay_bet = Mock(return_value=AUTOPLAY_BASE_BET)
        game.new_round = Mock(
            side_effect=lambda: setattr(game, "active", True)
        )
        game.play_bot = Mock()

        game._start_autoplay_round()

        game.bet_var.set.assert_called_once_with(str(AUTOPLAY_BASE_BET))
        game.new_round.assert_called_once_with()
        game.play_bot.assert_called_once_with()

    def test_scales_the_bet_up_when_the_true_count_is_positive(self):
        game = BlackjackGame.__new__(BlackjackGame)
        game.shoe = [None] * (TOTAL_CARDS - 8)
        game.seen_counts = [0] * len(RANKS)
        game.seen_counts[1] = 8
        game.bankroll = 100

        self.assertEqual(game._autoplay_bet(), 3 * AUTOPLAY_BASE_BET)

    def test_caps_the_bet_to_the_remaining_bankroll(self):
        game = BlackjackGame.__new__(BlackjackGame)
        game.shoe = [None] * TOTAL_CARDS
        game.seen_counts = [0] * len(RANKS)
        game.bankroll = 3

        self.assertEqual(game._autoplay_bet(), 3)
        self.assertEqual(AUTOPLAY_MAX_BET, 5 * AUTOPLAY_BASE_BET)

    def test_schedules_another_round_while_tokens_remain(self):
        game = BlackjackGame.__new__(BlackjackGame)
        game.autoplay_enabled = True
        game.active = False
        game.bot_running = False
        game.current_bet = 0
        game.bankroll = 100
        game.wins = 0
        game.losses = 0
        game.pushes = 0
        game.player_hands = [[8, 7]]
        game.hand_bets = [5]
        game.hand_busted = [False]
        game.hand_blackjack = [False]
        game.dealer_cards = [9, 7]
        game.root = Mock()
        game.status_var = Mock()
        game.advice_var = Mock()
        game._update_info = Mock()

        game._finish_round()

        game.root.after.assert_called_once_with(
            AUTOPLAY_ROUND_DELAY_MS, game._start_autoplay_round
        )

    def test_refills_tokens_and_shuffles_when_autoplay_runs_out(self):
        game = BlackjackGame.__new__(BlackjackGame)
        game.autoplay_enabled = True
        game.active = True
        game.bot_running = False
        game.current_bet = 5
        game.bankroll = 0
        game.wins = 0
        game.losses = 0
        game.pushes = 0
        game.player_hands = [[8, 7]]
        game.hand_bets = [5]
        game.hand_busted = [False]
        game.hand_blackjack = [False]
        game.dealer_cards = [9, 7]
        game.shoe = [(4, "♠", "5")]
        game.seen_counts = [1] * len(RANKS)
        game.root = Mock()
        game.status_var = Mock()
        game.advice_var = Mock()
        game._update_info = Mock()

        game._finish_round()

        self.assertEqual(game.bankroll, STARTING_TOKENS)
        self.assertEqual(len(game.shoe), TOTAL_CARDS)
        self.assertEqual(game.seen_counts, [0] * len(RANKS))
        self.assertEqual(game.losses, 1)
        self.assertIn("papildināti", game.status_var.set.call_args[0][0])
        game.root.after.assert_called_once_with(
            AUTOPLAY_ROUND_DELAY_MS, game._start_autoplay_round
        )


class MultiHandTests(unittest.TestCase):
    def test_bot_plays_both_hands_after_splitting(self):
        game = BlackjackGame.__new__(BlackjackGame)
        game.active = True
        game.bot_running = True
        game.autoplay_enabled = False
        game.active_hand_index = 0
        game.player_hands = [[(7, "♠", "8"), (7, "♥", "8")]]
        game.hand_bets = [5]
        game.hand_done = [False]
        game.hand_busted = [False]
        game.hand_blackjack = [False]
        game.hand_split_aces = [False]
        game.dealer_cards = [5, 9]
        game.hole_revealed = False
        game.bankroll = 95
        game.current_bet = 5
        game.wins = 0
        game.losses = 0
        game.pushes = 0
        game.shoe = [
            (2, "♦", "3"),
            (9, "♣", "10"),
            (1, "♠", "2"),
        ]
        game.seen_counts = [0] * len(RANKS)
        game.root = Mock()
        callbacks = []
        game.root.after.side_effect = lambda _, callback: callbacks.append(callback)
        game.status_var = Mock()
        game.advice_var = Mock()
        game._update_info = Mock()
        game._bot_analysis = Mock(
            side_effect=[
                ("split", 0.5, 0.5, None),
                ("stay", 0.5, 0.5, None),
                ("stay", 0.5, 0.5, None),
            ]
        )

        game._bot_step()
        callbacks.pop(0)()
        callbacks.pop(0)()

        self.assertFalse(game.active)
        self.assertEqual(len(game.player_hands), 2)
        self.assertEqual(game.losses, 2)
        self.assertEqual(game.bankroll, 90)
        self.assertEqual(game._bot_analysis.call_count, 3)

    def test_splitting_charges_a_second_bet_and_deals_both_hands(self):
        game = BlackjackGame.__new__(BlackjackGame)
        game.active = True
        game.bot_running = False
        game.active_hand_index = 0
        game.player_hands = [[(4, "♠", "5"), (4, "♥", "5")]]
        game.hand_bets = [10]
        game.hand_done = [False]
        game.hand_busted = [False]
        game.hand_blackjack = [False]
        game.hand_split_aces = [False]
        game.bankroll = 100
        game.current_bet = 10
        game.shoe = [(1, "♠", "2"), (2, "♥", "3")]
        game.seen_counts = [0] * len(RANKS)
        game._update_info = Mock()

        game.split_hand()

        self.assertEqual(game.bankroll, 90)
        self.assertEqual(game.current_bet, 20)
        self.assertEqual(game.hand_bets, [10, 10])
        self.assertEqual([len(hand) for hand in game.player_hands], [2, 2])
        self.assertEqual(game.active_hand_index, 0)

    def test_split_aces_receive_one_card_and_cannot_be_split_again(self):
        game = BlackjackGame.__new__(BlackjackGame)
        game.active = True
        game.bot_running = False
        game.active_hand_index = 0
        game.player_hands = [[(0, "♠", "A"), (0, "♥", "A")]]
        game.hand_bets = [10]
        game.hand_done = [False]
        game.hand_busted = [False]
        game.hand_blackjack = [False]
        game.hand_split_aces = [False]
        game.bankroll = 100
        game.current_bet = 10
        game.shoe = [(1, "♠", "2"), (2, "♥", "3")]
        game.seen_counts = [0] * len(RANKS)
        game._advance_hand = Mock()

        game.split_hand()

        self.assertEqual([len(hand) for hand in game.player_hands], [2, 2])
        self.assertEqual(game.hand_done, [True, True])
        self.assertFalse(game._can_split())
        self.assertFalse(game._can_double())
        game._advance_hand.assert_called_once_with()

    def test_double_deducts_the_second_bet_and_draws_one_card(self):
        game = BlackjackGame.__new__(BlackjackGame)
        game.active = True
        game.bot_running = False
        game.active_hand_index = 0
        game.player_hands = [[(4, "♠", "5"), (5, "♥", "6")]]
        game.hand_bets = [10]
        game.hand_split_aces = [False]
        game.hand_busted = [False]
        game.bankroll = 100
        game.current_bet = 10
        game.shoe = [(9, "♠", "10")]
        game.seen_counts = [0] * len(RANKS)
        game._advance_hand = Mock()

        game.double_down()

        self.assertEqual(game.bankroll, 90)
        self.assertEqual(game.current_bet, 20)
        self.assertEqual(game.hand_bets, [20])
        self.assertEqual(len(game.player_hands[0]), 3)
        game._advance_hand.assert_called_once_with()

    def test_settles_split_hands_individually(self):
        game = BlackjackGame.__new__(BlackjackGame)
        game.active = True
        game.bot_running = False
        game.autoplay_enabled = False
        game.player_hands = [[9, 8], [6, 7]]
        game.hand_bets = [10, 10]
        game.hand_busted = [False, False]
        game.hand_blackjack = [False, False]
        game.dealer_cards = [9, 7]
        game.bankroll = 80
        game.current_bet = 20
        game.wins = 0
        game.losses = 0
        game.pushes = 0
        game.status_var = Mock()
        game.advice_var = Mock()
        game._update_info = Mock()

        game._finish_round()

        self.assertEqual(game.wins, 1)
        self.assertEqual(game.losses, 1)
        self.assertEqual(game.bankroll, 100)

    def test_skips_dealer_draws_when_every_hand_busts(self):
        game = BlackjackGame.__new__(BlackjackGame)
        game.dealer_cards = [5, 9]
        game.hand_busted = [True]
        game.hole_revealed = False
        game.seen_counts = [0] * len(RANKS)
        game.shoe = [(8, "♠", "9")]
        game._update_info = Mock()
        game._finish_round = Mock()

        game._dealer_turn()

        self.assertEqual(len(game.dealer_cards), 2)
        self.assertTrue(game.hole_revealed)
        game._finish_round.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
