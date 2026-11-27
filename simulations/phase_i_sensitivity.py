"""Phase I: sensitivity (tornado) and Monte Carlo uncertainty of the design-point predictions, and a
design-space search for the best feasible PR / speed / TIT.
"""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tj.engine import EngineSpec, build  # noqa: E402
from tj.plotting import COLORS, plt, save, save_csv  # noqa: E402

base = EngineSpec()
bd = build(base)
F0, S0, E0 = bd.thrust, bd.cyc["tsfc_g_per_kNs"], bd.cyc["EGT"] - 273.15

# uncertain inputs: (label, field, low, high)
UNC = [
    ("Compressor build quality (−2/+6 pts)", "build_penalty", 0.00, 0.06),
    ("Compressor tip clearance 0.15–0.5 mm", "clear_c", 0.15e-3, 0.5e-3),
    ("Turbine tip clearance 0.15–0.5 mm", "clear_t", 0.15e-3, 0.5e-3),
    ("Combustion efficiency 0.85–0.95", "eta_b", 0.85, 0.95),
    ("Combustor pressure loss 3–8 %", "dp_comb", 0.03, 0.08),
    ("Turbine inlet temp. ±50 K", "TIT", base.TIT - 50, base.TIT + 50),
    ("Ambient −20 to +35 °C", "T0", 253.15, 308.15),
    ("Air flow ±5 %", "mdot", base.mdot * 0.95, base.mdot * 1.05),
]

rows = []
for lab, f, lo, hi in UNC:
    rl, rh = build(replace(base, **{f: lo})), build(replace(base, **{f: hi}))
    rows.append(dict(input=lab, field=f, thrust_lo=rl.thrust - F0, thrust_hi=rh.thrust - F0,
                     tsfc_lo=rl.cyc["tsfc_g_per_kNs"] - S0, tsfc_hi=rh.cyc["tsfc_g_per_kNs"] - S0,
                     egt_lo=rl.cyc["EGT"] - 273.15 - E0, egt_hi=rh.cyc["EGT"] - 273.15 - E0))
dt = pd.DataFrame(rows)
save_csv(dt, "phase_i_tornado")
fig, axs = plt.subplots(1, 2, figsize=(14, 4.8), sharey=True)
for ax, key, unit, base_v in ((axs[0], "thrust", "N", F0), (axs[1], "tsfc", "g/kN·s", S0)):
    d = dt.assign(span=(dt[f"{key}_hi"] - dt[f"{key}_lo"]).abs()).sort_values("span")
    y = np.arange(len(d))
    ax.barh(y, d[f"{key}_lo"], color=COLORS["margin"], label="low end of range")
    ax.barh(y, d[f"{key}_hi"], color=COLORS["thrust"] if key == "thrust" else COLORS["tsfc"], label="high end of range")
    ax.set_yticks(y, d.input, fontsize=8)
    ax.axvline(0, color="k", lw=0.8)
    ax.set_xlabel(f"Change in {'thrust' if key == 'thrust' else 'TSFC'} ({unit}) from {base_v:.1f}")
    ax.legend(fontsize=8, loc="lower right")
fig.suptitle("I1  What the predictions depend on most (one input at a time)", fontweight="bold")
save(fig, "I1_tornado", "sim")

# ---------------- I2: Monte Carlo
rng = np.random.default_rng(42)
N = 1500
mc = []
for _ in range(N):
    kw = {f: rng.uniform(lo, hi) for _, f, lo, hi in UNC if f not in ("T0",)}
    r = build(replace(base, **kw))
    mc.append(dict(**kw, thrust=r.thrust, tsfc=r.cyc["tsfc_g_per_kNs"], EGT_C=r.cyc["EGT"] - 273.15,
                   eta_c=r.comp["eta"], eta_t=r.turb["eta"]))
dm = pd.DataFrame(mc)
save_csv(dm, "phase_i_monte_carlo")
q = dm[["thrust", "tsfc", "EGT_C"]].quantile([0.05, 0.5, 0.95])
save_csv(q.reset_index().rename(columns={"index": "quantile"}), "phase_i_monte_carlo_summary")
fig, axs = plt.subplots(1, 3, figsize=(14, 4))
for ax, k, lab, c in ((axs[0], "thrust", "Thrust (N)", COLORS["thrust"]), (axs[1], "tsfc", "TSFC (g/kN·s)", COLORS["tsfc"]),
                      (axs[2], "EGT_C", "EGT (°C)", COLORS["egt"])):
    ax.hist(dm[k], bins=40, color=c, alpha=0.8)
    for qq in (0.05, 0.95):
        ax.axvline(q.loc[qq, k], color="k", ls="--", lw=1)
    ax.axvline(q.loc[0.5, k], color="k", lw=1.5)
    ax.set_xlabel(lab)
    ax.set_title(f"90 % range {q.loc[0.05, k]:.0f}–{q.loc[0.95, k]:.0f}", fontsize=10)
axs[0].set_ylabel("Count")
fig.suptitle(f"I2  Monte Carlo ({N} builds, uniform input ranges from I1, ISA day)", fontweight="bold")
save(fig, "I2_monte_carlo", "sim", "Covers parameter uncertainty only. Model-form error (map shape, loss correlations) comes on top.")

# ---------------- I3: design-space search
rows = []
for pr in np.arange(2.2, 3.61, 0.1):
    for rpm in np.arange(90_000, 140_001, 5_000):
        for tit in (1050, 1100, 1150, 1200):
            r = build(replace(base, pr=pr, rpm=rpm, TIT=tit))
            feas = (r.mech["sf_impeller"] >= 1.2 and r.mech["life_blade_h"] >= 1000 and r.cyc["EGT"] - 273.15 <= 750
                    and r.mech["burst_turbine"] >= 1.4 and r.turb["M2"] < 0.95 and r.comp["M1rel"] < 1.0)
            rows.append(dict(pr=pr, rpm=rpm, TIT=tit, thrust=r.thrust, tsfc=r.cyc["tsfc_g_per_kNs"],
                             D_case=r.geom["D_case"] * 1e3, sf_imp=r.mech["sf_impeller"], EGT_C=r.cyc["EGT"] - 273.15,
                             life=r.mech["life_blade_h"], feasible=feas))
dd = pd.DataFrame(rows)
save_csv(dd, "phase_i_design_space")
fig, ax = plt.subplots(figsize=(8.5, 5.5))
nf = dd[~dd.feasible]
f = dd[dd.feasible]
ax.scatter(nf.tsfc, nf.thrust / (np.pi / 4 * (nf.D_case / 1e3) ** 2) / 1e3, s=8, color="#d1d5db", label="violates a limit")
sc = ax.scatter(f.tsfc, f.thrust / (np.pi / 4 * (f.D_case / 1e3) ** 2) / 1e3, s=14, c=f.pr, cmap="viridis", label="feasible")
fig.colorbar(sc, ax=ax, label="Pressure ratio")
ax.plot(S0, F0 / (np.pi / 4 * bd.geom["D_case"] ** 2) / 1e3, "*", ms=16, color="gold", mec="k", label="TJ-110")
ax.set_xlabel("TSFC (g/kN·s)  ← better")
ax.set_ylabel("Thrust per frontal area (kN/m²)  → better")
ax.set_title("I3  Design space: PR 2.2–3.6, 90–140 krpm, TIT 1050–1200 K")
ax.legend(fontsize=8)
save(fig, "I3_design_space", "sim",
     "Limits: impeller SF ≥ 1.2, blade life ≥ 1000 h, EGT ≤ 750 °C, turbine burst margin ≥ 1.4, NGV Mach < 0.95, inducer Mach < 1.")
print(dt.round(2).to_string(index=False))
print(q.round(1))
print(f.sort_values("thrust", ascending=False).head(8).round(2).to_string(index=False))
