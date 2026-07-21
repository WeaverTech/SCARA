# Kinematyka i symulacja SCARA

Modul opisuje pelna kinematyke robota (model URDF), analityczna kinematyke
prosta/odwrotna oraz symulacje w PyBullet. Wszystko jest spojne ze stalymi
napedu z firmware ([`../src/main/main.ino`](../src/main/main.ino)).

## Zawartosc

| Plik | Opis |
| --- | --- |
| `scara.urdf` | Model URDF (lancuch kinematyczny, limity, geometria). |
| `kinematics.py` | Analityczna FK/IK + mapowanie katow na kroki silnikow. |
| `simulate.py` | Symulacja/wizualizacja w PyBullet (GUI lub headless). |
| `test_kinematics.py` | Testy FK/IK (round-trip, limity, kroki). |
| `requirements.txt` | Zaleznosci Pythona. |

## Model kinematyczny

SCARA z czterema osiami (wszystkie osie obrotowe sa pionowe, +Z):

```
world
  └─(fixed)        base_column        # pionowa wieza z profili 2020
      └─(Z, prismatic)  z_carriage    # podnoszenie na pasku GT2
          └─(shoulder, revolute) link1   # bark,  cykloidalna 20:1
              └─(elbow, revolute)  link2  # lokiec, cykloidalna 20:1
                  └─(tool, revolute) tool_link  # efektor (pasek)
                      └─(fixed) tool_tip         # punkt TCP
```

Parametry (zmierzone w CAD):

| Symbol | Wartosc | Opis |
| --- | ---: | --- |
| `z_offset` | 0.165 m | Kolumna -> os barku |
| `L1` | 0.139928 m | Bark -> lokiec |
| `L2` | 0.140000 m | Lokiec -> efektor |
| zakres Z | 0–0.15 m | Skok osi Z |
| strefa wykluczenia | R = 0.045 m | Wokol kolumny Z |

## Kinematyka prosta (FK)

Pozycja TCP w ukladzie osi barku:

```
x   = L1·cos(θ1) + L2·cos(θ1+θ2)
y   = L1·sin(θ1) + L2·sin(θ1+θ2)
z   = z_carriage                      (oś prismatic, niezależna)
φ   = θ1 + θ2 + θ_tool                (absolutna orientacja narzędzia)
```

## Kinematyka odwrotna (IK)

Dla zadanego (x, y, z, φ):

```
r²       = x² + y²
cos(θ2)  = (r² − L1² − L2²) / (2·L1·L2)
θ2       = ± acos(cos θ2)             (elbow "up" / "down")
θ1       = atan2(y, x) − atan2(L2·sin θ2, L1 + L2·cos θ2)
θ_tool   = φ − (θ1 + θ2)
z        = z (bezpośrednio)
```

Zwraca `None`, gdy punkt jest poza zasiegiem `|L1−L2| ≤ r ≤ L1+L2`.

## Mapowanie na kroki silnikow (spojne z firmware)

```
J1 bark   (cykloidalna 20:1): (200·16·20)/360 = 177.7778 kroków/°
J2 lokiec (cykloidalna 14:1): (200·16·14)/360 = 124.4444 kroków/°
oś Z (śruba napędowa):        400 kroków/mm
efektor (pasek):              (200·16·ratio)/360
```

## Uruchomienie

```bash
cd sim
python3 -m venv .venv && source .venv/bin/activate   # lub virtualenv
pip install -r requirements.txt

# Testy kinematyki
pytest -q

# Demo FK/IK w konsoli
python kinematics.py

# Symulacja bez okna (walidacja URDF + przejazd trajektorii)
python simulate.py --headless --demo

# Symulacja z oknem (wymaga srodowiska graficznego)
python simulate.py --demo
```

> Uwaga: `pybullet` kompiluje sie ze zrodel — na Linuksie wymaga naglowkow
> `python3-dev` oraz kompilatora `g++`/`build-essential`.

## Wykorzystanie w ROS 2 (opcjonalnie)

`scara.urdf` jest standardowym URDF, wiec dziala te z ekosystemem ROS 2:

- wizualizacja: `ros2 launch` + `robot_state_publisher` + RViz2,
- planowanie ruchu: MoveIt 2 (setup assistant wczyta URDF),
- symulacja fizyki: Gazebo (po dodaniu tagow `<gazebo>`).

## Dodanie realnych siatek (mesh) z CAD

Obecnie linki maja geometrie prymitywna (boxy/cylindry) dopasowana wymiarami.
Aby uzyc realnych ksztaltow:

1. W CAD wyeksportuj kazdy czlon do osobnego pliku **STL** (w mm).
2. Umiesc je w `sim/meshes/`.
3. W `scara.urdf` zamien `<geometry><box .../></geometry>` na
   `<geometry><mesh filename="meshes/link1.stl" scale="0.001 0.001 0.001"/></geometry>`
   (skala 0.001, bo URDF jest w metrach, a STL w mm).

## Status / TODO

- [x] Zmierzone realne L1 = 139.928 mm, L2 = 140.000 mm (CAD).
- [ ] Doprecyzowac limity stawow (z renderu widoczne adnotacje 60°/15°/25°).
- [ ] Dodac siatki STL dla lepszej wizualizacji i kolizji.
- [ ] (Opcjonalnie) pakiet ROS 2 + MoveIt 2.
