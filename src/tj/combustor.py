"""Annular combustor sizing: volume, residence time, loading, air split and hole areas.

The engine uses the vaporizer (\"walking stick\" / straight-tube) layout common in small turbojets:
fuel is sprayed into heated tubes and leaves as a rich vapour into the primary zone.

* Residence time tau = rho3 V_liner / mdot_liner (bulk, primary+secondary+dilution).
* Combustion loading theta = mdot / (p3^1.75 V exp(T3/300))  (Lefebvre & Ballal), reported for
  comparison with large-engine practice. Small engines run at much higher loading, which is why
  their combustion efficiency is lower (85-95 %) and is taken as an input.
* Liner pressure loss: dp = (mdot_liner / (Cd A_holes))^2 / (2 rho3)  with Cd = 0.6.
* Primary-zone equivalence ratio from the air split.
"""
from dataclasses import dataclass, field

import numpy as np

from .fuels import FUELS
from .gas import air, flame_temperature


@dataclass
class CombustorDesign:
    mdot_air: float
    far: float
    T03: float
    p03: float
    r_in: float          # liner inner wall radius, m
    r_out: float         # liner outer wall radius, m
    length: float        # liner length, m
    dp_frac: float = 0.05
    split_primary: float = 0.30   # fraction of air entering the primary zone (incl. vaporizer air)
    split_secondary: float = 0.25
    n_vaporizers: int = 8
    fuel: str = "Jet A-1"
    Cd: float = 0.60
    out: dict = field(default_factory=dict)


def size(c: CombustorDesign):
    fuel = FUELS[c.fuel]
    rho3 = c.p03 / (air.R * c.T03)
    V = np.pi * (c.r_out**2 - c.r_in**2) * c.length
    tau = rho3 * V / c.mdot_air
    theta = c.mdot_air / ((c.p03 / 1e3) ** 1.75 * V * np.exp(c.T03 / 300))
    dp = c.dp_frac * c.p03
    A_eff = c.mdot_air / np.sqrt(2 * rho3 * dp)
    A_holes = A_eff / c.Cd
    phi_overall = c.far / fuel.far_stoich
    phi_primary = c.far / (c.split_primary * fuel.far_stoich)
    T_primary = flame_temperature(c.T03, min(c.far / c.split_primary, fuel.far_stoich), c.fuel)
    Aref = np.pi * (c.r_out**2 - c.r_in**2)
    Vref = c.mdot_air / (rho3 * Aref)
    c.out = dict(volume=V, tau=tau, theta=theta, A_holes=A_holes, phi_overall=phi_overall,
                 phi_primary=phi_primary, T_primary=T_primary, V_ref=Vref, A_ref=Aref, rho3=rho3,
                 split_dilution=1 - c.split_primary - c.split_secondary,
                 hole_d_equiv=2 * np.sqrt(A_holes / np.pi / 120))
    return c.out
