import random
from pathlib import Path
import tkinter as tk
from functools import lru_cache
from tkinter import ttk


RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10")
CARD_VALUES = (11, 2, 3, 4, 5, 6, 7, 8, 9, 10)
DECKS = 4
CARDS_PER_DECK = 52
TOTAL_CARDS = DECKS * CARDS_PER_DECK
SHUFFLE_AFTER_CARDS = TOTAL_CARDS // 4
DECK_COUNTS = (4 * DECKS,) * 9 + (16 * DECKS,)
SUITS = (("♠", "black"), ("♥", "red"), ("♦", "red"), ("♣", "black"))
FACES = (
    ("A", 0), ("2", 1), ("3", 2), ("4", 3), ("5", 4), ("6", 5),
    ("7", 6), ("8", 7), ("9", 8), ("10", 9), ("J", 9), ("Q", 9), ("K", 9),
)
STARTING_TOKENS = 1000
AUTOPLAY_BASE_BET = 5
AUTOPLAY_MAX_BET = 25
AUTOPLAY_START_DELAY_MS = 150
AUTOPLAY_ROUND_DELAY_MS = 100
BOT_ACTION_DELAY_MS = 50
MAX_PLAYER_HANDS = 4
BACKGROUND = "#0b1220"
FELT = "#145b43"
TEXT = "#e7edf7"
MUTED = "#a9b8cb"
GOLD = "#ffd166"


def rank_of(card):
    return card[0] if isinstance(card, tuple) else card


def build_shoe():
    return [
        (rank, suit_symbol, face)
        for _ in range(DECKS)
        for suit_symbol, _ in SUITS
        for face, rank in FACES
    ]


def needs_shuffle(cards_remaining):
    return cards_remaining <= TOTAL_CARDS - SHUFFLE_AFTER_CARDS


def payout_return(bet, outcome, blackjack=False):
    if outcome == "win":
        return bet * (2.5 if blackjack else 2)
    if outcome == "push":
        return bet
    return 0


def hand_value(cards):
    ranks = [rank_of(card) for card in cards]
    total = sum(CARD_VALUES[card] for card in ranks)
    soft_aces = sum(card == 0 for card in ranks)
    while total > 21 and soft_aces:
        total -= 10
        soft_aces -= 1
    return total, soft_aces


def should_split_pair(player_cards, dealer_upcard):
    if (
        len(player_cards) != 2
        or rank_of(player_cards[0]) != rank_of(player_cards[1])
    ):
        return False

    pair = rank_of(player_cards[0])
    if pair in (0, 7):
        return True
    if pair in (1, 2):
        return 1 <= dealer_upcard <= 6
    if pair == 3:
        return dealer_upcard in (4, 5)
    if pair == 5:
        return 1 <= dealer_upcard <= 5
    if pair == 6:
        return 1 <= dealer_upcard <= 6
    if pair == 8:
        return dealer_upcard in (1, 2, 3, 4, 5, 7, 8)
    return False


class CardCountingBot:
    """Finite-shoe EV for hit, stand, and double; standard pair-split strategy."""

    def __init__(self, visible_unseen_counts, dealer_upcard):
        self.initial_counts = tuple(visible_unseen_counts)
        self.dealer_upcard = dealer_upcard

    @lru_cache(maxsize=None)
    def _dealer_outcomes(self, total, soft_aces, counts):
        if total >= 17:
            return ((total, 1.0),)

        remaining = sum(counts)
        if remaining == 0:
            return ((total, 1.0),)

        outcomes = {}
        for card, count in enumerate(counts):
            if not count:
                continue
            next_counts = list(counts)
            next_counts[card] -= 1
            next_total = total + CARD_VALUES[card]
            next_soft = soft_aces + (card == 0)
            while next_total > 21 and next_soft:
                next_total -= 10
                next_soft -= 1

            if next_total > 21:
                outcomes[22] = outcomes.get(22, 0.0) + count / remaining
                continue

            for result, probability in self._dealer_outcomes(
                next_total, next_soft, tuple(next_counts)
            ):
                outcomes[result] = (
                    outcomes.get(result, 0.0)
                    + count / remaining * probability
                )
        return tuple(sorted(outcomes.items()))

    @lru_cache(maxsize=None)
    def _stand_value(self, player_total, drawn_counts, hole_weights):
        unseen_counts = tuple(
            count - drawn
            for count, drawn in zip(self.initial_counts, drawn_counts)
        )
        total_hole_weight = sum(hole_weights)
        if total_hole_weight == 0:
            return 0.5

        value = 0.0
        for hole_card, weight in enumerate(hole_weights):
            if not weight:
                continue

            dealer_counts = list(unseen_counts)
            dealer_counts[hole_card] -= 1
            dealer_total, dealer_soft = hand_value(
                (self.dealer_upcard, hole_card)
            )
            if dealer_total == 21:
                result_value = 0.0
            else:
                result_value = 0.0
                for dealer_result, probability in self._dealer_outcomes(
                    dealer_total, dealer_soft, tuple(dealer_counts)
                ):
                    if dealer_result == 22 or player_total > dealer_result:
                        result_value += probability
                    elif player_total == dealer_result:
                        result_value += probability * 0.5
            value += weight / total_hole_weight * result_value
        return value

    @lru_cache(maxsize=None)
    def _best_value(self, player_total, soft_aces, drawn_counts, hole_weights):
        unseen_counts = tuple(
            count - drawn
            for count, drawn in zip(self.initial_counts, drawn_counts)
        )
        stand_value = self._stand_value(player_total, drawn_counts, hole_weights)
        accessible_total = sum(unseen_counts) - 1
        total_hole_weight = sum(hole_weights)
        if player_total >= 21 or accessible_total <= 0 or total_hole_weight == 0:
            return stand_value

        hit_value = 0.0
        for card, count in enumerate(unseen_counts):
            if not count:
                continue
            next_hole_weights = tuple(
                weight * (count - (hole_card == card))
                for hole_card, weight in enumerate(hole_weights)
            )
            draw_weight = sum(next_hole_weights)
            if draw_weight == 0:
                continue

            next_total = player_total + CARD_VALUES[card]
            next_soft = soft_aces + (card == 0)
            while next_total > 21 and next_soft:
                next_total -= 10
                next_soft -= 1
            probability = draw_weight / (
                total_hole_weight * accessible_total
            )
            if next_total > 21:
                continue

            next_drawn = list(drawn_counts)
            next_drawn[card] += 1
            hit_value += probability * self._best_value(
                next_total,
                next_soft,
                tuple(next_drawn),
                next_hole_weights,
            )
        return max(stand_value, hit_value)

    def _double_equity(self, player_total, soft_aces):
        drawn_counts = (0,) * len(RANKS)
        hole_weights = self.initial_counts
        accessible_total = sum(self.initial_counts) - 1
        total_hole_weight = sum(hole_weights)
        if accessible_total <= 0 or total_hole_weight == 0:
            return 0.0

        value = 0.0
        for card, count in enumerate(self.initial_counts):
            if not count:
                continue
            next_hole_weights = tuple(
                weight * (count - (hole_card == card))
                for hole_card, weight in enumerate(hole_weights)
            )
            draw_weight = sum(next_hole_weights)
            if draw_weight == 0:
                continue

            next_total = player_total + CARD_VALUES[card]
            next_soft = soft_aces + (card == 0)
            while next_total > 21 and next_soft:
                next_total -= 10
                next_soft -= 1
            probability = draw_weight / (
                total_hole_weight * accessible_total
            )
            if next_total <= 21:
                next_drawn = list(drawn_counts)
                next_drawn[card] += 1
                value += probability * self._stand_value(
                    next_total, tuple(next_drawn), next_hole_weights
                )
        return value

    def analyze(self, player_cards, can_double=False, can_split=False):
        try:
            return self._analyze(player_cards, can_double, can_split)
        finally:
            self._best_value.cache_clear()
            self._stand_value.cache_clear()
            self._dealer_outcomes.cache_clear()

    def _analyze(self, player_cards, can_double=False, can_split=False):
        player_total, soft_aces = hand_value(player_cards)
        drawn_counts = (0,) * len(RANKS)
        hole_weights = self.initial_counts
        stand_value = self._stand_value(
            player_total, drawn_counts, hole_weights
        )
        accessible_total = sum(self.initial_counts) - 1

        if player_total >= 21 or accessible_total <= 0:
            return "stay", stand_value, stand_value, None

        hit_value = 0.0
        for card, count in enumerate(self.initial_counts):
            if not count:
                continue
            next_hole_weights = tuple(
                weight * (count - (hole_card == card))
                for hole_card, weight in enumerate(hole_weights)
            )
            draw_weight = sum(next_hole_weights)
            if draw_weight == 0:
                continue

            next_total = player_total + CARD_VALUES[card]
            next_soft = soft_aces + (card == 0)
            while next_total > 21 and next_soft:
                next_total -= 10
                next_soft -= 1
            probability = draw_weight / (
                sum(hole_weights) * accessible_total
            )
            if next_total <= 21:
                next_drawn = list(drawn_counts)
                next_drawn[card] += 1
                hit_value += probability * self._best_value(
                    next_total,
                    next_soft,
                    tuple(next_drawn),
                    next_hole_weights,
                )

        action = "hit" if hit_value > stand_value else "stay"
        double_return = None
        if can_double:
            double_equity = self._double_equity(player_total, soft_aces)
            double_return = 2 * (2 * double_equity - 1)
            best_single_return = 2 * max(hit_value, stand_value) - 1
            if double_return > best_single_return:
                action = "double"
        if can_split and should_split_pair(
            player_cards, self.dealer_upcard
        ):
            action = "split"
        return action, hit_value, stand_value, double_return


class BlackjackGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Blackjack - Kāršu skaitīšanas bots")
        self.root.geometry("1060x820")
        self.root.minsize(900, 740)
        self.root.configure(bg=BACKGROUND)
        icon_path = Path(__file__).with_name("blackjack.ico")
        if (
            self.root.tk.call("tk", "windowingsystem") == "win32"
            and icon_path.is_file()
        ):
            self.root.iconbitmap(str(icon_path))

        self.shoe = []
        self.seen_counts = [0] * len(RANKS)
        self.player_hands = []
        self.hand_bets = []
        self.hand_done = []
        self.hand_busted = []
        self.hand_blackjack = []
        self.hand_split_aces = []
        self.active_hand_index = 0
        self.dealer_cards = []
        self.bankroll = STARTING_TOKENS
        self.current_bet = 0
        self.bet_var = tk.StringVar(value="25")
        self.bankroll_var = tk.StringVar()
        self.hole_revealed = False
        self.active = False
        self.bot_running = False
        self.autoplay_enabled = True
        self.wins = 0
        self.losses = 0
        self.pushes = 0
        self.status_var = tk.StringVar(value="Bots automātiski sāk spēli...")
        self.count_var = tk.StringVar()
        self.advice_var = tk.StringVar(
            value="Bots analizē redzamo kāršu sastāvu un aprēķina gājienu EV."
        )
        self.score_var = tk.StringVar()

        self._build_ui()
        self._update_info()
        self.root.after(AUTOPLAY_START_DELAY_MS, self._start_autoplay_round)

    @property
    def player_cards(self):
        if not self.player_hands:
            return []
        return self.player_hands[self.active_hand_index]

    def _build_ui(self):
        style = ttk.Style()
        style.configure("Game.TFrame", background=BACKGROUND)
        style.configure(
            "Title.TLabel",
            background=BACKGROUND,
            foreground=TEXT,
            font=("Segoe UI", 22, "bold"),
        )
        style.configure(
            "Info.TLabel",
            background=BACKGROUND,
            foreground=MUTED,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Status.TLabel",
            background=BACKGROUND,
            foreground=GOLD,
            font=("Segoe UI", 13, "bold"),
        )
        style.configure(
            "Balance.TLabel",
            background=BACKGROUND,
            foreground=GOLD,
            font=("Segoe UI", 13, "bold"),
        )
        style.configure("Game.TButton", font=("Segoe UI", 10, "bold"), padding=8)

        frame = ttk.Frame(self.root, style="Game.TFrame", padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame, text="BLACKJACK", style="Title.TLabel"
        ).pack(pady=(0, 2))
        ttk.Label(
            frame,
            text="Bots automātiski spēlē un pielāgo 5–25 žetonu likmi skaitam",
            style="Info.TLabel",
        ).pack(pady=(0, 8))
        ttk.Label(frame, textvariable=self.count_var, style="Info.TLabel").pack()
        ttk.Label(frame, textvariable=self.score_var, style="Info.TLabel").pack(
            pady=(0, 12)
        )
        bankroll_row = ttk.Frame(frame, style="Game.TFrame")
        bankroll_row.pack(pady=(0, 10))
        ttk.Label(
            bankroll_row,
            textvariable=self.bankroll_var,
            style="Balance.TLabel",
        ).pack(side="left", padx=(0, 18))
        ttk.Label(
            bankroll_row, text="Likme:", style="Info.TLabel"
        ).pack(side="left", padx=(0, 6))
        self.bet_spinbox = ttk.Spinbox(
            bankroll_row,
            from_=1,
            to=STARTING_TOKENS,
            increment=5,
            width=8,
            textvariable=self.bet_var,
            justify="center",
        )
        self.bet_spinbox.pack(side="left")
        ttk.Label(
            bankroll_row, text="žetoni", style="Info.TLabel"
        ).pack(side="left", padx=(6, 0))

        table = tk.Frame(frame, bg=FELT, highlightthickness=2, highlightbackground="#27785a")
        table.pack(fill="both", expand=True, pady=4)
        self.dealer_label = tk.Label(
            table, text="DĪLERIS", bg=FELT, fg=TEXT,
            font=("Segoe UI", 12, "bold")
        )
        self.dealer_label.pack(pady=(18, 5))
        self.dealer_cards_frame = tk.Frame(table, bg=FELT)
        self.dealer_cards_frame.pack(pady=(0, 22))
        self.player_label = tk.Label(
            table, text="TAVAS KĀRTIS", bg=FELT, fg=TEXT,
            font=("Segoe UI", 12, "bold")
        )
        self.player_label.pack(pady=(8, 5))
        self.player_cards_frame = tk.Frame(table, bg=FELT)
        self.player_cards_frame.pack(pady=(0, 16))
        self.total_label = tk.Label(
            table, text="", bg=FELT, fg=GOLD, font=("Segoe UI", 13, "bold")
        )
        self.total_label.pack(pady=(0, 12))

        ttk.Label(frame, textvariable=self.status_var, style="Status.TLabel").pack(
            pady=(10, 5)
        )
        ttk.Label(
            frame,
            textvariable=self.advice_var,
            style="Info.TLabel",
            wraplength=850,
            justify="center",
        ).pack(pady=(0, 12))

        controls = ttk.Frame(frame, style="Game.TFrame")
        controls.pack()
        self.new_button = ttk.Button(
            controls, text="Jauna spēle", style="Game.TButton", command=self.new_round
        )
        self.new_button.grid(row=0, column=0, padx=4)
        self.hit_button = ttk.Button(
            controls, text="Ņemt kārti", style="Game.TButton", command=self.hit
        )
        self.hit_button.grid(row=0, column=1, padx=4)
        self.stand_button = ttk.Button(
            controls, text="Palikt", style="Game.TButton", command=self.stand
        )
        self.stand_button.grid(row=0, column=2, padx=4)
        self.advice_button = ttk.Button(
            controls,
            text="Bot ieteikums",
            style="Game.TButton",
            command=self.show_advice,
        )
        self.advice_button.grid(row=0, column=3, padx=4)
        self.bot_button = ttk.Button(
            controls,
            text="Lai bots spēlē",
            style="Game.TButton",
            command=self.play_bot,
        )
        self.bot_button.grid(row=0, column=4, padx=4)
        self.double_button = ttk.Button(
            controls,
            text="Dubultot",
            style="Game.TButton",
            command=self.double_down,
        )
        self.double_button.grid(row=0, column=5, padx=4)
        self.split_button = ttk.Button(
            controls,
            text="Dalīt pāri",
            style="Game.TButton",
            command=self.split_hand,
        )
        self.split_button.grid(row=0, column=6, padx=4)

        ttk.Label(
            frame,
            text=(
                "Noteikumi: 4 kavas; pēc 52 izspēlētām kārtīm kava tiek "
                "sajaukta. Dīleris stāv pie 17 (arī soft 17). Blackjack "
                "maksā 3:2. Var dubultot sākuma divas kārtis un pēc dalīšanas; "
                "līdz četrām rokām, dalot vienādas kāršu vērtības. Dūžu pāri "
                "pēc dalīšanas saņem pa vienai kārtij. Bots precīzi modelē "
                "ņemšanas/palikšanas un dubultošanas EV, bet dalīšanai izmanto "
                "standarta pamatstratēģiju; apdrošināšanas un padošanās nav."
            ),
            style="Info.TLabel",
            wraplength=850,
            justify="center",
        ).pack(pady=(12, 0))
        self.bet_spinbox.configure(to=self.bankroll)
        self._set_controls()

    def _ensure_shoe(self):
        if not self.shoe or needs_shuffle(len(self.shoe)):
            self.shoe = build_shoe()
            random.shuffle(self.shoe)
            self.seen_counts = [0] * len(RANKS)
            if self.bankroll:
                self.status_var.set(
                    f"Kava sajaukta no jauna ({DECKS} kavas, 208 kārtis)."
                )

    def _draw(self, visible):
        if not self.shoe:
            raise RuntimeError("Kavā vairs nav kāršu; sāciet jaunu partiju.")
        card = self.shoe.pop()
        if visible:
            self.seen_counts[rank_of(card)] += 1
        return card

    def _unseen_counts(self):
        return tuple(
            count - seen for count, seen in zip(DECK_COUNTS, self.seen_counts)
        )

    def _running_count(self):
        return sum(
            count * (1 if 1 <= card <= 5 else -1 if card in (0, 9) else 0)
            for card, count in enumerate(self.seen_counts)
        )

    def _true_count(self):
        unseen = sum(self._unseen_counts())
        decks_left = max(unseen / CARDS_PER_DECK, 0.25)
        return self._running_count() / decks_left

    def _autoplay_bet(self):
        if not self.shoe or needs_shuffle(len(self.shoe)):
            return min(AUTOPLAY_BASE_BET, self.bankroll)
        units = min(
            AUTOPLAY_MAX_BET // AUTOPLAY_BASE_BET,
            max(1, 1 + int(max(self._true_count(), 0))),
        )
        return min(self.bankroll, AUTOPLAY_BASE_BET * units)

    def _count_text(self):
        running_count = self._running_count()
        true_count = self._true_count()
        dealt_since_shuffle = TOTAL_CARDS - len(self.shoe)
        until_shuffle = max(SHUFFLE_AFTER_CARDS - dealt_since_shuffle, 0)
        return (
            f"Hi-Lo skaitītājs: {running_count:+d}   |   "
            f"Pielāgotais skaits: {true_count:+.1f}   |   "
            f"Redzētas: {sum(self.seen_counts)}   |   "
            f"Līdz jaukšanai: {until_shuffle} kārtis"
        )

    def _update_info(self):
        self.count_var.set(self._count_text())
        self.score_var.set(
            f"Uzvaras: {self.wins}    Zaudējumi: {self.losses}    "
            f"Neizšķirti: {self.pushes}"
        )
        self.bankroll_var.set(f"Žetoni: {self.bankroll:g}")
        self.bet_spinbox.configure(to=max(self.bankroll, 1))
        self._render_cards()
        self._set_controls()

    def _card_widget(self, parent, card, hidden=False):
        card_frame = tk.Frame(
            parent,
            bg="#fdfcf8" if not hidden else "#18365a",
            width=76,
            height=108,
            highlightthickness=2,
            highlightbackground="#d7dce5" if not hidden else "#9bb6d5",
        )
        card_frame.pack(side="left", padx=5)
        card_frame.pack_propagate(False)
        if hidden:
            tk.Label(
                card_frame,
                text="♠  ♦\n♥  ♣\n♠  ♦",
                bg="#18365a",
                fg="#dbe9fb",
                font=("Segoe UI Symbol", 18, "bold"),
                justify="center",
            ).pack(expand=True)
            return

        _, suit, face = card
        suit_color = dict(SUITS)[suit]
        corner = tk.Label(
            card_frame,
            text=f"{face}\n{suit}",
            bg="#fdfcf8",
            fg=suit_color,
            font=("Segoe UI", 10, "bold"),
            justify="center",
        )
        corner.place(x=4, y=2)
        tk.Label(
            card_frame,
            text=suit,
            bg="#fdfcf8",
            fg=suit_color,
            font=("Segoe UI Symbol", 34),
        ).place(relx=0.5, rely=0.52, anchor="center")
        tk.Label(
            card_frame,
            text=f"{suit}\n{face}",
            bg="#fdfcf8",
            fg=suit_color,
            font=("Segoe UI", 10, "bold"),
            justify="center",
        ).place(relx=1.0, rely=1.0, anchor="se", x=-4, y=-2)

    def _render_cards(self, reveal_dealer=False):
        for frame in (self.dealer_cards_frame, self.player_cards_frame):
            for child in frame.winfo_children():
                child.destroy()

        for index, card in enumerate(self.dealer_cards):
            hidden = index == 1 and self.active and not reveal_dealer
            self._card_widget(self.dealer_cards_frame, card, hidden)
        for index, hand in enumerate(self.player_hands):
            hand_frame = tk.Frame(self.player_cards_frame, bg=FELT)
            hand_frame.pack(pady=3)
            total, _ = hand_value(hand)
            is_active = index == self.active_hand_index and self.active
            marker = "  ← BOTA GĀJIENS" if is_active else ""
            tk.Label(
                hand_frame,
                text=(
                    f"Roka {index + 1} · likme {self.hand_bets[index]} · "
                    f"summa {total}{marker}"
                ),
                bg=FELT,
                fg=GOLD if is_active else TEXT,
                font=("Segoe UI", 10, "bold"),
            ).pack()
            cards_frame = tk.Frame(hand_frame, bg=FELT)
            cards_frame.pack()
            for card in hand:
                self._card_widget(cards_frame, card)

        if self.player_cards:
            total, _ = hand_value(self.player_cards)
            self.total_label.config(
                text=f"Aktīvās rokas summa: {total}"
                if self.active
                else f"Pēdējās rokas summa: {total}"
            )
        else:
            self.total_label.config(text="")

    def _set_controls(self):
        state = "normal" if self.active and not self.bot_running else "disabled"
        for button in (self.hit_button, self.stand_button, self.advice_button):
            button.configure(state=state)
        self.bot_button.configure(state=state)
        self.double_button.configure(
            state="normal" if state == "normal" and self._can_double() else "disabled"
        )
        self.split_button.configure(
            state="normal" if state == "normal" and self._can_split() else "disabled"
        )
        self.new_button.configure(
            state="normal" if not self.active and self.bankroll > 0 else "disabled"
        )
        self.bet_spinbox.configure(state="disabled" if self.active else "normal")

    def new_round(self):
        if self.active:
            return
        try:
            bet = int(self.bet_var.get())
        except ValueError:
            self.status_var.set("Likmei jābūt veselam žetonu skaitam.")
            return
        if bet < 1 or bet > self.bankroll:
            self.status_var.set(
                f"Likmei jābūt no 1 līdz {self.bankroll:g} žetoniem."
            )
            return
        self._ensure_shoe()
        self.current_bet = bet
        self.bankroll -= bet
        self.player_hands = [[self._draw(True), self._draw(True)]]
        self.hand_bets = [bet]
        self.hand_done = [False]
        self.hand_busted = [False]
        self.hand_blackjack = [False]
        self.hand_split_aces = [False]
        self.active_hand_index = 0
        self.dealer_cards = [self._draw(True), self._draw(False)]
        self.hole_revealed = False
        self.active = True
        self.bot_running = False
        self.advice_var.set(
            "Bots aprēķina gājienu no atlikušajām kārtīm; dīlera aizklātā "
            "kārts tiek varbūtiski modelēta."
        )
        self.status_var.set(
            f"Likme: {bet} žetoni. Bots analizē kārtis un spēlē."
        )
        player_total, _ = hand_value(self.player_cards)
        player_natural = player_total == 21
        dealer_natural = hand_value(self.dealer_cards)[0] == 21
        if player_natural or dealer_natural:
            self.hand_blackjack[0] = player_natural
            self.hand_done[0] = True
            self._reveal_hole_card()
            self._finish_round()
        else:
            self._update_info()

    def _start_autoplay_round(self):
        if not self.autoplay_enabled or self.active or self.bankroll <= 0:
            return
        bet = self._autoplay_bet()
        self.bet_var.set(str(bet))
        self.new_round()
        if self.active:
            self.play_bot()

    def _reveal_hole_card(self):
        if self.dealer_cards and not self.hole_revealed:
            self.seen_counts[self.dealer_cards[1]] += 1
            self.hole_revealed = True

    def _can_double(self):
        if not self.active or not self.player_hands:
            return False
        index = self.active_hand_index
        return (
            len(self.player_cards) == 2
            and not self.hand_split_aces[index]
            and self.bankroll >= self.hand_bets[index]
        )

    def _can_split(self):
        if (
            not self.active
            or not self.player_hands
            or len(self.player_hands) >= MAX_PLAYER_HANDS
        ):
            return False
        index = self.active_hand_index
        return (
            len(self.player_cards) == 2
            and not self.hand_split_aces[index]
            and rank_of(self.player_cards[0]) == rank_of(self.player_cards[1])
            and self.bankroll >= self.hand_bets[index]
        )

    def hit(self):
        if not self.active or self.bot_running:
            return
        self.player_cards.append(self._draw(True))
        total, _ = hand_value(self.player_cards)
        if total > 21:
            self.hand_busted[self.active_hand_index] = True
            self._advance_hand()
        elif total == 21:
            self._advance_hand()
        else:
            self._update_info()

    def stand(self):
        if not self.active or self.bot_running:
            return
        self._advance_hand()

    def double_down(self, by_bot=False):
        if (
            not self.active
            or (self.bot_running and not by_bot)
            or not self._can_double()
        ):
            return
        index = self.active_hand_index
        extra_bet = self.hand_bets[index]
        self.bankroll -= extra_bet
        self.hand_bets[index] += extra_bet
        self.current_bet += extra_bet
        self.player_cards.append(self._draw(True))
        if hand_value(self.player_cards)[0] > 21:
            self.hand_busted[index] = True
        self._advance_hand()

    def split_hand(self, by_bot=False):
        if (
            not self.active
            or (self.bot_running and not by_bot)
            or not self._can_split()
        ):
            return
        index = self.active_hand_index
        first_card, second_card = self.player_cards
        split_aces = rank_of(first_card) == 0
        bet = self.hand_bets[index]
        self.bankroll -= bet
        self.current_bet += bet
        self.player_hands[index:index + 1] = [[first_card], [second_card]]
        self.hand_bets[index:index + 1] = [bet, bet]
        self.hand_done[index:index + 1] = [False, False]
        self.hand_busted[index:index + 1] = [False, False]
        self.hand_blackjack[index:index + 1] = [False, False]
        self.hand_split_aces[index:index + 1] = [split_aces, split_aces]
        self.player_hands[index].append(self._draw(True))
        self.player_hands[index + 1].append(self._draw(True))
        self.active_hand_index = index

        if split_aces:
            self.hand_done[index:index + 2] = [True, True]
            self._advance_hand()
        elif hand_value(self.player_cards)[0] == 21:
            self._advance_hand()
        else:
            self._update_info()
            if self.bot_running:
                self.root.after(BOT_ACTION_DELAY_MS, self._bot_step)

    def _advance_hand(self):
        current_index = self.active_hand_index
        self.hand_done[current_index] = True
        for index in range(current_index + 1, len(self.player_hands)):
            if self.hand_done[index]:
                continue
            total, _ = hand_value(self.player_hands[index])
            if total >= 21 or self.hand_split_aces[index]:
                self.hand_done[index] = True
                continue
            self.active_hand_index = index
            self._update_info()
            if self.bot_running:
                self.root.after(BOT_ACTION_DELAY_MS, self._bot_step)
            return
        self.bot_running = False
        self._dealer_turn()

    def _dealer_turn(self):
        self._reveal_hole_card()
        dealer_total, _ = hand_value(self.dealer_cards)
        if any(not busted for busted in self.hand_busted):
            while dealer_total < 17:
                self.dealer_cards.append(self._draw(True))
                dealer_total, _ = hand_value(self.dealer_cards)
        self._update_info()
        self._finish_round()

    def _finish_round(self):
        self.active = False
        self.bot_running = False
        dealer_total, _ = hand_value(self.dealer_cards)
        dealer_natural = hand_value(self.dealer_cards[:2])[0] == 21
        summaries = []
        for index, cards in enumerate(self.player_hands):
            blackjack = self.hand_blackjack[index]
            if self.hand_busted[index]:
                outcome = "loss"
            elif dealer_natural and blackjack:
                outcome = "push"
            elif dealer_natural:
                outcome = "loss"
            elif blackjack:
                outcome = "win"
            else:
                player_total, _ = hand_value(cards)
                if dealer_total > 21 or player_total > dealer_total:
                    outcome = "win"
                elif player_total == dealer_total:
                    outcome = "push"
                else:
                    outcome = "loss"

            if outcome == "win":
                self.wins += 1
                self.bankroll += payout_return(
                    self.hand_bets[index],
                    "win",
                    blackjack=blackjack,
                )
                result = "Blackjack!" if blackjack else "Uzvara"
            elif outcome == "push":
                self.pushes += 1
                self.bankroll += payout_return(self.hand_bets[index], "push")
                result = "Neizšķirts"
            else:
                self.losses += 1
                result = "Zaudējums"
            summaries.append(f"Roka {index + 1}: {result}")

        self.current_bet = 0
        self.status_var.set(" · ".join(summaries))
        refilled = self.autoplay_enabled and self.bankroll <= 0
        if refilled:
            self.bankroll = STARTING_TOKENS
            self.shoe = []
            self.seen_counts = [0] * len(RANKS)
            self._ensure_shoe()
            self.status_var.set(
                f"{' · '.join(summaries)} · "
                f"Žetoni papildināti līdz {STARTING_TOKENS}."
            )
            self.advice_var.set(
                "Bots turpina spēli ar jaunu četru kavu kavu."
            )
        elif self.bankroll:
            self.advice_var.set(
                "Bots automātiski sāks nākamo partiju pēc īsas pauzes."
            )
        else:
            self.advice_var.set("Žetoni beigušies — spēle ir galā.")
        self._update_info()
        if self.autoplay_enabled:
            self.root.after(
                AUTOPLAY_ROUND_DELAY_MS, self._start_autoplay_round
            )

    def _bot_analysis(self):
        bot = CardCountingBot(
            self._unseen_counts(), rank_of(self.dealer_cards[0])
        )
        return bot.analyze(
            self.player_cards,
            can_double=self._can_double(),
            can_split=self._can_split(),
        )

    def show_advice(self):
        if not self.active or self.bot_running:
            return
        action, hit_value, stand_value, double_return = self._bot_analysis()
        action_text = {
            "hit": "ŅEMT KĀRTI",
            "stay": "PALIKT",
            "double": "DUBULTOT",
            "split": "DALĪT PĀRI",
        }[action]
        double_text = (
            f"Dubultošanas EV: {double_return:.3f}. "
            if double_return is not None
            else ""
        )
        self.advice_var.set(
            f"Bota ieteikums: {action_text}  |  "
            f"Ņemt vērtība: {hit_value:.3f}  |  "
            f"Palikt vērtība: {stand_value:.3f}. {double_text}"
            "Skaitītājs izmanto visas zināmās kārtis; dīlera aizklātā "
            "kārts tiek varbūtiski modelēta."
        )

    def play_bot(self):
        if not self.active or self.bot_running:
            return
        self.bot_running = True
        self._set_controls()
        self.status_var.set("Bots precīzi aprēķina labāko gājienu...")
        self.root.after(BOT_ACTION_DELAY_MS, self._bot_step)

    def _bot_step(self):
        if not self.active:
            self.bot_running = False
            return
        action, hit_value, stand_value, double_return = self._bot_analysis()
        action_text = {
            "hit": "ņem kārti",
            "stay": "paliek",
            "double": "dubulto likmi",
            "split": "dala pāri",
        }[action]
        double_text = (
            f"; dubultot {double_return:.3f}"
            if double_return is not None
            else ""
        )
        self.advice_var.set(
            f"Bots izvēlas {action_text} "
            f"(ņemt {hit_value:.3f}; palikt {stand_value:.3f}"
            f"{double_text})."
        )
        if action == "hit":
            self.player_cards.append(self._draw(True))
            total, _ = hand_value(self.player_cards)
            if total > 21:
                self.hand_busted[self.active_hand_index] = True
                self._advance_hand()
            elif total == 21:
                self._advance_hand()
            else:
                self._update_info()
                self.root.after(BOT_ACTION_DELAY_MS, self._bot_step)
        elif action == "double":
            self.double_down(by_bot=True)
        elif action == "split":
            self.split_hand(by_bot=True)
        else:
            self._advance_hand()


def main():
    root = tk.Tk()
    BlackjackGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
