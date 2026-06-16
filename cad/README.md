# CAD — modele 3D i pliki do druku

Ten folder przeznaczony jest na modele 3D konstrukcji robota SCARA v1.0.

## Sugerowana organizacja

```
cad/
├── stl/        # Pliki STL gotowe do druku (slicer)
├── step/       # Modele parametryczne / źródłowe (STEP / F3D / SCAD)
└── prints/     # Notatki o ustawieniach druku (materiał, wypełnienie, itp.)
```

## Materiał

Elementy drukowane w **PET-G** (dobra wytrzymałość mechaniczna i odporność
temperaturowa, odpowiednia dla części konstrukcyjnych).

## Główne elementy do umieszczenia tutaj

- Autorska **przekładnia cykloidalna 20:1** (główna oś obrotowa ramienia).
- Mocowania silników NEMA 17 (Z, ramię, efektor).
- Ramię (L1 = 150 mm) i mocowanie efektora.
- Obudowa **Control Box** o strukturze plastra miodu
  (zasilacz 24 V, szyna DIN na Arduino Mega, 4× TB6600 pionowo).
- Uchwyty optycznych krańcówek (Z i ramię).

> Wskazówka: dla części przenoszących obciążenia (przekładnia, ramię) stosuj
> wyższe wypełnienie i więcej obrysów (perimeters).
