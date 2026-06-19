# SPDX-License-Identifier: AGPL-3.0-only
"""VeriSim/tests/test_verisim.py — verifiable simulation shards: run, replay, tamper, drift, spot-check."""
import os, sys, unittest
_V = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _V)
sys.path.insert(0, os.path.join(os.path.dirname(_V), "chronicle"))
import scenarios as SC
import runner as R
import court as C
from _cores import SCALE


def _brake():
    return R.run_simulation("brake_1d", SC.brake_seed(30, 8, 10), input_data={"m": "toy"})


class RunShard(unittest.TestCase):
    def test_shard_shape(self):
        s = _brake()
        self.assertEqual(s["schema"], "verisim/1"); self.assertEqual(s["scenario"], "brake_1d")
        self.assertGreater(s["steps"], 0); self.assertEqual(s["leaf_count"], s["steps"] + 1)
        self.assertTrue(s["final_state"]["halted"])

    def test_input_data_bound(self):
        a = R.run_simulation("brake_1d", SC.brake_seed(30, 8, 10), input_data={"m": "a"})
        b = R.run_simulation("brake_1d", SC.brake_seed(30, 8, 10), input_data={"m": "b"})
        self.assertNotEqual(a["input_data_hash"], b["input_data_hash"])

    def test_determinism(self):
        self.assertEqual(_brake()["merkle_root"], _brake()["merkle_root"])


class ReplayCourt(unittest.TestCase):
    def test_clean_replay(self):
        self.assertTrue(C.replay(_brake())["verified"])

    def test_forged_final_fails(self):
        s = _brake()
        bad = dict(s, final_state=dict(s["final_state"], p=s["final_state"]["p"] + SCALE))
        self.assertFalse(C.replay(bad)["verified"])

    def test_forged_merkle_fails(self):
        s = _brake()
        self.assertFalse(C.replay(dict(s, merkle_root="0" * 64))["verified"])

    def test_tampered_tessera_fails(self):
        s = _brake()
        bad = dict(s); bad["tessera"] = dict(s["tessera"], steps=s["tessera"]["steps"] - 3)
        self.assertFalse(C.replay(bad)["verified"])


class Drift(unittest.TestCase):
    GATE = ["p", "v", "halted"]

    def test_observable_drift_warns(self):
        s = _brake()
        v = C.classify_final(s, dict(s["final_state"], t=s["final_state"]["t"] + 5), self.GATE)
        self.assertEqual(v["verdict"], "WARN")

    def test_logic_change_fails(self):
        s = _brake()
        v = C.classify_final(s, dict(s["final_state"], p=s["final_state"]["p"] + SCALE), self.GATE)
        self.assertEqual(v["verdict"], "FAIL")


class SpotCheck(unittest.TestCase):
    def test_step_inclusion(self):
        s = _brake()
        ok, _ = C.spot_check_step(s, s["steps"] // 2)
        self.assertTrue(ok)

    def test_out_of_range(self):
        s = _brake()
        self.assertFalse(C.spot_check_step(s, s["steps"] + 999)[0])


class Bounded(unittest.TestCase):
    def test_runaway_halts_at_budget(self):
        s = R.run_simulation("projectile_1d", SC.projectile_seed(1000000, 0, 10, max_steps=300), fuel_budget=300)
        self.assertLessEqual(s["steps"], 300)


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("set PYTHONHASHSEED=0\n"); raise SystemExit(2)
    unittest.main(verbosity=2)
