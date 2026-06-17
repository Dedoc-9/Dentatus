"""
assay/court.py — the assay court. Re-verifies an assessment log on a separate machine.

For each assessment, in order, it proves: chain link + seq, the assay-authority attestation (committed
hash + signature), and then by kind:
  * metric   -> the metric source is unchanged AND re-running it over the recorded evidence reproduces the
                recorded value bit-for-bit AND the recorded verdict is the derived one. A fudged fairness
                number or flipped verdict fails here.
  * judgment -> the signed opinion is rubric-bound and verifies under the assessor's PINNED key. A forged
                or impersonated 'this was wise' fails here, even inside a validly assay-signed log.

It does NOT re-decide correctness/fairness/wisdom. It proves the recorded ASSESSMENTS are honest,
reproducible (metrics), and attributable (judgments). Integrity of the judgments, not their truth.
"""
import hashlib
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "llm_toolkit"))
import agent_core as core
from agent_core import GENESIS, HmacSigner

import metrics as M
import judgment as J


class Verdict:
    def __init__(self): self.ok = True; self.reason = None; self.at = None
    def fail(self, reason, at): self.ok = False; self.reason = reason; self.at = at; return self


def assay_audit(ledger, assay_verifier, rubrics, trusted_assessors):
    """rubrics = {rubric_name: Rubric};  trusted_assessors = {assessor_id: verifier-with-public-key}."""
    v = Verdict()
    vf = assay_verifier if hasattr(assay_verifier, "verify") else HmacSigner(assay_verifier)
    prev = GENESIS
    seq = 0
    for r in ledger:
        f = r["frame"]
        if f["prev"] != prev or f["seq"] != seq:
            return v.fail("CHAIN broken (insertion/deletion/reorder)", seq)
        # re-derive the assay-authority attestation
        sh = core.state_hash(f)
        committed = hashlib.sha256(("%s|%s" % (sh, prev)).encode()).hexdigest()
        if committed != r["committed_hash"]:
            return v.fail("TAMPER (assessment content hash mismatch)", f["seq"])
        if not vf.verify(committed.encode(), r["signature"]):
            return v.fail("TAMPER (assay signature mismatch / wrong key)", f["seq"])

        if f["kind"] == "metric":
            fn = M.METRICS.get(f["metric_name"])
            if fn is None:
                return v.fail("UNKNOWN metric %r" % f["metric_name"], f["seq"])
            if core.source_hash(fn) != f["metric_hash"]:
                return v.fail("METRIC changed (logic differs from what was recorded)", f["seq"])
            recomputed = core._canon(fn(f["evidence"]))
            if core.canonical_bytes(recomputed) != core.canonical_bytes(f["value"]):
                return v.fail("METRIC RECOMPUTE mismatch (recorded value was fudged)", f["seq"])
            if M.metric_verdict(f["dimension"], recomputed) != f["verdict"]:
                return v.fail("VERDICT mismatch (pass/fail does not follow from the metric)", f["seq"])
        elif f["kind"] == "judgment":
            j = f["judgment"]["jcore"]
            if j.get("target_hash") != f["target_hash"]:
                return v.fail("JUDGMENT not bound to its assessment target", f["seq"])
            rub = rubrics.get(j.get("rubric_name"))
            if rub is None:
                return v.fail("UNKNOWN rubric %r" % j.get("rubric_name"), f["seq"])
            ok, why = J.verify_judgment(f["judgment"], rub, trusted_assessors)
            if not ok:
                return v.fail("JUDGMENT rejected: %s" % why, f["seq"])
        else:
            return v.fail("UNKNOWN assessment kind %r" % f["kind"], f["seq"])

        prev = r["committed_hash"]
        seq += 1
    return v


def print_verdict(v, n):
    if v.ok:
        print("  VERIFIED -- %d assessments: metrics recomputed, judgments attributed, log untampered." % n)
    else:
        print("  REJECTED: %s  (at assessment seq %s)" % (v.reason, v.at))
    return 0 if v.ok else 1
