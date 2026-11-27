"""Phase A: the design point of TJ-110. Station table, T-s diagram, station profiles, energy flow.

Writes data/design_point.json (read by CAD, drawings and the report), data/phase_a_stations.csv,
charts A1-A4.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tj import cycle as cy  # noqa: E402
from tj.engine import EngineSpec, build  # noqa: E402
from tj.fuels import FUELS  # noqa: E402
from tj.gas import air  # noqa: E402
from tj.plotting import COLORS, DATA, plt, save, save_csv  # noqa: E402

spec = EngineSpec()
r = build(spec, rotordynamics=True)
c = r.cyc
st = c["stations"]

rows = []
names = {0: "Ambient", 1: "Compressor face", 3: "Diffuser exit / combustor inlet", 4: "Turbine inlet (NGV)",
         5: "Turbine exit", 9: "Nozzle exit"}
for k in (0, 1, 3, 4, 5, 9):
    d = st[k]
    T = d.get("T", d["T0"])
    p = d.get("p", d["p0"])
    rows.append(dict(station=k, name=names[k], T0_K=round(d["T0"], 1), T0_C=round(d["T0"] - 273.15, 1),
                     p0_kPa=round(d["p0"] / 1e3, 2), T_static_K=round(T, 1), p_static_kPa=round(p / 1e3, 2),
                     velocity_m_s=round(d.get("V", 0.0), 1)))
df = pd.DataFrame(rows)
save_csv(df, "phase_a_stations")


def f(x):
    if isinstance(x, (np.floating, float)):
        return float(x)
    if isinstance(x, (np.integer, int)):
        return int(x)
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    if isinstance(x, (list, tuple)):
        return [f(v) for v in x]
    return x


summary = {
    "spec": {k: f(v) for k, v in spec.__dict__.items()},
    "performance": {k: f(c[k]) for k in ("thrust", "tsfc_g_per_kNs", "mdot_fuel", "fuel_l_per_min", "far", "phi",
                                         "specific_thrust", "V9", "D9", "M9", "choked", "EGT", "T03", "p03", "pr_t",
                                         "P_comp", "P_jet", "eta_thermal")},
    "compressor": {k: f(v) for k, v in r.comp.items()},
    "turbine": {k: f(v) for k, v in r.turb.items()},
    "combustor": {k: f(v) for k, v in r.comb.items()},
    "mechanical": {k: f(v) for k, v in r.mech.items()},
    "geometry": {k: f(v) for k, v in r.geom.items()},
}
DATA.mkdir(exist_ok=True)
(DATA / "design_point.json").write_text(json.dumps(summary, indent=2))

# ---------------- A1: T-s diagram
ci = cy.CycleInputs(mdot=spec.mdot, pr_c=spec.pr, eta_c=r.comp["eta"], TIT=spec.TIT, eta_t=r.turb["eta"],
                    eta_b=spec.eta_b, dp_comb=spec.dp_comb)
pts, s_air, s_gas = cy.ts_points(ci)
fig, ax = plt.subplots(figsize=(7.5, 5.2))
g = c["gas"]
# isobars
for p, lab in ((st[0]["p0"], "ambient p"), (st[3]["p0"], "p03"), (st[4]["p0"], "p04"), (st[5]["p0"], "p05")):
    T = np.linspace(260, 1250, 100)
    sfun = s_air if p in (st[0]["p0"], st[3]["p0"]) else s_gas
    ax.plot([sfun(t, p) for t in T], T, color="#d1d5db", lw=0.8, zorder=0)
    ax.text(sfun(1240, p), 1240, f"{p / 1e3:.0f} kPa", fontsize=7, color="#9ca3af", ha="center", va="bottom")
seq = ["1", "3", "4", "5", "9"]
labels = {"1": "1 compressor face", "3": "3 compressor exit", "4": "4 turbine inlet", "5": "5 turbine exit",
          "9": "9 nozzle exit (static)"}
# combustion curve along p03 -> p04 (linear pressure loss)
Ts = np.linspace(st[3]["T0"], st[4]["T0"], 30)
ps = np.linspace(st[3]["p0"], st[4]["p0"], 30)
ax.plot([s_gas(t, p) for t, p in zip(Ts, ps)], Ts, color=COLORS["tit"], lw=2, label="combustion (heat added)")
ax.plot([pts["1"][0], pts["3"][0]], [pts["1"][1], pts["3"][1]], color=COLORS["pr"], lw=2, label="compression")
ax.plot([pts["4"][0], pts["5"][0]], [pts["4"][1], pts["5"][1]], color=COLORS["egt"], lw=2, label="turbine expansion")
ax.plot([pts["5"][0], pts["9"][0]], [pts["5"][1], pts["9"][1]], color=COLORS["thrust"], lw=2, label="nozzle expansion")
# ideal compression
T3s = air.T_isentropic(st[1]["T0"], spec.pr)
ax.plot([pts["1"][0], pts["1"][0]], [pts["1"][1], T3s], color=COLORS["pr"], lw=1, ls="--", label="ideal (isentropic)")
for k in seq:
    ax.plot(*pts[k], "o", color="k", ms=4)
    ax.annotate(labels[k], pts[k], xytext=(6, -2), textcoords="offset points", fontsize=8)
ax.set_xlabel("Specific entropy relative to ambient (J/(kg K))")
ax.set_ylabel("Temperature (K)")
ax.set_title("A1  TJ-110 design-point cycle (temperature-entropy)")
ax.legend(loc="upper left", fontsize=8)
save(fig, "A1_ts_diagram", "sim",
     f"Design point: {spec.mdot} kg/s, PR {spec.pr}, TIT {spec.TIT:.0f} K, {spec.rpm / 1e3:.0f} krpm, sea-level static ISA, Jet A-1.")

# ---------------- A2: station temperatures and pressures
fig, ax = plt.subplots(figsize=(8, 4.4))
lab = ["0\nambient", "1\ncomp. face", "3\ncomp. exit", "4\nturbine in", "5\nturbine out", "9\nnozzle exit"]
T0s = [st[k]["T0"] - 273.15 for k in (0, 1, 3, 4, 5, 9)]
p0s = [st[k]["p0"] / 1e3 for k in (0, 1, 3, 4, 5, 9)]
x = np.arange(6)
ax.bar(x - 0.2, T0s, 0.4, color=COLORS["egt"], label="total temperature (°C)")
ax2 = ax.twinx()
ax2.bar(x + 0.2, p0s, 0.4, color=COLORS["pr"], label="total pressure (kPa)")
for i, (t, p) in enumerate(zip(T0s, p0s)):
    ax.text(i - 0.2, t + 10, f"{t:.0f}", ha="center", fontsize=8)
    ax2.text(i + 0.2, p + 4, f"{p:.0f}", ha="center", fontsize=8)
ax.set_xticks(x, lab, fontsize=8)
ax.set_ylabel("Total temperature (°C)")
ax2.set_ylabel("Total pressure (kPa)")
ax2.grid(False)
ax2.spines["right"].set_visible(True)
ax.set_title("A2  Temperature and pressure through the engine")
h1, l1 = ax.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8)
save(fig, "A2_station_profile", "sim", "Station 9 shows total values; the nozzle is unchoked at this pressure ratio.")

# ---------------- A3: where the fuel energy goes
fuel = FUELS[spec.fuel]
Q = c["mdot_fuel"] * fuel.LHV
unburnt = Q / spec.eta_b * (1 - spec.eta_b)
jet = c["P_jet"]
mech = c["P_comp"] * (1 / 0.98 - 1)
leak = 0.02 * spec.mdot * c["w_c"]
heat = Q - jet - mech - leak
parts = [("Jet kinetic power (makes thrust)", jet, COLORS["thrust"]),
         ("Hot exhaust (heat thrown away)", heat, COLORS["egt"]),
         ("Leakage + bearing losses", mech + leak, COLORS["margin"]),
         ("Unburnt fuel (combustion inefficiency)", unburnt, "#9ca3af")]
fig, ax = plt.subplots(figsize=(8, 3.2))
left = 0
tot = Q + unburnt
for name, val, col in parts:
    ax.barh(0, val / 1e3, left=left / 1e3, color=col, edgecolor="white")
    ax.text((left + val / 2) / 1e3, 0, f"{name}\n{val / 1e3:.1f} kW ({100 * val / tot:.0f} %)", ha="center",
            va="center", fontsize=7.5, color="white" if col != "#9ca3af" else "black")
    left += val
ax.set_yticks([])
ax.set_xlabel("Power (kW)")
ax.set_title(f"A3  Where the fuel energy goes ({tot / 1e3:.1f} kW of fuel → {c['thrust']:.0f} N)")
ax.grid(axis="y", visible=False)
save(fig, "A3_energy_flow", "sim",
     "Compressor power is recycled inside the engine (turbine drives compressor) and is not a loss by itself.")

# ---------------- A4: component power balance
fig, ax = plt.subplots(figsize=(6.5, 3.6))
items = [("Compressor\nabsorbs", c["P_comp"] / 1e3, COLORS["pr"]),
         ("Turbine\ndelivers", c["m4"] * c["w_t"] / 1e3, COLORS["egt"]),
         ("Jet power\n(useful)", jet / 1e3, COLORS["thrust"]),
         ("Fuel heat\nreleased", Q / 1e3, COLORS["tit"])]
ax.bar([i[0] for i in items], [i[1] for i in items], color=[i[2] for i in items])
for i, it in enumerate(items):
    ax.text(i, it[1] + 0.8, f"{it[1]:.1f} kW", ha="center", fontsize=9)
ax.set_ylabel("Power (kW)")
ax.set_title("A4  Power balance at the design point")
save(fig, "A4_power_balance", "sim")

print(df.to_string(index=False))
print(json.dumps(summary["performance"], indent=1))
print("mech", {k: summary["mechanical"][k] for k in ("sf_impeller", "life_blade_h", "burst_turbine", "critical_rpm", "crit_margin")})
