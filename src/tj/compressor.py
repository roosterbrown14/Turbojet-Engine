"""Meanline model of a single-stage centrifugal compressor with a vaned diffuser.

Design (sizing) path: given mass flow, pressure ratio and shaft speed, find the inducer that
minimizes the inducer tip relative Mach number, the tip speed that delivers the work, the exit
width from continuity, and a stage efficiency from published correlations:

* slip factor: Wiesner (1967)  sigma = 1 - sqrt(cos beta2b) / Z^0.7  (beta2b from radial)
* base efficiency vs specific speed: a parabola in ln(Ns) fitted to the Rodgers / Balje trend,
  peak 0.84 at Ns = 0.75 for a large, smooth reference stage
* size (Reynolds) correction: Wiesner (1979) (1 - eta) / (1 - eta_ref) = (Re_ref / Re)^0.1
* tip clearance: delta eta = 0.35 * (clearance / exit blade height)   (Senoo-type rule)
* backsweep benefit: +0.5 point per 10 deg up to 40 deg
* a "build quality" penalty for hand-finished hobby/university hardware (default 4 points),
  chosen so the stage lands in the 0.70-0.77 range reported for small model-turbine compressors

Off-design path: a semi-empirical map (CompressorMap) built from the same geometry: Euler work
with slip at the actual flow coefficient, and an efficiency that falls quadratically with
incidence away from the design flow coefficient, with choke at the inducer throat.
"""
from dataclasses import dataclass, field

import numpy as np

from .gas import air

NU_AIR = 1.48e-5   # kinematic viscosity at ~15 degC, m^2/s


@dataclass
class CompressorDesign:
    mdot: float = 0.25            # kg/s
    pr: float = 2.8               # total-to-total
    rpm: float = 110_000
    T01: float = 288.15
    p01: float = 101_325.0
    beta2b: float = 30.0          # exit blade backsweep from radial, deg
    Z: int = 14                   # blades at exit (main + splitter)
    hub_tip: float = 0.35         # inducer hub/tip radius ratio
    clearance: float = 0.30e-3    # m, tip clearance (hobby machining)
    phi2: float = 0.28            # exit flow coefficient Cr2/U2
    blockage2: float = 0.90
    build_penalty: float = 0.04
    parasitic: float = 0.04       # disc friction + recirculation, fraction of Euler work
    diffuser_ratio: float = 1.50  # vaned diffuser exit radius / impeller tip radius
    eta_override: float | None = None
    # results
    out: dict = field(default_factory=dict)


def slip_wiesner(beta2b_deg, Z, r1_r2=0.0):
    """Wiesner (1967) slip factor with its inlet radius-ratio limit correction."""
    sig = 1.0 - np.sqrt(np.cos(np.radians(beta2b_deg))) / Z**0.7
    eps = np.exp(-8.16 * np.cos(np.radians(beta2b_deg)) / Z)
    if r1_r2 > eps:
        sig *= 1 - ((r1_r2 - eps) / (1 - eps)) ** 3
    return sig


def eta_specific_speed(Ns):
    """Peak stage efficiency of a large reference stage vs dimensionless specific speed."""
    return 0.84 - 0.15 * np.log(Ns / 0.75) ** 2


def design(c: CompressorDesign, iterate=True):
    omega = c.rpm * 2 * np.pi / 60
    rho01 = c.p01 / (air.R * c.T01)
    T03s = air.T_isentropic(c.T01, c.pr)
    dh_s = air.h(T03s) - air.h(c.T01)

    # --- inducer: choose tip radius to minimize relative tip Mach number
    a01 = np.sqrt(air.gamma(c.T01) * air.R * c.T01)
    best = None
    for r1t in np.linspace(0.008, 0.04, 400):
        r1h = c.hub_tip * r1t
        A1 = np.pi * (r1t**2 - r1h**2)
        C1 = c.mdot / (rho01 * A1)
        ok = True
        for _ in range(8):   # static density correction
            T1 = c.T01 - C1**2 / (2 * air.cp(c.T01))
            if T1 < 0.75 * c.T01:
                ok = False
                break
            rho1 = rho01 * (T1 / c.T01) ** (1 / (air.gamma(T1) - 1))
            C1 = c.mdot / (rho1 * A1 * 0.97)
        if not ok or C1 > 0.8 * a01:
            continue
        W1t = np.hypot(C1, omega * r1t)
        a1 = np.sqrt(air.gamma(T1) * air.R * T1)
        M1rel = W1t / a1
        if best is None or M1rel < best[0]:
            best = (M1rel, r1t, r1h, C1, T1, rho1, A1)
    M1rel, r1t, r1h, C1, T1, rho1, A1 = best
    beta1t = np.degrees(np.arctan2(omega * r1t, C1))

    # --- efficiency estimate
    Ns = omega * np.sqrt(c.mdot / rho01) / dh_s**0.75
    eta = eta_specific_speed(Ns) + 0.005 * min(c.beta2b, 40) / 10
    sigma = slip_wiesner(c.beta2b, c.Z)
    for _ in range(30):
        if "r2" in locals():
            sigma = slip_wiesner(c.beta2b, c.Z, r1t / r2)
        dh0 = dh_s / eta
        psi_euler = sigma * (1 - c.phi2 * np.tan(np.radians(c.beta2b)))
        U2 = np.sqrt(dh0 / (psi_euler * (1 + c.parasitic)))
        r2 = U2 / omega
        Re = U2 * 2 * r2 / NU_AIR
        eta_re = 1 - (1 - (eta_specific_speed(Ns) + 0.005 * min(c.beta2b, 40) / 10)) * (1e7 / Re) ** 0.1
        # exit state for blade height
        Cr2 = c.phi2 * U2
        Ctheta2 = psi_euler * U2
        T02 = c.T01 + dh0 / air.cp(0.5 * (c.T01 + c.T01 + dh0 / 1005))
        eta_imp = min(eta + 0.07, 0.95)
        p02 = c.p01 * air.pr_from_T(c.T01, c.T01 + eta_imp * (T02 - c.T01))
        C2 = np.hypot(Cr2, Ctheta2)
        T2 = T02 - C2**2 / (2 * air.cp(T02))
        p2 = p02 * (T2 / T02) ** (air.gamma(T2) / (air.gamma(T2) - 1))
        rho2 = p2 / (air.R * T2)
        b2 = c.mdot / (rho2 * Cr2 * 2 * np.pi * r2 * c.blockage2)
        d_clear = 0.35 * c.clearance / b2
        eta_new = eta_re - d_clear - c.build_penalty
        if c.eta_override is not None:
            eta_new = c.eta_override
        if not iterate or abs(eta_new - eta) < 1e-7:
            eta = eta_new
            break
        eta = eta_new
    T03 = c.T01 + (air.h(T03s) - air.h(c.T01)) / eta / air.cp(0.5 * (c.T01 + T03s))
    T03 = air.T_from_h(air.h(c.T01) + dh_s / eta, guess=T03)
    a2 = np.sqrt(air.gamma(T2) * air.R * T2)
    c.out = dict(
        omega=omega, Ns=Ns, eta=eta, eta_re=eta_re, d_eta_clear=d_clear, sigma=sigma,
        U2=U2, r2=r2, D2=2 * r2, b2=b2, r1t=r1t, r1h=r1h, D1t=2 * r1t, M1rel=M1rel, beta1t=beta1t, C1=C1,
        T1=T1, T02=T02, T03=T03, p03=c.p01 * c.pr, dh0=dh0, power=c.mdot * dh0, M2=C2 / a2,
        alpha2=np.degrees(np.arctan2(Ctheta2, Cr2)), Re=Re, Cr2=Cr2, Ctheta2=Ctheta2, T2=T2, p2=p2,
        r3=c.diffuser_ratio * r2, psi=dh0 / U2**2, phi_in=c.mdot / (rho01 * U2 * (2 * r2) ** 2),
        A1=A1, rho01=rho01,
    )
    return c.out


def impeller_stress(U2, material, T_c, K=0.60):
    """Peak von Mises stress estimate for a backswept impeller with a bore: sigma = K rho U2^2.

    K = 0.5-0.7 is typical of finite-element results for small backswept impellers; 0.60 is used.
    Burst-speed margin uses Robinson's average-hoop-stress criterion with the average hoop stress
    taken as half the peak (typical for an impeller with a small bore) and a 0.85 material
    utilization factor: N_burst / N = sqrt(0.85 UTS / (0.5 sigma_peak)).
    Returns (stress MPa, yield safety factor, burst-speed margin).
    """
    s = K * material.density * U2**2 / 1e6
    sf = material.YS(T_c) / s
    burst = np.sqrt(0.85 * material.UTS(T_c) / (0.5 * s))
    return s, sf, burst


class CompressorMap:
    """Semi-empirical map generated from the meanline design.

    Corrected speed n = N/N_design. For each speed, flow runs from surge to choke.
      * Euler work with slip:  psi(phi2) = sigma (1 - phi2 tan beta2b) (1 + parasitic)
      * efficiency: eta = eta_pk(n) [1 - k_inc (q/q_opt - 1)^2] - choke term
      * q_opt(n) = q_design * n^1.5 (inducer incidence-free flow scales with speed; the extra
        exponent is the vaned diffuser matching, which moves to lower flow as density ratio falls)
      * choke: q_choke(n) = q_opt(n) (1.25 + 0.4 (1 - n))   (wider speed lines at low speed)
      * surge: q_surge(n) = 0.66 q_opt(n) min(1, n)^0.6  (surge flow falls faster than the
        peak-efficiency flow at low pressure ratio, as on typical small turbocharger maps)
    The exponents and ratios are typical of published small turbocharger-class maps. They are
    assumptions, not measurements of this impeller.
    """

    def __init__(self, c: CompressorDesign):
        self.c = c
        o = c.out if c.out else design(c)
        self.o = o
        self.q_d = c.mdot          # corrected design flow (ISA inlet)
        self.eta_d = o["eta"]
        self.tanb = np.tan(np.radians(c.beta2b))
        self.sigma = o["sigma"]
        self.k_inc = 1.2
        self.q_exp = 1.5

    def q_opt(self, n):
        return self.q_d * n**self.q_exp

    def q_surge(self, n):
        return 0.66 * self.q_opt(n) * min(1.0, n) ** 0.6

    def q_choke(self, n):
        return self.q_opt(n) * (1.25 + 0.4 * max(0.0, 1 - n))

    def eta(self, q, n):
        e_pk = self.eta_d * (1 - 0.35 * (1 - n) ** 2) * (1 - 0.02 * max(0.0, n - 1) * 10)
        x = q / self.q_opt(n) - 1
        e = e_pk * (1 - self.k_inc * x**2)
        qc = self.q_choke(n)
        if q > 0.9 * qc:
            e -= 2.0 * ((q - 0.9 * qc) / (0.1 * qc)) ** 2 * 0.05
        return max(e, 0.2)

    def work(self, q, n):
        U2 = self.o["U2"] * n
        phi2 = self.c.phi2 * (q / self.q_d) / n     # density change with speed neglected
        psi = self.sigma * (1 - phi2 * self.tanb) * (1 + self.c.parasitic)
        return psi * U2**2

    def pr(self, q, n, T01=288.15):
        dh = self.work(q, n) * (T01 / 288.15)      # corrected work scales with T01
        dh_s = self.eta(q, n) * dh
        T2s = air.T_from_h(air.h(T01) + dh_s, guess=T01 + dh_s / 1005)
        return air.pr_from_T(T01, T2s)

    def speed_line(self, n, npts=40):
        q = np.linspace(self.q_surge(n), self.q_choke(n), npts)
        return q, np.array([self.pr(x, n) for x in q]), np.array([self.eta(x, n) for x in q])
