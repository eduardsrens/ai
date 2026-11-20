# Klāva botu versijas

- `bot.py` ir aktīvais sacensību bots; pašreizējā versija ir Klāvs v2.
- `versions/bot_v1.py` saglabā Klāvs v1, lai salīdzinājums paliktu nemainīgs.
- `versions/bot_v2.py` ir aktīvās v2 kopija salīdzināšanai nākotnē.

## Spēlēšana un salīdzināšana

No repozitorija mapes palaid:

```powershell
python .\klava_bots.py
```

Izvēlies botu A un botu B, tad nospied **Botu savstarpējā cīņa**. Sākuma loma
mainās katrā nākamajā mačā. Ar `--test` pārbauda obligātos gājienus un laika
limitu:

```powershell
python .\klava_bots.py --test
```

## Pašreizējais lokālais salīdzinājums

Turnīrā katrs botu pāris aizvadīja divas partijas, samainot sākuma lomu:

| Vieta | Bots | Uzvaras / neizšķirti / zaudējumi |
|---|---|---:|
| TOP 1 | Klāvs v2 | 6 / 0 / 0 |
| TOP 2 | Klāvs v1 | 4 / 0 / 2 |
| TOP 3 | GreedyAI 2 | 2 / 0 / 4 |
| TOP 4 | IQ 1 | 0 / 0 / 6 |

Klāvs v2 lēnākais izmērītais gājiens šajā turnīrā bija 0.819 s (ierobežojums
ir 1.0 s). Tie ir tikai divu partiju rezultāti katram pārim. Tie nav
salīdzinājuma rezultāti pret skolotāja botu; repozitorijā esošajam `Test1`
botam trūkst vajadzīgās `get_move` un Swap2 funkciju saskarnes.

## Nākamās versijas veidošana

`versions/bot_v2.py` ir saglabāta pašreizējā v2 versija. Veidojot v3, atstāj
arhīvu nemainītu, uzlabo `bot.py`, nomaini `BOT_NAME` uz Klāvs v3 un pārbaudi
to pret iepriekšējām versijām. Pēc pārbaudes saglabā v3 kā
`versions/bot_v3.py`. Sacensībām iesniedz tikai aktīvo `bot.py`; arhīvs un
GUI paredzēti salīdzināšanai.

TOP vietas izvēlnē apzīmē salīdzināšanas secību, nevis garantiju par uzvaru
pret skolotāja botu. IQ 1 un IQ 2 ir spēles grūtības pakāpes, nevis īsts IQ.
