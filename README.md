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

Wymiary zmierzone w CAD (od osi do osi):

| Parametr | Wartosc | Opis |
| --- | ---: | --- |
| Offset osi Z | 165 mm | Odleglosc kolumny Z od osi barku |
| Dlugosc ramienia L1 | 139.928 mm | Bark -> lokiec (zmierzone w CAD) |
| Dlugosc ramienia L2 | 140.000 mm | Lokiec -> efektor (zmierzone w CAD) |
| Maksymalny zasieg | 279.928 mm | L1 + L2 |
| Strefa martwa | 0.072 mm | \|L1 - L2\| |
| Strefa wykluczenia | R = 45 mm | Wokol kolumny Z (ochrona przed kolizja) |
| Przelozenie barku (J1) | 20:1 | Przekladnia cykloidalna |
| Przelozenie lokcia (J2) | 14:1 | Przekladnia cykloidalna |
| Mikrokrok | 1/16 | Ustawienie dla wszystkich sterownikow TB6600 |

### Przeliczniki krokow (mikrokrok 1/16, NEMA 17 = 200 krokow)

Pelny obrot silnika w mikrokrokach: `200 * 16 = 3200`.

```text
J1 (bark,  cykloidalna 20:1): (200 * 16 * 20) / 360 = 177.7778 krokow/stopien
J2 (lokiec, cykloidalna 14:1): (200 * 16 * 14) / 360 = 124.4444 krokow/stopien
Z  (sruba napedowa):           400 krokow/mm
```

Efektor (pasek zebaty z przelozeniem):

```text
steps/deg = (200 * 16 * przelozenie_paska) / 360
przelozenie_paska = zeby_kola_napedzanego / zeby_kola_silnika
```

> Przelozenie paska efektora (`TOOL_BELT_RATIO`) nalezy odczytac z modelu/BOM
> i uzupelnic w `src/main/config.h`.

## Elektronika

| Komponent | Konfiguracja |
| --- | --- |
| Mikrokontroler | Arduino Mega 2560, logika 5 V |
| Sterowniki | 4x TB6600 (wszystkie w uzyciu), sterowanie PUL/DIR/ENA |
| Silniki | 4x NEMA 17 (Z, bark, lokiec, efektor) |
| Zasilanie silnikow | Zasilacz przemyslowy 24 V, 8.3 A, 200 W |
| Zasilanie logiki | Osobny zasilacz 9 V do gniazda Arduino Mega |
| Krancowki | Opto/Hall: J1 -> pin 2, J2 -> pin 3, Z -> pin 18 (przerwania zewnetrzne) |

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
+-- host/                 # Klient Pythona (pyserial) dla firmware
+-- sim/                  # Kinematyka (URDF) i symulacja (PyBullet)
+-- webapp/               # Aplikacja webowa: GUI, punkty, programy, symulator
`-- src/
    `-- main/
        +-- config.h      # Geometria, przeliczniki, piny, limity
        `-- main.ino      # Firmware Arduino Mega (IK, homing, protokol)
```

## Aplikacja webowa (teach pendant)

W [`webapp/`](webapp/) znajduje sie lokalna aplikacja webowa w stylu RC+:
jog, pamiec punktow (Teach), edytor programow z interpolacja liniowa,
sterowanie predkoscia i gripperem (serwo SG90), wizualizacja 2D na zywo
oraz wbudowany symulator robota (praca bez sprzetu, port `sim`).
Uruchomienie: `cd webapp && pip install -r requirements.txt &&
uvicorn backend.main:app --port 8000`, GUI pod `http://localhost:8000`.

## Kinematyka i symulacja

W katalogu [`sim/`](sim/) znajduje sie model **URDF** robota, analityczna
kinematyka prosta i odwrotna (`kinematics.py`) oraz symulacja w **PyBullet**
(`simulate.py`). Przeliczniki katow na kroki silnikow sa spojne z firmware.
Model URDF jest standardowy, wiec da sie go uzyc takze w ROS 2 (RViz2, MoveIt 2,
Gazebo). Szczegoly: [`sim/README.md`](sim/README.md).

## Oprogramowanie

Firmware: [`src/main/main.ino`](src/main/main.ino) +
[`src/main/config.h`](src/main/config.h). Zawiera:

- pelna kinematyke odwrotna i prosta w plaszczyznie XY (dwa czlony L1/L2),
- wybor konfiguracji lokcia ("up"/"down") w komendzie ruchu,
- walidacje zasiegu, limitow stawow i strefy wykluczenia wokol kolumny Z,
- 3-fazowy homing (najazd -> odjazd -> wolny latch) na krancowkach z przerwaniami,
- monitoring krancowek w ruchu (przerwania zewnetrzne, ESTOP + wymagany re-home),
- liniowy protokol `OK`/`ERR`/`DONE` dla nadrzednego hosta w Pythonie,
- flage `ELBOW_PRESENT` do pracy bez fizycznego lokcia.

Host Python: [`host/scara_client.py`](host/scara_client.py) (pyserial) -
API `home()`, `move(x, y, z, tool)`, `jog()`, `solve_ik()`, `status()`.
Opis protokolu: [`host/README.md`](host/README.md).

### Wymagania

- Arduino IDE albo Arduino CLI.
- Plytka: **Arduino Mega 2560**.
- Biblioteka: **AccelStepper**.
- Host: Python 3 + **pyserial**.

### Przykladowe komendy szeregowe

Po wgraniu szkicu i otwarciu monitora portu szeregowego (`115200 baud`):

```text
PING
STATUS
HOME
MOVE X200 Y50 Z20 E1
IK X150 Y100
JOG J1 45
JOG Z 10
STOP
ESTOP
```

## Obudowa sterownika (Control Box)

Drukowana w 3D obudowa o strukturze plastra miodu (chlodzenie pasywne + miejsce
na wentylatory). Na dole zasilacz 24 V, nad nim zintegrowana szyna DIN dla
Arduino Mega, a 4 sterowniki TB6600 montowane pionowo obok siebie.

## Status projektu

Geometria (L1, L2, offset Z, zasieg) jest zmierzona w CAD i zweryfikowana.
Przed praca z pelnymi predkosciami nalezy:

1. Zweryfikowac kierunki ruchu wszystkich osi (`HOMING_DIR_*` w `config.h`).
2. Zmierzyc przelozenie paska efektora (`TOOL_BELT_RATIO`).
3. Zweryfikowac pozycje krancowek i wartosci `*_HOME_POS_*` w `config.h`.
4. Sprawdzic stany logiczne czujnikow (`LIMIT_ACTIVE_STATE`) i limity ruchu.
