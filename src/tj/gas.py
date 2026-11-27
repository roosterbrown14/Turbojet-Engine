"""Thermodynamic properties of air and kerosene combustion products (semi-perfect gas).

Each species has a molar heat capacity cp(T) given by a quartic least-squares fit to tabulated
JANAF values at 300-2000 K. Mixtures are ideal. Enthalpy and the entropy function
are integrated analytically from a 298.15 K reference. No dissociation is modelled, so results
above about 2000 K (near-stoichiometric flames) are overestimates.

Valid range: 220-2100 K. Air cp is within 0.5 % of tabulated values at 300-1500 K (tests/).
"""
from functools import lru_cache

import numpy as np

R_U = 8.314462618       # J/(mol K)
T_REF = 298.15

# Molar masses, kg/mol
M = {"N2": 0.0280134, "O2": 0.0319988, "Ar": 0.039948, "CO2": 0.0440095, "H2O": 0.0180153}

# Tabulated cp, J/(mol K) (JANAF thermochemical tables).
_T_PTS = np.array([300.0, 400.0, 500.0, 600.0, 800.0, 1000.0, 1500.0, 2000.0])
_CP_PTS = {
    "N2": [29.12, 29.25, 29.58, 30.11, 31.43, 32.70, 34.85, 36.00],
    "O2": [29.39, 30.11, 31.09, 32.09, 33.73, 34.88, 36.54, 37.78],
    "Ar": [20.79] * 8,
    "CO2": [37.22, 41.33, 44.63, 47.32, 51.43, 54.31, 58.38, 60.43],
    "H2O": [33.60, 34.26, 35.22, 36.32, 38.74, 41.27, 46.94, 51.18],
}
# Polynomial coefficients a0..a4 per species: cp = sum a_k T^k (fit in T/1000 for conditioning)
_FIT = {k: np.polyfit(_T_PTS / 1000.0, v, 4)[::-1] for k, v in _CP_PTS.items()}
COEF = {k: np.array([c / 1000.0**i for i, c in enumerate(v)]) for k, v in _FIT.items()}

AIR = {"N2": 0.7808, "O2": 0.2095, "Ar": 0.0097}   # mole fractions (CO2 folded into Ar)


def _species_cp(sp, T):
    a = COEF[sp]
    return a[0] + a[1] * T + a[2] * T**2 + a[3] * T**3 + a[4] * T**4


def _species_h(sp, T):
    """Sensible molar enthalpy relative to 298.15 K, J/mol."""
    a = COEF[sp]
    F = lambda t: a[0] * t + a[1] * t**2 / 2 + a[2] * t**3 / 3 + a[3] * t**4 / 4 + a[4] * t**5 / 5  # noqa: E731
    return F(T) - F(T_REF)


def _species_phi(sp, T):
    """Entropy function integral of cp/T dT from 298.15 K, J/(mol K)."""
    a = COEF[sp]
    F = lambda t: a[0] * np.log(t) + a[1] * t + a[2] * t**2 / 2 + a[3] * t**3 / 3 + a[4] * t**4 / 4  # noqa: E731
    return F(T) - F(T_REF)


class Mixture:
    """An ideal-gas mixture defined by mole fractions."""

    def __init__(self, x: dict):
        tot = sum(x.values())
        self.x = {k: v / tot for k, v in x.items() if v > 0}
        self.M = sum(v * M[k] for k, v in self.x.items())
        self.R = R_U / self.M

    def cp(self, T):
        return sum(v * _species_cp(k, T) for k, v in self.x.items()) / self.M

    def gamma(self, T):
        c = self.cp(T)
        return c / (c - self.R)

    def h(self, T):
        return sum(v * _species_h(k, T) for k, v in self.x.items()) / self.M

    def phi(self, T):
        return sum(v * _species_phi(k, T) for k, v in self.x.items()) / self.M

    def T_from_h(self, h, guess=600.0):
        T = guess
        for _ in range(50):
            dT = (h - self.h(T)) / self.cp(T)
            T += dT
            if abs(dT) < 1e-6:
                break
        return T

    def T_isentropic(self, T1, pr):
        """Temperature after an isentropic change of total-pressure ratio pr = p2/p1."""
        target = self.phi(T1) + self.R * np.log(pr)
        T = T1 * pr ** ((self.gamma(T1) - 1) / self.gamma(T1))
        for _ in range(50):
            dT = (target - self.phi(T)) / (self.cp(T) / T)
            T += dT
            if abs(dT) < 1e-7:
                break
        return T

    def pr_from_T(self, T1, T2):
        """Isentropic pressure ratio between two temperatures."""
        return float(np.exp((self.phi(T2) - self.phi(T1)) / self.R))


air = Mixture(AIR)


@lru_cache(maxsize=4096)
def _products_cached(far_key, fuel_name):
    from .fuels import FUELS
    return _products(far_key / 1e7, FUELS[fuel_name])


def _products(far, fuel):
    """Complete-combustion products of 1 kg dry air plus `far` kg fuel (lean only)."""
    n_air = 1.0 / air.M                          # mol of air per kg
    nf = far / fuel.M                           # mol fuel per kg air
    n = {k: v * n_air for k, v in air.x.items()}
    o2_need = nf * (fuel.C + fuel.H / 4 - fuel.O / 2)
    if o2_need > n["O2"] + 1e-15:
        raise ValueError("rich mixture: FAR above stoichiometric")
    n["O2"] -= o2_need
    n["CO2"] = n.get("CO2", 0.0) + nf * fuel.C
    n["H2O"] = n.get("H2O", 0.0) + nf * fuel.H / 2
    return Mixture(n)


def products(far, fuel_name="Jet A-1"):
    if far <= 0:
        return air
    return _products_cached(int(round(far * 1e7)), fuel_name)


def burn(T_in, T_out, fuel_name="Jet A-1", eta_b=1.0):
    """Fuel-air ratio that heats air from T_in to products at T_out.

    Energy balance on 1 kg air: (1+f) h_p(T_out) - h_air(T_in) = eta_b f LHV (sensible enthalpies
    referenced to 298.15 K; fuel enters at 298 K).
    """
    from .fuels import FUELS
    fuel = FUELS[fuel_name]
    f = air.cp(0.5 * (T_in + T_out)) * (T_out - T_in) / (eta_b * fuel.LHV)
    for _ in range(40):
        g = products(f, fuel_name)
        res = (1 + f) * g.h(T_out) - air.h(T_in) - eta_b * f * fuel.LHV
        dres = g.h(T_out) - eta_b * fuel.LHV
        f_new = f - res / dres
        if abs(f_new - f) < 1e-9:
            f = f_new
            break
        f = f_new
    return f


def flame_temperature(T_in, far, fuel_name="Jet A-1", eta_b=1.0):
    """Adiabatic products temperature for a given fuel-air ratio (no dissociation)."""
    from .fuels import FUELS
    fuel = FUELS[fuel_name]
    g = products(far, fuel_name)
    h_target = (air.h(T_in) + eta_b * far * fuel.LHV) / (1 + far)
    return g.T_from_h(h_target, guess=T_in + far * 40000)
