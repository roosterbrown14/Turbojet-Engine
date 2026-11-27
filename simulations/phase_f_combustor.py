"""Phase F: combustor and fuels. Flame temperature, fuel comparison, air split, liner length,
combustion efficiency.
"""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tj import combustor as cb  # noqa: E402
from tj.engine import EngineSpec, build  # noqa: E402
from tj.fuels import FUELS  # noqa: E402
from tj.gas import flame_temperature  # noqa: E402
from tj.plotting import COLORS, plt, save, save_csv  # noqa: E402

base = EngineSpec()
bd = build(base)
T03 = bd.cyc["T03"]
FCOL = {"Jet A-1": "#2563eb", "Kerosene (K-1)": "#60a5fa", "Diesel": "#4b5563", "Propane": "#d97706",
        "Butane": "#f59e0b", "Ethanol": "#059669"}

# ---------------- F1: flame temperature vs equivalence ratio
fig, ax = plt.subplots(figsize=(8, 4.8))
rows = []
for name, fu in FUELS.items():
    phis = np.linspace(0.15, 1.0, 40)
    T = [flame_temperature(T03, p * fu.far_stoich, name) for p in phis]
    ax.plot(phis, np.array(T) - 273.15, color=FCOL[name], lw=2, label=name)
    rows += [dict(fuel=name, phi=p, T_flame_C=t - 273.15) for p, t in zip(phis, T)]
save_csv(pd.DataFrame(rows), "phase_f_flame_temperature")
ax.axvline(bd.cyc["phi"], color="k", ls=":")
ax.text(bd.cyc["phi"] + 0.01, 300, "overall engine\n(turbine inlet)", fontsize=8)
ax.axvspan(0.8, 1.0, color=COLORS["tit"], alpha=0.08)
ax.text(0.81, 300, "primary zone", fontsize=8, color=COLORS["tit"])
ax.set_xlabel("Equivalence ratio φ (1 = stoichiometric)")
ax.set_ylabel("Adiabatic flame temperature (°C)")
ax.set_title(f"F1  Flame temperature with {T03 - 273.15:.0f} °C inlet air")
ax.legend(fontsize=8)
save(fig, "F1_flame_temperature", "analytic", "Complete combustion, no dissociation: overstates temperatures above ~1800 °C by up to ~150 °C.")

# ---------------- F2: fuel comparison at the design point
rows = []
for name, fu in FUELS.items():
    r = build(replace(base, fuel=name))
    rows.append(dict(fuel=name, thrust=r.thrust, mdot_fuel_g_s=r.cyc["mdot_fuel"] * 1e3, L_min=r.cyc["fuel_l_per_min"],
                     tsfc=r.cyc["tsfc_g_per_kNs"], tank_L_10min=r.cyc["fuel_l_per_min"] * 10, LHV_MJ=fu.LHV / 1e6,
                     flash_C=fu.flash_c, CO2_g_s=r.cyc["mdot_fuel"] * 1e3 * fu.C * 44.01 / (fu.M * 1000)))
df = pd.DataFrame(rows)
save_csv(df, "phase_f_fuels")
fig, axs = plt.subplots(1, 3, figsize=(14, 4.2))
cols = [FCOL[f] for f in df.fuel]
axs[0].bar(df.fuel, df.mdot_fuel_g_s, color=cols)
axs[0].set_ylabel("Fuel mass flow (g/s)")
axs[1].bar(df.fuel, df.tank_L_10min, color=cols)
axs[1].set_ylabel("Fuel volume for 10 min at full power (L)")
axs[2].bar(df.fuel, df.CO2_g_s, color=cols)
axs[2].set_ylabel("CO₂ emitted (g/s)")
for ax in axs:
    ax.tick_params(axis="x", rotation=35, labelsize=8)
fig.suptitle("F2  Fuels at the design point (same thrust): Jet A-1 or kerosene is the practical choice", fontweight="bold")
save(fig, "F2_fuel_comparison", "sim", "Same 1100 K turbine inlet temperature. Propane/butane volumes are as pressurized liquid.")

# ---------------- F3: air split along the liner
fig, ax = plt.subplots(figsize=(8, 3.6))
o = bd.comb
zones = [("Primary zone\n(vaporizers + 1st holes)", 0.30, COLORS["tit"]), ("Secondary zone", 0.25, COLORS["egt"]),
         ("Dilution zone", 0.45, COLORS["flow"])]
left = 0
for name, frac, c in zones:
    ax.barh(0, frac * 100, left=left, color=c, edgecolor="white")
    ax.text(left + frac * 50, 0, f"{name}\n{frac * 100:.0f} % of air", ha="center", va="center", fontsize=8, color="white")
    left += frac * 100
ax.set_yticks([])
ax.set_xlabel("Share of combustor air (%)")
ax.set_title(f"F3  Air split: primary-zone φ ≈ {o['phi_primary']:.2f}, overall φ = {o['phi_overall']:.2f}")
save(fig, "F3_air_split", "sim", f"Hole area (Cd 0.6) for a 5 % pressure loss: {o['A_holes'] * 1e6:.0f} mm² in total.")

# ---------------- F4: liner length -> residence time, engine length
rows = []
for L in np.linspace(0.04, 0.12, 17):
    c = cb.CombustorDesign(mdot_air=base.mdot * 0.98, far=bd.cyc["far"], T03=T03, p03=bd.cyc["p03"],
                           r_in=bd.geom["liner_in"], r_out=bd.geom["liner_out"], length=L)
    out = cb.size(c)
    rows.append(dict(L_mm=L * 1e3, tau_ms=out["tau"] * 1e3, V_ref=out["V_ref"], volume_cm3=out["volume"] * 1e6))
dl = pd.DataFrame(rows)
save_csv(dl, "phase_f_liner_length")
fig, ax = plt.subplots(figsize=(7.5, 4.3))
ax.plot(dl.L_mm, dl.tau_ms, "-o", ms=3, color=COLORS["tit"], lw=2)
ax.axhspan(3, 8, color=COLORS["flow"], alpha=0.12)
ax.text(42, 7.2, "typical small-engine residence time 3-8 ms", fontsize=8, color=COLORS["flow"])
ax.axvline(bd.geom["liner_len"] * 1e3, color="k", ls=":")
ax.set_xlabel("Liner length (mm)")
ax.set_ylabel("Bulk residence time (ms)")
ax.set_title("F4  Combustor length vs residence time (time the fuel has to burn)")
save(fig, "F4_liner_length", "analytic", f"Annulus {bd.geom['liner_in'] * 1e3:.0f}-{bd.geom['liner_out'] * 1e3:.0f} mm radius; bulk gas density at combustor inlet.")

# ---------------- F5: combustion efficiency
rows = []
for eb in np.linspace(0.75, 0.99, 13):
    r = build(replace(base, eta_b=eb))
    rows.append(dict(eta_b=eb, tsfc=r.cyc["tsfc_g_per_kNs"], L_min=r.cyc["fuel_l_per_min"], thrust=r.thrust))
de = pd.DataFrame(rows)
save_csv(de, "phase_f_combustion_efficiency")
fig, ax = plt.subplots(figsize=(7.5, 4.3))
ax.plot(de.eta_b, de.L_min, "-o", ms=3, color=COLORS["tsfc"], lw=2)
ax.axvspan(0.85, 0.95, color=COLORS["flow"], alpha=0.12)
ax.text(0.855, de.L_min.max() * 0.98, "reported for small\nvaporizer engines", fontsize=8, color=COLORS["flow"])
ax.set_xlabel("Combustion efficiency")
ax.set_ylabel("Fuel flow at full power (L/min)")
ax.set_title("F5  Combustion efficiency only changes fuel use (thrust unchanged at fixed TIT)")
save(fig, "F5_combustion_efficiency", "sim")
print(df.round(3).to_string(index=False))
print(bd.comb)
