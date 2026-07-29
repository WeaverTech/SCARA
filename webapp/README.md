# SCARA Web Control

Lokalna aplikacja webowa do sterowania robotem SCARA w stylu teach-pendant
(RC+): jog, pamiec punktow, budowanie i wykonywanie programow, wizualizacja 2D.

Polaczenie z robotem jest **przewodowe** - backend dziala na komputerze
podlaczonym kablem USB do Arduino Mega, a GUI otwierasz w przegladarce pod
`http://localhost:8000`. Wymaga firmware **SCARA-FW 2.1** (`../src/main/`).

## Uruchomienie

```bash
cd webapp
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Nastepnie otworz [http://localhost:8000](http://localhost:8000), wybierz port
(np. `/dev/ttyACM0` lub `COM3`) i kliknij **Polacz**.

> **Praca bez sprzetu:** wybierz port `sim` - wbudowany symulator odpowiada
> identycznym protokolem co firmware i animuje ruch osi w czasie rzeczywistym.

## Funkcje

- **Jog** osiowy (J1/J2/Z/TOOL, wzgledny - dziala tez przed homingiem)
  i kartezjanski (XY przez IK), wybor kroku, konfiguracja lokcia up/down.
- **Homing reczny** (praca bez krancowek): dojedz jogiem do pozycji
  krancowych (J1 = -125 st., J2 = -145 st., Z = 0) i kliknij "SET HOME" -
  biezaca pozycja staje sie pozycja odniesienia (komenda `SETHOME`,
  takze per-os). Uwaga: jog przed homingiem nie ma limitow programowych.
- **Predkosc globalna** 10-100% (suwak, komenda `SPEED`).
- **Gripper** (serwo SG90): otworz/zamknij (komenda `GRIP`).
- **Pamiec punktow**: Teach z biezacej pozycji, Go/Go-liniowy, punkty widoczne
  na wizualizacji; zapis w `data/points.json`.
- **Programy**: lista krokow (ruch joint/liniowy do punktu, Z, TOOL, gripper,
  czekaj) + liczba powtorzen; Run/Pauza/Wznow/Stop z podswietlaniem kroku;
  zapis w `data/programs.json`.
- **Interpolacja liniowa**: trasa TCP dzielona na segmenty 2 mm, cala trasa
  walidowana przed startem (zasieg, limity stawow, strefa kolizji kolumny).
- **Wizualizacja 2D** na zywo: ramie, obszar roboczy, strefa wykluczenia,
  punkty, slad TCP (polling STATUS ~10 Hz przez WebSocket).
- **Bezpieczenstwo**: STOP (rampa) i E-STOP (odciecie sterownikow, wymagany
  ponowny HOME) zawsze widoczne; blokada ruchow przed homingiem.
- **Konsola**: podglad surowej komunikacji + reczne komendy.

## Architektura

```
przegladarka (frontend/)  --HTTP/WS-->  FastAPI (backend/)  --USB-->  Arduino
```

| Modul | Rola |
| --- | --- |
| `backend/main.py` | REST API + WebSocket + serwowanie frontendu |
| `backend/robot_manager.py` | watki: reader / poller STATUS / runner programow |
| `backend/transport.py` | port szeregowy (pyserial) + symulator protokolu |
| `backend/interpolation.py` | segmentacja trasy liniowej + walidacja |
| `backend/kinematics_mm.py` | FK/IK w mm, zgodne 1:1 z firmware |
| `backend/storage.py` | punkty i programy w JSON (`data/`) |
| `frontend/` | GUI: HTML + vanilla JS + canvas |

## Testy

```bash
python3 -m pytest tests/ -q
```

Testy pokrywaja: FK/IK, interpolacje (segmentacja, odrzucanie tras
nieosiagalnych), storage, symulator protokolu oraz pelny cykl programu
(move -> grip -> move liniowy -> grip -> wait) na symulatorze.
