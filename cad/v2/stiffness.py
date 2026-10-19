"""Porownanie sztywnosci wozka osi Z: v1 (2 walki) vs warianty v2 (3 walki).

Model (celowo prosty, do porownan wzglednych):
  - walki to belki Eulera-Bernoulliego, wozek sztywny, ustawiony w polowie
    wolnej dlugosci walka (najgorszy przypadek),
  - kazdy walek przenosi obciazenie przez dwie tuleje rozstawione o h,
  - konce walka: "pinned" (krotkie SHF na drukowanej plycie) albo
    "clamped" (dlugi otwor/zacisk w plycie Al),
  - tuleje nie przenosza sil osiowych, wiec moment od ciezaru ramienia liczony
    jest wzgledem miejsca, w ktorym naped Z (pasek / sruba) trzyma wozek,
  - luz tulei liczony osobno (domyslnie 10 um promieniowo).

Uruchomienie:  python3 cad/v2/stiffness.py  [--plot plik.png]
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from typing import List, Tuple

E_STEEL = 210_000.0   # MPa
G = 9.81


def _defl_pinned(P: float, a: float, x: float, L: float, EI: float) -> float:
    b = L - a
    if x <= a:
        return P * b * x * (L * L - b * b - x * x) / (6.0 * L * EI)
    return _defl_pinned(P, L - a, L - x, L, EI)


def _defl_clamped(P: float, a: float, x: float, L: float, EI: float) -> float:
    b = L - a
    if x <= a:
        return P * b * b * x * x * (3.0 * a * L - 3.0 * a * x - b * x) / (6.0 * L ** 3 * EI)
    return _defl_clamped(P, L - a, L - x, L, EI)


def rod_stiffness(d: float, L: float, h: float, ends: str) -> Tuple[float, float]:
    """Zwraca (k_tilt [N*mm/rad], k_lateral [N/mm]) jednego walka."""
    EI = E_STEEL * math.pi * d ** 4 / 64.0
    f = _defl_pinned if ends == "pinned" else _defl_clamped
    x1, x2 = L / 2.0 - h / 2.0, L / 2.0 + h / 2.0

    def defl(loads, x):
        return sum(f(P, a, x, L, EI) for P, a in loads)

    M = 1000.0
    couple = [(M / h, x1), (-M / h, x2)]
    theta = (defl(couple, x1) - defl(couple, x2)) / h
    F = 1.0
    pair = [(F / 2.0, x1), (F / 2.0, x2)]
    delta = 0.5 * (defl(pair, x1) + defl(pair, x2))
    return M / theta, F / delta


@dataclass
class Variant:
    name: str
    rods: List[Tuple[float, float]]   # polozenia walkow XY [mm]
    d: float                          # srednica walka
    L: float                          # wolna dlugosc walka
    h: float                          # rozstaw tulei w pionie
    ends: str
    drive_x: float                    # X napedu Z (pasek / sruby) [mm]
    cg_x: float                       # X srodka ciezkosci ramienia [mm]
    tip_x: float                      # X koncowki przy wyprostowanym ramieniu
    clearance: float = 0.010          # luz promieniowy tulei [mm]


def evaluate(v: Variant, arm_mass: float, payload: float, j1_torque: float) -> dict:
    k_tilt_rod, k_lat_rod = rod_stiffness(v.d, v.L, v.h, v.ends)
    n = len(v.rods)
    cx = sum(p[0] for p in v.rods) / n
    cy = sum(p[1] for p in v.rods) / n
    k_tilt = n * k_tilt_rod
    k_tors = sum(k_lat_rod * ((x - cx) ** 2 + (y - cy) ** 2) for x, y in v.rods)
    r_min = min(math.hypot(x - cx, y - cy) for x, y in v.rods)

    M = G * (arm_mass * (v.cg_x - v.drive_x) + payload * (v.tip_x - v.drive_x))
    arm = v.tip_x - cx
    theta_tilt = M / k_tilt
    theta_tors = j1_torque * 1000.0 / k_tors
    return {
        "name": v.name,
        "M_Nm": M / 1000.0,
        "k_tilt": k_tilt / 1e6,
        "k_tors": k_tors / 1e6,
        "sag_tip": theta_tilt * arm,
        "twist_tip": theta_tors * arm,
        "play_tip": (2.0 * v.clearance / v.h + v.clearance / r_min) * arm,
    }


def default_variants() -> List[Variant]:
    from params import (ROD_XY, SCREW_XY, SCREW_ALT_XY, GEARBOX_IN_OUT_MM, ROD_FREE_LENGTH,
                        BUSHING_SPACING)

    # v1: dwa walki 8 mm w plaszczyznie x=0, rozstaw 85 mm, pasek GT2 miedzy nimi.
    # Srodek ciezkosci ramienia (z masami z STEP): 227 mm przed walkami,
    # os barku 161 mm, L1 + L2 = 320 mm (zmierzone w STEP).
    reach = 170.0 + 150.0
    v1_shoulder = 161.0
    v1_cg = 227.0
    rods_v1 = [(0.0, 42.5), (0.0, -42.5)]
    v1 = Variant("v1: 2x8 mm, L=450, h=45, SHF8, pasek", rods_v1, 8, 450, 45, "pinned",
                 0.0, v1_cg, v1_shoulder + reach)

    shift = 161.0 - GEARBOX_IN_OUT_MM
    cg2 = v1_cg - shift
    tip2 = GEARBOX_IN_OUT_MM + reach
    rear_x = SCREW_XY[0]
    dual_x = SCREW_ALT_XY[0][0]
    L2, h2 = ROD_FREE_LENGTH, BUSHING_SPACING
    return [
        v1,
        Variant("v2a: 3x8 mm, L=450, h=45, SHF8 (sam trojkat)", ROD_XY, 8, 450, 45, "pinned",
                rear_x, cg2, tip2),
        Variant(f"v2b: 3x10 mm, L={L2:.0f}, h={h2:.0f}, 1 sruba", ROD_XY, 10, L2, h2,
                "clamped", rear_x, cg2, tip2),
        Variant(f"v2c: 3x12 mm, L={L2:.0f}, h={h2:.0f}, 1 sruba (rekomendowany)", ROD_XY, 12, L2,
                h2, "clamped", rear_x, cg2, tip2),
        Variant(f"v2d: 3x12 mm, L={L2:.0f}, h={h2:.0f}, 2 sruby", ROD_XY, 12, L2, h2,
                "clamped", dual_x, cg2, tip2),
        Variant(f"v2e: 3x16 mm, L={L2:.0f}, h={h2:.0f}, 1 sruba", ROD_XY, 16, L2, h2,
                "clamped", rear_x, cg2, tip2),
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm-mass", type=float, default=3.57, help="masa ramienia z silnikami [kg]")
    ap.add_argument("--payload", type=float, default=0.5, help="ladunek na koncowce [kg]")
    ap.add_argument("--j1-torque", type=float, default=1.0, help="moment reakcji J1 [N*m]")
    ap.add_argument("--plot", help="zapisz wykres porownawczy do PNG")
    args = ap.parse_args()

    rows = [evaluate(v, args.arm_mass, args.payload, args.j1_torque) for v in default_variants()]
    base = rows[0]
    print(f"Masa ramienia {args.arm_mass} kg, ladunek {args.payload} kg, "
          f"moment J1 {args.j1_torque} N*m, wozek w polowie skoku\n")
    print("| Wariant | Moment na wozku [N*m] | Sztywn. przechyl [kN*m/rad] | "
          "Sztywn. skret [kN*m/rad] | Opadanie koncowki [mm] | Skret -> koncowka [mm] | "
          "Luz tulei -> koncowka [mm] |")
    print("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for r in rows:
        print(f"| {r['name']} | {r['M_Nm']:.2f} | {r['k_tilt']:.2f} ({r['k_tilt']/base['k_tilt']:.0f}x) | "
              f"{r['k_tors']:.2f} ({r['k_tors']/base['k_tors']:.0f}x) | {r['sag_tip']:.3f} | "
              f"{r['twist_tip']:.3f} | {r['play_tip']:.3f} |")

    if args.plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        labels = [r["name"].split(":")[0] for r in rows]
        fig, ax = plt.subplots(figsize=(8, 4.2), dpi=130)
        xs = range(len(rows))
        w = 0.38
        ax.bar([x - w / 2 for x in xs], [r["sag_tip"] for r in rows], w, label="opadanie (ciezar)")
        ax.bar([x + w / 2 for x in xs], [r["twist_tip"] for r in rows], w,
               label=f"przesuniecie boczne (J1 {args.j1_torque:.0f} N*m)")
        ax.set_yscale("log")
        ax.set_xticks(list(xs), labels)
        ax.set_ylabel("ugiecie na koncowce [mm] (skala log)")
        ax.set_title("Ugiecie od podatnosci osi Z (sam wozek + walki)")
        ax.grid(axis="y", which="both", alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(args.plot)
        print(f"\nwykres: {args.plot}")


if __name__ == "__main__":
    main()
