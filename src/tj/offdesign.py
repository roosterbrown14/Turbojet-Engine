"""Off-design matching of the fixed-geometry engine (equilibrium running line).

At each shaft speed three unknowns (corrected compressor flow, turbine inlet temperature,
turbine pressure ratio) are solved from three conditions:
  1. turbine flow capacity, Stodola ellipse law  m4 sqrt(T4)/p4 = K sqrt(1 - (p5/p4)^2)
  2. power balance  m4 dh_t eta_m = mdot dh_c
  3. fixed convergent nozzle area A9 passes m4 at (T5, p5)
The compressor follows the semi-empirical map in compressor.CompressorMap. Turbine efficiency
falls off quadratically with blade-speed ratio U/C0 away from its design value.
"""
import numpy as np
from scipy.optimize import least_squares

from . import cycle as cy
from .compressor import CompressorMap
from .gas import air, burn, products
from .fuels import FUELS


class OffDesign:
    def __init__(self, res, A9_scale=1.0):
        self.res = res
        s = res.spec
        self.s = s
        from .compressor import CompressorDesign, design
        cd = CompressorDesign(mdot=s.mdot, pr=s.pr, rpm=s.rpm, T01=288.15, p01=101325 * 0.99, beta2b=s.beta2b, Z=s.Z,
                              hub_tip=s.hub_tip, clearance=s.clear_c, build_penalty=s.build_penalty)
        design(cd)
        self.map = CompressorMap(cd)
        c = res.cyc
        self.A9 = c["A9"] * A9_scale
        p4, T4, p5 = c["p04"], s.TIT, c["p05"]
        self.K = c["m4"] * np.sqrt(T4) / p4 / np.sqrt(1 - (p5 / p4) ** 2)
        self.eta_t_d = res.turb["eta"]
        g = c["gas"]
        dh_is = g.h(T4) - g.h(g.T_isentropic(T4, p5 / p4))
        self.vr_d = res.turb["U"] / np.sqrt(2 * dh_is)
        self.leak = 0.02
        self.eta_m = 0.98

    def eta_t(self, vr):
        return max(0.3, self.eta_t_d * (1 - 1.2 * (vr / self.vr_d - 1) ** 2))

    def point(self, n, T0=288.15, p0=101325.0, V0=0.0, guess=None):
        s = self.s
        theta = T0 / 288.15
        delta = p0 / 101325.0
        N = n * s.rpm
        nc = n / np.sqrt(theta)                    # corrected speed fraction
        T01 = T0 + V0**2 / 2010
        p01 = p0 * air.pr_from_T(T0, T01) * 0.99

        def unpack(x):
            qc, T4, prt = x
            return qc, T4, prt

        def resid(x):
            qc, T4, prt = unpack(x)
            prc = self.map.pr(qc, nc)
            eta_c = self.map.eta(qc, nc)
            mdot = qc * delta / np.sqrt(theta)
            T03s = air.T_isentropic(T01, prc)
            wc = (air.h(T03s) - air.h(T01)) / eta_c
            T03 = air.T_from_h(air.h(T01) + wc, guess=T03s + 20)
            p03 = p01 * prc
            p04 = p03 * (1 - s.dp_comb)
            far = burn(T03, T4, s.fuel, s.eta_b) if T4 > T03 + 1 else 1e-6
            mc = mdot * (1 - self.leak)
            m4 = mc * (1 + far)
            g = products(far, s.fuel)
            p05 = p04 / prt
            T5s = g.T_isentropic(T4, 1 / prt)
            U = self.res.turb["U"] * n
            vr = U / np.sqrt(2 * max(g.h(T4) - g.h(T5s), 1.0))
            et = self.eta_t(vr)
            wt = et * (g.h(T4) - g.h(T5s))
            T05 = g.T_from_h(g.h(T4) - wt, guess=T4 - wt / 1150)
            r1 = m4 * np.sqrt(T4) / p04 / (self.K * np.sqrt(max(1 - (1 / prt) ** 2, 1e-9))) - 1
            r2 = m4 * wt * self.eta_m / (mdot * wc) - 1
            V9, A9, *_ = cy.nozzle(g, m4, T05, max(p05 * 0.98, p0 * 1.0005), p0, 0.97)
            r3 = A9 / self.A9 - 1 + 50 * max(0.0, p0 * 1.0005 - p05 * 0.98) / p0
            return [r1, r2, r3], dict(qc=qc, mdot=mdot, prc=prc, eta_c=eta_c, T03=T03, p03=p03, T4=T4, far=far,
                                      m4=m4, prt=prt, eta_t=et, T05=T05, p05=p05, g=g, vr=vr)

        x0 = guess if guess is not None else [self.map.q_opt(nc), self.s.TIT, self.res.cyc["pr_t"]]
        lo = [0.3 * self.map.q_opt(nc), 450.0, 1.005]
        hi = [1.6 * self.map.q_d, 1800.0, 4.0]
        x0 = np.clip(x0, np.array(lo) * 1.0001, np.array(hi) * 0.9999)
        sol = least_squares(lambda x: resid(x)[0], x0, bounds=(lo, hi), xtol=1e-12, ftol=1e-12, gtol=1e-12,
                            x_scale=[0.05, 100.0, 0.2])
        x = sol.x
        r, d = resid(x)
        ier = 1 if sol.success else 0
        V9, A9, p9, M9, choked, T9 = cy.nozzle(d["g"], d["m4"], d["T05"], max(d["p05"] * 0.98, p0 * 1.0005), p0, 0.97)
        F = d["m4"] * V9 + A9 * (p9 - p0) - d["mdot"] * V0
        mf = d["far"] * d["mdot"] * (1 - self.leak)
        q = d["qc"]
        surge_margin = (q / self.map.q_surge(nc) - 1)
        d.pop("g")
        d.update(n=n, rpm=N, thrust=F, mdot_fuel=mf, fuel_l_min=mf / FUELS[s.fuel].density * 6e4,
                 tsfc=mf / F * 1e6 if F > 0 else np.nan, EGT_C=d["T05"] - 273.15, TIT_C=d["T4"] - 273.15,
                 converged=bool(max(abs(np.array(r))) < 1e-5), surge_margin=surge_margin, V9=V9, x=x)
        return d

    def running_line(self, n_values, **kw):
        out = []
        guess = None
        for n in sorted(n_values, reverse=True):
            p = self.point(n, guess=guess, **kw)
            guess = p["x"]
            out.append(p)
        return out[::-1]
