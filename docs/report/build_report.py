"""Build the project report PDF (docs/report/Turbojet_Engine_Type_TJ110_report.pdf) from the repository's results.

Run: .venv/bin/python docs/report/build_report.py
"""
import json
from pathlib import Path

import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "report" / "Turbojet_Engine_Type_TJ110_report.pdf"
FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
pdfmetrics.registerFont(TTFont("DV", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DVB", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DVI", str(FONT_DIR / "DejaVuSans-Oblique.ttf")))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB", italic="DVI")

ss = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=ss["BodyText"], fontName="DV", fontSize=9.5, leading=13.5, spaceAfter=5)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=7.5, leading=10, textColor=colors.HexColor("#444"))
H1 = ParagraphStyle("h1", parent=ss["Heading1"], fontName="DVB", fontSize=16, spaceBefore=4, spaceAfter=8,
                    textColor=colors.HexColor("#7c2d12"))
H2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName="DVB", fontSize=12, spaceBefore=8, spaceAfter=4)
TITLE = ParagraphStyle("title", parent=H1, fontSize=26, leading=32, alignment=TA_CENTER)
SUB = ParagraphStyle("sub", parent=BODY, fontSize=12, leading=16, alignment=TA_CENTER)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=7.8, leading=10, spaceAfter=0)
CELLB = ParagraphStyle("cellb", parent=CELL, fontName="DVB")
W = A4[0] - 36 * mm
DP = json.loads((ROOT / "data" / "design_point.json").read_text())


def P(t, st=BODY):
    return Paragraph(t, st)


def img(rel, width=W, caption=None, max_h=205 * mm):
    path = ROOT / rel
    if not path.exists():
        return P(f"[missing figure: {rel}]", SMALL)
    im = Image(str(path))
    ratio = im.imageHeight / im.imageWidth
    h = width * ratio
    if h > max_h:
        width, h = max_h / ratio, max_h
    im.drawWidth, im.drawHeight = width, h
    parts = [im]
    if caption:
        parts.append(P(caption, SMALL))
    return KeepTogether(parts + [Spacer(1, 4)])


def table(rows, widths, header=True):
    data = [[P(str(c), CELLB if (header and i == 0) else CELL) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#bbb")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fde8d8")))
    t.setStyle(TableStyle(style))
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("DV", 7.5)
    canvas.setFillColor(colors.HexColor("#666"))
    canvas.drawString(18 * mm, 10 * mm, "Turbojet Engine - Type TJ-110: design study (simulation results, not yet validated by experiment)")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def first(*paths):
    for p in paths:
        if (ROOT / p).exists():
            return p
    return paths[0]


def build():
    pf, c, t, m = DP["performance"], DP["compressor"], DP["turbine"], DP["mechanical"]
    s = []
    s += [Spacer(1, 35 * mm), P("Turbojet Engine - Type TJ-110", TITLE),
          P("Design study of a small single-spool turbojet: centrifugal compressor, annular vaporizer combustor, "
            "axial turbine", SUB), Spacer(1, 6 * mm),
          img(first("prototypes/TJ110_cutaway.png", "diagrams/cad_TJ110_exterior.png", "diagrams/engine_stations.png"),
              width=120 * mm, max_h=95 * mm),
          Spacer(1, 4 * mm), P("Author: roosterbrown14 · November 2026", SUB),
          P("Repository: github.com/roosterbrown14/Turbojet-Engine", SUB), Spacer(1, 8 * mm),
          P("<b>Status.</b> Modelling and design are complete. No engine has been built and nothing has been measured. "
            "All numbers are model estimates; a benchmark against a published micro-turbojet agrees within ±7 %, but "
            "this engine's real performance could differ by ±10–20 %. The modelling code, analysis, CAD and documentation "
            "were developed with the help of Claude (Anthropic), an AI assistant.", SMALL), PageBreak()]

    s += [P("1. Summary", H1),
          P("TJ-110 is a hobby/university-buildable turbojet, 119 mm in diameter. Air enters a bellmouth, is compressed "
            "2.8× by an aluminum centrifugal impeller at 110 000 rpm, burns with kerosene in an annular combustor fed by "
            "vaporizer tubes, drives an Inconel axial turbine, and leaves through a convergent nozzle. Every component was "
            "sized by meanline models from the cycle requirement, and the whole design was checked for wheel stresses, "
            "creep, burst margin, critical speeds and bearing limits."),
          img("diagrams/how_it_works.png", width=W)]
    s.append(table([
        ["Result (sea level, 15 °C, static)", "Value"],
        ["Thrust", f"{pf['thrust']:.0f} N (90 % range for build scatter: 100–121 N)"],
        ["Fuel", f"{pf['fuel_l_per_min']:.2f} L/min Jet A-1 ({pf['mdot_fuel'] * 1e3:.2f} g/s); TSFC {pf['tsfc_g_per_kNs']:.1f} g/(kN·s)"],
        ["Air flow, pressure ratio, speed", f"0.25 kg/s, 2.8, 110 000 rpm"],
        ["Turbine inlet / exhaust gas temperature", f"827 °C / {pf['EGT'] - 273.15:.0f} °C"],
        ["Jet speed", f"{pf['V9']:.0f} m/s through a Ø{pf['D9'] * 1e3:.1f} mm nozzle (unchoked)"],
        ["Compressor", f"Ø{c['D2'] * 1e3:.1f} mm, 7 + 7 blades, 30° backsweep, tip speed {c['U2']:.0f} m/s, η = {c['eta']:.3f}"],
        ["Turbine", f"Ø{t['Dt'] * 1e3:.1f} mm, 27 blades, ψ = 1.3, φ = 0.65, η = {t['eta']:.3f}"],
        ["Weakest part", f"Impeller: safety factor {m['sf_impeller']:.2f} on yield; yields at ≈ +11 % overspeed"],
        ["Critical speeds", "23 and 36 krpm (rigid-body, below idle, needs O-ring bearing mounts); bending 180 krpm"],
    ], [60 * mm, W - 60 * mm]))
    s += [P("Main findings", H2), table([
        ["Finding", "Detail"],
        ["Pressure ratio is limited by the impeller", "PR 2.8 is the highest an Al 2618 wheel can deliver with SF ≥ 1.2. Higher PR needs titanium."],
        ["Shaft speed sets size, not stress", "Tip speed (418 m/s) is fixed by the work. 110 krpm gives a 119 mm engine within hybrid-bearing DN limits."],
        ["Soft-mount the bearings", "Hard-mounted bearings put two critical speeds (53, 92 krpm) inside the operating range. O-ring mounts move them to 23 and 36 krpm."],
        ["Build quality matters", "Compressor quality, combustor pressure loss and turbine tip clearance are the biggest builder-controlled factors (≈ ±5 N each)."],
        ["Creep is not the life limit at design TIT", "IN713C blade life > 10⁶ h at 827 °C, but only ≈ 50 h at 1030 °C TIT. Hot starts set the real life."],
        ["Nozzle area tunes the engine", "−2 mm nozzle diameter ≈ +6 N and +135 °C EGT."],
        ["Design point is near-optimal", "The highest-thrust feasible design in a 660-point search."],
    ], [55 * mm, W - 55 * mm]), PageBreak()]

    s += [P("2. Engine layout", H1),
          img(first("prototypes/TJ110_assembled_section.png", "diagrams/cad_TJ110_section.png", "diagrams/engine_stations.png"),
              caption="Assembled engine, section through the axis, coloured by material."),
          img("diagrams/engine_stations.png", caption="Station numbering used throughout the study."), PageBreak()]

    s += [P("3. Cycle", H1),
          img("charts/A1_ts_diagram.png", width=150 * mm, caption="Design-point cycle on a temperature–entropy diagram."),
          img("charts/A3_energy_flow.png", caption="Only ≈ 11 % of the fuel energy becomes jet power at PR 2.8."),
          img("charts/B2_pr_tit_maps.png", caption="Thrust, EGT and impeller safety factor over pressure ratio and TIT."),
          PageBreak()]

    s += [P("4. Components", H1),
          img("charts/C4_compressor_map.png", width=140 * mm, caption="Compressor map (semi-empirical) with the running line."),
          img("charts/C2_backsweep_blades.png", caption="Backsweep and blade count."),
          img("charts/D1_smith_chart.png", caption="Turbine efficiency chart: small size costs ≈ 9 points."),
          img("charts/D2_turbine_loading.png", width=150 * mm, caption="Turbine loading choice."),
          img("charts/F1_flame_temperature.png", width=130 * mm, caption="Flame temperature vs equivalence ratio for six fuels."),
          img("charts/F2_fuel_comparison.png", caption="Fuel comparison at the design point."), PageBreak()]

    s += [P("5. Materials", H1),
          img("charts/E1_strength_vs_temperature.png", caption="Yield and specific strength vs temperature (approximate handbook data)."),
          img("charts/E3_larson_miller.png", width=140 * mm, caption="Larson–Miller creep curves with TJ-110's parts."),
          img("charts/E4_turbine_creep_life.png", width=130 * mm, caption="Turbine blade creep life vs TIT."),
          img("charts/E5_impeller_materials.png", width=130 * mm, caption="Compressor wheel material vs tip speed.")]
    s.append(table([
        ["Part", "Material", "Why"],
        ["Compressor wheel", "Al 2618-T61", "Specific strength to 200 °C; machinable"],
        ["Shaft", "17-4PH H1025", "Strength, grinds well"],
        ["Bearings", "608 hybrid (Si₃N₄ balls)", "DN 0.88 × 10⁶ is beyond steel-ball limits"],
        ["Combustor liner, vaporizers", "310 stainless (Hastelloy X premium)", "Oxidation to ≈ 1035 °C, cheap"],
        ["NGV ring", "Inconel 625", "Weldable, oxidation resistant"],
        ["Turbine wheel", "Cast IN713C", "Creep strength at 730 °C root temperature"],
        ["Nozzle, casing", "321 / 304 stainless", "Cheap sheet and tube"],
    ], [45 * mm, 55 * mm, W - 100 * mm]))
    s.append(PageBreak())

    s += [P("6. Off-design and rotordynamics", H1),
          img("charts/G1_throttle_curve.png", width=150 * mm, caption="Throttle curve: thrust ∝ speed³, U-shaped EGT."),
          img("charts/G2_ambient_effects.png", caption="Weather and altitude at full speed."),
          img("charts/H1_campbell.png", width=140 * mm, caption="Campbell diagram with O-ring bearing mounts."),
          img("charts/H2_bearing_stiffness.png", width=130 * mm, caption="Critical speeds vs bearing support stiffness."),
          img("charts/I1_tornado.png", caption="What the predictions depend on most."),
          img("charts/V1_verification.png", caption="Verification: FE convergence and the published-engine benchmark."),
          PageBreak()]

    s += [P("7. Prototype build package", H1),
          img(first("prototypes/TJ110_exploded_3d.png", "prototypes/TJ110_exploded_section.png"),
              caption="Exploded view: every part in assembly order."),
          img(first("prototypes/TJ110_exploded_section.png", "diagrams/cad_TJ110_section.png"),
              caption="Exploded section with part labels."), PageBreak(),
          img("prototypes/TJ110_parts_sheet.png", caption="Every part laid out separately with material, quantity and key dimensions."),
          P("40 unique parts (117 placed); engine ≈ 1.96 kg, 239 mm long. Indicative cost CAD $5,035–17,880 including "
            "ECU, instrumentation and test stand (engine parts $3,235–11,410). Manufacturing routes, fits, balancing, the "
            "16-step assembly sequence and blank results sheets are in prototypes/README.md.", BODY), PageBreak()]

    s += [P("8. Testing and safety", H1),
          table([["#", "Test", "Why"],
                 ["T0", "Rotor balance and spin through 23/36 krpm on the starter", "Checks O-ring mounts and balance"],
                 ["T1–T3", "Propane ignition, kerosene transition, idle", "Finds the real self-sustaining and idle speeds (least certain model result)"],
                 ["T4–T5", "10 krpm steps to 110 krpm with thrust, EGT, fuel, p3", "Calibrates compressor efficiency and combustion efficiency"],
                 ["T6", "Nozzle trim to EGT ≈ 700 °C", "Final tuning"]],
                [12 * mm, 80 * mm, W - 92 * mm]),
          Spacer(1, 6),
          P("<b>Safety.</b> The wheels store ≈ 7 kJ at full speed and the casing will not contain a burst: never stand in "
            "the plane of rotation, run behind a barrier, and use an ECU speed limit. Kerosene only, CO₂ extinguishers, "
            "a hot-start procedure, ear protection (120–130 dB(A)), supervised runs only. Full procedure: docs/safety.md."),
          P("9. Limitations", H1),
          P("• Nothing is validated against measurements of this engine.<br/>"
            "• Losses come from correlations (Wiesner, Soderberg, Rodgers-type) plus assumed small-size and build penalties; no CFD.<br/>"
            "• The low-speed compressor map is assumed; the model's idle (51 krpm) is likely pessimistic.<br/>"
            "• Material data are approximate handbook trends, not certified allowables.<br/>"
            "• No transient (start-up) model, no heat-transfer model, no unbalance-response amplitudes."),
          P("10. Key references", H1),
          P("Saravanamuttoo H.I.H. et al. (2017) Gas Turbine Theory, 7th ed. Pearson.<br/>"
            "Dixon S.L., Hall C.A. (2014) Fluid Mechanics and Thermodynamics of Turbomachinery, 7th ed.<br/>"
            "Lefebvre A.H., Ballal D.R. (2010) Gas Turbine Combustion. doi:10.1201/9781420086058<br/>"
            "Wiesner F.J. (1967) A review of slip factors for centrifugal impellers. J. Eng. Power.<br/>"
            "Smith S.F. (1965) A simple correlation of turbine efficiency. J. R. Aeronaut. Soc.<br/>"
            "Larson F.R., Miller J. (1952) A time-temperature relationship for rupture and creep stresses.<br/>"
            "Jeffcott H.H. (1919) The lateral vibration of loaded shafts in the neighbourhood of a whirling speed. Phil. Mag.<br/>"
            "van den Hout F., Koullen J. (1996) The design, manufacture and successful operation of a very small turbojet "
            "engine. ASME 96-GT-456. doi:10.1115/96-gt-456<br/>"
            "Full list (40 sources): references/references.bib", SMALL)]

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=18 * mm, title="Turbojet Engine - Type TJ-110", author="roosterbrown14")
    doc.build(s, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    build()
    print(OUT)
