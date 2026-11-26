# AI kursa projekti

Šajā repozitorijā ir četras Python projektu grupas:

1. [Labirinti](#labirinti)
2. [Tic-Tac-Toe ar Swap2](#tic-tac-toe-ar-swap2)
3. [Blackjack ar kāršu skaitīšanas botu](#blackjack-ar-kāršu-skaitīšanas-botu)
4. [Game of Life un Pocket Party](#game-of-life-un-pocket-party)

## Labirinti

[`maze/`](maze/) satur vairākus atsevišķus labirintu risinātājus un spēles. Projekts ietver
labirintu ielādi no teksta failiem, ceļa atrašanu, algoritmu salīdzināšanu, animāciju,
grafisko interfeisu, vairāku līmeņu spēli un LAN režīmu.

**Studentu devums:**

- **Anete (Ance)** — izveidoja [`Ance_maze.py`](maze/Ance_maze.py) un spēles versiju
  [`Ance_maze_game.py`](maze/Ance_maze_game.py), tostarp labirintu algoritmus, līmeņus,
  vārdus, varoņu izvēli, rezultātu saglabāšanu un LAN sacīkstes.
- **Zane Goldmane** — izveidoja [`Zane maze/`](maze/Zane%20maze/) risinātāju ar Tkinter
  izvēlni, animētu ceļu, mazām kartēm, testiem un palaišanas failu.
- **Valters** — izstrādāja [`Valters_maze.py`](maze/Valters_maze.py), kurā ir vairāki ceļa
  meklēšanas algoritmi un rediģējams/neatkarīgs labirinta skatītājs.
- **Klāvs Barons-Kaupa** — izveidoja [`Klavs_maze.py`](maze/Klavs_maze.py) ar labirintu
  risinātāja dashboardu, alternatīviem risinājumiem un smagu testkartīti.
- **Karlis (GitHub `Shamejs`)** — pievienoja [`Karlis_maze.py`](maze/Karlis_maze.py) ar
  karšu nolasīšanu, BFS un otras risināšanas metodes, CLI un grafisko interfeisu.
- **Undine Stafecka** — izveidoja pilnvērtīgu labirintu spēli [`Undine_maze.py`](game-of-life/Undine/Undine_maze.py),
  ar tematiskiem līmeņiem, spēles mehāniku, algoritmu analīzi un dokumentāciju.
- **Eduards Rens** — sagatavoja kopējo [`maze/`](maze/) projektu un sākotnējās kartes,
  apvienoja kontribūcijas un papildināja kopīgo README un testu vidi.

Papildu instrukcijas: [`maze/README.md`](maze/README.md).

```powershell
py -3.13 -m pip install -r maze\requirements.txt
py -3.13 maze\Ance_maze.py
```

## Tic-Tac-Toe ar Swap2

[`tic-tac-toe/`](tic-tac-toe/) satur 15 × 15 Tic-Tac-Toe spēli ar piecu zīmju uzvaru
nosacījumu un Swap2 atklātni. [`main.py`](tic-tac-toe/main.py) atrod studējošo botus,
izpilda aizsargātus gājienus ar taimautu, pārbauda valdības likumus un noslēdz turnīrus.

**Studentu devums:**

- **Eduards Rens** — definēja spēles specifikāciju [`RULES.md`](tic-tac-toe/RULES.md),
  izveidoja turnīra dzinēju, botu ielādi, Swap2 spēles loģiku, GUI un testus.
- **Zane Goldmane** — izveidoja [`Zane G/bot.py`](tic-tac-toe/Zane%20G/bot.py) ar
  uzvara analīzi un meklēšanu, papildus `GUI` un pilnīgu bota moduļa versiju.
- **Undine Stafecka** — izveidoja [`Undine/bot.py`](tic-tac-toe/Undine/bot.py) ar
  stratēģisku gājienu novērtēšanu un [`Undine/gui.py`](tic-tac-toe/Undine/gui.py)
  grafisko interfeisu.
- **Kristers Kalniņš** — izveidoja [`kristers_kalnins/bot.py`](tic-tac-toe/kristers_kalnins/bot.py)
  ar laika ierobežotu meklēšanu un [`kristers_kalnins/gui.py`](tic-tac-toe/kristers_kalnins/gui.py).
- **Pēteris Pūniņš** — izveidoja [`peteris_punins/bot.py`](tic-tac-toe/peteris_punins/bot.py)
  ar spēles stāvokļa meklēšanu un atsevišķu [`peteris_punins/gui.py`](tic-tac-toe/peteris_punins/gui.py).
- **Testa varianti** — [`Test1/`](tic-tac-toe/Test1/), [`Test2/`](tic-tac-toe/Test2/) un
  [`Test4/`](tic-tac-toe/Test4/) satur alternatīvas bota politikas turnīra salīdzināšanai.

Palaišana:

```powershell
python tic-tac-toe/main.py
```

Tests:

```powershell
python -m unittest tic-tac-toe/test_game.py -v
```

## Blackjack ar kāršu skaitīšanas botu

[`blackjack/Undine/blackjack.py`](blackjack/Undine/blackjack.py) ir Tkinter Blackjack
spēle ar četrām kavām, kuras sajauc pēc 52 izspēlētām kārtīm. Spēlētājs sāk ar 1000
žetoniem. Bots spēlē automātiski un turpina arī pēc žetonu iztērēšanas: bilance tiek
papildināta līdz 1000, tiek sajaukta jauna kava, un uzvaru/zaudējumu statistika
saglabājas. Gājieni seko ar īsām pauzēm (50 ms starp botu darbībām un 100 ms starp
partijām). Bots liek 5–25 žetonus atkarībā no Hi-Lo patiesā skaita un precīzi
aprēķina atlikušās kavas EV ņemšanai, palikšanai un dubultošanai; pāru dalīšanai
izmanto standarta pamatstratēģiju. Dīlera aizklātā kārts tiek varbūtiski modelēta.
Kārtis attēlotas ar mastīm un kāršu zīmējumu. Spēlei ir palaišanas fails
[`Play Blackjack.bat`](game-of-life/zane/Play%20Blackjack.bat).

```powershell
$env:PYTHONPATH = "blackjack\Undine"
python blackjack\Undine\blackjack.py
python -m unittest discover -s game-of-life\zane -p test_blackjack.py -v
```

## Game of Life un Pocket Party

[`game-of-life/`](game-of-life/) satur vairākas patstāvīgas Conway's Game of Life
implementācijas, kā arī lokālu 3D ballīšu galda spēli.

**Studentu devums:**

- **Valters** — izveidoja [`valters/gol_ansons.py`](game-of-life/valters/gol_ansons.py),
  interaktīvu Game of Life versiju ar iestatījumu logu un vizualizāciju.
- **Anete (Ance)** — izveidoja [`ance/`](game-of-life/ance/) Pygame/Tkinter versiju,
  centrālo simetriju, krāsu sajaukšanu, zīmējumu saglabāšanu/atvēršanu un testus.
- **Zane Goldmane** — izveidoja [`zane/`](game-of-life/zane/) Solo un LAN multiplayer
  versiju, dzēšanu ar atslēgu, serveri/klientu un palaišanas failus.
- **Undine Stafecka** — izveidoja [`Undine/Life.py`](game-of-life/Undine/Life.py),
  paplašināmu vizuāli bagātu simuliāciju ar tēmu, animāciju un importēšanu.
- **GitHub `exploit123321`** — izveidoja [`Pocket Party`](game-of-life/pocket-party/)
  3D pass-and-play ballīšu spēli ar Python noteikumiem, Three.js skatu, saglabāšanu,
  mini-spēlēm un testiem.
- **Eduards Rens** — integrēja Pocket Party projektu, pakalpojuma palaišanu un GitHub Actions
  testu vidi, kā arī apvienoja atsevišķās Game of Life versijas vienā repozitorijā.

### Pocket Party palaišana

Nepieciešams Python 3.10+ un pārlūks ar WebGL2; papildu pip pakotnes nav vajadzīgas.

```powershell
cd game-of-life\pocket-party
python server.py --open
```

Uz Windows var izmantot [`Play Game.bat`](game-of-life/pocket-party/Play%20Game.bat).
Detalizētas Pocket Party instrukcijas atrodas [`game-of-life/pocket-party/README.md`](game-of-life/pocket-party/README.md).
