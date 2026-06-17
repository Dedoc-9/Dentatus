"""
assay/demo_assay.py — the meta-audit layer over a batch of lending decisions.

Run:  PYTHONHASHSEED=0 python3 demo_assay.py

  A. CORRECT (metric)   — assess each decision against a ground-truth label; the court recomputes it.
  B. FAIR (metric)      — group approval-parity over a cohort; a PASS cohort and a FAIL cohort, honestly.
  C. WISE (judgment)    — a named reviewer signs a rubric-scored opinion of a decision; attributed + bound.
  D. FUDGE CAUGHT       — someone edits a recorded fairness number; the court recomputes and REJECTS.
  E. FORGERY CAUGHT     — a rogue key signs a 'wise' verdict as a real reviewer; the pinned registry rejects.

Honest boundary: this proves the ASSESSMENTS are reproducible (metrics), attributable (judgments), and
untampered. It does NOT certify any decision is truly correct, fair, or wise. Integrity of the judgments,
not their truth — and fairness here is ONE metric (demographic parity); other definitions can disagree.
"""
import copy, hashlib
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "llm_toolkit"))
import agent_core as core
from agent_guard import Ed25519Signer, Ed25519Verifier

import assess as A
from court import assay_audit, print_verdict
import judgment as J

SECRET = b"assay_authority_key_demo"

# Three prior lending decisions to assess (each carries the committed_hash it had in its own ledger).
DECISIONS = [
    {"id": "DEC-001", "committed_hash": core.state_hash({"d": 1}), "approved": True,  "group": "A"},
    {"id": "DEC-002", "committed_hash": core.state_hash({"d": 2}), "approved": False, "group": "B"},
    {"id": "DEC-003", "committed_hash": core.state_hash({"d": 3}), "approved": True,  "group": "A"},
]
GROUND_TRUTH = {"DEC-001": True, "DEC-002": False, "DEC-003": False}   # DEC-003 was actually wrong


if __name__ == "__main__":
    core.require_deterministic_hashing("assay")
    authority = Ed25519Signer.generate()                     # signs the assessment LOG
    authority_verifier = Ed25519Verifier(authority.public_material())
    rec = A.AssayRecorder(authority)
    ledger = []

    print("A) CORRECT (deterministic, recomputable):")
    for d in DECISIONS:
        ev = {"decision": {"approved": d["approved"]},
              "ground_truth": {"approved": GROUND_TRUTH[d["id"]]}, "key": "approved"}
        r = rec.record_metric(d["committed_hash"], "correct", "correctness_vs_oracle", ev)
        ledger.append(r)
        print("   %s correct=%s (got=%s expected=%s)" % (d["id"], r["frame"]["value"]["correct"],
              r["frame"]["value"]["got"], r["frame"]["value"]["expected"]))

    print("\nB) FAIR (group approval-parity, ONE metric):")
    fair_pass = {"cohort": [{"group": "A", "approved": True}, {"group": "A", "approved": False},
                            {"group": "B", "approved": True}, {"group": "B", "approved": False}],
                 "decision_key": "approved", "tolerance": 0.10}
    fair_fail = {"cohort": [{"group": "A", "approved": True}, {"group": "A", "approved": True},
                            {"group": "B", "approved": False}, {"group": "B", "approved": False}],
                 "decision_key": "approved", "tolerance": 0.10}
    rp = rec.record_metric("COHORT-Q2-balanced", "fair", "group_approval_parity", fair_pass)
    rf = rec.record_metric("COHORT-Q2-skewed", "fair", "group_approval_parity", fair_fail)
    ledger += [rp, rf]
    print("   balanced cohort: rates=%s disparity=%s -> %s"
          % (rp["frame"]["value"]["rates"], rp["frame"]["value"]["max_disparity"], rp["frame"]["verdict"]))
    print("   skewed cohort  : rates=%s disparity=%s -> %s"
          % (rf["frame"]["value"]["rates"], rf["frame"]["value"]["max_disparity"], rf["frame"]["verdict"]))

    print("\nC) WISE (signed, attributed judgment under a rubric):")
    rubric = J.Rubric("lending-review-v1", ["policy_fit", "rationale_quality", "edge_case_handling"])
    alice = Ed25519Signer.generate()
    trusted = {"reviewer_alice": Ed25519Verifier(alice.public_material())}
    rubrics = {rubric.name: rubric}
    jr = J.make_judgment(DECISIONS[0]["committed_hash"], rubric, "reviewer_alice", alice,
                         {"policy_fit": 5, "rationale_quality": 4, "edge_case_handling": 3},
                         "Sound on policy; rationale could cite the duplicate-charge clause.")
    ledger.append(rec.record_judgment(DECISIONS[0]["committed_hash"], jr))
    print("   reviewer_alice scored DEC-001 under %s/%s" % (rubric.name, rubric.rubric_hash))

    print("\n   ASSAY COURT verifies the whole assessment log:")
    print_verdict(assay_audit(ledger, authority_verifier, rubrics, trusted), len(ledger))

    print("\nD) FUDGE CAUGHT: an attacker WITH the assay key edits the skewed cohort's recorded")
    print("   disparity to look compliant AND re-signs the log -- the court recomputes the metric:")
    def reseal(led, signer, start):
        out = copy.deepcopy(led)
        prev = out[start - 1]["committed_hash"] if start > 0 else core.GENESIS
        for i in range(start, len(out)):
            f = out[i]["frame"]; f["prev"] = prev
            sh = core.state_hash(f)
            committed = hashlib.sha256(("%s|%s" % (sh, prev)).encode()).hexdigest()
            out[i]["state_hash"] = sh; out[i]["committed_hash"] = committed
            out[i]["signature"] = signer.sign(committed.encode()); prev = committed
        return out
    bad = copy.deepcopy(ledger)                       # index 4 is the skewed (failing) cohort
    bad[4]["frame"]["value"]["max_disparity"] = 0.0
    bad[4]["frame"]["value"]["within_tolerance"] = True
    bad[4]["frame"]["verdict"] = "pass"
    bad = reseal(bad, authority, 4)                   # attacker re-signs: hashes + signatures now valid
    print_verdict(assay_audit(bad, authority_verifier, rubrics, trusted), len(bad))

    print("\nE) FORGERY CAUGHT: a rogue key signs a 'wise' verdict as reviewer_alice:")
    rogue = Ed25519Signer.generate()
    forged = J.make_judgment(DECISIONS[1]["committed_hash"], rubric, "reviewer_alice", rogue,
                             {"policy_fit": 5, "rationale_quality": 5, "edge_case_handling": 5}, "LGTM")
    forged_ledger = list(ledger) + [rec.record_judgment(DECISIONS[1]["committed_hash"], forged)]
    print_verdict(assay_audit(forged_ledger, authority_verifier, rubrics, trusted), len(forged_ledger))

    print("\n   NOTE: integrity != truth. The court proves assessments are reproducible/attributable,")
    print("   not that any decision was truly correct, fair, or wise. Fairness shown is ONE metric.")
