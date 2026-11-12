# Stan projektu

Data opisu: 2026-11-12. Źródła: pliki na `main`, pomiary z `cad/v1/SCARA.step` (opisane w `cad/v2/README.md`).

## Co jest czym

| Warstwa | Stan | Gdzie |
| --- | --- | --- |
| Mechanika v1 | Model Fusion: rama 2020, dwa wałki 8 mm, pasek GT2, dwie przekładnie cykloidalne, trzy NEMA 17 na ramieniu, silnik Z na szczycie wieży. | `cad/v1/SCARA.step`, `cad/v1/ramie.step`, `cad/v1/renders/` |
| Firmware | SCARA-FW 2.2. IK w płaszczyźnie, homing na przerwaniach, `SETHOME` / `JOGR` bez krańcówek, `SPEED`, gripper SG90. | `src/main/` |
| Panel | Teach pendant w przeglądarce, punkty, programy, interpolacja liniowa, port `sim`. | `webapp/` |
| Klient | Ten sam protokół, bez GUI. | `host/scara_client.py` |
| Symulacja | FK/IK i URDF ze stałymi firmware (nie ze STEP). | `sim/` |
| Oś Z v2 | Propozycja: 3× wałek 12 mm w trójkącie 140 mm, silnik J1 w środku, śruba T8, zabudowa. Niezbudowana. Firmware jej nie zna. | `cad/v2/` |

Łańcuch kinematyczny, który obsługuje kod: **Z → bark J1 (20:1) → łokieć J2 (14:1) → efektor (pasek)**. Czwarty silnik jest w użyciu. `ELBOW_PRESENT` w `config.h` (`1` = łokieć jest) pozwala pominąć drugą przekładnię na czas testów.

## Liczby, których nie wolno uzgadniać na ślepo

| Wielkość | CAD v1 (`SCARA.step`) | Firmware / `sim` / `webapp` | Jak z tego korzystać |
| --- | --- | --- | --- |
| L1, bark → łokieć | ok. **170 mm** (osie łożysk) | **139.928 mm** | Obie wartości są w repo. Ruch na prawdziwym robocie pojedzie według firmware. Zmiana wymaga pomiaru suwmiarką i tej samej poprawki w `config.h`, `sim/kinematics.py`, `sim/scara.urdf` i `webapp/backend/kinematics_mm.py`. |
| L2, łokieć → efektor | ok. **150 mm** | **140 mm** | J.w. |
| Odległość kolumny od osi barku | Wałki są ~61 mm za wejściem J1, oś barku ~161 mm przed wałkami. 165 mm to głębokość ramy (Y od −165 do 0), nie offset kinematyczny. | `Z_AXIS_OFFSET_MM = 165` | Zostaw 165 w kodzie, dopóki ktoś nie zmierzy, od jakiego punktu liczy się układ współrzędnych. |
| Przełożenie J1 | przekładnia cykloidalna | **20:1** | Zgodne. |
| Przełożenie J2 | przekładnia cykloidalna | **14:1** | Bierz 14:1 z `config.h`. Wzmianki o 20:1 dla łokcia w starych README są nieaktualne. |
| Napęd Z | pasek GT2, koła 36T, silnik na górze wieży (z ≈ 500 mm) | śruba, **400 kroków/mm** | CAD opisuje narysowaną maszynę. Firmware jest napisany pod śrubę T8x8 i nigdy nie został przeliczony na koło 36T (to byłoby ok. 44.4 kroku/mm). Nie zmieniaj `STEPS_PER_MM_Z`, dopóki nie wiadomo, co fizycznie kręci osią. |
| Skok Z | wałki długości 500 mm | `Z_MAX_MM = 150` | Limit programowy jest 150 mm. |
| Piny krok/kierunek/enable | — | Z 22/23/24, J1 26/27/28, J2 30/31/32, TOOL 34/35/36 | Tylko te. Schemat: `docs/WIRING.md`. |
| Krańcówki | — | J1 pin 2, J2 pin 3, Z pin 18, aktywne LOW | Efektor bez krańcówki. |
| Wersja firmware | — | `FW_VERSION "SCARA-FW 2.2"` | Panel odrzuca inną wersję. Nie obniżaj jej w dokumentacji do 2.0. |

Masa ramienia ~3.6 kg użyta w `cad/v2/stiffness.py` jest szacunkiem z objętości STEP (PETG 60%, NEMA 17 = 350 g), nie pomiarem na wadze.

## Oś Z v2 (skrót)

Policzona, niewybrana. Przy wałkach 12 mm, wolnej długości 348 mm i tulejach rozstawionych o 110 mm model belkowy daje około 30× sztywności na przechył i około 370× na skręcanie względem v1. Koszt: z pełną przednią osłoną bark ma około ±87° zamiast ±125° zapisanych w firmware. Szczegóły, BOM i otwarte pytania (skok Z, skok śruby, czy przesunąć J1 przed środek trójkąta) są w [`../cad/v2/README.md`](../cad/v2/README.md).

Dopóki v2 nie zostanie wybrana, kod sterujący opisuje maszynę z tabeli wyżej, a nie model z `cad/v2/`.

## Po decyzji pomiarowej

Jedna zmiana geometrii dotyka czterech miejsc: `src/main/config.h`, `sim/kinematics.py`, `sim/scara.urdf`, `webapp/backend/kinematics_mm.py`. Potem testy z `AGENTS.md` i wpis w tej tabeli, że wartość jest zmierzona.
