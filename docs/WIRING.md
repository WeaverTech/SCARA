# SCARA - kompletny schemat okablowania

Okablowanie dla firmware **SCARA-FW 2.2** (`src/main/config.h`).
Kontroler: Arduino Mega 2560, 4x sterownik TB6600, 4x NEMA 17,
serwo SG90 (gripper), opcjonalnie 3 krancowki optyczne.

## Schemat ogolny

```
                 +--------------------+
 PC (USB) -------|  Arduino Mega 2560 |
                 |  (logika 5 V)      |
 9 V PSU -------(barrel jack)         |
                 +---+----+----+----+-+
                     |    |    |    |         sygnaly PUL/DIR/ENA (5 V)
                +----+    |    |    +-------------------+
                |         |    |                        |
           +----v---+ +---v----+ +--------+        +---v----+
           | TB6600 | | TB6600 | | TB6600 |        | TB6600 |
           |   Z    | |   J1   | |   J2   |        |  TOOL  |
           +--+--+--+ +--+--+--+ +--+--+--+        +--+--+--+
              |  |       |  |       |  |              |  |
            24V  M     24V  M     24V  M            24V  M
              |  |       |  |       |  |              |  |
    24 V PSU -+--|-------+--|-------+--|--------------+  |
    (8.3 A)      |          |          |                 |
              NEMA17     NEMA17     NEMA17            NEMA17
              (os Z)     (bark)     (lokiec)          (efektor)
```

Trzy niezalezne obwody zasilania:

| Obwod | Zrodlo | Zasila |
| --- | --- | --- |
| Silniki | 24 V / 8.3 A (200 W) | Zaciski VCC/GND kazdego TB6600 |
| Logika | 9 V (barrel jack) | Arduino Mega |
| Serwo | 5 V (UBEC/BEC min. 1 A) | SG90 grippera (masa wspolna z Arduino!) |

> TB6600 maja wejscia optoizolowane, wiec masa 24 V **nie musi** byc laczona
> z masa Arduino. Masa serwa SG90 i ewentualnych krancowek **musi** byc
> wspolna z GND Arduino.

## 1. Sterowniki TB6600 -> Arduino Mega

Podlaczenie **wspolna katoda**: wszystkie wejscia `PUL-`, `DIR-`, `ENA-`
kazdego sterownika do **GND Arduino**. Wejscia `+` do pinow:

| Sterownik (os) | PUL+ | DIR+ | ENA+ | PUL-/DIR-/ENA- |
| --- | ---: | ---: | ---: | --- |
| Z (sruba) | 22 | 23 | 24 | GND Arduino |
| J1 (bark, 20:1) | 26 | 27 | 28 | GND Arduino |
| J2 (lokiec, 14:1) | 30 | 31 | 32 | GND Arduino |
| TOOL (efektor) | 34 | 35 | 36 | GND Arduino |

Logika ENA w firmware: pin **LOW = sterownik zalaczony** (ENABLE),
pin HIGH = odlaczony (DISABLE/ESTOP). Przy wspolnej katodzie dziala to
"z pudelka" - nic nie trzeba zmieniac.

## 2. Zasilanie i silniki -> TB6600

Kazdy TB6600:

| Zacisk | Podlaczenie |
| --- | --- |
| VCC | +24 V z zasilacza |
| GND | -V (masa) zasilacza 24 V |
| A+, A- | pierwsza cewka silnika |
| B+, B- | druga cewka silnika |

Pary cewek NEMA 17 znajdziesz multimetrem (para = ok. 1-3 om) albo
zwierajac dwa przewody - jesli walem kreci sie ciezko, to jest para.
Zamiana A+ z A- odwraca kierunek obrotow (alternatywa: `HOMING_DIR_*`
w `config.h`).

**Przekroje:** 24 V do sterownikow oraz silniki min. 0.5 mm2 (AWG20).
Sygnaly logiczne moga byc cienkie (0.25 mm2), najlepiej skrecane parami.

## 3. Przelaczniki DIP na TB6600 (wszystkie 4 sztuki tak samo)

- **Mikrokrok: 1/16 = 3200 imp/obr** - ustaw S1-S3 wg tabelki nadrukowanej
  na sterowniku w pozycji "3200 Pulse/rev" (tabelki roznia sie miedzy
  wersjami TB6600, dlatego kieruj sie nadrukiem, nie internetem).
- **Prad: ok. 1.5 A** (S4-S6 wg nadruku) - typowa wartosc dla NEMA 17;
  sprawdz prad znamionowy swoich silnikow i nie przekraczaj go.

Firmware zaklada 3200 krokow/obrot - inne ustawienie mikrokroku rozjedzie
wszystkie przeliczniki!

## 4. Krancowki (opcjonalne - bez nich uzywaj homingu recznego SETHOME)

Piny z przerwaniami zewnetrznymi, wejscia z `INPUT_PULLUP`,
stan aktywny **LOW**:

| Os | Pin Arduino | Czujnik optyczny (3 piny) | Mikrostyk (2 piny) |
| --- | ---: | --- | --- |
| J1 | 2 | VCC->5V, GND->GND, OUT->pin 2 | COM->GND, NO->pin 2 |
| J2 | 3 | VCC->5V, GND->GND, OUT->pin 3 | COM->GND, NO->pin 3 |
| Z | 18 | VCC->5V, GND->GND, OUT->pin 18 | COM->GND, NO->pin 18 |

Niepodlaczone piny sa bezpieczne (pullup trzyma stan HIGH = nieaktywny),
wiec robot dziala bez krancowek - homing wykonuj komenda `SETHOME`
(sekcja "Homing reczny" w aplikacji webowej).

> Jesli czujnik daje stan HIGH przy zadzialaniu, zmien
> `LIMIT_ACTIVE_STATE` w `config.h` na `HIGH`.

## 5. Gripper - serwo SG90

| Przewod SG90 | Podlaczenie |
| --- | --- |
| Pomaranczowy (sygnal) | pin **44** Arduino |
| Czerwony (+) | +5 V z **osobnego** zrodla 5 V (UBEC/BEC >= 1 A) |
| Brazowy (GND) | GND zrodla 5 V **oraz** GND Arduino (wspolna masa!) |

Nie zasilaj serwa z pinu 5V Arduino - SG90 przy zablokowaniu potrafi
pobrac >0.5 A i zresetuje plytke. Katy otwarcia/zamkniecia: `GRIPPER_OPEN_DEG`
/ `GRIPPER_CLOSED_DEG` w `config.h` (domyslnie 20 / 110 stopni).

## 6. Kolejnosc uruchomienia i test

1. Sprawdz DIP-y (3200 imp/obr, prad) **przed** podaniem 24 V.
2. Podlacz USB (bez 24 V) - wgraj firmware, w monitorze portu (115200)
   sprawdz `PING` -> `OK PONG`.
3. Podaj 24 V, komenda `ENABLE` - silniki powinny "zesztywniec".
4. `SETHOME`, potem `JOGR J1 5` - os ma sie ruszyc o 5 stopni. Sprawdz
   kierunki wszystkich osi (`JOGR J2/Z/TOOL ...`); odwrocone kierunki
   napraw zamiana A+/A- albo znakiem `HOMING_DIR_*`.
5. `GRIP 1` / `GRIP 0` - test grippera.
6. Dalej pracuj z aplikacji webowej (`webapp/`), najpierw na 10-20%
   predkosci.

## Checklist bezpieczenstwa

- [ ] Wspolna masa: Arduino GND <-> PUL-/DIR-/ENA- wszystkich TB6600.
- [ ] Wspolna masa: Arduino GND <-> GND zasilania serwa.
- [ ] Masa 24 V NIE laczona z logika (optoizolacja TB6600).
- [ ] DIP: 3200 imp/obr i prad <= znamionowego silnika (x4).
- [ ] Nigdy nie rozlaczaj przewodow silnika przy wlaczonym 24 V
      (grozi uszkodzeniem sterownika).
- [ ] Pierwsze ruchy: mala predkosc, reka na E-STOP w GUI.
