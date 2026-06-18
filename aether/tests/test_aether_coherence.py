"""
aether/tests/test_aether_coherence.py — Stage E: spectral observability over SPD.

Asserts: SPD substrate is informative while the Stiefel frame is degenerate (purity ≡ 1/k); purity &
coherence are exact deterministic fixed-point observables with correct ranges; entropy is float-only and
NOT wired into M̂_E (R1 step 4); the spectral series SEPARATE from {E,B,β} on a coupled trajectory
(R1 gate 5); and the spectral axis is pure telemetry (computed from state, never gating, never in a hash).
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import fixedpoint as F
import stiefel as ST
import spd as SP
import ghost as Gh
import field as FD
import coherence as CO
import regime as RG

S = F.SCALE
q = F.to_fp


class TestSubstrate(unittest.TestCase):
    def test_stiefel_frame_is_degenerate(self):
        # WWᵀ for an orthonormal 3×2 frame is a projector ⇒ purity pinned at 1/k = 0.5 (no information).
        import random
        random.seed(7)
        R = [[F.to_fp(random.randint(-1000, 1000), 1000) for _ in range(2)] for _ in range(3)]
        WWt = F.matmul(ST.gram_schmidt_integer(R), F.transpose(ST.gram_schmidt_integer(R)))
        self.assertEqual(round(CO.purity(WWt) / S, 3), 0.5)

    def test_spd_substrate_is_informative(self):
        # Different covariances ⇒ different purity (the substrate carries anisotropy).
        P1 = [[q(5, 1), 0, 0], [0, q(1, 1), 0], [0, 0, q(1, 1)]]      # anisotropic
        P2 = [[q(2, 1), 0, 0], [0, q(2, 1), 0], [0, 0, q(2, 1)]]      # isotropic
        self.assertNotEqual(CO.purity(P1), CO.purity(P2))


class TestExactObservables(unittest.TestCase):
    P = [[q(3, 1), q(1, 2), 0], [q(1, 2), q(2, 1), 0], [0, 0, q(1, 1)]]

    def test_purity_range_and_determinism(self):
        p = CO.purity(self.P)
        self.assertTrue(S // 3 <= p <= S)                  # [1/n, 1] for n=3
        self.assertEqual(p, CO.purity(self.P))             # deterministic

    def test_mixedness_complements_purity(self):
        self.assertEqual(CO.mixedness(self.P), S - CO.purity(self.P))

    def test_pinned_anchor(self):
        self.assertEqual(CO.purity(self.P), 1729917383)
        self.assertEqual(CO.coherence(self.P), 506166749)

    def test_diagonal_covariance_has_zero_coherence(self):
        self.assertEqual(CO.coherence([[q(2, 1), 0, 0], [0, q(3, 1), 0], [0, 0, q(1, 1)]]), 0)


class TestEntropyDeferred(unittest.TestCase):
    def test_entropy_is_float_and_not_in_meta_vector(self):
        P = [[q(3, 1), q(1, 2), 0], [q(1, 2), q(2, 1), 0], [0, 0, q(1, 1)]]
        self.assertIsInstance(CO.entropy_float(P), float)
        # R1 step 4: entropy is NOT among the exact spectral pressures wired into M̂_E.
        self.assertNotIn("entropy", CO.spectral_pressures(P))
        self.assertEqual(set(CO.spectral_pressures(P)), {"coherence", "mixedness"})


class TestIndependence(unittest.TestCase):
    def test_spectral_separates_from_existing_axes(self):
        # Coupled SPD flow: skew congruence (rotates basis) + symmetric drift (changes spectrum).
        A0 = [[0, q(3, 1), 0], [q(-3, 1), 0, 0], [0, 0, 0]]
        B0 = [[0, 0, q(2, 1)], [0, 0, 0], [q(-2, 1), 0, 0]]
        Dsym = [[F.to_fp(-1, 100), F.to_fp(2, 100), 0], [F.to_fp(2, 100), F.to_fp(-1, 100), 0], [0, 0, F.to_fp(1, 100)]]
        dt = q(1, 1000)
        P = [[q(3, 1), 0, 0], [0, q(2, 1), 0], [0, 0, q(1, 1)]]
        Sg = Gh.zeros_like(P)
        ser = {"coherence": [], "purity": [], "E": [], "B": [], "beta": []}
        prevA = None
        for t in range(4000):
            g = F.fp_mul(q(2, 1), P[0][1]) + F.fp_mul(q(1, 2), FD._tri(t, 300))
            A = F.add(A0, F.scalar(g, B0))
            M = F.add(F.identity(3), F.scalar(dt, A))
            P = SP.symmetrize(F.add(F.matmul(F.matmul(M, P), F.transpose(M)), F.scalar(dt, Dsym)))
            if t % 20 == 0:
                Sg = Gh.ema_matrix(Sg, Gh.ghost_residual(P, SP.project_spd(P)))
                ser["coherence"].append(CO.coherence(P)); ser["purity"].append(CO.purity(P))
                ser["E"].append(SP.spd_error(P)); ser["B"].append(Gh.backreaction(Sg, P))
                ser["beta"].append(FD._fro(FD._bracket(prevA, A)) if prevA is not None else 0)
            prevA = A
        verdict = CO.correlations(ser)
        self.assertEqual(verdict["verdict"], "separate")    # |corr| ≤ 0.5 ⇒ genuinely new axis
        self.assertLessEqual(verdict["max_abs_corr"], 0.5)


class TestPurityTelemetry(unittest.TestCase):
    def test_classify_E_has_spectral_axis(self):
        m = RG.meta_vector(10**14, F.SCALE * F.SCALE // (1 << 20), 1, 1, 0, 0, 1, 0, 0)
        mE = RG.extend_spectral(m, CO.coherence([[q(3,1),q(2,1),0],[q(2,1),q(2,1),0],[0,0,q(1,1)]]),
                                CO.mixedness([[q(3,1),q(2,1),0],[q(2,1),q(2,1),0],[0,0,q(1,1)]]))
        self.assertIn("spectral-limited", RG.classify_E(mE)["axes"])


class TestSpectralInvariance(unittest.TestCase):
    def test_purity_invariant_coherence_varies_under_rotation(self):
        # The quantum-info distinction, verified: purity is a unitary invariant (function of λ only);
        # coherence is basis-dependent. Rotate a fixed-spectrum covariance and check both.
        import random
        random.seed(0)
        P0 = [[q(4, 1), 0, 0], [0, q(2, 1), 0], [0, 0, q(1, 1)]]
        purities, coherences = [], []
        for _ in range(5):
            R = [[F.to_fp(random.randint(-1000, 1000), 1000) for _ in range(3)] for _ in range(3)]
            U = ST.gram_schmidt_integer(R)
            P = SP.symmetrize(F.matmul(F.matmul(U, P0), F.transpose(U)))
            purities.append(CO.purity(P)); coherences.append(CO.coherence(P))
        pur_spread = max(purities) - min(purities)
        coh_spread = max(coherences) - min(coherences)
        # purity is a spectral invariant UP TO fixed-point quantization (a few ulps); coherence is
        # basis-dependent and swings by orders of magnitude more.
        self.assertLess(pur_spread, S // 10000)            # purity ~invariant (quantization only)
        self.assertGreater(coh_spread, 100 * pur_spread)   # coherence varies far more (basis effect)

    def test_classify_E_separates_spectral_from_coherence(self):
        m = RG.meta_vector(1, 1, 0, 1, 0, 0, 1, 0, 0)
        mE = RG.extend_spectral(m, coherence=123, mixedness=456)
        axes = RG.classify_E(mE)["axes"]
        self.assertIn("spectral-limited", axes)
        self.assertIn("coherence-limited", axes)
        self.assertEqual(axes["spectral-limited"], 456)   # = mixedness (invariant)
        self.assertEqual(axes["coherence-limited"], 123)  # = coherence (basis)


if __name__ == "__main__":
    unittest.main(verbosity=2)