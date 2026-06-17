"""syracuse/tests/test_syracuse.py — integer Collatz/Syracuse map, gates/observables, ghost, ties. Stdlib."""
import os, sys, unittest
_S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _S)
import orbit as S
sys.path.insert(0, os.path.join(os.path.dirname(_S), "ration"))
import meter as R


class Map(unittest.TestCase):
    def test_step_values(self):
        self.assertEqual([S.step(n) for n in (2, 3, 5, 8)], [1, 5, 8, 4])

    def test_orbit_of_three(self):
        self.assertEqual(S.orbit(3), [3, 5, 8, 4, 2, 1])

    def test_orbit_reaches_one(self):
        for n in (1, 6, 27, 97, 703):
            self.assertEqual(S.orbit(n)[-1], 1)

    def test_rejects_nonpositive_and_bool(self):
        for bad in (0, -4, True):
            with self.assertRaises(S.SyracuseError):
                S.step(bad)

    def test_orbit_hash_deterministic(self):
        self.assertEqual(S.orbit_hash(S.orbit(27)), S.orbit_hash(S.orbit(27)))
        self.assertNotEqual(S.orbit_hash(S.orbit(27)), S.orbit_hash(S.orbit(28)))


class Gates(unittest.TestCase):
    def test_gates_within_budget(self):
        g = S.gates(27)
        self.assertTrue(g["reached_one"]); self.assertEqual(g["stopping_time"], 70); self.assertTrue(g["within_budget"])

    def test_budget_breach_is_unknown_not_false(self):
        g = S.gates(27, max_steps=5)
        self.assertFalse(g["within_budget"]); self.assertIsNone(g["reached_one"]); self.assertIsNone(g["orbit_hash"])

    def test_observables_do_not_gate(self):
        # two seeds with the same stopping-time gate can have different observables; gate is unaffected
        ob = S.observables(S.orbit(27))
        self.assertEqual(ob["peak"], 4616)
        self.assertEqual(len(ob["parity_word"]), 70)
        self.assertIsInstance(ob["log_drift"], float)        # a float observable, never in a gate/hash


class Ghost(unittest.TestCase):
    def test_witness_never_proves(self):
        w = S.ConjectureWitness()
        for n in range(1, 2000):
            w.record(S.gates(n, max_steps=2000))
        r = w.report()
        self.assertEqual(r["verified_count"], 1999)
        self.assertFalse(r["conjecture_proven"])             # structural: always False

    def test_refused_seeds_tracked(self):
        w = S.ConjectureWitness()
        w.record(S.gates(27, max_steps=3))                   # forced budget breach
        self.assertIn(27, w.report()["refused_within_budget"])
        self.assertFalse(w.report()["conjecture_proven"])


class RationTie(unittest.TestCase):
    POLICY = {"ceiling": 80, "per_category": {}, "weights": {"iterations": 1}}

    def test_short_orbit_within_budget(self):
        self.assertTrue(R.within_budget(S.ration_counts(27), self.POLICY))      # S=70 <= 80

    def test_long_orbit_refused(self):
        self.assertFalse(R.within_budget(S.ration_counts(703), self.POLICY))    # S=108 > 80

    def test_budget_breach_reports_ceiling_spent(self):
        c = S.ration_counts(27, max_steps=5)
        self.assertEqual(c["iterations"], 5)                 # unknown-within-budget => budget spent


class LockstepTie(unittest.TestCase):
    def test_orbit_as_truth_track(self):
        t = S.as_truth_track(27)
        self.assertEqual(t.tick, 70); self.assertEqual(t.states[-1]["n"], 1)

    def test_track_replay_deterministic(self):
        self.assertEqual(S.as_truth_track(27).hashes[-1], S.as_truth_track(27).hashes[-1])


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("set PYTHONHASHSEED=0\n"); raise SystemExit(2)
    unittest.main(verbosity=2)
