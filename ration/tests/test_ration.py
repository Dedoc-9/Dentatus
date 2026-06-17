"""Tests for ration deterministic resource clamps."""
import os, sys, copy, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import meter as M
import core
from court import verify_chain
from signing import HmacSigner
import demo_ration as D


class TestMeter(unittest.TestCase):
    def test_step_total_weighted(self):
        self.assertEqual(M.step_total({"iterations": 3, "mutations": 2}, {"mutations": 5}), 3 + 10)

    def test_within_budget_ceiling(self):
        pol = {"ceiling": 10}
        self.assertTrue(M.within_budget({"iterations": 10}, pol))
        self.assertFalse(M.within_budget({"iterations": 11}, pol))

    def test_within_budget_per_category(self):
        pol = {"ceiling": 100, "per_category": {"tokens": 5}}
        self.assertFalse(M.within_budget({"tokens": 6}, pol))

    def test_meter_accumulates(self):
        m = M.StepMeter().add("tokens", 3).add("tokens").add("nodes", 2)
        self.assertEqual(m.snapshot()["tokens"], 4)
        self.assertEqual(m.snapshot()["nodes"], 2)


class TestGatedRun(unittest.TestCase):
    def _rec(self):
        return core.Recorder(HmacSigner(b"k"), core.ruleset_hash(D.run_logic, D.budget_invariant))

    def test_within_seals_and_replays(self):
        s = D._sealed({"iterations": 100, "tokens": 100, "mutations": 0, "nodes": 0}, 9.9)
        r = self._rec().record("R", s, D.run_logic(s), D.budget_invariant)
        self.assertTrue(verify_chain([r], b"k", D.run_logic, D.budget_invariant).ok)

    def test_over_budget_refused(self):
        s = D._sealed({"iterations": 0, "tokens": 2000, "mutations": 0, "nodes": 0}, 9.9)
        with self.assertRaises(core.InvariantViolation):
            self._rec().record("R", s, D.run_logic(s), D.budget_invariant)

    def test_hardware_invariant_gate(self):
        counts = {"iterations": 300, "tokens": 600, "mutations": 0, "nodes": 0}
        # different captured cpu_ms must not change the gate outcome
        a = D._sealed(counts, 5.0); b = D._sealed(counts, 5000.0)
        self.assertEqual(D.budget_invariant(a, D.run_logic(a)), D.budget_invariant(b, D.run_logic(b)))
        # and content hash of the deterministic part (counts/total) is independent of cpu_ms in the gate
        self.assertEqual(D.run_logic(a)["total_steps"], D.run_logic(b)["total_steps"])

    def test_tamper_caught(self):
        s = D._sealed({"iterations": 100, "tokens": 100, "mutations": 0, "nodes": 0}, 9.9)
        r = self._rec().record("R", s, D.run_logic(s), D.budget_invariant)
        bad = copy.deepcopy([r]); bad[0]["frame"]["inputs"]["counts"]["tokens"] = 5
        self.assertFalse(verify_chain(bad, b"k", D.run_logic, D.budget_invariant).ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
