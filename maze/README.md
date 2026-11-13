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
