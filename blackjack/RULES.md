# Blackjack AI turnīra noteikumi un specifikācija

Spēlē piedalās vairāki boti pie viena galda pret Dīleri (ko vada pasniedzējs/students), kas testē visus botus.
Visi boti spēlē ar vienu kopīgu 4 kāršu kavu komplektu(208 kārtis), kas tiek pārmaisīta, kad izspēlēti ~75% kāršu.

## 1. Faila novietojums un struktūra
* Katrs dalībnieks izveido savu mapi: `blackjack/<vards_uzvards>/bot.py` (piem., `blackjack/janis_berzins/bot.py`).
* Failā **nedrīkst** izmantot `input()`, `print()` garus žurnālus vai ārējas bibliotēkas (tikai Python standarta bibliotēka: `random`, `time`, `math`, `collections` u.c.).
* Importējot `bot.py`, nedrīkst palaisties nekāds aprēķinu kods — visu testēšanu liec zem `if __name__ == "__main__":`.

## 2. Kāršu formāts
Katra kārts ir 2–3 simbolu virkne (`str`), piemēram: `"AS"`, `"TH"`, `"KD"`, `"2C"`:
* **Vērtība (`card[:-1]`):** `"2"`, `"3"`, `"4"`, `"5"`, `"6"`, `"7"`, `"8"`, `"9"`, `"T"`, `"J"`, `"Q"`, `"K"`, `"A"`.
* **Masts (`card[-1]`):** `"H"` (ērcens), `"D"` (kāravs), `"C"` (kreics), `"S"` (pīķis).
* **Punkti:** `2–9` atbilst nominālam; `T, J, Q, K` = `10` punkti; `A` (dūzis) = `11` vai `1` punkts.

## 3. Obligātie elementi failā `bot.py`

### `BOT_NAME: str`
Tavs bota nosaukums tabulai (bez garumzīmēm, lai korekti attēlojas konsolē), piemēram:
```python
BOT_NAME = "MonteCarloBot"

### `place_bet(bankroll: int, history: list[str], decks_remaining: float) -> int`
Izsauc pirms katra raunda kāršu izdalīšanas.
- `bankroll` — tavs pašreizējais žetonu skaits (sākumā `1000`).
- `history` — saraksts ar visām kārtīm, kas jau izspēlētas no pašreizējās kurpes.
- `decks_remaining` — aptuvenais atlikušo kavu skaits kurpē (piem., `3.4`).
- **Atgriež:** veselu skaitli (`int`) intervālā `[10, min(200, bankroll)]`.

### `decide_action(hand: list[str], dealer_upcard: str, history: list[str], can_double: bool, can_split: bool) -> str`
Izsauc katru reizi, kad ir tavs gājiens pie galda.
- `hand` — tavas kārtis rokā (piem., `["8S", "9D"]`).
- `dealer_upcard` — dīlera atvērtā kārts (piem., `"6C"`).
- `history` — visas līdz šim redzētās kārtis kurpē (ieskaitot citu botu atklātās kārtis šajā raundā!).
- `can_double` — `True`, ja tev ir tieši 2 kārtis un pietiek žetonu likmes dubultošanai.
- `can_split` — `True`, ja tev ir 2 vienādas vērtības kārtis (piem., `"8H"` un `"8S"`) un pietiek žetonu.
- **Atgriež:** vienu no virknēm: `"HIT"`, `"STAND"`, `"DOUBLE"` vai `"SPLIT"`.

## 4. Spēles noteikumi un limiti
- **Dīlera noteikumi:** Dīleris velk kārti, kamēr punktu summa ir `< 17`, un vienmēr apstājas pie `>= 17` (arī uz *Soft 17*).
- **Izmaksas:** Uzvara `1:1`, Blackjack (21 ar pirmajām 2 kārtīm) `3:2` (`1.5x`), neizšķirts (*Push*) atgriež likmi.
- **Laika limits:** Maksimums **0.5 sekundes** vienam lēmumam (`place_bet` vai `decide_action`).
- **Sodi par kļūdām:** Ja bots pārsniedz laiku, izmet kļūdu vai atgriež nelegālu darbību (piem., `"DOUBLE"`, kad `can_double=False`), tiesnesis automātiski piemēro `STAND` vai minimālo likmi `10`.
