"""Tests for pact multi-agent cross-attestation covenant."""
import os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "llm_toolkit"))
import covenant as P
import core
from agent_guard import Ed25519Signer, Ed25519Verifier, ed25519_available


def monotonic(prev, new): return new["acc"] >= prev["acc"]


@unittest.skipUnless(ed25519_available(), "cryptography unavailable")
class TestCovenant(unittest.TestCase):
    def setUp(self):
        self.A, self.B, self.C = (Ed25519Signer.generate() for _ in range(3))
        self.reg = {"A": Ed25519Verifier(self.A.public_material()), "B": Ed25519Verifier(self.B.public_material()),
                    "C": Ed25519Verifier(self.C.public_material())}
        self.inv = {"A": None, "B": monotonic, "C": monotonic}

    def _chain(self):
        rA = P.state_receipt("A", {"acc": 10}, self.A)
        lA = {"verdict": None, "verdict_sig": None, "receipt": rA}
        lB = P.cross_attest(rA, "B", {"acc": 15}, self.B, monotonic, self.reg)
        lC = P.cross_attest(lB["receipt"], "C", {"acc": 22}, self.C, monotonic, self.reg)
        return [lA, lB, lC]

    def test_clean_covenant_verifies(self):
        ok, fault = P.audit_covenant(self._chain(), self.reg, self.inv)
        self.assertTrue(ok, fault)

    def test_unknown_agent_rejected(self):
        rogue = Ed25519Signer.generate()
        ok, why = P.verify_receipt(P.state_receipt("Z", {"acc": 1}, rogue), self.reg)
        self.assertFalse(ok)

    def test_impersonation_rejected(self):
        rogue = Ed25519Signer.generate()
        ok, why = P.verify_receipt(P.state_receipt("A", {"acc": 1}, rogue), self.reg)
        self.assertFalse(ok)   # claims to be A but signed with a non-pinned key

    def test_tampered_state_rejected(self):
        r = P.state_receipt("A", {"acc": 10}, self.A); r["state"]["acc"] = 999
        ok, why = P.verify_receipt(r, self.reg)
        self.assertFalse(ok)

    def test_cross_attest_refuses_invariant_breach(self):
        rA = P.state_receipt("A", {"acc": 10}, self.A)
        with self.assertRaises(P.CovenantBreach):
            P.cross_attest(rA, "B", {"acc": 9}, self.B, monotonic, self.reg)   # acc drops -> refused

    def test_audit_isolates_injected_breach(self):
        rA = P.state_receipt("A", {"acc": 10}, self.A)
        lA = {"verdict": None, "verdict_sig": None, "receipt": rA}
        badB = P.state_receipt("B", {"acc": 9}, self.B, prev_hash=rA["state_hash"])
        vcore = {"from": "A", "from_hash": rA["state_hash"], "to": "B", "to_hash": badB["state_hash"]}
        link = {"verdict": vcore, "verdict_sig": self.B.sign(core.canonical_bytes(vcore)), "receipt": badB}
        ok, fault = P.audit_covenant([lA, link], self.reg, self.inv)
        self.assertFalse(ok)
        self.assertEqual(fault["agent"], "B")
        self.assertIn("invariant", fault["reason"])

    def test_broken_binding_caught(self):
        chain = self._chain()
        chain[1]["verdict"]["from_hash"] = "0" * 64   # break the A->B binding
        ok, fault = P.audit_covenant(chain, self.reg, self.inv)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
