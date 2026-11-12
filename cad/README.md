# CAD

Dwa modele. Nie mieszają się w jednym katalogu.

| Katalog | Co to jest | Czy według tego jeździ firmware |
| --- | --- | --- |
| [`v1/`](v1/) | Eksport z Fusion: maszyna narysowana w czerwcu 2026. | Częściowo. Ramię tak, oś Z w CAD jest na pasku, a firmware zakłada śrubę. Patrz [`../docs/STATUS.md`](../docs/STATUS.md). |
| [`v2/`](v2/) | Parametryczna propozycja nowej osi Z (CadQuery). Ramię jest brane z `v1/SCARA.step`. | Nie. To analiza i model do decyzji, nie zbudowana maszyna. |

## v1 — pliki

- [`v1/SCARA.step`](v1/SCARA.step) — cały zespół (rama 2020, oś Z, ramię, dwie przekładnie, napędy). AP214, milimetry.
- [`v1/ramie.step`](v1/ramie.step) — samo ramię z przekładnią cykloidalną.
- [`v1/renders/`](v1/renders/) — zrzuty z Fusion, nazwane po tym, co widać (wcześniej `Zrzut ekranu …`).

| Render | Zawartość |
| --- | --- |
| `full-machine-2026-06-09.png` / `.jpg` | Cała maszyna, wczesny widok. |
| `arm-iso-2026-06-10.png` | Ramię z boku. |
| `arm-top-2026-06-16.png` | Ramię z góry. |
| `full-machine-2026-06-16.png` | Cała maszyna, późniejszy widok. |
| `control-box-2026-06-10.png` | Obudowa sterownika, zasilacz i Mega. |
| `control-box-drivers-2026-06-10.png` | Ta sama obudowa z czterema TB6600. |

## v1 — z listy materiałowej STEP

- Rama: profile `2020 alu section`, zespół `SCARA_FRAME_V2`.
- Oś Z: wałki 8 mm, wsporniki `SHF8`, wózek `8mm Mil Araba`, nakrętka blokująca, pasek GT2, koła `GT2 36T`.
- Przekładnia `Cycloidal Drive 160mm` (TRICY MH-P16): krzywki `cam a-b` / `cam a-c`, pierścienie `ring a/b/c`, 20 kołków, wały wejściowy i wyjściowy, łożyska `NSK 6810ZZ` i `MH-P16`, obudowy `housing-top` / `housing-bottom`.
- Napędy: `NEMA17` + mocowania, płyty `Axis1_Plate_*` i `Axis2_Plate_*`.

Odległości osi zmierzone na tym STEP (do porównania z firmware, nie do cichej podmiany): bark → łokieć ≈ 170 mm, łokieć → efektor ≈ 150 mm, wejście przekładni J1 → oś barku = 100 mm. Rozpisane w [`v2/README.md`](v2/README.md) i [`../docs/STATUS.md`](../docs/STATUS.md).

## v2

Wejście: [`v2/README.md`](v2/README.md). Model: `v2/z_gantry_v2.py`, eksport `v2/z_gantry_v2.step`, rendery w `v2/renders/`.

Pliki STEP są duże. Przy kolejnych ciężkich modelach warto przejść na Git LFS, zanim katalog CAD urośnie drugi raz.
