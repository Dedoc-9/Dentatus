"""Tests for the privilege-separated PEP: path policy, verdict binding, tamper/forge, append-only log."""
import os, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "llm_toolkit"))
import agent_core as core
from agent_guard import Ed25519Signer, Ed25519Verifier
from isolated_pep import PathPolicy, sign_action_verdict, verify_action_verdict, IsolatedPEP


class TestPathPolicy(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp()
        self.design = os.path.join(self.work, "design"); os.makedirs(self.design)
        self.outside = os.path.join(self.work, "outside"); os.makedirs(self.outside)
        self.pol = PathPolicy([self.design])

    def test_allow_inside(self):
        d, _ = self.pol.evaluate({"op": "write", "paths": [os.path.join(self.design, "a.svg")]})
        self.assertEqual(d, "allow")

    def test_deny_traversal(self):
        d, _ = self.pol.evaluate({"op": "write", "paths": [os.path.join(self.design, "..", "outside", "x")]})
        self.assertEqual(d, "deny")

    def test_deny_absolute_outside(self):
        d, _ = self.pol.evaluate({"op": "read", "paths": ["/etc/passwd"]})
        self.assertEqual(d, "deny")

    def test_deny_symlink_escape(self):
        link = os.path.join(self.design, "link")
        try:
            os.symlink(self.outside, link)
        except OSError:
            self.skipTest("symlinks unsupported")
        d, _ = self.pol.evaluate({"op": "write", "paths": [os.path.join(link, "x")]})
        self.assertEqual(d, "deny")

    def test_unknown_op_denied(self):
        d, _ = self.pol.evaluate({"op": "delete", "paths": [self.design]})
        self.assertEqual(d, "deny")

    def test_policy_hash_pins_roots(self):
        self.assertNotEqual(PathPolicy([self.design]).policy_hash, PathPolicy([self.outside]).policy_hash)


class TestVerdictBinding(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp()
        self.design = os.path.join(self.work, "design"); os.makedirs(self.design)
        self.signer = Ed25519Signer.generate()
        self.pol = PathPolicy([self.design])

    def test_bound_and_signed(self):
        act = {"op": "write", "paths": [os.path.join(self.design, "a")]}
        r = sign_action_verdict(self.pol, self.signer, act)
        ok, _ = verify_action_verdict(r, Ed25519Verifier(self.signer.public_material()), act)
        self.assertTrue(ok)

    def test_wrong_action_rejected(self):
        act = {"op": "write", "paths": [os.path.join(self.design, "a")]}
        r = sign_action_verdict(self.pol, self.signer, act)
        other = {"op": "write", "paths": [os.path.join(self.design, "b")]}
        ok, _ = verify_action_verdict(r, Ed25519Verifier(self.signer.public_material()), other)
        self.assertFalse(ok)

    def test_flipped_decision_rejected(self):
        act = {"op": "read", "paths": ["/etc/shadow"]}
        r = sign_action_verdict(self.pol, self.signer, act)
        self.assertEqual(r["verdict"]["decision"], "deny")
        r["verdict"]["decision"] = "allow"
        ok, _ = verify_action_verdict(r, Ed25519Verifier(self.signer.public_material()), act)
        self.assertFalse(ok)

    def test_rogue_key_cannot_forge(self):
        act = {"op": "read", "paths": ["/etc/shadow"]}
        rogue = Ed25519Signer.generate()
        vcore = {"request_hash": core.state_hash(act), "policy_hash": self.pol.policy_hash,
                 "decision": "allow", "reasons": []}
        fake = {"verdict": vcore, "signature": rogue.sign(core.canonical_bytes(vcore)), "algo": "ed25519"}
        ok, _ = verify_action_verdict(fake, Ed25519Verifier(self.signer.public_material()), act)
        self.assertFalse(ok)


class TestLiveServerAndLog(unittest.TestCase):
    def test_http_and_append_only_log(self):
        import urllib.request, json
        work = tempfile.mkdtemp(); design = os.path.join(work, "design"); os.makedirs(design)
        with IsolatedPEP([design], violation_log=os.path.join(work, "v.jsonl")) as pep:
            v = pep.public_verifier()
            esc = {"op": "write", "paths": ["/etc/cron.d/x"]}
            req = urllib.request.Request(pep.base_url + "/authorize", data=json.dumps(esc).encode(),
                                         headers={"Content-Type": "application/json"}, method="POST")
            r = json.loads(urllib.request.urlopen(req, timeout=5).read())
            self.assertEqual(r["verdict"]["decision"], "deny")
            ok, _ = verify_action_verdict(r, v, esc)
            self.assertTrue(ok)                              # a signed DENY is still authentic
            self.assertEqual(sum(1 for _ in open(os.path.join(work, "v.jsonl"))), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
