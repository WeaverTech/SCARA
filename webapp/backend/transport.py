"""Warstwa transportu: prawdziwy port szeregowy oraz symulator robota.

Obie klasy maja identyczny interfejs liniowy (write_line/read_line), a symulator
odpowiada dokladnie tym samym protokolem co firmware (OK/ERR/DONE/READY),
wiec cala reszta backendu nie widzi roznicy.
"""

from __future__ import annotations

import time
from collections import deque
from threading import Lock
from typing import Deque, List, Optional

from . import kinematics_mm as kin

SIM_PORT_NAME = "sim"


class SerialTransport:
    """Transport przez pyserial (prawdziwy robot, polaczenie przewodowe USB)."""

    def __init__(self, port: str, baud: int = 115200) -> None:
        import serial  # import lokalny - symulator nie wymaga pyserial

        # write_timeout: na Windows zajety COM potrafi zawiesic write() bez limitu.
        # exclusive: unikaj cichego wspoldzielenia portu z Serial Monitor / IDE.
        kwargs = dict(port=port, baudrate=baud, timeout=0.1, write_timeout=2.0)
        try:
            self._serial = serial.Serial(**kwargs, exclusive=True)
        except TypeError:
            self._serial = serial.Serial(**kwargs)
        # Otwarcie portu resetuje Arduino (DTR) - wyczyść smieci z bootloadera.
        time.sleep(0.05)
        try:
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
        except Exception:
            pass

    def write_line(self, line: str) -> None:
        self._serial.write((line + "\n").encode("ascii"))
        self._serial.flush()

    def read_line(self, timeout: float = 0.1) -> Optional[str]:
        # Nie przypisuj self._serial.timeout przy kazdym odczycie: na Windows
        # kazde przypisanie wywoluje rekonfiguracje portu (SetCommState),
        # a czesc sterownikow USB-serial porzuca wtedy dane czekajace w
        # buforze RX - odpowiedzi z Arduino ginely losowo (NO_RESPONSE/504).
        if self._serial.timeout != timeout:
            self._serial.timeout = timeout
        raw = self._serial.readline()
        if not raw:
            return None
        return raw.decode("ascii", errors="replace").strip() or None

    def close(self) -> None:
        self._serial.close()


class _SimAxis:
    """Jedna os symulatora: ruch liniowy w czasie od start do celu."""

    def __init__(self, rate_per_s: float) -> None:
        self.base_rate = rate_per_s   # deg/s albo mm/s przy 100%
        self.start = 0.0
        self.target = 0.0
        self.t0 = 0.0
        self.duration = 0.0

    def position(self, now: float) -> float:
        if self.duration <= 0.0 or now >= self.t0 + self.duration:
            return self.target
        frac = (now - self.t0) / self.duration
        return self.start + (self.target - self.start) * frac

    def moving(self, now: float) -> bool:
        return now < self.t0 + self.duration

    def move_to(self, value: float, now: float, speed_pct: int) -> None:
        self.start = self.position(now)
        self.target = value
        self.t0 = now
        rate = self.base_rate * speed_pct / 100.0
        self.duration = abs(value - self.start) / rate if rate > 0 else 0.0

    def jump_to(self, value: float) -> None:
        self.start = self.target = value
        self.duration = 0.0


class SimulatedTransport:
    """Symulator firmware SCARA-FW 2.2 na poziomie protokolu liniowego."""

    def __init__(self) -> None:
        self._out: Deque[str] = deque(["READY SCARA-FW 2.2 (SIM)"])
        self._lock = Lock()
        # Bazowe tempo osi przy 100% (zgodne z config.h: kroki/s / przelicznik).
        self.j1 = _SimAxis(4000.0 / 177.7778)   # ~22.5 deg/s
        self.j2 = _SimAxis(4000.0 / 124.4444)   # ~32.1 deg/s
        self.z = _SimAxis(3000.0 / 400.0)       # 7.5 mm/s
        self.tool = _SimAxis(1200.0 / 8.8889)   # ~135 deg/s
        self.homed_j1 = False
        self.homed_j2 = False
        self.homed_z = False
        self.grip_closed = False
        self.speed_pct = 100
        self._done_pending = False

    @property
    def homed(self) -> bool:
        return self.homed_j1 and self.homed_j2 and self.homed_z

    @homed.setter
    def homed(self, value: bool) -> None:
        self.homed_j1 = self.homed_j2 = self.homed_z = value

    # ------------------------------------------------------------ interfejs
    def write_line(self, line: str) -> None:
        with self._lock:
            self._process(line.strip().upper())

    def read_line(self, timeout: float = 0.1) -> Optional[str]:
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                if self._out:
                    return self._out.popleft()
                if self._done_pending and not self._any_moving():
                    self._done_pending = False
                    return "DONE"
            if time.monotonic() >= deadline:
                return None
            time.sleep(0.01)

    def close(self) -> None:
        pass

    # ------------------------------------------------------------- protokol
    def _any_moving(self) -> bool:
        now = time.monotonic()
        return any(a.moving(now) for a in (self.j1, self.j2, self.z, self.tool))

    def _reply(self, line: str) -> None:
        self._out.append(line)

    def _err(self, code: str, msg: str) -> None:
        self._reply(f"ERR {code} {msg}")

    def _parse_param(self, args: str, key: str) -> Optional[float]:
        for token in args.split():
            if token.startswith(key):
                try:
                    return float(token[len(key):])
                except ValueError:
                    return None
        return None

    def _process(self, cmd: str) -> None:
        now = time.monotonic()
        busy = self._any_moving()
        head = cmd.split(" ", 1)[0]
        if busy and head not in ("STOP", "ESTOP", "STATUS", "PING", "SPEED", "GRIP"):
            self._err("BUSY", "ruch w toku - uzyj STOP lub poczekaj na DONE")
            return

        if cmd == "PING":
            self._reply("OK PONG")
        elif cmd == "VERSION":
            self._reply("OK SCARA-FW 2.2 (SIM)")
        elif cmd == "STATUS":
            self._status(now)
        elif cmd == "SETHOME" or cmd.startswith("SETHOME "):
            self._sethome(cmd[7:].strip())
        elif cmd == "HOME" or cmd.startswith("HOME "):
            self._home(cmd[4:].strip())
        elif cmd.startswith("MOVE "):
            self._move(cmd[5:], now)
        elif cmd.startswith("JOGR "):
            self._jog_relative(cmd[5:], now)
        elif cmd.startswith("JOG "):
            self._jog(cmd[4:], now)
        elif cmd.startswith("IK "):
            self._ik(cmd[3:])
        elif cmd.startswith("SPEED "):
            self._speed(cmd[6:])
        elif cmd.startswith("GRIP "):
            self._grip(cmd[5:])
        elif cmd == "STOP":
            self._stop(now)
            self._reply("OK")
        elif cmd == "ESTOP":
            self._stop(now)
            self.homed = False
            self._reply("OK")
        elif cmd in ("ENABLE",):
            self._reply("OK")
        elif cmd == "DISABLE":
            self.homed = False
            self._reply("OK")
        else:
            self._err("BAD_CMD", "nieznana komenda")

    def _status(self, now: float) -> None:
        j1 = self.j1.position(now)
        j2 = self.j2.position(now)
        x, y = kin.forward(j1, j2)
        state = "MOVING" if self._any_moving() else "IDLE"
        self._reply(
            f"OK STATE={state} HOMED={1 if self.homed else 0} "
            f"X={x:.3f} Y={y:.3f} Z={self.z.position(now):.3f} "
            f"J1={j1:.3f} J2={j2:.3f} TOOL={self.tool.position(now):.3f} "
            f"SPEED={self.speed_pct} GRIP={1 if self.grip_closed else 0}"
        )

    def _home(self, axis: str) -> None:
        # Homing w firmware jest blokujacy; w symulatorze krotkie opoznienie.
        if axis not in ("", "J1", "J2", "Z"):
            self._err("BAD_CMD", "uzycie: HOME [J1|J2|Z]")
            return
        time.sleep(0.3)
        if axis in ("", "Z"):
            self.z.jump_to(kin.Z_MIN_MM)
            self.homed_z = True
        if axis in ("", "J1"):
            self.j1.jump_to(kin.J1_MIN_DEG)
            self.homed_j1 = True
        if axis in ("", "J2"):
            self.j2.jump_to(kin.J2_MIN_DEG)
            self.homed_j2 = True
        self._reply("OK")

    def _sethome(self, args: str) -> None:
        parts = args.split()
        axis = parts[0] if parts else ""
        value: Optional[float] = None
        if len(parts) > 1:
            try:
                value = float(parts[1])
            except ValueError:
                self._err("BAD_CMD", "niepoprawna wartosc")
                return
        if axis == "":
            self.j1.jump_to(kin.J1_MIN_DEG)
            self.j2.jump_to(kin.J2_MIN_DEG)
            self.z.jump_to(kin.Z_MIN_MM)
            self.tool.jump_to(0.0)
            self.homed = True
        elif axis == "J1":
            self.j1.jump_to(kin.J1_MIN_DEG if value is None else value)
            self.homed_j1 = True
        elif axis == "J2":
            self.j2.jump_to(kin.J2_MIN_DEG if value is None else value)
            self.homed_j2 = True
        elif axis == "Z":
            self.z.jump_to(kin.Z_MIN_MM if value is None else value)
            self.homed_z = True
        elif axis == "TOOL":
            self.tool.jump_to(0.0 if value is None else value)
        else:
            self._err("BAD_CMD", "uzycie: SETHOME [J1|J2|Z|TOOL] [wartosc]")
            return
        self._reply("OK")

    def _jog_relative(self, args: str, now: float) -> None:
        parts = args.split()
        if len(parts) != 2:
            self._err("BAD_CMD", "uzycie: JOGR J1|J2|Z|TOOL <delta>")
            return
        axis_name, raw = parts
        try:
            delta = float(raw)
        except ValueError:
            self._err("BAD_CMD", "niepoprawna wartosc")
            return
        table = {
            "J1": (kin.J1_MIN_DEG, kin.J1_MAX_DEG, self.j1, self.homed_j1),
            "J2": (kin.J2_MIN_DEG, kin.J2_MAX_DEG, self.j2, self.homed_j2),
            "Z": (kin.Z_MIN_MM, kin.Z_MAX_MM, self.z, self.homed_z),
            "TOOL": (kin.TOOL_MIN_DEG, kin.TOOL_MAX_DEG, self.tool, True),
        }
        if axis_name not in table:
            self._err("BAD_CMD", "nieznana os (J1|J2|Z|TOOL)")
            return
        lo, hi, sim_axis, axis_homed = table[axis_name]
        target = sim_axis.position(now) + delta
        if axis_homed and not (lo <= target <= hi):
            self._err("JOINT_LIMIT", "cel poza zakresem osi")
            return
        sim_axis.move_to(target, now, self.speed_pct)
        self._done_pending = True
        self._reply("OK")

    def _move(self, args: str, now: float) -> None:
        if not self.homed:
            self._err("NOT_HOMED", "wykonaj HOME przed ruchem")
            return
        x = self._parse_param(args, "X")
        y = self._parse_param(args, "Y")
        z = self._parse_param(args, "Z")
        tool = self._parse_param(args, "T")
        elbow = self._parse_param(args, "E")
        if x is None or y is None:
            self._err("BAD_CMD", "uzycie: MOVE X<mm> Y<mm> [Z<mm>] [T<deg>] [E0|E1]")
            return
        if kin.in_column_exclusion(x, y):
            self._err("EXCLUSION_ZONE", "punkt w strefie kolizji z kolumna Z")
            return
        ik = kin.inverse(x, y, elbow is None or elbow >= 0.5)
        if ik is None:
            self._err("OUT_OF_REACH", "punkt poza zasiegiem ramienia")
            return
        j1, j2 = ik
        if not kin.joints_within_limits(j1, j2):
            self._err("JOINT_LIMIT", "rozwiazanie IK poza limitami stawow")
            return
        if z is not None and not (kin.Z_MIN_MM <= z <= kin.Z_MAX_MM):
            self._err("JOINT_LIMIT", "Z poza zakresem")
            return
        self.j1.move_to(j1, now, self.speed_pct)
        self.j2.move_to(j2, now, self.speed_pct)
        if z is not None:
            self.z.move_to(z, now, self.speed_pct)
        if tool is not None:
            self.tool.move_to(tool, now, self.speed_pct)
        self._done_pending = True
        self._reply(f"OK J1={j1:.3f} J2={j2:.3f}")

    def _jog(self, args: str, now: float) -> None:
        if not self.homed:
            self._err("NOT_HOMED", "wykonaj HOME przed ruchem")
            return
        parts = args.split()
        if len(parts) != 2:
            self._err("BAD_CMD", "uzycie: JOG J1|J2|Z|TOOL <wartosc>")
            return
        axis, raw = parts
        try:
            value = float(raw)
        except ValueError:
            self._err("BAD_CMD", "niepoprawna wartosc")
            return
        limits = {
            "J1": (kin.J1_MIN_DEG, kin.J1_MAX_DEG, self.j1),
            "J2": (kin.J2_MIN_DEG, kin.J2_MAX_DEG, self.j2),
            "Z": (kin.Z_MIN_MM, kin.Z_MAX_MM, self.z),
            "TOOL": (kin.TOOL_MIN_DEG, kin.TOOL_MAX_DEG, self.tool),
        }
        if axis not in limits:
            self._err("BAD_CMD", "nieznana os (J1|J2|Z|TOOL)")
            return
        lo, hi, sim_axis = limits[axis]
        if not (lo <= value <= hi):
            self._err("JOINT_LIMIT", f"{axis} poza zakresem")
            return
        sim_axis.move_to(value, now, self.speed_pct)
        self._done_pending = True
        self._reply("OK")

    def _ik(self, args: str) -> None:
        x = self._parse_param(args, "X")
        y = self._parse_param(args, "Y")
        elbow = self._parse_param(args, "E")
        if x is None or y is None:
            self._err("BAD_CMD", "uzycie: IK X<mm> Y<mm> [E0|E1]")
            return
        ik = kin.inverse(x, y, elbow is None or elbow >= 0.5)
        if ik is None:
            self._err("OUT_OF_REACH", "punkt poza zasiegiem ramienia")
            return
        j1, j2 = ik
        reachable = int(kin.joints_within_limits(j1, j2)
                        and not kin.in_column_exclusion(x, y))
        self._reply(f"OK J1={j1:.4f} J2={j2:.4f} REACHABLE={reachable}")

    def _speed(self, args: str) -> None:
        try:
            pct = int(args)
        except ValueError:
            pct = -1
        if not 10 <= pct <= 100:
            self._err("BAD_CMD", "uzycie: SPEED <10-100>")
            return
        self.speed_pct = pct
        self._reply("OK")

    def _grip(self, args: str) -> None:
        if args == "0":
            self.grip_closed = False
        elif args == "1":
            self.grip_closed = True
        else:
            self._err("BAD_CMD", "uzycie: GRIP 0|1")
            return
        self._reply("OK")

    def _stop(self, now: float) -> None:
        for axis in (self.j1, self.j2, self.z, self.tool):
            axis.jump_to(axis.position(now))
        self._done_pending = False


def list_serial_ports() -> List[dict]:
    """Lista dostepnych portow szeregowych + wirtualny port symulatora."""
    ports = [{"device": SIM_PORT_NAME, "description": "Symulator robota (bez sprzetu)"}]
    try:
        from serial.tools import list_ports

        for p in list_ports.comports():
            ports.append({"device": p.device, "description": p.description})
    except ImportError:
        pass
    return ports


def open_transport(port: str):
    if not port or not str(port).strip():
        raise ValueError("nie wybrano portu szeregowego")
    if port == SIM_PORT_NAME:
        return SimulatedTransport()
    return SerialTransport(port)
