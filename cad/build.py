"""Parametric 3-D models of every part of the TJ-110 micro-turbojet, plus the assembly.

Writes:
  cad/stl/<part>.stl               one watertight file per unique part, each at its own origin (millimetres)
  cad/assembly_TJ110.stl           assembled engine on its test stand (decimated for size)
  cad/viewer_TJ110.html            interactive 3-D viewer (Plotly)
  cad/bom_TJ110.csv                bill of materials with masses from the meshes
  cad/interference_TJ110.txt       pairwise overlap check + rotor/stator running clearances
  diagrams/cad_TJ110_section.png   section through the axis, coloured by part
  diagrams/cad_TJ110_exterior.png  shaded exterior render

Gas-path dimensions are read from data/design_point.json (SI, metres) and converted to mm.
Axial layout, wall thicknesses and fasteners are design choices made here (see cad/README.md).
Architecture: bellmouth -> centrifugal compressor -> vaned radial diffuser + axial deswirl ->
annular vaporizer combustor -> NGV -> axial turbine -> convergent nozzle with tail cone.
An original parametric design study: not built, not run.

Engine axis = +z (flow direction); "up" = +x; the test stand sits on the -x side.

Run: .venv/bin/python cad/build.py
"""
import csv
import json
import time
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import CrossSection, Manifold, Mesh
from shapely.geometry import LineString, Point, Polygon, box
from shapely.geometry.polygon import orient

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "cad"
SEG = 128
NAME = "TJ110"


# --------------------------------------------------------------------------- configuration
class Cfg:
    """All dimensions in mm. Gas-path numbers from the cycle/aero model; layout numbers chosen here."""

    def __init__(self, dp_path=ROOT / "data" / "design_point.json"):
        dp = json.loads(Path(dp_path).read_text())
        self.dp = dp
        s, c, t, g = dp["spec"], dp["compressor"], dp["turbine"], dp["geometry"]
        mm = 1e3
        # compressor
        self.r2, self.b2 = c["r2"] * mm, c["b2"] * mm
        self.r1t, self.r1h = c["r1t"] * mm, c["r1h"] * mm
        self.Zc = int(s["Z"]) // 2                      # main blades (same number of splitters)
        self.beta1t, self.beta2b = c["beta1t"], s["beta2b"]
        self.clear_c = s["clear_c"] * mm
        self.r3 = c["r3"] * mm
        self.alpha2c = c["alpha2"]
        self.n_diff = 18                                # wedge vanes (18 so 6 fixing screws fall on every 3rd vane)
        self.n_deswirl = 24
        # casing / combustor
        self.rc_in = g["r_case_in"] * mm
        self.wall = s["casing_wall"] * mm
        self.rc_out = self.rc_in + self.wall
        self.liner_in, self.liner_out, self.liner_len = g["liner_in"] * mm, g["liner_out"] * mm, g["liner_len"] * mm
        self.A_holes = dp["combustor"]["A_holes"] * 1e6
        self.split_dil = dp["combustor"]["split_dilution"]
        # rotor
        self.rs, self.rs_mid = s["shaft_d"] * mm / 2, s["shaft_d_mid"] * mm / 2
        self.span = s["bearing_span"] * mm
        self.k_bearing = s["k_bearing"]
        self.tunnel_r = g["shaft_tunnel_r"] * mm
        # turbine
        self.rt, self.rh, self.rm = t["rt"] * mm, t["rh"] * mm, t["rm"] * mm
        self.chord = t["chord"] * mm
        self.Zr, self.Zn = int(s["Zr"]), int(s["Zn"])
        self.clear_t = s["clear_t"] * mm
        self.U, self.Cx = t["U"], t["Cx"]
        self.Cth2 = t["C2"] * np.sin(np.radians(t["alpha2"]))
        self.Cth3 = self.Cth2 - t["psi"] * t["U"]
        self.r9 = g["D_nozzle"] * mm / 2
        # ------------------------------------------------ axial layout (z = 0 at the inducer leading edge)
        self.r_duct = self.r1t + self.clear_c          # inlet duct / shroud radius at the inducer
        self.z_hub_exit = round(0.262 * 2 * self.r2, 1)  # impeller axial length to the hub at the exit
        self.z_tip_exit = self.z_hub_exit - self.b2
        self.z_fw = self.z_tip_exit - self.clear_c     # front wall of the radial diffuser (front cover face)
        self.z_back = self.z_hub_exit + 3.0             # impeller back face
        self.bw, self.b_od, self.b_id = 7.0, 22.0, 8.0  # 608 bearing
        self.z_b1 = self.z_back + 1.5 + self.bw / 2     # front bearing centre
        self.z_b2 = self.z_b1 + self.span               # rear bearing centre
        self.z_t = self.z_b2 + 14.0                     # turbine disc centre
        self.z_tle = self.z_t - self.chord / 2          # turbine blade leading edge
        self.z_tte = self.z_t + self.chord / 2
        self.z_ngv_te = self.z_tle - 1.15               # NGV trailing edge
        self.ngv_cx = 10.0
        self.z_ngv_le = self.z_ngv_te - self.ngv_cx
        self.rt_s = self.rt + self.clear_t              # turbine shroud radius
        self.z_dome = 38.0                              # combustor dome
        self.z_liner_end = self.z_dome + self.liner_len
        self.z_noz_exit = 200.0
        # soft bearing mounts (rotordynamics update): sleeve on two O-rings per bearing
        self.sl_ri, self.sl_ro = self.b_od / 2, 12.0    # bearing sleeve 22 / 24 mm
        self.tun_bore = 12.15                           # tunnel bore over the sleeve: 0.15 mm radial travel
        self.groove_r = 13.35                           # O-ring groove bottom (1.35 mm gland for a 1.5 mm cord)
        self.housing_r = 14.6                           # tunnel bearing-housing OD
        self.or_cs = 1.5
        self.fl = 1.5                                   # flange thickness (casing, NGV, nozzle)
        self.ngv_ro = 36.2                              # NGV outer ring / turbine shroud OD


C = Cfg()
PIN_DZ = 3.1          # anti-rotation pin station from the sleeve front face


# --------------------------------------------------------------------------- helpers
def to_trimesh(m: Manifold):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)


def from_arrays(V, F):
    tm = trimesh.Trimesh(np.asarray(V, float), np.asarray(F), process=True)
    trimesh.repair.fix_normals(tm)
    m = Manifold(Mesh(vert_properties=np.asarray(tm.vertices, np.float32), tri_verts=np.asarray(tm.faces, np.uint32)))
    assert not m.is_empty(), "mesh is not a closed 2-manifold"
    return m


def tube(r_in, r_out, z0, z1, seg=SEG):
    m = Manifold.cylinder(z1 - z0, r_out, r_out, seg)
    if r_in > 0:
        m = m - Manifold.cylinder(z1 - z0 + 0.02, r_in, r_in, seg).translate([0, 0, -0.01])
    return m.translate([0, 0, z0])


def cyl(r, z0, z1, seg=48):
    return Manifold.cylinder(z1 - z0, r, r, seg).translate([0, 0, z0])


def cs_from_poly(poly):
    loops = []
    for p in getattr(poly, "geoms", [poly]):
        p = orient(p, 1.0)
        loops.append(np.asarray(p.exterior.coords)[:-1])
        loops += [np.asarray(i.coords)[:-1] for i in p.interiors]
    return CrossSection(loops)


def revolve(poly, seg=SEG):
    """Revolve a shapely polygon (x = r, y = z) about the z axis; a list of (r, z) points also works."""
    if not hasattr(poly, "geom_type"):
        poly = Polygon(poly)
    return cs_from_poly(poly.buffer(0).simplify(0.01)).revolve(seg)


def sheet(pts, t, toward):
    """Polygon of thickness t on the side of polyline pts that faces the point `toward`."""
    L = LineString(pts)
    a, b = L.buffer(t, single_sided=True), L.buffer(-t, single_sided=True)
    return a if a.distance(Point(toward)) < b.distance(Point(toward)) else b


def polar(m, n, phase=0.0):
    out = Manifold()
    for k in range(n):
        out += m.rotate([0, 0, phase + 360.0 * k / n])
    return out


def radial(m, r0, ang, z):
    """Part built along +z from its origin -> pointing radially outward from r0 at angle ang, axial station z."""
    return m.rotate([0, 90, 0]).translate([r0, 0, z]).rotate([0, 0, ang])


def axial(m, r, ang, z, flip=False):
    if flip:
        m = m.rotate([180, 0, 0])
    return m.translate([r, 0, z]).rotate([0, 0, ang])


def grid_solid(P):
    """Closed mesh from a (ni, nj, 2, 3) grid: two skins (k = 0, 1) joined along all four edges."""
    ni, nj = P.shape[:2]
    idx = np.arange(ni * nj * 2).reshape(ni, nj, 2)
    F = []

    def quads(a, b, c, d):
        a, b, c, d = (np.asarray(x).ravel() for x in (a, b, c, d))
        F.extend(np.c_[a, b, c]); F.extend(np.c_[a, c, d])

    for k in (0, 1):
        g = idx[:, :, k]
        quads(g[:-1, :-1], g[1:, :-1], g[1:, 1:], g[:-1, 1:])
    for j in (0, nj - 1):
        quads(idx[:-1, j, 0], idx[1:, j, 0], idx[1:, j, 1], idx[:-1, j, 1])
    for i in (0, ni - 1):
        quads(idx[i, :-1, 0], idx[i, 1:, 0], idx[i, 1:, 1], idx[i, :-1, 1])
    return from_arrays(P.reshape(-1, 3), np.array(F))


def thickness(xi, tmax, tmin):
    f = np.sqrt(np.clip(xi, 0, 1)) * (1 - xi) / 0.3849
    return np.maximum(tmin, tmax * f)


def axial_blade(radii, z0, cx, ang_in, ang_out, tmax, tmin, n=30):
    """Cambered, twisted blade for an axial row. Angles (deg, from axial, + = direction of rotation)
    are functions of radius; returns a Manifold with the section stacked about its centroid at theta = 0."""
    xi = 0.5 * (1 - np.cos(np.linspace(0, np.pi, n)))
    P = np.zeros((n, len(radii), 2, 3))
    for j, r in enumerate(radii):
        a = np.radians(ang_in(r) + (ang_out(r) - ang_in(r)) * xi)
        x = xi * cx
        y = np.concatenate([[0], np.cumsum(0.5 * (np.tan(a[1:]) + np.tan(a[:-1])) * np.diff(x))])
        y -= y.mean()
        t = thickness(xi, tmax(r), tmin)
        for k, sgn in enumerate((1, -1)):
            xs = x - sgn * t / 2 * np.sin(a)
            ys = y + sgn * t / 2 * np.cos(a)
            th = ys / r
            P[:, j, k] = np.c_[r * np.cos(th), r * np.sin(th), z0 + xs]
    return grid_solid(P)


# --------------------------------------------------------------------------- fasteners
def screw(L, d=3.0, head_d=5.5, head_h=3.0):
    """Socket-head cap screw: under-head face at z = 0, shank along +z (threads not modelled)."""
    shank = cyl(d / 2 - 0.05, 0, L, 24)
    head = cyl(head_d / 2, -head_h, 0, 32) - Manifold.cylinder(head_h * 0.5 + 0.01, d * 0.48, d * 0.48, 6).translate([0, 0, -head_h - 0.01])
    return shank + head


def nut(d=3.0, af=5.5, h=2.4):
    return Manifold.cylinder(h, af / np.sqrt(3), af / np.sqrt(3), 6) - cyl(d / 2, -0.1, h + 0.1, 24)


# --------------------------------------------------------------------------- parts (each at its own origin)
def bellmouth(c: Cfg):
    """Inlet: elliptical lip 14 mm radial x 16 mm axial, 2.5 mm wall, flange to the front cover,
    3 bosses with M3 holes for a starter bracket. Built in engine coordinates (z = -38..-6)."""
    t = np.radians(np.linspace(0, 90, 40))
    gas = [(c.r_duct, -6.0), (c.r_duct, -22.0)] + [(c.r_duct + 14 * (1 - np.cos(a)), -22 - 16 * np.sin(a)) for a in t[1:]]
    wall = sheet(gas, 2.5, (60, -15))
    end = np.array(gas[-1])
    lip = Point(end[0] + 1.25, end[1]).buffer(1.25, 24)
    prof = wall.union(lip).union(box(c.r_duct, -9, 32, -6))
    body = revolve(prof)
    body -= polar(cyl(1.7, -10, -5, 24).translate([29.2, 0, 0]), 6, 0)
    lug = cyl(3.5, -34, -26, 32).translate([44, 0, 0]) + Manifold.cube([17, 6, 8]).translate([27, -3, -34])
    lug -= cyl(1.5, -35, -27, 24).translate([44, 0, 0])
    cavity = revolve(Polygon([(0, -5)] + gas + [(end[0], -45), (0, -45)]))
    return body + (polar(lug, 3, 0) - cavity), gas


def front_cover(c: Cfg):
    """Compressor shroud (0.3 mm off the blade tips) + front wall of the radial diffuser + front flange."""
    a, b = c.r2 - c.r1t, c.z_tip_exit
    t = np.linspace(0, np.pi / 2, 60)
    T = np.c_[c.r2 - a * np.cos(t), b * np.sin(t)]
    n = np.c_[b * np.cos(t), -a * np.sin(t)]
    n /= np.linalg.norm(n, axis=1)[:, None]
    S = T + c.clear_c * n
    gas = [(c.r_duct, -6.0)] + [tuple(p) for p in S] + [(65.0, c.z_fw)]
    prof = sheet(gas, 3.5, (45, 0)).union(box(c.r_duct, -6, 32, -3))
    body = revolve(prof)
    body -= polar(cyl(1.5, -7, -2, 24).translate([29.2, 0, 0]), 6, 0)               # M3 tapped, bellmouth
    body -= polar(cyl(1.7, c.z_fw - 5, c.z_fw + 1, 24).translate([62.3, 0, 0]), 8, 0)  # front flange
    for x, y in diffuser_screw_xy(c):
        body -= cyl(1.7, c.z_fw - 5, c.z_fw + 1, 24).translate([x, y, 0])
    return body, gas


def impeller_profiles(c: Cfg):
    ah, bh = c.r2 - c.r1h, c.z_hub_exit
    t = np.linspace(0, np.pi / 2, 48)
    hub = np.c_[c.r2 - ah * np.cos(t), bh * np.sin(t)]
    a, b = c.r2 - c.r1t, c.z_tip_exit
    tip = np.c_[c.r2 - a * np.cos(t), b * np.sin(t)]
    return hub, tip


def impeller(c: Cfg):
    """Backswept impeller: 7 main + 7 splitter blades (~1 mm), hub disc with back face and rear boss."""
    hub, tip = impeller_profiles(c)
    rb = c.rs + 0.005
    prof = [(rb, -1.0), (c.r1h, -1.0)] + [tuple(p) for p in hub] + [(c.r2, c.z_hub_exit + 2), (20.0, c.z_back),
                                                                  (6.5, c.z_back), (6.5, c.z_back + 1.5), (rb, c.z_back + 1.5)]
    disc = revolve(prof)
    spans = np.linspace(-0.10, 1.0, 9)
    ni = hub.shape[0]
    tb1 = np.radians(c.beta1t)
    b2 = np.radians(c.beta2b)

    def blade(i0):
        P = np.zeros((ni - i0, len(spans), 2, 3))
        for j, s in enumerate(spans):
            pts = hub + s * (tip - hub)
            r, z = pts[:, 0], pts[:, 1]
            dl = np.r_[0, np.hypot(np.diff(r), np.diff(z))]
            ell = np.cumsum(dl); f = ell / ell[-1]
            bin_ = np.arctan(np.tan(tb1) * max(r[0], 1.0) / c.r1t)
            beta = bin_ * (1 - f) + b2 * f
            dth = np.tan(beta) / r
            th = -np.concatenate([[0], np.cumsum(0.5 * (dth[1:] + dth[:-1]) * np.diff(ell))])
            tk = (1.2 - 0.4 * np.clip(s, 0, 1)) * np.minimum(1, 0.35 + 0.65 * np.clip((f - f[i0]) / 0.08, 0, 1))
            for k, sgn in enumerate((1, -1)):
                tt = th + sgn * tk / 2 / r
                P[:, j, k] = np.c_[r * np.cos(tt), r * np.sin(tt), z][i0:]
        return grid_solid(P)

    main = blade(0)
    i_s = int(0.35 * ni)
    split = blade(i_s).rotate([0, 0, 180.0 / c.Zc])
    return disc + polar(main, c.Zc) + polar(split, c.Zc)


def wedge_vane_poly(c: Cfg):
    r_le = 1.08 * c.r2
    ro = c.r3 - 0.1
    pts = [(r_le, 0.0)]
    for alpha, sign in ((70.0, 1), (55.0, -1)):
        p = r_le * np.sin(np.radians(alpha))
        dth = np.radians(alpha) - np.arcsin(p / ro)
        pts.append((ro, dth))
    th = np.linspace(pts[1][1], pts[2][1], 8)
    xy = [(r_le, 0.0)] + [(ro * np.cos(a), ro * np.sin(a)) for a in th]
    return Polygon(xy)


def vane_phase(c: Cfg):
    """Rotate the vane pattern so that the fixing screw on vane 0 lies at 0 deg (in the section plane)."""
    pg = wedge_vane_poly(c)
    best = None
    for a in np.linspace(5, 35, 121):
        x, y = 50 * np.cos(np.radians(a)), 50 * np.sin(np.radians(a))
        d = pg.exterior.distance(Point(x, y)) if pg.contains(Point(x, y)) else -1
        if best is None or d > best[0]:
            best = (d, a)
    return -best[1], best[0]


def diffuser_screw_xy(c: Cfg):
    return [(50 * np.cos(np.radians(a)), 50 * np.sin(np.radians(a))) for a in range(0, 360, 60)]


def diffuser(c: Cfg):
    """Vaned radial diffuser (18 wedge vanes to r3) + rounded 90 deg turn + 24 axial deswirl vanes."""
    zf = c.z_fw
    ph = np.linspace(0, np.pi / 2, 16)
    z19 = c.z_hub_exit
    prof = [(c.housing_r + 0.1, 22.5), (c.r2 + 0.5, 22.5), (c.r2 + 0.5, z19)] + \
           [(c.r3, z19)] + [(50.5 + (c.r3 - 50.5) * np.cos(p), z19 + 4.0 * np.sin(p)) for p in ph[1:]] + \
           [(50.5, 27.0), (49.0, 27.0), (49.0, 25.5), (c.housing_r + 0.1, 25.5)]
    plate = revolve(prof)
    vane = cs_from_poly(wedge_vane_poly(c)).extrude(z19 + 0.05 - (zf + 0.03)).translate([0, 0, zf + 0.03])
    phase, _ = vane_phase(c)
    vanes = polar(vane, c.n_diff, phase)
    desw = axial_blade(np.linspace(50.2, c.rc_in - 0.12, 6), z19 + 2.5, 26.8 - (z19 + 2.5),
                       lambda r: 45.0, lambda r: 0.0, lambda r: 1.2, 0.4, n=16)
    body = plate + vanes + polar(desw, c.n_deswirl, 7.5)
    for x, y in diffuser_screw_xy(c):
        body -= cyl(1.5, zf - 1, z19 + 1.5, 24).translate([x, y, 0])        # M3 tapped in the vane
    body -= polar(cyl(1.5, 21.5, 26, 24).translate([20, 0, 0]), 6, 0)          # M3 tapped from the tunnel flange
    return body


def shaft(c: Cfg):
    prof = [(0, -6.0), (c.rs, -6.0), (c.rs, 31.5), (c.rs_mid, 32.0), (c.rs_mid, c.z_b2 - 4.5),
            (c.rs, c.z_b2 - 4.0), (c.rs, c.z_t + 13.0), (0, c.z_t + 13.0)]
    return revolve(prof, 64)


def compressor_nut(c: Cfg):
    hexa = Manifold.cylinder(6.0, 12 / np.sqrt(3), 12 / np.sqrt(3), 6)          # z 0..6 (AF 12)
    dome = revolve([(0, -2.5), (3.0, -2.3), (5.0, -1.2), (5.6, 0.0), (0, 0.0)], 48)
    return (hexa + dome) - cyl(c.rs + 0.005, 0.8, 6.1, 64)


def turbine_nut(c: Cfg):
    return Manifold.cylinder(6.0, 12 / np.sqrt(3), 12 / np.sqrt(3), 6) - cyl(c.rs + 0.005, -0.1, 6.1, 64)


def bearing_608(c: Cfg):
    ir = tube(c.b_id / 2 + 0.005, 5.9, 0, c.bw, 64)
    orr = tube(9.55, c.b_od / 2 - 0.005, 0, c.bw, 64)
    balls = polar(Manifold.sphere(3.969 / 2, 24).translate([7.75, 0, c.bw / 2]), 7)
    return ir + orr + balls


def spacer_tube(c: Cfg):
    return tube(c.rs_mid + 0.1, 6.8, 0, c.span - c.bw, 64)


def preload_spring(c: Cfg, length):
    wire = CrossSection.circle(0.4, 16).translate([10.2, 0])
    coils = length / 2.0
    return wire.extrude(length - 0.8, int(coils * 40), coils * 360.0).translate([0, 0, 0.4]) + \
        tube(9.8, 10.6, 0, 0.4, 64) + tube(9.8, 10.6, length - 0.4, length, 64)


def bearing_sleeve(c: Cfg, lip):
    """Thin 17-4PH cartridge round the bearing outer race; floats on two O-rings."""
    L = c.bw + (0.8 if lip else 0.0)
    m = tube(c.sl_ri, c.sl_ro, 0, L, 96)
    if lip:
        m += tube(9.8, c.sl_ri + 0.01, c.bw, L, 96)
    m -= cyl(1.0, 0, 2, 16).rotate([0, 90, 0]).translate([10.5, 0, PIN_DZ])  # anti-rotation pin hole
    if lip:
        m -= cyl(0.5, 0, 2, 16).rotate([0, 90, 0]).translate([10.5, 0, 0]).rotate([0, 0, 270]).translate([0, 0, 6.8])  # oil hole
    return m


def oring(c: Cfg):
    """Viton O-ring 24 x 1.5, shown at its installed 10 % squeeze (1.35 mm radial)."""
    rc = (c.sl_ro + c.groove_r) / 2
    return CrossSection.circle((c.groove_r - c.sl_ro) / 2, 24).translate([rc, 0]).revolve(96)


def anti_rotation_pin(c: Cfg):
    return cyl(0.75, 0, c.housing_r - 11.4, 16)


def shaft_tunnel(c: Cfg):
    """Bearing tunnel: front flange bolted behind the diffuser, rear spigot pilots in the NGV hub web."""
    zf0 = c.z_back + 1.0
    zs1 = c.z_b1 - c.bw / 2                     # front sleeve 23.5 .. 31.3
    zs1e = zs1 + c.bw + 0.8
    zr0 = c.z_b2 - c.bw / 2                     # rear sleeve 108.5 .. 115.5
    zend = c.z_b2 + c.bw / 2
    H = c.housing_r
    prof = [(c.tun_bore, zf0), (H, zf0), (H, 25.5), (24.0, 25.5), (24.0, 28.5), (H, 28.5), (H, 34.0),
            (c.tunnel_r, 36.0), (c.tunnel_r, c.z_b2 - 14.0), (H, c.z_b2 - 13.0), (H, zend), (c.tun_bore, zend),
            (c.tun_bore, zr0 - 0.2), (11.0, zr0 - 0.2), (11.0, c.z_b2 - 12.0), (9.5, c.z_b2 - 12.0), (9.5, zs1e),
            (c.tun_bore, zs1e)]
    body = revolve(prof)
    gw = c.or_cs + 0.4
    grooves = [zs1 + 1.2, zs1 + 5.1, zr0 + 1.2, zr0 + 5.8]
    for zg in grooves:
        body -= tube(0, c.groove_r, zg - gw / 2, zg + gw / 2, 96)
    body -= polar(cyl(1.7, 24.5, 29.5, 24).translate([20, 0, 0]), 6, 0)
    for zp in (zs1 + PIN_DZ, zr0 + PIN_DZ):
        body -= radial(cyl(0.75, 0, 5, 16), 10.5, 0, zp)
    body -= radial(cyl(0.6, 0, 5, 16), 10.5, 270, 30.3)                    # oil drilling
    return body, grooves


def casing(c: Cfg):
    """1 mm stainless sheet tube with welded flanges and bosses (fuel, oil, glow plug)."""
    z0, z1 = c.z_fw, c.z_ngv_te
    prof = [(c.rc_in, z0), (65, z0), (65, z0 + c.fl), (c.rc_out, z0 + c.fl), (c.rc_out, z1 - c.fl), (65, z1 - c.fl), (65, z1), (c.rc_in, z1)]
    body = revolve(prof)
    body += radial(cyl(4.0, 0, 62.5 - 58.8, 32), 58.8, 112.5, 34.0)
    body += radial(cyl(4.0, 0, 62.5 - 58.8, 32), 58.8, 270, 30.3)
    body += radial(cyl(5.0, 0, 63.0 - 58.8, 32), 58.8, 22.5, 46.0)
    body -= radial(cyl(1.55, 0, 10, 24), 55, 112.5, 34.0)
    body -= radial(cyl(1.55, 0, 10, 24), 55, 270, 30.3)
    body -= radial(cyl(3.2, 0, 10, 32), 55, 22.5, 46.0)
    for zz in (z0 - 1, z1 - 3):
        body -= polar(cyl(1.7, zz, zz + 4, 24).translate([62.3, 0, 0]), 8, 0)
    return body


def hole_rows(c: Cfg):
    """Liner hole rows: (z, wall, n, d). Areas split primary 25 % / secondary 30 % / dilution from the model."""
    rows = []
    A = c.A_holes
    for frac, dz in ((0.25, 12.0), (1 - 0.25 - c.split_dil, 28.0), (c.split_dil, 47.0)):
        for wall, share, n in (("outer", 0.75, 16), ("inner", 0.25, 8)):
            d = np.sqrt(4 * A * frac * share / (np.pi * n))
            rows.append((c.z_dome + dz, wall, n, round(d, 1)))
    return rows


def liner_outer(c: Cfg):
    """Outer liner + dome (0.5 mm sheet): 8 vaporizer holes in the dome; cone to the NGV spigot."""
    zd = c.z_dome
    ro = c.liner_out
    line = [(ro, zd), (ro, c.z_liner_end - 18), (c.ngv_ro + 0.3, c.z_liner_end - 9), (c.ngv_ro + 0.3, c.z_liner_end)]
    prof = LineString(line).buffer(0.25, cap_style=2, join_style=2).union(box(c.liner_in + 0.3, zd, ro + 0.25, zd + 0.5))
    body = revolve(prof)
    body -= polar(cyl(2.55, zd - 1, zd + 2, 32).translate([34, 0, 0]), 8, 0)
    for z, wall, n, d in hole_rows(c):
        if wall == "outer":
            body -= polar(radial(cyl(d / 2, 0, 4, 32), ro - 2, 0, z), n, 360 / n / 2)
    body -= radial(cyl(3.4, 0, 4, 32), ro - 2, 22.5, 46.0)
    return body


def liner_inner(c: Cfg):
    zd = c.z_dome
    ri = c.liner_in
    line = [(ri, zd), (ri, c.z_liner_end - 16), (18.2, c.z_liner_end - 9), (18.2, c.z_liner_end - 2.5)]
    body = revolve(LineString(line).buffer(0.25, cap_style=2, join_style=2))
    for z, wall, n, d in hole_rows(c):
        if wall == "inner":
            body -= polar(radial(cyl(d / 2, 0, 4, 32), ri - 2, 0, z), n, 360 / n / 2)
    return body


def vaporizer(c: Cfg):
    """J-shaped vaporizer: Ø5 x 0.5 tube, 34 mm straight leg, R5 bend, 12 mm return leg (local frame)."""
    ann = CrossSection.circle(2.5, 32) - CrossSection.circle(2.0, 32)
    leg1 = ann.extrude(34.0)
    bend = ann.translate([5, 0]).revolve(64, 180).rotate([90, 0, 0]).translate([5, 0, 34])
    leg2 = ann.extrude(12.0).translate([10, 0, 22])
    return leg1 + bend + leg2


def fuel_manifold(c: Cfg):
    ann = CrossSection.circle(1.5, 24).translate([34, 0]) - CrossSection.circle(1.0, 24).translate([34, 0])
    return ann.revolve(SEG)


def fuel_needle(c: Cfg):
    return tube(0.2, 0.4, 0, 3.05, 16)


def line_tube(r_out, r_in, L):
    return tube(r_in, r_out, 0, L, 24)


def line_fitting(c: Cfg):
    """Bulkhead fitting (hex AF7 + nipple), threaded into a casing boss."""
    return (Manifold.cylinder(4, 7 / np.sqrt(3), 7 / np.sqrt(3), 6) + cyl(2.2, 4, 9, 32)) - cyl(1.55, -1, 10, 24)


def glow_plug(c: Cfg):
    return cyl(3.15, 0, 12.1, 32) + Manifold.cylinder(4, 8 / np.sqrt(3), 8 / np.sqrt(3), 6).translate([0, 0, 12.1]) + cyl(1.5, 16.1, 22, 24)


def ngv_ring(c: Cfg):
    """19 cambered/twisted vanes (free vortex, exit ~63 deg) between inner and outer rings;
    the outer ring carries the turbine shroud and the rear flange; the inner web pilots the tunnel."""
    zl, zt = c.z_ngv_le, c.z_ngv_te
    inner = Polygon([(18.5, zl - 4), (c.rh, zl - 4), (c.rh, zt), (18.5, zt)]).union(box(c.housing_r + 0.05, c.z_b2 - 1, 18.5, c.z_b2 + 1))
    ro = c.ngv_ro
    outer = Polygon([(c.rt_s, zl - 4), (ro, zl - 4), (ro, zt), (65, zt), (65, zt + c.fl), (ro, zt + c.fl),
                     (ro, c.z_tte + 1.15), (c.rt_s, c.z_tte + 1.15)])
    body = revolve(inner) + revolve(outer)
    rm = c.rm
    a_out = lambda r: np.degrees(np.arctan(c.Cth2 * rm / r / c.Cx))
    vane = axial_blade(np.linspace(c.rh - 0.3, c.rt_s + 0.3, 8), zl, c.ngv_cx - 0.2, lambda r: 0.0, a_out,
                       lambda r: 1.8, 0.4, n=28)
    body += polar(vane, c.Zn)
    body -= polar(cyl(1.7, zt - 1, zt + 3, 24).translate([62.3, 0, 0]), 8, 0)
    return body


def turbine_wheel(c: Cfg):
    """27 twisted blades (free vortex: inlet ~25 deg, exit ~-57 deg at mean) on a 12 mm disc."""
    zt = c.z_t
    z0, z1 = c.z_tle - 0.15, c.z_tte + 0.15
    rb = c.rs + 0.005
    prof = [(rb, c.z_b2 + c.bw / 2), (6.5, c.z_b2 + c.bw / 2), (6.5, zt - 6), (10, zt - 6), (18, zt - 5), (18, z0),
            (c.rh, z0), (c.rh, z1), (18, z1), (18, zt + 5), (10, zt + 6), (rb, zt + 6)]
    disc = revolve(prof)
    rm, U, Cx = c.rm, c.U, c.Cx
    b_in = lambda r: np.degrees(np.arctan((c.Cth2 * rm / r - U * r / rm) / Cx))
    b_out = lambda r: np.degrees(np.arctan((c.Cth3 * rm / r - U * r / rm) / Cx))
    tmax = lambda r: 2.0 - 1.0 * (r - c.rh) / (c.rt - c.rh)
    blade = axial_blade(np.linspace(c.rh - 0.4, c.rt, 10), c.z_tle, c.chord, b_in, b_out, tmax, 0.35, n=28)
    return disc + polar(blade, c.Zr)


def nozzle(c: Cfg):
    z0 = c.z_tte + 1.15
    zs = z0 + 24
    t = np.linspace(0, 1, 30)
    conv = [(c.rt_s + (c.r9 - c.rt_s) * 0.5 * (1 - np.cos(np.pi * u)), zs + (c.z_noz_exit - zs) * u) for u in t]
    gas = [(c.rt_s, z0)] + conv
    r0, r1, zf = c.ngv_ro + 0.05, c.ngv_ro + 0.85, c.z_ngv_te + c.fl
    prof = sheet(gas, 0.8, (60, 150)).union(box(r0, zf, r1, z0 + 0.8)).union(
        box(c.rt_s, z0, r1, z0 + 0.8)).union(box(r0, zf, 65, zf + c.fl))
    body = revolve(prof)
    body -= polar(cyl(1.7, c.z_ngv_te + 1, c.z_ngv_te + 5, 24).translate([62.3, 0, 0]), 8, 0)
    body += radial(cyl(3.5, 0, 41 - 35.3, 32), 35.3, 0, 142.0)          # EGT thermocouple boss
    body -= radial(cyl(0.8, 0, 14, 16), 30, 0, 142.0)
    return body, gas


def tail_cone(c: Cfg):
    z0 = c.z_tte + 1.15
    O = Polygon([(0, z0), (20.6, z0), (20.6, z0 + 3), (2.5, z0 + 38), (0, z0 + 39)])
    Cv = Polygon([(0, z0 - 1), (19.8, z0 - 1), (19.8, z0 + 3.2), (1.7, z0 + 37.2), (0, z0 + 38.2)])
    shell = revolve(O.difference(Cv))
    strut = Manifold.cube([34.8 - 10, 1.2, 16]).translate([10, -0.6, z0 + 6])
    return shell + (polar(strut, 4, 45) - revolve(Cv))


def mounting_band(c: Cfg):
    """Split clamp band (Al) with clamp ears on top (+x) and a foot tab underneath (-x). Local z = -5..5."""
    ring = tube(c.rc_out + 0.06, 62.5, -5, 5, SEG)
    ears = Manifold.cube([8.5, 15, 10]).translate([60.5, -7.5, -5])
    web = Manifold.cube([7, 16, 10]).translate([-67, -8, -5])
    tab = Manifold.cube([6, 32, 10]).translate([-73, -16, -5])
    m = ring + ears + web + tab
    m -= Manifold.cube([16, 3, 12]).translate([55, -1.5, -6])
    m -= cyl(1.7, -10, 10, 24).rotate([90, 0, 0]).translate([65.5, 0, 0])
    m -= tube(0, c.rc_out + 0.06, -6, 6, SEG)
    for y in (-12.5, 12.5):
        m -= cyl(2.2, 0, 10, 24).rotate([0, 90, 0]).translate([-75, y, 0])
    return m


def stand_pillar(c: Cfg):
    m = Manifold.cube([37, 32, 20], center=True)
    for y in (-12.5, 12.5):
        m -= cyl(2.0, 0, 12, 24).rotate([0, -90, 0]).translate([18.6, y, 0])
    for y in (-8, 8):
        m -= cyl(2.0, 0, 10, 24).rotate([0, 90, 0]).translate([-18.6, y, 0])
    return m


def stand_base(c: Cfg, zc):
    m = Manifold.cube([8, 160, 260], center=True)
    for z in zc:
        for y in (-8, 8):
            m -= cyl(2.2, -10, 10, 24).rotate([0, 90, 0]).translate([0, y, z])
    for y in (-65, 65):
        for z in (-115, 115):
            m -= cyl(3.2, -10, 10, 24).rotate([0, 90, 0]).translate([0, y, z])
    return m


def egt_thermocouple(c: Cfg):
    """K-type, Ø1.5 Inconel-sheathed probe with compression fitting (bought). Tip at z = 0."""
    return cyl(0.75, 0, 15, 16) + Manifold.cylinder(4, 7 / np.sqrt(3), 7 / np.sqrt(3), 6).translate([0, 0, 15]) + cyl(1.5, 19, 29, 16)


# --------------------------------------------------------------------------- materials and part data
MATS = {  # key: (label, density g/mm3, colour)
    "Al2618": ("Aluminum 2618-T61", 2.76e-3, "#cfd8e3"),
    "Al6061": ("Aluminum 6061-T6", 2.70e-3, "#9fb4c9"),
    "SS174": ("Stainless 17-4PH H1025", 7.80e-3, "#5f6f80"),
    "SS304": ("Stainless 304", 8.00e-3, "#c4c8cc"),
    "SS310": ("Stainless 310 (or Inconel 625)", 7.90e-3, "#d9a066"),
    "SS321": ("Stainless 321", 7.92e-3, "#a3835f"),
    "IN718": ("Inconel 718", 8.19e-3, "#7ba37a"),
    "IN713C": ("Inconel 713C (cast)", 7.91e-3, "#4e79a7"),
    "BRG": ("Hybrid bearing (52100 races, Si3N4 balls)", 7.0e-3, "#333333"),
    "FKM": ("Viton (FKM) 75 Shore A", 1.85e-3, "#8c3b3b"),
    "SPR": ("Stainless 302 spring wire", 7.9e-3, "#e8c547"),
    "A2": ("Stainless A2-70 fasteners", 7.9e-3, "#6b6b80"),
    "A286": ("A286 heat-resisting fasteners", 7.94e-3, "#b07aa1"),
    "BUY": ("Bought-in (glow plug, thermocouple)", 7.6e-3, "#e15759"),
}

PART_INFO = {  # name: (material key, process, notes)
    "bellmouth": ("Al6061", "CNC lathe from Ø85 bar; 3 starter bosses milled", "Elliptical lip; M3 bosses for a starter bracket"),
    "front_cover": ("Al6061", "CNC lathe (shroud contour turned to the blade-tip offset)", "Compressor shroud + diffuser front wall + front flange"),
    "impeller": ("Al2618", "5-axis milled from forged bar; balanced", "7 main + 7 splitter blades, 30 deg backsweep"),
    "compressor_nut": ("SS174", "Lathe + hex mill", "M8 x 1 left-hand (tightens against rotation); starter cone seat"),
    "diffuser": ("Al6061", "CNC lathe + 4-axis mill (vanes)", "18 wedge vanes + 24 deswirl vanes, one piece"),
    "shaft": ("SS174", "Turned, aged H1025, ground at bearing seats", "Ø8 at bearings, Ø10 between; M8 x 1 ends"),
    "bearing_608": ("BRG", "Buy: 608 hybrid ceramic, C3, high-speed cage", "8 x 22 x 7; oil-mist lubricated"),
    "bearing_sleeve_front": ("SS174", "Lathe; ground OD/ID", "Soft mount: 1 mm wall, rear lip locates the outer race"),
    "bearing_sleeve_rear": ("SS174", "Lathe; ground OD/ID", "Soft mount: plain sleeve, outer race slides (preload)"),
    "oring_24x1.5": ("FKM", "Buy: Viton O-ring 24 x 1.5", "2 per bearing; ~0.75 MN/m each -> ~1.5 MN/m per bearing"),
    "anti_rotation_pin": ("SS174", "Buy: Ø1.5 dowel, cut to length", "Pressed into tunnel; loose in a Ø2 sleeve hole"),
    "spacer_tube": ("SS174", "Lathe; faces ground parallel", "Clamps the two inner races"),
    "preload_spring": ("SPR", "Buy/wind: Ø20.4 x 0.8 wire compression spring", "Axial preload ~20-30 N on the rear outer race"),
    "shaft_tunnel": ("SS174", "Lathe + drill; grooves for 4 O-rings", "Front flange bolted to diffuser; rear spigot floats in NGV web"),
    "outer_casing": ("SS304", "Roll + TIG-seam 1 mm sheet; flanges & bosses welded", "Flanges M3 x 8 on Ø124.6"),
    "liner_outer": ("SS310", "Laser-cut 0.5 mm sheet, rolled, TIG-welded; dome welded", "Holes: primary/secondary/dilution + glow plug"),
    "liner_inner": ("SS310", "Laser-cut 0.5 mm sheet, rolled, welded", "Holes: primary/secondary/dilution"),
    "vaporizer": ("SS310", "Bend Ø5 x 0.5 tube over a R5 former", "J-tube; brazed/welded into the dome"),
    "fuel_manifold": ("SS304", "Ø3 x 0.5 tube rolled to Ø68 ring, silver-brazed", "Fuel ring feeding 8 needles"),
    "fuel_needle": ("SS304", "Buy: 21 G hypodermic tube, cut", "One per vaporizer"),
    "fuel_line": ("SS304", "Ø3 x 0.5 tube", "Manifold to casing fitting"),
    "oil_line": ("SS304", "Ø2.5 x 0.5 tube", "Casing fitting to the front bearing housing"),
    "line_fitting": ("SS304", "Lathe + hex", "Bulkhead fitting in casing boss (fuel and oil)"),
    "glow_plug": ("BUY", "Buy: model-engine glow plug (1/4-32)", "Igniter; start with propane, then kerosene"),
    "ngv_ring": ("IN718", "Rings turned; vanes wire-EDM + vacuum brazed (or investment cast)", "19 vanes; shroud + rear flange"),
    "turbine_wheel": ("IN713C", "Investment-cast blank, finish-turned, balanced", "27 blades, unshrouded"),
    "turbine_nut": ("IN718", "Lathe + hex", "M8 x 1; IN718 for strength at ~600 C"),
    "nozzle": ("SS321", "Spun / rolled 0.8 mm sheet, 1.5 mm flange welded", "Convergent, 0.8 wall; EGT boss"),
    "tail_cone": ("SS321", "Spun 0.8 mm sheet + 4 welded struts", "Struts welded to nozzle wall"),
    "egt_thermocouple": ("BUY", "Buy: K-type Ø1.5 probe + compression fitting", "Exhaust-gas temperature"),
    "screw_M3x6": ("A2", "Buy: ISO 4762 M3 x 6", "Bellmouth (6), tunnel flange (6)"),
    "screw_M3x10": ("A2", "Buy: ISO 4762 M3 x 10", "Diffuser vanes (6), front flange (8)"),
    "nut_M3": ("A2", "Buy: ISO 4032 M3", "Front flange (8), band clamps (2)"),
    "screw_M3x12_A286": ("A286", "Buy: M3 x 12 A286 / Inconel", "Hot rear flange (8)"),
    "nut_M3_A286": ("A286", "Buy: M3 A286 / Inconel", "Hot rear flange (8)"),
    "screw_M3x16": ("A2", "Buy: ISO 4762 M3 x 16", "Mounting-band clamps"),
    "screw_M4x16": ("A2", "Buy: ISO 4762 M4 x 16", "Stand: tabs to pillars, pillars to base"),
    "mounting_band": ("Al6061", "Laser/waterjet from 10 mm plate, bored, slit", "Clamps the casing to the stand"),
    "stand_pillar": ("Al6061", "Saw + drill from 20 x 32 bar", "Test stand"),
    "stand_base": ("Al6061", "Saw + drill 8 mm plate", "Test stand; clamp to a thrust sled"),
}
STAND = {"mounting_band", "stand_pillar", "stand_base", "screw_M4x16", "screw_M3x16"}
ROTOR = {"impeller", "compressor_nut", "shaft", "spacer_tube", "turbine_wheel", "turbine_nut"}


def mat(name):
    return MATS[PART_INFO[name][0]]


# --------------------------------------------------------------------------- build
def build(c: Cfg = C):
    parts = {}
    placed = []                                 # (name, Manifold placed, tag)

    def put(name, m, tag=None):
        placed.append((name, m, tag or name))

    bm, _ = bellmouth(c)
    parts["bellmouth"] = bm.translate([0, 0, 6])          # own origin = flange face
    put("bellmouth", bm)
    fc, _ = front_cover(c)
    parts["front_cover"] = fc.translate([0, 0, -c.z_fw])
    put("front_cover", fc)
    imp = impeller(c)
    parts["impeller"] = imp
    put("impeller", imp)
    cn = compressor_nut(c)
    parts["compressor_nut"] = cn
    put("compressor_nut", cn.translate([0, 0, -7.0]))
    dif = diffuser(c)
    parts["diffuser"] = dif.translate([0, 0, -c.z_fw])
    put("diffuser", dif)
    sh = shaft(c)
    parts["shaft"] = sh.translate([0, 0, 6])
    put("shaft", sh)
    br = bearing_608(c)
    parts["bearing_608"] = br
    put("bearing_608", br.translate([0, 0, c.z_b1 - c.bw / 2]), "bearing_608@front")
    put("bearing_608", br.translate([0, 0, c.z_b2 - c.bw / 2]), "bearing_608@rear")
    sf, sr = bearing_sleeve(c, True), bearing_sleeve(c, False)
    parts["bearing_sleeve_front"], parts["bearing_sleeve_rear"] = sf, sr
    put("bearing_sleeve_front", sf.translate([0, 0, c.z_b1 - c.bw / 2]))
    put("bearing_sleeve_rear", sr.translate([0, 0, c.z_b2 - c.bw / 2]))
    tun, grooves = shaft_tunnel(c)
    parts["shaft_tunnel"] = tun.translate([0, 0, -(c.z_back + 1)])
    put("shaft_tunnel", tun)
    orr = oring(c)
    parts["oring_24x1.5"] = orr
    for k, zg in enumerate(grooves):
        put("oring_24x1.5", orr.translate([0, 0, zg]), f"oring_24x1.5@{'front' if k < 2 else 'rear'}")
    pin = anti_rotation_pin(c)
    parts["anti_rotation_pin"] = pin
    put("anti_rotation_pin", radial(pin, 11.4, 0, c.z_b1 - c.bw / 2 + PIN_DZ), "anti_rotation_pin@front")
    put("anti_rotation_pin", radial(pin, 11.4, 0, c.z_b2 - c.bw / 2 + PIN_DZ), "anti_rotation_pin@rear")
    sp = spacer_tube(c)
    parts["spacer_tube"] = sp
    put("spacer_tube", sp.translate([0, 0, c.z_b1 + c.bw / 2]))
    z_seat = c.z_b2 - 12.0
    spr = preload_spring(c, c.z_b2 - c.bw / 2 - z_seat)
    parts["preload_spring"] = spr
    put("preload_spring", spr.translate([0, 0, z_seat]))
    cas = casing(c)
    parts["outer_casing"] = cas.translate([0, 0, -c.z_fw])
    put("outer_casing", cas)
    lo, li = liner_outer(c), liner_inner(c)
    parts["liner_outer"] = lo.translate([0, 0, -c.z_dome])
    parts["liner_inner"] = li.translate([0, 0, -c.z_dome])
    put("liner_outer", lo)
    put("liner_inner", li)
    vap = vaporizer(c)
    parts["vaporizer"] = vap
    for k in range(8):
        put("vaporizer", vap.translate([34, 0, c.z_dome - 2]).rotate([0, 0, 45 * k]))
    fm = fuel_manifold(c)
    parts["fuel_manifold"] = fm
    put("fuel_manifold", fm.translate([0, 0, 34.0]))
    nd = fuel_needle(c)
    parts["fuel_needle"] = nd
    for k in range(8):
        put("fuel_needle", nd.translate([34, 0, 35.45]).rotate([0, 0, 45 * k]))
    fl = line_tube(1.5, 1.0, 71 - 35.55)
    parts["fuel_line"] = fl
    put("fuel_line", radial(fl, 35.55, 112.5, 34.0))
    ol = line_tube(1.25, 0.75, 71 - (c.housing_r + 0.05))
    parts["oil_line"] = ol
    put("oil_line", radial(ol, c.housing_r + 0.05, 270, 30.3))
    fit = line_fitting(c)
    parts["line_fitting"] = fit
    put("line_fitting", radial(fit, 62.5, 112.5, 34.0), "line_fitting@fuel")
    put("line_fitting", radial(fit, 62.5, 270, 30.3), "line_fitting@oil")
    gp = glow_plug(c)
    parts["glow_plug"] = gp
    put("glow_plug", radial(gp, c.liner_out - 2.5, 22.5, 46.0))
    ngv = ngv_ring(c)
    parts["ngv_ring"] = ngv.translate([0, 0, -c.z_ngv_le])
    put("ngv_ring", ngv)
    tw = turbine_wheel(c)
    parts["turbine_wheel"] = tw.translate([0, 0, -c.z_t])
    put("turbine_wheel", tw)
    tn = turbine_nut(c)
    parts["turbine_nut"] = tn
    put("turbine_nut", tn.translate([0, 0, c.z_t + 6]))
    nz, _ = nozzle(c)
    parts["nozzle"] = nz.translate([0, 0, -(c.z_ngv_te + c.fl)])
    put("nozzle", nz)
    tc = tail_cone(c)
    parts["tail_cone"] = tc.translate([0, 0, -(c.z_tte + 1.15)])
    put("tail_cone", tc)
    tcp = egt_thermocouple(c)
    parts["egt_thermocouple"] = tcp
    put("egt_thermocouple", radial(tcp, 26.0, 0, 142.0))
    # fasteners
    s6, s10, s12, s16 = screw(6), screw(10), screw(12), screw(16)
    s4 = screw(16, 4.0, 7.0, 4.0)
    n3 = nut()
    parts.update({"screw_M3x6": s6, "screw_M3x10": s10, "screw_M3x12_A286": s12, "screw_M3x16": s16,
                  "screw_M4x16": s4, "nut_M3": n3, "nut_M3_A286": n3})
    for k in range(6):
        put("screw_M3x6", axial(s6, 29.2, 60 * k, -9.0), "screw_M3x6@bellmouth")
        put("screw_M3x6", axial(s6, 20.0, 60 * k, 28.5, flip=True), "screw_M3x6@tunnel")
    for x, y in diffuser_screw_xy(c):
        put("screw_M3x10", s10.translate([x, y, c.z_fw - 3.5]), "screw_M3x10@diffuser")
    for k in range(8):
        put("screw_M3x10", axial(s10, 62.3, 45 * k, c.z_fw - 3.5), "screw_M3x10@front_flange")
        put("nut_M3", axial(n3, 62.3, 45 * k, c.z_fw + c.fl), "nut_M3@front_flange")
        put("screw_M3x12_A286", axial(s12, 62.3, 45 * k, c.z_ngv_te - c.fl), "screw_M3x12_A286@rear_flange")
        put("nut_M3_A286", axial(n3, 62.3, 45 * k, c.z_ngv_te + 2 * c.fl), "nut_M3_A286@rear_flange")
    # test stand: bands, pillars, base (stand on the -x side)
    band = mounting_band(c)
    parts["mounting_band"] = band
    pil = stand_pillar(c)
    parts["stand_pillar"] = pil
    zc = (65.0, 100.0)
    parts["stand_base"] = stand_base(c, [z - 85.0 for z in zc])
    for z in zc:
        put("mounting_band", band.translate([0, 0, z]))
        put("screw_M3x16", s16.rotate([-90, 0, 0]).translate([65.5, -7.5, z]), "screw_M3x16@band")
        put("nut_M3", n3.rotate([-90, 0, 0]).translate([65.5, 7.5, z]), "nut_M3@band")
        put("stand_pillar", pil.translate([-91.5, 0, z]))
        for y in (-12.5, 12.5):
            put("screw_M4x16", s4.rotate([0, -90, 0]).translate([-67, y, z]), "screw_M4x16@tab")
        for y in (-8, 8):
            put("screw_M4x16", s4.rotate([0, 90, 0]).translate([-118, y, z]), "screw_M4x16@base")
    put("stand_base", parts["stand_base"].translate([-114, 0, 85.0]))
    return parts, placed


# --------------------------------------------------------------------------- checks
def interference(placed, tol=0.5):
    """Volume (mm3) of every overlapping pair of placed parts; returns pairs above tol."""
    boxes = [m.bounding_box() for _, m, _ in placed]
    clashes = []
    for i in range(len(placed)):
        for j in range(i + 1, len(placed)):
            a, b = boxes[i], boxes[j]
            if any(a[k] > b[k + 3] or b[k] > a[k + 3] for k in range(3)):
                continue
            v = (placed[i][1] ^ placed[j][1]).volume()
            if v > tol:
                clashes.append((placed[i][2], placed[j][2], round(v, 2)))
    return clashes


def rz_segments(tms):
    """Unique mesh edges projected into the meridional (r, z) plane."""
    import shapely
    segs = []
    for tm in tms:
        v = tm.vertices
        rz = np.c_[np.hypot(v[:, 0], v[:, 1]), v[:, 2]]
        e = tm.edges_unique
        segs.append(np.stack([rz[e[:, 0]], rz[e[:, 1]]], axis=1))
    s = np.concatenate(segs)
    s = np.unique(np.round(s, 3), axis=0)
    return shapely.linestrings(s), s


def clearances(placed):
    """Running clearance of every rotating part to every stationary part, from their swept
    meridional footprints (exact for axisymmetric stators, conservative for vaned ones)."""
    from shapely import STRtree
    groups = {}
    for name, m, tag in placed:
        if name in STAND or name.startswith("bearing_608"):
            continue
        groups.setdefault(name, []).append(to_trimesh(m))
    rot = {n: rz_segments(t) for n, t in groups.items() if n in ROTOR}
    sta = {}
    for n, t in groups.items():
        if n in ROTOR:
            continue
        geoms, s = rz_segments(t)
        sta[n] = (STRtree(geoms), geoms, s)
    out = []
    for rn, (rg, rs) in rot.items():
        lo = rs.reshape(-1, 2).min(0) - 3; hi = rs.reshape(-1, 2).max(0) + 3
        for sn, (tree, sg, ss) in sta.items():
            sl = ss.reshape(-1, 2)
            if (sl[:, 0].max() < lo[0] or sl[:, 0].min() > hi[0] or sl[:, 1].max() < lo[1] or sl[:, 1].min() > hi[1]):
                continue
            (ia, ib), d = tree.query_nearest(rg, return_distance=True, all_matches=False)
            k = int(np.argmin(d))
            p = rs[ia[k]].mean(0)
            out.append((rn, sn, float(d[k]), p))
    out = sorted(out, key=lambda x: x[2])
    # named checks on part of a stator (filter on the stator segment mid-points)
    c = C
    named = [("turbine_wheel", "ngv_ring", "NGV trailing edge to turbine blade leading edge (axial)",
              lambda r, z: (z < c.z_ngv_te + 0.05) & (r > c.rh) & (r < c.rt_s), 0.8),
             ("turbine_wheel", "ngv_ring", "turbine blade tip to shroud (radial)",
              lambda r, z: (z > c.z_tle) & (r < c.rt_s + 0.1), c.clear_t - 0.05),
             ("impeller", "front_cover", "impeller blade tip to shroud",
              lambda r, z: z < c.z_fw + 0.05, 0.25),
             ("impeller", "diffuser", "impeller exit to diffuser vane leading edge (radial)",
              lambda r, z: (z < c.z_hub_exit - 0.1) & (r > c.r2), 1.5)]
    special = []
    for rn, sn, label, filt, req in named:
        rg, rs = rot[rn]
        _, _, ss = sta[sn]
        mid = ss.mean(1)
        keep = filt(mid[:, 0], mid[:, 1])
        import shapely
        tree = STRtree(shapely.linestrings(ss[keep]))
        (ia, ib), d = tree.query_nearest(rg, return_distance=True, all_matches=False)
        k = int(np.argmin(d))
        special.append((label, rn, sn, float(d[k]), req))
    return out, special


# --------------------------------------------------------------------------- z-buffer renderer
def render_zbuffer(items, view=(0.55, 1.0, -0.35), up=(1, 0, 0), width=1600, height=None, ss=2, margin=0.03,
                   outline=True, bounds=None, max_edge=4.0):
    """Orthographic, shaded render of [(trimesh, rgb), ...] with a real depth buffer.
    Returns (image HxWx3 float, project(points)->pixel xy)."""
    c = np.asarray(view, float); c /= np.linalg.norm(c)
    u = np.asarray(up, float); u = u - (u @ c) * c; u /= np.linalg.norm(u)
    rgt = np.cross(u, c)
    Rm = np.stack([rgt, u, c])
    if max_edge:
        items = [(trimesh.Trimesh(*trimesh.remesh.subdivide_to_size(tm.vertices, tm.faces, max_edge, max_iter=12),
                                  process=False), rgb) for tm, rgb in items]
    V = [tm.vertices @ Rm.T for tm, _ in items]
    allv = np.concatenate(V) if bounds is None else np.asarray(bounds) @ Rm.T
    lo, hi = allv.min(0), allv.max(0)
    if height is None:
        height = int(width * (hi[1] - lo[1]) / (hi[0] - lo[0]) * (1 + 2 * margin) / (1 + 2 * margin)) + 2 * int(margin * width)
    W, H = width * ss, height * ss
    s = min(W * (1 - 2 * margin) / (hi[0] - lo[0]), H * (1 - 2 * margin) / (hi[1] - lo[1]))
    ox = (W - s * (hi[0] - lo[0])) / 2 - s * lo[0]
    oy = (H - s * (hi[1] - lo[1])) / 2 + s * hi[1]

    def proj(P):
        q = np.asarray(P, float) @ Rm.T
        return np.c_[q[:, 0] * s + ox, oy - q[:, 1] * s] / ss

    L = np.array([-0.35, 0.55, 0.75]); L /= np.linalg.norm(L)
    zbuf = np.full(W * H, -np.inf)
    fbuf = np.full(W * H, -1, np.int64)
    cols, nrm, pid = [], [], []
    off = 0
    for ii, ((tm, rgb), v) in enumerate(zip(items, V)):
        F = tm.faces
        T = v[F]
        X = T[:, :, 0] * s + ox
        Y = oy - T[:, :, 1] * s
        D = T[:, :, 2]
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        nn = np.linalg.norm(n, axis=1); n = n / np.maximum(nn, 1e-12)[:, None]
        nd = np.abs(n @ L)
        hv = L + np.array([0, 0, 1.0]); hv /= np.linalg.norm(hv)
        spec = np.abs(n @ hv) ** 30
        shade = 0.38 + 0.62 * nd
        base = np.asarray(rgb, float)
        cols.append(np.clip(base[None] * shade[:, None] + 0.18 * spec[:, None], 0, 1))
        nrm.append(n); pid.append(np.full(len(F), ii))
        x0 = np.floor(X.min(1)).astype(int); x1 = np.ceil(X.max(1)).astype(int)
        y0 = np.floor(Y.min(1)).astype(int); y1 = np.ceil(Y.max(1)).astype(int)
        bw = np.maximum(x1 - x0, 1); bh = np.maximum(y1 - y0, 1)
        kw = (2 ** np.ceil(np.log2(bw))).astype(int); kh = (2 ** np.ceil(np.log2(bh))).astype(int)
        area = (X[:, 1] - X[:, 0]) * (Y[:, 2] - Y[:, 0]) - (X[:, 2] - X[:, 0]) * (Y[:, 1] - Y[:, 0])
        ok = (np.abs(area) > 1e-9) & (x1 >= 0) & (y1 >= 0) & (x0 < W) & (y0 < H)
        keys = kw.astype(np.int64) * 100000 + kh
        for key in np.unique(keys[ok]):
            sel = np.where(ok & (keys == key))[0]
            kx, ky = int(key // 100000), int(key % 100000)
            chunk = max(1, int(1e6 // (kx * ky)))
            for a0 in range(0, len(sel), chunk):
                f = sel[a0:a0 + chunk]
                gx = x0[f][:, None, None] + np.arange(kx)[None, None, :]
                gy = y0[f][:, None, None] + np.arange(ky)[None, :, None]
                px, py = gx + 0.5, gy + 0.5
                Xf, Yf = X[f][:, :, None, None], Y[f][:, :, None, None]
                ar = area[f][:, None, None]
                w0 = ((Xf[:, 1] - px) * (Yf[:, 2] - py) - (Xf[:, 2] - px) * (Yf[:, 1] - py)) / ar
                w1 = ((Xf[:, 2] - px) * (Yf[:, 0] - py) - (Xf[:, 0] - px) * (Yf[:, 2] - py)) / ar
                w2 = 1 - w0 - w1
                inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6) & (gx >= 0) & (gx < W) & (gy >= 0) & (gy < H)
                fi, yi, xi = np.nonzero(inside)
                if not len(fi):
                    continue
                Df = D[f]
                dd = w0[fi, yi, xi] * Df[fi, 0] + w1[fi, yi, xi] * Df[fi, 1] + w2[fi, yi, xi] * Df[fi, 2]
                pix = gy[fi, yi, 0] * W + gx[fi, 0, xi]
                order = np.lexsort((-dd, pix))
                pix, dd, fsel = pix[order], dd[order], f[fi[order]]
                first = np.r_[True, pix[1:] != pix[:-1]]
                pix, dd, fsel = pix[first], dd[first], fsel[first]
                better = dd > zbuf[pix]
                zbuf[pix[better]] = dd[better]
                fbuf[pix[better]] = fsel[better] + off
        off += len(F)
    cols = np.concatenate(cols); nrm = np.concatenate(nrm); pid = np.concatenate(pid)
    img = np.ones((W * H, 3))
    hit = fbuf >= 0
    img[hit] = cols[fbuf[hit]]
    img = img.reshape(H, W, 3)
    if outline:
        fb = fbuf.reshape(H, W); zb = zbuf.reshape(H, W)
        P = np.where(fb >= 0, pid[np.maximum(fb, 0)], -1)
        N = np.where((fb >= 0)[..., None], nrm[np.maximum(fb, 0)], 0)
        edge = np.zeros((H, W), bool)
        for dy, dx in ((0, 1), (1, 0)):
            a = (slice(0, H - dy), slice(0, W - dx)); b = (slice(dy, H), slice(dx, W))
            e = (P[a] != P[b])
            e |= (np.abs(np.nan_to_num(zb[a], neginf=-1e6) - np.nan_to_num(zb[b], neginf=-1e6)) > 1.2)
            e |= (np.sum(N[a] * N[b], -1) < 0.6) & (P[a] >= 0)
            edge[a] |= e
        img[edge] = img[edge] * 0.25
    img = img.reshape(height, ss, width, ss, 3).mean((1, 3))
    return img, proj


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


# --------------------------------------------------------------------------- outputs
def decimate(tm, max_faces):
    if len(tm.faces) <= max_faces:
        return tm
    import fast_simplification
    v, f = fast_simplification.simplify(tm.vertices.astype(np.float32), tm.faces.astype(np.int64),
                                        target_reduction=1 - max_faces / len(tm.faces))
    return trimesh.Trimesh(v, f, process=False)


def decimate_set(tms, budget=90000, floor=600):
    """Decimate a list of meshes so the total stays under `budget` faces; big parts give up most."""
    n = np.array([len(t.faces) for t in tms], float)
    if n.sum() <= budget:
        return tms
    w = n ** 0.6
    lo, hi = 0.0, budget / w.sum() * 50
    for _ in range(40):                                  # bisect the scale so sum(min(n, max(floor, s*w))) = budget
        s = 0.5 * (lo + hi)
        tot = np.minimum(n, np.maximum(floor, s * w)).sum()
        lo, hi = (s, hi) if tot < budget else (lo, s)
    tgt = np.minimum(n, np.maximum(floor, lo * w)).astype(int)
    return [decimate(t, k) for t, k in zip(tms, tgt)]


def write_outputs(c: Cfg = C):
    t0 = time.time()
    parts, placed = build(c)
    t_build = time.time() - t0
    stl = OUT / "stl"; stl.mkdir(parents=True, exist_ok=True)
    counts = {}
    for name, _, _ in placed:
        counts[name] = counts.get(name, 0) + 1
    rows = []
    for name, m in parts.items():
        tm = to_trimesh(m)
        assert tm.is_watertight, name
        tm.export(stl / f"{name}.stl")
        label, rho, _ = mat(name)
        vol = m.volume()
        ext = tm.bounds[1] - tm.bounds[0]
        q = counts.get(name, 0)
        rows.append({"part": name, "qty": q, "material": label, "process": PART_INFO[name][1],
                     "envelope_mm": " x ".join(f"{e:.1f}" for e in ext), "volume_mm3": round(vol, 1),
                     "mass_each_g": round(vol * rho, 2), "mass_total_g": round(vol * rho * q, 2),
                     "notes": PART_INFO[name][2]})
    with open(OUT / f"bom_{NAME}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    t1 = time.time()
    clashes = interference(placed)
    clear, special = clearances(placed)
    write_checks(c, placed, clashes, clear, special)
    t_check = time.time() - t1
    # assembly STL (decimated per part to keep the file small)
    scene = decimate_set([to_trimesh(m) for _, m, _ in placed], 95000)
    trimesh.util.concatenate(scene).export(OUT / f"assembly_{NAME}.stl")
    viewer(placed)
    render(c, placed)
    engine = sum(r["mass_total_g"] for r in rows if r["part"] not in STAND)
    rotor = sum(r["mass_total_g"] for r in rows if r["part"] in ROTOR)
    return rows, engine, rotor, clashes, (clear, special), (t_build, t_check, time.time() - t0)


def write_checks(c, placed, clashes, clear, special):
    req = {("impeller", "front_cover"): (0.25, "impeller blade tip to shroud"),
           ("turbine_wheel", "ngv_ring"): (0.25, "turbine tip to shroud / blade LE to NGV TE"),
           ("impeller", "diffuser"): (0.4, "impeller rim/back face to diffuser"),
           ("turbine_wheel", "tail_cone"): (0.5, "turbine disc to tail cone"),
           ("impeller", "shaft_tunnel"): (0.5, "impeller back face to tunnel"),
           ("turbine_wheel", "shaft_tunnel"): (0.5, "turbine boss to tunnel")}
    with open(OUT / f"interference_{NAME}.txt", "w") as f:
        f.write(f"TJ-110 geometry checks (design model, not measured)\n\n")
        f.write(f"1. Pairwise overlap check of {len(placed)} placed parts (boolean intersection, tolerance 0.5 mm3)\n")
        f.write("\n".join(f"   {a} x {b}: {v} mm3" for a, b, v in clashes) or "   No interferences found.")
        f.write("\n   (O-rings are modelled at their installed 10 % squeeze, so they only touch the sleeve and groove.)\n\n")
        f.write("2. Running clearances: rotating parts vs stationary parts, from swept meridional (r, z) footprints.\n"
                "   Exact for axisymmetric stators; for vaned stators it is the minimum over all rotor angles.\n"
                "   Cold, static dimensions: thermal growth and centrifugal growth are NOT included.\n\n")
        f.write(f"   {'rotor part':<16}{'stator part':<22}{'min gap (mm)':>13}   at r, z (mm)    requirement\n")
        for rn, sn, d, p in clear:
            if d > 6:
                continue
            rq = req.get((rn, sn))
            tag = f"{'PASS' if d >= rq[0] else 'FAIL'} >= {rq[0]} ({rq[1]})" if rq else ""
            f.write(f"   {rn:<16}{sn:<22}{d:>13.2f}   {p[0]:6.1f}, {p[1]:6.1f}   {tag}\n")
        f.write("\n   Key running clearances (cold):\n")
        for label, rn, sn, d, req in special:
            f.write(f"   {label:<58}{d:6.2f} mm   {'PASS' if d >= req else 'FAIL'} (>= {req:.2f})\n")
        f.write("\n3. Soft bearing mounts: radial travel of each sleeve in the tunnel bore before metal contact = "
                f"{c.tun_bore - c.sl_ro:.2f} mm (snubber), O-ring squeeze "
                f"{(1 - (c.groove_r - c.sl_ro) / c.or_cs) * 100:.0f} %, target support stiffness "
                f"{c.k_bearing / 1e6:.1f} MN/m per bearing.\n")


def viewer(placed):
    import plotly.graph_objects as go
    by = {}
    dec = decimate_set([to_trimesh(m) for _, m, _ in placed], 110000)
    for (name, _, _), tm in zip(placed, dec):
        by.setdefault(name, []).append(tm)
    fig = go.Figure()
    for name, ms in by.items():
        tm = trimesh.util.concatenate(ms)
        v, f = tm.vertices, tm.faces
        fig.add_trace(go.Mesh3d(x=v[:, 2], y=v[:, 1], z=v[:, 0], i=f[:, 0], j=f[:, 1], k=f[:, 2], name=name,
                                color=mat(name)[2], opacity=0.3 if name in ("outer_casing", "nozzle", "front_cover") else 1.0,
                                showlegend=True, flatshading=False))
    fig.update_layout(title="TJ-110 micro-turbojet (design study, not built): click legend entries to hide parts",
                      scene=dict(aspectmode="data", xaxis_title="z (mm), flow →", yaxis_title="y (mm)", zaxis_title="x (mm), up"),
                      margin=dict(l=0, r=0, t=40, b=0))
    fig.write_html(OUT / f"viewer_{NAME}.html", include_plotlyjs="cdn")


def render(c, placed):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    fig, ax = plt.subplots(figsize=(16, 9))
    seen = []
    for name, m, _ in placed:
        sec = to_trimesh(m).section(plane_origin=[0, 0.001, 0], plane_normal=[0, 1, 0])
        if sec is None:
            continue
        for poly in sec.discrete:
            ax.fill(poly[:, 2], poly[:, 0], color=mat(name)[2], ec="#222", lw=0.25)
        if PART_INFO[name][0] not in seen:
            seen.append(PART_INFO[name][0])
    ax.axhline(0, color="#999", lw=0.6, ls="-.")
    ax.set_aspect("equal"); ax.set_xlabel("z (mm), flow left to right"); ax.set_ylabel("x (mm), up")
    ax.set_title("TJ-110 micro-turbojet on its test stand: section through the axis (plane y = 0)\n"
                 "design study, not built", fontsize=11)
    ax.legend(handles=[Patch(color=MATS[k][2], label=MATS[k][0]) for k in seen], fontsize=7.5,
              loc="upper left", bbox_to_anchor=(1.01, 1))
    ax.grid(alpha=0.25)
    (ROOT / "diagrams").mkdir(exist_ok=True)
    fig.savefig(ROOT / "diagrams" / f"cad_{NAME}_section.png", dpi=130, bbox_inches="tight")
    plt.close(fig)

    items = [(to_trimesh(m), hex2rgb(mat(n)[2])) for n, m, _ in placed]
    img, _ = render_zbuffer(items, view=(0.55, 1.0, -0.4), width=1700, height=1000)
    fig, ax = plt.subplots(figsize=(13, 7.7))
    ax.imshow(img); ax.set_axis_off()
    ax.set_title("TJ-110 on its test stand: exterior (inlet left, nozzle right; design study, not built)", fontsize=11)
    fig.savefig(ROOT / "diagrams" / f"cad_{NAME}_exterior.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    rows, engine, rotor, clashes, (clear, special), (tb, tc, tt) = write_outputs()
    print(f"{len(rows)} unique parts, {sum(r['qty'] for r in rows)} placed; engine {engine:.0f} g "
          f"(rotor {rotor:.0f} g); clashes: {clashes or 'none'}")
    for rn, sn, d, p in clear[:12]:
        print(f"  {rn:>15} - {sn:<20} {d:6.2f} mm at r={p[0]:.1f} z={p[1]:.1f}")
    for sp in special:
        print(f"  {sp[0]}: {sp[3]:.2f} mm")
    print(f"build {tb:.1f} s, checks {tc:.1f} s, total {tt:.1f} s")
