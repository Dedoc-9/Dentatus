"""Tests for the hardened reflexive self-audit."""
import os, sys, json, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import evaluate as E
import assess as A
from court import assay_audit
from signing import HmacSigner

BASELINE = json.load(open(E.BASELINE_PATH)) if os.path.exists(E.BASELINE_PATH) else {}


class TestPureDetectors(unittest.TestCase):
    def test_compare_clean(self):
        b = {"x": "aa", "y": "bb"}
        self.assertEqual(E.compare_to_baseline({"x": "aa", "y": "bb"}, b), [])

    def test_compare_detects_change_missing_added(self):
        b = {"x": "aa", "y": "bb"}
        d = E.compare_to_baseline({"x": "ZZ", "z": "cc"}, b)
        self.assertIn("CHANGED x", d); self.assertIn("MISSING y", d); self.assertIn("ADDED z", d)

    def test_find_duplicated_cores_catches_renamed_copy(self):
        core_hashes = {"deadbeef"}
        siblings = {"glitch/legit.py": "feedface", "evil/mycore.py": "deadbeef"}
        self.assertEqual(E.find_duplicated_cores(core_hashes, siblings), ["evil/mycore.py"])

    def test_find_duplicated_cores_clean(self):
        self.assertEqual(E.find_duplicated_cores({"aa"}, {"s/x.py": "bb"}), [])


class TestLiveChecks(unittest.TestCase):
    def test_determinism(self):
        _, ok, _ = E.check_determinism(); self.assertTrue(ok)

    def test_parity(self):
        _, ok, ev = E.check_parity(); self.assertTrue(ok and ev["all_equal"])

    def test_frozen_cores_match_pinned_baseline(self):
        if not BASELINE:
            self.skipTest("baseline not established yet")
        _, ok, ev = E.check_frozen_cores(BASELINE)
        self.assertTrue(ok, ev.get("drift"))

    def test_no_core_copies_in_tree(self):
        _, ok, ev = E.check_sibling_law(); self.assertTrue(ok, ev["copies"])

    def test_drift_is_caught(self):
        if not BASELINE:
            self.skipTest("baseline not established yet")
        victim, caught = E.demonstrate_drift_caught(BASELINE)
        self.assertTrue(caught)


class TestIdentityAndSeal(unittest.TestCase):
    def test_workbench_H_deterministic(self):
        a, _ = E.workbench_identity(); b, _ = E.workbench_identity()
        self.assertEqual(a, b)

    def test_self_audit_ledger_replays_with_rich_evidence(self):
        wb_H, _ = E.workbench_identity()
        rec = A.AssayRecorder(HmacSigner(b"k")); ledger = []
        for name, ok, ev in [E.check_determinism(), E.check_parity(), E.check_sibling_law()]:
            evidence = {"decision": {"ok": ok}, "ground_truth": {"ok": True}, "key": "ok", "detail": ev}
            ledger.append(rec.record_metric(wb_H, "correct", "correctness_vs_oracle", evidence))
        self.assertTrue(assay_audit(ledger, b"k", {}, {}).ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
