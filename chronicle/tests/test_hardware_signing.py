"""Tests for HardwareSigner fallback tiers (Tier 2 ed25519-soft, Tier 3 hmac-scrypt).
The PKCS#11 hardware tier needs a physical token/middleware and is not exercised here."""
import os, sys, builtins, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import hardware_signing as H
import core
from court import verify_chain

os.environ.setdefault("CHRONICLE_SIGNER_PASSPHRASE", "unit-test-pass")


def _tmp_key():
    import tempfile
    return os.path.join(tempfile.mkdtemp(), "softkey")


def logic(i): return {"y": i["x"] * 2}
def inv(i, o): return True


class TestTier2(unittest.TestCase):
    def test_sign_verify_and_tamper(self):
        s = H.HardwareSigner(prefer_hardware=False, soft_key_path=_tmp_key())
        self.assertEqual(s.algo, "ed25519-soft")
        sig = s.sign(b"abc")
        self.assertTrue(s.verify(b"abc", sig))
        self.assertFalse(s.verify(b"abd", sig))
        self.assertTrue(s.public_material())                 # asymmetric -> has a public half

    def test_key_persists_encrypted_at_rest(self):
        p = _tmp_key()
        s1 = H.HardwareSigner(prefer_hardware=False, soft_key_path=p)
        s2 = H.HardwareSigner(prefer_hardware=False, soft_key_path=p)
        self.assertEqual(s1.public_material(), s2.public_material())
        blob = open(p, "rb").read()
        self.assertNotIn(b"\x00" * 16, blob[:16])            # salt present; file isn't plaintext key
        sig = s1.sign(b"m")
        self.assertTrue(s2.verify(b"m", sig))                # cross-instance verify

    def test_dropin_recorder_and_court(self):
        s = H.HardwareSigner(prefer_hardware=False, soft_key_path=_tmp_key())
        rec = core.Recorder(s, core.ruleset_hash(logic, inv))
        r = rec.record("D1", {"x": 3}, logic({"x": 3}), inv)
        self.assertEqual(r["algo"], "ed25519-soft")
        self.assertTrue(verify_chain([r], s, logic, inv).ok)


class TestTier3(unittest.TestCase):
    def _force_no_crypto(self):
        real = builtins.__import__
        def blocked(n, *a, **k):
            if n.startswith("cryptography"):
                raise ImportError("simulated")
            return real(n, *a, **k)
        return real, blocked

    def test_symmetric_fallback(self):
        real, blocked = self._force_no_crypto()
        builtins.__import__ = blocked
        try:
            s = H.HardwareSigner(prefer_hardware=False, soft_key_path=_tmp_key())
            self.assertEqual(s.algo, "hmac-scrypt")
            self.assertIsNone(s.public_material())            # symmetric: nothing safe to publish
            sig = s.sign(b"m")
            self.assertTrue(s.verify(b"m", sig))
            self.assertFalse(s.verify(b"x", sig))
        finally:
            builtins.__import__ = real

    def test_scrypt_key_is_passphrase_bound(self):
        real, blocked = self._force_no_crypto()
        builtins.__import__ = blocked
        try:
            os.environ["CHRONICLE_SIGNER_PASSPHRASE"] = "pass-A"
            a = H.HardwareSigner(prefer_hardware=False)
            os.environ["CHRONICLE_SIGNER_PASSPHRASE"] = "pass-B"
            b = H.HardwareSigner(prefer_hardware=False)
            self.assertNotEqual(a.sign(b"m"), b.sign(b"m"))   # different passphrase -> different MAC
        finally:
            os.environ["CHRONICLE_SIGNER_PASSPHRASE"] = "unit-test-pass"
            builtins.__import__ = real


if __name__ == "__main__":
    unittest.main(verbosity=2)
