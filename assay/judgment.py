"""
assay/judgment.py — SIGNED, attributable judgments (the 'wise'/quality tier).

'Wise' cannot be recomputed or proven. What the meta-layer CAN do is make a quality opinion a first-class
record: bound to the decision it judges, scored against a NAMED, source-hashed rubric, and signed by a
specific assessor whose key is pinned in a trusted registry. So:
  * a judgment cannot be altered after the fact (signature covers score + rationale + bindings), and
  * a judgment cannot be IMPERSONATED — a verdict claiming to be from 'reviewer_alice' must verify under
    alice's pinned public key, or the court rejects it.

This records WHO judged WHAT, under WHICH rubric. It never asserts the opinion is correct. Integrity of
the judgment, not truth of it.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "llm_toolkit"))
import agent_core as core


def _scoring_guide(criterion, score):
    """The (documented) shape of a rubric score: an int in 0..5 per criterion. Source-hashed into the
    rubric so 'the rubric did not change' is provable."""
    return isinstance(score, int) and 0 <= score <= 5


class Rubric:
    def __init__(self, name, criteria):
        self.name = name
        self.criteria = list(criteria)
        self.rubric_hash = core.state_hash({
            "name": name, "criteria": self.criteria,
            "guide": core.source_hash(_scoring_guide),
        })[:16]


def make_judgment(target_hash, rubric, assessor_id, assessor_signer, scores, rationale):
    """Build a signed judgment. `scores` is {criterion: int 0..5}. Signature covers the bound core."""
    jcore = {
        "target_hash": target_hash,
        "rubric_name": rubric.name,
        "rubric_hash": rubric.rubric_hash,
        "assessor_id": assessor_id,
        "scores": {k: scores[k] for k in sorted(scores)},
        "rationale": rationale,
    }
    sig = assessor_signer.sign(core.canonical_bytes(jcore))
    return {"jcore": jcore, "signature": sig, "algo": assessor_signer.algo}


def verify_judgment(record, rubric, trusted_assessors):
    """Return (ok, reason). Checks: rubric binding, assessor is known, and the signature verifies under the
    assessor's PINNED public key (so a rogue-key forgery for a real assessor id is rejected)."""
    j = record.get("jcore")
    sig = record.get("signature")
    if not j or sig is None:
        return False, "no judgment/signature"
    if j.get("rubric_hash") != rubric.rubric_hash or j.get("rubric_name") != rubric.name:
        return False, "rubric mismatch (judged under a different rubric than the auditor pins)"
    verifier = trusted_assessors.get(j.get("assessor_id"))
    if verifier is None:
        return False, "unknown assessor %r (not in trusted registry)" % j.get("assessor_id")
    if not verifier.verify(core.canonical_bytes(j), sig):
        return False, "signature invalid (impersonation or tampered judgment)"
    return True, "authentic, attributed, rubric-bound"
