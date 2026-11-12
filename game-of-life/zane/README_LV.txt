CONWAY'S GAME OF LIFE
=====================

PALAIŠANA WINDOWS DATORĀ
-----------------------
1. Izpako visu ZIP arhīvu vienā mapē.
2. Uzinstalē Python 3 no https://www.python.org/downloads/windows/
   Instalācijas laikā atzīmē "Add python.exe to PATH".
   Izmanto oficiālo Windows instalētāju, kurā ir iekļauts Tkinter.
3. Veic dubultklikšķi uz "Play Game.bat".
4. Spēles sākuma ekrānā izvēlies Solo vai Multiplayer.

SOLO
----
Klikšķini un velc, lai zīmētu. Izmanto zīmuli, dzēšgumiju, krāsu paleti
un Lexicon figūras. Scrollbar pārvieto bezgalīgo laukumu; peles ritenītis
maina tālummaiņu.

MULTIPLAYER
-----------
Šī versija darbojas lokālajā tīklā (tas pats Wi-Fi/LAN), nevis internetā.
Visiem spēlētājiem jābūt vienā tīklā un katram datorā jāpalaiž sava spēles
kopija.

1. Viens spēlētājs izvēlas 1v1 vai 2v2 un spiež "Host game".
2. Hosts pārējiem nosūta ekrānā redzamo Host address un Room code.
3. Pārējie ievada savu vārdu, host adresi un istabas kodu, tad spiež
   "Join game".
4. Multiplayer izvēlnē ir redzami spēles noteikumi. Kad visi pievienojušies,
   katrs uzzīmē sākuma figūru savā laukumā, tad hosts spiež "Start game".
5. Spēlētāji pēc kārtas izdara vienu gājienu: zīmē savā laukumā, lai
   aizsargātos, vai pretinieka laukumā (sarkanā), lai uzbruktu. 2v2 režīmā
   komandas biedriem uzbrukt nedrīkst.
6. Pēc visiem gājieniem spēle izpilda 10 Game of Life paaudzes. Spēlētājs
   tiek izslēgts, ja viņa sākuma laukumā vairs nav dzīvu šūnu. Uzvar pēdējais
   izdzīvojušais spēlētājs vai komanda; spēles beigās parādās uzvaras ekrāns
   ar tekstu "KONČA NO ZANES!".

Ja Windows Firewall jautā, atļauj Python piekļuvi Private networks
privātajam tīklam. Atļauju dod tikai uzticamā tīklā un kopīgo istabas kodu
tikai ar spēlētājiem, kurus esi uzaicinājis.

Failus drīkst pārvietot vai ZIP arhīvu nokopēt uz citu Windows datoru.
Otrajā datorā Python 3 jābūt uzinstalētam; spēles Python failus nevajag
instalēt vai pārkopēt atsevišķi no palaidēja.
