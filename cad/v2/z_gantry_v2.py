"""Parametryczny model osi Z v2 (CadQuery) + import ramienia v1 z cad/SCARA.step.

    python3 cad/v2/z_gantry_v2.py            # eksport cad/v2/z_gantry_v2.step
    python3 cad/v2/z_gantry_v2.py --check    # tylko raport kolizji / zakresu J1

Ramie (przekladnie cykloidalne, plyty Axis1/Axis2, silniki) jest brane 1:1 z
pliku STEP v1 i przesuwane tak, by os silnika J1 wypadla w centroidzie
trojkata walkow. Elementy wieży Z z v1 (profile, walki 8 mm, wozek, Gearbox
Mount) sa pomijane i zastapione nowymi.
"""

from __future__ import annotations

import argparse
import math
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cadquery as cq

import params as P

HERE = os.path.dirname(os.path.abspath(__file__))
V1_STEP = os.path.join(HERE, "..", "SCARA.step")

ALU = (0.72, 0.74, 0.77)
ALU_DARK = (0.16, 0.16, 0.17)
STEEL = (0.80, 0.81, 0.83)
PETG = (0.12, 0.12, 0.13)
PETG_ACCENT = (0.93, 0.45, 0.10)
BRASS = (0.78, 0.62, 0.30)
RUBBER = (0.05, 0.05, 0.05)
PANEL = (0.20, 0.21, 0.23)
SMOKE = (0.25, 0.28, 0.32)


@dataclass
class Part:
    name: str
    shape: cq.Shape
    color: Tuple[float, float, float]
    group: str               # frame | guide | drive | carriage | arm | panel | cable
    opacity: float = 1.0


# ---------------------------------------------------------------------------
# Elementy pomocnicze
# ---------------------------------------------------------------------------

def _profile_2020_face() -> cq.Workplane:
    s = P.PROFILE
    sec = cq.Workplane("XY").rect(s, s).extrude(1.0)
    for ang in (0, 90, 180, 270):
        slot = (cq.Workplane("XY").center(s / 2 - 0.9, 0).rect(1.8, 6.2).extrude(1.0)
                .union(cq.Workplane("XY").center(s / 2 - 1.8 - 2.1, 0).rect(4.2, 7.4).extrude(1.0)))
        sec = sec.cut(slot.rotate((0, 0, 0), (0, 0, 1), ang))
    sec = sec.cut(cq.Workplane("XY").circle(2.1).extrude(1.0))
    return sec.faces("<Z").val()


_PROFILE_FACE = None


def profile(p0: Tuple[float, float, float], p1: Tuple[float, float, float]) -> cq.Shape:
    """Profil 2020 osiowo rownolegly, od srodka czola p0 do srodka czola p1."""
    global _PROFILE_FACE
    if _PROFILE_FACE is None:
        _PROFILE_FACE = _profile_2020_face()
    d = [b - a for a, b in zip(p0, p1)]
    length = max(abs(c) for c in d)
    solid = cq.Solid.extrudeLinear(_PROFILE_FACE, cq.Vector(0, 0, length))
    axis = max(range(3), key=lambda i: abs(d[i]))
    if axis == 0:
        solid = solid.rotate(cq.Vector(), cq.Vector(0, 1, 0), 90)
    elif axis == 1:
        solid = solid.rotate(cq.Vector(), cq.Vector(1, 0, 0), -90)
    start = [min(a, b) if i == axis else a for i, (a, b) in enumerate(zip(p0, p1))]
    return solid.translate(cq.Vector(*start))


def cyl(r: float, z0: float, z1: float, x: float = 0.0, y: float = 0.0) -> cq.Workplane:
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(r).extrude(z1 - z0)


def box(x0, x1, y0, y1, z0, z1) -> cq.Workplane:
    return (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0)
            .translate(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)))


def rounded_triangle(z0: float, z1: float, margin: float) -> cq.Workplane:
    pts = [(x, y) for x, y in P.ROD_XY]
    return (cq.Workplane("XY").workplane(offset=z0).polyline(pts).close()
            .offset2D(margin).extrude(z1 - z0))


def nema17(x: float, y: float, z_face: float, down: bool, body_len: float = 48.0) -> List[Part]:
    """Silnik NEMA17: czolo (kolnierz) na z_face, korpus w gore (down=True) lub w dol."""
    sgn = 1 if down else -1
    z_body0, z_body1 = sorted((z_face, z_face + sgn * body_len))
    body = box(x - 21.15, x + 21.15, y - 21.15, y + 21.15, z_body0 + 9, z_body1 - 9).edges("|Z").chamfer(4)
    caps = []
    for t in (z_body0, z_body1 - 9):
        caps.append(box(x - 21.2, x + 21.2, y - 21.2, y + 21.2, t, t + 9).edges("|Z").chamfer(4.2))
    z_shaft = (z_face - 24, z_face) if down else (z_face, z_face + 24)
    shaft = cyl(2.5, *z_shaft, x=x, y=y)
    boss = cyl(11, *(sorted((z_face, z_face - sgn * 2))), x=x, y=y)
    return [Part("NEMA17 Z body", body.val(), (0.08, 0.08, 0.09), "drive"),
            Part("NEMA17 Z cap A", caps[0].val(), (0.55, 0.56, 0.58), "drive"),
            Part("NEMA17 Z cap B", caps[1].val(), (0.55, 0.56, 0.58), "drive"),
            Part("NEMA17 Z shaft", shaft.val(), STEEL, "drive"),
            Part("NEMA17 Z boss", boss.val(), (0.55, 0.56, 0.58), "drive")]


# ---------------------------------------------------------------------------
# Rama, prowadnice, naped
# ---------------------------------------------------------------------------

def frame_parts() -> List[Part]:
    s = P.PROFILE
    x0, x1 = P.FRAME_X
    Y = P.FRAME_Y
    zt = P.FRAME_H
    parts: List[Part] = []
    h = s / 2

    # podstawa: dwie szyny wzdluz X wysuniete do przodu + poprzeczki
    for sy in (-1, 1):
        y = sy * (Y - h)
        parts.append(Part("base rail", profile((x0, y, h), (P.BASE_FRONT_X, y, h)), ALU_DARK, "frame"))
    for xc in (x0 + h, x1 - h, P.BASE_FRONT_X - h):
        parts.append(Part("base cross", profile((xc, -Y + s, h), (xc, Y - s, h)), ALU_DARK, "frame"))
    # slupki
    for xc in (x0 + h, x1 - h):
        for sy in (-1, 1):
            parts.append(Part("upright", profile((xc, sy * (Y - h), s), (xc, sy * (Y - h), zt - s)),
                              ALU_DARK, "frame"))
    # gorny wieniec
    for sy in (-1, 1):
        parts.append(Part("top rail", profile((x0, sy * (Y - h), zt - h), (x1, sy * (Y - h), zt - h)),
                          ALU_DARK, "frame"))
    for xc in (x0 + h, x1 - h):
        parts.append(Part("top cross", profile((xc, -Y + s, zt - h), (xc, Y - s, zt - h)),
                          ALU_DARK, "frame"))
    # tylne poprzeczki w polowie wysokosci (mocowanie prowadnika kabli)
    zm = (P.FRAME_H) / 2
    parts.append(Part("rear mid cross", profile((x0 + h, -Y + s, zm), (x0 + h, Y - s, zm)),
                      ALU_DARK, "frame"))

    # stopki
    for xc in (x0 + 15, P.BASE_FRONT_X - 15):
        for sy in (-1, 1):
            parts.append(Part("foot", cyl(9, -6, 0, xc, sy * (Y - h)).val(), RUBBER, "frame"))

    # plyty Al: dolna (na podstawie) i gorna (pod wiencem)
    def plate(z0: float, z1: float, name: str) -> Part:
        pl = box(x0, x1, -Y, Y, z0, z1)
        for xc in (x0 + h, x1 - h):
            for sy in (-1, 1):
                pl = pl.cut(box(xc - h - 0.5, xc + h + 0.5, sy * (Y - h) - h - 0.5,
                                sy * (Y - h) + h + 0.5, z0 - 1, z1 + 1))
        for x, y in P.ROD_XY:
            pl = pl.cut(cyl(P.ROD_D / 2, z0 - 1, z1 + 1, x, y))
        pl = pl.cut(cyl(11, z0 - 1, z1 + 1, *P.SCREW_XY))
        if name == "bottom plate":
            pl = pl.cut(cyl(11.5, z0 - 1, z1 + 1, *P.Z_MOTOR_XY))
        return Part(name, pl.val(), ALU, "frame")

    parts.append(plate(s, s + P.PLATE_T, "bottom plate"))
    parts.append(plate(P.TOP_PLATE_Z, P.TOP_PLATE_Z + P.PLATE_T, "top plate"))
    return parts


def guide_parts() -> List[Part]:
    parts: List[Part] = []
    zb = P.PROFILE + P.PLATE_T
    zt = P.TOP_PLATE_Z
    for x, y in P.ROD_XY:
        parts.append(Part("rod 12h6", cyl(P.ROD_D / 2, zb - 4, zt + 4, x, y).val(), STEEL, "guide"))
        for z0, z1 in ((zb, zb + P.ROD_CLAMP_H), (zt - P.ROD_CLAMP_H, zt)):
            c = cyl(15, z0, z1, x, y).cut(cyl(P.ROD_D / 2, z0 - 1, z1 + 1, x, y))
            ang = math.atan2(y, x)
            ux, uy = math.cos(ang), math.sin(ang)
            slit = (cq.Workplane("XY").box(16, 1.6, z1 - z0 + 2)
                    .rotate((0, 0, 0), (0, 0, 1), math.degrees(ang))
                    .translate((x + ux * 9, y + uy * 9, (z0 + z1) / 2)))
            c = c.cut(slit)
            flange = (cq.Workplane("XY").workplane(offset=z0 if z0 == zb else z1 - 6)
                      .center(x, y).rect(36, 36).extrude(6).edges("|Z").fillet(5)
                      .cut(cyl(P.ROD_D / 2, z0 - 1, z1 + 1, x, y)))
            parts.append(Part("rod clamp", c.union(flange).val(), PETG_ACCENT, "guide"))
    return parts


def drive_parts() -> List[Part]:
    parts: List[Part] = []
    sx, sy = P.SCREW_XY
    zb = P.PROFILE
    zt = P.TOP_PLATE_Z + P.PLATE_T
    parts.append(Part("lead screw T8", cyl(P.SCREW_D / 2, 4, zt + 8, sx, sy).val(), STEEL, "drive"))
    for z0 in (zb + P.PLATE_T, P.TOP_PLATE_Z - 12):
        kfl = (cq.Workplane("XY").workplane(offset=z0).center(sx, sy)
               .slot2D(48, 26, 90).extrude(5)
               .union(cyl(10, z0, z0 + 12, sx, sy))
               .cut(cyl(4.2, z0 - 1, z0 + 13, sx, sy)))
        parts.append(Part("KFL08 bearing", kfl.val(), (0.30, 0.31, 0.33), "drive"))

    # przeniesienie GT2 20T:20T pod dolna plyta (w przestrzeni podstawy)
    mx, my = P.Z_MOTOR_XY
    for x, y in ((sx, sy), (mx, my)):
        pul = cyl(6.4, 5, 17, x, y).union(cyl(8, 5, 6.5, x, y)).union(cyl(8, 15.5, 17, x, y))
        parts.append(Part("GT2 20T pulley", pul.val(), (0.60, 0.61, 0.62), "drive"))
    dx, dy = mx - sx, my - sy
    dist = math.hypot(dx, dy)
    belt = (cq.Workplane("XY").workplane(offset=7).slot2D(dist + 13.8, 13.8, 0).extrude(6)
            .cut(cq.Workplane("XY").workplane(offset=6).slot2D(dist + 11.4, 11.4, 0).extrude(8))
            .rotate((0, 0, 0), (0, 0, 1), math.degrees(math.atan2(dy, dx)))
            .translate(((sx + mx) / 2, (sy + my) / 2, 0)))
    parts.append(Part("GT2 belt", belt.val(), RUBBER, "drive"))

    parts += nema17(mx, my, P.PROFILE + P.PLATE_T, down=True)
    return parts


# ---------------------------------------------------------------------------
# Wozek
# ---------------------------------------------------------------------------

def carriage_parts(zc: float) -> List[Part]:
    """zc: wysokosc lokalnego z=0 wozka (spod housing-bottom przekladni J1)."""
    parts: List[Part] = []
    shoulder = (P.GEARBOX_IN_OUT_MM, 0.0)
    t0, t1 = P.TOWER_Z0, P.TOWER_Z1
    r_tower = P.TOWER_OD / 2

    low = rounded_triangle(t0, t0 + P.CARRIAGE_LOW_PLATE_T, r_tower)
    low = low.cut(cyl(54.0, t0 - 1, t0 + P.CARRIAGE_LOW_PLATE_T + 1, *shoulder))
    up_z0 = t1 - 12
    up = rounded_triangle(up_z0, t1, r_tower)
    sx, sy = P.SCREW_XY
    low = low.cut(cyl(7, t0 - 1, t1 + 1, sx, sy))
    up = up.cut(cyl(5, t0 - 1, t1 + 1, sx, sy))
    up = up.cut(cyl(16, up_z0 - 1, t1 + 1, 0, 0))   # przepust kabli / chlodzenie silnika J1
    for x, y in P.ROD_XY:
        low = low.cut(cyl(r_tower, t0 - 1, t1 + 1, x, y))
        up = up.cut(cyl(r_tower, t0 - 1, t1 + 1, x, y))
    parts.append(Part("carriage lower plate (Al 10)", low.translate((0, 0, zc)).val(), ALU, "carriage"))
    parts.append(Part("carriage upper plate (Al 12)", up.translate((0, 0, zc)).val(), ALU, "carriage"))

    for x, y in P.ROD_XY:
        tower = cyl(r_tower, t0, t1, x, y).cut(cyl(P.BUSHING_OD / 2, t0 - 1, t1 + 1, x, y))
        parts.append(Part("bushing tower", tower.translate((0, 0, zc)).val(), PETG, "carriage"))
        for z0 in (t0, t1 - P.BUSHING_L):
            b = cyl(P.BUSHING_OD / 2, z0, z0 + P.BUSHING_L, x, y).cut(
                cyl(P.ROD_D / 2 + 0.05, z0 - 1, z0 + P.BUSHING_L + 1, x, y))
            parts.append(Part("LM12UU", b.translate((0, 0, zc)).val(), STEEL, "carriage"))

    # belka dociskowa obudowy przekladni J1 (miedzy przednimi wiezami, na housing-top)
    fx = P.ROD_XY[1][0]
    brace = box(fx - 14, fx - 2, -P.ROD_XY[1][1], P.ROD_XY[1][1], 40.0, 52.0)
    for _, y in P.ROD_XY[1:]:
        brace = brace.cut(cyl(r_tower + 0.5, 30, 60, fx, y))
    parts.append(Part("front clamp bar (Al 12x12)", brace.translate((0, 0, zc)).val(), ALU, "carriage"))
    # tylne zebro miedzy tylna wieza a dolna plyta (sztywnosc na skret)
    rx = P.ROD_XY[0][0]
    web = box(rx + r_tower, sx - 13, -3, 3, t0 + P.CARRIAGE_LOW_PLATE_T, up_z0)
    parts.append(Part("rear web", web.translate((0, 0, zc)).val(), PETG, "carriage"))

    nut = (cyl(11, up_z0 - 3.5, up_z0, sx, sy).union(cyl(5.1, up_z0 - 15, up_z0, sx, sy))
           .cut(cyl(4, up_z0 - 20, up_z0 + 1, sx, sy)))
    parts.append(Part("T8 anti-backlash nut", nut.translate((0, 0, zc)).val(), BRASS, "carriage"))
    return parts


def cable_chain(zc: float) -> List[Part]:
    """Prowadnik kabli (U w pionie) w szczelinie za tylnym walkiem."""
    parts: List[Part] = []
    x = (P.FRAME_X[0] + P.PROFILE + P.ROD_XY[0][0] - P.TOWER_OD / 2) / 2
    y_move, y_fix = 28.0, -28.0
    R = abs(y_move - y_fix) / 2
    z_move = zc + P.TOWER_Z1 - 10
    z_fix = P.FRAME_H / 2
    total = 360.0
    z_bend = (z_move + z_fix - (total - math.pi * R)) / 2
    pitch = 15.0
    link = lambda: cq.Workplane("XY").box(18, 15, 13.5).edges("|X").fillet(2.5)
    for y, z_top in ((y_move, z_move), (y_fix, z_fix)):
        n = max(int((z_top - z_bend) // pitch), 0)
        for i in range(n):
            zc_i = z_bend + pitch * (i + 0.5)
            parts.append(Part("cable chain link",
                              link().rotate((0, 0, 0), (1, 0, 0), 90).translate((x, y, zc_i)).val(),
                              (0.10, 0.10, 0.11), "cable"))
    n_bend = 6
    for i in range(n_bend):
        a = math.pi * (i + 0.5) / n_bend
        yy, zz = R * math.cos(a), -R * math.sin(a)
        parts.append(Part("cable chain link",
                          link().rotate((0, 0, 0), (1, 0, 0), math.degrees(a) - 90)
                          .translate((x, yy, z_bend + zz)).val(), (0.10, 0.10, 0.11), "cable"))
    bracket = box(x - 10, P.ROD_XY[0][0] - P.TOWER_OD / 2 + 2, y_move - 9, y_move + 9,
                  z_move + 6, z_move + 10)
    parts.append(Part("chain bracket", bracket.val(), PETG_ACCENT, "cable"))
    return parts


# ---------------------------------------------------------------------------
# Obudowa
# ---------------------------------------------------------------------------

SLOT_HALF_W = P.HOUSING_HALF_WIDTH + 8.0


def panel_parts(zc: float) -> List[Part]:
    x0, x1 = P.FRAME_X
    Y = P.FRAME_Y
    z0, z1 = P.PROFILE, P.FRAME_H
    t = 3.0
    parts: List[Part] = []
    parts.append(Part("side panel L (dibond 3)", box(x0, x1, Y, Y + t, z0, z1).val(), PANEL, "panel"))
    parts.append(Part("side window R (PMMA 3, dymiony)", box(x0, x1, -Y - t, -Y, z0, z1).val(),
                      SMOKE, "panel", 0.35))
    parts.append(Part("rear panel", box(x0 - t, x0, -Y, Y, z0, z1).val(), PANEL, "panel"))
    top = box(x0 - t, x1 + t, -Y - t, Y + t, z1, z1 + t).cut(cyl(10, z1 - 1, z1 + t + 1,
                                                                  *P.SCREW_XY))
    parts.append(Part("top cap", top.val(), PANEL, "panel"))

    s_z0 = P.CARRIAGE_Z_MIN + P.TOWER_Z0 - 4
    s_z1 = P.CARRIAGE_Z_MIN + P.Z_TRAVEL + 60
    front = box(x1, x1 + t, -Y, Y, z0, z1).cut(box(x1 - 1, x1 + t + 1, -SLOT_HALF_W, SLOT_HALF_W,
                                                   s_z0, s_z1))
    parts.append(Part("front panel", front.val(), PANEL, "panel"))
    # szczotki oslaniajace szczeline; w miejscu obudowy przekladni wyciecie
    opening = box(x1 - 5, x1 + t + 15, -P.HOUSING_HALF_WIDTH - 1, P.HOUSING_HALF_WIDTH + 1,
                  zc - 14, zc + 44)
    for sgn in (-1, 1):
        y_out, y_in = sgn * (SLOT_HALF_W + 6), sgn * 1.0
        brush = box(x1 + t, x1 + t + 6, min(y_out, y_in), max(y_out, y_in), s_z0, s_z1).cut(opening)
        parts.append(Part("brush strip", brush.val(), (0.07, 0.07, 0.08), "panel", 0.92))
        rail = box(x1 + t, x1 + t + 8, min(y_out, sgn * (SLOT_HALF_W - 2)),
                   max(y_out, sgn * (SLOT_HALF_W - 2)), s_z0, s_z1)
        parts.append(Part("brush holder", rail.val(), ALU, "panel"))
    return parts


# ---------------------------------------------------------------------------
# Ramie z v1 (STEP)
# ---------------------------------------------------------------------------

_V1_Z_PARTS = ("2020", "konfiguracja", "shaft_plate", "araba", "długość", "z axis plate",
               "locking nut", "nema 17 mount", "gearbox mount")


def _is_arm(name: str, bb) -> bool:
    n = name.lower()
    if any(k in n for k in _V1_Z_PARTS):
        return False
    cx = (bb[0] + bb[3]) / 2
    cz = (bb[2] + bb[5]) / 2
    if not (180.0 < cz < 300.0):
        return False
    if "gt2" in n:
        return cx > 300
    return cx > 63.0


def arm_parts(zc: float, step_path: str = V1_STEP, whole_v1: bool = False) -> List[Part]:
    """Ramie z v1 przesuniete do ukladu v2; whole_v1=True: caly montaz v1 bez zmian."""
    from OCP.BRepBndLib import BRepBndLib
    from OCP.Bnd import Bnd_Box
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.Quantity import Quantity_Color
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.TDataStd import TDataStd_Name
    from OCP.TDF import TDF_Label, TDF_LabelSequence
    from OCP.TDocStd import TDocStd_Document
    from OCP.TopLoc import TopLoc_Location
    from OCP.XCAFDoc import XCAFDoc_ColorType, XCAFDoc_DocumentTool

    doc = TDocStd_Document(TCollection_ExtendedString("v1"))
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    reader.SetColorMode(True)
    if reader.ReadFile(step_path) != IFSelect_RetDone:
        raise RuntimeError(f"nie mozna wczytac {step_path}")
    reader.Transfer(doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    ct = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())

    def name(lbl) -> str:
        attr = TDataStd_Name()
        return attr.Get().ToExtString() if lbl.FindAttribute(TDataStd_Name.GetID_s(), attr) else ""

    def color(lbl) -> Optional[Tuple[float, float, float]]:
        c = Quantity_Color()
        for t in (XCAFDoc_ColorType.XCAFDoc_ColorSurf, XCAFDoc_ColorType.XCAFDoc_ColorGen):
            if ct.GetColor_s(lbl, t, c):
                return (c.Red(), c.Green(), c.Blue())
        return None

    if whole_v1:
        dx = dy = dz = 0.0
    else:
        dx = -P.V1_J1_INPUT_XY[0]
        dy = -P.V1_J1_INPUT_XY[1]
        dz = zc - P.V1_HOUSING_BOTTOM_Z
    out: List[Part] = []

    def walk(lbl, loc, inherited, top_name):
        if st.IsReference_s(lbl):
            ref = TDF_Label()
            st.GetReferredShape_s(lbl, ref)
            col = color(lbl) or color(ref) or inherited
            walk(ref, loc.Multiplied(st.GetLocation_s(lbl)), col, f"{top_name}/{name(lbl)}")
            return
        if st.IsAssembly_s(lbl):
            seq = TDF_LabelSequence()
            st.GetComponents_s(lbl, seq)
            for i in range(1, seq.Length() + 1):
                walk(seq.Value(i), loc, inherited, top_name)
            return
        shape = st.GetShape_s(lbl).Moved(loc)
        bb = Bnd_Box()
        BRepBndLib.Add_s(shape, bb)
        if bb.IsVoid():
            return
        nm = top_name.strip("/") or name(lbl)
        if not whole_v1 and not _is_arm(nm, bb.Get()):
            return
        s = cq.Shape.cast(shape).translate(cq.Vector(dx, dy, dz))
        col = inherited or (0.85, 0.85, 0.85)
        if "nema17" in nm.lower() and col == (0.85, 0.85, 0.85):
            col = (0.08, 0.08, 0.09)
        if whole_v1 and "długość" in nm.lower():
            col = STEEL
        out.append(Part(nm, s, col, "arm"))

    free = TDF_LabelSequence()
    st.GetFreeShapes(free)
    for i in range(1, free.Length() + 1):
        root = free.Value(i)
        seq = TDF_LabelSequence()
        st.GetComponents_s(root, seq)
        for j in range(1, seq.Length() + 1):
            walk(seq.Value(j), TopLoc_Location(), None, "")
    return out


# ---------------------------------------------------------------------------

def carriage_z(fraction: float) -> float:
    return P.CARRIAGE_Z_MIN + P.Z_TRAVEL * fraction


def gantry_parts(fraction: float = 0.5, panels: bool = True) -> List[Part]:
    zc = carriage_z(fraction)
    parts = frame_parts() + guide_parts() + drive_parts() + carriage_parts(zc) + cable_chain(zc)
    if panels:
        parts += panel_parts(zc)
    return parts


def j1_limit(front_panel: bool) -> int:
    """Przyblizony zakres J1 zanim silnik J2 / tyl obudowy J2 dotknie wozka lub obudowy.

    Silnik J2 ~ okrag r=30 (pol-przekatna NEMA17), tyl obudowy przekladni J2 ~ okrag r=34
    wokol wejscia J2, ktore lezy 70 mm od osi barku (zmierzone w STEP v1).
    """
    sh = P.GEARBOX_IN_OUT_MM
    j2_in = math.hypot(264.0 - P.V1_SHOULDER_XY[0], -42.0 - P.V1_SHOULDER_XY[1])
    x_face = P.FRAME_X[1]
    uprights = [(x_face - P.PROFILE / 2, sy * (P.FRAME_Y - P.PROFILE / 2)) for sy in (-1, 1)]
    for deg in range(0, 181):
        a = math.radians(deg)
        mx, my = sh + j2_in * math.cos(a), j2_in * math.sin(a)
        hit = any(math.hypot(mx - x, my - y) < 34.0 + P.TOWER_OD / 2 for x, y in P.ROD_XY[1:])
        hit |= any(math.hypot(mx - x, my - y) < 34.0 + 14.2 for x, y in uprights)
        if front_panel:
            hit |= (mx - 30.0 < x_face + 3) and abs(my) + 21 > SLOT_HALF_W
        if hit:
            return deg - 1
    return 180


def j1_limit_report() -> None:
    print(f"J1 z pelnym panelem przednim: ok. +/-{j1_limit(True)} deg")
    print(f"J1 bez panelu przedniego (tylko slupki + szczotki): ok. +/-{j1_limit(False)} deg")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default=os.path.join(HERE, "z_gantry_v2.step"))
    args = ap.parse_args()

    print(f"trojkat walkow: bok {P.ROD_TRIANGLE_SIDE} mm, R = {P.ROD_R:.1f} mm, walki d{P.ROD_D}")
    print(f"wolna dlugosc walka {P.ROD_FREE_LENGTH:.0f} mm, walek {P.ROD_LENGTH:.0f} mm, "
          f"rozstaw tulei {P.BUSHING_SPACING:.0f} mm")
    print(f"skok Z {P.Z_TRAVEL:.0f} mm, wysokosc wiezy {P.FRAME_H:.0f} mm, "
          f"spod przekladni J1 od {P.CARRIAGE_Z_MIN:.0f} do {P.CARRIAGE_Z_MIN + P.Z_TRAVEL:.0f} mm")
    print(f"os barku {P.GEARBOX_IN_OUT_MM:.0f} mm od centroidu (v1: 161 mm od walkow)")
    j1_limit_report()
    if args.check:
        return

    asm = cq.Assembly(name="z_gantry_v2")
    for i, p in enumerate(gantry_parts(0.5, panels=True)):
        asm.add(p.shape, name=f"{i:03d}_{p.name}", color=cq.Color(*p.color, p.opacity))
    asm.export(args.out, exportType="STEP")
    print(f"zapisano {args.out}")


if __name__ == "__main__":
    main()
