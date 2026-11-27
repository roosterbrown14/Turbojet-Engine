"""Finite-element rotordynamics of the shaft, wheels and bearings.

Euler-Bernoulli beam elements (consistent mass), rigid discs with mass, diametral and polar
inertia at nodes, isotropic linear bearing springs. Using the complex whirl coordinate
r = y + i z the gyroscopic coupling reduces to a real quadratic eigenproblem in the whirl
frequency omega at shaft speed Omega:

    (K - omega^2 M + omega Omega P) R = 0      P = polar inertias on the tilt DOFs

Positive roots are forward whirl, negative roots backward whirl. Critical speeds are where a
forward-whirl frequency equals the running speed (synchronous excitation by unbalance).
"""
from dataclasses import dataclass, field

import numpy as np
from scipy.linalg import eig


@dataclass
class Disc:
    x: float          # axial position, m
    m: float          # kg
    Id: float         # diametral inertia, kg m^2
    Ip: float         # polar inertia, kg m^2
    name: str = ""


@dataclass
class Rotor:
    x_nodes: np.ndarray            # node positions, m
    d_elem: np.ndarray             # outer diameter of each element, m
    E: float = 200e9
    rho: float = 7800.0
    discs: list = field(default_factory=list)
    bearings: list = field(default_factory=list)   # (x, k N/m)
    d_bore: np.ndarray | None = None

    def node_of(self, x):
        return int(np.argmin(np.abs(self.x_nodes - x)))

    def matrices(self):
        n = len(self.x_nodes)
        K = np.zeros((2 * n, 2 * n))
        M = np.zeros_like(K)
        P = np.zeros_like(K)
        for e in range(n - 1):
            L = self.x_nodes[e + 1] - self.x_nodes[e]
            do = self.d_elem[e]
            di = 0.0 if self.d_bore is None else self.d_bore[e]
            A = np.pi / 4 * (do**2 - di**2)
            I = np.pi / 64 * (do**4 - di**4)
            k = self.E * I / L**3 * np.array([[12, 6 * L, -12, 6 * L], [6 * L, 4 * L**2, -6 * L, 2 * L**2],
                                              [-12, -6 * L, 12, -6 * L], [6 * L, 2 * L**2, -6 * L, 4 * L**2]])
            m = self.rho * A * L / 420 * np.array([[156, 22 * L, 54, -13 * L], [22 * L, 4 * L**2, 13 * L, -3 * L**2],
                                                    [54, 13 * L, 156, -22 * L], [-13 * L, -3 * L**2, -22 * L, 4 * L**2]])
            idx = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]
            K[np.ix_(idx, idx)] += k
            M[np.ix_(idx, idx)] += m
            # shaft polar inertia lumped (small)
            ip = self.rho * I * 2 * L / 2
            P[2 * e + 1, 2 * e + 1] += ip
            P[2 * e + 3, 2 * e + 3] += ip
        for d in self.discs:
            j = self.node_of(d.x)
            M[2 * j, 2 * j] += d.m
            M[2 * j + 1, 2 * j + 1] += d.Id
            P[2 * j + 1, 2 * j + 1] += d.Ip
        for xb, kb in self.bearings:
            j = self.node_of(xb)
            K[2 * j, 2 * j] += kb
        return K, M, P

    def whirl(self, Omega, nmodes=4):
        """Whirl frequencies (rad/s) at shaft speed Omega (rad/s): (forward, backward)."""
        K, M, P = self.matrices()
        n = K.shape[0]
        Z, I = np.zeros((n, n)), np.eye(n)
        A = np.block([[Z, I], [K, Omega * P]])
        B = np.block([[I, Z], [Z, M]])
        w, v = eig(A, B)
        w = w[np.isfinite(w)]
        w = w[np.abs(w.imag) < 1e-6 * np.maximum(1, np.abs(w.real))].real
        fw = np.sort(w[w > 1e-3])[:nmodes]
        bw = np.sort(-w[w < -1e-3])[:nmodes]
        return fw, bw

    def modes(self, Omega=0.0, nmodes=3):
        K, M, P = self.matrices()
        n = K.shape[0]
        Z, I = np.zeros((n, n)), np.eye(n)
        w, v = eig(np.block([[Z, I], [K, Omega * P]]), np.block([[I, Z], [Z, M]]))
        keep = np.isfinite(w) & (np.abs(w.imag) < 1e-6 * np.maximum(1, np.abs(w.real))) & (w.real > 1e-3)
        w, v = w[keep].real, v[:, keep].real
        order = np.argsort(w)[:nmodes]
        shapes = []
        for i in order:
            y = v[:n:2, i]
            shapes.append(y / np.max(np.abs(y)))
        return w[order], shapes

    def critical_speeds(self, Omega_max, n=4):
        """Synchronous forward critical speeds (rad/s) below Omega_max.

        Setting omega = Omega in the whirl equation gives the linear problem
        K R = Omega^2 (M - P) R, solved directly.
        """
        K, M, P = self.matrices()
        w2 = eig(K, M - P, right=False)
        w2 = w2[np.isfinite(w2)]
        w2 = w2[(np.abs(w2.imag) < 1e-6 * np.maximum(1, np.abs(w2.real))) & (w2.real > 0)].real
        crit = np.sort(np.sqrt(w2))
        return [float(c) for c in crit[crit <= Omega_max]][:n]


def disc_props(m, r_o, length, r_i=0.0):
    """Inertias of a solid cylinder approximation of a wheel."""
    Ip = 0.5 * m * (r_o**2 + r_i**2)
    Id = 0.25 * m * (r_o**2 + r_i**2) + m * length**2 / 12
    return Ip, Id
