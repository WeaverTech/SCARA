# Host Python dla SCARA

Klient `scara_client.py` komunikuje sie z firmware Arduino Mega
(`../src/main/main.ino`) przez port szeregowy (115200 baud).

## Instalacja

```bash
pip install -r requirements.txt
```

## Protokol

Kazda komenda dostaje jedna linie odpowiedzi `OK[ dane]` lub `ERR KOD opis`.
Po zakonczeniu ruchu kontroler wysyla asynchronicznie `DONE`.
Po resecie kontroler wysyla `READY SCARA-FW 2.0`.

| Komenda | Odpowiedz | Opis |
| --- | --- | --- |
| `PING` | `OK PONG` | test lacza |
| `VERSION` | `OK SCARA-FW 2.0` | wersja firmware |
| `STATUS` | `OK STATE=.. HOMED=.. X=.. Y=.. Z=.. J1=.. J2=.. TOOL=..` | pelny stan |
| `HOME [J1\|J2\|Z]` | `OK` / `ERR HOMING_FAIL ...` | homing (bez argumentu: Z, J1, J2) |
| `MOVE X<mm> Y<mm> [Z<mm>] [T<deg>] [E0\|E1]` | `OK J1=.. J2=..` + pozniej `DONE` | ruch IK (E1 = lokiec "up") |
| `JOG J1\|J2\|Z\|TOOL <wartosc>` | `OK` + pozniej `DONE` | ruch pojedynczej osi |
| `IK X<mm> Y<mm> [E0\|E1]` | `OK J1=.. J2=.. REACHABLE=0\|1` | samo IK, bez ruchu |
| `STOP` | `OK` | stop z rampa |
| `ESTOP` | `OK` | stop natychmiastowy + DISABLE (wymaga HOME) |
| `ENABLE` / `DISABLE` | `OK` | sterowniki TB6600 |

Kody bledow: `BAD_CMD`, `NOT_HOMED`, `OUT_OF_REACH`, `EXCLUSION_ZONE`,
`JOINT_LIMIT`, `BUSY`, `LIMIT_HIT`, `HOMING_FAIL`, `AXIS_DISABLED`.

## Przyklad

```python
from scara_client import ScaraClient

with ScaraClient("/dev/ttyACM0") as robot:
    robot.home()                              # Z -> J1 -> J2
    robot.move(x=200.0, y=50.0, z=20.0)       # IK + ruch, czeka na DONE
    print(robot.status())
    print(robot.solve_ik(150.0, 100.0))       # samo IK w firmware
```
