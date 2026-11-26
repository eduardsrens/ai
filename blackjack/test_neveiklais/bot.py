"""Vienkāršs testa bots ar apzināti vāju stratēģiju."""

BOT_NAME = "YOLO-17 bot"


def place_bet(bankroll: int, history: list[str], decks_remaining: float) -> int:
    """Vienmēr liek maksimālo atļauto likmi, neņemot vērā kāršu vēsturi."""
    return min(200, bankroll)


def decide_action(
    hand: list[str],
    dealer_upcard: str,
    history: list[str],
    can_double: bool,
    can_split: bool,
) -> str:
    """Vienkāršā stratēģija: velk līdz 17 un nekad nedubulto vai nesadala."""
    total = _hand_value(hand)
    return "STAND" if total >= 17 else "HIT"


def _hand_value(hand: list[str]) -> int:
    total = 0
    aces = 0
    for card in hand:
        rank = card[:-1]
        if rank == "A":
            total += 11
            aces += 1
        elif rank in {"T", "J", "Q", "K"}:
            total += 10
        else:
            total += int(rank)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total
