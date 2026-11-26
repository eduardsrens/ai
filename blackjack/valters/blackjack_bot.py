"""A small Tkinter blackjack game with a card-counting basic-strategy bot."""

from __future__ import annotations

import json
import math
import queue
import random
import threading
from dataclasses import dataclass
from pathlib import Path

try:  # The game logic and tests must work without a GUI toolkit.
    import tkinter as tk
    from tkinter import ttk
except ImportError:  # pragma: no cover - depends on the Python installation
    tk = ttk = None


RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
SUITS = ("S", "H", "D", "C")
TRAINING_FILE = Path(__file__).with_name("blackjack_training.json")
STRATEGY_FILE = Path(__file__).with_name("blackjack_strategy.json")
STARTING_BANKROLL = 1000
SPEED_DELAYS = (1.0, 0.8125, 0.625, 0.4375, 0.25)
SIMULATION_BANKROLL = 1_000_000


@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"

    @property
    def value(self) -> int:
        if self.rank == "A":
            return 11
        if self.rank in ("K", "Q", "J"):
            return 10
        return int(self.rank)

    @property
    def hi_lo_value(self) -> int:
        if self.rank in ("2", "3", "4", "5", "6"):
            return 1
        if self.rank in ("10", "J", "Q", "K", "A"):
            return -1
        return 0


def hand_value(cards: list[Card]) -> tuple[int, bool]:
    total = sum(card.value for card in cards)
    aces = sum(card.rank == "A" for card in cards)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total, aces > 0


def is_natural(cards: list[Card]) -> bool:
    return len(cards) == 2 and hand_value(cards)[0] == 21


def _dealer_value(card: Card) -> int:
    return 11 if card.rank == "A" else min(card.value, 10)


@dataclass(frozen=True)
class StrategyProfile:
    bet_trigger: int = 2
    max_bet_units: int = 3
    deviation_threshold: int = 2
    split_tens_threshold: int = 99

    def __post_init__(self) -> None:
        if any(
            type(value) is not int
            for value in (
                self.bet_trigger,
                self.max_bet_units,
                self.deviation_threshold,
                self.split_tens_threshold,
            )
        ):
            raise ValueError("strategy settings must be integers")
        if self.bet_trigger not in (1, 2, 3):
            raise ValueError("bet_trigger must be between 1 and 3")
        if self.max_bet_units not in (2, 3, 4, 5):
            raise ValueError("max_bet_units must be between 2 and 5")
        if self.deviation_threshold not in (1, 2, 3):
            raise ValueError("deviation_threshold must be between 1 and 3")
        if self.split_tens_threshold not in (4, 5, 6, 99):
            raise ValueError("split_tens_threshold must be 4, 5, 6, or 99")

    @classmethod
    def load(cls, path: Path = STRATEGY_FILE) -> StrategyProfile:
        if not path.exists():
            return cls()
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError as error:
            raise ValueError(f"saved strategy is not valid JSON: {error}") from error
        if not isinstance(data, dict):
            raise ValueError("saved strategy must contain a JSON object")
        try:
            return cls(
                bet_trigger=data["bet_trigger"],
                max_bet_units=data["max_bet_units"],
                deviation_threshold=data["deviation_threshold"],
                split_tens_threshold=data.get("split_tens_threshold", 99),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"saved strategy values are invalid: {error}") from error

    def save(self, path: Path = STRATEGY_FILE) -> None:
        temporary_path = path.with_suffix(path.suffix + ".tmp")
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(
                {
                    "bet_trigger": self.bet_trigger,
                    "max_bet_units": self.max_bet_units,
                    "deviation_threshold": self.deviation_threshold,
                    "split_tens_threshold": self.split_tens_threshold,
                },
                file,
                indent=2,
            )
        temporary_path.replace(path)


def basic_strategy(
    cards: list[Card],
    dealer_upcard: Card,
    can_double: bool = True,
    can_split: bool = True,
) -> str:
    """Return a basic-strategy action for 6-deck, S17, double-after-split rules."""
    total, soft = hand_value(cards)
    dealer = _dealer_value(dealer_upcard)

    if can_split and len(cards) == 2 and cards[0].value == cards[1].value:
        pair = cards[0].value
        if pair in (11, 8):
            return "split"
        if pair == 9:
            return "split" if dealer in (2, 3, 4, 5, 6, 8, 9) else "stand"
        if pair == 7:
            return "split" if dealer <= 7 else "hit"
        if pair == 6:
            return "split" if dealer <= 6 else "hit"
        if pair in (2, 3):
            return "split" if dealer <= 7 else "hit"
        if pair == 4:
            return "split" if dealer in (5, 6) else "hit"
        if pair == 5:
            if can_double and 2 <= dealer <= 9:
                return "double"
            return "hit"
        if pair == 10:
            return "stand"

    if soft:
        if total >= 19:
            return "stand"
        if total == 18:
            if 3 <= dealer <= 6:
                return "double" if can_double else "stand"
            return "stand" if dealer in (2, 7, 8) else "hit"
        if total == 17 and can_double and 3 <= dealer <= 6:
            return "double"
        if total in (15, 16) and can_double and 4 <= dealer <= 6:
            return "double"
        if total in (13, 14) and can_double and 5 <= dealer <= 6:
            return "double"
        return "hit"

    if total >= 17:
        return "stand"
    if 13 <= total <= 16:
        return "stand" if 2 <= dealer <= 6 else "hit"
    if total == 12:
        return "stand" if 4 <= dealer <= 6 else "hit"
    if can_double and total == 11 and dealer <= 10:
        return "double"  # vs an ace, S17 basic strategy hits 11
    if can_double and total == 10 and 2 <= dealer <= 9:
        return "double"
    if can_double and total == 9 and 3 <= dealer <= 6:
        return "double"
    return "hit"


def choose_action(
    cards: list[Card],
    dealer_upcard: Card,
    true_count: float,
    risk_level: int,
    can_double: bool = True,
    can_split: bool = True,
    deviation_threshold: int | None = None,
    split_tens_threshold: int = 99,
) -> tuple[str, str]:
    """Apply a few Hi-Lo index plays to basic strategy, at higher risk levels only."""
    action = basic_strategy(cards, dealer_upcard, can_double, can_split)
    total, soft = hand_value(cards)
    dealer = _dealer_value(dealer_upcard)
    if (
        risk_level >= 2
        and can_split
        and len(cards) == 2
        and cards[0].value == cards[1].value == 10
        and dealer in (5, 6)
        and split_tens_threshold < 99
        and true_count >= split_tens_threshold
    ):
        return "split", "Hi-Lo deviation: split tens against a weak dealer upcard"
    if risk_level < 2 or soft or len(cards) < 2 or action == "split":
        return action, "basic strategy"

    threshold = deviation_threshold if deviation_threshold is not None else (1 if risk_level == 3 else 2)
    if total == 16 and dealer == 10 and true_count >= threshold:
        return "stand", "Hi-Lo deviation: stand on 16 vs 10 at a high count"
    if total == 15 and dealer == 10 and true_count >= threshold + 2:
        return "stand", "Hi-Lo deviation: stand on 15 vs 10 at a high count"
    if total == 12 and dealer in (2, 3) and true_count >= threshold + (1 if dealer == 2 else 0):
        return "stand", "Hi-Lo deviation: stand on 12 at a high count"
    if total == 10 and dealer == 10 and can_double and true_count >= threshold + 2:
        return "double", "Hi-Lo deviation: double 10 vs 10 at a high count"
    return action, "basic strategy"


def wager_units(
    true_count: float,
    risk_level: int,
    profile: StrategyProfile | None = None,
) -> int:
    """Scale the base wager only when the count favors the player."""
    if profile is None:
        settings = {
            1: (3, 2),
            2: (2, 3),
            3: (1, 5),
        }
        trigger, cap = settings[risk_level]
    else:
        trigger, cap = profile.bet_trigger, profile.max_bet_units
    return min(cap, 1 + max(0, math.floor(true_count - trigger + 1)))


@dataclass(frozen=True)
class StrategyTrainingResult:
    profile: StrategyProfile
    improved: bool
    simulated_rounds: int
    validation_mean_gain: float
    validation_lower_bound: float


class StrategyTrainer:
    """Compare bounded strategy profiles in simulation and validate on fresh seeds."""

    CANDIDATES = (
        StrategyProfile(),
        StrategyProfile(1, 3, 2),
        StrategyProfile(3, 2, 2),
        StrategyProfile(2, 5, 2),
        StrategyProfile(2, 3, 1),
        StrategyProfile(2, 3, 3),
        StrategyProfile(1, 5, 1),
        StrategyProfile(2, 3, 2, 4),
        StrategyProfile(2, 3, 2, 5),
    )

    def __init__(
        self,
        rounds_per_seed: int = 2000,
        training_seeds: tuple[int, ...] | None = None,
        validation_seeds: tuple[int, ...] | None = None,
        candidates: tuple[StrategyProfile, ...] | None = None,
    ):
        if rounds_per_seed < 1:
            raise ValueError("rounds_per_seed must be positive")
        self.rounds_per_seed = rounds_per_seed
        seed_source = random.SystemRandom()
        self.training_seeds = training_seeds or tuple(
            seed_source.randrange(1 << 32) for _ in range(4)
        )
        if validation_seeds is None:
            training_seed_set = set(self.training_seeds)
            validation_seed_list = []
            while len(validation_seed_list) < 4:
                seed = seed_source.randrange(1 << 32)
                if seed not in training_seed_set and seed not in validation_seed_list:
                    validation_seed_list.append(seed)
            validation_seeds = tuple(validation_seed_list)
        self.validation_seeds = validation_seeds
        if not self.training_seeds or not self.validation_seeds:
            raise ValueError("training and validation require at least one random seed each")
        self.candidates = candidates or self.CANDIDATES

    def train(self, incumbent: StrategyProfile) -> StrategyTrainingResult:
        candidates = tuple(dict.fromkeys((*self.candidates, incumbent)))
        training_scores = {
            profile: self._score(profile, self.training_seeds)
            for profile in candidates
        }
        challenger = max(candidates, key=training_scores.__getitem__)
        if challenger == incumbent:
            return StrategyTrainingResult(
                incumbent, False, self._training_round_count(candidates), 0.0, 0.0
            )

        paired_gains = []
        incumbent_score = 0.0
        challenger_score = 0.0
        for seed in self.validation_seeds:
            old_result = self._simulate_seed(incumbent, seed)
            new_result = self._simulate_seed(challenger, seed)
            old_rate = old_result / self.rounds_per_seed
            new_rate = new_result / self.rounds_per_seed
            incumbent_score += old_rate
            challenger_score += new_rate
            paired_gains.append(new_rate - old_rate)

        sample_count = len(paired_gains)
        mean_gain = sum(paired_gains) / sample_count
        if sample_count > 1:
            variance = sum((gain - mean_gain) ** 2 for gain in paired_gains) / (sample_count - 1)
            standard_error = math.sqrt(variance / sample_count)
        else:
            standard_error = float("inf")
        lower_bound = mean_gain - 1.96 * standard_error
        rounds = self._training_round_count(candidates) + 2 * len(self.validation_seeds) * self.rounds_per_seed
        if mean_gain > 0 and lower_bound > 0:
            return StrategyTrainingResult(challenger, True, rounds, mean_gain, lower_bound)
        return StrategyTrainingResult(incumbent, False, rounds, mean_gain, lower_bound)

    def _training_round_count(self, candidates: tuple[StrategyProfile, ...]) -> int:
        return len(candidates) * len(self.training_seeds) * self.rounds_per_seed

    def _score(self, profile: StrategyProfile, seeds: tuple[int, ...]) -> float:
        scores = [
            self._simulate_seed(profile, seed) / self.rounds_per_seed
            for seed in seeds
        ]
        return sum(scores) / len(scores)

    def _simulate_seed(self, profile: StrategyProfile, seed: int) -> int:
        game = BlackjackGame(
            rng=random.Random(seed),
            training_path=None,
            strategy_profile=profile,
        )
        game.bankroll = SIMULATION_BANKROLL
        for _ in range(self.rounds_per_seed):
            if not game.deal():
                raise RuntimeError("Strategy simulation ran out of bankroll.")
            while game.phase == "player":
                game.bot_step()
        return game.training.total_profit


class Shoe:
    def __init__(self, decks: int = 6, rng: random.Random | None = None):
        self.decks = decks
        self.rng = rng or random.Random()
        self.cards: list[Card] = []
        self.running_count = 0
        self.shuffle()

    def shuffle(self) -> None:
        self.cards = [
            Card(rank, suit)
            for _ in range(self.decks)
            for suit in SUITS
            for rank in RANKS
        ]
        self.rng.shuffle(self.cards)
        self.running_count = 0

    def draw(self) -> Card:
        if not self.cards:
            raise RuntimeError("The shoe is empty; it must be shuffled before dealing.")
        return self.cards.pop()

    def count(self, card: Card) -> None:
        self.running_count += card.hi_lo_value

    @property
    def true_count(self) -> float:
        decks_remaining = max(len(self.cards) / 52, 0.25)
        return self.running_count / decks_remaining

    @property
    def cut_card_reached(self) -> bool:
        return len(self.cards) < self.decks * 52 * 0.25


@dataclass
class Hand:
    cards: list[Card]
    bet: int
    split_hand: bool = False
    split_aces: bool = False
    finished: bool = False
    doubled: bool = False


@dataclass
class TrainingData:
    rounds: int = 0
    wins: int = 0
    losses: int = 0
    pushes: int = 0
    actions: int = 0
    count_deviations: int = 0
    total_profit: int = 0

    @classmethod
    def load(cls, path: Path = TRAINING_FILE) -> TrainingData:
        if not path.exists():
            return cls()
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            if not isinstance(data, dict):
                raise ValueError("training file must contain a JSON object")
            allowed = set(cls.__dataclass_fields__)
            values = {key: value for key, value in data.items() if key in allowed}
            if not all(type(value) is int for value in values.values()):
                raise ValueError("training values must be integers")
            return cls(**values)
        except (OSError, ValueError):  # JSONDecodeError is a ValueError
            # Keep the unreadable file for inspection instead of overwriting it.
            try:
                path.replace(path.with_suffix(path.suffix + ".corrupt"))
            except OSError:
                pass
            return cls()

    def save(self, path: Path = TRAINING_FILE) -> None:
        data = {
            "rounds": self.rounds,
            "wins": self.wins,
            "losses": self.losses,
            "pushes": self.pushes,
            "actions": self.actions,
            "count_deviations": self.count_deviations,
            "total_profit": self.total_profit,
        }
        temporary_path = path.with_suffix(path.suffix + ".tmp")
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
        temporary_path.replace(path)


class BlackjackGame:
    def __init__(
        self,
        training: TrainingData | None = None,
        rng: random.Random | None = None,
        training_path: Path | None = TRAINING_FILE,
        strategy_profile: StrategyProfile | None = None,
    ):
        """`training_path=None` keeps results in memory only (useful for tests)."""
        self.shoe = Shoe(rng=rng)
        self.training = training or TrainingData()
        self.training_path = training_path
        self.strategy_profile = strategy_profile or StrategyProfile()
        self.round_strategy_profile = self.strategy_profile
        self.save_error = ""
        self.bankroll = STARTING_BANKROLL
        self.base_bet = 10
        self.risk_level = 2
        self.phase = "idle"
        self.dealer: list[Card] = []
        self.player_hands: list[Hand] = []
        self.active_hand = 0
        self.hole_revealed = False
        self.insurance_bet = 0
        self.last_message = "Ready to play."
        self._round_start_bankroll = self.bankroll
        self.last_round_profit = 0

    @property
    def next_bet(self) -> int:
        if self.bankroll < self.base_bet:
            return 0
        units = min(
            self.bankroll // self.base_bet,
            wager_units(self.shoe.true_count, self.risk_level, self.strategy_profile),
        )
        return self.base_bet * units

    def deal(self) -> bool:
        if self.phase not in ("idle", "complete"):
            return False
        if self.bankroll < self.base_bet:
            self.last_message = "Not enough bankroll for the minimum bet."
            return False
        notes: list[str] = []
        if self.shoe.cut_card_reached:
            self.shoe.shuffle()
            notes.append("The shoe was reshuffled.")

        self._round_start_bankroll = self.bankroll
        self.round_strategy_profile = self.strategy_profile
        # Whole betting units only, so 3:2 payouts and insurance stay exact.
        bet = self.next_bet
        self.bankroll -= bet
        self.dealer = []
        self.player_hands = [Hand([], bet)]
        self.active_hand = 0
        self.hole_revealed = False
        self.insurance_bet = 0
        self.phase = "player"

        player_card = self._draw_visible()
        dealer_up = self._draw_visible()
        second_player_card = self._draw_visible()
        hole_card = self.shoe.draw()
        self.player_hands[0].cards.extend((player_card, second_player_card))
        self.dealer = [dealer_up, hole_card]

        if dealer_up.rank == "A" and self.shoe.true_count >= 3:
            insurance = bet // 2
            if insurance > 0 and self.bankroll >= insurance:
                self.insurance_bet = insurance
                self.bankroll -= insurance
                notes.append(f"Bot takes ${insurance} insurance: true count is +3 or higher.")
        if not notes:
            notes.append("Bot is evaluating the hand.")
        self.last_message = " ".join(notes)

        dealer_natural = is_natural(self.dealer)
        player_natural = is_natural(self.player_hands[0].cards)
        if dealer_natural or player_natural:
            self._reveal_hole()
            if dealer_natural:
                self._settle(dealer_natural=True)
            else:
                self.bankroll += bet + bet * 3 // 2
                profit = self.bankroll - self._round_start_bankroll
                self._finish_round(profit)
                self.last_message = f"Blackjack! The bot is paid 3:2. Net {self._money(profit)}."
        return True

    def bot_step(self) -> bool:
        if self.phase != "player":
            return False
        hand = self.player_hands[self.active_hand]
        if hand.finished:
            self._advance_hand()
            return True

        can_double = len(hand.cards) == 2 and self.bankroll >= hand.bet
        can_split = (
            len(hand.cards) == 2
            and hand.cards[0].value == hand.cards[1].value
            and len(self.player_hands) < 4
            and self.bankroll >= hand.bet
            and not hand.split_aces
        )
        action, reason = choose_action(
            hand.cards,
            self.dealer[0],
            self.shoe.true_count,
            self.risk_level,
            can_double,
            can_split,
            self.round_strategy_profile.deviation_threshold,
            self.round_strategy_profile.split_tens_threshold,
        )
        self.training.actions += 1
        if reason != "basic strategy":
            self.training.count_deviations += 1

        if action == "hit":
            hand.cards.append(self._draw_visible())
            total, _ = hand_value(hand.cards)
            self.last_message = f"Bot hits ({reason}); hand total is {total}."
            if total >= 21:
                hand.finished = True
        elif action == "stand":
            hand.finished = True
            self.last_message = f"Bot stands ({reason})."
        elif action == "double":
            self.bankroll -= hand.bet
            hand.bet *= 2
            hand.doubled = True
            hand.cards.append(self._draw_visible())
            hand.finished = True
            self.last_message = f"Bot doubles ({reason})."
        elif action == "split":
            self.bankroll -= hand.bet
            first, second = hand.cards
            is_aces = first.rank == "A"
            hand.cards = [first, self._draw_visible()]
            hand.split_hand = True
            hand.split_aces = is_aces
            hand.finished = is_aces
            new_hand = Hand(
                [second, self._draw_visible()],
                hand.bet,
                split_hand=True,
                split_aces=is_aces,
                finished=is_aces,
            )
            self.player_hands.insert(self.active_hand + 1, new_hand)
            self.last_message = "Bot splits the pair."
        self._advance_hand()
        return True

    def _draw_visible(self) -> Card:
        card = self.shoe.draw()
        self.shoe.count(card)
        return card

    def _reveal_hole(self) -> None:
        if not self.hole_revealed:
            self.shoe.count(self.dealer[1])
            self.hole_revealed = True

    def _advance_hand(self) -> None:
        while self.active_hand < len(self.player_hands) and self.player_hands[self.active_hand].finished:
            self.active_hand += 1
        if self.active_hand >= len(self.player_hands):
            self._play_dealer_and_settle()

    def _play_dealer_and_settle(self) -> None:
        self._reveal_hole()
        while hand_value(self.dealer)[0] < 17:
            self.dealer.append(self._draw_visible())
        self._settle(dealer_natural=False)

    def _settle(self, dealer_natural: bool) -> None:
        dealer_total, _ = hand_value(self.dealer)
        dealer_bust = dealer_total > 21
        profit = 0
        for hand in self.player_hands:
            player_total, _ = hand_value(hand.cards)
            natural = not hand.split_hand and is_natural(hand.cards)
            if dealer_natural and natural:
                self.bankroll += hand.bet
            elif dealer_natural:
                pass
            elif natural:
                self.bankroll += hand.bet + hand.bet * 3 // 2
            elif player_total > 21:
                pass
            elif dealer_bust or player_total > dealer_total:
                self.bankroll += hand.bet * 2
            elif player_total == dealer_total:
                self.bankroll += hand.bet

        insurance_return = self.insurance_bet * 3 if dealer_natural else 0
        self.bankroll += insurance_return
        profit = self.bankroll - self._round_start_bankroll
        if dealer_natural and self.insurance_bet:
            self.last_message = "Dealer has blackjack; insurance pays 2:1."
        elif dealer_natural:
            self.last_message = "Dealer has blackjack."
        elif dealer_bust:
            self.last_message = "Dealer busts."
        else:
            self.last_message = "Round complete."
        self.last_message += f" Net {self._money(profit)}."
        self._finish_round(profit)

    @staticmethod
    def _money(amount: int) -> str:
        return f"{'-' if amount < 0 else '+'}${abs(amount)}"

    def _finish_round(self, profit: int) -> None:
        if self.phase == "complete":
            return
        self.phase = "complete"
        self.last_round_profit = profit
        self.training.rounds += 1
        self.training.total_profit += profit
        if profit > 0:
            self.training.wins += 1
        elif profit < 0:
            self.training.losses += 1
        else:
            self.training.pushes += 1
        self._save_training()

    def _save_training(self) -> None:
        if self.training_path is None:
            return
        try:
            self.training.save(self.training_path)
            self.save_error = ""
        except OSError as error:
            self.save_error = f"could not save training data ({error.strerror or error})"


class BlackjackWindow:
    def __init__(
        self,
        root: tk.Tk,
        training: TrainingData | None = None,
        strategy_profile: StrategyProfile | None = None,
        training_path: Path | None = TRAINING_FILE,
        strategy_path: Path | None = STRATEGY_FILE,
    ):
        self.root = root
        self.training_path = training_path
        self.strategy_path = strategy_path
        self.training = training if training is not None else (
            TrainingData.load(training_path) if training_path is not None else TrainingData()
        )
        self.strategy_load_warning = ""
        if strategy_profile is not None:
            self.strategy_profile = strategy_profile
        elif strategy_path is None:
            self.strategy_profile = StrategyProfile()
        else:
            try:
                self.strategy_profile = StrategyProfile.load(strategy_path)
            except (OSError, ValueError) as error:
                self.strategy_profile = StrategyProfile()
                self.strategy_load_warning = f"Saved strategy could not be loaded: {error}"
        self.game = BlackjackGame(
            self.training,
            training_path=training_path,
            strategy_profile=self.strategy_profile,
        )
        self.starting_amount_var = tk.StringVar(value=str(STARTING_BANKROLL))
        self.speed_var = tk.IntVar(value=3)
        self.auto_playing = False
        self._auto_job: str | None = None
        self._strategy_results: queue.Queue[
            tuple[StrategyTrainingResult | None, str | None, str | None]
        ] = queue.Queue()
        self.root.title("Blackjack Expert Bot")
        self.root.geometry("680x600")
        self.root.minsize(580, 500)
        self._build_ui()
        self._update_speed_label()
        self._render()
        self._start_strategy_training()

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="BLACKJACK EXPERT BOT", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(
            main,
            text="6 decks · dealer stands on soft 17 · blackjack pays 3:2 · bot-only play",
        ).pack(anchor="w", pady=(2, 12))

        settings = ttk.Frame(main)
        settings.pack(fill="x", pady=4)
        self.bankroll_label = ttk.Label(settings, font=("Segoe UI", 12, "bold"))
        self.bankroll_label.pack(side="left")
        ttk.Label(settings, text="Starting amount: $").pack(side="left", padx=(18, 2))
        self.starting_amount_entry = ttk.Entry(
            settings, textvariable=self.starting_amount_var, width=9
        )
        self.starting_amount_entry.pack(side="left")
        ttk.Label(settings, text="Risk level: 2 · balanced").pack(side="right")

        speed_row = ttk.Frame(main)
        speed_row.pack(fill="x", pady=(4, 0))
        ttk.Label(speed_row, text="Bot speed:").pack(side="left", padx=(0, 8))
        for speed in range(1, 6):
            ttk.Radiobutton(
                speed_row,
                text=str(speed),
                value=speed,
                variable=self.speed_var,
                style="Toolbutton",
                command=self._update_speed_label,
            ).pack(side="left", padx=2)
        self.speed_label = ttk.Label(speed_row)
        self.speed_label.pack(side="left", padx=10)

        table = ttk.LabelFrame(main, text="Table", padding=12)
        table.pack(fill="both", expand=True, pady=10)
        self.bet_label = ttk.Label(table, font=("Segoe UI", 11, "bold"))
        self.bet_label.pack(anchor="w", pady=4)
        self.dealer_label = ttk.Label(table, font=("Consolas", 15))
        self.dealer_label.pack(anchor="w", pady=10)
        self.player_label = ttk.Label(table, font=("Consolas", 15), justify="left")
        self.player_label.pack(anchor="w", pady=10)
        self.message_label = ttk.Label(table, wraplength=600, font=("Segoe UI", 10))
        self.message_label.pack(anchor="w", pady=8)

        self.count_label = ttk.Label(main, font=("Consolas", 10))
        self.count_label.pack(anchor="w")
        self.stats_label = ttk.Label(main, font=("Segoe UI", 9))
        self.stats_label.pack(anchor="w", pady=4)
        self.strategy_status_label = ttk.Label(
            main, text="Strategy training will run in the background.", wraplength=640
        )
        self.strategy_status_label.pack(anchor="w", pady=2)

        self.auto_button = ttk.Button(main, text="Start", command=self._toggle_auto)
        self.auto_button.pack(pady=(10, 4))

        ttk.Label(
            main,
            text="Start runs hands automatically until stopped or the bankroll is depleted. "
            "Training saves results locally; past results do not predict future hands.",
            wraplength=640,
        ).pack(anchor="w", pady=(8, 0))

    def _start_strategy_training(self) -> None:
        status = "Training strategy with simulated shoes (keeps basic strategy as its baseline)..."
        if self.strategy_load_warning:
            status += f" {self.strategy_load_warning}"
        self.strategy_status_label.configure(text=status)
        worker = threading.Thread(target=self._train_strategy_background, daemon=True)
        worker.start()
        self.root.after(100, self._poll_strategy_training)

    def _train_strategy_background(self) -> None:
        try:
            result = StrategyTrainer().train(self.strategy_profile)
        except (RuntimeError, ValueError) as error:
            self._strategy_results.put((None, str(error), None))
            return
        save_error = None
        if self.strategy_path is not None:
            try:
                result.profile.save(self.strategy_path)
            except OSError as error:
                save_error = f"Could not save the tuned strategy: {error.strerror or error}"
        self._strategy_results.put((result, None, save_error))

    def _poll_strategy_training(self) -> None:
        try:
            result, training_error, save_error = self._strategy_results.get_nowait()
        except queue.Empty:
            self.root.after(100, self._poll_strategy_training)
            return
        if training_error:
            self.strategy_status_label.configure(text=f"Strategy training failed: {training_error}")
            return
        if result is None:
            self.strategy_status_label.configure(text="Strategy training ended without a result.")
            return

        self.strategy_profile = result.profile
        self.game.strategy_profile = result.profile
        if result.improved:
            status = (
                f"Training selected a profile that improved held-out simulations by "
                f"${result.validation_mean_gain:.3f}/hand; 95% lower bound "
                f"${result.validation_lower_bound:.3f}/hand. "
            )
        else:
            status = "No candidate showed a validated improvement; kept the current profile. "
        status += f"Evaluated {result.simulated_rounds:,} simulated hands."
        if self.strategy_load_warning:
            status += " Started from the default profile because the saved profile was invalid."
            self.strategy_load_warning = ""
        if save_error:
            status += f" {save_error}"
        self.strategy_status_label.configure(text=status)
        self._render()

    def _toggle_auto(self) -> None:
        if self.auto_playing:
            self._stop_auto()
        else:
            try:
                starting_amount = int(self.starting_amount_var.get())
            except ValueError:
                self.game.last_message = "Starting amount must be a whole number."
                self._render()
                return
            if starting_amount < self.game.base_bet:
                self.game.last_message = f"Starting amount must be at least ${self.game.base_bet}."
                self._render()
                return
            if self.game.phase in ("idle", "complete"):
                self.game.bankroll = starting_amount
                self.game.last_message = f"Starting bankroll set to ${starting_amount}."
            self.auto_playing = True
            self.auto_button.configure(text="Stop")
            self.starting_amount_entry.configure(state="disabled")
            self._auto_step()

    def _stop_auto(self) -> None:
        self.auto_playing = False
        if self._auto_job is not None:
            self.root.after_cancel(self._auto_job)  # no stacked timers on Stop/Auto
            self._auto_job = None
        self.auto_button.configure(text="Start")
        self.starting_amount_entry.configure(state="normal")

    def _speed_delay(self) -> float:
        return SPEED_DELAYS[self.speed_var.get() - 1]

    def _update_speed_label(self) -> None:
        delay = self._speed_delay()
        self.speed_label.configure(text=f"{delay:g} sec per step")

    def _auto_step(self) -> None:
        self._auto_job = None
        if not self.auto_playing:
            return
        if self.game.phase in ("idle", "complete"):
            if not self.game.deal():
                self._render()
                self._stop_auto()
                return
            self._render()
            self._auto_job = self.root.after(int(self._speed_delay() * 1000), self._auto_step)
            return
        if self.game.phase == "player":
            self.game.bot_step()
            self._render()
        if self.auto_playing:
            self._auto_job = self.root.after(int(self._speed_delay() * 1000), self._auto_step)

    def _render(self) -> None:
        self.bankroll_label.configure(text=f"Bankroll: ${self.game.bankroll}")
        hand_stakes = sum(hand.bet for hand in self.game.player_hands)
        if self.game.phase == "player":
            wager_text = f"Current hand bets: ${hand_stakes}"
            if self.game.insurance_bet:
                wager_text += f" + ${self.game.insurance_bet} insurance"
        elif self.game.player_hands and self.game.phase == "complete":
            wager_text = f"Last hand bet: ${hand_stakes} · Next bet: ${self.game.next_bet}"
        else:
            wager_text = (
                f"Next bet: ${self.game.next_bet}"
                if self.game.next_bet
                else "Next bet: bankroll is below the $10 minimum"
            )
        self.bet_label.configure(text=wager_text)
        dealer_cards = self.game.dealer
        if dealer_cards:
            shown = [str(dealer_cards[0])]
            shown.append(str(dealer_cards[1]) if self.game.hole_revealed else "??")
            shown.extend(str(card) for card in dealer_cards[2:])
            dealer_text = f"Dealer: {'  '.join(shown)}"
            if self.game.hole_revealed:
                dealer_text += f"  (total {hand_value(dealer_cards)[0]})"
        else:
            dealer_text = "Dealer: —"
        self.dealer_label.configure(text=dealer_text)

        if self.game.player_hands:
            lines = []
            for index, hand in enumerate(self.game.player_hands):
                total, _ = hand_value(hand.cards)
                marker = "▶ " if self.game.phase == "player" and index == self.game.active_hand else "  "
                lines.append(
                    f"{marker}Bot hand {index + 1}: {'  '.join(map(str, hand.cards))} "
                    f"(total {total}, bet ${hand.bet})"
                )
            player_text = "\n".join(lines)
        else:
            player_text = "Bot hand: —"
        self.player_label.configure(text=player_text)
        self.message_label.configure(text=self.game.last_message)
        count = self.game.shoe.true_count
        self.count_label.configure(
            text=(
                f"Hi-Lo running count: {self.game.shoe.running_count:+d}   "
                f"True count: {count:+.1f}   Cards left: {len(self.game.shoe.cards)}"
            )
        )
        data = self.training
        self.stats_label.configure(
            text=(
                f"Training record: {data.rounds} rounds (W {data.wins} / L {data.losses} / "
                f"P {data.pushes}) · decisions {data.actions} · count deviations "
                f"{data.count_deviations} · net ${data.total_profit:+d}"
                + (f" · {self.game.save_error}" if self.game.save_error else "")
            )
        )

def main() -> None:
    if tk is None:
        raise SystemExit("Tkinter is not installed, so the game window cannot start.")
    root = tk.Tk()
    BlackjackWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
