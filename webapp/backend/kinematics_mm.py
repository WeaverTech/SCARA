"""Kinematyka SCARA w milimetrach - zgodna 1:1 z firmware (src/main/config.h).

Uzywana przez backend do walidacji tras i interpolacji liniowej.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

ARM_L1_MM = 139.928
ARM_L2_MM = 140.000
Z_AXIS_OFFSET_MM = 165.0
MAX_REACH_MM = 279.928
MIN_REACH_MM = 0.072
Z_COL_EXCLUSION_R = 45.0

J1_MIN_DEG, J1_MAX_DEG = -125.0, 125.0
J2_MIN_DEG, J2_MAX_DEG = -145.0, 145.0
Z_MIN_MM, Z_MAX_MM = 0.0, 150.0
TOOL_MIN_DEG, TOOL_MAX_DEG = -180.0, 180.0


def forward(j1_deg: float, j2_deg: float) -> Tuple[float, float]:
    """Kinematyka prosta: katy [deg] -> (x, y) [mm] w ukladzie barku."""
    t1 = math.radians(j1_deg)
    t12 = math.radians(j1_deg + j2_deg)
    x = ARM_L1_MM * math.cos(t1) + ARM_L2_MM * math.cos(t12)
    y = ARM_L1_MM * math.sin(t1) + ARM_L2_MM * math.sin(t12)
    return x, y


def inverse(x: float, y: float, elbow_up: bool = True) -> Optional[Tuple[float, float]]:
    """Kinematyka odwrotna: (x, y) [mm] -> (j1, j2) [deg] albo None poza zasiegiem."""
    r2 = x * x + y * y
    r = math.sqrt(r2)
    if r > MAX_REACH_MM + 0.001 or r < MIN_REACH_MM - 0.001:
        return None
    cos_t2 = (r2 - ARM_L1_MM**2 - ARM_L2_MM**2) / (2.0 * ARM_L1_MM * ARM_L2_MM)
    cos_t2 = max(-1.0, min(1.0, cos_t2))
    t2 = math.acos(cos_t2)
    if not elbow_up:
        t2 = -t2
    t1 = math.atan2(y, x) - math.atan2(
        ARM_L2_MM * math.sin(t2), ARM_L1_MM + ARM_L2_MM * math.cos(t2)
    )
    return math.degrees(t1), math.degrees(t2)


def in_column_exclusion(x: float, y: float) -> bool:
    """Czy punkt lezy w strefie kolizji z kolumna Z (kolumna w (-165, 0))."""
    dx = x + Z_AXIS_OFFSET_MM
    return (dx * dx + y * y) < Z_COL_EXCLUSION_R**2


def joints_within_limits(j1_deg: float, j2_deg: float) -> bool:
    return (J1_MIN_DEG <= j1_deg <= J1_MAX_DEG
            and J2_MIN_DEG <= j2_deg <= J2_MAX_DEG)


def validate_point(x: float, y: float, elbow_up: bool = True) -> Optional[str]:
    """Zwraca None gdy punkt jest osiagalny, inaczej kod bledu."""
    if in_column_exclusion(x, y):
        return "EXCLUSION_ZONE"
    ik = inverse(x, y, elbow_up)
    if ik is None:
        return "OUT_OF_REACH"
    if not joints_within_limits(*ik):
        return "JOINT_LIMIT"
    return None
