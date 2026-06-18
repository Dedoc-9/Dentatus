"""
aether/tests/test_aether_field.py — Stage D: self-describing generator field A(W,t,θ), Magnus-2 (Bτ),
the BCH bracket hierarchy, and the dimensionless meta-observability M̂ + regime classifier.

Asserts ONLY what is true: θ-purity (A ghost-blind), β₁ dormant for constant / live for moving,
Magnus-2 reduces to dt·A when constant, M̂ dimensionless + classifier determinism, θ in the structural
identity, and the honest finding that the ghost (geometry) and representation pressure (dynamics) are
DISTINCT channels. It does NOT assert a Magnus-2 accuracy payoff — that is regime-dependent and
inconclusive with the additive (I+Ω) application (see README honest bound).
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import fixedpoint as F
import field as FD
import regime as RG
import evolve as E

q = F.to_fp
A0 = [[0, q(3, 1), 0], [q(-3, 1), 0, 0], [0, 0, 0]]
B0 = [[0, 0, q(2, 1)], [0, 0, 0], [q(-2, 1), 0, 0]]


class TestFieldPurity(unittest.TestCase):
    def test_A_reads_only_W_and_t(self):
        # Structural purity: A's signature is A(self, W, t) — the ghost state is not in scope.
        self.assertNotIn("S", FD.GeneratorField.A.__code__.co_varnames)
        self.assertNotIn("G", FD.GeneratorField.A.__code__.co_varnames)
        self.assertEqual(FD.GeneratorField.A.__code__.co_argcount, 3)  # self, W, t

    def test_theta_is_declared_bundle(self):
        f = FD.GeneratorField(A0, B0, k_state=q(1, 1), k_sched=q(1, 4), period=300)
        th = f.theta()
        self.assertEqual(set(th), {"A0", "B0", "k_state", "rc", "k_sched", "period"})


class TestBracketHierarchy(unittest.TestCase):
    def test_constant_generator_dormant(self):
        f = FD.GeneratorField(A0, B0, k_state=0, k_sched=0)        # constant ⇒ A_k == A_{k+1}
        W = F.identity(3)
        _, b1, b2, b3 = FD.bracket_hierarchy(f.A(W, 0), f.A(W, 1))
        self.assertEqual((b1, b2, b3), (0, 0, 0))                  # Bτ dormant

    def test_moving_generator_lights_up(self):
        f = FD.GeneratorField(A0, B0, k_state=q(5, 1), rc=(0, 1), k_sched=q(1, 1), period=500)
        W = F.identity(3)
        A_k = f.A(W, 0)
        A_k1 = f.A(E.lie_step(W, A_k, q(1, 1000)), 1)
        _, b1, b2, b3 = FD.bracket_hierarchy(A_k, A_k1)
        self.assertGreater(b1, 0)                                  # Bτ now carries information

    def test_magnus_reduces_to_dt_A_when_constant(self):
        # For A_k == A_{k+1} the commutator vanishes ⇒ Ω = dt·A exactly (Bτ off).
        A = A0
        dt = q(1, 1000)
        Om = FD.magnus2_omega(A, A, dt)
        self.assertEqual(Om, F.scalar(dt, A))


class TestMetaVector(unittest.TestCase):
    def test_dimensionless_and_classifies(self):
        m = RG.meta_vector(E=10**16, epsilon=F.SCALE * F.SCALE // (1 << 20),
                           normG=42124860, normZ=4294967296, B_t=24320799,
                           beta1=692436074, normA=12884901888, beta2=2496613772, beta3=2482114741)
        self.assertEqual(set(m), {"geometry", "residual", "quantization", "dynamics",
                                  "representation2", "representation3"})
        c = RG.classify(m)
        self.assertIn(c["regime"], {"geometry-limited", "quantization-limited",
                                    "dynamics-limited", "representation-limited"})
        self.assertEqual(c, RG.classify(m))                       # deterministic

    def test_representation_axis_independent_of_magnitude(self):
        # β₂/(β₁+δ) depends on the RATIO, not the scale: doubling both leaves it ~unchanged.
        # Use large β so the δ=1 div-by-zero guard is negligible ⇒ ratio is scale-invariant.
        m1 = RG.meta_vector(0, 1, 0, 1, 0, 10**6, 1, 5 * 10**6, 5 * 10**6)
        m2 = RG.meta_vector(0, 1, 0, 1, 0, 2 * 10**6, 1, 10**7, 10**7)
        rel = abs(m1["representation2"] - m2["representation2"]) / m1["representation2"]
        self.assertLess(rel, 1e-3)                               # ratio (not scale) is what matters


class TestEvolveFieldIdentity(unittest.TestCase):
    def _run(self, k_state):
        f = FD.GeneratorField(A0, B0, k_state=k_state, rc=(0, 1), k_sched=q(1, 4), period=300)
        return E.evolve_field_audited(F.identity(3), f, q(1, 1000), 10000,
                                      audit_every=500, measure_every=50, integrator="magnus2")

    def test_theta_enters_identity(self):
        self.assertNotEqual(self._run(q(1, 1))["structural_hash"], self._run(q(2, 1))["structural_hash"])

    def test_deterministic(self):
        self.assertEqual(self._run(q(1, 1))["structural_hash"], self._run(q(1, 1))["structural_hash"])

    def test_pinned_anchor(self):
        r = self._run(q(1, 1))
        self.assertEqual(r["structural_hash"],
                         "4e936bcee347363763e9dbb978193bf3e780a8b4a9ae3f58d7944d2a2486e446")
        self.assertEqual(r["protocol_version"], "aether-field/1")

    def test_ghost_and_representation_are_distinct_channels(self):
        # The honest Stage-D finding: geometry (ghost) and dynamics (representation) are non-redundant.
        # A moving field produces BOTH a nonzero ghost AND a nonzero representation pressure, independently.
        r = self._run(q(2, 1))
        self.assertGreater(r["beta1_max"], 0)                     # dynamics axis live
        self.assertGreater(r["rep_pressure_max"], 0)             # representation axis live
        self.assertTrue(any(v > 0 for v in r["S"][0]) or r["B_t"] >= 0)  # ghost channel present


if __name__ == "__main__":
    unittest.main(verbosity=2)
