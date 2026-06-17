"""Tests for the reflexive self-audit (the workbench evaluating the workbench)."""
import os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import evaluate as E
import assess as A
from court import assay_audit
from signing import HmacSigner


class TestChecks(unittest.TestCase):
    def test_all_checks_pass_on_current_tree(self):
        for fn in E.CHECKS:
            name, ok, ev = fn()
            self.assertTrue(ok, "%s failed: %s" % (name, ev))

    def test_determinism_check(self):
        _, ok, _ = E.check_determinism(); self.assertTrue(ok)

    def test_parity_check(self):
        _, ok, _ = E.check_parity(); self.assertTrue(ok)

    def test_sibling_law_no_core_duplication(self):
        _, ok, ev = E.check_sibling_law(); self.assertTrue(ok, ev["violations"])


class TestIdentityAndSeal(unittest.TestCase):
    def test_workbench_H_deterministic(self):
        a, _ = E.workbench_identity(); b, _ = E.workbench_identity()
        self.assertEqual(a, b)

    def test_self_audit_ledger_replays(self):
        wb_H, _ = E.workbench_identity()
        rec = A.AssayRecorder(HmacSigner(b"k"))
        ledger = []
        for fn in E.CHECKS:
            _, ok, _ = fn()
            ev = {"decision": {"ok": ok}, "ground_truth": {"ok": True}, "key": "ok"}
            ledger.append(rec.record_metric(wb_H, "correct", "correctness_vs_oracle", ev))
        self.assertTrue(assay_audit(ledger, b"k", {}, {}).ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
