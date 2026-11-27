"""Integrated engine design: compressor meanline -> cycle -> turbine meanline -> combustor ->
nozzle -> stresses, creep life and rotordynamics. One call returns everything a study needs.

Component efficiencies are not inputs here: they come out of the compressor and turbine
meanline models (sized for the actual flow and speed), and the cycle is iterated until they
agree.
"""
from dataclasses import dataclass, field, replace

import numpy as np

from . import combustor as cb
from . import compressor as cm
from . import cycle as cy
from . import rotor as rt
from . import turbine as tb
from .materials import BEARINGS, MATERIALS


@dataclass
class EngineSpec:
    # cycle
    mdot: float = 0.25
    pr: float = 2.8
    TIT: float = 1100.0
    rpm: float = 110_000
    fuel: str = "Jet A-1"
    eta_b: float = 0.90
    dp_comb: float = 0.05
    T0: float = 288.15
    p0: float = 101_325.0
    # compressor
    beta2b: float = 30.0
    Z: int = 14
    hub_tip: float = 0.35
    clear_c: float = 0.30e-3
    build_penalty: float = 0.04
    diffuser_ratio: float = 1.50
    # turbine
    phi_t: float = 0.65
    psi_t: float = 1.3
    clear_t: float = 0.30e-3
    aspect_t: float = 1.0
    Zr: int = 27
    Zn: int = 19
    # materials
    mat_comp: str = "Al2618"
    mat_turb: str = "IN713C"
    mat_shaft: str = "SS174"
    bearing: str = "Hybrid Si3N4 balls"
    # mechanical layout
    shaft_d: float = 8.0e-3        # at the bearings (608-size bore)
    shaft_d_mid: float = 10.0e-3
    bearing_span: float = 0.085
    k_bearing: float = 1.5e6       # N/m per bearing: bearing outer races in O-ring dampers (phase H)
    casing_wall: float = 1.0e-3


@dataclass
class EngineResult:
    spec: EngineSpec
    comp: dict = field(default_factory=dict)
    cyc: dict = field(default_factory=dict)
    turb: dict = field(default_factory=dict)
    comb: dict = field(default_factory=dict)
    mech: dict = field(default_factory=dict)
    geom: dict = field(default_factory=dict)

    @property
    def thrust(self):
        return self.cyc["thrust"]


def build(s: EngineSpec, rotordynamics=False) -> EngineResult:
    cd = cm.CompressorDesign(mdot=s.mdot, pr=s.pr, rpm=s.rpm, T01=s.T0, p01=s.p0 * 0.99, beta2b=s.beta2b, Z=s.Z,
                             hub_tip=s.hub_tip, clearance=s.clear_c, build_penalty=s.build_penalty,
                             diffuser_ratio=s.diffuser_ratio)
    comp = cm.design(cd)
    ci = cy.CycleInputs(mdot=s.mdot, pr_c=s.pr, eta_c=comp["eta"], TIT=s.TIT, eta_t=0.80, eta_b=s.eta_b,
                        dp_comb=s.dp_comb, T0=s.T0, p0=s.p0, fuel=s.fuel)
    for _ in range(30):
        cyc = cy.run(ci)
        td = tb.TurbineDesign(work=cyc["w_t"], mdot=cyc["m4"], T04=s.TIT, p04=cyc["p04"], rpm=s.rpm, far=cyc["far"],
                              phi=s.phi_t, psi=s.psi_t, r_mean=None, aspect=s.aspect_t, clearance=s.clear_t,
                              Zr=s.Zr, Zn=s.Zn)
        turb = tb.design(td)
        if abs(turb["eta"] - ci.eta_t) < 1e-6:
            break
        ci = replace(ci, eta_t=turb["eta"])
    cyc = cy.run(ci)

    # ---- geometry
    r2 = comp["r2"]
    r_case_in = comp["r3"] + 0.004               # room for the diffuser vanes' outer ring
    r_case_out = r_case_in + s.casing_wall
    shaft_tunnel_r = 0.011
    liner_in = shaft_tunnel_r + 0.004
    liner_out = r_case_in - 0.005
    liner_len = 0.075
    cbd = cb.CombustorDesign(mdot_air=s.mdot * 0.98, far=cyc["far"], T03=cyc["T03"], p03=cyc["p03"], r_in=liner_in,
                             r_out=liner_out, length=liner_len, dp_frac=s.dp_comb, fuel=s.fuel)
    comb = cb.size(cbd)
    geom = dict(D_case=2 * r_case_out, r_case_in=r_case_in, liner_in=liner_in, liner_out=liner_out,
                liner_len=liner_len, shaft_tunnel_r=shaft_tunnel_r, D_nozzle=cyc["D9"],
                D_turb_tip=turb["Dt"], D_comp=comp["D2"], D_inducer=comp["D1t"])

    # ---- mechanical: stresses, creep, bearings
    mc, mt = MATERIALS[s.mat_comp], MATERIALS[s.mat_turb]
    T_imp_c = cyc["T03"] - 273.15 - 0.3 * (cyc["T03"] - s.T0)   # wheel metal temp: between inlet and exit air
    s_imp, sf_imp, burst_imp = cm.impeller_stress(comp["U2"], mc, T_imp_c)
    s_root = tb.blade_root_stress(td, mt)
    T_blade_c = turb["T0rel"] - 273.15 - 30.0      # root runs a little cooler than the gas
    life_blade = mt.rupture_life(T_blade_c, s_root * 1.0)
    r_rim = turb["rh"] - 0.001
    disc_t = 0.012
    P_rim = tb.rim_load(td, mt, r_rim, disc_t)
    _, _, st_disc, st_avg = tb.disc_stress(s.rpm, s.shaft_d / 2, r_rim, mt.density, mt.nu, P_rim)
    T_disc_c = T_blade_c - 120.0
    burst_turb = np.sqrt(0.85 * mt.UTS(T_disc_c) / st_avg)
    life_disc = mt.rupture_life(T_disc_c, st_disc.max())
    br = BEARINGS[s.bearing]
    DN = s.shaft_d * 1e3 * s.rpm
    mech = dict(stress_impeller=s_imp, sf_impeller=sf_imp, burst_impeller=burst_imp, T_impeller=T_imp_c,
                stress_blade_root=s_root, T_blade=T_blade_c, life_blade_h=life_blade, rim_load=P_rim,
                stress_disc_max=st_disc.max(), stress_disc_avg=st_avg, burst_turbine=burst_turb, T_disc=T_disc_c,
                life_disc_h=life_disc, sf_blade_yield=mt.YS(T_blade_c) / s_root, DN=DN, DN_ok=DN <= br["DN_max"],
                tip_speed_turb=turb["U"] * turb["rt"] / turb["rm"])
    res = EngineResult(s, comp, cyc, turb, comb, mech, geom)
    if rotordynamics:
        mech.update(rotor_summary(res))
    return res


def make_rotor(res: EngineResult, k_bearing=None, span=None, d_mid=None):
    s = res.spec
    k_bearing = k_bearing or s.k_bearing
    span = span or s.bearing_span
    d_mid = d_mid or s.shaft_d_mid
    mc, mt, ms = MATERIALS[s.mat_comp], MATERIALS[s.mat_turb], MATERIALS[s.mat_shaft]
    oc = 0.012          # compressor wheel centre ahead of front bearing
    ot = 0.014          # turbine wheel centre behind rear bearing
    L = oc + span + ot + 0.006
    x = np.linspace(0, L, 41)
    xb1, xb2 = oc + 0.002, oc + 0.002 + span
    d = np.array([s.shaft_d if (xm < xb1 + 0.006 or xm > xb2 - 0.006) else d_mid
                  for xm in 0.5 * (x[1:] + x[:-1])])
    r2 = res.comp["r2"]
    # compressor wheel: a cone-like solid, about 30 % of the tip-radius cylinder volume
    m_c = mc.density * np.pi * r2**2 * 0.022 * 0.30
    Ip_c, Id_c = rt.disc_props(m_c, r2 * 0.75, 0.022)
    rt_t = res.turb["rt"]
    m_t = mt.density * (np.pi * res.turb["rh"] ** 2 * 0.012 + 0.06 * res.turb["chord"] ** 2 * res.turb["h"] * s.Zr)
    Ip_t, Id_t = rt.disc_props(m_t, 0.85 * rt_t, 0.012)
    discs = [rt.Disc(oc - 0.004, m_c, Id_c, Ip_c, "compressor"), rt.Disc(xb2 + ot, m_t, Id_t, Ip_t, "turbine")]
    return rt.Rotor(x, d, E=ms.E * 1e9, rho=ms.density, discs=discs, bearings=[(xb1, k_bearing), (xb2, k_bearing)]), \
        dict(m_comp=m_c, m_turb=m_t, L_shaft=L, xb=(xb1, xb2))


def rotor_summary(res: EngineResult):
    R, info = make_rotor(res)
    Omega_op = res.spec.rpm * 2 * np.pi / 60
    crit = R.critical_speeds(2.5 * Omega_op)
    crit_rpm = [c * 60 / (2 * np.pi) for c in crit]
    above = [c for c in crit_rpm if c > res.spec.rpm]
    below = [c for c in crit_rpm if c <= res.spec.rpm]
    margin = (min(above) / res.spec.rpm - 1) if above else np.inf
    return dict(critical_rpm=crit_rpm, crit_margin=margin, crit_below=below, **info)
