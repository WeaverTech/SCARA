# CAD

Modele 3D i materialy zrodlowe robota SCARA.

## Pliki w repozytorium

- `SCARA.step` - pelny montaz (rama 2020, os Z, ramie, dwie przekladnie
  cykloidalne, napedy NEMA 17). Eksport z Autodesk Fusion, AP214, jednostki mm.
- `ramie.step` - sam podzespol ramienia z przekladnia cykloidalna.
- `Zrzut ekranu *.png/.jpg` - rendery konstrukcji (cala maszyna, ramie,
  control box).

## Wybrana lista materialowa (BOM)

- **Rama:** profile `2020 alu section`, `SCARA_FRAME_V2`.
- **Os Z:** walki liniowe 8 mm, wsporniki `SHF8`, wozek liniowy
  (`8mm Mil Araba`), nakretka blokujaca, pasek GT2.
- **Przekladnia cykloidalna** `Cycloidal Drive 160mm` (TRICY MH-P16):
  krzywki `cam a-b` / `cam a-c`, pierscienie `ring a/b/c`, 20 kolkow (`pin`),
  waly `input-shaft` / `output shaft`, lozyska `NSK 6810ZZ` i `MH-P16 Bearing`,
  obudowa `housing-top` / `housing-bottom`.
- **Napedy:** `NEMA17 Model` + `Nema 17 mount` + `Gearbox Mount`,
  plyty `Axis1_Plate_*`, `Axis2_Plate_*`, dystanse.
- **Lacznik:** sruby `91292A352`, standoffy.

## Sugerowany podzial przy rozbudowie

- `printed-parts/` - elementy drukowane w 3D z PET-G,
- `control-box/` - obudowa elektroniki i mocowania sterownikow,
- `gearbox/` - przekladnia cykloidalna (bark i lokiec),
- `exports/` - pliki STL/STEP gotowe do druku lub obrobki.

> Pliki STEP sa duze (kilkanascie MB). Przy dalszym przyroscie ciezkich modeli
> warto rozwazyc Git LFS.
