"""Shared chart style: consistent colours, provenance footer, PNG + SVG export."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CHARTS = ROOT / "charts"
DATA = ROOT / "data"

COLORS = {
    "thrust": "#2563eb", "tsfc": "#dc2626", "egt": "#d97706", "tit": "#b91c1c", "flow": "#059669",
    "pr": "#7c3aed", "eta": "#0891b2", "stress": "#be185d", "margin": "#4b5563", "design": "#111827",
}
# One colour per material family, used in every materials chart
MAT_COLORS = {
    "Al2618": "#60a5fa", "Al7075": "#93c5fd", "Al6061": "#bfdbfe", "Ti64": "#a78bfa", "SS174": "#9ca3af",
    "S4140": "#6b7280", "IN718": "#f59e0b", "IN713C": "#dc2626", "MARM247": "#7f1d1d", "IN625": "#fb923c",
    "HX": "#16a34a", "H230": "#15803d", "SS310": "#0d9488", "SS321": "#14b8a6", "SS304": "#5eead4",
}

SOURCE_TAGS = {
    "sim": "Source: numerical simulation, meanline + cycle model in src/tj (unvalidated)",
    "od": "Source: numerical simulation, off-design matching with a semi-empirical compressor map (unvalidated)",
    "fe": "Source: numerical simulation, finite-element rotordynamics model (unvalidated)",
    "analytic": "Source: analytical calculation",
    "data": "Source: approximate handbook data compiled in src/tj/materials.py (not design allowables)",
    "qual": "Source: qualitative engineering assessment (not measured data)",
}

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 160, "font.size": 10, "axes.titlesize": 12,
    "axes.titleweight": "bold", "axes.grid": True, "grid.alpha": 0.3,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
})


def footer(fig, source="sim", assumptions=""):
    text = SOURCE_TAGS[source]
    if assumptions:
        text += "\n" + assumptions
    fig.text(0.01, -0.01, text, fontsize=7, color="#555", va="top", ha="left", wrap=True)


def save(fig, name, source="sim", assumptions=""):
    footer(fig, source, assumptions)
    CHARTS.mkdir(exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(CHARTS / f"{name}.{ext}", bbox_inches="tight")
    plt.close(fig)
    return CHARTS / f"{name}.png"


def save_csv(df, name):
    DATA.mkdir(exist_ok=True)
    df.to_csv(DATA / f"{name}.csv", index=False)
