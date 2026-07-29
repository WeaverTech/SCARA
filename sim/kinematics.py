"""Analityczna kinematyka robota SCARA (bark + lokiec + efektor + os Z).

Konwencja:
  - Uklad planarny (X, Y) ma poczatek w osi BARKU (shoulder).
  - theta1 - kat barku, theta2 - kat lokcia (wzgledny), theta_tool - kat efektora.
  - Pozycja TCP w plaszczyznie:
        x = L1*cos(t1) + L2*cos(t1+t2)
        y = L1*sin(t1) + L2*sin(t1+t2)
  - Orientacja narzedzia (absolutna): phi = t1 + t2 + theta_tool
  - Wysokosc Z pochodzi bezposrednio z osi prismatic (niezalezna od planaru).

Konwersje na kroki silnikow sa spojne ze stalymi z firmware
(src/main/config.h): mikrokrok 1/16, NEMA 17 = 200 krokow,
cykloidalna 20:1 (bark) i 14:1 (lokiec), sruba Z 400 krokow/mm.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# --- Stale napedu (zgodne z firmware src/main/config.h) ---
MOTOR_STEPS_PER_REV = 200.0
MICROSTEPS = 16.0
STEPS_PER_REV = MOTOR_STEPS_PER_REV * MICROSTEPS  # 3200

J1_GEAR_RATIO = 20.0  # przekladnia cykloidalna barku
J2_GEAR_RATIO = 14.0  # przekladnia cykloidalna lokcia
J1_STEPS_PER_DEG = (STEPS_PER_REV * J1_GEAR_RATIO) / 360.0  # 177.7778
J2_STEPS_PER_DEG = (STEPS_PER_REV * J2_GEAR_RATIO) / 360.0  # 124.4444

# Os Z - sruba napedowa.
Z_STEPS_PER_MM = 400.0

# Efektor - pasek (TODO: potwierdzic przelozenie)
TOOL_BELT_RATIO = 1.0
TOOL_STEPS_PER_DEG = (STEPS_PER_REV * TOOL_BELT_RATIO) / 360.0

# Strefa wykluczenia wokol kolumny Z (m) - kolumna w (-z_offset, 0).
Z_COL_EXCLUSION_R = 0.045


@dataclass
class JointState:
    """Stan osi robota."""

    z: float = 0.0           # m (os prismatic)
    theta1: float = 0.0      # rad (bark)
    theta2: float = 0.0      # rad (lokiec)
    theta_tool: float = 0.0  # rad (efektor, kat wzgledny)

    def as_tuple(self) -> Tuple[float, float, float, float]:
        return (self.z, self.theta1, self.theta2, self.theta_tool)


@dataclass
class Pose:
    """Pozycja TCP w ukladzie barku."""

    x: float          # m
    y: float          # m
    z: float          # m
    phi: float        # rad - absolutna orientacja narzedzia w plaszczyznie


@dataclass
class ScaraKinematics:
    """Model kinematyczny SCARA. Dlugosci w metrach, katy w radianach."""

    # Zmierzone w CAD: L1 = 139.928 mm, L2 = 140.000 mm.
    l1: float = 0.139928
    l2: float = 0.140000
    z_offset: float = 0.165
    # Limity (rad / m) - spojne z URDF.
    theta1_limits: Tuple[float, float] = (-math.pi, math.pi)
    theta2_limits: Tuple[float, float] = (-2.6180, 2.6180)
    theta_tool_limits: Tuple[float, float] = (-math.pi, math.pi)
    z_limits: Tuple[float, float] = (0.0, 0.15)

    # ------------------------------------------------------------------ FK
    def forward(self, q: JointState) -> Pose:
        """Kinematyka prosta: stan osi -> pozycja TCP."""
        t1, t2 = q.theta1, q.theta2
        x = self.l1 * math.cos(t1) + self.l2 * math.cos(t1 + t2)
        y = self.l1 * math.sin(t1) + self.l2 * math.sin(t1 + t2)
        phi = t1 + t2 + q.theta_tool
        return Pose(x=x, y=y, z=q.z, phi=phi)

    # ------------------------------------------------------------------ IK
    def inverse(
        self,
        pose: Pose,
        elbow: str = "up",
    ) -> Optional[JointState]:
        """Kinematyka odwrotna: pozycja TCP -> stan osi.

        elbow: "up" lub "down" - wybor konfiguracji lokcia.
        Zwraca None, jesli punkt jest poza zasiegiem.
        """
        x, y = pose.x, pose.y
        r2 = x * x + y * y
        r = math.sqrt(r2)

        # Zasieg ramienia.
        if r > (self.l1 + self.l2) + 1e-9 or r < abs(self.l1 - self.l2) - 1e-9:
            return None

        cos_t2 = (r2 - self.l1 ** 2 - self.l2 ** 2) / (2.0 * self.l1 * self.l2)
        cos_t2 = max(-1.0, min(1.0, cos_t2))
        t2 = math.acos(cos_t2)
        if elbow == "down":
            t2 = -t2

        t1 = math.atan2(y, x) - math.atan2(
            self.l2 * math.sin(t2), self.l1 + self.l2 * math.cos(t2)
        )

        theta_tool = pose.phi - (t1 + t2)
        theta_tool = _wrap_angle(theta_tool)

        return JointState(z=pose.z, theta1=t1, theta2=t2, theta_tool=theta_tool)

    # ------------------------------------------------------------- limity
    def within_limits(self, q: JointState) -> bool:
        return (
            _in_range(q.z, self.z_limits)
            and _in_range(q.theta1, self.theta1_limits)
            and _in_range(q.theta2, self.theta2_limits)
            and _in_range(q.theta_tool, self.theta_tool_limits)
        )

    # ------------------------------------------------ strefa wykluczenia
    def in_column_exclusion(self, x: float, y: float) -> bool:
        """Czy punkt (m) lezy w strefie kolizji z kolumna Z."""
        dx = x + self.z_offset
        return (dx * dx + y * y) < Z_COL_EXCLUSION_R ** 2

    # ---------------------------------------------------- mapowanie krokow
    @staticmethod
    def joint_to_steps(q: JointState) -> dict:
        """Mapuje stan osi na kroki silnikow (jak w firmware)."""
        return {
            "z": round(q.z * 1000.0 * Z_STEPS_PER_MM),
            "shoulder": round(math.degrees(q.theta1) * J1_STEPS_PER_DEG),
            "elbow": round(math.degrees(q.theta2) * J2_STEPS_PER_DEG),
            "tool": round(math.degrees(q.theta_tool) * TOOL_STEPS_PER_DEG),
        }


def _wrap_angle(a: float) -> float:
    """Sprowadza kat do zakresu (-pi, pi]."""
    return math.atan2(math.sin(a), math.cos(a))


def _in_range(v: float, limits: Tuple[float, float]) -> bool:
    return limits[0] - 1e-9 <= v <= limits[1] + 1e-9


def reachable_workspace(
    kin: ScaraKinematics, samples: int = 60
) -> List[Tuple[float, float]]:
    """Zwraca punkty (x, y) brzegu obszaru roboczego (do wizualizacji)."""
    pts: List[Tuple[float, float]] = []
    r_out = kin.l1 + kin.l2
    r_in = abs(kin.l1 - kin.l2)
    for i in range(samples + 1):
        a = -math.pi + 2.0 * math.pi * i / samples
        pts.append((r_out * math.cos(a), r_out * math.sin(a)))
    if r_in > 1e-6:
        for i in range(samples + 1):
            a = -math.pi + 2.0 * math.pi * i / samples
            pts.append((r_in * math.cos(a), r_in * math.sin(a)))
    return pts


if __name__ == "__main__":
    kin = ScaraKinematics()
    print("=== SCARA - parametry ===")
    print(f"L1={kin.l1} m, L2={kin.l2} m, Z_offset={kin.z_offset} m")
    print(f"J1_STEPS_PER_DEG = {J1_STEPS_PER_DEG:.4f}")
    print(f"J2_STEPS_PER_DEG = {J2_STEPS_PER_DEG:.4f}")
    print(f"Z_STEPS_PER_MM   = {Z_STEPS_PER_MM:.4f}")
    print()

    q = JointState(z=0.1, theta1=math.radians(30), theta2=math.radians(45),
                   theta_tool=math.radians(0))
    pose = kin.forward(q)
    print("FK:", q.as_tuple())
    print(f"  -> TCP x={pose.x:.4f} y={pose.y:.4f} z={pose.z:.4f} "
          f"phi={math.degrees(pose.phi):.2f} deg")

    q2 = kin.inverse(pose, elbow="up")
    print("IK (elbow up):", None if q2 is None else
          tuple(round(v, 4) for v in q2.as_tuple()))
    if q2 is not None:
        print("  kroki silnikow:", kin.joint_to_steps(q2))
