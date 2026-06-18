"""stasis/tests/test_stasis.py — Iron Canon, Divergence Ledger, Lazy Lattice."""
import os, sys, unittest
_S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _S)
import canon as C
import drift as D
import batch as B


class Canon(unittest.TestCase):
    def test_key_order_independent(self):
        self.assertEqual(C.canon_hash({"a": 1, "b": 2}), C.canon_hash({"b": 2, "a": 1}))

    def test_rejects_set(self):
        with self.assertRaises(C.CanonizationError):
            C.canonicalize({"s": {1, 2}})

    def test_rejects_bytes(self):
        with self.assertRaises(C.CanonizationError):
            C.canonicalize({"b": b"x"})

    def test_rejects_float_by_default(self):
        with self.assertRaises(C.CanonizationError):
            C.canonicalize({"f": 1.5})

    def test_allows_float_when_flagged_but_not_nan(self):
        C.canonicalize({"obs": 1.5}, allow_float=True)
        with self.assertRaises(C.CanonizationError):
            C.canonicalize({"obs": float("inf")}, allow_float=True)

    def test_rejects_nonstring_keys(self):
        with self.assertRaises(C.CanonizationError):
            C.canonicalize({7: "x"})


class Drift(unittest.TestCase):
    GATE = ["decision", "amount_cents"]
    EXP = {"decision": "approve", "amount_cents": 4500, "logprob": -0.12, "latency_ms": 40}

    def test_exact_match_passes(self):
        self.assertEqual(D.classify(self.EXP, dict(self.EXP), self.GATE)["verdict"], D.PASS)

    def test_observable_drift_warns(self):
        v = D.classify(self.EXP, dict(self.EXP, logprob=-0.99, latency_ms=88), self.GATE)
        self.assertEqual(v["verdict"], D.WARN); self.assertEqual(v["event"]["type"], "OBSERVABLE_DRIFT")

    def test_gate_change_fails(self):
        v = D.classify(self.EXP, dict(self.EXP, decision="deny"), self.GATE)
        self.assertEqual(v["verdict"], D.FAIL); self.assertEqual(v["event"]["field"], "decision")

    def test_gate_change_beats_observable_drift(self):
        # both a gate AND an observable differ -> still FAIL (the decision changed)
        v = D.classify(self.EXP, dict(self.EXP, decision="deny", latency_ms=99), self.GATE)
        self.assertEqual(v["verdict"], D.FAIL)


class Batch(unittest.TestCase):
    def test_root_deterministic(self):
        leaves = [C.canon_hash({"i": i}) for i in range(7)]
        self.assertEqual(B.merkle_root(leaves), B.merkle_root(list(leaves)))

    def test_inclusion_proof_verifies(self):
        leaves = [C.canon_hash({"i": i}) for i in range(8)]
        root = B.merkle_root(leaves)
        for idx in range(8):
            self.assertTrue(B.verify_inclusion(leaves[idx], B.inclusion_proof(leaves, idx), root))

    def test_odd_count_inclusion(self):
        leaves = [C.canon_hash({"i": i}) for i in range(5)]   # odd -> duplicate-last path
        root = B.merkle_root(leaves)
        self.assertTrue(B.verify_inclusion(leaves[4], B.inclusion_proof(leaves, 4), root))

    def test_tampered_leaf_fails(self):
        leaves = [C.canon_hash({"i": i}) for i in range(8)]
        root = B.merkle_root(leaves)
        proof = B.inclusion_proof(leaves, 3)
        self.assertFalse(B.verify_inclusion(C.canon_hash({"i": 999}), proof, root))

    def test_empty_batch_errors(self):
        with self.assertRaises(B.StasisError):
            B.merkle_root([])


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("set PYTHONHASHSEED=0\n"); raise SystemExit(2)
    unittest.main(verbosity=2)
