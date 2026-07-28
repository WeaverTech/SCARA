"""Trwaly zapis punktow i programow w plikach JSON (webapp/data/)."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional

from .models import Point, Program

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class Storage:
    def __init__(self, data_dir: Path = DEFAULT_DATA_DIR) -> None:
        self._dir = Path(data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._points_file = self._dir / "points.json"
        self._programs_file = self._dir / "programs.json"
        self._lock = Lock()
        self._points: Dict[str, Point] = {}
        self._programs: Dict[str, Program] = {}
        self._load()

    # ------------------------------------------------------------------ IO
    def _load(self) -> None:
        if self._points_file.exists():
            data = json.loads(self._points_file.read_text(encoding="utf-8"))
            self._points = {p["name"]: Point(**p) for p in data}
        if self._programs_file.exists():
            data = json.loads(self._programs_file.read_text(encoding="utf-8"))
            self._programs = {p["name"]: Program(**p) for p in data}

    def _save_points(self) -> None:
        payload = [p.model_dump() for p in self._points.values()]
        self._points_file.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _save_programs(self) -> None:
        payload = [p.model_dump() for p in self._programs.values()]
        self._programs_file.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # -------------------------------------------------------------- punkty
    def list_points(self) -> List[Point]:
        with self._lock:
            return list(self._points.values())

    def get_point(self, name: str) -> Optional[Point]:
        with self._lock:
            return self._points.get(name)

    def save_point(self, point: Point) -> None:
        with self._lock:
            self._points[point.name] = point
            self._save_points()

    def delete_point(self, name: str) -> bool:
        with self._lock:
            if name not in self._points:
                return False
            del self._points[name]
            self._save_points()
            return True

    # ------------------------------------------------------------ programy
    def list_programs(self) -> List[Program]:
        with self._lock:
            return list(self._programs.values())

    def get_program(self, name: str) -> Optional[Program]:
        with self._lock:
            return self._programs.get(name)

    def save_program(self, program: Program) -> None:
        with self._lock:
            self._programs[program.name] = program
            self._save_programs()

    def delete_program(self, name: str) -> bool:
        with self._lock:
            if name not in self._programs:
                return False
            del self._programs[name]
            self._save_programs()
            return True
