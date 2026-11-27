"""Meanline model of a single-stage axial turbine (nozzle guide vanes + rotor), uncooled.

Velocity triangles at the mean radius assume constant axial velocity, constant mean radius
and zero exit swirl, so the stage is fixed by the flow coefficient phi = Cx/U and the loading
coefficient psi = dh0/U^2 (reaction R = 1 - psi/2).

Losses: Soderberg's correlation as given by Dixon & Hall (zeta = 0.04 [1 + 1.5 (eps/100)^2],
eps = blade deflection in deg) with the aspect-ratio and Reynolds-number corrections, plus a
tip-clearance penalty delta eta = 2.0 * clearance / blade height for an unshrouded rotor.
Plotting eta over (phi, psi) reproduces the shape of the Smith (1965) chart.

Stresses: blade root centrifugal stress sigma = K rho omega^2 A / (2 pi) with taper factor
K = 0.6; disc stress from the elastic rotating-disc solution (uniform thickness, with bore)
loaded by the blade pull at the rim.
"""
from dataclasses import dataclass, field

import numpy as np

from .gas import products


@dataclass
class TurbineDesign:
    work: float = 1.2e5           # J/kg of gas (specific work required)
    mdot: float = 0.25            # kg/s of gas
    T04: float = 1100.0
    p04: float = 2.6e5
    rpm: float = 110_000
    far: float = 0.02
    phi: float = 0.55
    psi: float | None = None      # None: set from the mean radius below
    r_mean: float | None = 0.0285  # m (used when psi is None)
    aspect: float = 1.0           # blade height / axial chord
    clearance: float = 0.30e-3    # m
    Zr: int = 27                  # rotor blades
    Zn: int = 19                  # NGVs
    taper_K: float = 0.6
    out: dict = field(default_factory=dict)


def soderberg(eps_deg, aspect, Re):
    z = 0.04 * (1 + 1.5 * (eps_deg / 100) ** 2)
    z = (1 + z) * (0.975 + 0.075 / aspect) - 1
    return z * (1e5 / Re) ** 0.25


def triangles(phi, psi):
    """Mean-line flow angles (deg) for zero exit swirl."""
    a2 = np.degrees(np.arctan(psi / phi))
    b2 = np.degrees(np.arctan((psi - 1) / phi))
    b3 = np.degrees(np.arctan(-1 / phi))
    return a2, b2, b3


def eta_stage(phi, psi, aspect=1.0, Re=2e5, clearance_ratio=0.0):
    """Total-to-total efficiency from Soderberg losses (Dixon & Hall eq. for a repeating stage)."""
    a2, b2, b3 = triangles(phi, psi)
    zN = soderberg(a2, aspect, Re)
    zR = soderberg(b2 - b3, aspect, Re)
    # kinetic energies per U^2
    C2 = phi**2 + psi**2
    W3 = phi**2 + 1.0
    eta = 1.0 / (1.0 + (zN * C2 + zR * W3) / (2 * psi))
    return eta - 2.0 * clearance_ratio


def design(t: TurbineDesign):
    g = products(t.far)
    omega = t.rpm * 2 * np.pi / 60
    if t.psi is None:
        U = omega * t.r_mean
        psi = t.work / U**2
    else:
        psi = t.psi
        U = np.sqrt(t.work / psi)
    rm = U / omega
    Cx = t.phi * U
    a2, b2, b3 = triangles(t.phi, psi)
    Ct2 = psi * U
    C2 = np.hypot(Cx, Ct2)
    W2 = np.hypot(Cx, Ct2 - U)
    W3 = np.hypot(Cx, U)
    cp = g.cp(t.T04 - 0.5 * t.work / 1150)
    gam = g.gamma(t.T04)
    T2 = t.T04 - C2**2 / (2 * cp)
    M2 = C2 / np.sqrt(gam * g.R * T2)
    # first pass efficiency for the exit state
    eta = 0.8
    for _ in range(20):
        T05 = g.T_from_h(g.h(t.T04) - t.work, guess=t.T04 - t.work / cp)
        T05s = g.T_from_h(g.h(t.T04) - t.work / eta, guess=T05 - 20)
        pr_t = 1 / g.pr_from_T(T05s, t.T04)
        p05 = t.p04 * pr_t
        T3 = T05 - Cx**2 / (2 * cp)
        p3 = p05 * (T3 / T05) ** (gam / (gam - 1))
        rho3 = p3 / (g.R * T3)
        h = t.mdot / (rho3 * Cx * 2 * np.pi * rm)
        chord = h / t.aspect
        mu = 4.5e-5 * (T2 / 1100) ** 0.7
        Re = (p3 / (g.R * T3)) * W3 * chord / mu
        e = eta_stage(t.phi, psi, t.aspect, Re, t.clearance / h)
        if abs(e - eta) < 1e-7:
            eta = e
            break
        eta = e
    # NGV throat: flow capacity and exit Mach
    T2s = T2
    rho2 = t.p04 * (T2s / t.T04) ** (gam / (gam - 1)) / (g.R * T2s)
    rt, rh = rm + h / 2, rm - h / 2
    T0rel = T2 + W2**2 / (2 * cp)
    out = dict(U=U, rm=rm, Dm=2 * rm, rt=rt, rh=rh, Dt=2 * rt, h=h, chord=chord, psi=psi, phi=t.phi,
               reaction=1 - psi / 2, alpha2=a2, beta2=b2, beta3=b3, C2=C2, W2=W2, W3=W3, M2=M2, Cx=Cx,
               eta=eta, T05=T05, p05=p05, pr=t.p04 / p05, T0rel=T0rel, Re=Re, rho2=rho2, omega=omega,
               hub_tip=rh / rt, capacity=t.mdot * np.sqrt(t.T04) / t.p04)
    t.out = out
    return out


def blade_root_stress(t: TurbineDesign, material):
    o = t.out
    A = np.pi * (o["rt"] ** 2 - o["rh"] ** 2)
    return t.taper_K * material.density * o["omega"] ** 2 * A / (2 * np.pi) / 1e6


def disc_stress(rpm, r_bore, r_rim, rho, nu, rim_load_mpa, n=200):
    """Radial and hoop stress (MPa) in a uniform rotating disc with a bore and rim pressure.

    Classical solution (Timoshenko & Goodier). rim_load_mpa is the radial tensile stress at the
    rim from the blades. Returns r, sigma_r, sigma_theta, average hoop stress.
    """
    w = rpm * 2 * np.pi / 60
    a, b = r_bore, r_rim
    r = np.linspace(a, b, n)
    k = (3 + nu) / 8 * rho * w**2
    sr = k * (a**2 + b**2 - a**2 * b**2 / r**2 - r**2)
    st = k * (a**2 + b**2 + a**2 * b**2 / r**2 - (1 + 3 * nu) / (3 + nu) * r**2)
    P = rim_load_mpa * 1e6
    sr += P * b**2 / (b**2 - a**2) * (1 - a**2 / r**2)
    st += P * b**2 / (b**2 - a**2) * (1 + a**2 / r**2)
    avg = np.trapezoid(st, r) / (b - a)
    return r, sr / 1e6, st / 1e6, avg / 1e6


def rim_load(t: TurbineDesign, material, r_rim, disc_thickness):
    """Radial stress at the disc rim from the blades' centrifugal pull."""
    o = t.out
    blade_vol = o["h"] * o["chord"] * 0.08 * o["chord"] * 0.75   # aerofoil area ~ 0.06-0.1 c^2, taper
    F = t.Zr * material.density * blade_vol * o["omega"] ** 2 * o["rm"]
    return F / (2 * np.pi * r_rim * disc_thickness) / 1e6
