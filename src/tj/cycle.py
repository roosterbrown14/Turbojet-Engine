"""Design-point thermodynamic cycle of a single-spool turbojet (semi-perfect gas).

Stations (SAE ARP755 style):
  0 ambient   1 bellmouth exit / compressor face (2 in many texts)   3 diffuser exit
  4 turbine inlet (NGV)   5 turbine exit   9 nozzle exit
Losses: bellmouth total-pressure recovery, compressor isentropic efficiency, combustor pressure
loss and combustion efficiency, mechanical efficiency (bearings), turbine isentropic efficiency,
jet-pipe total-pressure loss, convergent nozzle (choked or not) with a velocity coefficient.
A small leakage fraction of compressor air bypasses the turbine (bearing cooling, seals).
"""
from dataclasses import dataclass

import numpy as np

from .fuels import FUELS
from .gas import air, burn, products


@dataclass
class CycleInputs:
    mdot: float = 0.25          # compressor air flow, kg/s
    pr_c: float = 2.8
    eta_c: float = 0.76
    TIT: float = 1100.0         # K, turbine inlet total temperature
    eta_t: float = 0.80
    eta_b: float = 0.90
    eta_m: float = 0.98
    dp_comb: float = 0.05       # fraction of p03
    pi_inlet: float = 0.99
    pi_jetpipe: float = 0.98
    leak: float = 0.02          # fraction of compressor air lost before the turbine
    cv_nozzle: float = 0.97     # nozzle velocity coefficient
    T0: float = 288.15
    p0: float = 101_325.0
    V0: float = 0.0             # flight speed, m/s
    fuel: str = "Jet A-1"


def nozzle(g, mdot, T05, p05, p0, cv):
    """Convergent nozzle exit state. Returns velocity, area, exit pressure, Mach, choked flag."""
    gam = g.gamma(0.5 * (T05 + 0.85 * T05))
    p_crit = p05 * (2 / (gam + 1)) ** (gam / (gam - 1))
    choked = p_crit > p0
    p9 = p_crit if choked else p0
    T9s = g.T_isentropic(T05, p9 / p05)
    dh = (g.h(T05) - g.h(T9s)) * cv**2
    V9 = np.sqrt(2 * dh)
    T9 = g.T_from_h(g.h(T05) - V9**2 / 2, guess=T9s)
    rho9 = p9 / (g.R * T9)
    A9 = mdot / (rho9 * V9)
    M9 = V9 / np.sqrt(g.gamma(T9) * g.R * T9)
    return V9, A9, p9, M9, choked, T9


def run(ci: CycleInputs):
    s = {}
    # ram + bellmouth
    T01 = ci.T0 + ci.V0**2 / (2 * air.cp(ci.T0))
    p01 = ci.p0 * air.pr_from_T(ci.T0, T01) * ci.pi_inlet
    s[0] = dict(T0=ci.T0, p0=ci.p0)
    s[1] = dict(T0=T01, p0=p01)
    # compressor
    T03s = air.T_isentropic(T01, ci.pr_c)
    w_c = (air.h(T03s) - air.h(T01)) / ci.eta_c
    T03 = air.T_from_h(air.h(T01) + w_c, guess=T03s + 20)
    p03 = p01 * ci.pr_c
    s[3] = dict(T0=T03, p0=p03)
    # combustor
    m_core = ci.mdot * (1 - ci.leak)
    far = burn(T03, ci.TIT, ci.fuel, ci.eta_b)
    mf = far * m_core
    p04 = p03 * (1 - ci.dp_comb)
    s[4] = dict(T0=ci.TIT, p0=p04)
    g = products(far, ci.fuel)
    # turbine drives compressor
    m4 = m_core + mf
    w_t = ci.mdot * w_c / (ci.eta_m * m4)
    T05 = g.T_from_h(g.h(ci.TIT) - w_t, guess=ci.TIT - w_t / 1150)
    T05s = g.T_from_h(g.h(ci.TIT) - w_t / ci.eta_t, guess=T05 - 20)
    p05 = p04 * g.pr_from_T(ci.TIT, T05s)
    s[5] = dict(T0=T05, p0=p05)
    p05j = p05 * ci.pi_jetpipe
    V9, A9, p9, M9, choked, T9 = nozzle(g, m4, T05, p05j, ci.p0, ci.cv_nozzle)
    s[9] = dict(T0=T05, p0=p05j, T=T9, p=p9, V=V9, M=M9)
    F_gross = m4 * V9 + A9 * (p9 - ci.p0)
    F = F_gross - ci.mdot * ci.V0
    fuel = FUELS[ci.fuel]
    tsfc = mf / F if F > 0 else np.inf
    P_jet = 0.5 * (m4 * V9**2 - ci.mdot * ci.V0**2)
    eta_th = P_jet / (mf * fuel.LHV)
    return dict(
        stations=s, far=far, mdot_fuel=mf, thrust=F, F_gross=F_gross, specific_thrust=F / ci.mdot,
        tsfc=tsfc, tsfc_g_per_kNs=tsfc * 1e6, fuel_l_per_min=mf / fuel.density * 1000 * 60,
        V9=V9, A9=A9, D9=2 * np.sqrt(A9 / np.pi), M9=M9, choked=choked, p9=p9, w_c=w_c, w_t=w_t,
        P_comp=ci.mdot * w_c, P_jet=P_jet, eta_thermal=eta_th, EGT=T05, T03=T03, p03=p03, p04=p04, p05=p05,
        m4=m4, phi=far / fuel.far_stoich, pr_t=p04 / p05, gas=g,
    )


def ts_points(ci: CycleInputs, r=None):
    """Temperature-entropy coordinates of the cycle for plotting (entropy relative to station 0)."""
    r = r or run(ci)
    st = r["stations"]
    g = r["gas"]

    def s_air(T, p):
        return air.phi(T) - air.R * np.log(p / ci.p0)

    def s_gas(T, p):
        return g.phi(T) - g.R * np.log(p / ci.p0) + (air.phi(st[3]["T0"]) - air.R * np.log(st[3]["p0"] / ci.p0)
                                                     - (g.phi(st[3]["T0"]) - g.R * np.log(st[3]["p0"] / ci.p0)))
    pts = {}
    pts["0"] = (s_air(st[0]["T0"], st[0]["p0"]), st[0]["T0"])
    pts["1"] = (s_air(st[1]["T0"], st[1]["p0"]), st[1]["T0"])
    pts["3"] = (s_air(st[3]["T0"], st[3]["p0"]), st[3]["T0"])
    pts["4"] = (s_gas(st[4]["T0"], st[4]["p0"]), st[4]["T0"])
    pts["5"] = (s_gas(st[5]["T0"], st[5]["p0"]), st[5]["T0"])
    pts["9"] = (s_gas(st[9]["T"], st[9]["p"]), st[9]["T"])
    return pts, s_air, s_gas
