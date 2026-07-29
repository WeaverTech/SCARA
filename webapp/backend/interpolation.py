"""Interpolacja liniowa trasy TCP w plaszczyznie XY.

Trasa dzielona jest na segmenty o dlugosci <= SEGMENT_MM. Kazdy segment jest
walidowany (zasieg, strefa wykluczenia, limity stawow) PRZED wykonaniem ruchu,
wiec nieosiagalna trasa jest odrzucana w calosci.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

from . import kinematics_mm as kin

SEGMENT_MM = 2.0


@dataclass
class Segment:
    x: float
    y: float
    z: Optional[float]
    j1: float
    j2: float


class PathError(ValueError):
    """Trasa liniowa niewykonalna; code = kod bledu firmware-style."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def linear_path(
    x0: float, y0: float, x1: float, y1: float,
    z0: Optional[float] = None, z1: Optional[float] = None,
    elbow_up: bool = True, segment_mm: float = SEGMENT_MM,
) -> List[Segment]:
    """Dzieli prosta (x0,y0)->(x1,y1) na segmenty z gotowym IK.

    Rzuca PathError, gdy ktorykolwiek punkt posredni jest nieosiagalny.
    Z (jesli podane) interpolowane liniowo razem z XY.
    """
    dist = math.hypot(x1 - x0, y1 - y0)
    n = max(1, math.ceil(dist / segment_mm))
    segments: List[Segment] = []
    for i in range(1, n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        err = kin.validate_point(x, y, elbow_up)
        if err is not None:
            raise PathError(
                err,
                f"trasa liniowa nieosiagalna w punkcie ({x:.1f}, {y:.1f}): {err}",
            )
        j1, j2 = kin.inverse(x, y, elbow_up)  # type: ignore[misc]
        z = None
        if z0 is not None and z1 is not None:
            z = z0 + (z1 - z0) * t
        elif z1 is not None:
            z = z1
        segments.append(Segment(x=x, y=y, z=z, j1=j1, j2=j2))
    return segments
