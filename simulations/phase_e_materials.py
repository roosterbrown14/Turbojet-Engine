"""Phase E: materials. Strength and specific strength vs temperature, creep (Larson-Miller), turbine
creep life vs TIT, compressor wheel material vs tip speed, liner materials, thermal-expansion
clearance change, qualitative scorecard and a part-by-part selection table.

All property data are approximate handbook trends (see src/tj/materials.py); they rank materials
and size the design study. They are not design allowables.
"""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tj import compressor as cm  # noqa: E402
from tj.engine import EngineSpec, build  # noqa: E402
from tj.materials import LMP_C, MATERIALS  # noqa: E402
from tj.plotting import COLORS, MAT_COLORS, plt, save, save_csv  # noqa: E402

base = EngineSpec()
bd = build(base)

# ---------------- E1/E2: yield and specific strength vs temperature
fig, axs = plt.subplots(1, 2, figsize=(14, 5.2))
rows = []
for k, m in MATERIALS.items():
    T = np.linspace(m.t_tab[0], min(m.t_tab[-1], m.t_max + 50), 60)
    ys = [m.YS(t) for t in T]
    sp = [m.specific_strength(t) for t in T]
    axs[0].plot(T, ys, color=MAT_COLORS[k], lw=2)
    axs[1].plot(T, sp, color=MAT_COLORS[k], lw=2, label=m.name)
    axs[0].text(T[-1] + 8, ys[-1], k, fontsize=7, color=MAT_COLORS[k], va="center")
    for t in m.t_tab:
        rows.append(dict(material=m.name, T_C=t, UTS_MPa=m.UTS(t), YS_MPa=m.YS(t), density=m.density,
                         specific_YS_kNm_kg=m.specific_strength(t)))
save_csv(pd.DataFrame(rows), "phase_e_strength")
spans = [("compressor wheel", bd.mech["T_impeller"], COLORS["pr"]), ("turbine blade root", bd.mech["T_blade"], COLORS["tit"]),
         ("turbine disc", bd.mech["T_disc"], COLORS["egt"])]
for ax in axs:
    for lab, t, c in spans:
        ax.axvline(t, color=c, ls=":", lw=1.2)
        ax.text(t + 5, 0.02, lab, rotation=90, fontsize=8, color=c, va="bottom", transform=ax.get_xaxis_transform())
    ax.set_xlabel("Temperature (°C)")
axs[0].set_ylabel("0.2 % yield strength (MPa)")
axs[1].set_ylabel("Yield strength / density (kN·m/kg)")
axs[1].legend(fontsize=7, ncol=2, loc="upper right")
fig.suptitle("E1  Strength vs temperature: aluminum is lightest below ~200 °C, titanium to ~400 °C, nickel alloys above",
             fontweight="bold")
save(fig, "E1_strength_vs_temperature", "data", "Dotted lines: design-point metal temperatures in TJ-110.")

# ---------------- E3: Larson-Miller master curves with operating points
fig, ax = plt.subplots(figsize=(9, 5.5))
for k in ("IN713C", "MARM247", "IN718", "IN625", "HX", "H230", "SS310", "Ti64", "Al2618"):
    m = MATERIALS[k]
    P = np.linspace(min(p for p, _ in m.lmp_pts), max(p for p, _ in m.lmp_pts), 50)
    s = 10 ** np.polyval(m._lmp_fit(), P)
    ax.semilogy(P, s, color=MAT_COLORS[k], lw=2, label=m.name)
    ax.semilogy([p for p, _ in m.lmp_pts], [s for _, s in m.lmp_pts], "o", color=MAT_COLORS[k], ms=3)
for lab, T, s, mk in (("turbine blade root\n(1000 h)", bd.mech["T_blade"], bd.mech["stress_blade_root"], "*"),
                      ("turbine disc bore\n(1000 h)", bd.mech["T_disc"], bd.mech["stress_disc_max"], "D"),
                      ("impeller\n(1000 h)", bd.mech["T_impeller"], bd.mech["stress_impeller"], "s")):
    P = (T + 273.15) * (LMP_C + 3) / 1000
    ax.plot(P, s, mk, ms=12, color="k")
    ax.annotate(lab, (P, s), xytext=(8, 6), textcoords="offset points", fontsize=8)
ax.set_xlabel("Larson-Miller parameter P = T(K) · (20 + log₁₀ t_hours) / 1000")
ax.set_ylabel("Stress-rupture strength (MPa)")
ax.set_title("E3  Creep: stress-rupture master curves and where TJ-110's parts sit")
ax.legend(fontsize=7, ncol=2, loc="lower left")
save(fig, "E3_larson_miller", "data",
     "A part is safe for 1000 h if its marker sits BELOW its material's curve. Approximate representative curves.")

# ---------------- E4: turbine creep life vs TIT for three turbine alloys
rows = []
for tit in np.arange(1000, 1351, 25):
    r = build(replace(base, TIT=tit))
    for k in ("IN713C", "MARM247", "IN718"):
        m = MATERIALS[k]
        s = r.mech["stress_blade_root"] * m.density / MATERIALS[base.mat_turb].density
        rows.append(dict(TIT=tit, material=k, T_blade=r.mech["T_blade"], stress=s,
                         life_h=min(m.rupture_life(r.mech["T_blade"], s), 1e8), thrust=r.thrust))
dl = pd.DataFrame(rows)
save_csv(dl, "phase_e_turbine_life")
fig, ax = plt.subplots(figsize=(8, 4.8))
for k, g in dl.groupby("material"):
    ax.semilogy(g.TIT - 273.15, g.life_h, "-o", ms=3, color=MAT_COLORS[k], lw=2, label=MATERIALS[k].name)
ax.axhline(50, color="r", ls=":")
ax.text(730, 60, "50 h: a realistic hobby-engine overhaul interval", color="r", fontsize=8)
ax.axvline(base.TIT - 273.15, color="k", ls=":")
ax.set_xlabel("Turbine inlet temperature (°C)")
ax.set_ylabel("Blade-root stress-rupture life (h)")
ax.set_ylim(1, 1e8)
ax.set_title("E4  Turbine blade creep life vs TIT (steady running, no safety factor)")
ax.legend()
save(fig, "E4_turbine_creep_life", "sim",
     "Larson-Miller with approximate curves. Real life is set more by hot starts, overtemperature and bearing wear than by steady creep.")

# ---------------- E5: compressor wheel material vs tip speed
rows = []
U = np.linspace(300, 560, 40)
fig, ax = plt.subplots(figsize=(8, 4.8))
for k in ("Al2618", "Al7075", "Ti64", "SS174"):
    m = MATERIALS[k]
    sf = [cm.impeller_stress(u, m, bd.mech["T_impeller"])[1] for u in U]
    ax.plot(U, sf, color=MAT_COLORS[k], lw=2, label=f"{m.name} ({m.density:.0f} kg/m³)")
    for u, s in zip(U, sf):
        rows.append(dict(material=k, U2=u, sf=s))
save_csv(pd.DataFrame(rows), "phase_e_impeller_materials")
ax.axhline(1.2, color="r", ls=":")
ax.axvline(bd.comp["U2"], color="k", ls=":")
ax.text(bd.comp["U2"] + 3, 2.6, f"TJ-110\nU2 = {bd.comp['U2']:.0f} m/s", fontsize=8)
ax.set_xlabel("Impeller tip speed (m/s)")
ax.set_ylabel("Yield safety factor")
ax.set_ylim(0.5, 3)
ax.set_title(f"E5  Compressor wheel: specific strength decides (metal at {bd.mech['T_impeller']:.0f} °C)")
ax.legend(fontsize=8)
save(fig, "E5_impeller_materials", "sim", "σ = 0.6 ρ U². Steel is strong but heavy, so it is no better than aluminum on a spinning wheel.")

# ---------------- E6: liner / hot-sheet materials: temperature capability vs cost
fig, ax = plt.subplots(figsize=(8, 4.8))
for k in ("SS304", "SS321", "SS310", "IN625", "HX", "H230", "IN718"):
    m = MATERIALS[k]
    ax.scatter(m.cost_cad_kg, m.t_max, s=180, color=MAT_COLORS[k], edgecolor="k", zorder=3)
    ax.annotate(m.name, (m.cost_cad_kg, m.t_max), xytext=(8, -3), textcoords="offset points", fontsize=8)
ax.axhspan(850, 950, color=COLORS["egt"], alpha=0.15)
ax.text(5, 905, "expected liner wall 850-950 °C (vaporizer engines)", fontsize=8, color=COLORS["egt"])
ax.set_xscale("log")
ax.set_xlabel("Indicative cost (CAD/kg, small quantities, log scale)")
ax.set_ylabel("Practical oxidation / service limit (°C)")
ax.set_title("E6  Combustor liner sheet: 310 stainless is the value pick, Hastelloy X the premium")
save(fig, "E6_liner_materials", "qual", "Prices vary widely by supplier and form; use as a ranking only.")

# ---------------- E7: thermal growth and running clearance
r_case = bd.turb["rt"] + base.clear_t
dT_wheel = bd.mech["T_disc"] - 15
rows = []
fig, ax = plt.subplots(figsize=(8, 4.6))
for k_case in ("SS304", "SS310", "IN625", "IN718"):
    gaps = []
    Tcase = np.linspace(300, 800, 40)
    for Tc in Tcase:
        grow_wheel = bd.turb["rt"] * MATERIALS[base.mat_turb].alpha * 1e-6 * (bd.mech["T_blade"] - 15)
        stretch = bd.turb["rt"] * bd.mech["stress_blade_root"] / (MATERIALS[base.mat_turb].E * 1e3) * 0.5
        grow_case = r_case * MATERIALS[k_case].alpha * 1e-6 * (Tc - 15)
        gaps.append((base.clear_t + grow_case - grow_wheel - stretch) * 1e3)
        rows.append(dict(shroud=k_case, T_shroud=Tc, hot_clearance_mm=gaps[-1]))
    ax.plot(Tcase, gaps, lw=2, color=MAT_COLORS[k_case], label=f"shroud: {MATERIALS[k_case].name}")
save_csv(pd.DataFrame(rows), "phase_e_clearance")
ax.axhline(0, color="r", lw=1.5)
ax.text(305, 0.02, "rub", color="r")
ax.axhline(base.clear_t * 1e3, color="k", ls=":")
ax.text(305, base.clear_t * 1e3 + 0.02, "cold clearance 0.30 mm", fontsize=8)
ax.set_xlabel("Turbine shroud (NGV ring) temperature (°C)")
ax.set_ylabel("Hot running tip clearance (mm)")
ax.set_title("E7  Thermal expansion changes the turbine tip clearance")
ax.legend(fontsize=8)
save(fig, "E7_thermal_clearance", "analytic",
     "Wheel at blade-root temperature, IN713C; includes elastic stretch. A cool, high-expansion shroud closes the gap at start-up.")

# ---------------- E8: scorecard heatmap
crit = ["Strength at temp.", "Low density", "Creep / oxidation", "Machinability", "Cost", "Availability (Canada)"]
score = {
    "Al2618": [3, 5, 2, 4, 3, 3], "Al7075": [2, 5, 1, 4, 4, 5], "Ti64": [4, 4, 3, 2, 2, 3],
    "SS174": [4, 2, 3, 3, 4, 4], "IN718": [5, 2, 4, 1, 2, 3], "IN713C": [5, 2, 5, 1, 2, 1],
    "MARM247": [5, 1, 5, 1, 1, 1], "SS310": [2, 2, 4, 3, 5, 4], "HX": [3, 2, 5, 2, 2, 2], "IN625": [3, 2, 4, 2, 2, 3],
}
S = np.array(list(score.values()))
fig, ax = plt.subplots(figsize=(9, 5.2))
im = ax.imshow(S, cmap="RdYlGn", vmin=1, vmax=5, aspect="auto")
ax.set_xticks(range(len(crit)), crit, rotation=25, ha="right", fontsize=8)
ax.set_yticks(range(len(score)), [MATERIALS[k].name for k in score], fontsize=8)
for i in range(S.shape[0]):
    for j in range(S.shape[1]):
        ax.text(j, i, S[i, j], ha="center", va="center", fontsize=9)
ax.grid(False)
fig.colorbar(im, ax=ax, label="1 = poor, 5 = excellent")
ax.set_title("E8  Materials scorecard (qualitative)")
save(fig, "E8_material_scorecard", "qual", "Scores are engineering judgement for a university/hobby workshop, not measured data.")
pd.DataFrame(S, index=list(score), columns=crit).to_csv(Path(__file__).resolve().parents[1] / "data" / "phase_e_scorecard_QUALITATIVE.csv")

# ---------------- selection table
sel = [
    ("Compressor wheel", "Al2618", "Ti64", f"{bd.mech['T_impeller']:.0f}", f"{bd.mech['stress_impeller']:.0f}",
     f"SF {bd.mech['sf_impeller']:.2f} on yield; Ti-6Al-4V gives SF {cm.impeller_stress(bd.comp['U2'], MATERIALS['Ti64'], bd.mech['T_impeller'])[1]:.2f} at 1.6× the mass"),
    ("Diffuser", "Al6061", "Al2618", "≈150", "low", "Machined vanes; anodize"),
    ("Shaft", "SS174", "S4140", "≈250-350", "torque + bending", "Ground at bearing seats; hardened 4140 is cheaper"),
    ("Bearings", "Hybrid Si3N4 balls", "-", "≤150 (oil-mist cooled)", f"DN {bd.mech['DN'] / 1e6:.2f}×10⁶",
     "Steel 608 bearings exceed their DN limit (0.9×10⁶)"),
    ("Combustor liner", "SS310", "HX", "850-950", "low", "0.5 mm sheet, rolled and spot/TIG welded"),
    ("Vaporizer tubes", "SS310", "IN625", "900-1000", "low", "Ø5 × 0.3 mm tube; inspect for burn-through"),
    ("NGV ring", "IN625", "IN718", f"≈{base.TIT - 273.15:.0f} (gas)", "low", "Sheet vanes brazed/welded into rings, or cast"),
    ("Turbine wheel", "IN713C", "MARM247", f"{bd.mech['T_blade']:.0f} (blade root)", f"{bd.mech['stress_blade_root']:.0f}",
     "Buy a cast blank; machining from bar is very hard"),
    ("Nozzle and tail cone", "SS321", "SS310", f"≈{bd.cyc['EGT'] - 273.15:.0f}", "low", "0.5 mm sheet"),
    ("Outer casing", "SS304", "Al6061 (cold front only)", "150-400", "pressure 1.8 bar(g)", "1 mm tube or rolled sheet"),
    ("Front cover / inlet", "Al6061", "-", "≈20-60", "low", "Machined"),
]
ds = pd.DataFrame(sel, columns=["part", "chosen", "alternative", "metal_T_C", "stress_MPa", "notes"])
ds["chosen"] = ds["chosen"].map(lambda k: MATERIALS[k].name if k in MATERIALS else k)
ds["alternative"] = ds["alternative"].map(lambda k: MATERIALS[k].name if k in MATERIALS else k)
save_csv(ds, "phase_e_material_selection")
print(ds.to_string(index=False))
print(dl[dl.material == "IN713C"][["TIT", "T_blade", "stress", "life_h"]].round(0).to_string(index=False))
