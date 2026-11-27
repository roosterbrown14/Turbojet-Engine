"""Phase D: turbine design. Smith-type efficiency chart, loading choice, blade/disc stress, velocity
triangles, disc stress distribution.
"""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tj import turbine as tb  # noqa: E402
from tj.engine import EngineSpec, build  # noqa: E402
from tj.materials import MATERIALS  # noqa: E402
from tj.plotting import COLORS, MAT_COLORS, plt, save, save_csv  # noqa: E402

base = EngineSpec()
bd = build(base)
Re = bd.turb["Re"]
cr = base.clear_t / bd.turb["h"]

# ---------------- D1: Smith-type chart (Soderberg losses) with design point and blade-height overlay
phi = np.linspace(0.35, 1.2, 120)
psi = np.linspace(0.8, 2.6, 120)
PHI, PSI = np.meshgrid(phi, psi)
ETA0 = tb.eta_stage(PHI, PSI, 1.0, 3e5, 0.0)
ETA = tb.eta_stage(PHI, PSI, 1.0, Re, cr)
fig, axs = plt.subplots(1, 2, figsize=(13, 5))
for ax, Z, title in ((axs[0], ETA0, "Large, smooth turbine (Re 3×10⁵, no clearance)"),
                     (axs[1], ETA, f"TJ-110 size (Re {Re:.0e}, clearance {100 * cr:.1f} % of span)")):
    cs = ax.contourf(PHI, PSI, Z, levels=np.arange(0.70, 0.95, 0.01), cmap="RdYlGn", extend="both")
    ax.contour(PHI, PSI, Z, levels=np.arange(0.70, 0.95, 0.02), colors="k", linewidths=0.4)
    fig.colorbar(cs, ax=ax, label="Total-to-total efficiency")
    ax.plot(base.phi_t, base.psi_t, "*", ms=15, color="gold", mec="k", label="TJ-110 design")
    ax.set_xlabel("Flow coefficient φ = Cx/U")
    ax.set_title(title, fontsize=10)
    ax.legend(loc="upper left")
axs[0].set_ylabel("Loading coefficient ψ = Δh0/U²")
fig.suptitle("D1  Turbine efficiency chart (Smith-chart shape from Soderberg losses)", fontweight="bold")
save(fig, "D1_smith_chart", "sim", "Zero exit swirl, constant axial velocity. Small size costs ~6 efficiency points: Reynolds number and tip clearance.")

# ---------------- D2: loading choice -> size, efficiency, stress, NGV Mach
rows = []
for ps in np.linspace(0.9, 2.2, 14):
    for ph in (0.45, 0.55, 0.65, 0.75, 0.85):
        r = build(replace(base, psi_t=ps, phi_t=ph))
        rows.append(dict(psi=ps, phi=ph, eta_t=r.turb["eta"], Dt_mm=r.turb["Dt"] * 1e3, h_mm=r.turb["h"] * 1e3,
                         M2=r.turb["M2"], hub_tip=r.turb["hub_tip"], root_stress=r.mech["stress_blade_root"],
                         life=r.mech["life_blade_h"], thrust=r.thrust, reaction=r.turb["reaction"]))
dl = pd.DataFrame(rows)
save_csv(dl, "phase_d_loading")
fig, axs = plt.subplots(2, 2, figsize=(12, 8))
cmap = plt.cm.plasma
for i, (ph, g) in enumerate(dl.groupby("phi")):
    c = cmap(i / 5)
    axs[0, 0].plot(g.psi, g.eta_t, "-o", ms=3, color=c, label=f"φ = {ph}")
    axs[0, 1].plot(g.psi, g.Dt_mm, "-o", ms=3, color=c)
    axs[1, 0].plot(g.psi, g.root_stress, "-o", ms=3, color=c)
    axs[1, 1].plot(g.psi, g.M2, "-o", ms=3, color=c)
axs[0, 0].set_ylabel("Turbine efficiency")
axs[0, 0].legend(fontsize=8)
axs[0, 1].set_ylabel("Turbine tip diameter (mm)")
axs[1, 0].set_ylabel("Blade root stress (MPa)")
axs[1, 1].set_ylabel("NGV exit Mach number")
axs[1, 1].axhline(1.0, color="r", ls=":")
for ax in axs.flat:
    ax.set_xlabel("Loading coefficient ψ")
    ax.axvline(base.psi_t, color="k", lw=0.8, ls=":")
fig.suptitle("D2  Turbine loading: high ψ = small, light turbine but lower efficiency and near-sonic NGVs", fontweight="bold")
save(fig, "D2_turbine_loading", "sim", "Design: ψ = 1.3, φ = 0.65 (reaction 0.35).")

# ---------------- D3: velocity triangles
o = bd.turb
fig, ax = plt.subplots(figsize=(8, 5))
U, Cx, Ct2 = o["U"], o["Cx"], o["psi"] * o["U"]


def arrow(x0, y0, dx, dy, col, lab, off=(5, 0)):
    ax.annotate("", (x0 + dx, y0 + dy), (x0, y0), arrowprops=dict(arrowstyle="-|>", color=col, lw=2))
    ax.text(x0 + dx / 2 + off[0], y0 + dy / 2 + off[1], lab, color=col, fontsize=9)


# inlet to rotor (station 2): C2 from origin, W2 = C2 - U
arrow(0, 0, Ct2, -Cx, COLORS["egt"], f"C2 {o['C2']:.0f} m/s\n(NGV exit, α2 {o['alpha2']:.0f}°)", (-150, -30))
arrow(0, 0, Ct2 - U, -Cx, COLORS["pr"], f"W2 {o['W2']:.0f} m/s\n(β2 {o['beta2']:.0f}°)", (-150, 10))
arrow(Ct2 - U, -Cx, U, 0, COLORS["design"], f"U {U:.0f} m/s", (-30, -25))
# exit (station 3)
x0 = 0
arrow(x0, -260, 0, -Cx, COLORS["egt"], f"C3 {Cx:.0f} m/s (axial)", (8, 0))
arrow(x0, -260, -U, -Cx, COLORS["pr"], f"W3 {o['W3']:.0f} m/s (β3 {o['beta3']:.0f}°)", (-170, 0))
arrow(-U, -260 - Cx, U, 0, COLORS["design"], "U", (0, -25))
ax.text(-U - 60, 20, "Rotor inlet", fontweight="bold")
ax.text(-U - 60, -240, "Rotor exit", fontweight="bold")
ax.set_aspect("equal")
ax.set_xlim(-U - 80, Ct2 + 80)
ax.set_ylim(-260 - Cx - 60, 60)
ax.set_xlabel("Tangential velocity (m/s)")
ax.set_ylabel("Axial velocity (m/s, flow downward)")
ax.set_title("D3  Turbine mean-line velocity triangles at the design point")
save(fig, "D3_velocity_triangles", "sim")

# ---------------- D4: disc stress distribution
mt = MATERIALS[base.mat_turb]
r_rim = o["rh"] - 0.001
r, sr, st, avg = tb.disc_stress(base.rpm, base.shaft_d / 2, r_rim, mt.density, mt.nu, bd.mech["rim_load"])
fig, ax = plt.subplots(figsize=(7.5, 4.3))
ax.plot(r * 1e3, st, color=COLORS["stress"], lw=2, label="hoop stress")
ax.plot(r * 1e3, sr, color=COLORS["pr"], lw=2, label="radial stress")
ax.axhline(mt.YS(bd.mech["T_disc"]), color="k", ls="--", lw=1, label=f"IN713C yield at {bd.mech['T_disc']:.0f} °C")
ax.axhline(avg, color=COLORS["stress"], ls=":", lw=1, label=f"average hoop {avg:.0f} MPa (burst criterion)")
ax.set_xlabel("Radius (mm)")
ax.set_ylabel("Stress (MPa)")
ax.set_title(f"D4  Turbine disc stresses at {base.rpm / 1e3:.0f} krpm (uniform disc, blades as rim load)")
ax.legend(fontsize=8)
save(fig, "D4_disc_stress", "analytic",
     f"Burst margin {bd.mech['burst_turbine']:.2f}× speed (Robinson, 0.85 UTS). Peak at the bore; a real disc thickened at the hub is lower.")

# ---------------- D5: overspeed — stresses vs rpm for the hot parts
rows = []
for rpm in np.arange(80_000, 150_001, 5_000):
    r_ = build(replace(base, rpm=rpm))
    # same hardware spun faster: scale stresses with speed squared from the design build
    k = (rpm / base.rpm) ** 2
    rows.append(dict(rpm=rpm, imp=bd.mech["stress_impeller"] * k, root=bd.mech["stress_blade_root"] * k,
                     disc=bd.mech["stress_disc_max"] * k))
dv = pd.DataFrame(rows)
save_csv(dv, "phase_d_overspeed")
fig, ax = plt.subplots(figsize=(7.5, 4.3))
ax.plot(dv.rpm / 1e3, dv.imp, color=MAT_COLORS["Al2618"], lw=2, label="impeller peak (Al 2618)")
ax.plot(dv.rpm / 1e3, dv.root, color=MAT_COLORS["IN713C"], lw=2, label="turbine blade root (IN713C)")
ax.plot(dv.rpm / 1e3, dv.disc, color=MAT_COLORS["MARM247"], lw=2, label="turbine disc bore (IN713C)")
ax.axhline(MATERIALS["Al2618"].YS(bd.mech["T_impeller"]), color=MAT_COLORS["Al2618"], ls="--", lw=1)
ax.axhline(mt.YS(bd.mech["T_disc"]), color=MAT_COLORS["MARM247"], ls="--", lw=1)
ax.axvline(base.rpm / 1e3, color="k", ls=":")
ax.axvline(base.rpm * 1.05 / 1e3, color="r", ls=":")
ax.text(base.rpm * 1.05 / 1e3 + 0.5, ax.get_ylim()[1] * 0.95, "governor limit +5 %", color="r", fontsize=8)
ax.set_xlabel("Shaft speed of the as-built rotor (krpm)")
ax.set_ylabel("Stress (MPa)")
ax.set_title("D5  Overspeed: stresses grow with speed squared (dashed = yield)")
ax.legend(fontsize=8)
save(fig, "D5_overspeed", "analytic", "Same hardware spun faster; metal temperatures held at design values.")
print(bd.turb)
print(dl.loc[(dl.phi == 0.65)].round(3).to_string(index=False))
