"""Tests for the glitch deterministic state-space explorer."""
import os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import explorer as G
import core
from court import verify_chain
from signing import HmacSigner
import demo_glitch as D


class TestExplore(unittest.TestCase):
    def test_finds_the_bug(self):
        r = G.explore(D.INITIAL, D.EVENTS, D.step, D.invariant, max_depth=4)
        self.assertTrue(r.found)
        self.assertEqual([e["op"] for e in r.path], ["discount", "discount", "purchase"])

    def test_deterministic(self):
        a = G.explore(D.INITIAL, D.EVENTS, D.step, D.invariant, max_depth=4).path
        b = G.explore(D.INITIAL, D.EVENTS, D.step, D.invariant, max_depth=4).path
        self.assertEqual(a, b)

    def test_dedup_prunes(self):
        r = G.explore(D.INITIAL, D.EVENTS, D.step, D.invariant, max_depth=4)
        self.assertLessEqual(r.distinct_states, r.states_explored)   # dedup never inflates the frontier

    def test_fixed_system_has_no_counterexample_in_depth(self):
        r = G.explore(D.INITIAL, D.EVENTS, D.fixed_step, D.invariant, max_depth=4)
        self.assertFalse(r.found)


class TestShrink(unittest.TestCase):
    def test_minimal_and_still_fails(self):
        r = G.explore(D.INITIAL, D.EVENTS, D.step, D.invariant, max_depth=4)
        m = G.shrink(D.INITIAL, r.path, D.step, D.invariant)
        self.assertTrue(G._still_fails(D.INITIAL, m, D.step, D.invariant))
        # minimality: dropping any single event must stop the failure
        for i in range(len(m)):
            self.assertFalse(G._still_fails(D.INITIAL, m[:i] + m[i + 1:], D.step, D.invariant))


class TestSealAndReplay(unittest.TestCase):
    def test_seal_refuses_breaking_step_and_prefix_replays(self):
        r = G.explore(D.INITIAL, D.EVENTS, D.step, D.invariant, max_depth=4)
        m = G.shrink(D.INITIAL, r.path, D.step, D.invariant)
        ledger, refused, logic, gate = G.seal_counterexample(D.INITIAL, m, D.step, D.invariant, HmacSigner(b"k"))
        self.assertEqual(refused["op"], "purchase")          # fail-closed at the exact breaking step
        self.assertTrue(verify_chain(ledger, b"k", logic, gate).ok)
        self.assertEqual(len(ledger), len(m) - 1)            # only the valid prefix sealed


if __name__ == "__main__":
    unittest.main(verbosity=2)
