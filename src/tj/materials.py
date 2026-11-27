"""Material property database for the engine parts.

IMPORTANT: strength-versus-temperature tables and Larson-Miller stress-rupture curves are
APPROXIMATE REPRESENTATIVE VALUES compiled from typical handbook and supplier data-sheet trends
(ASM Handbook vol. 2 and vol. 1, Special Metals / Haynes / ATI data sheets, MMPDS-style
trends). They are good enough to rank materials and to size a design study. They are NOT
design allowables. Check the supplier's certified data for the exact alloy, temper and form
before making a part that will spin.

Units: temperature degC in tables, MPa for strength, kg/m^3, GPa, um/(m K), W/(m K).
"""
from dataclasses import dataclass, field

import numpy as np

LMP_C = 20.0   # Larson-Miller constant (Larson & Miller 1952), used for every alloy here


@dataclass
class Material:
    key: str
    name: str
    family: str
    density: float
    E: float
    nu: float
    alpha: float             # thermal expansion, um/(m K)
    k: float                 # thermal conductivity, W/(m K)
    t_max: float             # practical max service / oxidation temperature, degC
    t_tab: list              # temperatures for the strength table, degC
    uts: list                # ultimate tensile strength, MPa
    ys: list                 # 0.2 % yield strength, MPa
    lmp_pts: list            # (P/1000, rupture stress MPa) pairs, P = T_K (20 + log10 t_h)
    form: str                # how a hobbyist/university shop would obtain it
    machinability: int       # 1 (hard) .. 5 (easy)
    cost_cad_kg: float       # indicative small-quantity cost, CAD/kg (bar/sheet/casting service)
    uses: list = field(default_factory=list)

    def UTS(self, T):
        return float(np.interp(T, self.t_tab, self.uts))

    def YS(self, T):
        return float(np.interp(T, self.t_tab, self.ys))

    def specific_strength(self, T):
        """Yield strength / density, kN m/kg."""
        return self.YS(T) * 1e3 / self.density

    def _lmp_fit(self):
        P = np.array([p for p, _ in self.lmp_pts])
        s = np.log10([s for _, s in self.lmp_pts])
        return np.polyfit(P, s, 2 if len(P) > 3 else 1)

    def rupture_stress(self, T_c, hours):
        P = (T_c + 273.15) * (LMP_C + np.log10(hours)) / 1000.0
        return float(10 ** np.polyval(self._lmp_fit(), P))

    def rupture_life(self, T_c, stress):
        """Hours to stress-rupture at constant temperature and stress (Larson-Miller)."""
        c = self._lmp_fit().copy()
        c[-1] -= np.log10(max(stress, 1e-3))
        roots = np.roots(c)
        roots = roots[np.isreal(roots)].real
        Plo, Phi = min(p for p, _ in self.lmp_pts) - 3, max(p for p, _ in self.lmp_pts) + 3
        roots = [r for r in roots if Plo <= r <= Phi]
        if not roots:
            return np.inf if stress < min(s for _, s in self.lmp_pts) else 0.0
        # the decreasing branch: pick the root where stress falls with P
        P = min(roots, key=lambda r: abs(r - np.mean([p for p, _ in self.lmp_pts])))
        return float(10 ** (P * 1000.0 / (T_c + 273.15) - LMP_C))


MATERIALS = {m.key: m for m in [
    Material("Al2618", "Aluminum 2618-T61", "Aluminum alloy", 2760, 74, 0.33, 22.3, 147, 230,
             [20, 100, 150, 200, 250, 300], [440, 420, 390, 330, 220, 100], [370, 360, 340, 290, 180, 80],
             [(9, 330), (10, 250), (11, 160), (12, 80)], "forged bar; 5-axis machined", 4, 60,
             ["compressor wheel"]),
    Material("Al7075", "Aluminum 7075-T6", "Aluminum alloy", 2810, 72, 0.33, 23.4, 130, 130,
             [20, 100, 150, 200, 250], [572, 485, 380, 215, 110], [503, 450, 360, 185, 90],
             [(8, 450), (9, 330), (10, 180), (11, 70)], "plate/bar; machined", 4, 35,
             ["compressor wheel (cold only)", "front cover"]),
    Material("Al6061", "Aluminum 6061-T6", "Aluminum alloy", 2700, 69, 0.33, 23.6, 167, 150,
             [20, 100, 150, 200, 250], [310, 290, 235, 130, 60], [276, 260, 215, 105, 45],
             [(8, 250), (9, 170), (10, 100), (11, 45)], "bar/tube; machined", 5, 15,
             ["inlet", "front cover", "outer casing", "mounts"]),
    Material("Ti64", "Titanium Ti-6Al-4V", "Titanium alloy", 4430, 114, 0.34, 8.9, 6.7, 400,
             [20, 200, 300, 400, 500], [950, 790, 720, 680, 620], [880, 690, 610, 570, 500],
             [(14, 600), (15, 450), (16, 280), (17, 130)], "bar; machined (slow) or 3-D printed (SLM)", 2, 120,
             ["compressor wheel (hot/high speed)"]),
    Material("SS174", "Stainless 17-4PH H1025", "Precipitation-hardened stainless", 7800, 197, 0.27, 10.8, 18, 315,
             [20, 200, 300, 400], [1070, 980, 940, 860], [1000, 920, 880, 800],
             [(14, 900), (16, 650), (18, 300)], "bar; machined then aged", 3, 30,
             ["shaft", "nuts"]),
    Material("S4140", "Steel AISI 4140 (Q&T)", "Low-alloy steel", 7850, 205, 0.29, 12.3, 42.6, 400,
             [20, 200, 300, 400, 500], [1020, 960, 920, 840, 680], [900, 840, 800, 720, 560],
             [(13, 650), (15, 400), (17, 150)], "bar; machined, hardened and ground", 3, 10,
             ["shaft"]),
    Material("IN718", "Inconel 718", "Nickel superalloy (wrought)", 8190, 200, 0.29, 13.0, 11.4, 700,
             [20, 400, 600, 650, 700, 760, 870], [1375, 1280, 1240, 1210, 1100, 950, 600],
             [1100, 1030, 1000, 990, 950, 850, 500],
             [(20, 1000), (21, 800), (22, 640), (23, 470), (24, 300), (25, 160), (26, 70)],
             "bar; machined (difficult) or wire-EDM", 1, 150,
             ["turbine wheel (cooler engines)", "shaft (hot end)", "NGV"]),
    Material("IN713C", "Inconel 713C (cast)", "Nickel superalloy (cast)", 7910, 206, 0.30, 10.6, 10.9, 980,
             [20, 600, 760, 870, 980, 1050], [850, 860, 900, 760, 500, 300], [740, 730, 740, 650, 420, 250],
             [(22, 700), (24, 480), (26, 280), (28, 130)],
             "investment-cast blank (commercial turbine wheels) then finish-machined", 1, 250,
             ["turbine wheel", "NGV"]),
    Material("MARM247", "MAR-M247 (cast)", "Nickel superalloy (cast)", 8540, 206, 0.30, 12.5, 9.0, 1050,
             [20, 760, 870, 980, 1050], [965, 1035, 900, 650, 450], [815, 860, 800, 550, 380],
             [(22, 900), (24, 640), (26, 400), (28, 200), (30, 70)],
             "investment casting only (foundry service)", 1, 500,
             ["turbine wheel (high TIT)"]),
    Material("IN625", "Inconel 625", "Nickel superalloy (wrought)", 8440, 205, 0.31, 12.8, 9.8, 980,
             [20, 650, 760, 870], [930, 800, 650, 400], [517, 400, 380, 300],
             [(20, 420), (22, 230), (24, 100), (26, 35)], "sheet/bar", 2, 90,
             ["combustor liner", "NGV", "nozzle"]),
    Material("HX", "Hastelloy X", "Nickel superalloy (sheet)", 8220, 205, 0.32, 13.9, 9.1, 1175,
             [20, 650, 870, 1000], [785, 590, 340, 150], [360, 280, 240, 110],
             [(20, 300), (22, 150), (24, 70), (26, 25)], "sheet 0.3-0.5 mm", 2, 110,
             ["combustor liner"]),
    Material("H230", "Haynes 230", "Nickel superalloy (sheet)", 8970, 211, 0.31, 12.7, 8.9, 1150,
             [20, 760, 870, 980], [860, 640, 440, 250], [390, 300, 280, 160],
             [(20, 380), (22, 200), (24, 95), (26, 38)], "sheet", 2, 130,
             ["combustor liner"]),
    Material("SS310", "Stainless 310", "Austenitic stainless", 7900, 200, 0.29, 15.9, 14.2, 1035,
             [20, 600, 800, 1000], [655, 470, 200, 60], [310, 170, 120, 40],
             [(17, 300), (19, 150), (21, 60), (23, 20)], "sheet/tube", 3, 25,
             ["combustor liner", "vaporizer tubes", "nozzle"]),
    Material("SS321", "Stainless 321", "Austenitic stainless", 7920, 193, 0.29, 16.6, 16.1, 870,
             [20, 400, 600, 800], [620, 470, 400, 160], [240, 170, 150, 95],
             [(17, 280), (19, 130), (21, 50), (23, 17)], "sheet/tube", 3, 20,
             ["nozzle", "vaporizer tubes", "exhaust cone"]),
    Material("SS304", "Stainless 304", "Austenitic stainless", 8000, 193, 0.29, 17.3, 16.2, 870,
             [20, 400, 600, 800], [515, 420, 330, 140], [205, 150, 120, 80],
             [(17, 260), (19, 120), (21, 45), (23, 15)], "sheet/tube", 3, 15,
             ["outer casing", "nozzle", "fuel lines"]),
]}

# Bearings: limiting temperatures (degC) and DN limits (bore mm x rpm) for grease-free oil-mist lubrication
BEARINGS = {
    "52100 steel balls": {"t_max": 150, "DN_max": 0.9e6, "ball_density": 7810},
    "Hybrid Si3N4 balls": {"t_max": 220, "DN_max": 1.4e6, "ball_density": 3200},
}
