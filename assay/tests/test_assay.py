"""Stdlib unittest suite for the assay meta-audit layer."""
import os, sys, copy, hashlib, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "llm_toolkit"))

import agent_core as core
from agent_guard import Ed25519Signer, Ed25519Verifier
import assess as A
import metrics as M
import judgment as J
from court import assay_audit

TGT = core.state_hash({"decision": 1})


def _authority():
    s = Ed25519Signer.generate()
    return s, Ed25519Verifier(s.public_material())


def _reseal(led, signer, start):
    out = copy.deepcopy(led)
    prev = out[start - 1]["committed_hash"] if start > 0 else core.GENESIS
    for i in range(start, len(out)):
        f = out[i]["frame"]; f["prev"] = prev
        sh = core.state_hash(f)
        committed = hashlib.sha256(("%s|%s" % (sh, prev)).encode()).hexdigest()
        out[i]["state_hash"] = sh; out[i]["committed_hash"] = committed
        out[i]["signature"] = signer.sign(committed.encode()); prev = committed
    return out


class TestMetrics(unittest.TestCase):
    def test_correctness(self):
        v = M.correctness_vs_oracle({"decision": {"a": True}, "ground_truth": {"a": True}, "key": "a"})
        self.assertTrue(v["correct"])

    def test_parity_disparity(self):
        v = M.group_approval_parity({"cohort": [{"group": "A", "approved": True}, {"group": "B", "approved": False}],
                                     "decision_key": "approved", "tolerance": 0.1})
        self.assertEqual(v["max_disparity"], 1.0)
        self.assertFalse(v["within_tolerance"])


class TestAssayCourt(unittest.TestCase):
    def setUp(self):
        self.sig, self.ver = _authority()
        self.rec = A.AssayRecorder(self.sig)
        self.led = [
            self.rec.record_metric(TGT, "correct", "correctness_vs_oracle",
                                   {"decision": {"approved": True}, "ground_truth": {"approved": True}, "key": "approved"}),
            self.rec.record_metric("C1", "fair", "group_approval_parity",
                                   {"cohort": [{"group": "A", "approved": True}, {"group": "B", "approved": False}],
                                    "decision_key": "approved", "tolerance": 0.1}),  # skewed -> fudge is real
        ]

    def test_clean_verifies(self):
        self.assertTrue(assay_audit(self.led, self.ver, {}, {}).ok)

    def test_fudged_metric_caught_even_resigned(self):
        bad = copy.deepcopy(self.led)
        bad[1]["frame"]["value"]["max_disparity"] = 0.0
        bad[1]["frame"]["value"]["within_tolerance"] = True
        bad = _reseal(bad, self.sig, 1)                       # attacker has the assay key
        v = assay_audit(bad, self.ver, {}, {})
        self.assertFalse(v.ok)
        self.assertIn("RECOMPUTE", v.reason)

    def test_reorder_caught(self):
        led = copy.deepcopy(self.led); led[0], led[1] = led[1], led[0]
        self.assertFalse(assay_audit(led, self.ver, {}, {}).ok)

    def test_wrong_assay_key(self):
        _, other = _authority()
        self.assertFalse(assay_audit(self.led, other, {}, {}).ok)


class TestJudgments(unittest.TestCase):
    def setUp(self):
        self.auth, self.authv = _authority()
        self.rec = A.AssayRecorder(self.auth)
        self.rubric = J.Rubric("r1", ["fit", "clarity"])
        self.alice, alicev = _authority()
        self.trusted = {"alice": Ed25519Verifier(self.alice.public_material())}
        self.rubrics = {"r1": self.rubric}

    def test_authentic_judgment_verifies(self):
        jr = J.make_judgment(TGT, self.rubric, "alice", self.alice, {"fit": 5, "clarity": 4}, "ok")
        led = [self.rec.record_judgment(TGT, jr)]
        self.assertTrue(assay_audit(led, self.authv, self.rubrics, self.trusted).ok)

    def test_impersonation_caught(self):
        rogue = Ed25519Signer.generate()
        jr = J.make_judgment(TGT, self.rubric, "alice", rogue, {"fit": 5, "clarity": 5}, "lgtm")
        led = [self.rec.record_judgment(TGT, jr)]
        v = assay_audit(led, self.authv, self.rubrics, self.trusted)
        self.assertFalse(v.ok)

    def test_unknown_assessor_caught(self):
        jr = J.make_judgment(TGT, self.rubric, "mallory", self.alice, {"fit": 5, "clarity": 5}, "x")
        led = [self.rec.record_judgment(TGT, jr)]
        self.assertFalse(assay_audit(led, self.authv, self.rubrics, self.trusted).ok)

    def test_altered_score_caught(self):
        jr = J.make_judgment(TGT, self.rubric, "alice", self.alice, {"fit": 5, "clarity": 4}, "ok")
        jr["jcore"]["scores"]["clarity"] = 1                  # tamper after signing
        led = [self.rec.record_judgment(TGT, jr)]
        self.assertFalse(assay_audit(led, self.authv, self.rubrics, self.trusted).ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
