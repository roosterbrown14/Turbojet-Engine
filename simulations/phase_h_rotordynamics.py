"""Phase H: rotordynamics. Campbell diagram, critical speeds vs bearing stiffness, span and shaft
diameter, mode shapes, bearing speed (DN) check.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tj.engine import EngineSpec, build, make_rotor  # noqa: E402
from tj.materials import BEARINGS  # noqa: E402
from tj.plotting import COLORS, plt, save, save_csv  # noqa: E402

base = EngineSpec()
bd = build(base)
R, info = make_rotor(bd)
Wop = base.rpm * 2 * np.pi / 60
rpm2w = 2 * np.pi / 60

# ---------------- H1: Campbell diagram
speeds = np.linspace(0, 1.6 * base.rpm, 50)
F, B = [], []
for n in speeds:
    fw, bw = R.whirl(max(n * rpm2w, 1.0), 3)
    F.append(fw[:3] / rpm2w)
    B.append(bw[:3] / rpm2w)
F, B = np.array(F), np.array(B)
save_csv(pd.DataFrame({"rpm": speeds, **{f"fwd_{i + 1}_rpm": F[:, i] for i in range(3)},
                       **{f"bwd_{i + 1}_rpm": B[:, i] for i in range(3)}}), "phase_h_campbell")
crit = bd.mech.get("critical_rpm") or [c / rpm2w for c in R.critical_speeds(2.5 * Wop)]
fig, ax = plt.subplots(figsize=(8.5, 5.5))
names = ["mode 1 (cylindrical bounce)", "mode 2 (conical rocking)", "mode 3 (shaft bending)"]
for i in range(3):
    ax.plot(speeds / 1e3, F[:, i] / 1e3, color=plt.cm.tab10(i), lw=2, label=f"{names[i]}, forward")
    ax.plot(speeds / 1e3, B[:, i] / 1e3, color=plt.cm.tab10(i), lw=1, ls="--")
ax.plot(speeds / 1e3, speeds / 1e3, "k-", lw=1.5, label="1× running speed (unbalance)")
for c in crit:
    if c < 1.6 * base.rpm:
        ax.plot(c / 1e3, c / 1e3, "o", ms=10, mfc="none", mec="r", mew=2)
ax.axvspan(base.rpm * 0.45 / 1e3, base.rpm * 1.05 / 1e3, color=COLORS["flow"], alpha=0.08)
ax.text(base.rpm * 0.46 / 1e3, 5, "operating range (idle-max)", fontsize=8, color=COLORS["flow"])
ax.set_xlabel("Shaft speed (krpm)")
ax.set_ylabel("Whirl frequency (k cycles/min)")
ax.set_ylim(0, 1.6 * base.rpm * 1.6 / 1e3)
ax.set_title("H1  Campbell diagram (red circles = critical speeds; dashed = backward whirl)")
ax.legend(fontsize=8, loc="upper left")
save(fig, "H1_campbell", "fe",
     f"Bearings {base.k_bearing:.0e} N/m each, span {base.bearing_span * 1e3:.0f} mm, shaft Ø{base.shaft_d * 1e3:.0f}/{base.shaft_d_mid * 1e3:.0f} mm 17-4PH. Gyroscopic stiffening included.")

# ---------------- H2: critical speeds vs bearing stiffness
rows = []
for k in np.logspace(6, 8.3, 24):
    Rk, _ = make_rotor(bd, k_bearing=k)
    cs = [c / rpm2w for c in Rk.critical_speeds(2.5 * Wop)]
    rows.append(dict(k=k, **{f"crit{i + 1}": (cs[i] if i < len(cs) else np.nan) for i in range(3)}))
dk = pd.DataFrame(rows)
save_csv(dk, "phase_h_bearing_stiffness")
fig, ax = plt.subplots(figsize=(8, 4.6))
for i in range(3):
    ax.semilogx(dk.k, dk[f"crit{i + 1}"] / 1e3, "-o", ms=3, color=plt.cm.tab10(i), lw=2, label=names[i])
ax.axhspan(base.rpm * 0.45 / 1e3, base.rpm * 1.05 / 1e3, color=COLORS["flow"], alpha=0.1)
ax.axvline(base.k_bearing, color="k", ls=":")
ax.set_xlabel("Bearing radial stiffness (N/m, each)")
ax.set_ylabel("Critical speed (krpm)")
ax.set_title("H2  Critical speeds vs bearing stiffness: the rigid-body modes move, bending barely does")
ax.legend(fontsize=8)
save(fig, "H2_bearing_stiffness", "fe", "Green band: operating speeds. Soft (O-ring) mounts push the rigid-body modes well below idle.")

# ---------------- H3: span and shaft diameter -> bending critical
rows = []
for span in np.linspace(0.06, 0.13, 15):
    for dm in (8e-3, 10e-3, 12e-3):
        Rs, _ = make_rotor(bd, span=span, d_mid=dm)
        cs = [c / rpm2w for c in Rs.critical_speeds(3.0 * Wop)]
        rows.append(dict(span_mm=span * 1e3, d_mid_mm=dm * 1e3, bending=cs[2] if len(cs) > 2 else np.nan, n_crit=len(cs)))
ds = pd.DataFrame(rows)
save_csv(ds, "phase_h_span")
fig, ax = plt.subplots(figsize=(8, 4.6))
for i, (dm, g) in enumerate(ds.groupby("d_mid_mm")):
    ax.plot(g.span_mm, g.bending / 1e3, "-o", ms=3, lw=2, color=plt.cm.viridis(i / 2.5), label=f"shaft Ø{dm:.0f} mm between bearings")
ax.axhline(base.rpm * 1.2 / 1e3, color="r", ls=":")
ax.text(61, base.rpm * 1.2 / 1e3 + 4, "max speed + 20 % margin", color="r", fontsize=8)
ax.axvline(base.bearing_span * 1e3, color="k", ls=":")
ax.set_xlabel("Bearing span (mm)")
ax.set_ylabel("Shaft-bending critical speed (krpm)")
ax.set_title("H3  Keep the shaft short and stiff: bending critical vs span and diameter")
ax.legend(fontsize=8)
save(fig, "H3_span_diameter", "fe")

# ---------------- H4: mode shapes at rest
w, shapes = R.modes(0.0, 3)
fig, ax = plt.subplots(figsize=(9, 4))
x = R.x_nodes * 1e3
for i, sh in enumerate(shapes):
    ax.plot(x, sh, lw=2, color=plt.cm.tab10(i), label=f"{names[i]}: {w[i] / rpm2w / 1e3:.0f} krpm (at rest)")
for xb, _ in R.bearings:
    ax.plot(xb * 1e3, 0, "^", ms=12, color="k")
for d in R.discs:
    ax.axvline(d.x * 1e3, color="#9ca3af", ls="--")
    ax.text(d.x * 1e3, 1.05, d.name, ha="center", fontsize=8)
ax.set_xlabel("Axial position along shaft (mm, inlet → exhaust)")
ax.set_ylabel("Normalized deflection")
ax.set_title("H4  Mode shapes (triangles = bearings)")
ax.legend(fontsize=8, loc="lower left")
save(fig, "H4_mode_shapes", "fe")

# ---------------- H5: bearing DN
fig, ax = plt.subplots(figsize=(7.5, 4.2))
rpm = np.linspace(0, 130_000, 50)
for bore in (6, 8, 10):
    ax.plot(rpm / 1e3, bore * rpm / 1e6, lw=2, label=f"{bore} mm bore")
for nm, b in BEARINGS.items():
    ax.axhline(b["DN_max"] / 1e6, ls="--", color="k" if "Hybrid" in nm else "#9ca3af")
    ax.text(2, b["DN_max"] / 1e6 + 0.02, f"{nm} limit (oil-mist)", fontsize=8)
ax.axvline(base.rpm / 1e3, color="k", ls=":")
ax.set_xlabel("Shaft speed (krpm)")
ax.set_ylabel("DN (millions: bore mm × rpm)")
ax.set_title("H5  Bearing speed: 8 mm bore at 110 krpm needs hybrid ceramic bearings")
ax.legend(fontsize=8, loc="lower right")
save(fig, "H5_bearing_DN", "analytic", "Indicative DN limits for small angular-contact bearings with fuel/oil-mist lubrication.")
print("criticals", crit, info)
print(dk.round(0).to_string(index=False))
print(ds.round(0).to_string(index=False))
