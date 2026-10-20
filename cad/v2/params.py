"""Parametry geometrii osi Z v2 (wszystkie wymiary w mm).

Uklad wspolrzednych v2:
  - poczatek (0, 0) w srodku trojkata walkow (centroid), z = 0 na blacie stolu,
  - +X do przodu (w strone ramienia), +Z do gory.
Silnik J1 (wejscie przekladni cykloidalnej) stoi dokladnie w centroidzie,
os barku (wyjscie przekladni) jest przesunieta o GEARBOX_IN_OUT_MM wzdluz +X.
"""

from math import sqrt

# --- Pomiar z cad/SCARA.step (v1) ---
V1_J1_INPUT_XY = (101.0, -72.5)    # os silnika J1 / wejscie przekladni
V1_SHOULDER_XY = (201.0, -72.5)    # os barku (lozysko MH-P16)
V1_ELBOW_XY = (353.6, 2.4)         # os lokcia
V1_TOOL_XY = (439.75, -120.35)     # os efektora (6810ZZ)
V1_ROD_PLANE_X = 40.0              # plaszczyzna dwoch walkow 8 mm
V1_HOUSING_BOTTOM_Z = 207.1        # spod housing-bottom przekladni J1
GEARBOX_IN_OUT_MM = 100.0          # wejscie -> wyjscie przekladni J1
HOUSING_HALF_WIDTH = 34.0          # polowa szerokosci obudowy przekladni

# --- Prowadnice ---
ROD_D = 12.0                       # srednica walkow (h6, hartowane)
ROD_TRIANGLE_SIDE = 140.0          # bok trojkata rownobocznego
ROD_R = ROD_TRIANGLE_SIDE / sqrt(3.0)
ROD_XY = [
    (-ROD_R, 0.0),                               # tylny (wierzcholek)
    (ROD_R / 2.0, ROD_TRIANGLE_SIDE / 2.0),      # przedni lewy
    (ROD_R / 2.0, -ROD_TRIANGLE_SIDE / 2.0),     # przedni prawy
]
BUSHING_OD, BUSHING_L = 21.0, 30.0              # LM12UU
TOWER_OD = 34.0                                  # obudowa pary tulei
CARRIAGE_H = 140.0                               # wysokosc wieży tulei
BUSHING_SPACING = CARRIAGE_H - BUSHING_L         # rozstaw srodkow tulei (110)

# --- Naped Z: jedna sruba T8 miedzy silnikiem J1 a tylnym walkiem,
#     silnik Z na dole obok, przeniesienie paskiem GT2 pod dolna plyta ---
SCREW_D = 8.0
SCREW_XY = (-48.0, 0.0)
SCREW_ALT_XY = [(15.0, 50.0), (15.0, -50.0)]   # opcja: dwie sruby po bokach obudowy
Z_MOTOR_XY = (-100.0, -62.0)

# --- Zakres Z ---
Z_TRAVEL = 200.0

# --- Rama 2020 ---
PROFILE = 20.0
FRAME_X = (-150.0, 70.0)          # tyl / przod (zewnetrzne krawedzie)
FRAME_Y = 120.0                   # polowa szerokosci (zewnetrzna)
BASE_FRONT_X = 190.0              # wysuniecie podstawy do przodu
PLATE_T = 8.0                     # plyty Al: dolna i gorna
ROD_CLAMP_H = 24.0                # oprawa walka (dlugi otwor, zacisk)

# --- Wozek (lokalne z = 0 na spodzie housing-bottom przekladni J1) ---
CARRIAGE_LOW_PLATE_T = 10.0
TOWER_Z0 = -CARRIAGE_LOW_PLATE_T - 2.0   # spod wiezy tulei
TOWER_Z1 = TOWER_Z0 + CARRIAGE_H

# Wysokosc wozka (lokalne z = 0) w najnizszym polozeniu nad stolem.
CARRIAGE_Z_MIN = PROFILE + PLATE_T + ROD_CLAMP_H + 4.0 - TOWER_Z0
ROD_FREE_LENGTH = Z_TRAVEL + CARRIAGE_H + 8.0
ROD_LENGTH = ROD_FREE_LENGTH + 2 * ROD_CLAMP_H
TOP_PLATE_Z = PROFILE + PLATE_T + ROD_FREE_LENGTH + 2 * ROD_CLAMP_H
FRAME_H = TOP_PLATE_Z + PLATE_T + PROFILE      # gorna rama 2020 nad plyta
