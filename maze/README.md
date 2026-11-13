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

# Labirintu risinātājs

## Palaišana

No projekta mapes uzinstalē `pygame-ce` un palaid programmu:

```powershell
python -m pip install -r maze/requirements.txt
python maze/Ance_maze.py
```

Programma automātiski atrod un nolasa visas derīgās `.txt` kartes, kas atrodas
`maze` mapē. Citu karti var norādīt palaišanas komandā:

```powershell
python maze/Ance_maze.py ceļš\uz\karti.txt
```

Kartei jābūt taisnstūrveida teksta režģim: `#` apzīmē sienu, atstarpe — eju,
`A` — sākumu un `B` — galamērķi. Katrā kartē jābūt tieši vienam `A` un vienam
`B`.

## Vadība

- Bultiņas pa kreisi/pa labi — pārslēgt karti.
- `Enter` — atrisināt karti vēlreiz.
- `Space` — apturēt vai turpināt risinājuma animāciju.
- `R` — atkārtot animāciju.
- `Esc` — aizvērt programmu.

Programma vienlaikus palaiž BFS un DFS. BFS atrod īsāko ceļu; logā tiek
salīdzināti atrasto soļu skaits, izpildes laiks un apskatīto šūnu skaits.
Mērījumi var nedaudz mainīties katrā palaišanas reizē.

## Dārzeņu labirinta spēle

Spēlē divi spēlētāji sacenšas vienā un tajā pašā, saimnieka ģenerētajā 20
līmeņu kartē. Katrā nākamajā līmenī labirints kļūst lielāks. Pirmajā līmenī
izeja atveras pēc 60 sekundēm, lai to nevarētu pabeigt ātrāk. Savāktā ⭐ balva
noņem 5 sekundes no spēlētāja kopējā laika. Rezultāti un vietu tabula tiek
saglabāti `maze/maze_scores.json`.

Palaid spēli ar:

```powershell
python maze/Ance_maze_game.py
```

Spēlētāji ievada vārdus, izvēlas dārzeņu emoji avatārus un spēles izvēlnē
izvēlas solo spēli vai LAN sacīksti. Izvēles un avatārus var noklikšķināt,
vai izmantot ekrānā redzamos īsinājumtaustiņus. LAN režīmā saimnieks izvēlas
`2`, bet otrs spēlētājs — `3` un ievada saimnieka lokālo IP adresi.
Pārvietojies, turot WASD vai bultiņu taustiņu; pirmais līdz izejai iegūst
līmeņa uzvaras punktus. Solo spēlē pēc finiša uznirstošajā logā vari izvēlēties
nākamo līmeni vai atgriezties izvēlnē. Izeju var sasniegt, nesavācot visas
zvaigznes.

## Testi

```powershell
python -m unittest discover -s maze -p "test_*.py" -v
```
