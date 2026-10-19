"""Rendery osi Z v2 (PyVista, bez okna).

    python3 cad/v2/render.py                 # wszystkie widoki -> cad/v2/renders/
    python3 cad/v2/render.py --views open    # wybrane widoki
"""

from __future__ import annotations

import argparse
import os
from typing import Dict, Iterable, List

import numpy as np
import pyvista as pv

import params as P
from z_gantry_v2 import Part, arm_parts, carriage_z, gantry_parts

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "renders")

_mesh_cache: Dict[int, pv.PolyData] = {}


def to_mesh(part: Part, tol: float = 0.15) -> pv.PolyData:
    key = id(part.shape)
    if key not in _mesh_cache:
        verts, tris = part.shape.tessellate(tol, 0.25)
        pts = np.array([(v.x, v.y, v.z) for v in verts], dtype=float)
        faces = np.hstack([[3, *t] for t in tris]) if tris else np.empty(0, dtype=int)
        _mesh_cache[key] = pv.PolyData(pts, faces) if len(tris) else pv.PolyData()
    return _mesh_cache[key]


def _merge_by_color(parts: Iterable[Part]):
    groups: Dict[tuple, List[pv.PolyData]] = {}
    for p in parts:
        m = to_mesh(p)
        if m.n_points == 0:
            continue
        key = (tuple(round(c, 3) for c in p.color), round(p.opacity, 2), p.group)
        groups.setdefault(key, []).append(m)
    for (color, opacity, group), meshes in groups.items():
        yield color, opacity, group, pv.merge(meshes) if len(meshes) > 1 else meshes[0]


def make_plotter(size=(1900, 1300)) -> pv.Plotter:
    pl = pv.Plotter(off_screen=True, window_size=size, lighting="none")
    pl.set_background((0.30, 0.34, 0.40), top=(0.62, 0.66, 0.72))
    key = pv.Light(position=(900, -700, 1400), focal_point=(0, 0, 200), intensity=0.85)
    fill = pv.Light(position=(-900, -300, 600), focal_point=(0, 0, 200), intensity=0.35)
    rim = pv.Light(position=(-400, 900, 900), focal_point=(0, 0, 200), intensity=0.45)
    head = pv.Light(light_type="headlight", intensity=0.25)
    for light in (key, fill, rim, head):
        pl.add_light(light)
    return pl


def add_parts(pl: pv.Plotter, parts: Iterable[Part]) -> None:
    for color, opacity, group, mesh in _merge_by_color(parts):
        mesh = mesh.compute_normals(split_vertices=True, feature_angle=35, auto_orient_normals=False)
        metallic = group in ("guide", "drive") or color == (0.72, 0.74, 0.77)
        pl.add_mesh(mesh, color=color, opacity=opacity, smooth_shading=True,
                    specular=0.55 if metallic else 0.25, specular_power=30 if metallic else 12,
                    ambient=0.18, diffuse=0.85)


def add_ground(pl: pv.Plotter, center=(80, 0), size=1400) -> None:
    ground = pv.Plane(center=(center[0], center[1], -6.2), direction=(0, 0, 1),
                      i_size=size, j_size=size)
    pl.add_mesh(ground, color=(0.80, 0.81, 0.83), ambient=0.35, diffuse=0.7, specular=0.0)


def label(pl: pv.Plotter, text: str) -> None:
    pl.add_text(text, position="upper_left", font_size=13, color="white", shadow=True)


def finish(pl: pv.Plotter, name: str) -> str:
    pl.enable_ssao(radius=12, bias=0.5, kernel_size=128, blur=True)
    pl.enable_anti_aliasing("ssaa")
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{name}.png")
    pl.screenshot(path)
    pl.close()
    print("render:", path)
    return path


def scene(fraction: float, panels: bool, arm: List[Part], hide=()) -> List[Part]:
    parts = gantry_parts(fraction, panels=panels) + arm
    return [p for p in parts if not any(h in p.name for h in hide)]


def view_enclosed(arm: List[Part]) -> None:
    pl = make_plotter()
    add_ground(pl)
    add_parts(pl, scene(0.55, True, arm))
    pl.camera_position = [(920, -980, 720), (90, 0, 215), (0, 0, 1)]
    pl.camera.view_angle = 30
    label(pl, "SCARA v2 - zabudowana os Z (3 walki 12 mm w trojkacie, silnik J1 w srodku)")
    finish(pl, "v2_enclosed_iso")


def view_open(arm: List[Part]) -> None:
    pl = make_plotter()
    add_ground(pl)
    add_parts(pl, scene(0.55, False, arm))
    pl.camera_position = [(900, -940, 640), (60, 0, 215), (0, 0, 1)]
    pl.camera.view_angle = 30
    label(pl, "SCARA v2 - bez oslon: trojkat walkow, wozek, sruba T8 z tylu, silnik Z na dole")
    finish(pl, "v2_open_iso")


def view_rear(arm: List[Part]) -> None:
    pl = make_plotter()
    add_ground(pl)
    add_parts(pl, scene(0.3, False, arm))
    pl.camera_position = [(-900, 760, 620), (-20, 0, 200), (0, 0, 1)]
    pl.camera.view_angle = 30
    label(pl, "SCARA v2 - widok z tylu: prowadnik kabli, sruba T8, przeniesienie GT2 pod plyta")
    finish(pl, "v2_open_rear")


def view_carriage(arm: List[Part]) -> None:
    pl = make_plotter()
    hide = ("upright", "top rail", "top cross", "top plate", "side", "rear panel", "front panel",
            "top cap", "brush", "cable chain", "chain bracket")
    hide += ("rear mid cross",)
    parts = scene(0.5, False, arm, hide=hide)
    zc = carriage_z(0.5)
    add_parts(pl, parts)
    pl.camera_position = [(330, -420, zc + 330), (10, 0, zc + 40), (0, 0, 1)]
    pl.camera.view_angle = 30
    label(pl, "Wozek Z v2: 3x LM12UU x2 (rozstaw 110 mm), silnik J1 w centroidzie")
    finish(pl, "v2_carriage_closeup")


def view_top(arm: List[Part]) -> None:
    pl = make_plotter((1600, 1300))
    hide = ("top rail", "top cross", "top plate", "top cap", "KFL08", "rod clamp", "front panel",
            "side", "rear panel", "brush")
    parts = scene(0.5, True, arm, hide=hide)
    parts = [Part(p.name, p.shape, p.color, p.group, 0.3) if "upper plate" in p.name else p
             for p in parts]
    add_parts(pl, parts)
    zc = carriage_z(0.5)
    tri = np.array([(x, y, zc + P.TOWER_Z1 + 2) for x, y in P.ROD_XY] +
                   [(P.ROD_XY[0][0], P.ROD_XY[0][1], zc + P.TOWER_Z1 + 2)])
    pl.add_lines(tri, color=(1.0, 0.85, 0.1), width=4, connected=True)
    pl.add_point_labels([(0, 0, zc + P.TOWER_Z1 + 4), (P.GEARBOX_IN_OUT_MM, 0, zc + 60)],
                        ["J1 (silnik) - centroid", "os barku (+100 mm)"],
                        font_size=20, point_size=12, point_color="yellow", text_color="white",
                        shape_opacity=0.6, always_visible=True)
    pl.camera_position = [(140, 0, 1500), (140, 0, 0), (1, 0, 0)]
    pl.enable_parallel_projection()
    pl.camera.parallel_scale = 330
    label(pl, "Widok z gory: trojkat walkow (bok 140 mm), sruba T8 za silnikiem J1")
    finish(pl, "v2_top")


def view_compare(arm: List[Part], v1: List[Part]) -> None:
    pl = make_plotter((2200, 1200))
    shift = 560.0
    add_ground(pl, center=(150, shift / 2), size=2600)
    v1_moved = [Part(p.name, p.shape.translate(pv_vec(-40, 72.5 + shift, 20)), p.color, p.group)
                for p in v1]
    add_parts(pl, v1_moved)
    add_parts(pl, scene(0.55, True, arm))
    pl.add_point_labels([(0, shift, 600), (-40, 0, 520)], ["v1", "v2"], font_size=30,
                        point_size=1, text_color="white", shape_opacity=0.0, show_points=False,
                        always_visible=True)
    pl.camera_position = [(1650, -700, 820), (40, shift / 2, 230), (0, 0, 1)]
    pl.camera.view_angle = 30
    label(pl, "v1 (2 walki 8 mm, rama 500 mm) vs v2 (3 walki 12 mm, zabudowa)")
    finish(pl, "v1_vs_v2")


def pv_vec(x, y, z):
    import cadquery as cq
    return cq.Vector(x, y, z)


VIEWS = {
    "enclosed": view_enclosed,
    "open": view_open,
    "rear": view_rear,
    "carriage": view_carriage,
    "top": view_top,
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--views", nargs="*", default=list(VIEWS) + ["compare"])
    args = ap.parse_args()

    arm_cache: Dict[float, List[Part]] = {}

    def arm_at(fraction: float) -> List[Part]:
        if fraction not in arm_cache:
            arm_cache[fraction] = arm_parts(carriage_z(fraction))
        return arm_cache[fraction]

    fractions = {"enclosed": 0.55, "open": 0.55, "rear": 0.3, "carriage": 0.5, "top": 0.5}
    for v in args.views:
        if v == "compare":
            view_compare(arm_at(0.55), arm_parts(0.0, whole_v1=True))
        else:
            VIEWS[v](arm_at(fractions[v]))


if __name__ == "__main__":
    main()
