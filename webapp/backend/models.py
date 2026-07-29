"""Modele danych: punkty, programy, kroki programu."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

StepType = Literal[
    "move_joint",    # ruch typu joint do punktu (kazda os niezaleznie)
    "move_linear",   # ruch liniowy TCP do punktu (interpolacja XY+Z)
    "move_z",        # os Z do wysokosci [mm]
    "tool",          # efektor do kata [deg]
    "grip",          # gripper: value 0 = otwarty, 1 = zamkniety
    "wait",          # pauza [s]
]


class Point(BaseModel):
    name: str = Field(min_length=1, max_length=48)
    x: float
    y: float
    z: float
    tool: float = 0.0
    j1: float
    j2: float
    elbow_up: bool = True


class Step(BaseModel):
    type: StepType
    point: Optional[str] = None    # nazwa punktu (move_joint / move_linear)
    value: Optional[float] = None  # move_z: mm, tool: deg, grip: 0/1, wait: s


class Program(BaseModel):
    name: str = Field(min_length=1, max_length=48)
    steps: List[Step] = []
    repeat: int = Field(default=1, ge=1, le=10000)


class ConnectRequest(BaseModel):
    port: str


class JogRequest(BaseModel):
    axis: Literal["J1", "J2", "Z", "TOOL"]
    value: float


class MoveRequest(BaseModel):
    x: float
    y: float
    z: Optional[float] = None
    tool: Optional[float] = None
    elbow_up: bool = True
    linear: bool = False


class SpeedRequest(BaseModel):
    percent: int = Field(ge=10, le=100)


class GripRequest(BaseModel):
    closed: bool


class HomeRequest(BaseModel):
    axis: Optional[Literal["J1", "J2", "Z"]] = None


class JogRelativeRequest(BaseModel):
    axis: Literal["J1", "J2", "Z", "TOOL"]
    delta: float


class SetHomeRequest(BaseModel):
    axis: Optional[Literal["J1", "J2", "Z", "TOOL"]] = None
    value: Optional[float] = None


class RawCommandRequest(BaseModel):
    command: str = Field(min_length=1, max_length=90)
