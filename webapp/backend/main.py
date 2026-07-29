"""SCARA Web Control - backend FastAPI.

Uruchomienie (z katalogu webapp/):
    uvicorn backend.main:app --host 127.0.0.1 --port 8000

GUI: http://localhost:8000
Polaczenie z robotem jest przewodowe (USB/port szeregowy) - przegladarka
rozmawia z lokalnym backendem, backend z Arduino przez pyserial.
Port "sim" uruchamia wbudowany symulator (praca bez sprzetu).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional, Set

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import kinematics_mm as kin
from .models import (ConnectRequest, GripRequest, HomeRequest,
                     JogRelativeRequest, JogRequest, MoveRequest, Point,
                     Program, RawCommandRequest, SetHomeRequest, SpeedRequest)
from .robot_manager import RobotError, RobotManager
from .storage import Storage
from .transport import list_serial_ports

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="SCARA Web Control")
storage = Storage()
manager = RobotManager(storage)

_ws_clients: Set[asyncio.Queue] = set()
_loop: Optional[asyncio.AbstractEventLoop] = None


def _broadcast(event: dict) -> None:
    """Wolane z watkow menedzera - przekazuje zdarzenie do klientow WS."""
    if _loop is None:
        return
    for q in list(_ws_clients):
        _loop.call_soon_threadsafe(q.put_nowait, event)


@app.on_event("startup")
async def _startup() -> None:
    global _loop
    _loop = asyncio.get_running_loop()
    manager.set_event_handler(_broadcast)


@app.on_event("shutdown")
async def _shutdown() -> None:
    if manager.connected:
        manager.disconnect()


def _robot_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except RobotError as exc:
        raise HTTPException(status_code=409,
                            detail={"code": exc.code, "message": exc.message})
    except TimeoutError as exc:
        raise HTTPException(status_code=504,
                            detail={"code": "TIMEOUT", "message": str(exc)})


# ------------------------------------------------------------- polaczenie
@app.get("/api/ports")
def api_ports():
    return list_serial_ports()


@app.post("/api/connect")
def api_connect(req: ConnectRequest):
    _robot_call(manager.connect, req.port)
    return {"connected": True, "port": req.port}


@app.post("/api/disconnect")
def api_disconnect():
    manager.disconnect()
    return {"connected": False}


@app.get("/api/status")
def api_status():
    return {
        "connected": manager.connected,
        "port": manager.port,
        "program_running": manager.program_running,
        "robot": manager.status(),
    }


# ------------------------------------------------------------------ ruch
@app.post("/api/home")
def api_home(req: HomeRequest):
    _robot_call(manager.home, req.axis)
    return {"ok": True}


@app.post("/api/jog")
def api_jog(req: JogRequest):
    _robot_call(manager.jog, req.axis, req.value)
    return {"ok": True}


@app.post("/api/jog_relative")
def api_jog_relative(req: JogRelativeRequest):
    _robot_call(manager.jog_relative, req.axis, req.delta)
    return {"ok": True}


@app.post("/api/sethome")
def api_sethome(req: SetHomeRequest):
    _robot_call(manager.set_home, req.axis, req.value)
    return {"ok": True}


@app.post("/api/move")
def api_move(req: MoveRequest):
    err = kin.validate_point(req.x, req.y, req.elbow_up)
    if err is not None:
        raise HTTPException(status_code=409,
                            detail={"code": err, "message": "punkt nieosiagalny"})
    if req.linear:
        if manager.program_running:
            raise HTTPException(status_code=409,
                                detail={"code": "PROGRAM_RUNNING",
                                        "message": "zatrzymaj program"})
        # Ruch liniowy jest blokujacy (sekwencja segmentow) - w tle.
        import threading
        threading.Thread(
            target=lambda: _safe_linear(req), daemon=True).start()
        return {"ok": True, "linear": True}
    joints = _robot_call(manager.move_joint, req.x, req.y, z=req.z,
                         tool=req.tool, elbow_up=req.elbow_up)
    return {"ok": True, "joints": joints}


def _safe_linear(req: MoveRequest) -> None:
    try:
        manager.move_linear(req.x, req.y, z=req.z, tool=req.tool,
                            elbow_up=req.elbow_up)
        _broadcast({"type": "linear", "state": "finished"})
    except (RobotError, TimeoutError) as exc:
        _broadcast({"type": "linear", "state": "error", "detail": str(exc)})


@app.post("/api/speed")
def api_speed(req: SpeedRequest):
    _robot_call(manager.set_speed, req.percent)
    return {"ok": True}


@app.post("/api/grip")
def api_grip(req: GripRequest):
    _robot_call(manager.set_grip, req.closed)
    return {"ok": True}


@app.post("/api/stop")
def api_stop():
    manager.stop_program()
    _robot_call(manager.stop_motion)
    return {"ok": True}


@app.post("/api/estop")
def api_estop():
    _robot_call(manager.estop)
    return {"ok": True}


@app.post("/api/command")
def api_command(req: RawCommandRequest):
    reply = _robot_call(manager.command, req.command.strip())
    return {"ok": True, "reply": reply}


@app.get("/api/ik")
def api_ik(x: float, y: float, elbow_up: bool = True):
    ik = kin.inverse(x, y, elbow_up)
    if ik is None:
        return {"reachable": False}
    j1, j2 = ik
    ok = kin.joints_within_limits(j1, j2) and not kin.in_column_exclusion(x, y)
    return {"reachable": ok, "j1": j1, "j2": j2}


# ---------------------------------------------------------------- punkty
@app.get("/api/points")
def api_points():
    return storage.list_points()


@app.post("/api/points")
def api_save_point(point: Point):
    err = kin.validate_point(point.x, point.y, point.elbow_up)
    if err is not None:
        raise HTTPException(status_code=409,
                            detail={"code": err, "message": "punkt nieosiagalny"})
    storage.save_point(point)
    _broadcast({"type": "points_changed"})
    return {"ok": True}


@app.post("/api/points/teach/{name}")
def api_teach_point(name: str):
    status = manager.status()
    if "x" not in status:
        raise HTTPException(status_code=409,
                            detail={"code": "NO_STATUS",
                                    "message": "brak pozycji robota"})
    point = Point(name=name, x=status["x"], y=status["y"], z=status["z"],
                  tool=status["tool"], j1=status["j1"], j2=status["j2"],
                  elbow_up=status["j2"] >= 0)
    storage.save_point(point)
    _broadcast({"type": "points_changed"})
    return point


@app.delete("/api/points/{name}")
def api_delete_point(name: str):
    if not storage.delete_point(name):
        raise HTTPException(status_code=404, detail="punkt nie istnieje")
    _broadcast({"type": "points_changed"})
    return {"ok": True}


@app.post("/api/points/{name}/goto")
def api_goto_point(name: str, linear: bool = False):
    point = storage.get_point(name)
    if point is None:
        raise HTTPException(status_code=404, detail="punkt nie istnieje")
    req = MoveRequest(x=point.x, y=point.y, z=point.z, tool=point.tool,
                      elbow_up=point.elbow_up, linear=linear)
    return api_move(req)


# --------------------------------------------------------------- programy
@app.get("/api/programs")
def api_programs():
    return storage.list_programs()


@app.post("/api/programs")
def api_save_program(program: Program):
    for step in program.steps:
        if step.type in ("move_joint", "move_linear"):
            if not step.point or storage.get_point(step.point) is None:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "NO_POINT",
                            "message": f"punkt '{step.point}' nie istnieje"})
    storage.save_program(program)
    _broadcast({"type": "programs_changed"})
    return {"ok": True}


@app.delete("/api/programs/{name}")
def api_delete_program(name: str):
    if not storage.delete_program(name):
        raise HTTPException(status_code=404, detail="program nie istnieje")
    _broadcast({"type": "programs_changed"})
    return {"ok": True}


@app.post("/api/programs/{name}/run")
def api_run_program(name: str):
    program = storage.get_program(name)
    if program is None:
        raise HTTPException(status_code=404, detail="program nie istnieje")
    _robot_call(manager.run_program, program)
    return {"ok": True}


@app.post("/api/programs/pause")
def api_pause_program():
    manager.pause_program()
    return {"ok": True}


@app.post("/api/programs/resume")
def api_resume_program():
    manager.resume_program()
    return {"ok": True}


@app.post("/api/programs/stop")
def api_stop_program():
    manager.stop_program()
    return {"ok": True}


# -------------------------------------------------------------- websocket
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    q: asyncio.Queue = asyncio.Queue()
    _ws_clients.add(q)
    try:
        while True:
            event = await q.get()
            await ws.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(q)


# --------------------------------------------------------------- frontend
@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
