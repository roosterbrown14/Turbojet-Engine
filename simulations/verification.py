"""Verification: check each model against exact solutions, tabulated data and one published engine.

V1 gas properties vs JANAF air cp; V2 cycle vs closed-form ideal Brayton (constant cp, ideal parts);
V3 rotor FE vs exact Euler-Bernoulli beam frequencies; V4 disc solver vs closed-form solid disc;
V5 off-design solver reproduces the design point at 100 % speed;
V6 benchmark against van den Hout & Koullen (1996) published micro-turbojet (abstract values).
"""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tj import cycle as cy  # noqa: E402
from tj import rotor as rt  # noqa: E402
from tj import turbine as tb  # noqa: E402
from tj.engine import EngineSpec, build  # noqa: E402
from tj.gas import air  # noqa: E402
from tj.offdesign import OffDesign  # noqa: E402
from tj.plotting import COLORS, plt, save, save_csv  # noqa: E402

rows = []

# V1
janaf = {300: 1005, 400: 1013, 500: 1029, 600: 1051, 800: 1099, 1000: 1142, 1200: 1173, 1500: 1216}
for T, ref in janaf.items():
    rows.append(dict(check="V1 air cp", case=f"{T} K", model=air.cp(T), reference=ref, error_pct=100 * (air.cp(T) / ref - 1)))

# V2: first law. With perfect components and the nozzle unchoked, the whole engine is one open
# system: jet kinetic energy = fuel heat - heat rejected in the exhaust. This must close exactly.
# (The constant-cp textbook efficiency 1 - T1/T3s is ~8 % higher than the real-gas value because hot
# combustion gas has a lower gamma; that difference is physics, not error, so it is not a pass/fail check.)
from tj.fuels import FUELS  # noqa: E402
for pr in (1.5, 2.0, 2.5):
    ci = cy.CycleInputs(pr_c=pr, eta_c=1.0, eta_t=1.0, eta_b=1.0, eta_m=1.0, dp_comb=0.0, pi_inlet=1.0, pi_jetpipe=1.0,
                        leak=0.0, cv_nozzle=1.0, TIT=1200.0)
    r = cy.run(ci)
    f, g = r["far"], r["gas"]
    T9 = r["stations"][9]["T"]
    ke_first_law = (air.h(ci.T0) + f * FUELS[ci.fuel].LHV - (1 + f) * g.h(T9)) / (1 + f)
    ke_model = r["V9"] ** 2 / 2
    rows.append(dict(check="V2 first-law closure, ideal engine", case=f"PR {pr}{' (choked)' if r['choked'] else ''}",
                     model=ke_model, reference=ke_first_law, error_pct=100 * (ke_model / ke_first_law - 1)))

# V3: free-free & pinned-pinned uniform beam (no bearings -> pinned via stiff springs)
L, d, E, rho = 0.2, 0.01, 200e9, 7800
x = np.linspace(0, L, 61)
R = rt.Rotor(x, np.full(60, d), E=E, rho=rho, bearings=[(0.0, 1e13), (L, 1e13)])
w, _ = R.modes(0.0, 3)
A, I = np.pi * d**2 / 4, np.pi * d**4 / 64
for k in (1, 2, 3):
    exact = (k * np.pi / L) ** 2 * np.sqrt(E * I / (rho * A))
    rows.append(dict(check="V3 beam natural frequency (pinned-pinned)", case=f"mode {k}", model=w[k - 1] / (2 * np.pi),
                     reference=exact / (2 * np.pi), error_pct=100 * (w[k - 1] / exact - 1)))
# convergence
conv = []
for ne in (4, 8, 16, 32, 64):
    Rn = rt.Rotor(np.linspace(0, L, ne + 1), np.full(ne, d), E=E, rho=rho, bearings=[(0.0, 1e13), (L, 1e13)])
    wn, _ = Rn.modes(0.0, 3)
    conv.append(dict(elements=ne, **{f"err_mode{k}": abs(wn[k - 1] / ((k * np.pi / L) ** 2 * np.sqrt(E * I / (rho * A))) - 1)
                                     for k in (1, 2, 3)}))
dconv = pd.DataFrame(conv)
save_csv(dconv, "verification_rotor_convergence")

# V4: disc with tiny bore vs solid-disc centre stress (3+nu)/8 rho w^2 b^2 (bore doubles it: check the bore formula)
rpm, b, rho_d, nu = 100_000, 0.03, 8000, 0.3
w_ = rpm * 2 * np.pi / 60
r_, sr, st, avg = tb.disc_stress(rpm, 1e-4, b, rho_d, nu, 0.0)
exact_bore = (3 + nu) / 4 * rho_d * w_**2 * b**2 * (1 + (1 - nu) / (3 + nu) * 1e-8 / b**2) / 1e6
rows.append(dict(check="V4 disc hoop stress at a pin-hole bore", case="b = 30 mm, 100 krpm", model=st[0], reference=exact_bore,
                 error_pct=100 * (st[0] / exact_bore - 1)))
avg_exact = rho_d * w_**2 * b**2 / 3 / 1e6     # average hoop stress of a solid disc = rho w^2 b^2 / 3
rows.append(dict(check="V4 disc average hoop stress", case="solid disc", model=avg, reference=avg_exact,
                 error_pct=100 * (avg / avg_exact - 1)))

# V5: off-design returns the design point
bd = build(EngineSpec())
p = OffDesign(bd).point(1.0)
for k, ref, mod in (("thrust", bd.thrust, p["thrust"]), ("TIT", EngineSpec().TIT, p["T4"]), ("air flow", 0.25, p["mdot"])):
    rows.append(dict(check="V5 off-design at 100 % speed", case=k, model=mod, reference=ref, error_pct=100 * (mod / ref - 1)))

# V6: published engine (van den Hout & Koullen 1996, abstract): 110 mm, 40 N, 0.150 kg/s, PR 1.90,
# TIT 953 K, 100 krpm, 62.5 mg/(N s)
spec = replace(EngineSpec(), mdot=0.150, pr=1.90, TIT=953.0, rpm=100_000)
r6 = build(spec)
for k, ref, mod in (("thrust (N)", 40.0, r6.thrust), ("TSFC (g/kN·s)", 62.5, r6.cyc["tsfc_g_per_kNs"]),
                    ("outer diameter (mm)", 110.0, r6.geom["D_case"] * 1e3)):
    rows.append(dict(check="V6 published micro-turbojet (vandenhout1996)", case=k, model=mod, reference=ref,
                     error_pct=100 * (mod / ref - 1)))

df = pd.DataFrame(rows)
save_csv(df, "verification_summary")
print(df.round(3).to_string(index=False))
print(dconv)

fig, axs = plt.subplots(1, 2, figsize=(13, 4.5))
for k in (1, 2, 3):
    axs[0].loglog(dconv.elements, dconv[f"err_mode{k}"], "-o", label=f"mode {k}")
axs[0].set_xlabel("Number of beam elements")
axs[0].set_ylabel("Relative frequency error")
axs[0].set_title("Rotor FE convergence (pinned beam)", fontsize=10)
axs[0].legend()
v6 = df[df.check.str.startswith("V6")]
xx = np.arange(len(v6))
axs[1].bar(xx - 0.2, v6.reference, 0.4, color=COLORS["margin"], label="published")
axs[1].bar(xx + 0.2, v6.model, 0.4, color=COLORS["thrust"], label="this model")
for i, (rf, md) in enumerate(zip(v6.reference, v6.model)):
    axs[1].text(i + 0.2, md + 1, f"{100 * (md / rf - 1):+.0f} %", ha="center", fontsize=9)
axs[1].set_xticks(xx, v6.case)
axs[1].set_title("Benchmark: published 110 mm micro-turbojet (van den Hout & Koullen 1996)", fontsize=10)
axs[1].legend()
fig.suptitle("V1  Verification", fontweight="bold")
save(fig, "V1_verification", "sim", "Benchmark inputs from the paper's abstract (PR 1.90, TIT 953 K, 0.150 kg/s, 100 krpm); our component models fill the rest.")
