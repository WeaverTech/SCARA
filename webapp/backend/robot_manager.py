"""Menedzer robota: polaczenie, kolejkowanie komend, polling stanu,
wykonywanie programow (run/pause/stop) i emisja zdarzen do GUI.

Watki:
  - reader: czyta linie z transportu, rozdziela odpowiedzi / DONE / logi,
  - poller: cyklicznie pyta STATUS (~10 Hz) i emituje stan do GUI,
  - runner: wykonuje program krok po kroku (osobny watek na czas RUN).

Zdarzenia (callback on_event, wolany z watkow roboczych):
  {"type": "status", "data": {...}}
  {"type": "log", "direction": "tx"|"rx", "line": "..."}
  {"type": "connection", "connected": bool, "port": str|None}
  {"type": "program", "state": "running"|"paused"|"finished"|"stopped"|"error",
   "program": str, "step": int|None, "cycle": int, "detail": str|None}
"""

from __future__ import annotations

import queue
import time
from threading import Event, Lock, Thread
from typing import Callable, Dict, Optional

from . import kinematics_mm as kin
from .interpolation import PathError, linear_path
from .models import Point, Program
from .storage import Storage
from .transport import open_transport

STATUS_POLL_INTERVAL = 0.1
DEFAULT_CMD_TIMEOUT = 5.0
HOME_TIMEOUT = 180.0
MOTION_TIMEOUT = 300.0


class RobotError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class RobotManager:
    def __init__(self, storage: Storage,
                 on_event: Optional[Callable[[dict], None]] = None) -> None:
        self._storage = storage
        self._on_event = on_event or (lambda event: None)

        self._transport = None
        self._port: Optional[str] = None
        self._cmd_lock = Lock()          # jedna komenda na raz
        self._reply_queue: "queue.Queue[str]" = queue.Queue()
        self._done_event = Event()
        self._moving = False
        self._alive = Event()

        self._reader_thread: Optional[Thread] = None
        self._poller_thread: Optional[Thread] = None

        self._status: Dict = {}
        self._status_lock = Lock()

        self._runner_thread: Optional[Thread] = None
        self._run_stop = Event()
        self._run_pause = Event()

    # ------------------------------------------------------------ zdarzenia
    def set_event_handler(self, handler: Callable[[dict], None]) -> None:
        self._on_event = handler

    def _emit(self, event: dict) -> None:
        try:
            self._on_event(event)
        except Exception:
            pass

    # ---------------------------------------------------------- polaczenie
    @property
    def connected(self) -> bool:
        return self._transport is not None

    @property
    def port(self) -> Optional[str]:
        return self._port

    def connect(self, port: str) -> None:
        if self.connected:
            raise RobotError("ALREADY_CONNECTED", f"polaczono z {self._port}")
        self._transport = open_transport(port)
        self._port = port
        self._alive.set()
        self._reply_queue = queue.Queue()
        self._done_event.clear()
        self._moving = False

        self._reader_thread = Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()
        self._poller_thread = Thread(target=self._poller_loop, daemon=True)
        self._poller_thread.start()

        # Poczekaj na READY (reset Arduino przy otwarciu portu) lub sprawdz PING.
        deadline = time.monotonic() + 4.0
        while time.monotonic() < deadline:
            with self._status_lock:
                if self._status:
                    break
            time.sleep(0.1)
        try:
            self.command("PING", timeout=3.0)
        except (RobotError, TimeoutError):
            self.disconnect()
            raise RobotError("NO_RESPONSE", "brak odpowiedzi z kontrolera")
        self._emit({"type": "connection", "connected": True, "port": port})

    def disconnect(self) -> None:
        self.stop_program()
        self._alive.clear()
        transport = self._transport
        self._transport = None
        self._port = None
        if self._reader_thread is not None:
            self._reader_thread.join(timeout=1.0)
            self._reader_thread = None
        if self._poller_thread is not None:
            self._poller_thread.join(timeout=1.0)
            self._poller_thread = None
        if transport is not None:
            try:
                transport.close()
            except Exception:
                pass
        with self._status_lock:
            self._status = {}
        self._emit({"type": "connection", "connected": False, "port": None})

    # --------------------------------------------------------------- watki
    def _reader_loop(self) -> None:
        while self._alive.is_set():
            transport = self._transport
            if transport is None:
                return
            try:
                line = transport.read_line(timeout=0.1)
            except Exception:
                if self._alive.is_set():
                    self._alive.clear()
                    self._emit({"type": "connection", "connected": False,
                                "port": None, "detail": "utracono polaczenie"})
                return
            if not line:
                continue
            self._emit({"type": "log", "direction": "rx", "line": line})
            if line == "DONE":
                self._moving = False
                self._done_event.set()
            elif line.startswith("READY"):
                with self._status_lock:
                    self._status = {"fw": line}
            elif line.startswith(("OK", "ERR")):
                self._reply_queue.put(line)
            # inne linie (np. ERR LIMIT_HIT async) - tylko do logu:
            if line.startswith("ERR LIMIT_HIT"):
                self._moving = False
                self._done_event.set()
                self._emit({"type": "alarm", "detail": line})

    def _poller_loop(self) -> None:
        while self._alive.is_set():
            time.sleep(STATUS_POLL_INTERVAL)
            if not self._alive.is_set() or self._transport is None:
                return
            # Nie wchodz w droge trwajacej komendzie (np. HOME).
            if not self._cmd_lock.acquire(blocking=False):
                continue
            try:
                reply = self._send_and_wait("STATUS", timeout=2.0)
            except (RobotError, TimeoutError):
                continue
            finally:
                self._cmd_lock.release()
            status = self._parse_status(reply)
            with self._status_lock:
                self._status = status
            self._emit({"type": "status", "data": status})

    # -------------------------------------------------------------- komendy
    def _send_and_wait(self, cmd: str, timeout: float) -> str:
        """Wysyla komende, zwraca tresc odpowiedzi OK. Wolac pod _cmd_lock."""
        if self._transport is None:
            raise RobotError("NOT_CONNECTED", "brak polaczenia z robotem")
        # Oproznij ewentualne stare odpowiedzi.
        while not self._reply_queue.empty():
            try:
                self._reply_queue.get_nowait()
            except queue.Empty:
                break
        self._emit({"type": "log", "direction": "tx", "line": cmd})
        self._transport.write_line(cmd)
        try:
            line = self._reply_queue.get(timeout=timeout)
        except queue.Empty:
            raise TimeoutError(f"brak odpowiedzi na komende: {cmd!r}")
        if line.startswith("OK"):
            return line[2:].strip()
        parts = line.split(" ", 2)
        raise RobotError(parts[1] if len(parts) > 1 else "UNKNOWN",
                         parts[2] if len(parts) > 2 else "")

    def command(self, cmd: str, timeout: float = DEFAULT_CMD_TIMEOUT) -> str:
        with self._cmd_lock:
            return self._send_and_wait(cmd, timeout)

    def motion_command(self, cmd: str, timeout: float = DEFAULT_CMD_TIMEOUT) -> str:
        """Komenda rozpoczynajaca ruch: po OK ustawia flage moving."""
        with self._cmd_lock:
            self._done_event.clear()
            reply = self._send_and_wait(cmd, timeout)
            self._moving = True
            return reply

    def wait_done(self, timeout: float = MOTION_TIMEOUT) -> None:
        if not self._moving:
            return
        if not self._done_event.wait(timeout):
            raise TimeoutError("ruch nie zakonczyl sie w zadanym czasie")

    # --------------------------------------------------------------- status
    @staticmethod
    def _parse_status(reply: str) -> Dict:
        fields: Dict[str, str] = {}
        for token in reply.split():
            key, _, value = token.partition("=")
            fields[key] = value
        try:
            return {
                "state": fields["STATE"],
                "homed": fields["HOMED"] == "1",
                "x": float(fields["X"]),
                "y": float(fields["Y"]),
                "z": float(fields["Z"]),
                "j1": float(fields["J1"]),
                "j2": float(fields["J2"]),
                "tool": float(fields["TOOL"]),
                "speed": int(fields.get("SPEED", "100")),
                "grip": fields.get("GRIP", "0") == "1",
            }
        except (KeyError, ValueError):
            return {"raw": reply}

    def status(self) -> Dict:
        with self._status_lock:
            return dict(self._status)

    # ------------------------------------------------------------ operacje
    def home(self, axis: Optional[str] = None) -> None:
        cmd = "HOME" if not axis else f"HOME {axis}"
        self.command(cmd, timeout=HOME_TIMEOUT)

    def jog(self, axis: str, value: float, wait: bool = False) -> None:
        self.motion_command(f"JOG {axis} {value:.3f}")
        if wait:
            self.wait_done()

    def jog_relative(self, axis: str, delta: float, wait: bool = False) -> None:
        """Jog wzgledny - dziala takze przed homingiem (homing reczny)."""
        self.motion_command(f"JOGR {axis} {delta:.3f}")
        if wait:
            self.wait_done()

    def set_home(self, axis: Optional[str] = None,
                 value: Optional[float] = None) -> None:
        """Homing reczny: biezaca pozycja = pozycja krancowa (lub podana)."""
        cmd = "SETHOME"
        if axis:
            cmd += f" {axis}"
            if value is not None:
                cmd += f" {value:.3f}"
        self.command(cmd)

    def set_speed(self, percent: int) -> None:
        self.command(f"SPEED {percent}")

    def set_grip(self, closed: bool) -> None:
        self.command(f"GRIP {1 if closed else 0}")

    def move_joint(self, x: float, y: float, z: Optional[float] = None,
                   tool: Optional[float] = None, elbow_up: bool = True,
                   wait: bool = False) -> Dict[str, float]:
        cmd = f"MOVE X{x:.3f} Y{y:.3f}"
        if z is not None:
            cmd += f" Z{z:.3f}"
        if tool is not None:
            cmd += f" T{tool:.3f}"
        cmd += f" E{1 if elbow_up else 0}"
        reply = self.motion_command(cmd)
        joints = {k.lower(): float(v) for k, _, v in
                  (t.partition("=") for t in reply.split())}
        if wait:
            self.wait_done()
        return joints

    def move_linear(self, x: float, y: float, z: Optional[float] = None,
                    tool: Optional[float] = None, elbow_up: bool = True,
                    stop_event: Optional[Event] = None,
                    pause_event: Optional[Event] = None) -> None:
        """Ruch liniowy TCP: walidacja calej trasy, potem segmenty MOVE."""
        current = self._parse_status(self.command("STATUS"))
        if "x" not in current:
            raise RobotError("NO_STATUS", "brak aktualnej pozycji robota")
        x0, y0, z0 = current["x"], current["y"], current["z"]
        try:
            segments = linear_path(x0, y0, x, y, z0=z0, z1=z,
                                   elbow_up=elbow_up)
        except PathError as exc:
            raise RobotError(exc.code, str(exc))
        for i, seg in enumerate(segments):
            if stop_event is not None and stop_event.is_set():
                return
            if pause_event is not None:
                while pause_event.is_set():
                    if stop_event is not None and stop_event.is_set():
                        return
                    time.sleep(0.05)
            cmd = f"MOVE X{seg.x:.3f} Y{seg.y:.3f}"
            if seg.z is not None:
                cmd += f" Z{seg.z:.3f}"
            if tool is not None and i == len(segments) - 1:
                cmd += f" T{tool:.3f}"
            cmd += f" E{1 if elbow_up else 0}"
            self.motion_command(cmd)
            self.wait_done()

    def stop_motion(self) -> None:
        self.command("STOP")

    def estop(self) -> None:
        self.stop_program()
        self.command("ESTOP")

    # ------------------------------------------------------------- programy
    @property
    def program_running(self) -> bool:
        return self._runner_thread is not None and self._runner_thread.is_alive()

    def run_program(self, program: Program) -> None:
        if not self.connected:
            raise RobotError("NOT_CONNECTED", "brak polaczenia z robotem")
        if self.program_running:
            raise RobotError("PROGRAM_RUNNING", "program juz dziala")
        # Swiezy STATUS (cache moglby byc sprzed homingu).
        status = self._parse_status(self.command("STATUS"))
        with self._status_lock:
            self._status = status
        if not status.get("homed"):
            raise RobotError("NOT_HOMED", "wykonaj HOME przed startem programu")
        self._run_stop.clear()
        self._run_pause.clear()
        self._runner_thread = Thread(
            target=self._runner_loop, args=(program,), daemon=True)
        self._runner_thread.start()

    def pause_program(self) -> None:
        if self.program_running:
            self._run_pause.set()

    def resume_program(self) -> None:
        self._run_pause.clear()

    def stop_program(self) -> None:
        if self.program_running:
            self._run_stop.set()
            self._run_pause.clear()
            self._runner_thread.join(timeout=5.0)

    def _runner_loop(self, program: Program) -> None:
        name = program.name
        try:
            for cycle in range(1, program.repeat + 1):
                for index, step in enumerate(program.steps):
                    if self._run_stop.is_set():
                        self._emit({"type": "program", "state": "stopped",
                                    "program": name, "step": index,
                                    "cycle": cycle, "detail": None})
                        return
                    while self._run_pause.is_set():
                        self._emit({"type": "program", "state": "paused",
                                    "program": name, "step": index,
                                    "cycle": cycle, "detail": None})
                        if self._run_stop.is_set():
                            return
                        time.sleep(0.1)
                    self._emit({"type": "program", "state": "running",
                                "program": name, "step": index,
                                "cycle": cycle, "detail": None})
                    self._execute_step(step)
            self._emit({"type": "program", "state": "finished",
                        "program": name, "step": None,
                        "cycle": program.repeat, "detail": None})
        except (RobotError, TimeoutError) as exc:
            self._emit({"type": "program", "state": "error", "program": name,
                        "step": None, "cycle": 0, "detail": str(exc)})

    def _resolve_point(self, name: Optional[str]) -> Point:
        if not name:
            raise RobotError("BAD_PROGRAM", "krok ruchu bez nazwy punktu")
        point = self._storage.get_point(name)
        if point is None:
            raise RobotError("NO_POINT", f"punkt '{name}' nie istnieje")
        return point

    def _execute_step(self, step) -> None:
        if step.type == "move_joint":
            p = self._resolve_point(step.point)
            self.move_joint(p.x, p.y, z=p.z, tool=p.tool,
                            elbow_up=p.elbow_up, wait=True)
        elif step.type == "move_linear":
            p = self._resolve_point(step.point)
            self.move_linear(p.x, p.y, z=p.z, tool=p.tool, elbow_up=p.elbow_up,
                             stop_event=self._run_stop,
                             pause_event=self._run_pause)
        elif step.type == "move_z":
            if step.value is None:
                raise RobotError("BAD_PROGRAM", "krok move_z bez wartosci")
            self.jog("Z", step.value, wait=True)
        elif step.type == "tool":
            if step.value is None:
                raise RobotError("BAD_PROGRAM", "krok tool bez wartosci")
            self.jog("TOOL", step.value, wait=True)
        elif step.type == "grip":
            self.set_grip(bool(step.value))
            time.sleep(0.4)  # czas na domkniecie serwa SG90
        elif step.type == "wait":
            duration = float(step.value or 0.0)
            end = time.monotonic() + duration
            while time.monotonic() < end:
                if self._run_stop.is_set():
                    return
                time.sleep(0.05)
        else:
            raise RobotError("BAD_PROGRAM", f"nieznany typ kroku: {step.type}")
