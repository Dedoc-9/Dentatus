"""fuel/tests/test_fuel.py — integer bounded-execution VM: exact fuel, fail-closed, determinism, proof."""
import os, sys, unittest
_F = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WB = os.path.dirname(_F)
sys.path.insert(0, _F)
sys.path.insert(0, os.path.join(_WB, "syracuse"))
sys.path.insert(0, os.path.join(_WB, "crucible"))
sys.path.insert(0, os.path.join(_WB, "chronicle"))
import vm as V
import programs as P
import proof as PR
import orbit as SY
import forest as C

PROG = P.syracuse_program()


class Engine(unittest.TestCase):
    def test_arithmetic(self):
        r = V.run([["set", "a", 6], ["set", "b", 7], ["mul", "c", "a", "b"], ["halt"]], {}, 100)
        self.assertEqual(r["regs"]["c"], 42); self.assertEqual(r["reason"], "halt")

    def test_sum_program(self):
        self.assertEqual(V.run(P.sum_to_program(), {"k": 10, "s": 0}, 1000)["regs"]["s"], 55)

    def test_fuel_used_is_exact_and_weighted(self):
        # set(1) + mul(2) + halt(1) = 4 fuel exactly
        r = V.run([["set", "a", 2], ["mul", "a", "a", "a"], ["halt"]], {}, 100)
        self.assertEqual(r["fuel_used"], 4)


class FailClosed(unittest.TestCase):
    def test_out_of_fuel_halts_not_errors(self):
        r = V.run(PROG, {"n": 27, "s": 0}, fuel_limit=50)
        self.assertEqual(r["reason"], "out of fuel"); self.assertFalse(r["error"]); self.assertEqual(r["fuel_left"], 0)

    def test_div_by_zero_errors(self):
        r = V.run([["div", "x", "x", 0]], {"x": 5}, 10)
        self.assertTrue(r["error"]); self.assertIn("zero", r["reason"])

    def test_run_always_terminates(self):
        # an infinite loop is bounded by fuel
        r = V.run([["jmp", 0]], {}, fuel_limit=20)
        self.assertEqual(r["reason"], "out of fuel")


class Determinism(unittest.TestCase):
    def test_byte_identical_runs(self):
        self.assertEqual(V.run(PROG, {"n": 27, "s": 0}, 100000), V.run(PROG, {"n": 27, "s": 0}, 100000))

    def test_matches_syracuse(self):
        for n in (3, 6, 27, 97, 703):
            self.assertEqual(V.run(PROG, {"n": n, "s": 0}, 100000)["regs"]["s"], SY.gates(n)["stopping_time"])


class CrucibleHammer(unittest.TestCase):
    def test_hard_seed_exact_halt(self):
        hard = C.seed_just_under(35, value_ceiling=10 ** 6)
        r = V.run(PROG, {"n": hard["n"], "s": 0}, 100000)
        self.assertEqual(r["reason"], "halt")
        self.assertEqual(r["regs"]["s"], hard["stopping_time"])    # exact, no drift on a chaotic input


class Proof(unittest.TestCase):
    def test_run_emits_verifiable_tessera(self):
        shard = PR.prove(PROG, {"n": 27, "s": 0}, 100000)
        ok, detail = PR.verify_proof(shard)
        self.assertTrue(ok, detail)

    def test_tampered_proof_rejected(self):
        shard = PR.prove(PROG, {"n": 27, "s": 0}, 100000)
        self.assertFalse(PR.verify_proof(dict(shard, steps=shard["steps"] - 3))[0])

    def test_program_is_bound_into_proof(self):
        # a verifier running a DIFFERENT program must not validate the shard
        shard = PR.prove(PROG, {"n": 27, "s": 0}, 100000)
        # mutate the program inside the seed -> seed differs -> replay diverges
        bad = dict(shard, seed=dict(shard["seed"], prog=P.sum_to_program()))
        self.assertFalse(PR.verify_proof(bad)[0])


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("set PYTHONHASHSEED=0\n"); raise SystemExit(2)
    unittest.main(verbosity=2)
