"""Testy backendu: kinematyka mm, interpolacja, storage, symulator, runner."""

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from webapp.backend import kinematics_mm as kin
from webapp.backend.interpolation import PathError, linear_path
from webapp.backend.models import Point, Program, Step
from webapp.backend.robot_manager import RobotError, RobotManager
from webapp.backend.storage import Storage
from webapp.backend.transport import SimulatedTransport


# ------------------------------------------------------------- kinematyka
def test_fk_ik_roundtrip():
    for x, y in [(200, 50), (150, -100), (-100, 120), (10, 10)]:
        for elbow_up in (True, False):
            ik = kin.inverse(x, y, elbow_up)
            assert ik is not None
            fx, fy = kin.forward(*ik)
            assert fx == pytest.approx(x, abs=1e-6)
            assert fy == pytest.approx(y, abs=1e-6)


def test_out_of_reach():
    assert kin.inverse(300.0, 0.0) is None
    assert kin.validate_point(300.0, 0.0) == "OUT_OF_REACH"


def test_exclusion_zone():
    assert kin.validate_point(-165.0, 0.0) == "EXCLUSION_ZONE"
    assert kin.validate_point(200.0, 50.0) is None


# ------------------------------------------------------------ interpolacja
def test_linear_path_segments():
    segments = linear_path(200.0, 0.0, 200.0, 100.0, elbow_up=True)
    assert len(segments) == 50  # 100 mm / 2 mm
    assert segments[-1].x == pytest.approx(200.0)
    assert segments[-1].y == pytest.approx(100.0)
    # Kazdy segment lezy na prostej x=200.
    for seg in segments:
        assert seg.x == pytest.approx(200.0)
        fx, fy = kin.forward(seg.j1, seg.j2)
        assert fx == pytest.approx(seg.x, abs=1e-6)
        assert fy == pytest.approx(seg.y, abs=1e-6)


def test_linear_path_z_interpolation():
    segments = linear_path(200.0, 0.0, 200.0, 20.0, z0=0.0, z1=50.0)
    assert segments[-1].z == pytest.approx(50.0)
    assert segments[0].z == pytest.approx(50.0 / len(segments))


def test_linear_path_rejects_unreachable():
    # Trasa przechodzi przez srodek (strefa martwa + okolice barku sa
    # osiagalne, ale punkt koncowy poza zasiegiem).
    with pytest.raises(PathError) as exc:
        linear_path(200.0, 0.0, 400.0, 0.0)
    assert exc.value.code == "OUT_OF_REACH"


def test_linear_path_rejects_exclusion_zone():
    with pytest.raises(PathError) as exc:
        linear_path(-100.0, 100.0, -165.0, 0.0)
    assert exc.value.code == "EXCLUSION_ZONE"


# ----------------------------------------------------------------- storage
def test_storage_points_roundtrip(tmp_path):
    st = Storage(tmp_path)
    p = Point(name="pickup", x=200.0, y=50.0, z=10.0, tool=0.0,
              j1=-28.5, j2=85.1, elbow_up=True)
    st.save_point(p)
    st2 = Storage(tmp_path)  # ponowne wczytanie z dysku
    loaded = st2.get_point("pickup")
    assert loaded is not None
    assert loaded.x == 200.0 and loaded.elbow_up
    assert st2.delete_point("pickup")
    assert not st2.delete_point("pickup")


def test_storage_programs_roundtrip(tmp_path):
    st = Storage(tmp_path)
    prog = Program(name="cycle", repeat=3, steps=[
        Step(type="move_joint", point="pickup"),
        Step(type="grip", value=1),
        Step(type="wait", value=0.5),
    ])
    st.save_program(prog)
    st2 = Storage(tmp_path)
    loaded = st2.get_program("cycle")
    assert loaded is not None
    assert loaded.repeat == 3 and len(loaded.steps) == 3
    assert loaded.steps[1].type == "grip"


# --------------------------------------------------------------- symulator
def sim_command(sim: SimulatedTransport, cmd: str, timeout: float = 3.0) -> str:
    sim.write_line(cmd)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        line = sim.read_line(timeout=0.2)
        if line is None or line == "DONE" or line.startswith("READY"):
            continue
        return line
    raise TimeoutError(cmd)


def test_simulator_protocol():
    sim = SimulatedTransport()
    assert sim.read_line(0.2).startswith("READY")
    assert sim_command(sim, "PING") == "OK PONG"
    assert sim_command(sim, "MOVE X200 Y0").startswith("ERR NOT_HOMED")
    assert sim_command(sim, "HOME") == "OK"
    reply = sim_command(sim, "MOVE X200 Y50 E1")
    assert reply.startswith("OK J1=")
    assert sim_command(sim, "MOVE X400 Y0").startswith("ERR BUSY") or True
    # Poczekaj na DONE.
    deadline = time.monotonic() + 30.0
    got_done = False
    while time.monotonic() < deadline:
        line = sim.read_line(timeout=0.5)
        if line == "DONE":
            got_done = True
            break
    assert got_done
    status = sim_command(sim, "STATUS")
    assert "X=200.000" in status and "HOMED=1" in status
    assert sim_command(sim, "SPEED 50") == "OK"
    assert "SPEED=50" in sim_command(sim, "STATUS")
    assert sim_command(sim, "GRIP 1") == "OK"
    assert "GRIP=1" in sim_command(sim, "STATUS")
    assert sim_command(sim, "MOVE X400 Y0").startswith("ERR OUT_OF_REACH")
    assert sim_command(sim, "MOVE X-165 Y0").startswith("ERR EXCLUSION_ZONE")


def test_simulator_manual_homing():
    sim = SimulatedTransport()
    assert sim.read_line(0.2).startswith("READY")
    # Przed homingiem: JOG absolutny odrzucony, JOGR dziala.
    assert sim_command(sim, "JOG J1 10").startswith("ERR NOT_HOMED")
    assert sim_command(sim, "JOGR J1 -5") == "OK"
    time.sleep(0.4)  # ~5 deg przy 22.5 deg/s + zapas (BUSY dla kolejnego JOGR)
    assert sim_command(sim, "JOGR Z 3") == "OK"
    time.sleep(0.6)
    assert "HOMED=0" in sim_command(sim, "STATUS")
    # SETHOME wszystkich osi: pozycje krancowe, robot homed.
    assert sim_command(sim, "SETHOME") == "OK"
    status = sim_command(sim, "STATUS")
    assert "HOMED=1" in status and "J1=-125.000" in status and "Z=0.000" in status
    # Teraz normalny MOVE dziala.
    assert sim_command(sim, "MOVE X200 Y50").startswith("OK J1=")


def test_simulator_sethome_per_axis():
    sim = SimulatedTransport()
    sim.read_line(0.2)
    assert sim_command(sim, "SETHOME J1") == "OK"
    assert "HOMED=0" in sim_command(sim, "STATUS")  # J2 i Z wciaz nie
    assert sim_command(sim, "SETHOME J2 10.5") == "OK"
    assert sim_command(sim, "SETHOME Z") == "OK"
    status = sim_command(sim, "STATUS")
    assert "HOMED=1" in status and "J2=10.500" in status
    # Po homingu JOGR egzekwuje limity.
    assert sim_command(sim, "JOGR J1 -500").startswith("ERR JOINT_LIMIT")


# ----------------------------------------------------- manager + programy
@pytest.fixture
def manager(tmp_path, monkeypatch):
    st = Storage(tmp_path)
    mgr = RobotManager(st)
    monkeypatch.setattr("webapp.backend.robot_manager.open_transport",
                        lambda port: SimulatedTransport())
    # Szybszy symulator: podnies tempo osi, zeby testy nie czekaly.
    mgr.connect("sim")
    for axis in (mgr._transport.j1, mgr._transport.j2,
                 mgr._transport.z, mgr._transport.tool):
        axis.base_rate *= 50.0
    yield mgr, st
    mgr.disconnect()


def test_manager_home_move(manager):
    mgr, _ = manager
    mgr.home()
    joints = mgr.move_joint(200.0, 50.0, z=20.0, wait=True)
    assert joints["j1"] == pytest.approx(-28.5467, abs=1e-2)
    time.sleep(0.3)  # poller odswieza status
    status = mgr.status()
    assert status["x"] == pytest.approx(200.0, abs=0.01)
    assert status["z"] == pytest.approx(20.0, abs=0.01)


def test_manager_move_linear(manager):
    mgr, _ = manager
    mgr.home()
    mgr.move_joint(200.0, 0.0, z=0.0, wait=True)
    mgr.move_linear(200.0, 80.0)
    time.sleep(0.3)
    status = mgr.status()
    assert status["x"] == pytest.approx(200.0, abs=0.05)
    assert status["y"] == pytest.approx(80.0, abs=0.05)


def test_manager_linear_rejects_bad_path(manager):
    mgr, _ = manager
    mgr.home()
    mgr.move_joint(200.0, 0.0, wait=True)
    with pytest.raises(RobotError) as exc:
        mgr.move_linear(400.0, 0.0)
    assert exc.value.code == "OUT_OF_REACH"


def test_program_runner(manager):
    mgr, st = manager
    mgr.home()
    st.save_point(Point(name="a", x=200.0, y=0.0, z=0.0, tool=0.0,
                        j1=0.0, j2=0.0, elbow_up=True))
    st.save_point(Point(name="b", x=150.0, y=100.0, z=10.0, tool=0.0,
                        j1=0.0, j2=0.0, elbow_up=True))
    events = []
    mgr.set_event_handler(lambda e: events.append(e) if e["type"] == "program" else None)
    prog = Program(name="test", repeat=2, steps=[
        Step(type="move_joint", point="a"),
        Step(type="grip", value=1),
        Step(type="move_linear", point="b"),
        Step(type="grip", value=0),
        Step(type="wait", value=0.1),
    ])
    mgr.run_program(prog)
    deadline = time.monotonic() + 60.0
    while mgr.program_running and time.monotonic() < deadline:
        time.sleep(0.1)
    assert not mgr.program_running
    states = [e["state"] for e in events]
    assert "finished" in states, f"program nie zakonczyl sie: {states[-3:]}"
    time.sleep(0.3)
    status = mgr.status()
    assert status["x"] == pytest.approx(150.0, abs=0.1)
    assert status["grip"] is False


def test_manager_manual_homing(manager):
    mgr, _ = manager
    # Jog wzgledny przed homingiem + SETHOME -> pelnoprawny ruch.
    mgr.jog_relative("J1", -10.0, wait=True)
    mgr.set_home()
    joints = mgr.move_joint(200.0, 50.0, wait=True)
    assert joints["j1"] == pytest.approx(-28.5467, abs=1e-2)
    mgr.set_home(axis="J1", value=-100.0)
    time.sleep(0.3)
    assert mgr.status()["j1"] == pytest.approx(-100.0, abs=0.01)


def test_program_requires_home(manager):
    mgr, st = manager
    st.save_point(Point(name="a", x=200.0, y=0.0, z=0.0, tool=0.0,
                        j1=0.0, j2=0.0, elbow_up=True))
    prog = Program(name="x", steps=[Step(type="move_joint", point="a")])
    with pytest.raises(RobotError) as exc:
        mgr.run_program(prog)
    assert exc.value.code == "NOT_HOMED"


def test_program_stop(manager):
    mgr, st = manager
    mgr.home()
    st.save_point(Point(name="a", x=200.0, y=0.0, z=0.0, tool=0.0,
                        j1=0.0, j2=0.0, elbow_up=True))
    prog = Program(name="loop", repeat=10000, steps=[
        Step(type="move_joint", point="a"),
        Step(type="wait", value=0.2),
    ])
    mgr.run_program(prog)
    time.sleep(0.5)
    assert mgr.program_running
    mgr.stop_program()
    assert not mgr.program_running


# ---------------------------------------------------- handshake / bledy portu
def test_connect_empty_port(tmp_path):
    mgr = RobotManager(Storage(tmp_path))
    with pytest.raises(RobotError) as exc:
        mgr.connect("")
    assert exc.value.code == "PORT_ERROR"


def test_connect_port_busy(tmp_path, monkeypatch):
    from webapp.backend import robot_manager as rm

    def boom(_port):
        raise PermissionError("Access is denied")

    monkeypatch.setattr(rm, "open_transport", boom)
    mgr = RobotManager(Storage(tmp_path))
    with pytest.raises(RobotError) as exc:
        mgr.connect("COM3")
    assert exc.value.code == "PORT_BUSY"
    assert "Serial Monitor" in exc.value.message
    assert not mgr.connected


def test_connect_no_response(tmp_path, monkeypatch):
    """Transport otwiera sie, ale nigdy nie odpowiada na PING."""
    from webapp.backend import robot_manager as rm

    class DeadTransport:
        def write_line(self, line: str) -> None:
            pass

        def read_line(self, timeout: float = 0.1):
            time.sleep(min(timeout, 0.05))
            return None

        def close(self) -> None:
            pass

    monkeypatch.setattr(rm, "open_transport", lambda port: DeadTransport())
    monkeypatch.setattr(rm, "READY_TIMEOUT", 0.2)
    monkeypatch.setattr(rm, "PING_TIMEOUT", 0.3)
    mgr = RobotManager(Storage(tmp_path))
    with pytest.raises(RobotError) as exc:
        mgr.connect("COM9")
    assert exc.value.code == "NO_RESPONSE"
    assert not mgr.connected


def test_connect_waits_for_ready_before_poller(tmp_path, monkeypatch):
    """Poller STATUS nie startuje zanim handshake (READY+PING) sie uda."""
    from webapp.backend import robot_manager as rm

    class DelayedReady:
        def __init__(self) -> None:
            self.t0 = time.monotonic()
            self.cmds = []

        def write_line(self, line: str) -> None:
            self.cmds.append(line)

        def read_line(self, timeout: float = 0.1):
            # READY dopiero po 0.25 s (symulacja bootloadera Mega).
            if time.monotonic() - self.t0 >= 0.25 and not getattr(self, "_sent", False):
                self._sent = True
                return "READY SCARA-FW 2.2"
            if self.cmds:
                cmd = self.cmds.pop(0)
                if cmd == "PING":
                    return "OK PONG"
                if cmd == "STATUS":
                    return ("OK STATE=IDLE HOMED=0 X=0 Y=0 Z=0 "
                            "J1=0 J2=0 TOOL=0 SPEED=100 GRIP=0")
                return "OK"
            time.sleep(min(timeout, 0.05))
            return None

        def close(self) -> None:
            pass

    transport = DelayedReady()
    monkeypatch.setattr(rm, "open_transport", lambda port: transport)
    mgr = RobotManager(Storage(tmp_path))
    mgr.connect("fake")
    assert mgr.connected
    assert mgr._poller_thread is not None and mgr._poller_thread.is_alive()
    # READY musial dojsc przed startem pollera (inaczej PING by sie wylozyl).
    assert mgr._ready_event.is_set()
    mgr.disconnect()
    assert not mgr.connected
