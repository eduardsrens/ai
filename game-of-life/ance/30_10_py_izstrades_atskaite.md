# Game of Life programmas izstrādes atskaite

## Mērķis

Paplašināt Conway spēles “Game of Life” programmu, lai lietotājs varētu veidot, krāsot, saglabāt un atjaunot figūras, kā arī zīmēt ar centrālo simetriju.

## Izstrādes gaita

### 1. Sākotnējās figūras atiestatīšana

Pievienota poga **Atjaunot**. Programma saglabā sākotnējo figūru, ko veido lietotājs vai iegūst ar nejaušināšanas funkciju. Atiestatīšana aptur simulāciju, atgriež šo figūru un iestata paaudžu skaitu uz nulli. Esošā poga **Tīrīt** joprojām atsevišķi notīra laukumu.

### 2. Zīmējumu saglabāšana un ielāde

Pievienotas pogas **Saglabāt** un **Atvērt**. Zīmējumus var saglabāt ar nosaukumu un vēlāk ielādēt. Tie tiek glabāti JSON datnē `game_of_life_drawings.json` blakus programmas failam. Pirms esoša zīmējuma pārrakstīšanas programma prasa apstiprinājumu.

Saglabāšanas formātam pievienota datu pārbaude. Atbalstīti arī vecākā formāta vienkrāsainie zīmējumi, lai iepriekš saglabātās figūras paliktu atveramas.

### 3. Zīmēšana ar peles vilkšanu

Laukumā var zīmēt, turot nospiestu kreiso peles pogu un velkot. Labais klikšķis dzēš šūnu. Zīmējot pirmo paaudzi, programma atjauno atiestatīšanas sākuma figūras kopiju.

### 4. Krāsu izvēle katrai šūnai

Poga **Krāsa** atver krāsas izvēles logu. Jaunā krāsa tiek piemērota šūnām, kuras zīmē pēc tās izvēles; jau iekrāsotās šūnas savu krāsu saglabā. Krāsa ir iekļauta arī saglabājamajā zīmējumā.

Krāsu izvēles kļūda tika novērsta, izmantojot Tkinter loga atgriezto RGB skaitļu tuple, nevis heksadecimālo virkni ar `#`.

### 5. Krāsu sajaukšana paaudžu laikā

Šūnu stāvoklis un krāsa tiek glabāti atsevišķi. Izdzīvojušās šūnas saglabā savu krāsu, bet jaunām šūnām tiek aprēķināts dzīvo kaimiņu krāsu RGB vidējais. Tādējādi dažādu krāsu apgabali, attīstoties pēc Game of Life noteikumiem, rada pārejas krāsas.

### 6. Centrālā simetrija

Pievienota poga **Simetr.**, kas ieslēdz vai izslēdz centrālās simetrijas režīmu. Režīmā, zīmējot vai dzēšot šūnu, tā pati darbība tiek veikta arī pretējā vietā pāri laukuma centram. Abām šūnām tiek piešķirta viena un tā pati krāsa.

## Tehniskais risinājums

- Programmas galvenais kods atrodas vienā Python failā un izmanto Pygame spēles logam un Tkinter dialogiem.
- Spēles laukums ir 48 kolonnas × 32 rindas; šūnu kaimiņi turpina skaitīties pāri laukuma malām.
- Paaudzes aprēķins saglabā esošos Game of Life noteikumus un papildus pārnes vai sajauc šūnu krāsas.
- Saglabātie krāsu dati tiek validēti, ielādējot JSON datni.

## Pārbaudes

Veiktas šādas pārbaudes:

- Python sintakses pārbaude — kļūdu nav.
- Pylance diagnostika — kļūdu nav.
- Esošie automatizētie testi: `python -m unittest test_23_10_py.py` — visi 9 testi izturēti.
- Atsevišķi izpildītas mērķētas pārbaudes krāsu sajaukšanai, krāsainu zīmējumu saglabāšanai un ielādei, vecā saglabāšanas formāta nolasīšanai, simetrijas koordinātēm un vadības pogu attēlošanai.

**Piezīme par testu tvērumu:** esošie 9 automatizētie testi pārbauda intervālu apvienošanas programmu, nevis Game of Life funkcionalitāti. Game of Life jaunajām funkcijām tika veiktas iepriekš minētās atsevišķās mērķētās pārbaudes; pilna lietotāja saskarnes manuāla pārbaude nav veikta.

## Gala rezultāts

Programma atbalsta figūru veidošanu ar peli, vairāku krāsu izmantošanu vienā figūrā, jauno šūnu krāsu sajaukšanu, zīmējumu saglabāšanu un ielādi, figūras atiestatīšanu un centrāli simetrisku zīmēšanu.
