# SCARA Robot

Repozytorium robota typu SCARA budowanego z profili aluminiowych 20x20 i
elementow drukowanych w 3D z PET-G. Docelowa konstrukcja to **dwuczlonowe
ramie** (bark + lokiec) z podnoszona osia Z oraz obrotowym efektorem koncowym.

> **Uwaga o prototypie fizycznym:** na etapie testow srodkowy przegub (lokiec)
> moze byc chwilowo pominiety, aby uniknac budowy drugiej przekladni
> cykloidalnej. W repozytorium kod i obliczenia traktuja jednak lokiec jako
> obecny (wersja docelowa). Do pracy bez fizycznego lokcia wystarczy ustawic
> `ELBOW_PRESENT = false` w [`src/main/main.ino`](src/main/main.ino).

## Architektura robota

Lancuch kinematyczny (4 osie / 4 silniki NEMA 17, 4 sterowniki TB6600):

- **Os Z** - ruch gora/dol realizowany na **pasku GT2** (prowadnice na walkach
  8 mm, wsporniki SHF8).
- **Bark (glowna os obrotowa)** - autorska, drukowana w 3D **przekladnia
  cykloidalna 20:1**.
- **Lokiec (srodkowy przegub)** - druga **przekladnia cykloidalna 20:1**
  (w prototypie opcjonalnie pomijana, patrz uwaga powyzej).
- **Efektor koncowy** - obrot narzedzia napedzany **paskiem zebatym** z silnika
  umieszczonego na ramieniu.

## Wymiary i dane kinematyczne

| Parametr | Wartosc | Opis |
| --- | ---: | --- |
| Offset osi Z | 165 mm | Odleglosc od osi prowadnic pionowych do srodka glownej osi obrotu |
| Dlugosc ramienia L1 | 150 mm* | Bark -> lokiec (*do potwierdzenia pomiarem z modelu) |
| Dlugosc ramienia L2 | 150 mm* | Lokiec -> efektor (*do potwierdzenia pomiarem z modelu) |
| Przelozenie barku | 20:1 | Przekladnia cykloidalna |
| Przelozenie lokcia | 20:1 | Przekladnia cykloidalna |
| Mikrokrok | 1/16 | Ustawienie dla wszystkich sterownikow TB6600 |

> Brief w wersji uproszczonej podawal 150 mm jako odleglosc glownej osi obrotu od
> efektora. Po wprowadzeniu lokcia ramie ma dwa czlony (L1, L2), ktore nalezy
> zmierzyc osobno na podstawie modelu `cad/SCARA.step`.

### Przeliczniki krokow (mikrokrok 1/16, NEMA 17 = 200 krokow)

Pelny obrot silnika w mikrokrokach: `200 * 16 = 3200`.

Osie obrotowe (przekladnia cykloidalna 20:1) - bark i lokiec:

```text
(200 * 16 * 20) / 360 = 177.7778 krokow/stopien
```

Os Z (pasek GT2):

```text
steps/mm = (200 * 16) / (liczba_zebow_kola * skok_paska_mm)
         = 3200 / (Z_PULLEY_TEETH * 2 mm)   # GT2 = 2 mm
```

Efektor (pasek zebaty z przelozeniem):

```text
steps/deg = (200 * 16 * przelozenie_paska) / 360
przelozenie_paska = zeby_kola_napedzanego / zeby_kola_silnika
```

> Liczbe zebow kol pasowych osi Z i efektora nalezy odczytac z modelu/BOM i
> uzupelnic stale `Z_PULLEY_TEETH` oraz `TOOL_BELT_RATIO` w kodzie.

## Elektronika

| Komponent | Konfiguracja |
| --- | --- |
| Mikrokontroler | Arduino Mega 2560, logika 5 V |
| Sterowniki | 4x TB6600 (wszystkie w uzyciu), sterowanie PUL/DIR/ENA |
| Silniki | 4x NEMA 17 (Z, bark, lokiec, efektor) |
| Zasilanie silnikow | Zasilacz przemyslowy 24 V, 8.3 A, 200 W |
| Zasilanie logiki | Osobny zasilacz 9 V do gniazda Arduino Mega |
| Krancowki | Optyczne czujniki szczelinowe (Z, bark, lokiec) |

Masy zasilania logiki i sygnalow sterujacych TB6600 powinny byc wspolne
(mostkowane GND). Zasilanie silnikow (24 V) prowadzone jest oddzielnie do
sterownikow. Efektor nie ma krancowki (pozycja zerowa przyjmowana programowo).

## Modele CAD (`cad/`)

Pliki STEP wyeksportowane z Autodesk Fusion (AP214, jednostki: mm):

- `SCARA.step` - pelny montaz (rama, os Z, ramie, przekladnie, napedy).
- `ramie.step` - sam podzespol ramienia z przekladnia cykloidalna.

Wybrane elementy z listy materialowej (BOM):

- Rama: profile `2020 alu section`, `SCARA_FRAME_V2`.
- Os Z: walki 8 mm, wsporniki `SHF8`, wozek liniowy, pasek GT2.
- Przekladnia cykloidalna `Cycloidal Drive 160mm` (typ TRICY MH-P16): krzywki
  (`cam a-b`, `cam a-c`), pierscienie (`ring a/b/c`), 20 kolkow, waly
  wejsciowy/wyjsciowy, lozyska `NSK 6810ZZ` i `MH-P16`.
- Napedy: `NEMA17` + mocowania, plyty `Axis1`/`Axis2`.

## Struktura repozytorium

```text
.
+-- cad/                  # Modele 3D (STEP) i zrzuty konstrukcji
+-- docs/                 # Schematy, notatki montazowe i kalibracja
`-- src/
    `-- main/
        `-- main.ino      # Szkic Arduino Mega z AccelStepper (4 osie)
```

## Oprogramowanie

Kod znajduje sie w [`src/main/main.ino`](src/main/main.ino). Szkic zawiera:

- definicje pinow `PUL`, `DIR`, `ENA` dla czterech osi,
- flage `ELBOW_PRESENT` do pracy bez fizycznego lokcia,
- konfiguracje biblioteki `AccelStepper` (predkosci, przyspieszenia),
- stale przeliczeniowe (cykloidalne 20:1, pasek Z GT2, pasek efektora),
- stale geometrii (offset Z, L1, L2) pod przyszla kinematyke odwrotna,
- szablony procedur homingu dla osi Z, barku i lokcia,
- parser prostych komend przez port szeregowy.

### Wymagania

- Arduino IDE albo Arduino CLI.
- Plytka: **Arduino Mega 2560**.
- Biblioteka: **AccelStepper**.

### Przykladowe komendy szeregowe

Po wgraniu szkicu i otwarciu monitora portu szeregowego (`115200 baud`):

```text
STATUS
HOME Z
HOME SHOULDER
HOME ELBOW
MOVE Z 10
MOVE SHOULDER 45
MOVE ELBOW 30
MOVE TOOL 90
STOP
```

## Obudowa sterownika (Control Box)

Drukowana w 3D obudowa o strukturze plastra miodu (chlodzenie pasywne + miejsce
na wentylatory). Na dole zasilacz 24 V, nad nim zintegrowana szyna DIN dla
Arduino Mega, a 4 sterowniki TB6600 montowane pionowo obok siebie.

## Status projektu

Wersja docelowa zaklada pelny dwuczlonowy SCARA. Przed praca z pelnymi
predkosciami nalezy:

1. Zweryfikowac kierunki ruchu wszystkich osi.
2. Zmierzyc liczbe zebow kola pasowego osi Z i uzupelnic `Z_PULLEY_TEETH`.
3. Zmierzyc przelozenie paska efektora (`TOOL_BELT_RATIO`).
4. Zmierzyc dlugosci czlonow L1 i L2 z modelu CAD.
5. Sprawdzic stany logiczne czujnikow optycznych i bezpieczne limity ruchu.
