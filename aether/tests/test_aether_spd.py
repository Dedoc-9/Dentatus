"""
aether/tests/test_aether_spd.py — Stage C: SPD cone (log-Cholesky) + E-driven adaptive cadence.

Verifies: fixed-point Cholesky correctness; the EXACT Sylvester positivity gate; Π_SPD retraction
repairs a drifted/indefinite matrix; the adaptive cadence is driven only by the gate margin (ghost
measurement never changes the committed forward path); the cone is held under strong drift; determinism
+ a pinned structural anchor.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import fixedpoint as F
import spd as SP
import evolve as E

q = lambda x: F.to_fp(x, 1)


class TestCholesky(unittest.TestCase):
    def test_factor_matches_real(self):
        P = [[q(4), q(2)], [q(2), q(3)]]            # real L = [[2,0],[1,sqrt2]]
        L, ok, _ = SP.cholesky_int(P)
        self.assertTrue(ok)
        self.assertEqual(L[0][0], q(2))             # exact 2
        self.assertEqual(L[1][0], q(1))             # exact 1
        # recompose ≈ P within quantization
        self.assertLess(SP.frob2(F.sub(P, SP.recompose(L))), 1000)

    def test_recompose_roundtrip_spd(self):
        P = [[q(9), q(3), q(0)], [q(3), q(5), q(1)], [q(0), q(1), q(2)]]
        self.assertTrue(SP.is_spd_exact(P))
        self.assertLess(SP.spd_error(P), 1 << 20)   # already on the cone ⇒ tiny error


class TestExactGate(unittest.TestCase):
    def test_sylvester_accepts_spd_rejects_indefinite(self):
        self.assertTrue(SP.is_spd_exact([[q(4), q(2)], [q(2), q(3)]]))
        self.assertFalse(SP.is_spd_exact([[q(1), q(2)], [q(2), q(1)]]))   # indefinite
        self.assertFalse(SP.is_spd_exact([[q(1), q(0)], [q(0), q(-1)]]))  # negative pivot


class TestRetraction(unittest.TestCase):
    def test_projects_indefinite_onto_cone(self):
        ind = [[q(1), q(2)], [q(2), q(1)]]
        self.assertFalse(SP.is_spd_exact(ind))
        self.assertTrue(SP.is_spd_exact(SP.project_spd(ind)))

    def test_projection_near_idempotent_on_cone(self):
        # Π_SPD is idempotent only UP TO fixed-point quantization (a few ulps) — deterministic, not exact.
        P = [[q(4), q(1)], [q(1), q(4)]]
        once = SP.project_spd(P)
        twice = SP.project_spd(once)
        self.assertTrue(SP.is_spd_exact(once) and SP.is_spd_exact(twice))
        self.assertLess(SP.frob2(F.sub(once, twice)), 1 << 20)   # near-idempotent (quantization only)
        self.assertEqual(once, SP.project_spd(P))                # but fully DETERMINISTIC (re-run equal)


class TestAdaptiveCadence(unittest.TestCase):
    def test_latency_win_when_calm(self):
        # Weak drift: state stays deep in the cone ⇒ adaptive does far FEWER retractions than uniform.
        P0 = [[q(4), q(0)], [q(0), q(4)]]
        D = [[F.to_fp(-1, 1000), F.to_fp(3, 100)], [F.to_fp(3, 100), F.to_fp(-1, 1000)]]
        r = E.evolve_spd_audited(P0, D, F.to_fp(1, 1000), 4000, horizon=64,
                                 measure_every=64, uniform_every=64)
        self.assertLess(r["retractions"], r["uniform_retractions"])
        self.assertTrue(SP.is_spd_exact(r["P"]))

    def test_holds_cone_under_strong_drift(self):
        # Strong drift breaks PD without help; the adaptive policy holds the committed state on-cone.
        P0 = [[q(1), q(0)], [q(0), q(1)]]
        D = [[F.to_fp(-2, 10), F.to_fp(5, 10)], [F.to_fp(5, 10), F.to_fp(-2, 10)]]
        dt = F.to_fp(1, 1000)
        raw = P0
        for _ in range(3000):
            raw = E.symmetrize_add(raw, D, dt)
        self.assertFalse(SP.is_spd_exact(raw))                      # drift really threatens the cone
        r = E.evolve_spd_audited(P0, D, dt, 3000, horizon=64)
        self.assertTrue(SP.is_spd_exact(r["P"]))                    # committed state held on-cone

    def test_cadence_independent_of_ghost_sampling(self):
        # OBSERVABLE PURITY: ghost measurement cadence does not change the committed forward path.
        P0 = [[q(3), q(0)], [q(0), q(3)]]
        D = [[F.to_fp(-1, 100), F.to_fp(4, 100)], [F.to_fp(4, 100), F.to_fp(-1, 100)]]
        dt = F.to_fp(1, 1000)
        a = E.evolve_spd_audited(P0, D, dt, 2000, horizon=32, measure_every=1)
        b = E.evolve_spd_audited(P0, D, dt, 2000, horizon=32, measure_every=500)
        self.assertEqual(a["final_hash"], b["final_hash"])          # legacy P-only identity invariant
        self.assertEqual(a["P"], b["P"])
        self.assertEqual(a["retractions"], b["retractions"])        # cadence unaffected by ghost


class TestDeterminismAndAnchor(unittest.TestCase):
    def test_structural_deterministic(self):
        P0 = [[q(2), q(0)], [q(0), q(2)]]
        D = [[F.to_fp(-1, 100), F.to_fp(4, 100)], [F.to_fp(4, 100), F.to_fp(-1, 100)]]
        a = E.evolve_spd_audited(P0, D, F.to_fp(1, 1000), 2000, horizon=32, measure_every=32)
        b = E.evolve_spd_audited(P0, D, F.to_fp(1, 1000), 2000, horizon=32, measure_every=32)
        self.assertEqual(a["structural_hash"], b["structural_hash"])

    def test_pinned_anchor(self):
        P0 = [[q(2), q(0)], [q(0), q(2)]]
        D = [[F.to_fp(-1, 100), F.to_fp(4, 100)], [F.to_fp(4, 100), F.to_fp(-1, 100)]]
        r = E.evolve_spd_audited(P0, D, F.to_fp(1, 1000), 2000, horizon=32,
                                 measure_every=32, uniform_every=32)
        self.assertEqual(r["structural_hash"],
                         "1d0c1d0fec540ceb76cfd2b0c4aac5cb8d161035beab5dfeb86bd3adab40aee1")
        self.assertEqual(r["protocol_version"], "aether-spd/1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
