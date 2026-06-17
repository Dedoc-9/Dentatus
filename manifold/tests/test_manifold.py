"""Tests for NGGV manifold_core + topology-gated commits on the frozen Chronicle workbench."""
import os, sys, copy, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import manifold_core as M
import core as C
from core import Recorder, ruleset_hash, InvariantViolation
from court import verify_chain
from signing import HmacSigner
import demo_manifold as D


class TestTopology(unittest.TestCase):
    def test_world_hash_is_order_invariant(self):
        e = [(0, 1), (1, 2), (2, 0)]
        self.assertEqual(M.world_hash(3, e), M.world_hash(3, list(reversed(e))))

    def test_world_hash_changes_with_topology(self):
        self.assertNotEqual(M.world_hash(3, [(0, 1), (1, 2)]), M.world_hash(3, [(0, 1), (1, 2), (2, 0)]))

    def test_connectivity_exact(self):
        self.assertTrue(M.is_connected(4, [(0, 1), (1, 2), (2, 3)]))
        self.assertFalse(M.is_connected(4, [(0, 1), (2, 3)]))

    def test_bridges_exact(self):
        self.assertEqual(M.bridges(4, [(0, 1), (1, 2), (2, 3)]), [(0, 1), (1, 2), (2, 3)])
        self.assertEqual(M.bridges(3, [(0, 1), (1, 2), (2, 0)]), [])   # cycle has no bridges

    def test_lambda2_zero_on_disconnection(self):
        if M.fiedler_value(4, [(0, 1), (1, 2), (2, 3)]) is None:
            self.skipTest("numpy unavailable")
        self.assertEqual(M.fiedler_value(4, [(0, 1), (2, 3)]), 0.0)
        self.assertGreater(M.fiedler_value(4, [(0, 1), (1, 2), (2, 3)]), 0.0)


class TestGatedLedger(unittest.TestCase):
    def setUp(self):
        self.ruleset = ruleset_hash(D.manifold_transition, D.topology_gate)

    def _commit(self, edges):
        rec = Recorder(HmacSigner(b"k"), self.ruleset)
        sealed = D.seal(D.N, edges)
        return rec, rec.record("T", sealed, D.manifold_transition(sealed), D.topology_gate)

    def test_connected_commits_and_replays(self):
        rec, r = self._commit(D.BASE_EDGES)
        self.assertTrue(verify_chain([r], b"k", D.manifold_transition, D.topology_gate).ok)

    def test_bisection_refused(self):
        bis = [e for e in D.BASE_EDGES if tuple(sorted(e)) != (2, 3)]
        with self.assertRaises(InvariantViolation):
            self._commit(bis)

    def test_tamper_caught(self):
        rec, r = self._commit(D.BASE_EDGES)
        bad = copy.deepcopy([r]); bad[0]["frame"]["inputs"]["edges"].append([0, 5])
        self.assertFalse(verify_chain(bad, b"k", D.manifold_transition, D.topology_gate).ok)

    def test_replay_is_deterministic_without_numpy(self):
        # transition reads captured lambda2; recomputing must match (no eigensolver on replay path)
        sealed = D.seal(D.N, D.BASE_EDGES)
        a = C.canonical_bytes(D.manifold_transition(sealed))
        b = C.canonical_bytes(D.manifold_transition(sealed))
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main(verbosity=2)
