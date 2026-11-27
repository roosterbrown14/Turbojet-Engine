"""Automated verification tests (run on every push by GitHub Actions)."""
from dataclasses import replace

import numpy as np
import pytest

from tj import cycle as cy
from tj import rotor as rt
from tj import turbine as tb
from tj.compressor import CompressorMap, CompressorDesign, design, slip_wiesner
from tj.engine import EngineSpec, build, make_rotor
from tj.fuels import FUELS
from tj.gas import air, burn, flame_temperature, products
from tj.materials import MATERIALS
from tj.offdesign import OffDesign


@pytest.fixture(scope="module")
def base():
    return build(EngineSpec())


def test_air_cp_matches_janaf():
    for T, ref in {300: 1005, 500: 1029, 1000: 1142, 1500: 1216}.items():
        assert abs(air.cp(T) / ref - 1) < 0.005


def test_isentropic_close_to_perfect_gas_at_low_temperature():
    T2 = air.T_isentropic(288.15, 2.0)
    assert abs(T2 - 288.15 * 2 ** (0.4 / 1.4)) < 1.0


def test_burn_and_flame_temperature_are_inverse():
    f = burn(420.0, 1100.0)
    assert abs(flame_temperature(420.0, f) - 1100.0) < 0.5


def test_stoichiometric_far_kerosene():
    assert 0.066 < FUELS["Jet A-1"].far_stoich < 0.070


def test_products_reject_rich_mixture():
    with pytest.raises(ValueError):
        products(0.08)


def test_first_law_closure_ideal_engine():
    ci = cy.CycleInputs(pr_c=2.0, eta_c=1, eta_t=1, eta_b=1, eta_m=1, dp_comb=0, pi_inlet=1, pi_jetpipe=1, leak=0,
                        cv_nozzle=1, TIT=1200.0)
    r = cy.run(ci)
    f, g = r["far"], r["gas"]
    ke = (air.h(ci.T0) + f * FUELS[ci.fuel].LHV - (1 + f) * g.h(r["stations"][9]["T"])) / (1 + f)
    assert abs(r["V9"] ** 2 / 2 / ke - 1) < 1e-6


def test_design_point_in_expected_class(base):
    assert 90 < base.thrust < 130
    assert 35 < base.cyc["tsfc_g_per_kNs"] < 55
    assert 0.70 < base.comp["eta"] < 0.80
    assert 0.75 < base.turb["eta"] < 0.85


def test_turbine_work_balances_compressor(base):
    c = base.cyc
    assert abs(c["m4"] * c["w_t"] * 0.98 / c["P_comp"] - 1) < 1e-9


def test_wiesner_slip_limits():
    assert slip_wiesner(0, 1e6) == pytest.approx(1.0, abs=1e-3)
    assert slip_wiesner(30, 14) > slip_wiesner(30, 8)


def test_compressor_map_passes_through_design_point():
    cd = CompressorDesign()
    design(cd)
    m = CompressorMap(cd)
    assert abs(m.pr(cd.mdot, 1.0) / cd.pr - 1) < 0.02


def test_beam_frequency_matches_exact():
    L, d = 0.2, 0.01
    R = rt.Rotor(np.linspace(0, L, 41), np.full(40, d), bearings=[(0, 1e13), (L, 1e13)])
    w, _ = R.modes(0.0, 1)
    A, I = np.pi * d**2 / 4, np.pi * d**4 / 64
    exact = (np.pi / L) ** 2 * np.sqrt(200e9 * I / (7800 * A))
    assert abs(w[0] / exact - 1) < 1e-3


def test_rotor_bending_critical_above_max_speed(base):
    R, _ = make_rotor(base)
    crit = R.critical_speeds(3 * base.spec.rpm * 2 * np.pi / 60)
    bending = crit[2] * 60 / (2 * np.pi)
    assert bending > 1.2 * base.spec.rpm
    assert crit[1] * 60 / (2 * np.pi) < 0.45 * base.spec.rpm      # rigid-body modes below idle (soft mounts)


def test_disc_average_hoop_stress():
    rpm, b, rho = 100_000, 0.03, 8000
    _, _, st, avg = tb.disc_stress(rpm, 1e-4, b, rho, 0.3, 0.0)
    w = rpm * 2 * np.pi / 60
    assert abs(avg / (rho * w**2 * b**2 / 3e6) - 1) < 0.01


def test_larson_miller_life_monotonic():
    m = MATERIALS["IN713C"]
    assert m.rupture_life(700, 200) > m.rupture_life(800, 200) > m.rupture_life(900, 200)
    assert m.rupture_life(800, 150) > m.rupture_life(800, 300)


def test_offdesign_reproduces_design_point(base):
    p = OffDesign(base).point(1.0)
    assert p["converged"]
    assert abs(p["thrust"] / base.thrust - 1) < 1e-4


def test_thrust_falls_with_speed(base):
    od = OffDesign(base)
    pts = od.running_line([0.7, 0.85, 1.0])
    F = [p["thrust"] for p in pts]
    assert F[0] < F[1] < F[2]


def test_hot_day_reduces_thrust(base):
    od = OffDesign(base)
    assert od.point(1.0, T0=308.15)["thrust"] < od.point(1.0, T0=268.15)["thrust"]


def test_published_engine_benchmark():
    r = build(replace(EngineSpec(), mdot=0.150, pr=1.90, TIT=953.0, rpm=100_000))
    assert abs(r.thrust / 40.0 - 1) < 0.15
    assert abs(r.cyc["tsfc_g_per_kNs"] / 62.5 - 1) < 0.15
