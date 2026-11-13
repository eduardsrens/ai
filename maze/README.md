# Undīnes labirintu laboratorija

## Palaišana

Arcade ir pārbaudīts ar Python 3.13. No darbvietas saknes palaidiet:

```powershell
py -3.13 -m pip install -r maze\requirements.txt
py -3.13 maze\Undine_maze.py
```

Spēlē turiet bultiņu, lai kāmītis skrietu pa eju; atlaižot taustiņu, viņš pabeidz iesākto soli un apstājas. Atslēga atrodas labirinta sānu atzarā, tāpēc tā jāatrod, novirzoties no ceļa. Ar atslēgu atveriet vārtus un sasniedziet gurķi. Pēc gurķa atrašanas zvaigznes paliek uz ekrāna; nospiediet `Space`, lai tās notīrītu un sāktu nākamo līmeni. `P` vai `Esc` ieslēdz pauzi.

Katram līmenim ir numurs un sava pasaule: Candy Land, Volcano Land, Underwater World, Enchanted Forest, Moon Base un Desert Ruins. Labirinti un vajadzīgo soļu skaits pakāpeniski pieaug. Skrienot samazinās enerģija; ja tā beidzas, spēle ir zaudēta. Enerģija tiek atjaunota katrā jaunā līmenī. `P` vai `Esc` ieslēdz/izslēdz pauzi, bet `R` sāk līmeni no jauna.

Iepriekšējais karšu un algoritmu vizualizētājs pieejams ar `--analyze`:

```powershell
py -3.13 maze\Undine_maze.py --analyze
```

Termināļa versija un karšu saraksts ir pieejami šādi:

```powershell
py -3.13 maze\Undine_maze.py --cli maze\maze_15x25.txt
py -3.13 maze\Undine_maze.py --list
```

## Karšu formāts

Programma automātiski pārbauda šīs mapes `.txt` failus pēc satura, nevis faila nosaukuma. Karte ir taisnstūrveida: visām rindām jābūt vienāda platuma. Sienas var apzīmēt ar `#`, `X` vai `1`; brīvos lauciņus ar atstarpi, `.` vai `0`. Sākumam izmantojiet vienu `A` vai `S`, bet mērķim vienu `B`, `E` vai `G`.
