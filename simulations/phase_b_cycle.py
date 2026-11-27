"""Phase B: cycle trade studies. Pressure ratio x turbine inlet temperature, component efficiencies,
engine size (mass flow).

Every point is a full engine build: compressor and turbine efficiencies come from the meanline
models, so changing PR also changes the compressor tip speed and efficiency.
"""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tj import cycle as cy  # noqa: E402
from tj.engine import EngineSpec, build  # noqa: E402
from tj.plotting import COLORS, plt, save, save_csv  # noqa: E402

base = EngineSpec()
bd = build(base)

# ---------------- B1: PR x TIT carpet
rows = []
for pr in np.arange(2.0, 4.01, 0.25):
    for tit in np.arange(950, 1251, 50):
        r = build(replace(base, pr=pr, TIT=tit))
        rows.append(dict(pr=pr, TIT=tit, thrust=r.thrust, specific_thrust=r.cyc["specific_thrust"],
                         tsfc=r.cyc["tsfc_g_per_kNs"], EGT_C=r.cyc["EGT"] - 273.15, eta_c=r.comp["eta"],
                         eta_t=r.turb["eta"], U2=r.comp["U2"], sf_imp=r.mech["sf_impeller"],
                         life_blade=r.mech["life_blade_h"], D2_mm=r.comp["D2"] * 1e3))
df = pd.DataFrame(rows)
save_csv(df, "phase_b_carpet")

fig, ax = plt.subplots(figsize=(8, 5.5))
for pr, g in df.groupby("pr"):
    ax.plot(g.specific_thrust, g.tsfc, color=COLORS["pr"], lw=0.9)
    ax.text(g.specific_thrust.iloc[-1] + 3, g.tsfc.iloc[-1], f"PR {pr:.2f}", fontsize=7, color=COLORS["pr"])
for tit, g in df.groupby("TIT"):
    ax.plot(g.specific_thrust, g.tsfc, color=COLORS["tit"], lw=0.9, ls="--")
    ax.text(g.specific_thrust.iloc[0], g.tsfc.iloc[0] + 0.6, f"{tit:.0f} K", fontsize=7, color=COLORS["tit"], ha="center")
ax.plot(bd.cyc["specific_thrust"], bd.cyc["tsfc_g_per_kNs"], "*", ms=14, color=COLORS["design"], label="TJ-110 design")
ax.set_xlabel("Specific thrust (N per kg/s of air)")
ax.set_ylabel("TSFC (g of fuel per kN·s)")
ax.set_title("B1  Cycle carpet: pressure ratio (solid) × turbine inlet temperature (dashed)")
ax.legend(loc="upper right")
save(fig, "B1_cycle_carpet", "sim", "0.25 kg/s, 110 krpm, sea-level static. Up and right = more thrust per kg of air; down = better fuel economy.")

# ---------------- B2: feasibility map: PR x TIT shaded by constraints
fig, axs = plt.subplots(1, 3, figsize=(14, 4.2))
P = df.pivot(index="TIT", columns="pr", values="thrust")
E = df.pivot(index="TIT", columns="pr", values="EGT_C")
S = df.pivot(index="TIT", columns="pr", values="sf_imp")
for ax, Z, title, cmap in ((axs[0], P, "Thrust (N)", "Blues"), (axs[1], E, "Exhaust gas temperature (°C)", "Oranges"),
                           (axs[2], S, "Impeller safety factor on yield", "Greens")):
    cs = ax.contourf(Z.columns, Z.index, Z.values, 14, cmap=cmap)
    fig.colorbar(cs, ax=ax)
    ax.contour(Z.columns, Z.index, Z.values, cs.levels[::3], colors="k", linewidths=0.4)
    ax.plot(base.pr, base.TIT, "*", ms=13, color="k")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("Compressor pressure ratio")
axs[0].set_ylabel("Turbine inlet temperature (K)")
axs[1].contour(E.columns, E.index, E.values, [750], colors="r", linewidths=2)
axs[2].contour(S.columns, S.index, S.values, [1.2], colors="r", linewidths=2)
fig.suptitle("B2  What PR and TIT do to thrust, EGT and the compressor wheel (red: EGT 750 °C, SF 1.2)", fontweight="bold")
save(fig, "B2_pr_tit_maps", "sim", "Higher PR at a fixed shaft speed needs a bigger, faster impeller, which is what drives its safety factor down.")

# ---------------- B3: component efficiencies
rows = []
for name, key, rng in (("Compressor η", "eta_c", np.linspace(0.65, 0.85, 9)),
                       ("Turbine η", "eta_t", np.linspace(0.70, 0.90, 9)),
                       ("Combustion η", "eta_b", np.linspace(0.80, 0.99, 9))):
    for v in rng:
        ci = cy.CycleInputs(mdot=base.mdot, pr_c=base.pr, eta_c=bd.comp["eta"], TIT=base.TIT, eta_t=bd.turb["eta"],
                            eta_b=base.eta_b)
        ci = replace(ci, **{key: v})
        r = cy.run(ci)
        rows.append(dict(component=name, eta=v, thrust=r["thrust"], tsfc=r["tsfc_g_per_kNs"], EGT_C=r["EGT"] - 273.15))
de = pd.DataFrame(rows)
save_csv(de, "phase_b_efficiencies")
fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
cols = {"Compressor η": COLORS["pr"], "Turbine η": COLORS["egt"], "Combustion η": COLORS["tit"]}
for name, g in de.groupby("component"):
    axs[0].plot(g.eta, g.thrust, "-o", ms=3, color=cols[name], label=name)
    axs[1].plot(g.eta, g.tsfc, "-o", ms=3, color=cols[name], label=name)
axs[0].set_ylabel("Thrust (N)")
axs[1].set_ylabel("TSFC (g/kN·s)")
for ax in axs:
    ax.set_xlabel("Component efficiency")
    ax.legend()
fig.suptitle("B3  Component efficiency: the compressor and turbine matter far more than the burner for thrust",
             fontweight="bold")
save(fig, "B3_component_efficiency", "sim", "Fixed PR 2.8, TIT 1100 K, 0.25 kg/s. Combustion efficiency only changes fuel use, not thrust.")

# ---------------- B4: engine size
rows = []
for m in np.linspace(0.10, 0.50, 17):
    rpm = base.rpm * np.sqrt(base.mdot / m)          # constant tip speed scaling
    r = build(replace(base, mdot=m, rpm=rpm))
    rows.append(dict(mdot=m, rpm=rpm, thrust=r.thrust, tsfc=r.cyc["tsfc_g_per_kNs"], eta_c=r.comp["eta"],
                     eta_t=r.turb["eta"], D_case_mm=r.geom["D_case"] * 1e3, thrust_per_area=r.thrust / (np.pi / 4 * r.geom["D_case"] ** 2)))
dm = pd.DataFrame(rows)
save_csv(dm, "phase_b_size")
fig, axs = plt.subplots(1, 3, figsize=(14, 4))
axs[0].plot(dm.D_case_mm, dm.thrust, "-o", ms=3, color=COLORS["thrust"])
axs[0].set_ylabel("Thrust (N)")
axs[1].plot(dm.D_case_mm, dm.eta_c, "-o", ms=3, color=COLORS["pr"], label="compressor")
axs[1].plot(dm.D_case_mm, dm.eta_t, "-o", ms=3, color=COLORS["egt"], label="turbine")
axs[1].set_ylabel("Efficiency")
axs[1].legend()
axs[2].plot(dm.D_case_mm, dm.tsfc, "-o", ms=3, color=COLORS["tsfc"])
axs[2].set_ylabel("TSFC (g/kN·s)")
for ax in axs:
    ax.set_xlabel("Engine outer diameter (mm)")
    ax.axvline(bd.geom["D_case"] * 1e3, color="k", lw=0.8, ls=":")
fig.suptitle("B4  Engine size: small engines lose efficiency (Reynolds number and fixed 0.3 mm clearances)", fontweight="bold")
save(fig, "B4_engine_size", "sim", "Mass flow 0.10-0.50 kg/s; shaft speed scaled to keep tip speeds constant; same PR and TIT.")
print(df.loc[df.thrust.idxmax()])
print(dm[["mdot", "D_case_mm", "thrust", "tsfc"]].round(2).to_string(index=False))
