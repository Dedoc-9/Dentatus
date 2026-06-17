"""tessera/tests/test_tessera.py — portable replayable shards: mint/verify, tamper, divergence, lineage."""
import os, sys, unittest
_T = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WB = os.path.dirname(_T)
sys.path.insert(0, _T)
sys.path.insert(0, os.path.join(_WB, "syracuse"))
sys.path.insert(0, os.path.join(_WB, "chronicle"))
import shard as T
import orbit as SY
from signing import Ed25519Signer, ed25519_available


def rule(state):
    return {"n": SY.step(state["n"])}


def done(state):
    return state["n"] == 1


def rule_uncompressed(state):
    return {"n": SY.step(state["n"], compressed=False)}


class MintVerify(unittest.TestCase):
    def test_mint_then_replay(self):
        t = T.mint(rule, done, {"n": 27})
        self.assertEqual(t["steps"], 70); self.assertEqual(t["terminus"], {"n": 1})
        self.assertEqual(T.verify(t, rule, done), (True, "VERIFIED"))

    def test_replay_is_producer_independent(self):
        # a verifier reconstructs everything from seed + rule; the shard carries no path
        t = T.mint(rule, done, {"n": 97})
        self.assertNotIn("path", t)
        self.assertTrue(T.verify(t, rule, done)[0])

    def test_signed_authorship_roundtrips(self):
        if not ed25519_available():
            self.skipTest("cryptography not installed")
        s = Ed25519Signer()
        t = T.mint(rule, done, {"n": 27}, signer=s)
        self.assertTrue(T.verify(t, rule, done)[0])             # embedded public key verifies authorship


class Tamper(unittest.TestCase):
    def setUp(self):
        self.t = T.mint(rule, done, {"n": 27})

    def test_step_count_forgery(self):
        self.assertFalse(T.verify(dict(self.t, steps=40), rule, done)[0])

    def test_terminus_forgery(self):
        self.assertIn("TERMINUS", T.verify(dict(self.t, terminus={"n": 2}), rule, done)[1])

    def test_path_hash_forgery(self):
        self.assertIn("PATH", T.verify(dict(self.t, path_hash="0" * 64), rule, done)[1])

    def test_wrong_rule_rejected(self):
        self.assertIn("RULESET", T.verify(self.t, rule_uncompressed, done)[1])

    def test_signature_forgery(self):
        if not ed25519_available():
            self.skipTest("cryptography not installed")
        a, b = Ed25519Signer(), Ed25519Signer()
        t = T.mint(rule, done, {"n": 27}, signer=a)               # authentic under a's key (embedded)
        forged = dict(t, signature=T.mint(rule, done, {"n": 27}, signer=b)["signature"])  # b signs same body
        self.assertIn("SIGNATURE", T.verify(forged, rule, done)[1])   # path is valid; signature is not


class Divergence(unittest.TestCase):
    def test_locates_exact_step(self):
        t = T.mint(rule, done, {"n": 27})
        scroll = [{"n": x} for x in SY.orbit(27)]
        self.assertIsNone(T.locate_divergence(t, rule, scroll))
        scroll[10] = {"n": 7777}
        self.assertEqual(T.locate_divergence(t, rule, scroll), 10)

    def test_wrong_seed_diverges_at_zero(self):
        t = T.mint(rule, done, {"n": 27})
        self.assertEqual(T.locate_divergence(t, rule, [{"n": 28}]), 0)


class Lineage(unittest.TestCase):
    def test_chain_verifies(self):
        t1 = T.mint(rule, done, {"n": 27})
        t2 = T.link(t1, rule, done, seed_from=lambda term: {"n": 97})
        self.assertEqual(T.verify_lineage([t1, t2], rule, done), (True, None))

    def test_broken_link_located(self):
        t1 = T.mint(rule, done, {"n": 27})
        t2 = T.link(t1, rule, done, seed_from=lambda term: {"n": 97})
        ok, fault = T.verify_lineage([t1, dict(t2, prev="0" * 64)], rule, done)
        self.assertFalse(ok); self.assertEqual(fault["link"], 1); self.assertIn("LINEAGE", fault["reason"])


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("set PYTHONHASHSEED=0\n"); raise SystemExit(2)
    unittest.main(verbosity=2)
