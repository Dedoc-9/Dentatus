"""
airlock/tests/test_airlock.py — the LLM→kernel membrane (transitions-only).

Proves the two architectural laws hold STRUCTURALLY, not by convention:
  intent ≠ authority  — claims/provenance never decide commit; only mechanical checks do.
  telemetry ≠ control — R_p (proposal residual) is computed but never gates.
Plus: every gate rejects into a shard without mutating state; commits chain + are deterministic;
witness is reproduction-admission; and a GOAL is not a transition (rejected at the schema, by design).
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import adapters as A
import adapters_kv as KV
import contract
import conformance as CF
import membrane as M

K = A.K


def world():
    return K.make_world([K.body(0, (0, 5, 0), (0, 0, 0), (1, 1, 1))], ((-10, -10, -10), (10, 10, 10)))


def P(transition, **kw):
    base = {"transition": transition, "budget": kw.pop("budget", {"max_cost": 50, "max_delta": 10**15})}
    base.update(kw)
    return base


class TestGatesRejectIntoShards(unittest.TestCase):
    def setUp(self):
        self.W = world(); self.L = M.Ledger(); self.h0 = A.state_hash(self.W)

    def _reject(self, proposal, gate):
        r = M.propose(self.W, proposal, A, ledger=self.L)
        self.assertFalse(r["ok"]); self.assertEqual(r["gate"], gate)
        self.assertIsNotNone(r["shard"]["shard_hash"])          # evidence emitted
        self.assertEqual(A.state_hash(self.W), self.h0)         # state UNCHANGED

    def test_canon(self):     self._reject({"transition": {"op": "impulse", "id": 0, "dv": [0.5, 0, 0]}, "budget": {}}, "CANON")
    def test_schema(self):    self._reject(P({"op": "teleport"}), "SCHEMA")
    def test_budget(self):    self._reject(P({"op": "advance", "ticks": 100}, budget={"max_cost": 10}), "BUDGET")
    def test_apply(self):     self._reject(P({"op": "impulse", "id": 99, "dv": [1, 0, 0]}), "APPLY")
    def test_constraint(self):
        self._reject(P({"op": "spawn", "body": {"id": 9, "pos": [3, 5, 0], "vel": [0, 0, 0], "half": [1, 1, 1]}},
                       constraints={"max_bodies": 1}), "CONSTRAINT")

    def test_rejection_count(self):
        for p, g in [({"transition": {"op": "impulse", "id": 0, "dv": [0.5, 0, 0]}, "budget": {}}, "CANON"),
                     (P({"op": "teleport"}), "SCHEMA")]:
            M.propose(self.W, p, A, ledger=self.L)
        self.assertEqual(len(self.L.commits), 0)
        self.assertEqual(len(self.L.rejections), 2)


class TestCommit(unittest.TestCase):
    def test_commit_mutates_and_emits(self):
        W, L = world(), M.Ledger()
        r = M.propose(W, P({"op": "impulse", "id": 0, "dv": [2, 0, 0]}), A, ledger=L)
        self.assertTrue(r["ok"])
        self.assertNotEqual(A.state_hash(r["world"]), A.state_hash(W))   # candidate differs
        self.assertEqual(r["shard"]["post_hash"], A.state_hash(r["world"]))
        self.assertEqual(len(L.commits), 1)

    def test_commit_chain_and_determinism(self):
        def run():
            W, L = world(), M.Ledger()
            for dv in ([1, 0, 0], [0, 1, 0]):
                r = M.propose(W, P({"op": "impulse", "id": 0, "dv": dv}), A, ledger=L); W = r["world"]
            return [c["shard_hash"] for c in L.commits], L.commits[1]["prev"] == L.commits[0]["shard_hash"]
        a, chained = run(); b, _ = run()
        self.assertEqual(a, b)        # deterministic shard chain
        self.assertTrue(chained)      # commit N+1 links commit N


class TestIntentNotAuthority(unittest.TestCase):
    def test_wrong_claims_still_commit(self):
        # Wildly false claims (huge R_p) must NOT block a mechanically-valid transition.
        W, L = world(), M.Ledger()
        r = M.propose(W, P({"op": "impulse", "id": 0, "dv": [1, 0, 0]},
                           claims={"expect_body_count": 999, "expect_tick": 777}), A, ledger=L)
        self.assertTrue(r["ok"])                       # intent (claims) does NOT gate
        self.assertGreater(r["telemetry"]["R_p"], 0)   # but the mismatch IS measured (telemetry)

    def test_perfect_claims_still_rejected_on_constraint(self):
        # Perfectly truthful claims cannot rescue a mechanically-inadmissible transition.
        W, L = world(), M.Ledger()
        r = M.propose(W, P({"op": "spawn", "body": {"id": 5, "pos": [3, 5, 0], "vel": [0, 0, 0], "half": [1, 1, 1]}},
                           constraints={"max_bodies": 1}, claims={"expect_body_count": 2}), A, ledger=L)
        self.assertFalse(r["ok"]); self.assertEqual(r["gate"], "CONSTRAINT")

    def test_provenance_never_authorizes(self):
        # Same transition, different provenance ("admin" vs "anon") → identical mechanical outcome.
        W = world()
        r1 = M.propose(W, P({"op": "advance", "ticks": 3}, provenance={"who": "admin", "trust": "high"}), A)
        r2 = M.propose(W, P({"op": "advance", "ticks": 3}, provenance={"who": "anon", "trust": "none"}), A)
        self.assertEqual(r1["ok"], r2["ok"])
        self.assertEqual(r1["shard"]["post_hash"], r2["shard"]["post_hash"])


class TestTelemetryNotControl(unittest.TestCase):
    def test_Rp_is_telemetry_only(self):
        # R_p is recorded on commit and reject alike; it never changes the gate decision.
        W = world()
        committed = M.propose(W, P({"op": "impulse", "id": 0, "dv": [1, 0, 0]},
                                   claims={"expect_state_hash": "0" * 64}), A)
        self.assertTrue(committed["ok"])               # bogus expected hash (R_p>0) still commits
        self.assertEqual(committed["telemetry"]["R_p"], 1)


class TestWitnessReproduction(unittest.TestCase):
    def test_honest_witnesses_admit(self):
        W = world()
        honest = [lambda w, t: A.state_hash(A.apply(w, t)) for _ in range(3)]
        r = M.propose(W, P({"op": "impulse", "id": 0, "dv": [1, 0, 0]}), A, witnesses=honest, k=2)
        self.assertTrue(r["ok"])

    def test_divergent_witness_blocks(self):
        W = world()
        honest = lambda w, t: A.state_hash(A.apply(w, t))
        liar = lambda w, t: "f" * 64
        r = M.propose(W, P({"op": "impulse", "id": 0, "dv": [1, 0, 0]}), A, witnesses=[honest, liar, liar], k=3)
        self.assertFalse(r["ok"]); self.assertEqual(r["gate"], "WITNESS")


class TestGoalIsNotTransition(unittest.TestCase):
    def test_goal_rejected_at_schema(self):
        # The kernel only admits decomposed transitions; a raw GOAL is not in ALLOWED_OPS (intent ≠ authority).
        W = world()
        r = M.propose(W, P({"op": "goal", "desc": "make the box bounce forever"}), A)
        self.assertFalse(r["ok"]); self.assertEqual(r["gate"], "SCHEMA")




class TestAdapterContract(unittest.TestCase):
    def test_both_adapters_satisfy_contract(self):
        self.assertTrue(contract.validate_adapter(A))
        self.assertTrue(contract.validate_adapter(KV))

    def test_broken_adapter_rejected(self):
        class Broken:
            ALLOWED_OPS = ("x",)
            ApplyError = ValueError
            cost = staticmethod(lambda t: 1)
            # missing apply/delta_norm/state_hash/validate/residual
        with self.assertRaises(contract.ContractError):
            contract.validate_adapter(Broken)


class TestGeneralMembrane(unittest.TestCase):
    """The SAME membrane governs a non-physics (config/repo) reality."""
    def _kvp(self, txn, **kw):
        base = {"transition": txn, "budget": kw.pop("budget", {"max_cost": 5, "max_delta": 10**9})}
        base.update(kw)
        return base

    def test_kv_commit_and_frozen_reject(self):
        W, L = KV.empty_world(), M.Ledger()
        r = M.propose(W, self._kvp({"op": "set", "key": "replicas", "value": 3}), KV, ledger=L)
        self.assertTrue(r["ok"]); W = r["world"]
        r = M.propose(W, self._kvp({"op": "freeze", "key": "replicas"}), KV, ledger=L)
        self.assertTrue(r["ok"]); W = r["world"]
        r = M.propose(W, self._kvp({"op": "set", "key": "replicas", "value": 9}), KV, ledger=L)
        self.assertFalse(r["ok"]); self.assertEqual(r["gate"], "APPLY")    # frozen → inadmissible
        self.assertEqual(W["kv"]["replicas"], 3)                           # state unchanged on reject

    def test_kv_intent_not_authority(self):
        # False claims do not block a valid config change; true claims do not rescue a frozen write.
        W, L = KV.empty_world(), M.Ledger()
        r = M.propose(W, self._kvp({"op": "set", "key": "a", "value": 1},
                                   claims={"expect_key_count": 99}), KV, ledger=L)
        self.assertTrue(r["ok"]); self.assertEqual(r["telemetry"]["R_p"], 98)   # measured, not gated

    def test_kv_schema_rejects_unknown_op(self):
        r = M.propose(KV.empty_world(), self._kvp({"op": "deploy_to_prod"}), KV)
        self.assertFalse(r["ok"]); self.assertEqual(r["gate"], "SCHEMA")


class TestConformanceVectors(unittest.TestCase):
    def _seq(self):
        return [{"transition": {"op": "set", "key": "replicas", "value": 3}},
                {"transition": {"op": "bump", "key": "replicas", "by": 2}},
                {"transition": {"op": "freeze", "key": "replicas"}},
                {"transition": {"op": "set", "key": "replicas", "value": 9}},
                {"transition": {"op": "set", "key": "region", "value": "us-east"}}]

    def test_make_and_verify_roundtrip(self):
        v = CF.make_vector("kv", KV, KV.empty_world(), self._seq(),
                           budget={"max_cost": 5, "max_delta": 10**9}, constraints={"max_keys": 4})
        ok, detail = CF.verify_vector(v, KV)
        self.assertTrue(ok, detail)
        self.assertEqual(v["gates"], ["COMMIT", "COMMIT", "COMMIT", "APPLY", "COMMIT"])

    def test_tampered_vector_fails(self):
        v = CF.make_vector("kv", KV, KV.empty_world(), self._seq(),
                           budget={"max_cost": 5, "max_delta": 10**9}, constraints={"max_keys": 4})
        v["ledger_head"] = "0" * 64
        ok, _ = CF.verify_vector(v, KV)
        self.assertFalse(ok)

    def test_physics_vector_roundtrips_too(self):
        W = A.K.make_world([A.K.body(0, (0, 5, 0), (0, 0, 0), (1, 1, 1))], ((-10, -10, -10), (10, 10, 10)))
        seq = [{"transition": {"op": "impulse", "id": 0, "dv": [1, 0, 0]}},
               {"transition": {"op": "advance", "ticks": 3}}]
        v = CF.make_vector("phys", A, W, seq, budget={"max_cost": 10, "max_delta": 10**15})
        self.assertTrue(CF.verify_vector(v, A)[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
