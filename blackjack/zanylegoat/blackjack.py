"""Blackjack table: the bot plays the player hand and you deal."""

from dataclasses import dataclass
import random
import tkinter as tk
from tkinter import ttk

from bot import (
    BOT_NAME,
    analyze_hand,
    hand_value,
    learn_from_result,
    start_hand,
)


SUITS = ("♠", "♥", "♦", "♣")
RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
DECK_COUNT = 4
RESHUFFLE_REMAINING = 52


@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    @property
    def value(self):
        if self.rank == "A":
            return 11
        if self.rank in ("J", "Q", "K"):
            return 10
        return int(self.rank)

    def __str__(self):
        return f"{self.rank}{self.suit}"


def new_shoe():
    cards = [
        Card(rank, suit)
        for _ in range(DECK_COUNT)
        for suit in SUITS
        for rank in RANKS
    ]
    random.shuffle(cards)
    return cards


def is_blackjack(hand):
    return len(hand) == 2 and hand_value(hand)[0] == 21


def describe_decision(hand, dealer_upcard, dealer_hits_soft_17, seen_cards):
    total, soft = hand_value(hand)
    kind = "soft" if soft else "hard"
    action, values, running_count, true_count = analyze_hand(
        hand, dealer_upcard, dealer_hits_soft_17, seen_cards
    )
    ev_summary = " / ".join(
        f"{name.title()} {value:+.2f}"
        for name, value in values.items()
    )
    reason = (
        f"{kind} {total} vs dealer {dealer_upcard} | Sampled EV: {ev_summary} | "
        f"Hi-Lo count: {running_count} (true {true_count:+.1f})"
    )
    return action, reason


class BlackjackGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Blackjack — You Deal, Bot Plays")
        self.root.configure(bg="#0b3d2e")
        self.root.minsize(720, 560)
        self.shoe = new_shoe()
        self.player_hand = []
        self.dealer_hand = []
        self.round_active = False
        self.phase = "ready"
        self.double_down = False
        self.seen_cards = []
        self.hole_revealed = False

        tk.Label(
            root, text="BLACKJACK", font=("Segoe UI", 26, "bold"),
            fg="#f6e8bd", bg="#0b3d2e",
        ).pack(pady=(18, 0))
        tk.Label(
            root, text="You deal. The bot compares expected values and counts exposed cards.",
            font=("Segoe UI", 11), fg="#d0dfd4", bg="#0b3d2e",
        ).pack(pady=(0, 12))

        self.dealer_panel = self.make_hand_panel(root, "DEALER")
        self.player_panel = self.make_hand_panel(root, BOT_NAME)

        controls = tk.Frame(root, bg="#0b3d2e")
        controls.pack(pady=8)
        self.deal_button = tk.Button(
            controls, text="Deal new hand", command=self.start_round,
            font=("Segoe UI", 12, "bold"), bg="#e8bd55", fg="#17231c",
            activebackground="#f2d578", relief="flat", padx=18, pady=9,
        )
        self.deal_button.pack(side="left", padx=6)
        self.action_button = tk.Button(
            controls, text="Deal next card", command=self.deal_requested_card,
            font=("Segoe UI", 11, "bold"), bg="#f1f3ed", fg="#17231c",
            activebackground="#ffffff", relief="flat", padx=16, pady=9,
            state="disabled",
        )
        self.action_button.pack(side="left", padx=6)

        rule_frame = tk.Frame(root, bg="#0b3d2e")
        rule_frame.pack(pady=(6, 0))
        tk.Label(
            rule_frame, text="Dealer on soft 17:", fg="#d0dfd4", bg="#0b3d2e",
            font=("Segoe UI", 10),
        ).pack(side="left", padx=4)
        self.rule_menu = ttk.Combobox(
            rule_frame, state="readonly", width=16,
            values=("Stand (S17)", "Hit (H17)"),
        )
        self.rule_menu.current(0)
        self.rule_menu.pack(side="left", padx=4)
        self.status = tk.Label(
            root, text="Press “Deal new hand” to begin.",
            font=("Segoe UI", 12), fg="#fff5d6", bg="#0b3d2e",
            wraplength=680, justify="center",
        )
        self.status.pack(pady=(14, 4))
        self.detail = tk.Label(
            root, text="4-deck shoe • EV estimates • Hi-Lo card count • Online Q-learning",
            font=("Segoe UI", 9), fg="#b7c9bd", bg="#0b3d2e",
            wraplength=680, justify="center",
        )
        self.detail.pack(pady=(0, 12))

    def make_hand_panel(self, parent, title):
        panel = tk.Frame(parent, bg="#14533d", padx=16, pady=12)
        panel.pack(fill="x", padx=28, pady=6)
        tk.Label(
            panel, text=title, font=("Segoe UI", 11, "bold"),
            fg="#d4e4d7", bg="#14533d",
        ).pack(anchor="w")
        cards = tk.Frame(panel, bg="#14533d")
        cards.pack(anchor="w", pady=6)
        total = tk.Label(
            panel, text="Total: —", font=("Segoe UI", 10),
            fg="#f6e8bd", bg="#14533d",
        )
        total.pack(anchor="w")
        return cards, total

    @property
    def dealer_hits_soft_17(self):
        return self.rule_menu.get() == "Hit (H17)"

    def draw(self):
        if not self.shoe:
            self.shoe = new_shoe()
        return self.shoe.pop()

    def start_round(self):
        if len(self.shoe) <= RESHUFFLE_REMAINING:
            self.shoe = new_shoe()
            self.seen_cards = []
        self.player_hand = []
        self.dealer_hand = []
        self.hole_revealed = False
        start_hand()
        self.round_active = True
        self.double_down = False
        self.phase = "player"
        self.rule_menu.configure(state="disabled")
        self.deal_button.configure(state="disabled")
        self.detail.configure(text="Four decks • No betting, insurance, surrender, or splits.")
        self.player_hand.extend((self.draw(), self.draw()))
        self.dealer_hand.extend((self.draw(), self.draw()))
        self.seen_cards.extend(self.player_hand)
        self.seen_cards.append(self.dealer_hand[0])
        self.render_hands(hide_hole=True)

        player_natural = is_blackjack(self.player_hand)
        dealer_natural = is_blackjack(self.dealer_hand)
        if player_natural or dealer_natural:
            self.show_result()
        else:
            self.update_bot_turn()

    def update_bot_turn(self):
        if not self.round_active:
            return
        total, _ = hand_value(self.player_hand)
        if total > 21:
            self.show_result()
            return
        if total == 21:
            self.begin_dealer_turn()
            return
        action, reason = describe_decision(
            self.player_hand,
            self.dealer_hand[0],
            self.dealer_hits_soft_17,
            self.seen_cards,
        )
        if action == "stand":
            self.status.configure(text=f"Bot stands ({reason}). Now deal the dealer hand.")
            self.begin_dealer_turn()
        else:
            self.phase = "player"
            self.double_down = action == "double"
            button_text = "Deal bot's final card (DOUBLE)" if self.double_down else "Deal card to bot (HIT)"
            self.action_button.configure(text=button_text, state="normal")
            self.status.configure(text=f"Bot chooses {action.upper()} — {reason}. Deal the card.")

    def deal_requested_card(self):
        if not self.round_active:
            return
        if self.phase == "player":
            card = self.draw()
            self.player_hand.append(card)
            self.seen_cards.append(card)
            total, _ = hand_value(self.player_hand)
            self.render_hands(hide_hole=True)
            if total > 21:
                self.show_result()
            elif self.double_down or total == 21:
                self.begin_dealer_turn()
            else:
                self.update_bot_turn()
        elif self.phase == "dealer":
            card = self.draw()
            self.dealer_hand.append(card)
            self.seen_cards.append(card)
            self.render_hands(hide_hole=False)
            total, soft = hand_value(self.dealer_hand)
            if total < 17 or (total == 17 and soft and self.dealer_hits_soft_17):
                self.set_dealer_button()
            else:
                self.show_result()

    def begin_dealer_turn(self):
        if not self.round_active:
            return
        self.phase = "dealer"
        self.reveal_hole_card()
        self.render_hands(hide_hole=False)
        total, soft = hand_value(self.dealer_hand)
        if total < 17 or (total == 17 and soft and self.dealer_hits_soft_17):
            self.status.configure(text="Your turn: dealer must hit. Deal the dealer a card.")
            self.set_dealer_button()
        else:
            self.show_result()

    def set_dealer_button(self):
        self.action_button.configure(text="Deal card to dealer", state="normal")

    def show_result(self):
        self.round_active = False
        self.phase = "ready"
        self.reveal_hole_card()
        self.action_button.configure(state="disabled")
        self.deal_button.configure(state="normal")
        self.rule_menu.configure(state="readonly")
        self.render_hands(hide_hole=False)
        player_total, _ = hand_value(self.player_hand)
        dealer_total, _ = hand_value(self.dealer_hand)

        if is_blackjack(self.player_hand) and is_blackjack(self.dealer_hand):
            result = "Push — both hands have blackjack."
            reward = 0
        elif is_blackjack(self.player_hand):
            result = "Bot wins with blackjack!"
            reward = 1
        elif is_blackjack(self.dealer_hand):
            result = "Dealer wins with blackjack."
            reward = -1
        elif player_total > 21:
            result = "Dealer wins — the bot busted."
            reward = -1
        elif dealer_total > 21:
            result = "Bot wins — the dealer busted."
            reward = 1
        elif player_total > dealer_total:
            result = "Bot wins!"
            reward = 1
        elif player_total < dealer_total:
            result = "Dealer wins."
            reward = -1
        else:
            result = "Push — tie."
            reward = 0
        if self.double_down:
            reward *= 2
        learn_from_result(reward)
        self.status.configure(text=result)
        self.detail.configure(
            text=(
                f"Final totals — Bot: {player_total} | Dealer: {dealer_total} "
                f"| {len(self.seen_cards)} cards seen in this shoe"
            )
        )

    def reveal_hole_card(self):
        if len(self.dealer_hand) > 1 and not self.hole_revealed:
            self.seen_cards.append(self.dealer_hand[1])
            self.hole_revealed = True

    def render_hands(self, hide_hole):
        self.render_hand(self.dealer_panel, self.dealer_hand, hide_hole)
        self.render_hand(self.player_panel, self.player_hand, False)

    def render_hand(self, panel, hand, hide_hole):
        cards_frame, total_label = panel
        for child in cards_frame.winfo_children():
            child.destroy()
        for index, card in enumerate(hand):
            hidden = hide_hole and index == 1
            text = "?" if hidden else str(card)
            color = "#c0393b" if not hidden and card.suit in ("♥", "♦") else "#17231c"
            tk.Label(
                cards_frame, text=text, font=("Segoe UI", 16, "bold"),
                width=4, height=2, bg="#fffdf5" if not hidden else "#d2bd86",
                fg=color, relief="raised", bd=2,
            ).pack(side="left", padx=(0, 6))
        if not hand:
            total_label.configure(text="Total: —")
        elif hide_hole and len(hand) > 1:
            total_label.configure(text=f"Showing: {hand_value(hand[:1])[0]} + hidden card")
        else:
            total, soft = hand_value(hand)
            total_label.configure(text=f"Total: {total}" + (" (soft)" if soft else ""))


def main():
    root = tk.Tk()
    BlackjackGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
