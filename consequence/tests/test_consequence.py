"""consequence/tests/test_consequence.py — the State-Graph Taint Map (consequence ≠ magnitude)."""
import os
import sys
import unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import graph as G

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
