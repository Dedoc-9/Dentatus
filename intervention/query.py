"""
intervention/query.py — the causal query: turn an authorized question into admissible evidence (never an edge).

Given an InterventionCandidate (source, target) and a world's dynamics, it runs the airlock gate, then the
do-operator probes, and returns one of four verdicts with an evidence delta — NOT a graph edit:

    UNAUTHORIZED : the airlock refused the question (scope / rollback / self-loop)
    REJECTED     : do(source) leaves target unchanged -> source does NOT cause target (confounder / spurious).
                   This is the case persistence alone cannot resolve.
    CYCLE        : do(source) moves target AND do(target) moves source -> bidirectional. Emit a CYCLE WARNING,
                   never a stronger edge (cycles are where causal discovery becomes self-fulfilling).
    CONFIRMED    : do(source) moves target, do(target) does not move source -> directed evidence source→target.

`evidence_delta` is +1 / 0 / −1 / 0 (confirm / cycle / reject / unauthorized): it updates the WEIGHT of
EVIDENCE for an existing proposal; promotion to a real edge still requires external review (intent ≠ authority).
Deterministic. Stdlib only.
"""
from collections import namedtuple

from protocol import authorize
from experiment import causal_effect

CausalVerdict = namedtuple("CausalVerdict",
                           "source target verdict effect_fwd effect_bwd evidence_delta reason")


def query(candidate, dynamics, init, steps=12, v1=1, v2=1000, threshold=0, scope_limit=4):
    """Run the authorized interventional test. Pure w.r.t. the world (all probes on shadow copies)."""
    adm = authorize(candidate, scope_limit=scope_limit)
    if not adm.admitted:
        return CausalVerdict(candidate.source, candidate.target, "UNAUTHORIZED", 0, 0, 0, adm.reason)

    ef = causal_effect(dynamics, init, steps, candidate.source, candidate.target, v1, v2)
    if ef <= threshold:
        return CausalVerdict(candidate.source, candidate.target, "REJECTED", ef, 0, -1,
                             "do(source) leaves target unchanged -> confounded / spurious")

    eb = causal_effect(dynamics, init, steps, candidate.target, candidate.source, v1, v2)
    if eb > threshold:
        return CausalVerdict(candidate.source, candidate.target, "CYCLE", ef, eb, 0,
                             "do(source)->target AND do(target)->source -> cycle warning, no stronger edge")

    return CausalVerdict(candidate.source, candidate.target, "CONFIRMED", ef, eb, +1,
                         "do(source) moves target; do(target) does not move source -> directed evidence")
