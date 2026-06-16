# Kinematyka uproszczonego SCARA

## Model ruchu

Wersja 1.0 nie posiada jeszcze "lokcia", dlatego uklad ma trzy sterowane osie:

1. **Os Z** - ruch pionowy narzedzia,
2. **Os ramienia** - obrot calego ramienia wokol osi bazy,
3. **Os efektora** - obrot narzedzia na koncu ramienia.

Z punktu widzenia ruchu w plaszczyznie XY narzedzie nie porusza sie po dowolnym punkcie, ale po **luku o stalym promieniu**.

## Parametry geometryczne

- `OFFSET_X = 165 mm`
- `L1 = 150 mm`

Przyjmujac, ze srodek pionowej osi Z jest w punkcie `(0, 0)`, a os obrotu ramienia jest przesunieta o `OFFSET_X` w osi X:

```text
x = OFFSET_X + L1 * cos(theta)
y =             L1 * sin(theta)
```

gdzie:

- `theta` - kat ramienia w stopniach lub radianach,
- `L1` - dlugosc ramienia od osi przekladni do osi efektora.

## Ograniczenie zasiegu

Poniewaz promien jest staly, poprawne polozenia XY musza spelniac warunek:

```text
sqrt((x - OFFSET_X)^2 + y^2) = L1
```

To oznacza, ze w tej wersji nie ma pelnej odwrotnej kinematyki SCARA - mozliwy jest tylko ruch po zadanym luku.

## Przeliczenie krokow dla osi ramienia

Przy silniku 200 krokow/obrot, mikrokroku 1/16 oraz przelozeniu 20:1:

```text
steps_per_degree = (200 * 16 * 20) / 360
steps_per_degree = 177.777...
```

W kodzie wartosc ta jest zapisana jako:

```cpp
ARM_STEPS_PER_DEG
```

## Przeliczenie krokow dla osi Z

Wartosc zalezy od rzeczywistego skoku napedu:

```text
steps_per_mm = (200 * 16) / lead_mm_per_rev
```

Do uzupelnienia po pomiarze:

```cpp
Z_LEAD_MM_PER_REV
Z_STEPS_PER_MM
```

## Przeliczenie krokow dla efektora

Wartosc zalezy od stosunku zebatek:

```text
tool_steps_per_degree = (200 * 16 * tool_ratio) / 360
```

Do uzupelnienia po policzeniu przelozenia:

```cpp
TOOL_RATIO
TOOL_STEPS_PER_DEG
```
