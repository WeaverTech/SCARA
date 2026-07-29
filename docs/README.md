# Dokumentacja

Ten katalog jest przeznaczony na dokumentacje techniczna robota SCARA.

Proponowana zawartosc:

- schemat polaczen Arduino Mega 2560 ze sterownikami TB6600 (4 osie),
- schemat zasilania 24 V dla silnikow i 9 V dla logiki,
- notatki z kalibracji osi Z (pasek GT2) i efektora,
- opis procedury homingu z czujnikami optycznymi (Z, bark, lokiec),
- zdjecia montazu i rewizje mechaniczne.

## Mapa pinow (Arduino Mega 2560 -> TB6600)

| Os | Silnik / naped | STEP (PUL) | DIR | ENA | Krancowka |
| --- | --- | ---: | ---: | ---: | ---: |
| Z | NEMA 17 / pasek GT2 | 22 | 23 | 24 | 40 |
| Bark (SHOULDER) | NEMA 17 / cykloidalna 20:1 | 26 | 27 | 28 | 41 |
| Lokiec (ELBOW) | NEMA 17 / cykloidalna 20:1 | 30 | 31 | 32 | 42 |
| Efektor (TOOL) | NEMA 17 / pasek zebaty | 34 | 35 | 36 | - |

Efektor nie ma krancowki - pozycja zerowa przyjmowana programowo.

## Przeliczniki krokow

Mikrokrok 1/16, NEMA 17 = 200 krokow -> `3200` mikrokrokow na obrot silnika.

| Os | Wzor | Wynik |
| --- | --- | --- |
| Bark | `(200*16*20)/360` | 177.7778 krokow/stopien |
| Lokiec | `(200*16*20)/360` | 177.7778 krokow/stopien |
| Z (GT2) | `3200 / (zeby_kola * 2 mm)` | np. 20T -> 80 krokow/mm |
| Efektor | `(200*16*przelozenie)/360` | zalezne od kol pasowych |

## Dane do uzupelnienia podczas uruchomienia

| Parametr | Stala w kodzie | Wartosc |
| --- | --- | --- |
| Zeby kola pasowego osi Z | `Z_PULLEY_TEETH` | TODO |
| Kroki osi Z na 1 mm | `Z_STEPS_PER_MM` | TODO (wyliczane) |
| Przelozenie paska efektora | `TOOL_BELT_RATIO` | TODO |
| Kroki efektora na 1 stopien | `TOOL_STEPS_PER_DEGREE` | TODO (wyliczane) |
| Dlugosc czlonu L1 (bark->lokiec) | `ARM1_LENGTH_MM` | TODO (pomiar z CAD) |
| Dlugosc czlonu L2 (lokiec->efektor) | `ARM2_LENGTH_MM` | TODO (pomiar z CAD) |
| Stan aktywny krancowki Z | - | TODO |
| Stan aktywny krancowki barku | - | TODO |
| Stan aktywny krancowki lokcia | - | TODO |

## Tryb prototypu bez lokcia

Druga przekladnia cykloidalna moze byc dobudowana pozniej. Do testow bez niej
nalezy w `src/main/main.ino` ustawic:

```cpp
constexpr bool ELBOW_PRESENT = false;
```

Sterownik pominie wtedy zalaczanie, homing i ruchy osi lokcia, zachowujac pelna
obsluge osi Z, barku i efektora.
