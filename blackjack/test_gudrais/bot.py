"""Hi-Lo kāršu skaitīšanas un blackjack pamatstratēģijas testa bots."""

BOT_NAME = "Half Smart bot"

_HI_LO = {
    "2": 1,
    "3": 1,
    "4": 1,
    "5": 1,
    "6": 1,
    "7": 0,
    "8": 0,
    "9": 0,
    "T": -1,
    "J": -1,
    "Q": -1,
    "K": -1,
    "A": -1,
}


def place_bet(bankroll: int, history: list[str], decks_remaining: float) -> int:
    """Palielina likmi, ja Hi-Lo patiesais skaits dod priekšrocību."""
    max_bet = min(200, bankroll)
    running_count = _running_count(history)
    true_count = running_count / max(decks_remaining, 0.25)
    units = 1 + max(0, int(true_count))
    return min(max_bet, max(10, units * 10))


def decide_action(
    hand: list[str],
    dealer_upcard: str,
    history: list[str],
    can_double: bool,
    can_split: bool,
) -> str:
    """Lieto pāru, soft/hard roku pamatstratēģiju un dažus skaita noviržu gājienus."""
    if not hand:
        return "STAND"

    total, soft = _hand_value(hand)
    if total >= 21:
        return "STAND"

    dealer = _card_value(dealer_upcard)
    count = _running_count(history)

    if can_split and len(hand) == 2:
        pair = _card_value(hand[0])
        if _should_split(pair, dealer):
            return "SPLIT"

    if soft:
        if total >= 19:
            return "STAND"
        if total == 18:
            if 3 <= dealer <= 6 and can_double:
                return "DOUBLE"
            return "STAND" if dealer in {2, 7, 8} else "HIT"
        if 3 <= dealer <= 6 and total in {13, 14, 15, 16, 17} and can_double:
            return "DOUBLE"
        return "HIT"

    if total == 16 and dealer == 10 and count >= 0:
        return "STAND"
    if total == 15 and dealer == 10 and count >= 4:
        return "STAND"
    if total == 12 and dealer == 3 and count >= 2:
        return "STAND"
    if total == 12 and dealer == 2 and count >= 3:
        return "STAND"

    if total >= 17:
        return "STAND"
    if 13 <= total <= 16:
        return "STAND" if dealer <= 6 else "HIT"
    if total == 12:
        return "STAND" if 4 <= dealer <= 6 else "HIT"
    if total == 11:
        return "DOUBLE" if can_double else "HIT"
    if total == 10:
        return "DOUBLE" if can_double and dealer <= 9 else "HIT"
    if total == 9:
        return "DOUBLE" if can_double and 3 <= dealer <= 6 else "HIT"
    return "HIT"


def _card_value(card: str) -> int:
    rank = card[:-1]
    if rank == "A":
        return 11
    if rank in {"T", "J", "Q", "K"}:
        return 10
    return int(rank)


def _hand_value(hand: list[str]) -> tuple[int, bool]:
    total = 0
    aces = 0
    for card in hand:
        rank = card[:-1]
        if rank == "A":
            total += 1
            aces += 1
        else:
            total += _card_value(card)
    soft = aces > 0 and total + 10 <= 21
    if soft:
        total += 10
    return total, soft


def _running_count(history: list[str]) -> int:
    return sum(_HI_LO.get(card[:-1], 0) for card in history if len(card) >= 2)


def _should_split(pair: int, dealer: int) -> bool:
    if pair in {11, 8}:
        return True
    if pair in {2, 3}:
        return 2 <= dealer <= 7
    if pair == 4:
        return dealer in {5, 6}
    if pair == 6:
        return 2 <= dealer <= 6
    if pair == 7:
        return 2 <= dealer <= 7
    if pair == 9:
        return 2 <= dealer <= 6 or dealer in {8, 9}
    return False
