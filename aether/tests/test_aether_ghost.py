"""
aether/tests/test_aether_ghost.py — Stage B dual ghost channel.

Verifies: ghost closure Gₜ=Zₜ−Π_W(Zₜ); fixed-point EMA recurrence & determinism; OBSERVABLE PURITY
(measurement never perturbs the forward Z path / legacy hash); η_CLT null under zero drift; structural
identity includes S (ghost in Hₜ); a pinned structural-hash regression anchor.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import fixedpoint as F
import stiefel as S
import ghost as Gh
import evolve as E

GEN = [[0, F.to_fp(1, 2), 0], [F.to_fp(-1, 2), 0, F.to_fp(1, 3)], [0, F.to_fp(-1, 3), 0]]
DT = F.to_fp(1, 1000)


class TestGhostClosure(unittest.TestCase):
    def test_residual_is_exact_difference(self):
        Z = E.lie_step(F.identity(3), GEN, F.to_fp(1, 100))
        Wp = S.gram_schmidt_integer(Z)
        G = Gh.ghost_residual(Z, Wp)
        # Gₜ = Zₜ − Π_W(Zₜ), entrywise exact
        self.assertEqual(G, F.sub(Z, Wp))

    def test_on_manifold_has_zero_ghost(self):
        # An exactly-orthonormal frame projects to itself ⇒ G = 0.
        I = F.identity(3)
        G = Gh.ghost_residual(I, S.gram_schmidt_integer(I))
        self.assertTrue(all(v == 0 for row in G for v in row))
        self.assertEqual(Gh.frob_norm(G), 0)


class TestEMA(unittest.TestCase):
    def test_recurrence_matches_manual(self):
        G = [[F.to_fp(1, 1), 0, 0], [0, F.to_fp(2, 1), 0], [0, 0, F.to_fp(3, 1)]]
        S0 = Gh.zeros_like(G)
        a = Gh.ALPHA_DEFAULT
        S1 = Gh.ema_matrix(S0, G, a)
        # S1 = α·0 + (1−α)·G, computed with the same symmetric fp_mul
        manual = F.scalar(F.SCALE - a, G)
        self.assertEqual(S1, manual)

    def test_ema_deterministic(self):
        G = E.lie_step(F.identity(3), GEN, DT)
        S0 = Gh.zeros_like(G)
        self.assertEqual(Gh.ema_matrix(S0, G), Gh.ema_matrix(S0, G))

    def test_ema_sign_symmetry(self):
        # The dual space inherits fp_mul's sign-symmetry: EMA(−G) = −EMA(G) from S0=0.
        G = [[F.to_fp(7, 3), F.to_fp(-5, 2), 0], [0, F.to_fp(1, 9), 0], [0, 0, F.to_fp(-4, 7)]]
        S0 = Gh.zeros_like(G)
        negG = [[-v for v in row] for row in G]
        pos = Gh.ema_matrix(S0, G)
        neg = Gh.ema_matrix(S0, negG)
        self.assertEqual(neg, [[-v for v in row] for row in pos])


class TestObservablePurity(unittest.TestCase):
    def test_measurement_never_perturbs_forward_path(self):
        # The legacy W-only identity is identical regardless of ghost sampling cadence:
        # measurement runs Π_W but never writes back to Z.
        dense = E.evolve_audited(F.identity(3), GEN, DT, 20000, audit_every=500, measure_every=1)
        sparse = E.evolve_audited(F.identity(3), GEN, DT, 20000, audit_every=500, measure_every=5000)
        self.assertEqual(dense["final_hash"], sparse["final_hash"])
        self.assertEqual(dense["W"], sparse["W"])
        self.assertEqual(dense["retractions"], sparse["retractions"])

    def test_ghost_in_structural_identity(self):
        # Same μ,Z,W but different S ⇒ different Hₜ (the ghost is first-class state).
        Z = E.lie_step(F.identity(3), GEN, DT)
        Wp = S.gram_schmidt_integer(Z)
        S1 = Gh.zeros_like(Z)
        S2 = Gh.ema_matrix(S1, Gh.ghost_residual(Z, Wp))
        h1 = Gh.structural_hash(GEN, Z, S1, Wp)
        h2 = Gh.structural_hash(GEN, Z, S2, Wp)
        self.assertNotEqual(h1, h2)
        self.assertEqual(h1, Gh.structural_hash(GEN, Z, S1, Wp))   # deterministic

    def test_structural_differs_from_legacy(self):
        r = E.evolve_audited(F.identity(3), GEN, DT, 5000, audit_every=500)
        self.assertNotEqual(r["final_hash"], r["structural_hash"])


class TestCLTNull(unittest.TestCase):
    def test_zero_generator_zero_drift(self):
        # No generator ⇒ no motion ⇒ G=0 every step ⇒ S=0, B(t)=0, η_CLT=0.
        zero = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        r = E.evolve_audited(F.identity(3), zero, DT, 5000, audit_every=500, measure_every=1)
        self.assertTrue(all(v == 0 for row in r["S"] for v in row))
        self.assertEqual(r["B_t"], 0)
        self.assertEqual(r["eta_clt"]["eta"], 0)

    def test_clt_eta_counts_samples(self):
        r = E.evolve_audited(F.identity(3), GEN, DT, 10000, audit_every=500, measure_every=1)
        self.assertEqual(r["eta_clt"]["N"], r["ghost_samples"])
        self.assertEqual(r["ghost_samples"], 10000)


class TestDeterminismAndAnchor(unittest.TestCase):
    def test_structural_hash_deterministic(self):
        a = E.evolve_audited(F.identity(3), GEN, DT, 20000, audit_every=500, measure_every=1)
        b = E.evolve_audited(F.identity(3), GEN, DT, 20000, audit_every=500, measure_every=1)
        self.assertEqual(a["structural_hash"], b["structural_hash"])

    def test_pinned_structural_anchor(self):
        # Regression anchor for the Stage-B identity (the deliberate Hₜ pin).
        r = E.evolve_audited(F.identity(3), GEN, DT, 20000, audit_every=500, measure_every=1)
        self.assertEqual(r["structural_hash"],
                         "00b152f365325d3bf01f183f57935d4789851b57f6e09cd5f6680b27a0b52a23")
        self.assertEqual(r["protocol_version"], "aether/2")


if __name__ == "__main__":
    unittest.main(verbosity=2)
