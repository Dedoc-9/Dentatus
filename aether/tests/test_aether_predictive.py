"""
aether/tests/test_aether_predictive.py — Stage E hardening: the held-out incremental-predictive-value gate.

Asserts: OLS recovers a known linear fit; the negative control (random feature) never earns a 'predictive'
verdict; the gate CAN fire when a genuinely predictive feature is present (positive control); and the
HONEST measured result — the spectral axes are 'descriptive' (NOT predictive) for forecasting future ERROR
(ghost ‖G‖). independent information ≠ predictive power.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import fixedpoint as F
import spd as SP
import ghost as Gh
import field as FD
import coherence as CO
import predictive as PR

S = F.SCALE
q = F.to_fp


def _coupled_series(steps=6000, stride=15):
    """A coupled SPD trajectory: skew congruence (rotates basis) + symmetric drift (changes spectrum).
    Returns aligned pressure columns + the spectral columns + the ghost-norm series."""
    A0 = [[0, q(3, 1), 0], [q(-3, 1), 0, 0], [0, 0, 0]]
    B0 = [[0, 0, q(2, 1)], [0, 0, 0], [q(-2, 1), 0, 0]]
    Dsym = [[F.to_fp(-1, 100), F.to_fp(2, 100), 0], [F.to_fp(2, 100), F.to_fp(-1, 100), 0], [0, 0, F.to_fp(1, 100)]]
    dt = q(1, 1000)
    P = [[q(3, 1), 0, 0], [0, q(2, 1), 0], [0, 0, q(1, 1)]]
    Sg = Gh.zeros_like(P)
    prevA = None
    E, Bv, Be, Cc, Mx, Gn = [], [], [], [], [], []
    for t in range(steps):
        g = F.fp_mul(q(2, 1), P[0][1]) + F.fp_mul(q(1, 2), FD._tri(t, 300))
        A = F.add(A0, F.scalar(g, B0))
        M = F.add(F.identity(3), F.scalar(dt, A))
        P = SP.symmetrize(F.add(F.matmul(F.matmul(M, P), F.transpose(M)), F.scalar(dt, Dsym)))
        if t % stride == 0:
            Gm = Gh.ghost_residual(P, SP.project_spd(P)); Sg = Gh.ema_matrix(Sg, Gm)
            E.append(SP.spd_error(P) / (S * S)); Bv.append(Gh.backreaction(Sg, P) / S)
            Be.append((FD._fro(FD._bracket(prevA, A)) if prevA is not None else 0) / S)
            Cc.append(CO.coherence(P) / S); Mx.append(CO.mixedness(P) / S); Gn.append(Gh.frob_norm(Gm) / S)
        prevA = A
    return E, Bv, Be, Cc, Mx, Gn


class TestRegression(unittest.TestCase):
    def test_ols_recovers_linear(self):
        x1 = [i * 0.1 for i in range(200)]
        x2 = [(i % 7) * 0.5 for i in range(200)]
        y = [2 * a - 3 * b for a, b in zip(x1, x2)]
        self.assertGreater(PR._held_out_r2([list(r) for r in zip(x1, x2)], y), 0.999)


class TestGateIntegrity(unittest.TestCase):
    def test_negative_control_never_predictive(self):
        # Baseline of real pressures; the augment IS a fresh random column ⇒ must be 'descriptive'.
        import random
        rng = random.Random(2)
        n = 300
        b1 = [rng.random() for _ in range(n)]
        target = [rng.random() for _ in range(n)]
        r = PR.incremental_value([b1], [[rng.random() for _ in range(n)]], target)
        self.assertEqual(r["verdict"], "descriptive")

    def test_gate_can_fire_positive_control(self):
        # If the augment column genuinely carries the target (a lag of it), the gate MUST say 'predictive'.
        E, Bv, Be, Cc, Mx, Gn = _coupled_series()
        H = 4
        n = len(Mx) - H
        target = [Mx[i + H] for i in range(n)]            # future mixedness
        # baseline = error pressures (blind to spectral); augment = current mixedness (its own lag)
        r = PR.incremental_value([E[:n], Bv[:n], Be[:n]], [Mx[:n]], target)
        self.assertEqual(r["verdict"], "predictive")      # the gate CAN detect real signal
        self.assertGreater(r["delta_aug"], 10 * max(r["delta_ctl"], 0.0))


class TestHonestVerdict(unittest.TestCase):
    def test_spectral_not_predictive_for_future_error(self):
        # The measured Stage-E result: spectral adds NO incremental forecasting of future ghost ‖G‖.
        E, Bv, Be, Cc, Mx, Gn = _coupled_series()
        H = 4
        n = len(Gn) - H
        target = [Gn[i + H] for i in range(n)]
        r = PR.incremental_value([E[:n], Bv[:n], Be[:n]], [Cc[:n], Mx[:n]], target)
        self.assertEqual(r["verdict"], "descriptive")     # independent (gate 5) but NOT predictive
        self.assertLess(r["delta_aug"], PR.DELTA_FLOOR)   # ΔR² below the predictive floor


if __name__ == "__main__":
    unittest.main(verbosity=2)
