"""intervention/tests/test_intervention.py — the causal query protocol.

Covers: the airlock authorization gate, the shadow do-operator (committed history untouched), the four
verdicts, and the Causal Intervention Benchmark separating cause / confounder / cycle."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import protocol as P
import experiment as E
import query as Q
import benchmark as B

MOD = B.MOD


def _true_dyn():
    return {"A": 5, "C": 0, "drive": 7}, (lambda s: {"A": (s["A"] + s["drive"]) % MOD,
                                                     "C": (3 * s["A"]) % MOD, "drive": s["drive"]})


class TestProtocol(unittest.TestCase):
    def test_authorize_admits_bounded_question(self):
        self.assertTrue(P.authorize(P.make("A", "C")).admitted)

    def test_authorize_rejects_self_scope_rollback(self):
        self.assertFalse(P.authorize(P.make("A", "A")).admitted)
        self.assertFalse(P.authorize(P.make("A", "C", allowed_scope=999)).admitted)
        self.assertFalse(P.authorize(P.make("A", "C", rollback_boundary=0)).admitted)

    def test_from_coupling_forms_question(self):
        Cd = __import__("collections").namedtuple("C", "source target ghost_total")
        c = P.from_coupling(Cd("A", "C", 500))
        self.assertEqual((c.source, c.target), ("A", "C"))
        self.assertEqual(c.expected_effect, 500)

    def test_candidate_hash_deterministic(self):
        self.assertEqual(P.make("A", "C").h, P.make("A", "C").h)


class TestExperimentShadow(unittest.TestCase):
    def test_do_run_does_not_mutate_init(self):
        init, dyn = _true_dyn()
        snap = dict(init)
        E.do_run(dyn, init, 10, {"A": 999})
        self.assertEqual(init, snap)                       # the world was never touched

    def test_effect_is_directional(self):
        init, dyn = _true_dyn()
        self.assertGreater(E.causal_effect(dyn, init, 12, "A", "C", 1, 1000), 0)   # A causes C
        self.assertEqual(E.causal_effect(dyn, init, 12, "C", "A", 1, 1000), 0)     # C does not cause A

    def test_committed_unchanged(self):
        import hashlib, json
        init, dyn = _true_dyn()
        h = lambda w: hashlib.sha256(json.dumps(w, sort_keys=True).encode()).hexdigest()
        self.assertTrue(E.committed_unchanged(h, init, dyn, "A", "C", 12, 1, 1000))


class TestQueryVerdicts(unittest.TestCase):
    def test_unauthorized(self):
        init, dyn = _true_dyn()
        self.assertEqual(Q.query(P.make("A", "A"), dyn, init).verdict, "UNAUTHORIZED")

    def test_confirmed(self):
        init, dyn = _true_dyn()
        self.assertEqual(Q.query(P.make("A", "C"), dyn, init).verdict, "CONFIRMED")


class TestCausalInterventionBenchmark(unittest.TestCase):
    def test_separates_three_worlds(self):
        rows = B.run()
        self.assertEqual(rows["true"].verdict, "CONFIRMED")
        self.assertEqual(rows["confounder"].verdict, "REJECTED")   # the case persistence cannot resolve
        self.assertEqual(rows["feedback"].verdict, "CYCLE")

    def test_verdict_and_determinism(self):
        label, _ = B.verdict()
        self.assertEqual(label, "intervention-separates-cause-confounder-cycle")
        self.assertEqual(B.verdict(), B.verdict())

    def test_evidence_is_not_authority(self):
        # a CONFIRMED verdict carries an evidence delta, never a graph edit
        r = B.run()["true"]
        self.assertEqual(r.evidence_delta, 1)
        self.assertFalse(hasattr(r, "apply"))


class TestExperimentInvariantOnKernel(unittest.TestCase):
    def setUp(self):
        import demo_intervention as D
        self.D = D

    def test_committed_history_untouched_by_experiments(self):
        r = self.D.run()
        self.assertTrue(r["authorized"])
        self.assertTrue(r["committed_history_identical"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
