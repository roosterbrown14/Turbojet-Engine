"""Correct test-stand logs to ISA and compare with the model's throttle curve.

Usage: .venv/bin/python experiments/analyze.py experiments/runs/*.csv
Each CSV follows experiments/run_log_template.csv. With no files, writes the model-only reference chart.
Writes charts/X1_measured_vs_model.png.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tj.plotting import COLORS, plt, save  # noqa: E402

model = pd.read_csv(ROOT / "data" / "phase_g_throttle.csv")
model = model[model.converged]

runs = []
for f in sys.argv[1:]:
    d = pd.read_csv(f)
    theta = (d.T_amb_C + 273.15) / 288.15
    delta = d.p_amb_kPa / 101.325
    d["N_corr"] = d.rpm / np.sqrt(theta)
    d["F_corr"] = d.thrust_N / delta
    d["fuel_corr"] = d.fuel_g_s / (delta * np.sqrt(theta))
    d["EGT_corr"] = (d.EGT_C + 273.15) / theta - 273.15
    d["run"] = Path(f).stem
    runs.append(d)

fig, axs = plt.subplots(1, 3, figsize=(15, 4.3))
axs[0].plot(model.rpm / 1e3, model.thrust, color=COLORS["thrust"], lw=2, label="model")
axs[0].fill_between(model.rpm / 1e3, model.thrust * 0.9, model.thrust * 1.1, color=COLORS["thrust"], alpha=0.15,
                    label="model ±10 %")
axs[1].plot(model.rpm / 1e3, model.mdot_fuel * 1e3, color=COLORS["tsfc"], lw=2)
axs[2].plot(model.rpm / 1e3, model.EGT_C, color=COLORS["egt"], lw=2)
for d in runs:
    axs[0].plot(d.N_corr / 1e3, d.F_corr, "o", ms=3, label=d.run.iloc[0])
    axs[1].plot(d.N_corr / 1e3, d.fuel_corr, "o", ms=3)
    axs[2].plot(d.N_corr / 1e3, d.EGT_corr, "o", ms=3)
axs[0].set_ylabel("Thrust (N, ISA-corrected)")
axs[1].set_ylabel("Fuel flow (g/s, ISA-corrected)")
axs[2].set_ylabel("EGT (°C, ISA-corrected)")
for ax in axs:
    ax.set_xlabel("Corrected speed (krpm)")
axs[0].legend(fontsize=8)
fig.suptitle("X1  Measured vs model" + ("" if runs else " (no measurements yet)"), fontweight="bold")
save(fig, "X1_measured_vs_model", "od", "Measured points corrected with θ = T0/288.15 K, δ = p0/101.325 kPa.")
print(f"{len(runs)} run(s) compared")
