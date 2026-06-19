"""consequence/tests/test_consequence.py — the State-Graph Taint Map (consequence ≠ magnitude)."""
import os
import sys
import unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import graph as G
import butterfly as BF
import extractor as EX
import propagation as PR
import fingerprint as FP
import cache as CA
import reconstruct as RC

S = G.SCALE


def _hub_leaf():
    g = G.Graph()
    for dep in ("a", "b", "c", "d"):
        g.add_edge("hub", dep, int(0.9 * S)); g.add_edge(dep, "sink", int(0.7 * S))
    g.add_edge("leaf", "tiny", int(0.2 * S))
    return g


class TestDependencyMass(unittest.TestCase):
    def test_hub_exceeds_leaf(self):
        g = _hub_leaf()
        self.assertGreater(G.dependency_mass(g, "hub"), G.dependency_mass(g, "leaf"))

    def test_deterministic(self):
        g = _hub_leaf()
        self.assertEqual(G.dependency_mass(g, "hub"), G.dependency_mass(g, "hub"))

    def test_cycle_terminates(self):
        g = G.Graph().add_edge("x", "y", S).add_edge("y", "x", S)   # a cycle
        self.assertGreater(G.dependency_mass(g, "x", depth=6), 0)    # decay+depth bound it; no hang


class TestConsequenceNotMagnitude(unittest.TestCase):
    def test_same_magnitude_differs_by_position(self):
        g = _hub_leaf()
        self.assertGreater(G.consequence(g, "hub", 1 * S), G.consequence(g, "leaf", 1 * S))

    def test_butterfly_small_at_hub_beats_large_at_leaf(self):
        g = _hub_leaf()
        self.assertGreater(G.consequence(g, "hub", 1 * S), G.consequence(g, "leaf", 10 * S))

    def test_consequence_scales_with_magnitude(self):
        g = _hub_leaf()
        self.assertEqual(G.consequence(g, "hub", 2 * S), 2 * G.consequence(g, "hub", 1 * S))


class TestFieldAndTaint(unittest.TestCase):
    def test_field_is_per_node(self):
        g = _hub_leaf()
        cf = G.field(g, {"hub": 1 * S, "leaf": 1 * S})
        self.assertEqual(set(cf), g.nodes)
        self.assertGreater(cf["hub"], cf["leaf"])

    def test_taint_spreads_downstream(self):
        g = _hub_leaf()
        t = G.taint(g, {"hub": 10 * S})
        self.assertGreater(t["a"], 0)        # hub taints its dependents
        self.assertEqual(t.get("leaf", 0), 0)  # an unrelated leaf is untainted




class TestButterflyBenchmark(unittest.TestCase):
    def test_flat_world_ties_at_budget_fraction(self):
        r = BF.run(n=200, seed=3, budget_frac=0.1)
        for sch in ("distance", "visibility", "consequence"):
            self.assertAlmostEqual(r["flat"][sch], 0.1, places=6)   # nothing to find ⇒ all = budget frac

    def test_chained_world_consequence_dominates(self):
        r = BF.run(n=200, seed=3)
        self.assertGreater(r["chained"]["consequence"], 1.5 * r["chained"]["distance"])
        self.assertGreater(r["chained"]["consequence"], 1.5 * r["chained"]["visibility"])

    def test_verdict_and_determinism(self):
        r1 = BF.run(seed=3); r2 = BF.run(seed=3)
        self.assertEqual(r1["verdict"], "consequence-wins-on-structure")
        self.assertEqual(r1, r2)                                     # deterministic given seed


class TestExtractor(unittest.TestCase):
    def test_pure_diff_and_magnitudes(self):
        ch, mg = EX.extract({"a": 10, "b": 5, "c": 3}, {"a": 10, "b": 9, "d": 1})
        self.assertEqual(sorted(ch), ["b", "c", "d"])
        self.assertEqual(mg["b"], 4)                       # numeric delta
        self.assertEqual(mg["c"], S)                        # disappear = full structural change
        self.assertEqual(mg["d"], S)                        # appear   = full structural change

    def test_no_change_empty(self):
        ch, mg = EX.extract({"a": 1}, {"a": 1})
        self.assertEqual(ch, frozenset()); self.assertEqual(mg, {})

    def test_float_refused(self):
        with self.assertRaises(TypeError):
            EX.delta_magnitude(1, 2.0)


class TestPropagation(unittest.TestCase):
    def _chain(self):
        g = G.Graph()
        for u, v in [("h", "a"), ("a", "b"), ("b", "c")]:
            g.add_edge(u, v, S)
        g.add_node("z")
        return g

    def test_frontier_reaches_downstream(self):
        g = self._chain()
        F = PR.frontier(g, frozenset(["h"]), {"h": S})
        self.assertEqual(set(F), {"h", "a", "b", "c"})

    def test_isolated_node_alone(self):
        g = self._chain()
        F = PR.frontier(g, frozenset(["z"]), {"z": S})
        self.assertEqual(set(F), {"z"})

    def test_merge_matches_chain_values(self):
        g = self._chain()
        r = PR.reached(g, {"h": S})
        self.assertGreater(r["a"], r["b"]); self.assertGreater(r["b"], r["c"])  # monotone decay


class TestFingerprint(unittest.TestCase):
    def _g(self):
        g = G.Graph()
        for u, v in [("h", "a"), ("a", "b"), ("b", "c")]:
            g.add_edge(u, v, S)
        g.add_node("leaf")
        return g

    def test_hub_exceeds_leaf(self):
        g = self._g()
        th = FP.fingerprint(g, "h", 1000); tl = FP.fingerprint(g, "leaf", 1000)
        self.assertGreater(th.score, tl.score)

    def test_uncertainty_scales_linearly(self):
        g = self._g()
        full = FP.fingerprint(g, "h", 1000, uncertainty=S).score
        half = FP.fingerprint(g, "h", 1000, uncertainty=S // 2).score
        self.assertEqual(half, full // 2)                   # epistemic axis is orthogonal & linear

    def test_hash_deterministic(self):
        g = self._g()
        a = FP.fingerprint(g, "h", 1000, now=0, ttl=240, reachable_dependents=4)
        b = FP.fingerprint(g, "h", 1000, now=0, ttl=240, reachable_dependents=4)
        self.assertEqual(a.h, b.h)

    def test_float_refused(self):
        g = self._g()
        with self.assertRaises(TypeError):
            FP.fingerprint(g, "h", 1.0)


class TestCache(unittest.TestCase):
    def _seed(self, cap):
        g = G.Graph()
        for u, v in [("h", "a"), ("a", "b"), ("b", "c")]:
            g.add_edge(u, v, S)
        for n in ["leaf1", "leaf2"]:
            g.add_node(n)
        c = CA.ConsequenceCache(capacity=cap)
        for n in ["h", "a", "b", "c", "leaf1", "leaf2"]:
            c.put(FP.fingerprint(g, n, 1000, now=0, ttl=10))
        return c

    def test_capacity_keeps_top_scores(self):
        c = self._seed(3)
        self.assertEqual(len(c), 3)
        self.assertEqual(c.frontier(3), ["h", "a", "b"])    # leaves (score 0) evicted

    def test_tick_drops_expired(self):
        c = self._seed(8)
        self.assertEqual(c.tick(20), 6)                     # all 6 expire at 10
        self.assertEqual(len(c), 0)


class TestCausalReconstruction(unittest.TestCase):
    def test_flat_is_negative_control(self):
        r = RC.reconstruct(RC.flat_world(), steps=24)
        self.assertLess(r["compute_saved"], 0.10)           # dense world: nothing to skip
        self.assertGreaterEqual(r["divergence_preserved"], 0.99)

    def test_chained_saves_and_preserves(self):
        r = RC.reconstruct(RC.chained_world(), steps=24)
        self.assertGreater(r["compute_saved"], 0.5)
        self.assertGreaterEqual(r["divergence_preserved"], 0.99)

    def test_declared_trigger_is_caught(self):
        r = RC.reconstruct(RC.trigger_world(), steps=24)
        self.assertGreaterEqual(r["divergence_preserved"], 0.99)  # per-step re-extraction catches it

    def test_hidden_coupling_breaks_reconstruction(self):
        r = RC.reconstruct(RC.hidden_trigger_world(), steps=24)
        self.assertLess(r["divergence_preserved"], 0.9)     # THE BOUND: undeclared coupling is missed

    def test_verdict_and_determinism(self):
        tag, overall = RC.verdict()
        self.assertEqual(overall, "reconstruction-valid-with-declared-bound")
        self.assertTrue(tag["hidden"].startswith("BOUND"))
        self.assertEqual(RC.run(), RC.run())                # deterministic


if __name__ == "__main__":
    unittest.main(verbosity=2)
