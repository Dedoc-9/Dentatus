"""Tests for the anti_cheat sibling: pinned visibility, fail-closed occlusion gate, culling, replay/tamper."""
import os, sys, copy, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import match_forensics as MF
import core
from court import verify_chain
from signing import Ed25519Signer, Ed25519Verifier, HmacSigner

MAP = {"Spawn": ["Courtyard"], "Courtyard": ["B-Site"]}


def _mf():
    return MF.MatchForensics(MAP, HmacSigner(b"k"))


class TestVisibility(unittest.TestCase):
    def setUp(self): MF.configure_map(MAP)

    def test_symmetric_closure(self):
        self.assertTrue(MF.visible("Spawn", "Courtyard"))
        self.assertTrue(MF.visible("Courtyard", "Spawn"))      # mutual
        self.assertTrue(MF.visible("Spawn", "Spawn"))          # self

    def test_occlusion(self):
        self.assertFalse(MF.visible("Spawn", "B-Site"))

    def test_culling_drops_occluded(self):
        enemies = [{"id": "E1", "sector": "Courtyard"}, {"id": "E2", "sector": "B-Site"}]
        self.assertEqual([e["id"] for e in MF.visible_enemies("Spawn", enemies)], ["E1"])


class TestGatedLedger(unittest.TestCase):
    def test_legit_seals_and_replays(self):
        mf = _mf()
        r = mf.record_tick("T1", "Courtyard", "Courtyard", True, 35)
        self.assertTrue(verify_chain([r], b"k", MF.server_resolve, MF.hit_invariant).ok)

    def test_wallbang_refused(self):
        mf = _mf()
        with self.assertRaises(core.InvariantViolation):
            mf.record_tick("T2", "Spawn", "B-Site", True, 100)

    def test_miss_through_wall_is_fine(self):
        mf = _mf()  # a non-hit across occlusion is not an impossibility; it may seal
        r = mf.record_tick("T3", "Spawn", "B-Site", claimed_hit=False, claimed_damage=0)
        self.assertTrue(verify_chain([r], b"k", MF.server_resolve, MF.hit_invariant).ok)

    def test_tamper_caught(self):
        mf = _mf()
        r = mf.record_tick("T1", "Courtyard", "Courtyard", True, 35)
        bad = copy.deepcopy([r]); bad[0]["frame"]["inputs"]["enemy_sector"] = "B-Site"
        self.assertFalse(verify_chain(bad, b"k", MF.server_resolve, MF.hit_invariant).ok)

    def test_replay_deterministic(self):
        mf = _mf()
        inp = {"player_sector": "Courtyard", "enemy_sector": "Courtyard",
               "claimed_hit": True, "claimed_damage": 35, "aim_angle": 1.0}
        self.assertEqual(core.canonical_bytes(MF.server_resolve(inp)),
                         core.canonical_bytes(MF.server_resolve(inp)))


@unittest.skipUnless(__import__("signing").ed25519_available(), "cryptography unavailable")
class TestThirdPartyVerify(unittest.TestCase):
    def test_public_key_verifies_league_audit(self):
        s = Ed25519Signer.generate()
        mf = MF.MatchForensics(MAP, s)
        r = mf.record_tick("T1", "Courtyard", "Courtyard", True, 35)
        self.assertTrue(verify_chain([r], Ed25519Verifier(s.public_material()),
                                     MF.server_resolve, MF.hit_invariant).ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
