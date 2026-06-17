"""Tests for stride cross-boundary state transport."""
import os, sys, copy, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import transport as T
import core
from court import verify_chain
from signing import HmacSigner
import demo_stride as D


class TestTransport(unittest.TestCase):
    def test_roundtrip_matching_env(self):
        env = core.state_hash({"a": "1"})
        buf = T.pack({"n": 3}, env)
        self.assertEqual(T.receive(buf, env), {"n": 3})

    def test_env_mismatch_refused(self):
        buf = T.pack({"n": 3}, core.state_hash({"a": "1"}))
        with self.assertRaises(T.EnvironmentMismatch):
            T.receive(buf, core.state_hash({"a": "DRIFT"}))

    def test_pack_is_deterministic(self):
        env = core.state_hash({"a": "1"})
        self.assertEqual(T.pack({"n": 3, "m": 4}, env), T.pack({"m": 4, "n": 3}, env))

    def test_telemetry_canonicalized(self):
        t = T.capture_link_telemetry(12.84, 3.1, 2, 7)
        self.assertEqual(t["latency_ms"], "12.84")   # float -> .12g string (captured observable)
        self.assertEqual(t["dropped"], 2)


class TestSealedMigration(unittest.TestCase):
    def _rec(self):
        return core.Recorder(HmacSigner(b"k"), core.ruleset_hash(D.migrate_logic, D.transport_invariant))

    def test_migration_replays(self):
        sealed = {"state": {"n": 5, "acc": 0}, "_cap": {"link": T.capture_link_telemetry(1, 0, 0, 1)}}
        r = self._rec().record("M", sealed, D.migrate_logic(sealed), D.transport_invariant)
        self.assertTrue(verify_chain([r], b"k", D.migrate_logic, D.transport_invariant).ok)

    def test_tamper_caught(self):
        sealed = {"state": {"n": 5, "acc": 0}, "_cap": {"link": T.capture_link_telemetry(1, 0, 0, 1)}}
        r = self._rec().record("M", sealed, D.migrate_logic(sealed), D.transport_invariant)
        bad = copy.deepcopy([r]); bad[0]["frame"]["inputs"]["state"]["n"] = 99
        self.assertFalse(verify_chain(bad, b"k", D.migrate_logic, D.transport_invariant).ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
