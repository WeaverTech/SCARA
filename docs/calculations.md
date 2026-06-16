# Obliczenia stałych (kroki na jednostkę)

Wszystkie osie używają silników NEMA 17 (**200 pełnych kroków / obrót**) oraz
sterowników TB6600 w trybie mikrokroku **1/16**.

Liczba mikrokroków na pełny obrót silnika:

```
200 × 16 = 3200 mikrokroków / obrót
```

---

## 1. Ramię główne — przekładnia cykloidalna 20:1

Przełożenie 20:1 oznacza, że wał wyjściowy obraca się 20× wolniej niż silnik.

```
kroki_na_stopień = (200 × 16 × 20) / 360
                 = 64000 / 360
                 = 177.777...  kroków / 1°
```

Stała w kodzie: `ARM_STEPS_PER_DEG` (z `ARM_GEAR_RATIO = 20`).

Pełny obrót ramienia (360°) = `64000` mikrokroków.

---

## 2. Oś Z — śruba trapezowa

Wzór ogólny:

```
kroki_na_mm = (200 × 16) / skok_gwintu_mm
            = 3200 / lead_mm
```

| Skok śruby (lead) | kroki / mm |
| --- | --- |
| 2 mm | 1600 |
| 4 mm | 800 |
| 8 mm | 400 |

> ⚠️ **DO POMIARU:** zmierz rzeczywisty skok śruby z Elegoo Saturn i wpisz do
> `Z_LEAD_MM` w `src/config.h`. Domyślnie ustawiono przykładowo `8.0 mm`.

Stała w kodzie: `Z_STEPS_PER_MM`.

---

## 3. Efektor — napęd paskiem zębatym

Przełożenie paska = liczba zębów koła napędzanego / liczba zębów koła silnika.

```
kroki_na_stopień = (200 × 16 × przełożenie_paska) / 360
```

| Przełożenie | kroki / ° |
| --- | --- |
| 1:1 | 8.888… |
| 2:1 | 17.777… |
| 3:1 | 26.666… |

> ⚠️ **DO POMIARU:** policz zęby zębatek i wpisz do `EFFECTOR_GEAR_RATIO`
> w `src/config.h`. Domyślnie ustawiono przykładowo `2.0`.

Stała w kodzie: `EFF_STEPS_PER_DEG`.

---

## 4. Geometria (dla przyszłej kinematyki odwrotnej)

| Symbol | Wartość | Opis |
| --- | --- | --- |
| `Z_AXIS_OFFSET_MM` | 165 mm | Offset osi Z (prowadnice → środek osi obrotu). |
| `ARM_LENGTH_L1_MM` | 150 mm | Promień ramienia L1 (oś obrotu → oś efektora). |

W wersji 1.0 narzędzie porusza się po **łuku o stałym promieniu L1**, więc
pozycja kątowa ramienia jednoznacznie określa położenie efektora na tym łuku.
Pełna kinematyka X/Y zostanie dodana wraz z drugim segmentem ("łokciem") w v2.0.
