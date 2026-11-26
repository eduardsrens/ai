"""Tkinter blackjack turnīrs pret visiem blackjack apakšmapju botiem."""

from __future__ import annotations

import importlib.util
import random
import sys
import time
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import messagebox, ttk


ROOT = Path(__file__).resolve().parent
RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A")
SUITS = ("H", "D", "C", "S")
SUIT_NAMES = {"H": "♥", "D": "♦", "C": "♣", "S": "♠"}
RED_SUITS = {"H", "D"}
BOT_TIME_LIMIT = 0.5


def hand_value(hand: list[str]) -> int:
    """Atgriež blackjack punktu skaitu, dūžus pēc vajadzības skaitot kā 1."""
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


def is_natural(hand: list[str], was_split: bool = False) -> bool:
    return not was_split and len(hand) == 2 and hand_value(hand) == 21


def make_shoe(deck_count: int) -> list[str]:
    shoe = [rank + suit for _ in range(deck_count) for suit in SUITS for rank in RANKS]
    random.shuffle(shoe)
    return shoe


@dataclass
class BotPlayer:
    name: str
    module: object
    bankroll: float
    hands: list[dict] = field(default_factory=list)
    bet: int = 0


def load_bots() -> tuple[list[BotPlayer], list[str]]:
    bots = []
    errors = []
    for index, bot_path in enumerate(sorted(ROOT.rglob("bot.py"))):
        if "__pycache__" in bot_path.parts:
            continue
        module_name = f"blackjack_bot_{index}_{bot_path.parent.name}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, bot_path)
            if spec is None or spec.loader is None:
                raise ImportError("Nevar ielādēt moduļa specifikāciju")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            try:
                spec.loader.exec_module(module)
            except Exception:
                sys.modules.pop(module_name, None)
                raise
            if not callable(getattr(module, "place_bet", None)):
                raise AttributeError("Trūkst place_bet funkcijas")
            if not callable(getattr(module, "decide_action", None)):
                raise AttributeError("Trūkst decide_action funkcijas")
            name = str(getattr(module, "BOT_NAME", bot_path.parent.name))
            bots.append(BotPlayer(name=name, module=module, bankroll=0))
        except Exception as exc:
            errors.append(f"{bot_path.relative_to(ROOT)}: {type(exc).__name__}: {exc}")
    return bots, errors


class BlackjackTournament:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Blackjack botu turnīrs")
        self.root.minsize(900, 680)
        self.root.configure(bg="#e8eef2")

        self.bots, load_errors = load_bots()
        self.round_number = 0
        self.settings = {}
        self.shoe = []
        self.history = []
        self.dealer_hand = []
        self.dealer_hole_hidden = False
        self.phase = "ready"
        self.auto_running = False
        self.after_id = None
        self.log_lines = []

        self._build_ui()
        self._refresh_scoreboard()
        self._draw_table()
        if load_errors:
            self._log("Botu ielādes kļūdas:")
            for error in load_errors:
                self._log("  " + error)
        if not self.bots:
            self._log("Nav atrasts neviens derīgs bots. Pievienojiet bot.py apakšmapei.")
        self._set_status("Iestatiet turnīru un spiediet “Jauns turnīrs” vai “Sākt auto”.")

    def _build_ui(self):
        settings = ttk.LabelFrame(self.root, text="Turnīra parametri", padding=8)
        settings.pack(fill="x", padx=10, pady=(10, 5))

        self.vars = {
            "rounds": tk.StringVar(value="100"),
            "bankroll": tk.StringVar(value="1000"),
            "decks": tk.StringVar(value="4"),
            "cut_percent": tk.StringVar(value="75"),
            "delay_ms": tk.StringVar(value="200"),
        }
        fields = (
            ("Partiju skaits", "rounds", 1, 100000),
            ("Sākuma čipi", "bankroll", 10, 100000000),
            ("Kavu skaits", "decks", 1, 16),
            ("Jaukt pie izspēlētiem %", "cut_percent", 50, 95),
            ("Auto pauze (ms)", "delay_ms", 0, 10000),
        )
        for column, (label, key, low, high) in enumerate(fields):
            frame = ttk.Frame(settings)
            frame.grid(row=0, column=column, padx=4, sticky="w")
            ttk.Label(frame, text=label).pack(anchor="w")
            ttk.Spinbox(
                frame,
                textvariable=self.vars[key],
                from_=low,
                to=high,
                width=12,
            ).pack()

        self.auto_dealer_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            settings,
            text="Automātisks dīleris",
            variable=self.auto_dealer_var,
        ).grid(row=0, column=len(fields), padx=10, sticky="w")

        controls = ttk.Frame(self.root, padding=(10, 3))
        controls.pack(fill="x")
        ttk.Button(controls, text="Jauns turnīrs", command=self.new_tournament).pack(side="left", padx=(0, 6))
        ttk.Button(controls, text="Nākamā partija", command=self.play_next_round).pack(side="left", padx=6)
        self.auto_button = ttk.Button(controls, text="Sākt auto", command=self.toggle_auto)
        self.auto_button.pack(side="left", padx=6)
        self.hit_button = ttk.Button(controls, text="Dīleris: ņemt kārti", command=self.dealer_hit, state="disabled")
        self.hit_button.pack(side="right", padx=4)
        self.stand_button = ttk.Button(controls, text="Dīleris: stāvēt", command=self.dealer_stand, state="disabled")
        self.stand_button.pack(side="right", padx=4)

        self.status_var = tk.StringVar()
        ttk.Label(self.root, textvariable=self.status_var, padding=(12, 4)).pack(fill="x")

        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.table = tk.Canvas(
            table_frame, height=260, bg="#176b45", highlightthickness=1,
            highlightbackground="#0c432b", yscrollincrement=24,
        )
        table_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=table_scroll.set)
        self.table.pack(side="left", fill="both", expand=True)
        table_scroll.pack(side="right", fill="y")

        lower = ttk.Panedwindow(self.root, orient="horizontal")
        lower.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        scores = ttk.LabelFrame(lower, text="Čipu tabula", padding=5)
        lower.add(scores, weight=3)
        self.score_tree = ttk.Treeview(scores, columns=("name", "chips", "status"), show="headings", height=8)
        self.score_tree.heading("name", text="Bots")
        self.score_tree.heading("chips", text="Čipi")
        self.score_tree.heading("status", text="Stāvoklis")
        self.score_tree.column("name", width=220)
        self.score_tree.column("chips", width=100, anchor="e")
        self.score_tree.column("status", width=120)
        self.score_tree.pack(fill="both", expand=True)

        log_frame = ttk.LabelFrame(lower, text="Turnīra notikumi", padding=5)
        lower.add(log_frame, weight=2)
        self.log_text = tk.Text(log_frame, height=8, width=48, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True)

    def _read_settings(self) -> dict:
        try:
            values = {key: int(variable.get()) for key, variable in self.vars.items()}
        except ValueError as exc:
            raise ValueError("Visiem turnīra parametriem jābūt veseliem skaitļiem.") from exc
        if values["rounds"] < 1:
            raise ValueError("Partiju skaitam jābūt vismaz 1.")
        if values["bankroll"] < 10:
            raise ValueError("Sākuma čipu skaitam jābūt vismaz 10.")
        if values["decks"] < 1:
            raise ValueError("Jābūt vismaz vienai kāršu kavai.")
        if not 50 <= values["cut_percent"] <= 95:
            raise ValueError("Jaukšanas slieksnim jābūt no 50% līdz 95%.")
        if values["delay_ms"] < 0:
            raise ValueError("Auto pauze nedrīkst būt negatīva.")
        return values

    def new_tournament(self):
        try:
            self.settings = self._read_settings()
        except ValueError as exc:
            messagebox.showerror("Nederīgi parametri", str(exc), parent=self.root)
            return
        self.stop_auto()
        self.round_number = 0
        self.shoe = make_shoe(self.settings["decks"])
        self.history = []
        self.dealer_hand = []
        self.phase = "ready"
        self.log_lines.clear()
        for bot in self.bots:
            bot.bankroll = self.settings["bankroll"]
            bot.hands.clear()
            bot.bet = 0
        self._log(f"Jauns turnīrs: {len(self.bots)} boti, {self.settings['rounds']} partijas.")
        self._refresh_scoreboard()
        self._draw_table()
        self._set_status("Turnīrs sagatavots. Sāciet nākamo partiju vai auto režīmu.")

    def play_next_round(self):
        if not self.settings:
            self.new_tournament()
            if not self.settings:
                return
        if self.phase not in {"ready", "round_done"}:
            self._set_status("Vispirms pabeidziet pašreizējo partiju.")
            return
        if self.round_number >= self.settings["rounds"]:
            self._finish_tournament()
            return
        active = [bot for bot in self.bots if bot.bankroll >= 10]
        if not active:
            self._finish_tournament()
            return

        shoe_size = self.settings["decks"] * 52
        cut_size = int(shoe_size * (1 - self.settings["cut_percent"] / 100))
        if len(self.shoe) < max(2 * len(active) + 2, cut_size):
            self.shoe = make_shoe(self.settings["decks"])
            self.history = []
            self._log("Kava samaisīta; redzēto kāršu vēsture atiestatīta.")

        self.round_number += 1
        self.dealer_hand = []
        self.dealer_hole_hidden = True
        for bot in self.bots:
            bot.hands = []
            bot.bet = 0
            if bot not in active:
                continue
            max_allowed = min(200, int(bot.bankroll))
            try:
                started = time.monotonic()
                bet = bot.module.place_bet(int(bot.bankroll), list(self.history), len(self.shoe) / 52)
                self._check_bot_time(started, bot, "place_bet")
                if isinstance(bet, bool) or not isinstance(bet, int):
                    raise ValueError(f"place_bet atgrieza ne-veselu likmi: {bet!r}")
                bet = max(10, min(max_allowed, bet))
            except Exception as exc:
                self._log(f"{bot.name}: place_bet kļūda ({exc}); izmantota minimālā likme.")
                bet = 10
            bot.bet = bet
            bot.bankroll -= bet
            bot.hands = [self._new_hand(bet)]

        for _ in range(2):
            for bot in active:
                bot.hands[0]["cards"].append(self._draw_card(visible=True))
            self.dealer_hand.append(self._draw_card(visible=(len(self.dealer_hand) == 0)))

        self._log(f"Partija {self.round_number}/{self.settings['rounds']} sākusies.")
        self.phase = "players"
        self._play_all_bots(active)
        if self.phase == "players":
            self._begin_dealer_turn()
        self._refresh_scoreboard()
        self._draw_table()

    @staticmethod
    def _new_hand(bet: int, was_split: bool = False) -> dict:
        return {"cards": [], "bet": bet, "done": False, "was_split": was_split, "split_used": False}

    def _draw_card(self, visible: bool) -> str:
        if not self.shoe:
            raise RuntimeError("Kāršu kava beidzās partijas laikā.")
        card = self.shoe.pop()
        if visible:
            self.history.append(card)
        return card

    def _check_bot_time(self, started: float, bot: BotPlayer, function: str):
        elapsed = time.monotonic() - started
        if elapsed > BOT_TIME_LIMIT:
            raise TimeoutError(
                f"{bot.name}.{function} aizņēma {elapsed:.2f} s (limits 0.5 s)"
            )

    def _play_all_bots(self, active: list[BotPlayer]):
        for bot in active:
            hand_index = 0
            while hand_index < len(bot.hands):
                hand = bot.hands[hand_index]
                if is_natural(hand["cards"]):
                    hand["done"] = True
                    hand_index += 1
                    continue
                actions = 0
                while not hand["done"]:
                    actions += 1
                    if actions > 40:
                        self._log(f"{bot.name}: pārāk daudz gājienu; roka apturēta.")
                        hand["done"] = True
                        break
                    can_double = len(hand["cards"]) == 2 and bot.bankroll >= hand["bet"]
                    pair = (
                        len(hand["cards"]) == 2
                        and hand_value([hand["cards"][0]]) == hand_value([hand["cards"][1]])
                    )
                    can_split = pair and not hand["split_used"] and bot.bankroll >= hand["bet"]
                    try:
                        started = time.monotonic()
                        action = bot.module.decide_action(
                            list(hand["cards"]),
                            self.dealer_hand[0],
                            list(self.history),
                            can_double,
                            can_split,
                        )
                        self._check_bot_time(started, bot, "decide_action")
                        if action not in {"HIT", "STAND", "DOUBLE", "SPLIT"}:
                            raise ValueError(f"neatļauta darbība: {action!r}")
                        if action == "DOUBLE" and not can_double:
                            action = "STAND"
                        if action == "SPLIT" and not can_split:
                            action = "STAND"
                    except Exception as exc:
                        self._log(f"{bot.name}: decide_action kļūda ({exc}); roka apstādināta.")
                        action = "STAND"

                    if action == "HIT":
                        hand["cards"].append(self._draw_card(visible=True))
                        if hand_value(hand["cards"]) >= 21:
                            hand["done"] = True
                    elif action == "DOUBLE":
                        bot.bankroll -= hand["bet"]
                        hand["bet"] *= 2
                        hand["cards"].append(self._draw_card(visible=True))
                        hand["done"] = True
                    elif action == "SPLIT":
                        first_card, second_card = hand["cards"]
                        bot.bankroll -= hand["bet"]
                        hand["cards"] = [first_card, self._draw_card(visible=True)]
                        hand["split_used"] = True
                        hand["was_split"] = True
                        second_hand = self._new_hand(hand["bet"], was_split=True)
                        second_hand["cards"] = [second_card, self._draw_card(visible=True)]
                        second_hand["split_used"] = True
                        bot.hands.insert(hand_index + 1, second_hand)
                        hand["done"] = hand_value(hand["cards"]) >= 21 or first_card[:-1] == "A"
                        if hand["done"]:
                            second_hand["done"] = True
                    else:
                        hand["done"] = True
                if hand_value(hand["cards"]) > 21:
                    self._log(f"{bot.name}: bust ({hand_value(hand['cards'])}).")
                hand_index += 1

    def _begin_dealer_turn(self):
        self.phase = "dealer"
        self.dealer_hole_hidden = False
        self.history.append(self.dealer_hand[1])
        dealer_total = hand_value(self.dealer_hand)
        self._log(f"Dīlera kārtis: {self._format_hand(self.dealer_hand)} ({dealer_total}).")
        self._draw_table()
        if self.auto_dealer_var.get():
            while hand_value(self.dealer_hand) < 17:
                self.dealer_hand.append(self._draw_card(visible=True))
            self._settle_round()
        else:
            self.hit_button.configure(state="normal")
            self.stand_button.configure(state="normal")
            self._set_status("Dīlera gājiens: ņemiet kārti vai stājieties.")

    def dealer_hit(self):
        if self.phase != "dealer":
            return
        self.dealer_hand.append(self._draw_card(visible=True))
        total = hand_value(self.dealer_hand)
        self._log(f"Dīleris paņēma kārti; punktu summa: {total}.")
        self._draw_table()
        if total >= 17:
            self.dealer_stand()
        else:
            self._set_status(f"Dīlerim {total} punkti. Ņemiet kārti vai stājieties.")

    def dealer_stand(self):
        if self.phase != "dealer":
            return
        self._settle_round()

    def _settle_round(self):
        self.phase = "round_done"
        self.hit_button.configure(state="disabled")
        self.stand_button.configure(state="disabled")
        dealer_total = hand_value(self.dealer_hand)
        dealer_natural = is_natural(self.dealer_hand)
        dealer_bust = dealer_total > 21
        for bot in self.bots:
            for hand in bot.hands:
                total = hand_value(hand["cards"])
                natural = is_natural(hand["cards"], hand["was_split"])
                if total > 21:
                    result, payout = "Bust", 0
                elif natural and dealer_natural:
                    result, payout = "Push", hand["bet"]
                elif natural:
                    result, payout = "Blackjack", hand["bet"] * 2.5
                elif dealer_natural:
                    result, payout = "Loss", 0
                elif dealer_bust or total > dealer_total:
                    result, payout = "Win", hand["bet"] * 2
                elif total == dealer_total:
                    result, payout = "Push", hand["bet"]
                else:
                    result, payout = "Loss", 0
                bot.bankroll += payout
                self._log(
                    f"{bot.name}: {self._format_hand(hand['cards'])} — {result}, "
                    f"likme {hand['bet']}, čipi {self._format_chips(bot.bankroll)}."
                )
        self._refresh_scoreboard()
        self._draw_table()
        self._set_status(
            f"Partija {self.round_number}/{self.settings['rounds']} pabeigta. "
            f"Dīlerim {dealer_total}{' (bust)' if dealer_bust else ''}."
        )
        if self.auto_running:
            self._schedule_next_round()
        elif self.round_number >= self.settings["rounds"]:
            self._finish_tournament()

    def toggle_auto(self):
        if self.auto_running:
            self.stop_auto()
            self._set_status("Automātiskais turnīrs apturēts.")
            return
        if not self.settings:
            self.new_tournament()
            if not self.settings:
                return
        elif self.phase == "finished":
            self.new_tournament()
        if self.phase == "dealer" and not self.auto_dealer_var.get():
            self._set_status("Vispirms pabeidziet dīlera gājienu.")
            return
        self.auto_running = True
        self.auto_button.configure(text="Apturēt auto")
        if self.phase in {"ready", "round_done"}:
            self._schedule_next_round(delay=0)

    def stop_auto(self):
        self.auto_running = False
        self.auto_button.configure(text="Sākt auto")
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def _schedule_next_round(self, delay=None):
        if not self.auto_running:
            return
        if self.round_number >= self.settings["rounds"]:
            self._finish_tournament()
            return
        wait = self.settings["delay_ms"] if delay is None else delay
        self.after_id = self.root.after(wait, self._auto_next_round)

    def _auto_next_round(self):
        self.after_id = None
        if self.auto_running:
            self.play_next_round()

    def _finish_tournament(self):
        self.stop_auto()
        self.phase = "finished"
        if not self.bots:
            self._set_status("Turnīrs beidzies; nav derīgu botu.")
            return
        highest = max(bot.bankroll for bot in self.bots)
        winners = [bot.name for bot in self.bots if bot.bankroll == highest]
        outcome = ", ".join(winners) if len(winners) > 1 else winners[0]
        self._set_status(
            f"Turnīrs beidzies pēc {self.round_number} partijām. "
            f"Uzvarētājs: {outcome} ({self._format_chips(highest)} čipi)."
        )
        self._log(f"Turnīra uzvarētājs: {outcome} ar {self._format_chips(highest)} čipiem.")
        messagebox.showinfo("Turnīrs pabeigts", self.status_var.get(), parent=self.root)

    def _refresh_scoreboard(self):
        for item in self.score_tree.get_children():
            self.score_tree.delete(item)
        ranked = sorted(self.bots, key=lambda bot: bot.bankroll, reverse=True)
        for bot in ranked:
            status = "Spēlē" if bot.bankroll >= 10 else "Izstājies"
            self.score_tree.insert(
                "", "end",
                values=(bot.name, self._format_chips(bot.bankroll), status),
            )

    @staticmethod
    def _format_chips(chips: float) -> str:
        return str(int(chips)) if float(chips).is_integer() else f"{chips:.1f}"

    @staticmethod
    def _format_hand(hand: list[str]) -> str:
        return " ".join(f"{card[:-1]}{SUIT_NAMES[card[-1]]}" for card in hand)

    def _draw_table(self):
        self.table.delete("all")
        width = max(self.table.winfo_width(), 900)
        self.table.create_text(width // 2, 22, text="DĪLERIS", fill="white", font=("Segoe UI", 13, "bold"))
        dealer_display = list(self.dealer_hand)
        if self.dealer_hole_hidden and len(dealer_display) > 1:
            dealer_display[1] = None
        self._draw_cards(width // 2 - max(45, len(dealer_display) * 45 // 2), 42, dealer_display)
        dealer_score = "?" if self.dealer_hole_hidden else str(hand_value(self.dealer_hand))
        self.table.create_text(width // 2, 145, text=f"Punkti: {dealer_score}", fill="white", font=("Segoe UI", 10))

        count = max(1, len(self.bots))
        columns = max(1, min(count, width // 190))
        cell_width = width // columns
        for index, bot in enumerate(self.bots):
            row, column = divmod(index, columns)
            x = column * cell_width + cell_width // 2
            y = 185 + row * 150
            label = f"{bot.name}  |  {self._format_chips(bot.bankroll)} čipi"
            self.table.create_text(x, y, text=label, fill="white", font=("Segoe UI", 10, "bold"))
            cards = []
            if bot.hands:
                for hand in bot.hands:
                    cards.append((hand["cards"], hand["bet"]))
            offset = 0
            for hand_cards, bet in cards:
                self._draw_cards(x - 70 + offset, y + 15, hand_cards, small=True)
                self.table.create_text(
                    x - 25 + offset, y + 103,
                    text=f"{hand_value(hand_cards)} p. | likme {bet}",
                    fill="white", font=("Segoe UI", 9),
                )
                offset += min(150, cell_width // max(1, len(cards)))
        self.table.configure(scrollregion=self.table.bbox("all"))

    def _draw_cards(self, x, y, cards, small=False):
        card_width = 48 if small else 58
        card_height = 68 if small else 82
        gap = 7
        for index, card in enumerate(cards):
            left = x + index * (card_width + gap)
            if card is None:
                self.table.create_rectangle(
                    left, y, left + card_width, y + card_height,
                    fill="#244b91", outline="white", width=2,
                )
                self.table.create_text(left + card_width / 2, y + card_height / 2, text="?", fill="white")
                continue
            suit = card[-1]
            color = "#c62828" if suit in RED_SUITS else "#202020"
            self.table.create_rectangle(
                left, y, left + card_width, y + card_height,
                fill="#fffdf7", outline="#d9d2c5", width=2,
            )
            self.table.create_text(
                left + card_width / 2, y + card_height / 2,
                text=f"{card[:-1]}\n{SUIT_NAMES[suit]}",
                fill=color, font=("Segoe UI", 12 if small else 14, "bold"),
            )

    def _log(self, line: str):
        self.log_lines.append(line)
        self.log_lines = self.log_lines[-300:]
        if not hasattr(self, "log_text"):
            return
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("end", "\n".join(self.log_lines) + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _set_status(self, text: str):
        self.status_var.set(text)


def main():
    root = tk.Tk()
    BlackjackTournament(root)
    root.mainloop()


if __name__ == "__main__":
    main()
