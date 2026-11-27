"""Explanatory diagrams: engine schematic with stations and the gas path, and a 'how it works' strip.

Writes diagrams/engine_stations.png|svg and diagrams/how_it_works.png|svg.
"""
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, Polygon, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "diagrams"
OUT.mkdir(exist_ok=True)
dp = json.loads((ROOT / "data" / "design_point.json").read_text())
c, t, g = dp["compressor"], dp["turbine"], dp["geometry"]
mm = 1e3

fig, ax = plt.subplots(figsize=(12, 5.2))
R = g["r_case_in"] * mm
x_imp0, x_imp1 = 20, 42
x_cb0, x_cb1 = 70, 70 + g["liner_len"] * mm
x_ngv, x_tur = x_cb1 + 4, x_cb1 + 22
x_noz = x_tur + 70
for sgn in (1, -1):
    # casing
    ax.plot([x_imp0 - 5, x_noz - 40], [sgn * (R + 1)] * 2, color="#6b7280", lw=3)
    ax.plot([x_noz - 40, x_noz], [sgn * (R + 1), sgn * dp["performance"]["D9"] * mm / 2], color="#6b7280", lw=3)
    # bellmouth
    th = np.linspace(0, np.pi / 2, 20)
    ax.plot(x_imp0 - 5 - 15 * np.sin(th), sgn * (c["r1t"] * mm + 15 * (1 - np.cos(th))), color="#6b7280", lw=3)
    # impeller
    ax.add_patch(Polygon([[x_imp0, sgn * c["r1h"] * mm], [x_imp0, sgn * c["r1t"] * mm],
                          [x_imp1, sgn * c["r2"] * mm], [x_imp1, sgn * 6]], color="#60a5fa", alpha=0.9))
    # diffuser
    ax.add_patch(Rectangle((x_imp1 + 1, sgn * c["r2"] * mm if sgn > 0 else -c["r3"] * mm), 6,
                           (c["r3"] - c["r2"]) * mm, color="#93c5fd"))
    ax.add_patch(Rectangle((x_imp1 + 8, sgn * (R - 4) if sgn > 0 else -R), 14, 4, color="#93c5fd"))
    # combustor liner
    ax.add_patch(Rectangle((x_cb0, sgn * g["liner_in"] * mm if sgn > 0 else -g["liner_out"] * mm), x_cb1 - x_cb0,
                           (g["liner_out"] - g["liner_in"]) * mm, fill=False, ec="#0d9488", lw=2, ls="--"))
    ax.add_patch(Rectangle((x_cb0 + 5, sgn * g["liner_in"] * mm + (8 if sgn > 0 else -30)), x_cb1 - x_cb0 - 10, 22,
                           color="#fca5a5", alpha=0.5))
    # NGV and turbine
    ax.add_patch(Rectangle((x_ngv, sgn * t["rh"] * mm if sgn > 0 else -t["rt"] * mm), 10, t["h"] * mm, color="#fb923c"))
    ax.add_patch(Rectangle((x_tur - 6, sgn * t["rh"] * mm if sgn > 0 else -t["rt"] * mm), 10, t["h"] * mm, color="#dc2626"))
    ax.add_patch(Rectangle((x_tur - 6, 0 if sgn > 0 else -t["rh"] * mm), 10, t["rh"] * mm, color="#dc2626", alpha=0.7))
    # tail cone
    ax.add_patch(Polygon([[x_tur + 5, 0], [x_tur + 5, sgn * t["rh"] * mm], [x_tur + 45, 0]], color="#9ca3af", alpha=0.6))
# shaft + tunnel
ax.add_patch(Rectangle((x_imp0 - 4, -4), x_tur - x_imp0 + 8, 8, color="#374151"))
ax.add_patch(Rectangle((x_imp1 + 3, -11), x_ngv - x_imp1 - 3, 22, fill=False, ec="#374151", lw=1.2))
for xb in (x_imp1 + 8, x_ngv - 6):
    ax.add_patch(Rectangle((xb - 3.5, -11), 7, 22, color="#111827"))
# flow arrows
for y in (30, -30):
    ax.add_patch(FancyArrowPatch((x_imp0 - 30, y * 0.6), (x_imp0 - 2, y * 0.5), arrowstyle="-|>", mutation_scale=14, color="#2563eb"))
ax.add_patch(FancyArrowPatch((x_noz - 10, 0), (x_noz + 30, 0), arrowstyle="-|>", mutation_scale=22, color="#d97706", lw=3))
# stations
st = {"1": x_imp0 - 2, "2": x_imp1, "3": x_cb0 - 2, "4": x_ngv, "5": x_tur + 6, "9": x_noz}
for k, x in st.items():
    ax.axvline(x, color="#9ca3af", lw=0.8, ls=":")
    ax.text(x, R + 12, k, ha="center", fontweight="bold", bbox=dict(boxstyle="circle", fc="white", ec="k"))
labels = [(x_imp0 + 5, -R - 16, "compressor\n(Al 2618)"), (x_imp1 + 10, R + 24, "diffuser"),
          ((x_cb0 + x_cb1) / 2, -R - 16, "annular combustor\n(vaporizer tubes)"), (x_ngv + 2, R + 24, "NGV"),
          (x_tur, -R - 16, "turbine\n(IN713C)"), (x_noz - 15, -R - 10, "nozzle"), ((x_imp1 + x_ngv) / 2, 0, "shaft + bearings")]
for x, y, s in labels:
    ax.text(x, y, s, ha="center", va="center", fontsize=8.5, color="white" if s.startswith("shaft") else "k")
st_data = dp["performance"]
ax.text(x_imp0 - 40, -R - 5, f"{dp['spec']['mdot']} kg/s air", color="#2563eb", fontsize=9)
ax.text(x_noz + 2, 12, f"{st_data['V9']:.0f} m/s jet\n{st_data['thrust']:.0f} N", color="#d97706", fontsize=9)
ax.set_aspect("equal")
ax.set_xlim(x_imp0 - 50, x_noz + 40)
ax.set_ylim(-R - 30, R + 32)
ax.axis("off")
ax.set_title("TJ-110 schematic half-sections and SAE station numbers (not to exact scale)", fontweight="bold")
fig.savefig(OUT / "engine_stations.png", dpi=160, bbox_inches="tight")
fig.savefig(OUT / "engine_stations.svg", bbox_inches="tight")
plt.close(fig)

# how it works strip
steps = [("1  Suck", "The bellmouth\nfeeds air smoothly\nto the compressor", "#2563eb"),
         ("2  Squeeze", f"Impeller at {dp['spec']['rpm'] / 1e3:.0f} krpm\nraises pressure\n{dp['spec']['pr']}×", "#7c3aed"),
         ("3  Bang", f"Kerosene burns,\nheating the gas to\n{dp['spec']['TIT'] - 273.15:.0f} °C", "#dc2626"),
         ("4  Spin", "The turbine takes\njust enough energy\nto drive the compressor", "#d97706"),
         ("5  Blow", f"The rest leaves as a\n{st_data['V9']:.0f} m/s jet:\n{st_data['thrust']:.0f} N of thrust", "#059669")]
fig, ax = plt.subplots(figsize=(12, 2.6))
for i, (h, b, col) in enumerate(steps):
    ax.add_patch(Rectangle((i * 2.4, 0), 2.1, 1.6, color=col, alpha=0.12, ec=col))
    ax.text(i * 2.4 + 1.05, 1.32, h, ha="center", fontweight="bold", color=col, fontsize=12)
    ax.text(i * 2.4 + 1.05, 0.6, b, ha="center", va="center", fontsize=9)
    if i < 4:
        ax.annotate("", (i * 2.4 + 2.38, 0.8), (i * 2.4 + 2.12, 0.8), arrowprops=dict(arrowstyle="-|>", color="k"))
ax.set_xlim(-0.1, 12)
ax.set_ylim(-0.1, 1.7)
ax.axis("off")
fig.savefig(OUT / "how_it_works.png", dpi=160, bbox_inches="tight")
fig.savefig(OUT / "how_it_works.svg", bbox_inches="tight")
plt.close(fig)
print("diagrams written")
