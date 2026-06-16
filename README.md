# SCARA Robot V1.0

Repozytorium startowe dla uproszczonego robota SCARA budowanego z profili
aluminiowych i elementow drukowanych w 3D z PET-G. Wersja 1.0 skupia sie na
uruchomieniu podstawowej mechaniki: osi Z, jednej glownej osi obrotowej ramienia
oraz obrotowego efektora koncowego.

## Architektura robota

Robot pracuje jako uproszczony SCARA:

- **Os Z** - ruch gora/dol realizowany na pasku.
- **Glowne ramie** - jedna os obrotowa napedzana autorska, drukowana w 3D
  przekladnia cykloidalna.
- **Efektor koncowy** - obrot narzedzia napedzany paskiem zebatym z silnika
  umieszczonego na ramieniu.

Na tym etapie projekt pomija klasyczny "lokiec" SCARA. Narzedzie porusza sie po
stalym promieniu, czyli po luku wyznaczonym przez dlugosc ramienia.

## Wymiary i dane kinematyczne

| Parametr | Wartosc | Opis |
| --- | ---: | --- |
| Offset osi Z | 165 mm | Odleglosc od osi prowadnic pionowych do srodka glownej osi obrotu |
| Promien ramienia L1 | 150 mm | Odleglosc od osi przekladni cykloidalnej do osi efektora |
| Przelozenie glownej osi | 20:1 | Matematyczne przelozenie przekladni cykloidalnej |
| Mikrokrok | 1/16 | Ustawienie dla wszystkich sterownikow TB6600 |

### Przeliczniki krokow

Glowne ramie:

```text
(200 krokow silnika * 16 mikrokrokow * 20) / 360 stopni = 177.7778 krokow/stopien
```

Os Z i efektor wymagaja kalibracji po pomiarze rzeczywistego napedu:

- **Os Z**: `(200 * 16) / skok_w_mm`.
- **Efektor**: przelicznik zalezy od liczby zebow kol pasowych i ewentualnego
  przelozenia paska.

## Elektronika

| Komponent | Konfiguracja |
| --- | --- |
| Mikrokontroler | Arduino Mega 2560, logika 5 V |
| Sterowniki | 4x TB6600, sterowanie PUL/DIR/ENA |
| Silniki | NEMA 17 dla osi Z, glownego ramienia i efektora |
| Zasilanie silnikow | Zasilacz przemyslowy 24 V, 8.3 A, 200 W |
| Zasilanie logiki | Osobny zasilacz 9 V do gniazda Arduino Mega |
| Krancowki | Optyczne czujniki szczelinowe dla osi Z i glownej osi obrotowej |

Masy zasilania logiki i sygnalow sterujacych TB6600 powinny byc wspolne.
Zasilanie silnikow pozostaje prowadzone oddzielnie do sterownikow.

## Struktura repozytorium

```text
.
├── cad/                  # Modele 3D i pliki produkcyjne
├── docs/                 # Schematy, notatki montazowe i kalibracja
└── src/
    └── main/
        └── main.ino      # Szkic Arduino Mega z AccelStepper
```

## Oprogramowanie

Kod startowy znajduje sie w [`src/main/main.ino`](src/main/main.ino). Szkic
zawiera:

- definicje pinow `PUL`, `DIR`, `ENA` dla trzech osi,
- konfiguracje biblioteki `AccelStepper`,
- stale przeliczeniowe dla glownego ramienia,
- miejsca do uzupelnienia kalibracji osi Z i efektora,
- szablony procedur homingu dla osi Z i glownego ramienia,
- przykladowy parser prostych komend przez port szeregowy.

### Wymagania

- Arduino IDE albo Arduino CLI.
- Plytka: **Arduino Mega 2560**.
- Biblioteka: **AccelStepper**.

### Przykladowe komendy szeregowe

Po wgraniu szkicu i otwarciu monitora portu szeregowego z predkoscia
`115200 baud` mozna uzyc:

```text
STATUS
HOME Z
HOME ARM
MOVE Z 10
MOVE ARM 45
MOVE TOOL 90
STOP
```

## Obudowa sterownika

Control box jest planowany jako drukowana w 3D obudowa o strukturze plastra
miodu. Dolna czesc miesci zasilacz 24 V, nad nim znajduje sie zintegrowana szyna
DIN dla Arduino Mega, a sterowniki TB6600 sa montowane pionowo obok siebie w celu
oszczedzenia miejsca i poprawy przeplywu powietrza.

## Status projektu

Wersja 1.0 jest baza do testow mechaniki, elektroniki i procedur bazowania.
Przed praca z pelnymi predkosciami nalezy:

1. Zweryfikowac kierunki ruchu wszystkich osi.
2. Zmierzyc rzeczywisty przelicznik osi Z.
3. Zmierzyc przelozenie efektora.
4. Sprawdzic stany logiczne czujnikow optycznych.
5. Ustawic bezpieczne limity predkosci i przyspieszen.
