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
import admissibility as AD
import possibility as PS
import horizon as HZ
import membrane as M
import impact as IM

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




class TestSeverityLadder(unittest.TestCase):
    """Severity toggles validator DEPTH, never the kernel. game = fast (strict deferred); strict = inline
    causal gate; audit = offline physics court that flags a lower-severity commit."""
    def _world(self):
        return A.K.make_world([A.K.body(0, (0, 5, 0), (0, 0, 0), (1, 1, 1))],
                              ((-1000, -1000, -1000), (1000, 1000, 1000)))
    def _superluminal(self, c=5 * (1 << 32)):
        return {"transition": {"op": "impulse", "id": 0, "dv": [99, 0, 0]},
                "budget": {"max_cost": 5, "max_delta": 10**22}, "constraints": {"max_bodies": 4, "c_limit": c}}

    def test_game_commits_and_defers_strict(self):
        W = self._world()
        r = M.propose(W, self._superluminal(), A, severity="game")
        self.assertTrue(r["ok"])                                   # fast path admits it
        self.assertIn("validate_strict", r["telemetry"]["deferred"])
        self.assertEqual(r["shard"]["severity"], "game")          # severity is declared + hashed in the shard

    def test_strict_blocks_causal_violation(self):
        r = M.propose(self._world(), self._superluminal(), A, severity="strict")
        self.assertFalse(r["ok"]); self.assertEqual(r["gate"], "STRICT")

    def test_audit_flags_lower_severity_commit(self):
        W = self._world(); p = self._superluminal()
        committed = M.propose(W, p, A, severity="game")           # committed at game speed
        v = M.audit(W, p["transition"], A, constraints=p["constraints"], commit_hash=committed["shard"]["shard_hash"])
        self.assertEqual(v["verdict"], "FLAG")                    # physics court flags it offline...
        self.assertEqual(v["commit_hash"], committed["shard"]["shard_hash"])  # ...referencing, not mutating

    def test_severity_does_not_change_the_kernel(self):
        # A LAWFUL transition produces the IDENTICAL committed world at game and strict — severity changes
        # admissibility, never the deterministic kernel output.
        lawful = {"transition": {"op": "impulse", "id": 0, "dv": [2, 0, 0]},
                  "budget": {"max_cost": 5, "max_delta": 10**22}, "constraints": {"max_bodies": 4, "c_limit": 5 * (1 << 32)}}
        rg = M.propose(self._world(), dict(lawful), A, severity="game")
        rs = M.propose(self._world(), dict(lawful), A, severity="strict")
        self.assertTrue(rg["ok"] and rs["ok"])
        self.assertEqual(rg["shard"]["post_hash"], rs["shard"]["post_hash"])

    def test_severity_applies_to_kv_reality(self):
        cons = {"max_keys": 8, "forbid_substr": "secret"}
        p = {"transition": {"op": "set", "key": "db_secret", "value": "x"},
             "budget": {"max_cost": 5, "max_delta": 10**9}, "constraints": cons}
        self.assertTrue(M.propose(KV.empty_world(), dict(p), KV, severity="game")["ok"])      # game allows
        self.assertFalse(M.propose(KV.empty_world(), dict(p), KV, severity="strict")["ok"])   # strict policy blocks




class TestMultiFidelity(unittest.TestCase):
    """Severity as a POLICY (world,txn)->tier: ONE world audited at different depth per region.
    Proves fidelity (where you look) is independent of integrity (how hard you check)."""
    def _world(self):
        S = 1 << 32
        return A.K.make_world([A.K.body(0, (0, 0, 0), (0, 0, 0), (1, 1, 1)),        # near origin → strict
                               A.K.body(1, (500, 0, 0), (0, 0, 0), (1, 1, 1))],     # far field   → game
                              ((-10000, -10000, -10000), (10000, 10000, 10000)))

    def _policy(self):
        S = 1 << 32; R = 20 * S
        def pol(world, txn):
            bid = txn.get("id")
            b = next((x for x in world["bodies"] if x["id"] == bid), None)
            if b is None:
                return "game"
            return "strict" if sum(c * c for c in b["pos"]) <= R * R else "game"
        return pol

    def _boom(self, bid):
        S = 1 << 32
        return {"transition": {"op": "impulse", "id": bid, "dv": [99, 0, 0]},
                "budget": {"max_cost": 5, "max_delta": 10**22},
                "constraints": {"max_bodies": 8, "c_limit": 5 * S}}

    def test_near_strict_far_game_same_world(self):
        W, pol = self._world(), self._policy()
        rn = M.propose(W, self._boom(0), A, severity=pol)   # near → strict → causal block
        rf = M.propose(W, self._boom(1), A, severity=pol)   # far  → game  → cheap admit
        self.assertFalse(rn["ok"]); self.assertEqual(rn["gate"], "STRICT")
        self.assertEqual(rn["telemetry"]["severity"], "strict")   # severity recorded even on reject
        self.assertTrue(rf["ok"]); self.assertEqual(rf["telemetry"]["severity"], "game")

    def test_policy_callable_resolves_per_proposal(self):
        # a constant-callable behaves like the fixed string
        W = self._world()
        r = M.propose(W, self._boom(1), A, severity=lambda w, t: "game")
        self.assertTrue(r["ok"]); self.assertEqual(r["telemetry"]["severity"], "game")




class TestAdmissibilityGeometry(unittest.TestCase):
    """The membrane records what ALMOST happened; admissibility.geometry makes it a first-class observable."""
    def _session(self):
        W = world(); L = M.Ledger()
        props = [{"op": "impulse", "id": 0, "dv": [1, 0, 0]},                         # COMMIT
                 {"op": "impulse", "id": 0, "dv": [0.5, 0, 0]},                       # CANON
                 {"op": "teleport"},                                                  # SCHEMA
                 {"op": "advance", "ticks": 2},                                       # COMMIT
                 {"op": "impulse", "id": 99, "dv": [1, 0, 0]}]                        # APPLY
        for t in props:
            M.propose(W, {"transition": t, "budget": {"max_cost": 5, "max_delta": 10**18},
                          "constraints": {"max_bodies": 4}}, A, ledger=L)
        return L

    def test_counts_and_pressure(self):
        g = AD.geometry(self._session())
        self.assertEqual((g["realized"], g["unrealized"], g["proposed"]), (2, 3, 5))
        self.assertEqual(g["admissibility_permille"] + g["proposal_pressure_permille"], 1000)
        self.assertEqual(sum(g["gate_histogram"].values()), 3)        # the shape of the filter
        self.assertIn(g["dominant_gate"], g["gate_histogram"])

    def test_pure_does_not_mutate_ledger(self):
        L = self._session()
        nc, nr = len(L.commits), len(L.rejections)
        AD.geometry(L); AD.geometry(L)
        self.assertEqual((len(L.commits), len(L.rejections)), (nc, nr))   # observation never mutates

    def test_merge_aggregates(self):
        g = AD.geometry(self._session())
        m = AD.merge(g, g)
        self.assertEqual(m["realized"], 2 * g["realized"])
        self.assertEqual(m["unrealized"], 2 * g["unrealized"])

    def test_empty_ledger(self):
        g = AD.geometry(M.Ledger())
        self.assertEqual(g["proposed"], 0)
        self.assertIsNone(g["admissibility_permille"])




class TestPossibilitySpace(unittest.TestCase):
    """possible ⊋ admissible ⊋ realized — measure the lawful freedom (the 'arbitrary' set) at a state."""
    def _candidates(self):
        B = {"budget": {"max_cost": 5, "max_delta": 10**18}, "constraints": {"max_bodies": 2}}
        return [
            {"transition": {"op": "impulse", "id": 0, "dv": [1, 0, 0]}, **B},      # admissible
            {"transition": {"op": "impulse", "id": 0, "dv": [0, 1, 0]}, **B},      # admissible
            {"transition": {"op": "advance", "ticks": 3}, **B},                    # admissible
            {"transition": {"op": "impulse", "id": 0, "dv": [0.5, 0, 0]}, **B},    # CANON (inadmissible)
            {"transition": {"op": "teleport"}, **B},                               # SCHEMA (inadmissible)
        ]

    def test_admissible_classification_and_freedom(self):
        W = world()
        g = PS.admissible_set(W, self._candidates(), A)
        self.assertEqual(g["candidates"], 5)
        self.assertEqual(g["admissible"], [0, 1, 2])
        self.assertEqual(g["inadmissible"], {3: "CANON", 4: "SCHEMA"})
        self.assertEqual(g["freedom_permille"], 600)        # 3 lawful of 5 proposed

    def test_shadow_evaluation_is_pure(self):
        W = world(); h0 = A.state_hash(W)
        PS.admissible_set(W, self._candidates(), A)
        self.assertEqual(A.state_hash(W), h0)               # evaluating possibility never mutates reality

    def test_unrealized_admissible_remainder(self):
        W = world()
        g = PS.admissible_set(W, self._candidates(), A)
        self.assertEqual(PS.unrealized_admissible(g, chosen=0), [1, 2])   # lawful, not chosen
        self.assertEqual(PS.unrealized_admissible(g, chosen=None), [0, 1, 2])

    def test_empty(self):
        self.assertIsNone(PS.admissible_set(world(), [], A)["freedom_permille"])




class TestPossibilityNeighborhood(unittest.TestCase):
    """The geometry of the field of unrealized admissible alternatives around a realized state."""
    def _W(self):
        return A.K.make_world([A.K.body(0, (0, 5, 0), (0, 0, 0), (1, 1, 1))], ((-100, -100, -100), (100, 100, 100)))
    def _B(self):
        return {"budget": {"max_cost": 9, "max_delta": 10**18}, "constraints": {"max_bodies": 3}}

    def test_pressure_reach_and_purity(self):
        B = self._B(); W = self._W(); h0 = A.state_hash(W)
        cands = [{"transition": {"op": "impulse", "id": 0, "dv": [1, 0, 0]}, **B},
                 {"transition": {"op": "impulse", "id": 0, "dv": [40, 0, 0]}, **B},
                 {"transition": {"op": "advance", "ticks": 8}, **B}]
        g = HZ.neighborhood(W, 0, cands, A)
        self.assertEqual(g["alternatives"], 2)
        self.assertEqual(g["possibility_pressure"], sum(g["distances"].values()))
        self.assertEqual(g["reach"], max(g["distances"].values()))
        self.assertEqual(A.state_hash(W), h0)                  # shadow: reality untouched

    def test_alive_exceeds_tight(self):
        B = self._B(); W = self._W()
        alive = [{"transition": {"op": "impulse", "id": 0, "dv": [1, 0, 0]}, **B},
                 {"transition": {"op": "impulse", "id": 0, "dv": [40, 0, 0]}, **B},
                 {"transition": {"op": "advance", "ticks": 8}, **B}]
        tight = [{"transition": {"op": "impulse", "id": 0, "dv": [1, 0, 0]}, **B},
                 {"transition": {"op": "impulse", "id": 0, "dv": [2, 0, 0]}, **B}]
        self.assertGreater(HZ.neighborhood(W, 0, alive, A)["possibility_pressure"],
                           HZ.neighborhood(W, 0, tight, A)["possibility_pressure"])

    def test_realized_must_be_admissible(self):
        B = self._B(); W = self._W()
        cands = [{"transition": {"op": "teleport"}, **B},                              # inadmissible
                 {"transition": {"op": "impulse", "id": 0, "dv": [1, 0, 0]}, **B}]
        with self.assertRaises(ValueError):
            HZ.neighborhood(W, 0, cands, A)                    # index 0 is not admissible

    def test_deterministic(self):
        B = self._B(); W = self._W()
        cands = [{"transition": {"op": "impulse", "id": 0, "dv": [1, 0, 0]}, **B},
                 {"transition": {"op": "advance", "ticks": 5}, **B}]
        self.assertEqual(HZ.neighborhood(W, 0, cands, A), HZ.neighborhood(W, 0, cands, A))




class TestImpactValidationDepth(unittest.TestCase):
    """impact_density → validation depth (ALLOWED) ; impact_density → committed outcome (FORBIDDEN)."""
    def _world(self):
        return A.K.make_world([A.K.body(i, (i - 2, 5, 0), (0, 0, 0), (1, 1, 1)) for i in range(4)],
                              ((-80, -80, -80), (80, 80, 80)))

    def test_cheap_predicts_true_ordering(self):
        W = self._world()
        big = {"op": "impulse", "id": 0, "dv": [60, 0, 0]}
        small = {"op": "impulse", "id": 0, "dv": [1, 0, 0]}
        self.assertGreater(IM.cheap_impact(W, big, A), IM.cheap_impact(W, small, A))
        self.assertGreater(IM.impact_density(W, big, A), IM.impact_density(W, small, A))

    def test_policy_routes_by_impact(self):
        W = self._world()
        pol = IM.bind(IM.validation_policy(5 * (1 << 32)), A)
        self.assertEqual(pol(W, {"op": "impulse", "id": 0, "dv": [1, 0, 0]}), "game")    # low → cheap
        self.assertEqual(pol(W, {"op": "impulse", "id": 0, "dv": [60, 0, 0]}), "strict")  # high → deep

    def test_validation_depth_never_changes_outcome(self):
        # THE LAW: a transition committed at any depth (game / strict / impact-policy) yields the SAME state.
        W = self._world()
        pol = IM.bind(IM.validation_policy(5 * (1 << 32)), A)
        p = {"transition": {"op": "impulse", "id": 0, "dv": [1, 0, 0]},
             "budget": {"max_cost": 5, "max_delta": 10**22}, "constraints": {"max_bodies": 8, "c_limit": 200 * (1 << 32)}}
        hg = M.propose(W, dict(p), A, severity="game")["shard"]["post_hash"]
        hs = M.propose(W, dict(p), A, severity="strict")["shard"]["post_hash"]
        hp = M.propose(W, dict(p), A, severity=pol)["shard"]["post_hash"]
        self.assertEqual(hg, hs); self.assertEqual(hs, hp)


if __name__ == "__main__":
    unittest.main(verbosity=2)
