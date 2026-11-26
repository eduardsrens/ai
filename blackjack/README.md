# Blackjack botu turnīrs

Palaidiet vizuālo turnīru ar Python 3:

```powershell
python blackjack\tournament.py
```

Lietotne pati atrod `bot.py` failus blackjack apakšmapēs. Katram botam jānodrošina
`place_bet(bankroll, history, decks_remaining)` un
`decide_action(hand, dealer_upcard, history, can_double, can_split)` funkcijas,
kā aprakstīts [RULES.md](RULES.md).

Iestatiet partiju skaitu, sākuma čipus, kavu skaitu, kavas jaukšanas slieksni
un automātiskā režīma pauzi. Likmes robežas nav maināmas: saskaņā ar noteikumiem
likmei jābūt no 10 līdz `min(200, bankroll)` čipiem. Spiediet **Jauns turnīrs**, lai
sāktu manuāli ar pogu **Nākamā partija**, vai **Sākt auto**, lai turpinātu
partijas automātiski. Atzīme **Automātisks dīleris** liek dīlerim vilkt līdz
17 punktiem; ja tā nav atzīmēta, dīlera kārtis vada lietotājs.

Rezultātā uzvar bots ar lielāko čipu skaitu pēc norādītā partiju skaita.
Botu izsaukumu izpildes laiku pārbauda pēc atgriešanās; pārsnieguma gadījumā
turnīrs reģistrē kļūdu un izmanto minimālo likmi vai apstājas pie gājiena.

Testi:

```powershell
python -m unittest blackjack.test_tournament -v
```
