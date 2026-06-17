"""Tests for the dini hyperbolic novelty compass."""
import os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import compass as D
import core
from court import verify_chain
from signing import HmacSigner
import demo_dini as DEMO


def _chain(names, edge=1.0):
    m = D.HyperbolicMap(edge_length=edge); root = {"p": [0]}; m.set_root(root)
    s = root; obs = []
    for n in names:
        nxt = {"p": s["p"] + [n]}; obs.append(m.observe(s, nxt)); s = nxt
    return m, obs


class TestEmbedding(unittest.TestCase):
    def test_root_distance_zero(self):
        m = D.HyperbolicMap(); o = m.set_root({"p": [0]}); self.assertEqual(o["dini_distance"], 0.0)

    def test_chain_distance_monotonic(self):
        _, obs = _chain([1, 2, 3, 4])
        d = [o["dini_distance"] for o in obs]
        self.assertEqual(d, sorted(d))
        self.assertTrue(all(d[i] < d[i + 1] for i in range(len(d) - 1)))

    def test_depth_exact(self):
        _, obs = _chain([1, 2, 3])
        self.assertEqual([o["depth"] for o in obs], [1, 2, 3])

    def test_novelty_then_revisit(self):
        m = D.HyperbolicMap(); root = {"p": [0]}; m.set_root(root)
        a = m.observe(root, {"p": [0, 1]}); b = m.observe(root, {"p": [0, 1]})
        self.assertTrue(a["novelty"]); self.assertFalse(b["novelty"])
        self.assertEqual(a["dini_distance"], b["dini_distance"])   # same state -> same reading

    def test_branches_separate(self):
        m = D.HyperbolicMap(); root = {"p": [0]}; m.set_root(root)
        x = {"p": [0, "x"]}; y = {"p": [0, "y"]}
        m.observe(root, x); m.observe(root, y)
        self.assertGreater(m.distance_between(x, y), 0.0)

    def test_coords_inside_disk(self):
        m, _ = _chain([1, 2, 3, 4, 5])
        for z in m.coord.values():
            self.assertLess(abs(z), 1.0)

    def test_deterministic(self):
        _, a = _chain([1, 2, 3]); _, b = _chain([1, 2, 3])
        self.assertEqual([o["dini_distance"] for o in a], [o["dini_distance"] for o in b])

    def test_anomaly_threshold(self):
        _, obs = _chain([1, 2, 3, 4, 5, 6, 7])
        self.assertFalse(D.anomaly(obs[0], 6.0))
        self.assertTrue(D.anomaly(obs[-1], 6.0))


class TestSensorIsCapturedNotGate(unittest.TestCase):
    def test_sealed_loop_replays(self):
        rec = core.Recorder(HmacSigner(b"k"), core.ruleset_hash(DEMO.agent_logic, DEMO.no_gate))
        m = D.HyperbolicMap(); root = {"path": ["repo"]}; m.set_root(root)
        ledger = []; s = root
        for i, c in enumerate(["engine", "kernel"]):
            nxt = DEMO.descend(s, c); obs = m.observe(s, nxt)
            sealed = {"path": nxt["path"], "_cap": {"dini_distance": obs["dini_distance"], "depth": obs["depth"]}}
            ledger.append(rec.record("N%d" % i, sealed, DEMO.agent_logic(sealed), DEMO.no_gate)); s = nxt
        self.assertTrue(verify_chain(ledger, b"k", DEMO.agent_logic, DEMO.no_gate).ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
