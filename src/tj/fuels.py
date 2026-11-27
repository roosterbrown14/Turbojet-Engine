"""Fuels considered for the engine. Lower heating values at 25 degC with water as vapour.

Values are typical handbook figures (Lefebvre & Ballal, Gas Turbine Combustion, 3rd ed.;
ASTM D1655 for Jet A-1). Real batches vary by about +/-1 %.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Fuel:
    name: str
    C: float            # atoms per molecule (surrogate formula)
    H: float
    O: float
    LHV: float          # J/kg
    density: float      # kg/m^3 at 15 degC (liquid; propane/butane as pressurized liquid)
    flash_c: float      # flash point, degC (approximate)
    note: str

    @property
    def M(self):
        return (12.011 * self.C + 1.008 * self.H + 15.999 * self.O) / 1000.0

    @property
    def far_stoich(self):
        o2 = self.C + self.H / 4 - self.O / 2
        return self.M / (o2 / 0.2095 * 0.028965)


FUELS = {
    "Jet A-1": Fuel("Jet A-1", 12, 23, 0, 43.2e6, 800.0, 38,
                    "Aviation kerosene. Standard for model turbines; mixed with about 5 % turbine oil."),
    "Kerosene (K-1)": Fuel("Kerosene (K-1)", 12, 24, 0, 43.0e6, 810.0, 43,
                           "Heating kerosene. Similar to Jet A-1; check sulphur and additives."),
    "Diesel": Fuel("Diesel", 12, 23, 0, 42.8e6, 840.0, 55,
                   "Heavier; harder to vaporize and to start, more soot."),
    "Propane": Fuel("Propane", 3, 8, 0, 46.35e6, 507.0, -104,
                    "Gas; used for starting and for gas-only test runs. Needs a pressure regulator."),
    "Butane": Fuel("Butane", 4, 10, 0, 45.7e6, 573.0, -60,
                   "Common start gas (often a propane/butane blend)."),
    "Ethanol": Fuel("Ethanol", 2, 6, 1, 26.8e6, 789.0, 13,
                    "Low energy per kg; needs about 1.6x the fuel flow."),
}
