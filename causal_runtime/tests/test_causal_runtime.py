"""causal_runtime/tests/test_causal_runtime.py — the causal-allocation substrate.

Covers: the dual-separated future-surface field, the pure AttentionField (no mutation surface), the Causal
Freshness Benchmark, and the CARDINAL INVARIANT against a real Aether application (AetherPulse): attaching the
observer leaves every committed hash bit-identical while still producing a non-trivial allocation."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import field as F
import runtime as R
import freshness as FR
import novelty as NV
import discovery as DV

S = F.SCALE


class TestField(unittest.TestCase):
    def test_uncertainty_breaks_consequence_tie(self):
        cons = {"a": 500, "b": 500}                          # equal raw consequence
        unc = {"a": S, "b": S // 4}                          # a more uncertain
        surf = F.future_surface(cons, unc)
        self.assertGreater(surf["a"], surf["b"])             # composite separates them

    def test_possibility_is_third_axis(self):
        cons = {"a": 100}; unc = {"a": S}
        full = F.future_surface(cons, unc, {"a": S})["a"]
        half = F.future_surface(cons, unc, {"a": S // 2})["a"]
        self.assertEqual(half, full // 2)                    # orthogonal & linear

    def test_hamilton_sums_to_budget(self):
        w = {"a": 7, "b": 3, "c": 1}
        alloc = F._hamilton(w, 100)
        self.assertEqual(sum(alloc.values()), 100)

    def test_depth_and_freshness_monotone(self):
        cons = {"hi": 1000, "lo": 1}; unc = {"hi": S, "lo": S}
        toks = F.attention_tokens(cons, unc, budget=50)
        self.assertGreaterEqual(toks["hi"].validation_depth, toks["lo"].validation_depth)
        self.assertLessEqual(toks["hi"].freshness, toks["lo"].freshness)   # hi surface -> refresh sooner

    def test_token_hash_deterministic(self):
        cons = {"a": 10}; unc = {"a": S}
        self.assertEqual(F.attention_tokens(cons, unc)["a"].h,
                         F.attention_tokens(cons, unc)["a"].h)


class TestAttentionField(unittest.TestCase):
    def test_allocation_sums_per_channel(self):
        af = R.AttentionField(budgets={"streaming": 50, "ai_tick": 30, "fidelity": 40,
                                       "network": 20, "validation": 10})
        af.observe({"a": 500, "b": 100, "c": 5}, {"a": S, "b": S, "c": S})
        al = af.allocation()
        self.assertEqual(sum(al["streaming"].values()), 50)
        self.assertEqual(sum(al["validation"].values()), 10)

    def test_no_mutation_surface(self):
        af = R.AttentionField()
        methods = [a for a in dir(af) if not a.startswith("_") and callable(getattr(af, a))]
        # the substrate exposes only read/observe/allocate verbs — nothing that writes a world
        self.assertNotIn("apply", methods); self.assertNotIn("commit", methods)
        self.assertNotIn("mutate", methods); self.assertNotIn("step", methods)

    def test_law_string(self):
        self.assertIn("FORBIDDEN", R.AttentionField.law())

    def test_frontier_orders_by_budget(self):
        af = R.AttentionField(budgets={"validation": 100})
        af.observe({"a": 900, "b": 90, "c": 9}, {"a": S, "b": S, "c": S})
        self.assertEqual(af.frontier("validation", 1), ["a"])


class TestCausalFreshness(unittest.TestCase):
    def test_aligned_is_negative_control(self):
        r = FR.reconstruct("aligned")
        self.assertLessEqual(abs(r["missed_visibility"] - r["missed_causal"]), 0.05)

    def test_causal_wins_on_hidden(self):
        r = FR.reconstruct("hidden")
        self.assertLess(r["missed_causal"], r["missed_visibility"] - 0.05)

    def test_verdict_and_determinism(self):
        v, _ = FR.verdict()
        self.assertEqual(v, "causal-freshness-wins-on-hidden-importance")
        self.assertEqual(FR.run(), FR.run())


class TestAetherInvariant(unittest.TestCase):
    """The cardinal invariant: observation cannot change the committed hash."""

    def setUp(self):
        import demo_aether_attention as D
        self.D = D

    def test_committed_hashes_identical_with_and_without_observer(self):
        r = self.D.run(ticks=24)
        self.assertTrue(r["identical_hashes"])               # the outcome hash cannot know the difference

    def test_attention_is_non_trivial(self):
        r = self.D.run(ticks=24)
        self.assertTrue(r["alloc_varies_across_bodies"])     # real signal, not a no-op
        self.assertTrue(r["alloc_varies_over_time"])

    def test_deterministic(self):
        self.assertEqual(self.D.run(ticks=16), self.D.run(ticks=16))


class TestNoveltyAndGhost(unittest.TestCase):
    def test_ghost_rectified_nonnegative(self):
        g = NV.ghost_field({"x": 10}, {"x": 10 ** 6})       # model OVER-predicted
        self.assertEqual(g["x"], 0)                          # surprise floor: never negative

    def test_hidden_coupling_spikes_ghost(self):
        # H changes most but consequence predicted 0 (undeclared) -> full ghost
        g = NV.ghost_field({"a": 100, "b": 80, "H": 1000}, {"a": 800, "b": 400, "H": 0})
        self.assertEqual(g["H"], F.SCALE)
        self.assertEqual(g["a"], 0)

    def test_aggregate_confidence_weighted(self):
        sigs = NV.ingest("dini", {"n": F.SCALE}, confidence=F.SCALE // 2)
        self.assertEqual(NV.aggregate(sigs)["n"], F.SCALE // 2)

    def test_attention_adds_ghost(self):
        cons = {"a": 800, "H": 0}
        base = NV.attention_field(cons)
        with_g = NV.attention_field(cons, ghost={"H": F.SCALE})
        self.assertGreater(with_g["H"], base["H"])           # surprise lifts a zero-consequence node

    def test_ghost_pulls_node_into_frontier(self):
        af = R.AttentionField(budgets={"validation": 2})
        cons = {"a": 800, "b": 400, "H": 0}
        af.observe(cons, {"a": F.SCALE, "b": F.SCALE, "H": F.SCALE})
        self.assertNotIn("H", af.frontier("validation", 2))
        af.observe(cons, {"a": F.SCALE, "b": F.SCALE, "H": F.SCALE},
                   ghost=NV.ghost_field({"a": 1, "b": 1, "H": 1000}, cons))
        self.assertIn("H", af.frontier("validation", 2))


class TestBlindDiscovery(unittest.TestCase):
    def test_ghost_discovers_hidden_anomaly(self):
        r = DV.discover("hidden")
        self.assertIsNone(r["latency"]["distance"])          # blind to low visibility
        self.assertIsNone(r["latency"]["consequence"])       # blind to undeclared coupling
        self.assertIsNotNone(r["latency"]["ghost"])          # surprise catches it

    def test_declared_is_negative_control(self):
        r = DV.discover("declared")
        self.assertTrue(all(v is not None for v in r["latency"].values()))  # all find a declared node

    def test_verdict_and_determinism(self):
        v, _ = DV.verdict()
        self.assertEqual(v, "ghost-discovers-the-undeclared-anomaly")
        self.assertEqual(DV.run(), DV.run())


class TestDiniProducerInvariant(unittest.TestCase):
    def setUp(self):
        import demo_dini_novelty as D
        self.D = D

    def test_cardinal_invariant_holds_with_dini(self):
        r = self.D.run(ticks=20)
        self.assertTrue(r["identical_hashes"])               # dini changes attention, not the hash

    def test_novelty_signal_nontrivial(self):
        r = self.D.run(ticks=20)
        self.assertTrue(r["novelty_grows"])

    def test_deterministic(self):
        self.assertEqual(self.D.run(ticks=14), self.D.run(ticks=14))


if __name__ == "__main__":
    unittest.main(verbosity=2)
