"""Standalone four-deck blackjack tournament bot.

The tournament can call:
    choose_action(state) -> "hit" | "stand" | "double" | "split"
    choose_bet(state) -> integer wager

State contract:
    player_hand: cards in this hand, e.g. ["10H", "6S"] or [{"rank": "10"}]
    dealer_upcard: exposed dealer card
    seen_cards: all publicly exposed cards since the last shuffle, including
                cards exposed by every player at a shared table
    legal_actions: optional iterable of currently legal action names
    risk_level: optional integer 1 (safe), 2 (balanced), or 3 (risky)

Betting state uses bankroll, base_bet/min_bet, and optional max_bet/legal_bets.
Rules assumed for the basic-strategy chart: four decks, dealer stands on soft
17, blackjack pays 3:2, and double after split is allowed. The tournament
engine should supply its own rule-specific legal_actions.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any


DECKS = 4
BASE_BET = 10
STRATEGY_SETTINGS = {
    "bet_trigger": 2,
    "max_bet_units": 3,
    "deviation_threshold": 2,
    "split_tens_threshold": 99,
}

# Snapshot of the statistics file when this standalone bot was generated.
# These values are informational only; played-game statistics do not affect
# tournament decisions.
HISTORICAL_STATS = {
    "rounds": 644,
    "wins": 313,
    "losses": 285,
    "pushes": 46,
    "actions": 821,
    "count_deviations": 0,
    "total_profit": 745,
}

_HI_LO = {
    "2": 1,
    "3": 1,
    "4": 1,
    "5": 1,
    "6": 1,
    "10": -1,
    "J": -1,
    "Q": -1,
    "K": -1,
    "A": -1,
}
_ACTION_ALIASES = {
    "hit": "hit",
    "stand": "stand",
    "stay": "stand",
    "double": "double",
    "double down": "double",
    "double_down": "double",
    "split": "split",
}


def _rank(card: Any) -> str:
    if isinstance(card, Mapping):
        value = card.get("rank")
    elif isinstance(card, str):
        value = card.strip().upper()
        if value.endswith(("S", "H", "D", "C")):
            value = value[:-1]
    else:
        value = card

    rank = str(value).strip().upper()
    if rank == "T":
        rank = "10"
    if rank not in ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"):
        raise ValueError(f"Unrecognized card rank: {value!r}")
    return rank


def _value(rank: str) -> int:
    if rank == "A":
        return 11
    if rank in ("J", "Q", "K"):
        return 10
    return int(rank)


def _hand_ranks(cards: Any) -> list[str]:
    if isinstance(cards, (str, bytes)) or not isinstance(cards, Sequence) or not cards:
        raise ValueError("player_hand must be a non-empty sequence of cards")
    return [_rank(card) for card in cards]


def _hand_value(cards: Sequence[str]) -> tuple[int, bool]:
    total = sum(_value(card) for card in cards)
    aces = sum(card == "A" for card in cards)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total, aces > 0


def _true_count(state: Mapping[str, Any]) -> float:
    if state.get("true_count") is not None:
        return float(state["true_count"])
    if state.get("running_count") is not None:
        running_count = int(state["running_count"])
    else:
        seen_cards = state.get("seen_cards", ())
        if isinstance(seen_cards, (str, bytes)) or not isinstance(seen_cards, Sequence):
            raise ValueError("seen_cards must be a sequence of exposed cards")
        running_count = sum(_HI_LO.get(_rank(card), 0) for card in seen_cards)

    decks_remaining = state.get("decks_remaining")
    if decks_remaining is None:
        seen_count = len(state.get("seen_cards", ()))
        decks_remaining = max(DECKS - seen_count / 52, 0.25)
    else:
        decks_remaining = max(float(decks_remaining), 0.25)
    return running_count / decks_remaining


def _dealer_value(card: str) -> int:
    return _value(card)


def _basic_action(
    cards: Sequence[str],
    dealer_card: str,
    can_double: bool,
    can_split: bool,
) -> str:
    total, soft = _hand_value(cards)
    dealer = _dealer_value(dealer_card)

    if can_split and len(cards) == 2 and _value(cards[0]) == _value(cards[1]):
        pair = _value(cards[0])
        if pair in (8, 11):
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
        return "double"
    if can_double and total == 10 and 2 <= dealer <= 9:
        return "double"
    if can_double and total == 9 and 3 <= dealer <= 6:
        return "double"
    return "hit"


def _legal_actions(state: Mapping[str, Any]) -> set[str] | None:
    supplied = state.get("legal_actions")
    if supplied is None:
        return None
    if isinstance(supplied, (str, bytes)) or not isinstance(supplied, Sequence):
        raise ValueError("legal_actions must be a sequence of action names")
    actions = {
        _ACTION_ALIASES[str(action).strip().lower().replace("-", " ")]
        for action in supplied
        if str(action).strip().lower().replace("-", " ") in _ACTION_ALIASES
    }
    if not actions:
        raise ValueError("legal_actions contains no supported blackjack actions")
    return actions


def _risk_level(state: Mapping[str, Any]) -> int:
    level = int(state.get("risk_level", 2))
    if level not in (1, 2, 3):
        raise ValueError("risk_level must be 1, 2, or 3")
    return level


def choose_action(state: Mapping[str, Any]) -> str:
    """Choose one legal play action from the documented tournament state."""
    if not isinstance(state, Mapping):
        raise ValueError("state must be a mapping")
    cards = _hand_ranks(state.get("player_hand"))
    dealer_card = _rank(state.get("dealer_upcard"))
    actions = _legal_actions(state)
    can_double = len(cards) == 2 and (actions is None or "double" in actions)
    can_split = (
        len(cards) == 2
        and _value(cards[0]) == _value(cards[1])
        and (actions is None or "split" in actions)
    )
    risk_level = _risk_level(state)
    count = _true_count(state)
    action = _basic_action(cards, dealer_card, can_double, can_split)
    total, soft = _hand_value(cards)

    deviation_threshold = STRATEGY_SETTINGS["deviation_threshold"]
    if risk_level == 3:
        deviation_threshold = 1
    if risk_level >= 2 and not soft and len(cards) >= 2 and action != "split":
        dealer = _dealer_value(dealer_card)
        if (
            can_split
            and _value(cards[0]) == 10
            and dealer in (5, 6)
            and count >= STRATEGY_SETTINGS["split_tens_threshold"]
        ):
            action = "split"
        elif total == 16 and dealer == 10 and count >= deviation_threshold:
            action = "stand"
        elif total == 15 and dealer == 10 and count >= deviation_threshold + 2:
            action = "stand"
        elif total == 12 and dealer in (2, 3) and count >= deviation_threshold + (
            1 if dealer == 2 else 0
        ):
            action = "stand"
        elif total == 10 and dealer == 10 and can_double and count >= deviation_threshold + 2:
            action = "double"

    if actions is None or action in actions:
        return action
    if total >= 17 and "stand" in actions:
        return "stand"
    if "hit" in actions:
        return "hit"
    if "stand" in actions:
        return "stand"
    raise ValueError(f"No safe fallback for legal actions: {sorted(actions)}")


def choose_bet(state: Mapping[str, Any]) -> int:
    """Choose a whole-unit wager using count, configured risk, and bankroll."""
    if not isinstance(state, Mapping):
        raise ValueError("state must be a mapping")
    try:
        bankroll = int(state["bankroll"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("betting state must include an integer bankroll") from error
    base_bet = int(state.get("base_bet", state.get("min_bet", BASE_BET)))
    if base_bet < 1:
        raise ValueError("base_bet must be a positive integer")
    if bankroll < base_bet:
        return 0

    risk_level = _risk_level(state)
    if risk_level == 1:
        trigger, cap = 3, 2
    elif risk_level == 3:
        trigger, cap = 1, 5
    else:
        trigger = STRATEGY_SETTINGS["bet_trigger"]
        cap = STRATEGY_SETTINGS["max_bet_units"]

    units = min(cap, 1 + max(0, math.floor(_true_count(state) - trigger + 1)))
    bet = min(bankroll, base_bet * units)
    if state.get("max_bet") is not None:
        bet = min(bet, int(state["max_bet"]))
    if bet < base_bet:
        return 0
    legal_bets = state.get("legal_bets")
    if legal_bets is not None:
        choices = sorted(
            {
                int(value)
                for value in legal_bets
                if base_bet <= int(value) <= bet
            }
        )
        if not choices:
            return 0
        bet = choices[-1]
    return max(0, bet)


