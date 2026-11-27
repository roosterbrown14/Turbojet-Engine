"""TJ-110 drawing package: dimensioned assembly, exploded views, cutaway and per-part sheet.

All dimensions come from the parametric CAD model (cad/build.py), which reads the gas-path sizes
from data/design_point.json. They are design dimensions, not measurements of a built engine.

Writes (in prototypes/):
  TJ110_assembled_section.png|svg   fully assembled, dimensioned section, coloured by material
  TJ110_exploded_section.png|svg    sub-assemblies pulled apart along the axis in assembly order, every part labelled
  TJ110_parts_sheet.png|svg         every unique part on its own with dimensions, material, quantity and a 3-D view
  TJ110_exploded_3d.png             shaded 3-D exploded view, colour = material
  TJ110_cutaway.png                 shaded 3-D render with a quarter removed
  TJ110_exploded.stl, TJ110_viewer_exploded.html   3-D exploded model and interactive viewer
  TJ110_parts_list.csv              parts, materials, key dimensions, masses, process

Run: .venv/bin/python prototypes/build_drawings.py
"""
import csv
import importlib.util
import time
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
import trimesh  # noqa: E402
from manifold3d import Manifold  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "prototypes"
spec = importlib.util.spec_from_file_location("cadbuild", ROOT / "cad" / "build.py")
cad = importlib.util.module_from_spec(spec); spec.loader.exec_module(cad)

C = cad.C
DP = C.dp
LABEL = {
    "bellmouth": "Inlet bellmouth", "front_cover": "Front cover / compressor shroud", "impeller": "Compressor impeller",
    "compressor_nut": "Compressor nut", "diffuser": "Diffuser (radial + deswirl vanes)", "shaft": "Shaft",
    "bearing_608": "Bearing 608 hybrid", "bearing_sleeve_front": "Bearing sleeve, front", "bearing_sleeve_rear": "Bearing sleeve, rear",
    "oring_24x1.5": "O-ring 24 × 1.5 (soft mount)", "anti_rotation_pin": "Anti-rotation pin", "spacer_tube": "Bearing spacer tube",
    "preload_spring": "Preload spring", "shaft_tunnel": "Shaft tunnel", "outer_casing": "Outer casing",
    "liner_outer": "Combustor outer liner + dome", "liner_inner": "Combustor inner liner", "vaporizer": "Vaporizer tube",
    "fuel_manifold": "Fuel manifold ring", "fuel_needle": "Fuel needle", "fuel_line": "Fuel line", "oil_line": "Oil line",
    "line_fitting": "Bulkhead fitting", "glow_plug": "Glow plug (igniter)", "ngv_ring": "NGV ring + turbine shroud",
    "turbine_wheel": "Turbine wheel", "turbine_nut": "Turbine nut", "nozzle": "Exhaust nozzle", "tail_cone": "Tail cone + struts",
    "egt_thermocouple": "EGT thermocouple", "screw_M3x6": "Screw M3 × 6", "screw_M3x10": "Screw M3 × 10",
    "screw_M3x12_A286": "Screw M3 × 12 (hot)", "screw_M3x16": "Screw M3 × 16", "screw_M4x16": "Screw M4 × 16",
    "nut_M3": "Nut M3", "nut_M3_A286": "Nut M3 (hot)", "mounting_band": "Mounting band", "stand_pillar": "Stand pillar",
    "stand_base": "Stand base plate",
}
d = lambda r: f"Ø{2 * r:.1f}"
KEY_DIMS = {
    "bellmouth": f"{d(C.r_duct)} throat, lip {d(C.r_duct + 14 + 2.5)}, 33 long, 2.5 wall; 3 starter bosses M3",
    "front_cover": f"shroud {d(C.r_duct)}→{d(C.r2 + C.clear_c)} (0.3 off tips), flange Ø130, 8 × Ø3.4 on Ø124.6",
    "impeller": f"D2 {2 * C.r2:.1f}, D1t {2 * C.r1t:.1f}, hub {2 * C.r1h:.1f}, b2 {C.b2:.2f}, {C.Zc}+{C.Zc} blades, {C.beta2b:.0f}° backsweep",
    "compressor_nut": "M8 × 1 LH, hex AF12 × 6 + nose", "diffuser": f"{C.n_diff} wedge vanes {d(1.08 * C.r2)}→{d(C.r3)}, {C.n_deswirl} deswirl vanes, Ø116",
    "shaft": f"Ø{2 * C.rs:.0f} at bearings, Ø{2 * C.rs_mid:.0f} between, 145 long, M8 × 1 ends",
    "bearing_608": "8 × 22 × 7, Si3N4 balls, C3", "bearing_sleeve_front": "Ø22 / Ø24 × 7.8, rear lip Ø19.6, Ø2 pin hole, Ø1 oil hole",
    "bearing_sleeve_rear": "Ø22 / Ø24 × 7, Ø2 pin hole", "oring_24x1.5": "24 ID × 1.5 cord, gland 1.35 (10 % squeeze)",
    "anti_rotation_pin": "Ø1.5 × 3.2 dowel", "spacer_tube": f"Ø10.2 / Ø13.6 × {C.span - C.bw:.0f}",
    "preload_spring": "Ø20.4 mean, 0.8 wire, 8.5 installed", "shaft_tunnel": f"bore Ø{2 * C.tun_bore:.1f} (sleeves), housings Ø{2 * C.housing_r:.1f}, tube Ø{2 * C.tunnel_r:.0f}, flange Ø48",
    "outer_casing": f"Ø{2 * C.rc_in:.1f} ID × {C.wall:.0f} wall × {C.z_ngv_te - C.z_fw:.0f}, flanges Ø130 × 1.5",
    "liner_outer": f"Ø{2 * C.liner_out:.1f} × 0.5 sheet, {C.liner_len:.0f} long, cone to Ø{2 * (C.ngv_ro + 0.3):.1f}, 8 vaporizer holes Ø5.1",
    "liner_inner": f"Ø{2 * C.liner_in:.0f} × 0.5 sheet, cone to Ø36.4", "vaporizer": "Ø5 × 0.5 tube, J: 34 + R5 + 12",
    "fuel_manifold": "Ø3 × 0.5 tube on Ø68", "fuel_needle": "Ø0.8 × 3 (21 G)", "fuel_line": "Ø3 × 0.5 × 35.5",
    "oil_line": "Ø2.5 × 0.5 × 56", "line_fitting": "hex AF7, Ø4.4 nipple, Ø3.1 bore", "glow_plug": "1/4-32 body, hex AF8",
    "ngv_ring": f"{C.Zn} vanes, hub {d(C.rh)}, tip {d(C.rt_s)}, axial chord {C.ngv_cx - 0.2:.1f}, exit ~{np.degrees(np.arctan(C.Cth2 / C.Cx)):.0f}°",
    "turbine_wheel": f"tip {d(C.rt)}, hub {d(C.rh)}, {C.Zr} blades, h = chord = {C.chord:.1f}, disc 12",
    "turbine_nut": "M8 × 1, hex AF12 × 6", "nozzle": f"Ø{2 * C.rt_s:.1f} → exit {d(C.r9)}, 0.8 wall, flange Ø130 × 1.5",
    "tail_cone": "Ø41.2 × 39, 0.8 wall, 4 struts 1.2 thick", "egt_thermocouple": "Ø1.5 probe, 15 immersion",
    "screw_M3x6": "ISO 4762", "screw_M3x10": "ISO 4762", "screw_M3x12_A286": "A286", "screw_M3x16": "ISO 4762",
    "screw_M4x16": "ISO 4762", "nut_M3": "ISO 4032", "nut_M3_A286": "A286", "mounting_band": "Ø118.9 bore, 3 wall, 10 wide",
    "stand_pillar": "37 × 32 × 20", "stand_base": "260 × 160 × 8",
}


def color(name):
    return cad.mat(name)[2]


def section(m, y=0.001):
    """Section through the plane y = 0; returned in drawing coordinates (z horizontal, x vertical)."""
    tm = cad.to_trimesh(m) if isinstance(m, Manifold) else m
    sec = tm.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
    return [] if sec is None else [p[:, [2, 0]] for p in sec.discrete]


def fill(ax, loops, fc, lw=0.35):
    """Fill closed section loops with the even-odd rule, so holes stay open."""
    from matplotlib.path import Path as MPath
    from matplotlib.patches import PathPatch
    from shapely.geometry import Polygon
    from shapely.validation import make_valid
    from shapely.ops import unary_union
    shape = None
    for lp in loops:
        if len(lp) < 3:
            continue
        pg = make_valid(Polygon(lp))
        pg = unary_union([q for q in getattr(pg, 'geoms', [pg]) if q.geom_type in ('Polygon', 'MultiPolygon')])
        if pg.is_empty:
            continue
        shape = pg if shape is None else shape.symmetric_difference(pg)
    if shape is None or shape.is_empty:
        return
    for g in getattr(shape, "geoms", [shape]):
        if g.geom_type != "Polygon":
            continue
        verts, codes = [], []
        for ring in [g.exterior, *g.interiors]:
            xy = np.asarray(ring.coords)
            verts += xy.tolist(); codes += [MPath.MOVETO] + [MPath.LINETO] * (len(xy) - 2) + [MPath.CLOSEPOLY]
        ax.add_patch(PathPatch(MPath(verts, codes), fc=fc, ec="#222", lw=lw))


def dim(ax, p0, p1, text, off=(0, 0), fs=7.5, color="k", rot=0):
    (x0, y0), (x1, y1) = p0, p1
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="<->", lw=0.7, color=color, shrinkA=0, shrinkB=0))
    ax.text((x0 + x1) / 2 + off[0], (y0 + y1) / 2 + off[1], text, fontsize=fs, ha="center", va="center", rotation=rot,
            color=color, bbox=dict(fc="white", ec="none", pad=0.6))


def ext(ax, p0, p1):
    ax.plot([p0[0], p1[0]], [p0[1], p1[1]], lw=0.45, ls=(0, (4, 3)), color="#777", zorder=0.5)


def material_legend(ax, names, loc="upper left", anchor=(1.01, 1), ncol=1):
    keys = []
    for n in names:
        k = cad.PART_INFO[n][0]
        if k not in keys:
            keys.append(k)
    ax.legend(handles=[Patch(fc=cad.MATS[k][2], ec="#333", lw=0.5, label=cad.MATS[k][0]) for k in keys],
              title="Material", fontsize=7.5, title_fontsize=8.5, loc=loc, bbox_to_anchor=anchor, frameon=False, ncol=ncol)


def tmb(m):
    return cad.to_trimesh(m)


# --------------------------------------------------------------------------- assembled section
def assembled(parts, placed, mass):
    fig, ax = plt.subplots(figsize=(18, 13))
    names = []
    for name, m, _ in placed:
        fill(ax, section(m), color(name), 0.3)
        names.append(name)
    ax.axhline(0, color="#888", lw=0.6, ls="-.", zorder=0.4)
    zb0 = tmb(parts["bellmouth"]).bounds[0, 2] - 6
    zexit = C.z_noz_exit
    # overall length and axial stations (below the stand)
    dim(ax, (zb0, -134), (zexit, -134), f"{zexit - zb0:.0f} overall (bellmouth lip to nozzle exit)", off=(0, 0))
    ext(ax, (zb0, -40), (zb0, -138)); ext(ax, (zexit, -22), (zexit, -138))
    # internal axial dimensions (upper half, above the casing)
    y = 74
    for z0, z1, txt in ((C.z_b1, C.z_b2, f"bearing span {C.span:.0f}"),):
        dim(ax, (z0, y), (z1, y), txt)
        ext(ax, (z0, 11), (z0, y + 2)); ext(ax, (z1, 11), (z1, y + 2))
    y = 84
    dim(ax, (C.z_dome, y), (C.z_liner_end, y), f"combustor liner {C.liner_len:.0f}")
    ext(ax, (C.z_dome, 54), (C.z_dome, y + 2)); ext(ax, (C.z_liner_end, 38), (C.z_liner_end, y + 2))
    dim(ax, (0, y), (C.z_t, y), f"inducer LE to turbine disc centre {C.z_t:.0f}", off=(0, 0))
    ext(ax, (0, 24), (0, y + 2)); ext(ax, (C.z_t, 35), (C.z_t, y + 2))
    y = 94
    dim(ax, (zb0, y), (C.z_fw, y), f"inlet {C.z_fw - zb0:.0f}", fs=7)
    ext(ax, (C.z_fw, 66), (C.z_fw, y + 2)); ext(ax, (zb0, 40), (zb0, y + 2))
    dim(ax, (C.z_fw, y), (C.z_ngv_te, y), f"casing {C.z_ngv_te - C.z_fw:.0f}")
    ext(ax, (C.z_ngv_te, 66), (C.z_ngv_te, y + 2))
    dim(ax, (C.z_ngv_te, y), (zexit, y), f"nozzle {zexit - C.z_ngv_te:.0f}")
    # diameters: right-hand column
    cols = [(212, C.rc_out, C.z_fw + 40, f"Ø{2 * C.rc_out:.1f}\ncasing"), (226, 65.0, C.z_ngv_te, "Ø130\nflanges"),
            (240, C.rt, C.z_t, f"Ø{2 * C.rt:.1f}\nturbine\ntip"), (254, C.r9, zexit, f"Ø{2 * C.r9:.1f}\nnozzle\nexit")]
    for zc, r, zf, txt in cols:
        dim(ax, (zc, -r), (zc, r), txt, fs=7)
        ext(ax, (zf, r), (zc + 2, r)); ext(ax, (zf, -r), (zc + 2, -r))
    # diameters: left-hand column
    lip = C.r_duct + 14 + 2.5
    cols = [(-52, C.r1t, 0, f"Ø{2 * C.r1t:.1f}\ninducer"), (-66, C.r2, C.z_hub_exit - 2, f"Ø{2 * C.r2:.1f}\nimpeller\nD2"),
            (-80, C.r3, C.z_hub_exit - 2, f"Ø{2 * C.r3:.1f}\ndiffuser\nexit")]
    for zc, r, zf, txt in cols:
        dim(ax, (zc, -r), (zc, r), txt, fs=7)
        ext(ax, (zf, r), (zc - 2, r)); ext(ax, (zf, -r), (zc - 2, -r))
    # callouts (upper half)
    calls = [("Inlet bellmouth (starter bosses)", (-28, 33)), ("Front cover / shroud, 0.30 tip gap", (6, 27)),
             ("Compressor nut", (-6, 5)), ("Impeller, Al 2618", (8, 18)),
             ("Diffuser: 18 wedge + 24 deswirl vanes", (17, 47)), ("Front bearing on 2 O-rings", (C.z_b1, 9)),
             ("Fuel manifold + 8 needles", (34, 35.5)), ("Vaporizer (J-tube) × 8", (55, 34)),
             ("Combustor outer liner, 0.5 sheet", (70, C.liner_out)), ("Outer casing, 1 mm SS304", (88, C.rc_out)),
             ("Shaft tunnel + spacer + shaft", (75, 10)), ("Preload spring", (104, 10.2)),
             ("Rear bearing on 2 O-rings", (C.z_b2, 9)), ("NGV ring, 19 vanes", (C.z_ngv_le + 4, 28)),
             ("Turbine wheel, 27 blades", (C.z_t, 26)), ("Tail cone + struts", (152, 14)),
             ("EGT thermocouple", (142, 44)), ("Exhaust nozzle", (182, 26))]
    calls.sort(key=lambda c: c[1][0])
    nlv = 4
    width = [1.55 * len(t) + 5 for t, _ in calls]
    zs = np.array([c[1][0] for c in calls], float)
    for lv in range(nlv):
        idx = list(range(lv, len(calls), nlv))
        for a_, b_ in zip(idx[:-1], idx[1:]):                         # push right to clear the previous label
            zs[b_] = max(zs[b_], zs[a_] + 0.5 * (width[a_] + width[b_]))
        zs[idx[-1]] = min(zs[idx[-1]], 262 - 0.5 * width[idx[-1]])
        for a_, b_ in zip(idx[::-1][1:], idx[::-1][:-1]):             # then pull left from the right edge
            zs[a_] = min(zs[a_], zs[b_] - 0.5 * (width[a_] + width[b_]))
    for k, ((txt, (zt, xt)), zl) in enumerate(zip(calls, zs)):
        yl = 104 + 10 * (k % nlv)
        ax.annotate(txt, xy=(zt, xt), xytext=(zl, yl), fontsize=7.2, ha="center", va="bottom", rotation=0,
                    arrowprops=dict(arrowstyle="-", lw=0.45, color="#444", shrinkA=0, shrinkB=0),
                    bbox=dict(fc="white", ec="#bbb", lw=0.4, pad=1.2))
        ax.plot([zt], [xt], "o", ms=2, color="#222")
    # lower half: stand labels
    for txt, xy, xyt in (("Mounting band (clamp)", (65, -62), (5, -80)), ("Stand pillar", (100, -95), (140, -92)),
                         ("Stand base plate", (180, -114), (180, -100))):
        ax.annotate(txt, xy=xy, xytext=xyt, fontsize=7.2, ha="center", arrowprops=dict(arrowstyle="-", lw=0.45, color="#444"),
                    bbox=dict(fc="white", ec="#bbb", lw=0.4, pad=1.2))
    p = DP["performance"]
    info = (f"TJ-110 design point (ISA SLS)\nthrust {p['thrust']:.0f} N, ṁ {DP['spec']['mdot']:.2f} kg/s\n"
            f"{DP['spec']['rpm'] / 1e3:.0f} k rpm, PR {DP['spec']['pr']:.1f}, TIT {DP['spec']['TIT']:.0f} K\n"
            f"fuel {p['fuel_l_per_min']:.2f} L/min, EGT {p['EGT']:.0f} K\nengine mass ≈ {mass:.0f} g (CAD)\n"
            f"bearing supports {C.k_bearing / 1e6:.1f} MN/m (O-rings)")
    ax.text(-85, -110, info, fontsize=7.5, va="bottom", ha="left", family="monospace",
            bbox=dict(fc="#f7f7f7", ec="#999", lw=0.5, pad=4))
    ax.set_aspect("equal"); ax.set_xlim(-92, 268); ax.set_ylim(-142, 150)
    ax.set_xlabel("z (mm), flow left to right"); ax.set_ylabel("x (mm), up")
    ax.grid(alpha=0.15)
    ax.set_title("TJ-110 micro-turbojet, fully assembled on its test stand: section through the axis\n"
                 "design dimensions in mm (not yet built or measured)", fontsize=11)
    material_legend(ax, names)
    for e in ("png", "svg"):
        fig.savefig(OUT / f"TJ110_assembled_section.{e}", dpi=150, bbox_inches="tight")
    plt.close(fig)


# --------------------------------------------------------------------------- exploded
RADIAL = {"line_fitting@fuel": (112.5, 0), "line_fitting@oil": (270, 180), "glow_plug": (22.5, 0),
          "fuel_line": (112.5, 0), "oil_line": (270, 180), "egt_thermocouple": (0, 0),
          "anti_rotation_pin@front": (0, 0), "anti_rotation_pin@rear": (0, 0)}

ROWS = [  # title, anchor item, front items (outward), rear items (outward). item = (tags, followers[(tag, dz, dr)])
    ("Casing and gas-path statics",
     (["outer_casing"], [("nut_M3@front_flange", 9, 0), ("screw_M3x12_A286@rear_flange", -14, 0),
                         ("line_fitting@fuel", 0, 14), ("line_fitting@oil", 0, 14), ("glow_plug", 0, 14)]),
     [(["diffuser"], []), (["front_cover"], [("screw_M3x10@diffuser", -16, 0), ("screw_M3x10@front_flange", -16, 0)]),
      (["bellmouth"], [("screw_M3x6@bellmouth", -14, 0)])],
     [(["ngv_ring"], []), (["nozzle"], [("nut_M3_A286@rear_flange", 9, 0), ("egt_thermocouple", 0, 14)]),
      (["tail_cone"], [])]),
    ("Combustor",
     (["liner_outer"], []),
     [(["vaporizer"], []), (["fuel_manifold", "fuel_needle"], [("fuel_line", 0, 10)])],
     [(["liner_inner"], [])]),
    ("Bearing tunnel and soft mounts",
     (["shaft_tunnel"], [("screw_M3x6@tunnel", 12, 0), ("oil_line", 0, 14), ("anti_rotation_pin@front", 0, 10),
                         ("anti_rotation_pin@rear", 0, 10)]),
     [(["oring_24x1.5@front"], []), (["bearing_sleeve_front"], []), (["bearing_608@front"], [])],
     [(["preload_spring"], []), (["oring_24x1.5@rear"], []), (["bearing_sleeve_rear"], []), (["bearing_608@rear"], [])]),
    ("Rotor",
     (["shaft"], []),
     [(["impeller"], []), (["compressor_nut"], [])],
     [(["spacer_tube"], []), (["turbine_wheel"], []), (["turbine_nut"], [])]),
]


def exploded_layout(placed, gap=14.0, row_gap=70.0):
    """Pull each sub-assembly apart along the axis. Returns rows of (title, moved parts, label groups, x offset);
    a label group is a list of (name, Manifold) that gets one balloon."""
    by_tag = {}
    for name, m, tag in placed:
        by_tag.setdefault(tag, []).append((name, m))

    def get(tag, dz=0.0, dr=0.0):
        out = []
        for name, m in by_tag[tag]:
            if tag in RADIAL:
                a0, a1 = RADIAL[tag]
                m = m.rotate([0, 0, a1 - a0])
                m = m.translate([dr * np.cos(np.radians(a1)), dr * np.sin(np.radians(a1)), 0])
            out.append((name, m.translate([0, 0, dz])))
        return out

    def item(spec):
        tags, fol = spec
        groups = [[x for t in tags for x in get(t)]] + [get(t, dz, dr) for t, dz, dr in fol]
        return groups

    rows = []
    for title, anchor, front, rear in ROWS:
        groups = item(anchor)
        moved = [x for g in groups for x in g]
        labels = list(groups)
        b = np.array([m.bounding_box() for _, m in moved])
        zmin, zmax = b[:, 2].min(), b[:, 5].max()
        for seq, sign in ((front, -1), (rear, 1)):
            edge = zmin if sign < 0 else zmax
            for spec_ in seq:
                groups = item(spec_)
                allm = [x for g in groups for x in g]
                bb = np.array([m.bounding_box() for _, m in allm])
                ilo, ihi = bb[:, 2].min(), bb[:, 5].max()
                dz = min(edge - gap - ihi, 0) if sign < 0 else max(edge + gap - ilo, 0)
                groups = [[(n, m.translate([0, 0, dz])) for n, m in g] for g in groups]
                moved += [x for g in groups for x in g]
                labels += groups
                edge = (ilo + dz) if sign < 0 else (ihi + dz)
                zmin, zmax = min(zmin, edge), max(zmax, edge)
        rows.append((title, moved, labels))
    out, x_top = [], 0.0
    for title, moved, labels in rows:
        b = np.array([m.bounding_box() for _, m in moved])
        hi, lo = b[:, 3].max(), b[:, 0].min()
        dx = x_top - hi
        moved = [(n, m.translate([dx, 0, 0])) for n, m in moved]
        labels = [[(n, m.translate([dx, 0, 0])) for n, m in g] for g in labels]
        labels.sort(key=lambda g: np.mean([m.bounding_box()[2] + m.bounding_box()[5] for _, m in g]))
        out.append((title, moved, labels, dx))
        x_top = lo + dx - row_gap
    return out


def group_text(g):
    names = list(dict.fromkeys(n for n, _ in g))
    return ", ".join(f"{LABEL[n]} ×{sum(1 for q, _ in g if q == n)}" for n in names), \
        " / ".join(dict.fromkeys(cad.mat(n)[0] for n in names))


def crop(img, top=20, pad=20):
    """Trim white margins from a render; returns the image and the (x, y) pixel offset removed."""
    ink = np.where(img.min(2) < 0.985)
    y0, y1 = max(ink[0].min() - top, 0), min(ink[0].max() + pad, img.shape[0])
    x0, x1 = max(ink[1].min() - pad, 0), min(ink[1].max() + pad, img.shape[1])
    out = img[y0:y1, x0:x1]
    if ink[0].min() - top < 0:
        out = np.vstack([np.ones((top - ink[0].min(), out.shape[1], 3)), out])
        y0 -= top - ink[0].min()
    return out, np.array([x0, y0])


def balloon(ax, xy, xyt, num, fs=7):
    ax.annotate(str(num), xy=xy, xytext=xyt, fontsize=fs, ha="center", va="center", fontweight="bold",
                arrowprops=dict(arrowstyle="-", lw=0.5, color="#444", shrinkA=5, shrinkB=0),
                bbox=dict(boxstyle="circle,pad=0.25", fc="white", ec="#333", lw=0.7))


def exploded(placed):
    rows = exploded_layout(placed)
    moved = [x for _, mv, _, _ in rows for x in mv]
    full = [(n, tmb(m)) for n, m in moved]
    dec = cad.decimate_set([t for _, t in full], 95000)
    trimesh.util.concatenate(dec).export(OUT / "TJ110_exploded.stl")
    # interactive viewer
    import plotly.graph_objects as go
    fig = go.Figure()
    by = {}
    for (n, _), t in zip(full, dec):
        by.setdefault(n, []).append(t)
    for n, ms in by.items():
        tm = trimesh.util.concatenate(ms)
        v, f = tm.vertices, tm.faces
        fig.add_trace(go.Mesh3d(x=v[:, 2], y=v[:, 1], z=v[:, 0], i=f[:, 0], j=f[:, 1], k=f[:, 2],
                                name=f"{LABEL[n]} ({cad.mat(n)[0]})", color=color(n), showlegend=True))
    fig.update_layout(title="TJ-110: exploded view by sub-assembly (design, not built). Click the legend to hide parts.",
                      scene=dict(aspectmode="data", xaxis_title="z (mm)", zaxis_title="x (mm)"), margin=dict(l=0, r=0, t=40, b=0))
    fig.write_html(OUT / "TJ110_viewer_exploded.html", include_plotlyjs="cdn")
    # numbering in assembly order (row by row, inlet to exhaust)
    numbered = []
    for title, mv, labels, dx in rows:
        for g in labels:
            numbered.append((len(numbered) + 1, title, g))
    # 2-D exploded section with balloons
    fig, ax = plt.subplots(figsize=(20, 17))
    names = []
    for n, m in moved:
        fill(ax, section(m), color(n), 0.3)
        names.append(n)
    zall = np.array([m.bounding_box() for _, m in moved])
    zlo, zhi = zall[:, 2].min(), zall[:, 5].max()
    k_all = 0
    for title, mv, labels, dx in rows:
        b = np.array([m.bounding_box() for _, m in mv])
        top, bot = b[:, 3].max(), b[:, 0].min()
        ax.text(zlo - 10, 0.5 * (top + bot), title, fontsize=10, fontweight="bold", ha="right", va="center", rotation=90)
        ax.axhline(dx, color="#aaa", lw=0.5, ls="-.", zorder=0.3)
        for k, g in enumerate(labels):
            num = numbered[k_all][0]; k_all += 1
            bb = np.array([m.bounding_box() for _, m in g])
            zc = 0.5 * (bb[:, 2].min() + bb[:, 5].max())
            above = k % 2 == 0
            lvl = (k // 2) % 3
            if above:
                xy, yt = (zc, bb[:, 3].max()), top + 7 + 9 * lvl
            else:
                xy, yt = (zc, bb[:, 0].min()), bot - 7 - 9 * lvl
            balloon(ax, xy, (zc, yt), num)
    ax.set_aspect("equal"); ax.grid(alpha=0.15)
    ax.set_xlim(zlo - 25, zhi + 10)
    ax.set_xlabel("z (mm): each sub-assembly pulled apart along the engine axis (inlet to the left); "
                  "balloon numbers follow assembly order")
    ax.set_ylabel("mm")
    ax.set_title("TJ-110: exploded by sub-assembly, section through the axis (design, not built)\n"
                 "fasteners, fittings and lines are drawn with the part they fit; radial parts are rotated into the "
                 "section plane; test-stand parts are on the parts sheet", fontsize=11)
    material_legend(ax, names, anchor=(1.01, 1.0))
    table = "\n".join(f"{num:>2}  {group_text(g)[0]}" for num, _, g in numbered)
    ax.text(1.02, 0.60, "Item  part × qty\n" + table, transform=ax.transAxes, fontsize=7.4, va="top", ha="left",
            family="DejaVu Sans Mono")
    for e in ("png", "svg"):
        fig.savefig(OUT / f"TJ110_exploded_section.{e}", dpi=130, bbox_inches="tight")
    plt.close(fig)
    # 3-D shaded exploded render (full-resolution meshes) with the same balloons
    items = [(t, cad.hex2rgb(color(n))) for n, t in full]
    img, proj0 = cad.render_zbuffer(items, view=(0.5, 1.0, -0.25), width=2400, height=1500)
    img, off = crop(img, top=110)
    proj = lambda P: proj0(P) - off
    fig, ax = plt.subplots(figsize=(17, 12.5))
    ax.imshow(img); ax.set_axis_off()
    for k, (num, _, g) in enumerate(numbered):
        bb = np.array([m.bounding_box() for _, m in g])
        p = proj(np.array([[bb[:, 3].max(), 0, 0.5 * (bb[:, 2].min() + bb[:, 5].max())]]))[0]
        balloon(ax, p, (p[0] + (14 if k % 2 else -14), p[1] - 35 - 22 * (k % 3)), num, fs=8)
    ax.legend(handles=[Patch(fc=cad.MATS[kk][2], ec="#333", lw=0.5, label=cad.MATS[kk][0])
                       for kk in dict.fromkeys(cad.PART_INFO[n][0] for n, _ in full)],
              loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=8, frameon=False, title="Material")
    ax.text(1.01, 0.52, "\n".join(f"{num:>2}  {group_text(g)[0]}" for num, _, g in numbered), transform=ax.transAxes,
            fontsize=7.4, va="top", family="DejaVu Sans Mono")
    ax.set_title("TJ-110 exploded by sub-assembly (colour = material; numbers = assembly order; design, not built)", fontsize=12)
    fig.savefig(OUT / "TJ110_exploded_3d.png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return numbered


# --------------------------------------------------------------------------- cutaway
def cutaway(placed):
    cutter = Manifold.cube([300, 300, 700]).translate([0, 0, -300])
    items = []
    for n, m, _ in placed:
        mm = m - cutter
        if mm.is_empty():
            continue
        tm = tmb(mm)
        items.append((tm, cad.hex2rgb(color(n))))
    img, proj0 = cad.render_zbuffer(items, view=(0.55, 1.0, -0.35), width=2200, height=1350)
    img, off = crop(img, top=200)
    fig, ax = plt.subplots(figsize=(18, 11))
    ax.imshow(img); ax.set_axis_off()
    calls = [("Bellmouth", (30, -24)), ("Impeller", (22, 6)), ("Front cover / shroud", (40, 9)), ("Diffuser", (46, 18)),
             ("Front bearing + O-rings", (9, C.z_b1)), ("Shaft tunnel", (11, 60)), ("Vaporizer", (34, 55)),
             ("Combustor liner", (C.liner_out, 72)), ("Outer casing", (C.rc_out, 95)), ("NGV", (28, C.z_ngv_le + 5)),
             ("Turbine", (27, C.z_t)), ("Tail cone", (12, 155)), ("Nozzle", (26, 188)), ("EGT thermocouple", (46, 142)),
             ("Rear bearing", (9, C.z_b2)), ("Shaft", (2, 80)), ("Fuel manifold", (35, 34))]
    pts = proj0(np.array([[x, -0.2, z] for _, (x, z) in calls])) - off
    order = np.argsort(pts[:, 0])
    lanes = [-1e9] * 4
    for k, i in enumerate(order):
        txt = calls[i][0]
        w = 13.5 * len(txt) + 24
        lane = k % 4
        x = max(pts[i, 0], lanes[lane] + w / 2)
        lanes[lane] = x + w / 2
        ax.annotate(txt, xy=pts[i], xytext=(x, 35 + 40 * lane), fontsize=8.5, ha="center", va="center",
                    arrowprops=dict(arrowstyle="-", lw=0.6, color="#222"), bbox=dict(fc="white", ec="#999", lw=0.5, pad=1.5))
        ax.plot(*pts[i], "o", ms=2.5, color="#111")
    ax.set_title("TJ-110 cutaway (quarter removed; colour = material; design, not built)", fontsize=12)
    fig.savefig(OUT / "TJ110_cutaway.png", dpi=120, bbox_inches="tight")
    plt.close(fig)


# --------------------------------------------------------------------------- parts sheet
ORDER = ["bellmouth", "front_cover", "impeller", "compressor_nut", "diffuser", "shaft", "spacer_tube", "bearing_608",
         "bearing_sleeve_front", "bearing_sleeve_rear", "oring_24x1.5", "anti_rotation_pin", "preload_spring",
         "shaft_tunnel", "outer_casing", "liner_outer", "liner_inner", "vaporizer", "fuel_manifold", "fuel_needle",
         "fuel_line", "oil_line", "line_fitting", "glow_plug", "ngv_ring", "turbine_wheel", "turbine_nut", "nozzle",
         "tail_cone", "egt_thermocouple", "screw_M3x6", "screw_M3x10", "screw_M3x12_A286", "screw_M3x16", "screw_M4x16",
         "nut_M3", "nut_M3_A286", "mounting_band", "stand_pillar", "stand_base"]


def parts_sheet(parts, counts, bom):
    cols = 5
    rows = int(np.ceil(len(ORDER) / cols))
    fig, axs = plt.subplots(rows, cols, figsize=(23, 4.6 * rows))
    rows_csv = []
    for ax, n in zip(axs.flat, ORDER):
        m = parts[n]
        tm = tmb(m)
        lo, hi = tm.bounds
        loops = section(m)
        if not loops:
            loops = section(m, y=0.5 * (lo[1] + hi[1]))
        fill(ax, loops, color(n), 0.4)
        w, h = hi[2] - lo[2], hi[0] - lo[0]
        dim(ax, (lo[2], lo[0] - 0.12 * h - 0.4), (hi[2], lo[0] - 0.12 * h - 0.4), f"{w:.1f}", fs=7)
        dim(ax, (hi[2] + 0.06 * w + 0.3, lo[0]), (hi[2] + 0.06 * w + 0.3, hi[0]), f"{h:.1f}", fs=7)
        pad = max(w, h) * 0.18 + 1
        x0, x1 = lo[2] - pad * 0.4, hi[2] + pad + 0.9 * max(w, h)
        y0, y1 = lo[0] - pad, hi[0] + pad * 0.4
        if (y1 - y0) < 0.62 * (x1 - x0):
            ex = 0.5 * (0.62 * (x1 - x0) - (y1 - y0)); y0 -= ex; y1 += ex
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_color("#ccc")
        img, _ = cad.render_zbuffer([(tm, cad.hex2rgb(color(n)))], view=(0.6, 1.0, -0.6), width=260, height=260, max_edge=None)
        ins = ax.inset_axes([0.60, 0.40, 0.40, 0.60])
        ins.imshow(img); ins.set_axis_off()
        mat = cad.mat(n)[0]
        b = bom[n]
        ax.set_title(f"{LABEL[n]}  ×{counts[n]}\n{mat} · {float(b['mass_each_g']):.2f} g each", fontsize=8.3)
        ax.text(0.5, -0.02, KEY_DIMS[n], transform=ax.transAxes, ha="center", va="top", fontsize=6.6, color="#333", wrap=True)
        rows_csv.append({"part": LABEL[n], "file": f"cad/stl/{n}.stl", "qty": counts[n], "material": mat,
                         "key_dimensions_mm": KEY_DIMS[n], "envelope_mm": b["envelope_mm"],
                         "mass_each_g": b["mass_each_g"], "mass_total_g": b["mass_total_g"], "process": cad.PART_INFO[n][1]})
    for ax in list(axs.flat)[len(ORDER):]:
        ax.axis("off")
    fig.suptitle("TJ-110: every part, separated. Section through the part axis (horizontal = part axis) with overall "
                 "dimensions in mm, plus a 3-D view. Each panel has its own scale.", fontsize=12, fontweight="bold")
    keys = list(dict.fromkeys(cad.PART_INFO[n][0] for n in ORDER))
    fig.legend(handles=[Patch(fc=cad.MATS[k][2], ec="#333", lw=0.5, label=cad.MATS[k][0]) for k in keys],
               loc="lower center", ncol=5, fontsize=8.5, frameon=False, bbox_to_anchor=(0.5, -0.005))
    fig.tight_layout(rect=(0, 0.025, 1, 0.98))
    for e in ("png", "svg"):
        fig.savefig(OUT / f"TJ110_parts_sheet.{e}", dpi=110, bbox_inches="tight")
    plt.close(fig)
    with open(OUT / "TJ110_parts_list.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_csv[0])); w.writeheader(); w.writerows(rows_csv)
    return rows_csv


if __name__ == "__main__":
    t0 = time.time()
    parts, placed = cad.build(C)
    counts = {}
    for n, _, _ in placed:
        counts[n] = counts.get(n, 0) + 1
    bom = {r["part"]: r for r in csv.DictReader(open(ROOT / "cad" / "bom_TJ110.csv"))}
    engine = sum(float(r["mass_total_g"]) for n, r in bom.items() if n not in cad.STAND)
    timings = {}
    for label, fn in (("assembled", lambda: assembled(parts, placed, engine)), ("exploded", lambda: exploded(placed)),
                      ("cutaway", lambda: cutaway(placed)), ("parts sheet", lambda: parts_sheet(parts, counts, bom))):
        t = time.time(); fn(); timings[label] = time.time() - t
    print(f"{len(ORDER)} unique parts, {sum(counts.values())} placed, engine {engine:.0f} g; "
          + ", ".join(f"{k} {v:.0f} s" for k, v in timings.items()) + f"; total {time.time() - t0:.0f} s")
