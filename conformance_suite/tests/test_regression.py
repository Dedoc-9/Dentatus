"""conformance_suite/tests/test_regression.py — the harness itself, and the pinned baseline, are stable."""
import os, sys, unittest
_C = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _C)
import runner as R


class Harness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current = R.collect()
        cls.baseline = R.load_baseline()

    def test_all_apps_probe_cleanly(self):
        for app, res in self.current.items():
            self.assertNotIn("error", res, "%s probe failed: %s" % (app, res.get("error")))
            self.assertIn("golden", res)

    def test_matches_pinned_baseline(self):
        ok, faults = R.compare(self.current, self.baseline)
        self.assertTrue(ok, "conformance drift: %s" % faults)

    def test_drift_is_detected(self):
        mutated = {k: dict(v) for k, v in self.baseline.items()}
        first = sorted(mutated)[0]
        mutated[first]["golden"] = "0" * 64
        ok, faults = R.compare(self.current, mutated)
        self.assertFalse(ok)
        self.assertEqual(faults[0]["app"], first); self.assertEqual(faults[0]["reason"], "DRIFT")

    def test_determinism_repeat(self):
        again = R.collect()
        for app in self.current:
            self.assertEqual(self.current[app].get("golden"), again[app].get("golden"), app)


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("set PYTHONHASHSEED=0\n"); raise SystemExit(2)
    unittest.main(verbosity=2)
