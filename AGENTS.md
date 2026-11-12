# SCARA — jak kontynuować pracę

Ten plik jest dla kolejnego agenta (albo człowieka), który otwiera repozytorium bez historii czatu.

## Gałąź

Źródłem prawdy jest **`main`**. Jest tu firmware, panel webowy, symulacja, CAD v1 i propozycja osi Z v2.

Gałęzie `cursor/*` to kolejne sesje agentów. Ich treść albo już jest w `main`, albo została świadomie odrzucona, bo była starsza i sprzeczna (inne piny, robot bez łokcia, inne stałe). Lista: [`docs/HISTORY.md`](docs/HISTORY.md).

Nie rób tego:

- nie szukaj „prawdziwego” projektu na innej gałęzi,
- nie merguj PR #1, #2, #3 ani #4 — są sprzed uporządkowania i część celuje w pusty albo częściowy `main`,
- nie odtwarzaj `src/main.ino` ani `src/config.h` z korzenia `src/` (aktualny szkic to `src/main/`).

Nową pracę commituj na gałęzi od **aktualnego `main`** i otwieraj PR do `main`.

## Zanim zmienisz liczby

Przeczytaj [`docs/STATUS.md`](docs/STATUS.md). Świadomie zostały dwie niespójności i nie wolno ich „naprawić” przez skopiowanie jednej wartości do drugiej:

1. Długości ramion. Firmware, `sim/` i `webapp/` mają L1 = 139.928 mm, L2 = 140 mm. Odległości osi w `cad/v1/SCARA.step` to około 170 mm i 150 mm.
2. Oś Z. CAD v1 to pasek GT2 i koła 36T. Firmware ma `STEPS_PER_MM_Z = 400` (śruba, odpowiednik T8x8).

Piny, przełożenie J1 20:1, przełożenie J2 **14:1**, mikrokrok 1/16 i wersja `SCARA-FW 2.2` bierz z [`src/main/config.h`](src/main/config.h). Starsze README pisały, że łokieć jest 20:1 — to nieaktualne. `ELBOW_PRESENT` jest w `config.h`.

`cad/v2/` to propozycja mechaniczna (nie zbudowana). Nie przepisuj pod nią firmware, dopóki użytkownik nie wybierze wariantu (zakres J1, skok Z, skok śruby).

## Mapa

| Katalog | Rola | Wejście |
| --- | --- | --- |
| `src/main/` | firmware Mega 2560, AccelStepper | `config.h`, `main.ino` |
| `webapp/` | GUI teach pendant, FastAPI, port `sim` | `webapp/README.md` |
| `host/` | klient szeregowy | `host/README.md` |
| `sim/` | FK/IK, URDF, PyBullet | `sim/README.md` |
| `cad/v1/` | STEP i rendery zbudowanego modelu | `cad/README.md` |
| `cad/v2/` | model CadQuery nowej osi Z, sztywność, rendery | `cad/v2/README.md` |
| `docs/` | stan, okablowanie, historia | `docs/README.md` |

Kinematyka w milimetrach jest zdublowana: `sim/kinematics.py` (metry) i `webapp/backend/kinematics_mm.py` (milimetry). Obie mają trzymać te same stałe co `config.h`.

## Jak sprawdzić, że nic się nie rozsypało

```bash
cd webapp && python3 -m pytest tests/ -q
cd sim    && python3 -m pytest -q
cd cad/v2 && python3 -m pytest -q test_stiffness.py
```

Model 3D v2 (`cad/v2/z_gantry_v2.py`, `render.py`) potrzebuje CadQuery i PyVista z `cad/v2/requirements.txt`. Sam test sztywności ich nie wymaga. Ramię w eksporcie STEP jest wczytywane z `cad/v1/SCARA.step`.

Panel bez robota: `uvicorn backend.main:app --host 127.0.0.1 --port 8000` w `webapp/`, w GUI port `sim`.

## Język i styl zmian

Użytkownik pisze po polsku — odpowiadaj po polsku. Istniejące komentarze w kodzie są po polsku, zwykle bez ogonków. Nowe dokumenty w `docs/` i ten plik są po polsku z ogonkami.

Nie dorzucaj drugiego README z tą samą treścią. Aktualizuj `docs/STATUS.md`, kiedy zmienia się to, co jest zbudowane, albo kiedy któraś niespójność zostaje zmierzona i rozstrzygnięta.
