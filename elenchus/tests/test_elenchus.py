"""elenchus/tests/test_elenchus.py — reasoning-trace interrogation: valid, FABRICATED, GAP, UNKNOWN, proof."""
import os, sys, unittest
_E = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _E)
sys.path.insert(0, os.path.join(os.path.dirname(_E), "chronicle"))
import interrogate as E

PREM = [{"var": "a", "val": 27}]
VALID = [
    {"rule": "collatz", "args": {"src": "a", "dst": "b"}, "claim": {"kind": "val", "var": "b", "val": 41}},
    {"rule": "collatz", "args": {"src": "b", "dst": "c"}, "claim": {"kind": "val", "var": "c", "val": 62}},
    {"rule": "compare", "args": {"lhs": "a", "rhs": "b", "op": "<"}, "claim": {"kind": "rel", "lhs": "a", "op": "<", "rhs": "b"}},
    {"rule": "compare", "args": {"lhs": "b", "rhs": "c", "op": "<"}, "claim": {"kind": "rel", "lhs": "b", "op": "<", "rhs": "c"}},
    {"rule": "transitivity", "args": {"a": "a", "b": "b", "c": "c", "op": "<"}, "claim": {"kind": "rel", "lhs": "a", "op": "<", "rhs": "c"}},
]
CONCLUSION = {"kind": "rel", "lhs": "a", "op": "<", "rhs": "c"}


class Valid(unittest.TestCase):
    def test_clean_trace(self):
        self.assertEqual(E.verify_trace(PREM, VALID, conclusion=CONCLUSION), (True, None))

    def test_arithmetic_rules(self):
        steps = [
            {"rule": "add", "args": {"a": "a", "b": 3, "dst": "s"}, "claim": {"kind": "val", "var": "s", "val": 30}},
            {"rule": "mul", "args": {"a": "s", "b": 2, "dst": "t"}, "claim": {"kind": "val", "var": "t", "val": 60}},
        ]
        self.assertTrue(E.verify_trace(PREM, steps)[0])


class Faults(unittest.TestCase):
    def test_fabricated_output(self):
        bad = list(VALID); bad[0] = {"rule": "collatz", "args": {"src": "a", "dst": "b"},
                                     "claim": {"kind": "val", "var": "b", "val": 40}}
        ok, fault = E.verify_trace(PREM, bad)
        self.assertFalse(ok); self.assertEqual(fault["step"], 0); self.assertIn("FABRICATED", fault["reason"])

    def test_fabricated_false_comparison(self):
        steps = [{"rule": "collatz", "args": {"src": "a", "dst": "b"}, "claim": {"kind": "val", "var": "b", "val": 41}},
                 {"rule": "compare", "args": {"lhs": "b", "rhs": "a", "op": "<"},   # 41 < 27 is false
                  "claim": {"kind": "rel", "lhs": "b", "op": "<", "rhs": "a"}}]
        ok, fault = E.verify_trace(PREM, steps)
        self.assertFalse(ok); self.assertIn("does not hold", fault["reason"])

    def test_skipped_step_gap(self):
        gap = [VALID[0], VALID[1], VALID[2], VALID[4]]              # transitivity without b<c
        ok, fault = E.verify_trace(PREM, gap)
        self.assertFalse(ok); self.assertEqual(fault["rule"], "transitivity"); self.assertIn("GAP", fault["reason"])

    def test_gap_unestablished_operand(self):
        steps = [{"rule": "add", "args": {"a": "ghost", "b": 1, "dst": "x"}, "claim": {"kind": "val", "var": "x", "val": 1}}]
        self.assertIn("GAP", E.verify_trace(PREM, steps)[1]["reason"])

    def test_unknown_rule(self):
        ok, fault = E.verify_trace(PREM, [{"rule": "telepathy", "args": {}, "claim": {"kind": "val", "var": "z", "val": 1}}])
        self.assertFalse(ok); self.assertIn("UNKNOWN_RULE", fault["reason"])

    def test_incomplete_conclusion(self):
        ok, fault = E.verify_trace(PREM, VALID[:2], conclusion=CONCLUSION)
        self.assertFalse(ok); self.assertIn("INCOMPLETE", fault["reason"])


class Proof(unittest.TestCase):
    def test_verdict_is_replayable_tessera(self):
        shard = E.prove_trace(PREM, VALID)
        self.assertTrue(E.verify_proof(shard)[0])

    def test_tampered_proof_rejected(self):
        shard = E.prove_trace(PREM, VALID)
        self.assertFalse(E.verify_proof(dict(shard, steps=shard["steps"] - 1))[0])

    def test_trace_is_bound_into_proof(self):
        shard = E.prove_trace(PREM, VALID)
        bad_seed = dict(shard["seed"], steps=[VALID[0]])           # different trace
        self.assertFalse(E.verify_proof(dict(shard, seed=bad_seed))[0])


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("set PYTHONHASHSEED=0\n"); raise SystemExit(2)
    unittest.main(verbosity=2)
