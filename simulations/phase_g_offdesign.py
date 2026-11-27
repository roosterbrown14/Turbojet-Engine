"""Phase G: off-design. Throttle curve (idle to full), ambient temperature (Canadian winter to summer),
altitude, nozzle exit area.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tj.engine import EngineSpec, build  # noqa: E402
from tj.offdesign import OffDesign  # noqa: E402
from tj.plotting import COLORS, plt, save, save_csv  # noqa: E402

base = EngineSpec()
bd = build(base)
od = OffDesign(bd)


def isa(alt):
    T = 288.15 - 0.0065 * alt
    return T, 101325 * (T / 288.15) ** 5.2559


# ---------------- G1: throttle curve
rl = od.running_line(np.linspace(0.42, 1.05, 43))
df = pd.DataFrame([{k: v for k, v in p.items() if k != "x"} for p in rl])
save_csv(df, "phase_g_throttle")
ok = df[df.converged]
idle = ok.rpm.min()
fig, axs = plt.subplots(2, 2, figsize=(12, 8))
axs[0, 0].plot(ok.rpm / 1e3, ok.thrust, color=COLORS["thrust"], lw=2)
axs[0, 0].set_ylabel("Thrust (N)")
axs[0, 1].plot(ok.rpm / 1e3, ok.fuel_l_min, color=COLORS["tsfc"], lw=2)
axs[0, 1].set_ylabel("Fuel flow (L/min)")
axs[1, 0].plot(ok.rpm / 1e3, ok.EGT_C, color=COLORS["egt"], lw=2, label="EGT (what you measure)")
axs[1, 0].plot(ok.rpm / 1e3, ok.TIT_C, color=COLORS["tit"], lw=2, ls="--", label="turbine inlet")
axs[1, 0].set_ylabel("Temperature (°C)")
axs[1, 0].legend(fontsize=8)
axs[1, 1].plot(ok.rpm / 1e3, ok.prc, color=COLORS["pr"], lw=2, label="pressure ratio")
axs[1, 1].plot(ok.rpm / 1e3, ok.mdot * 10, color=COLORS["flow"], lw=2, label="air flow ×10 (kg/s)")
axs[1, 1].set_ylabel("Pressure ratio / air flow")
axs[1, 1].legend(fontsize=8)
for ax in axs.flat:
    ax.set_xlabel("Shaft speed (krpm)")
    ax.axvline(base.rpm / 1e3, color="k", ls=":", lw=0.8)
    ax.axvspan(0, idle / 1e3, color="#e5e7eb")
    ax.set_xlim(40, 118)
axs[0, 0].text(41, ok.thrust.max() * 0.85, "model cannot\nrun itself here", fontsize=8, color="#6b7280")
fig.suptitle(f"G1  Throttle curve, sea level 15 °C. Lowest self-sustaining speed in the model ≈ {idle / 1e3:.0f} krpm",
             fontweight="bold")
save(fig, "G1_throttle_curve", "od",
     "Below design speed the TIT first falls, then rises again towards idle. Engines of this class idle at 30-40 % speed; the model's low-speed map is its weakest part.")

# ---------------- G2: ambient temperature and altitude at full speed
rows = []
for Tc in np.arange(-30, 41, 5):
    p = od.point(1.0, T0=Tc + 273.15)
    rows.append(dict(case="temperature", T_amb_C=Tc, alt_m=0, thrust=p["thrust"], EGT_C=p["EGT_C"], TIT_C=p["TIT_C"],
                     conv=p["converged"], fuel=p["fuel_l_min"]))
for alt in np.arange(0, 3001, 250):
    T, pa = isa(alt)
    p = od.point(1.0, T0=T, p0=pa)
    rows.append(dict(case="altitude", T_amb_C=T - 273.15, alt_m=alt, thrust=p["thrust"], EGT_C=p["EGT_C"],
                     TIT_C=p["TIT_C"], conv=p["converged"], fuel=p["fuel_l_min"]))
da = pd.DataFrame(rows)
save_csv(da, "phase_g_ambient")
fig, axs = plt.subplots(1, 2, figsize=(12, 4.3))
t = da[da.case == "temperature"]
axs[0].plot(t.T_amb_C, t.thrust, "-o", ms=3, color=COLORS["thrust"], lw=2)
a2 = axs[0].twinx()
a2.plot(t.T_amb_C, t.EGT_C, "--", color=COLORS["egt"])
a2.set_ylabel("EGT (°C, dashed)", color=COLORS["egt"])
a2.grid(False)
axs[0].set_xlabel("Outside air temperature (°C)")
axs[0].set_ylabel("Thrust at 110 krpm (N)")
axs[0].set_title("Winter to summer (sea level)", fontsize=10)
a = da[da.case == "altitude"]
axs[1].plot(a.alt_m, a.thrust, "-o", ms=3, color=COLORS["thrust"], lw=2)
axs[1].set_xlabel("Field elevation (m, ISA)")
axs[1].set_ylabel("Thrust at 110 krpm (N)")
axs[1].set_title("Altitude (Calgary ≈ 1050 m, Banff ≈ 1400 m)", fontsize=10)
fig.suptitle("G2  Cold, dense air gives more thrust; hot days and high fields give less", fontweight="bold")
save(fig, "G2_ambient_effects", "od",
     "Fixed mechanical speed 110 krpm. On hot days the EGT rises: a real ECU would cap EGT and lose more thrust.")

# ---------------- G3: nozzle exit area
rows = []
for s in np.linspace(0.85, 1.20, 15):
    o = OffDesign(bd, A9_scale=s)
    p = o.point(1.0)
    rows.append(dict(A9_scale=s, D9_mm=bd.cyc["D9"] * np.sqrt(s) * 1e3, thrust=p["thrust"], EGT_C=p["EGT_C"],
                     TIT_C=p["TIT_C"], surge_margin=p["surge_margin"], prc=p["prc"], conv=p["converged"]))
dn = pd.DataFrame(rows)
save_csv(dn, "phase_g_nozzle")
fig, axs = plt.subplots(1, 3, figsize=(14, 4))
axs[0].plot(dn.D9_mm, dn.thrust, "-o", ms=3, color=COLORS["thrust"])
axs[0].set_ylabel("Thrust (N)")
axs[1].plot(dn.D9_mm, dn.TIT_C, "-o", ms=3, color=COLORS["tit"], label="turbine inlet")
axs[1].plot(dn.D9_mm, dn.EGT_C, "-o", ms=3, color=COLORS["egt"], label="EGT")
axs[1].set_ylabel("Temperature (°C)")
axs[1].legend(fontsize=8)
axs[2].plot(dn.D9_mm, dn.surge_margin * 100, "-o", ms=3, color=COLORS["margin"])
axs[2].set_ylabel("Surge margin (%)")
for ax in axs:
    ax.set_xlabel("Nozzle exit diameter (mm)")
    ax.axvline(bd.cyc["D9"] * 1e3, color="k", ls=":")
fig.suptitle("G3  Nozzle size is the tuning knob: smaller = hotter, more thrust, closer to surge", fontweight="bold")
save(fig, "G3_nozzle_area", "od", "Fixed 110 krpm. This is how builders tune EGT on the test stand: trim or extend the nozzle.")
print(ok[["rpm", "thrust", "prc", "TIT_C", "EGT_C", "fuel_l_min", "surge_margin"]].round(2).to_string(index=False))
print(da.round(1).to_string(index=False))
print(dn.round(2).to_string(index=False))
