"""crucible/tests/test_crucible.py — attack simulations (which are also the preflight unit suite)."""
import os, sys, unittest
_C = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _C)
import forest as C
import oracle as O


class Forest(unittest.TestCase):
    def test_preimages(self):
        self.assertEqual(C.preimages(8), [16, 5])              # even branch then odd branch
        self.assertEqual(C.preimages(2), [4])                  # odd preimage would be 1 -> excluded (cycle)

    def test_generation_is_deterministic(self):
        a = [s["n"] for s in C.generate(14, 10 ** 5)]
        b = [s["n"] for s in C.generate(14, 10 ** 5)]
        self.assertEqual(a, b)

    def test_every_seed_matches_forward_replay(self):
        for s in C.generate(16, 10 ** 5):
            ok, detail = C.verify_seed(s)
            self.assertTrue(ok, "%s: %s" % (s, detail))        # stopping_time == reverse depth, peak matches

    def test_power_of_two_is_trivial(self):
        # 2^d is generated at depth d with altitude exactly 1 (pure descent, no climb)
        forest = C.generate(12, 10 ** 6)
        p = next(s for s in forest if s["n"] == 4096)
        self.assertEqual(p["stopping_time"], 12); self.assertEqual(p["altitude"], 1)

    def test_select_prefers_real_climbers(self):
        forest = C.generate(25, 10 ** 6)
        hard = C.select(forest, within_budget=25, by="altitude")
        self.assertGreater(hard["altitude"], 1)                # not a power of 2

    def test_seed_just_under_within_budget(self):
        s = C.seed_just_under(20, 10 ** 6)
        self.assertLessEqual(s["stopping_time"], 20)
        self.assertTrue(C.verify_seed(s)[0])


class Oracle(unittest.TestCase):
    def test_ration_boundary(self):
        r = O.inject_ration(30)
        self.assertTrue(r["inside"]["admitted"])               # hard seed inside budget admitted
        self.assertFalse(r["over"]["admitted"])                # deeper seed refused

    def test_tessera_survives_hard_seed(self):
        forest = C.generate(25, 10 ** 6)
        hard = C.select(forest, within_budget=25, by="altitude")
        res = O.inject_tessera(hard["n"])
        self.assertTrue(res["verified"]); self.assertEqual(res["steps"], hard["stopping_time"])

    def test_manifest_reproducible_and_verified(self):
        m1 = O.build_manifest(20, 10 ** 6, top=8)
        m2 = O.build_manifest(20, 10 ** 6, top=8)
        self.assertEqual(m1["manifest_hash"], m2["manifest_hash"])
        self.assertTrue(all(s["verified_forward"] for s in m1["seeds"]))

    def test_generator_gate(self):
        # the "build fails if the generator is broken" guard, as a deterministic assertion
        s = C.seed_just_under(18, 10 ** 6)
        self.assertIsNotNone(s); self.assertTrue(C.verify_seed(s)[0]); self.assertGreater(s["altitude"], 1)


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("set PYTHONHASHSEED=0\n"); raise SystemExit(2)
    unittest.main(verbosity=2)
