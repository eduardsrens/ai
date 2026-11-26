"""Finite-shoe blackjack bot with EV analysis and optional online Q-learning."""

import random
from typing import Protocol, Sequence


BOT_NAME: str = "zanylegoat"
DECK_COUNT = 4
SIMULATIONS = 8192
MAX_SIMULATIONS = 16384
LEARNING_MIN_SAMPLES = 20
EV_TIE_MARGIN = 0.025
_CARD_VALUES = tuple(range(1, 11))
_Q_VALUES: dict[tuple[tuple[int, bool, int, bool, int], str], float] = {}
_Q_COUNTS: dict[tuple[tuple[int, bool, int, bool, int], str], int] = {}
_PENDING: tuple[tuple[int, bool, int, bool, int], str] | None = None


class CardLike(Protocol):
    """Card fields required when the caller uses card objects instead of strings."""

    rank: str


CardInput = str | CardLike


def _rank(card: CardInput) -> str:
    if isinstance(card, str):
        if len(card) not in (2, 3) or card[-1].upper() not in "HDCS":
            raise ValueError(f"invalid card string: {card!r}")
        rank = card[:-1].upper()
    else:
        rank = card.rank.upper()
    if rank == "T":
        rank = "10"
    if rank not in ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"):
        raise ValueError(f"invalid card rank: {rank!r}")
    return rank


def _value(card: CardInput) -> int:
    rank = _rank(card)
    if rank == "A":
        return 11
    if rank in ("J", "Q", "K"):
        return 10
    return int(rank)


def _bucket(card: CardInput) -> int:
    rank = _rank(card)
    if rank in ("10", "J", "Q", "K"):
        return 10
    return 1 if rank == "A" else int(rank)


def hand_value(hand: Sequence[CardInput]) -> tuple[int, bool]:
    """Return the best total and whether the hand is soft."""
    total = sum(_value(card) for card in hand)
    aces = sum(_rank(card) == "A" for card in hand)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total, aces > 0


def _value_hand(values: Sequence[int]) -> tuple[int, bool]:
    total = sum(values)
    aces = sum(value == 11 for value in values)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total, aces > 0


def _basic_action(
    total: int,
    soft: bool,
    upcard: int,
    can_double: bool,
    dealer_hits_soft_17: bool,
) -> str:
    """Continuation policy used when estimating the result of a hit."""
    if total >= 21:
        return "stand"
    if soft:
        if total < 13:
            return "hit"
        if total <= 17:
            double_from = {13: 5, 14: 5, 15: 4, 16: 4, 17: 3}
            if can_double and double_from[total] <= upcard <= 6:
                return "double"
            return "hit"
        if total == 18:
            if can_double and 3 <= upcard <= 6:
                return "double"
            if upcard in (2, 7, 8):
                return "stand"
            return "hit"
        if total == 19 and dealer_hits_soft_17 and upcard == 6 and can_double:
            return "double"
        return "stand"

    if total <= 8:
        return "hit"
    if total == 9:
        return "double" if can_double and 3 <= upcard <= 6 else "hit"
    if total == 10:
        return "double" if can_double and 2 <= upcard <= 9 else "hit"
    if total == 11:
        if can_double and (upcard <= 10 or dealer_hits_soft_17):
            return "double"
        return "hit"
    if total == 12:
        return "stand" if 4 <= upcard <= 6 else "hit"
    if 13 <= total <= 16:
        return "stand" if 2 <= upcard <= 6 else "hit"
    return "stand"


def _remaining_shoe(
    seen_cards: Sequence[CardInput],
) -> list[int]:
    counts = [0] + [4 * DECK_COUNT for _ in range(9)] + [16 * DECK_COUNT]
    for card in seen_cards:
        counts[_bucket(card)] -= 1
    if any(count < 0 for count in counts[1:]):
        raise ValueError("seen_cards contains more cards than a four-deck shoe")
    return counts


def count_info(seen_cards: Sequence[CardInput]) -> tuple[int, float]:
    """Return Hi-Lo running and true counts from the exposed cards."""
    running_count = 0
    for card in seen_cards:
        value = _bucket(card)
        if 2 <= value <= 6:
            running_count += 1
        elif value in (1, 10):
            running_count -= 1
    remaining = max((DECK_COUNT * 52 - len(seen_cards)) / 52, 0.25)
    return running_count, running_count / remaining


def place_bet(bankroll: int, history: list[str], decks_remaining: float) -> int:
    """Choose a conservative count-based wager within the tournament limits."""
    bankroll = max(0, int(bankroll))
    if bankroll < 10:
        return bankroll

    running_count, _ = count_info(history)
    true_count = running_count / max(float(decks_remaining), 0.25)
    estimated_edge = max(0.0, 0.005 * true_count - 0.005)
    target = max(10, int(bankroll * estimated_edge / 1.3))
    bankroll_cap = max(10, bankroll // 10)
    return int(min(target, 200, bankroll, bankroll_cap))


def _state_key(
    hand: Sequence[CardInput],
    upcard: CardInput,
    seen_cards: Sequence[CardInput],
) -> tuple[int, bool, int, bool, int]:
    total, soft = hand_value(hand)
    _, true_count = count_info(seen_cards)
    count_bucket = max(-5, min(5, int(true_count)))
    return total, soft, _bucket(upcard), len(hand) == 2, count_bucket


def _draw_player(
    action: str,
    hand: list[int],
    upcard: int,
    draws: Sequence[int],
    position: int,
    dealer_hits_soft_17: bool,
) -> tuple[list[int], int, int]:
    stake = 2 if action == "double" else 1
    current = list(hand)
    if action == "stand":
        return current, position, stake

    if position >= len(draws):
        return current, position, stake
    current.append(draws[position])
    position += 1
    if action == "double":
        return current, position, stake

    while position < len(draws):
        total, soft = _value_hand(current)
        if total > 21 or _basic_action(total, soft, upcard, False, dealer_hits_soft_17) != "hit":
            break
        current.append(draws[position])
        position += 1
    return current, position, stake


def _dealer_total(
    upcard: int,
    hole_card: int,
    draws: Sequence[int],
    position: int,
    dealer_hits_soft_17: bool,
) -> tuple[int, int]:
    dealer = [11 if upcard == 1 else upcard, hole_card]
    while position < len(draws):
        dealer_total, dealer_soft = _value_hand(dealer)
        if dealer_total > 21 or (
            dealer_total > 17
            or (dealer_total == 17 and (not dealer_soft or not dealer_hits_soft_17))
        ):
            break
        dealer.append(draws[position])
        position += 1
    return _value_hand(dealer)[0], position


def _settle_total(player_total: int, dealer_total: int, stake: int) -> int:
    if player_total > 21:
        return -stake
    if dealer_total > 21 or player_total > dealer_total:
        return stake
    if player_total == dealer_total:
        return 0
    return -stake


def _settle(
    player: Sequence[int],
    upcard: int,
    hole_card: int,
    draws: Sequence[int],
    position: int,
    dealer_hits_soft_17: bool,
    stake: int,
) -> int:
    player_total, _ = _value_hand(player)
    dealer_total, _ = _dealer_total(
        upcard, hole_card, draws, position, dealer_hits_soft_17
    )
    return _settle_total(player_total, dealer_total, stake)


def _draw_split_hand(
    first_card: int,
    upcard: int,
    draws: Sequence[int],
    position: int,
    dealer_hits_soft_17: bool,
    can_double: bool,
) -> tuple[list[int], int, int]:
    hand = [first_card]
    if position >= len(draws):
        return hand, position, 1
    hand.append(draws[position])
    position += 1
    if first_card == 11:
        return hand, position, 1

    stake = 1
    while position < len(draws):
        total, soft = _value_hand(hand)
        action = _basic_action(
            total,
            soft,
            upcard,
            len(hand) == 2 and can_double,
            dealer_hits_soft_17,
        )
        if action == "stand":
            break
        hand.append(draws[position])
        position += 1
        if action == "double":
            stake = 2
            break
    return hand, position, stake


def _split_round(
    pair: Sequence[int],
    upcard: int,
    hole_card: int,
    draws: Sequence[int],
    position: int,
    dealer_hits_soft_17: bool,
    can_double: bool,
) -> int:
    first_hand, position, first_stake = _draw_split_hand(
        pair[0], upcard, draws, position, dealer_hits_soft_17, can_double
    )
    second_hand, position, second_stake = _draw_split_hand(
        pair[1], upcard, draws, position, dealer_hits_soft_17, can_double
    )
    dealer_total, _ = _dealer_total(
        upcard, hole_card, draws, position, dealer_hits_soft_17
    )
    first_total, _ = _value_hand(first_hand)
    second_total, _ = _value_hand(second_hand)
    return (
        _settle_total(first_total, dealer_total, first_stake)
        + _settle_total(second_total, dealer_total, second_stake)
    )


def _action_values(
    hand: Sequence[CardInput],
    dealer_upcard: CardInput,
    dealer_hits_soft_17: bool,
    seen_cards: Sequence[CardInput],
    simulations: int,
    can_double: bool | None,
    can_split: bool,
) -> dict[str, float]:
    shoe_counts = _remaining_shoe(seen_cards)
    population = [
        11 if value == 1 else value
        for value in _CARD_VALUES
        for _ in range(shoe_counts[value])
    ]
    if not population:
        raise ValueError("No unseen cards remain in the shoe")

    upcard = _bucket(dealer_upcard)
    player_values = [_value(card) for card in hand]
    actions = ["hit", "stand"]
    if can_double is None:
        can_double = len(hand) == 2
    can_double = can_double and len(hand) == 2
    can_split = (
        can_split
        and len(hand) == 2
        and player_values[0] == player_values[1]
    )
    if can_double:
        actions.append("double")
    if can_split:
        actions.append("split")
    totals = {action: 0 for action in actions}

    seed = (
        sum((index + 1) * count for index, count in enumerate(shoe_counts))
        + sum(player_values) * 31
        + upcard * 97
        + int(dealer_hits_soft_17) * 997
    )
    rng = random.Random(seed)
    sample_size = min(32, len(population))
    completed = 0
    while completed < simulations:
        draws = rng.sample(population, sample_size)
        hole = draws[0]
        if (upcard == 1 and hole == 10) or (upcard == 10 and hole == 11):
            continue
        completed += 1
        for action in actions:
            if action == "split":
                totals[action] += _split_round(
                    player_values,
                    upcard,
                    hole,
                    draws,
                    1,
                    dealer_hits_soft_17,
                    can_double,
                )
                continue
            player, position, stake = _draw_player(
                action,
                player_values,
                upcard,
                draws,
                1,
                dealer_hits_soft_17,
            )
            totals[action] += _settle(
                player,
                upcard,
                hole,
                draws,
                position,
                dealer_hits_soft_17,
                stake,
            )
    return {action: totals[action] / simulations for action in actions}


def _update_q(
    state: tuple[int, bool, int, bool, int],
    action: str,
    target: float,
) -> None:
    key = (state, action)
    count = _Q_COUNTS.get(key, 0) + 1
    old = _Q_VALUES.get(key, 0.0)
    _Q_VALUES[key] = old + (target - old) / min(count, 20)
    _Q_COUNTS[key] = count


def start_hand() -> None:
    """Start an RL episode; call once when a new round begins."""
    global _PENDING
    _PENDING = None


def learn_from_result(reward: float) -> None:
    """Finish an RL episode with +1/-1 for a win/loss or 0 for a push."""
    global _PENDING
    if reward not in (-2, -1, 0, 1, 2):
        raise ValueError("reward must be -2, -1, 0, 1, or 2")
    if _PENDING is not None:
        _update_q(*_PENDING, float(reward))
        _PENDING = None


def analyze_hand(
    hand: Sequence[CardInput],
    dealer_upcard: CardInput,
    dealer_hits_soft_17: bool = False,
    seen_cards: Sequence[CardInput] | None = None,
    simulations: int = SIMULATIONS,
    can_double: bool | None = None,
    can_split: bool = False,
    use_learning: bool = True,
) -> tuple[str, dict[str, float], int, float]:
    """Return chosen action, sampled EVs, running count, and true count.

    ``seen_cards`` must include this hand and the dealer upcard but not the
    dealer's hidden card. Draws are sampled without replacement from the
    remaining four-deck shoe; dealer naturals are excluded because they must be
    resolved before a player decision.
    """
    global _PENDING
    if not hand:
        raise ValueError("hand must contain at least one card")
    if simulations < 1:
        raise ValueError("simulations must be positive")
    if seen_cards is None:
        seen_cards = [*hand, dealer_upcard]

    values = _action_values(
        hand,
        dealer_upcard,
        dealer_hits_soft_17,
        seen_cards,
        simulations,
        can_double,
        can_split,
    )
    if simulations < MAX_SIMULATIONS and simulations >= 512 and len(values) > 1:
        ordered = sorted(values.values(), reverse=True)
        if ordered[0] - ordered[1] < 0.06:
            simulations = min(simulations * 2, MAX_SIMULATIONS)
            values = _action_values(
                hand,
                dealer_upcard,
                dealer_hits_soft_17,
                seen_cards,
                simulations,
                can_double,
                can_split,
            )
    best_ev = max(values.values())
    tied = [
        action
        for action in ("stand", "hit", "double", "split")
        if action in values and best_ev - values[action] <= EV_TIE_MARGIN
    ]
    state = _state_key(hand, dealer_upcard, seen_cards)
    learned = [
        action
        for action in tied
        if use_learning
        and _Q_COUNTS.get((state, action), 0) >= LEARNING_MIN_SAMPLES
    ]
    if not use_learning:
        action = max(values, key=values.get)
    elif learned:
        action = max(learned, key=lambda candidate: _Q_VALUES[(state, candidate)])
    else:
        action = min(
            tied,
            key=lambda candidate: (
                _Q_COUNTS.get((state, candidate), 0),
                -values[candidate],
            ),
        )

    if use_learning and _PENDING is not None:
        next_q = max(
            _Q_VALUES.get((state, next_action), 0.0)
            for next_action in ("hit", "stand", "double")
            if next_action in values
        )
        _update_q(*_PENDING, 0.9 * next_q)
    if use_learning:
        _PENDING = (state, action)

    running_count, true_count = count_info(seen_cards)
    return action, values, running_count, true_count


def get_move(
    hand: Sequence[CardInput],
    dealer_upcard: CardInput,
    dealer_hits_soft_17: bool = False,
    seen_cards: Sequence[CardInput] | None = None,
) -> str:
    """Choose hit, stand, or double using shoe-aware simulated expected value.

    Tournament runners should pass all exposed cards in ``seen_cards``;
    exclude the dealer's hidden card. Call ``learn_from_result`` after a hand
    and ``start_hand`` before the next one to enable online Q-learning.
    """
    return analyze_hand(
        hand,
        dealer_upcard,
        dealer_hits_soft_17,
        seen_cards,
    )[0]


def decide_action(
    hand: list[str],
    dealer_upcard: str,
    history: list[str],
    can_double: bool,
    can_split: bool,
) -> str:
    """Tournament API: choose a legal action using the four-deck shoe history."""
    if not hand:
        raise ValueError("hand must contain at least one card")
    if hand_value(hand)[0] >= 21:
        return "STAND"
    action, _, _, _ = analyze_hand(
        hand,
        dealer_upcard,
        dealer_hits_soft_17=False,
        seen_cards=history,
        can_double=can_double,
        can_split=can_split,
        use_learning=False,
    )
    return action.upper()
