"""Phase C: compressor design choices. Shaft speed vs wheel size and stress, backsweep, blade count,
tip clearance, the compressor map with the engine running line.
"""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tj import compressor as cm  # noqa: E402
from tj.engine import EngineSpec, build  # noqa: E402
from tj.materials import MATERIALS  # noqa: E402
from tj.offdesign import OffDesign  # noqa: E402
from tj.plotting import COLORS, MAT_COLORS, plt, save, save_csv  # noqa: E402

base = EngineSpec()
bd = build(base)

# ---------------- C1: shaft speed -> wheel size, tip speed, stress per material
rows = []
for rpm in np.arange(80_000, 150_001, 5_000):
    r = build(replace(base, rpm=rpm))
    d = dict(rpm=rpm, D2_mm=r.comp["D2"] * 1e3, U2=r.comp["U2"], eta_c=r.comp["eta"], M1rel=r.comp["M1rel"],
             thrust=r.thrust, Ns=r.comp["Ns"], D_case_mm=r.geom["D_case"] * 1e3, T_imp=r.mech["T_impeller"])
    for k in ("Al2618", "Al7075", "Ti64"):
        s, sf, burst = cm.impeller_stress(r.comp["U2"], MATERIALS[k], r.mech["T_impeller"])
        d[f"sf_{k}"] = sf
        d[f"burst_{k}"] = burst
    rows.append(d)
df = pd.DataFrame(rows)
save_csv(df, "phase_c_speed")
fig, axs = plt.subplots(1, 3, figsize=(14, 4.2))
axs[0].plot(df.rpm / 1e3, df.D2_mm, "-o", ms=3, color=COLORS["pr"], label="impeller tip Ø")
axs[0].plot(df.rpm / 1e3, df.D_case_mm, "-o", ms=3, color=COLORS["margin"], label="engine outer Ø")
axs[0].set_ylabel("Diameter (mm)")
axs[0].legend()
axs[1].plot(df.rpm / 1e3, df.eta_c, "-o", ms=3, color=COLORS["eta"])
axs[1].set_ylabel("Compressor stage efficiency")
ax3 = axs[1].twinx()
ax3.plot(df.rpm / 1e3, df.M1rel, "--", color=COLORS["tsfc"])
ax3.set_ylabel("Inducer tip relative Mach (dashed)", color=COLORS["tsfc"])
ax3.grid(False)
for k in ("Al2618", "Al7075", "Ti64"):
    axs[2].plot(df.rpm / 1e3, df[f"sf_{k}"], "-o", ms=3, color=MAT_COLORS[k], label=MATERIALS[k].name)
axs[2].axhline(1.2, color="r", ls=":", lw=1)
axs[2].text(81, 1.22, "minimum SF 1.2", color="r", fontsize=8)
axs[2].set_ylabel("Impeller yield safety factor")
axs[2].legend(fontsize=8)
for ax in axs:
    ax.set_xlabel("Design shaft speed (krpm)")
    ax.axvline(base.rpm / 1e3, color="k", lw=0.8, ls=":")
fig.suptitle("C1  Faster shaft = smaller engine, but the tip speed (and so wheel stress) hardly changes", fontweight="bold")
save(fig, "C1_shaft_speed", "sim", "PR 2.8, 0.25 kg/s. Tip speed is set by the work, not the rpm; rpm only sets the diameter.")

# ---------------- C2: backsweep and blade count
rows = []
for b in np.arange(0, 51, 5):
    for Z in (10, 12, 14, 16, 20):
        r = build(replace(base, beta2b=float(b), Z=Z))
        rows.append(dict(beta2b=b, Z=Z, U2=r.comp["U2"], eta=r.comp["eta"], sigma=r.comp["sigma"],
                         sf=r.mech["sf_impeller"], thrust=r.thrust, D2=r.comp["D2"] * 1e3))
db = pd.DataFrame(rows)
save_csv(db, "phase_c_backsweep")
fig, axs = plt.subplots(1, 3, figsize=(14, 4.2))
cm_ = plt.cm.viridis
for i, (Z, g) in enumerate(db.groupby("Z")):
    c = cm_(i / 4)
    axs[0].plot(g.beta2b, g.U2, "-o", ms=3, color=c, label=f"Z = {Z}")
    axs[1].plot(g.beta2b, g.thrust, "-o", ms=3, color=c)
    axs[2].plot(g.beta2b, g.sf, "-o", ms=3, color=c)
axs[0].set_ylabel("Required tip speed U2 (m/s)")
axs[1].set_ylabel("Engine thrust (N)")
axs[2].set_ylabel("Impeller yield safety factor (Al 2618)")
axs[2].axhline(1.2, color="r", ls=":")
axs[0].legend(fontsize=8)
for ax in axs:
    ax.set_xlabel("Exit blade backsweep from radial (deg)")
    ax.axvline(base.beta2b, color="k", lw=0.8, ls=":")
fig.suptitle("C2  Backsweep and blade count: more backsweep is more efficient but needs a faster, more stressed wheel",
             fontweight="bold")
save(fig, "C2_backsweep_blades", "sim", "Z counts main + splitter blades at the exit. Slip from Wiesner (1967).")

# ---------------- C3: tip clearance
rows = []
for cl in np.arange(0.1, 0.81, 0.05):
    r = build(replace(base, clear_c=cl * 1e-3))
    r2 = build(replace(base, clear_t=cl * 1e-3))
    rows.append(dict(clearance_mm=cl, eta_c=r.comp["eta"], thrust_c=r.thrust, eta_t=r2.turb["eta"], thrust_t=r2.thrust,
                     tsfc_c=r.cyc["tsfc_g_per_kNs"], tsfc_t=r2.cyc["tsfc_g_per_kNs"]))
dc = pd.DataFrame(rows)
save_csv(dc, "phase_c_clearance")
fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
axs[0].plot(dc.clearance_mm, dc.eta_c, "-o", ms=3, color=COLORS["pr"], label="compressor (only its clearance varied)")
axs[0].plot(dc.clearance_mm, dc.eta_t, "-o", ms=3, color=COLORS["egt"], label="turbine (only its clearance varied)")
axs[0].set_ylabel("Component efficiency")
axs[1].plot(dc.clearance_mm, dc.thrust_c, "-o", ms=3, color=COLORS["pr"], label="compressor clearance")
axs[1].plot(dc.clearance_mm, dc.thrust_t, "-o", ms=3, color=COLORS["egt"], label="turbine clearance")
axs[1].set_ylabel("Thrust at fixed TIT (N)")
for ax in axs:
    ax.set_xlabel("Tip clearance (mm)")
    ax.axvline(0.3, color="k", lw=0.8, ls=":")
    ax.legend(fontsize=8)
fig.suptitle("C3  Tip clearance: every 0.1 mm costs thrust. Turbine clearance hurts most (short blades)", fontweight="bold")
save(fig, "C3_tip_clearance", "sim", "Compressor: Δη = 0.35 ε/b2; turbine: Δη = 2 ε/h. Design value 0.3 mm (dotted).")

# ---------------- C4: compressor map with running line
od = OffDesign(bd)
mp = od.map
fig, ax = plt.subplots(figsize=(8.5, 6))
Q, PR, E = [], [], []
for n in np.linspace(0.45, 1.05, 49):
    q, pr, eta = mp.speed_line(n, 60)
    Q.append(q); PR.append(pr); E.append(eta)
sc = ax.contourf(np.array(Q), np.array(PR), np.array(E), levels=np.arange(0.50, 0.785, 0.02), cmap="YlGnBu", alpha=0.75)
for n in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.05):
    q, pr, eta = mp.speed_line(n, 50)
    ax.plot(q, pr, color="#374151", lw=1)
    ax.text(q[-1] + 0.003, pr[-1], f"{n * 100:.0f} %", fontsize=8, color="#374151", va="center")
fig.colorbar(sc, ax=ax, label="Isentropic efficiency")
ns = np.linspace(0.45, 1.05, 30)
ax.plot([mp.q_surge(n) for n in ns], [mp.pr(mp.q_surge(n), n) for n in ns], "r-", lw=2, label="surge line (assumed)")
rl = od.running_line(np.linspace(0.5, 1.05, 23))
rl = [p for p in rl if p["converged"]]
ax.plot([p["qc"] for p in rl], [p["prc"] for p in rl], "k-o", ms=3, lw=2, label="engine running line (model)")
ax.plot(base.mdot, base.pr, "*", ms=15, color="gold", mec="k", label="design point")
ax.set_xlabel("Corrected air mass flow (kg/s)")
ax.set_ylabel("Total pressure ratio")
ax.set_title("C4  Compressor map with the TJ-110 running line")
ax.legend(loc="upper left", fontsize=8)
save(fig, "C4_compressor_map", "od",
     "Semi-empirical map from the meanline design (shape assumed from typical small-turbocharger maps, not measured). Labels: % design speed.")
pd.DataFrame([{k: v for k, v in p.items() if k != "x"} for p in rl]).to_csv(
    Path(__file__).resolve().parents[1] / "data" / "phase_c_running_line.csv", index=False)
print(df[["rpm", "D2_mm", "U2", "eta_c", "sf_Al2618", "sf_Ti64"]].round(3).to_string(index=False))
print(dc.round(3).to_string(index=False))
