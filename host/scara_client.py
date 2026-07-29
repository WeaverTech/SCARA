"""Klient Pythona dla firmware SCARA (Arduino Mega, protokol OK/ERR/DONE).

Protokol (115200 baud, linie '\n'):
  - kazda komenda dostaje jedna linie odpowiedzi: "OK[ dane]" albo "ERR KOD opis",
  - po zakonczeniu ruchu kontroler wysyla asynchronicznie linie "DONE",
  - po resecie kontroler wysyla "READY SCARA-FW x.y".

Przyklad:
    from scara_client import ScaraClient

    with ScaraClient("/dev/ttyACM0") as robot:
        robot.home()
        robot.move(x=200.0, y=50.0, z=20.0, wait=True)
        print(robot.status())

Wymaga: pyserial (pip install pyserial).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional

import serial


class ScaraError(RuntimeError):
    """Blad zgloszony przez firmware (linia 'ERR KOD opis')."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass
class ScaraStatus:
    state: str      # IDLE | MOVING | HOMING
    homed: bool
    x: float        # mm
    y: float        # mm
    z: float        # mm
    j1: float       # deg
    j2: float       # deg
    tool: float     # deg


class ScaraClient:
    def __init__(self, port: str, baud: int = 115200, timeout: float = 2.0) -> None:
        self._serial = serial.Serial(port, baud, timeout=timeout)
        # Arduino resetuje sie przy otwarciu portu - czekamy na "READY".
        self._wait_for_ready(timeout=5.0)

    # ------------------------------------------------------------- context
    def __enter__(self) -> "ScaraClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        self._serial.close()

    # ------------------------------------------------------------ low-level
    def _wait_for_ready(self, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            line = self._read_line()
            if line and line.startswith("READY"):
                return
        # Kontroler mogl byc juz uruchomiony (brak resetu) - sprawdz PING.
        self._serial.reset_input_buffer()
        self.ping()

    def _read_line(self) -> str:
        return self._serial.readline().decode("ascii", errors="replace").strip()

    def _command(self, cmd: str, move_timeout: Optional[float] = None) -> str:
        """Wysyla komende i zwraca tresc odpowiedzi OK (bez prefiksu).

        Linie "DONE" przychodzace asynchronicznie (z poprzednich ruchow)
        sa pomijane. Rzuca ScaraError przy odpowiedzi ERR.
        """
        self._serial.write((cmd + "\n").encode("ascii"))
        deadline = time.monotonic() + (move_timeout or self._serial.timeout or 2.0)
        while time.monotonic() < deadline:
            line = self._read_line()
            if not line or line == "DONE" or line.startswith("READY"):
                continue
            if line.startswith("OK"):
                return line[2:].strip()
            if line.startswith("ERR"):
                parts = line.split(" ", 2)
                code = parts[1] if len(parts) > 1 else "UNKNOWN"
                message = parts[2] if len(parts) > 2 else ""
                raise ScaraError(code, message)
        raise TimeoutError(f"brak odpowiedzi na komende: {cmd!r}")

    def wait_done(self, timeout: float = 120.0) -> None:
        """Czeka na asynchroniczna linie DONE (koniec ruchu)."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            line = self._read_line()
            if line == "DONE":
                return
            if line.startswith("ERR"):
                parts = line.split(" ", 2)
                raise ScaraError(parts[1] if len(parts) > 1 else "UNKNOWN",
                                 parts[2] if len(parts) > 2 else "")
        raise TimeoutError("ruch nie zakonczyl sie w zadanym czasie")

    # ------------------------------------------------------------- komendy
    def ping(self) -> None:
        reply = self._command("PING")
        if reply != "PONG":
            raise ScaraError("BAD_REPLY", f"nieoczekiwana odpowiedz: {reply!r}")

    def version(self) -> str:
        return self._command("VERSION")

    def status(self) -> ScaraStatus:
        fields: Dict[str, str] = {}
        for token in self._command("STATUS").split():
            key, _, value = token.partition("=")
            fields[key] = value
        return ScaraStatus(
            state=fields["STATE"],
            homed=fields["HOMED"] == "1",
            x=float(fields["X"]),
            y=float(fields["Y"]),
            z=float(fields["Z"]),
            j1=float(fields["J1"]),
            j2=float(fields["J2"]),
            tool=float(fields["TOOL"]),
        )

    def home(self, axis: Optional[str] = None, timeout: float = 180.0) -> None:
        """Homing wszystkich osi (Z -> J1 -> J2) albo jednej ('J1'|'J2'|'Z')."""
        cmd = "HOME" if axis is None else f"HOME {axis.upper()}"
        self._command(cmd, move_timeout=timeout)

    def move(
        self,
        x: float,
        y: float,
        z: Optional[float] = None,
        tool: Optional[float] = None,
        elbow_up: bool = True,
        wait: bool = True,
        timeout: float = 120.0,
    ) -> Dict[str, float]:
        """Ruch IK do punktu (mm, stopnie). Zwraca rozwiazane katy J1/J2."""
        cmd = f"MOVE X{x:.3f} Y{y:.3f}"
        if z is not None:
            cmd += f" Z{z:.3f}"
        if tool is not None:
            cmd += f" T{tool:.3f}"
        cmd += f" E{1 if elbow_up else 0}"
        reply = self._command(cmd)
        joints = {
            key.lower(): float(value)
            for key, _, value in (tok.partition("=") for tok in reply.split())
        }
        if wait:
            self.wait_done(timeout=timeout)
        return joints

    def jog(self, axis: str, value: float, wait: bool = True,
            timeout: float = 120.0) -> None:
        """Ruch pojedynczej osi: J1/J2/TOOL w stopniach, Z w mm."""
        self._command(f"JOG {axis.upper()} {value:.3f}")
        if wait:
            self.wait_done(timeout=timeout)

    def jog_relative(self, axis: str, delta: float, wait: bool = True,
                     timeout: float = 120.0) -> None:
        """Jog wzgledny - dziala takze przed homingiem (homing reczny)."""
        self._command(f"JOGR {axis.upper()} {delta:.3f}")
        if wait:
            self.wait_done(timeout=timeout)

    def set_home(self, axis: Optional[str] = None,
                 value: Optional[float] = None) -> None:
        """Homing reczny: biezaca pozycja = pozycja krancowa z config.h.

        Bez argumentow ustawia wszystkie osie (robot musi fizycznie stac
        w pozycjach krancowych). Z argumentem - jedna os, opcjonalnie
        z podana wartoscia zamiast domyslnej krancowej.
        """
        cmd = "SETHOME"
        if axis:
            cmd += f" {axis.upper()}"
            if value is not None:
                cmd += f" {value:.3f}"
        self._command(cmd)

    def solve_ik(self, x: float, y: float, elbow_up: bool = True) -> Dict[str, float]:
        """Oblicza IK w firmware bez wykonywania ruchu."""
        reply = self._command(f"IK X{x:.3f} Y{y:.3f} E{1 if elbow_up else 0}")
        return {
            key.lower(): float(value)
            for key, _, value in (tok.partition("=") for tok in reply.split())
        }

    def set_speed(self, percent: int) -> None:
        """Globalny procent predkosci wszystkich osi (10-100)."""
        self._command(f"SPEED {int(percent)}")

    def set_grip(self, closed: bool) -> None:
        """Gripper (serwo SG90): True = zamkniety, False = otwarty."""
        self._command(f"GRIP {1 if closed else 0}")

    def stop(self) -> None:
        self._command("STOP")

    def emergency_stop(self) -> None:
        self._command("ESTOP")

    def enable(self) -> None:
        self._command("ENABLE")

    def disable(self) -> None:
        self._command("DISABLE")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Prosty test klienta SCARA")
    parser.add_argument("port", help="port szeregowy, np. /dev/ttyACM0 lub COM3")
    args = parser.parse_args()

    with ScaraClient(args.port) as robot:
        print("Firmware:", robot.version())
        print("Status:", robot.status())
