"""
causal_runtime/tiers.py — the two-tier split that resolves the "causal" overclaim.

The dependency graph is used for two different jobs with two different proof burdens:

  PREDICTIVE tier  — answers "where should we spend compute?"  Correlation / dependency / historical
                     association is ENOUGH; no causal claim is made. Feeds salience, validation depth,
                     streaming, attention. Every proposed edge lives here unconditionally.

  CORROBORATED tier — answers "which structural assumptions survived attempts to fail them?"  Only edges whose
                     StructureProposal reached CORROBORATED (held-out hits, zero held-out misses, real
                     discriminating opportunity) qualify. ONLY this tier may wear structural/causal vocabulary.

The corroborated set is always a strict subset of the predictive set, so allocation never waits on
falsification and the strong claim is always earned. Law:

    correlation/prediction → allocation        ALLOWED
    prediction → truth                          FORBIDDEN
    only CORROBORATED → structural claim         (the vocabulary gate)

Deterministic. Stdlib only.
"""
from falsification import CORROBORATED, PROPOSED, DECAYING, REJECTED

PREDICTIVE, CORROBORATED_TIER = "predictive", "corroborated"


def predictive_edges(proposals):
    """Every edge that is not REJECTED is usable for ALLOCATION — correlation suffices, no causal claim. (A
    rejected edge has been actively falsified, so it is dropped even from prediction.)"""
    return sorted({(p.source, p.target) for p in proposals if p.status != REJECTED}, key=str)


def corroborated_edges(proposals):
    """Only edges that survived held-out falsification. These — and only these — may be described with
    structural / causal vocabulary."""
    return sorted({(p.source, p.target) for p in proposals if p.status == CORROBORATED}, key=str)


def tier_of(proposal):
    """Which tier an edge may be used in. CORROBORATED -> both; PROPOSED/DECAYING -> predictive only;
    REJECTED -> neither."""
    if proposal.status == CORROBORATED:
        return CORROBORATED_TIER
    if proposal.status in (PROPOSED, DECAYING):
        return PREDICTIVE
    return None                                         # REJECTED -> not usable


def classify(proposals):
    """Bucket proposals and assert the invariant: corroborated ⊆ predictive. Returns a report."""
    pred = predictive_edges(proposals)
    corr = corroborated_edges(proposals)
    assert set(corr).issubset(set(pred)), "corroborated edges must be a subset of predictive edges"
    by_status = {}
    for p in proposals:
        by_status.setdefault(p.status, []).append((p.source, p.target))
    return {"predictive": pred, "corroborated": corr,
            "may_claim_structure": corr, "allocation_only": sorted(set(pred) - set(corr), key=str),
            "by_status": by_status}


def vocabulary_for(proposal):
    """The honest words allowed for an edge, by tier. Prevents prose from overclaiming."""
    t = tier_of(proposal)
    if t == CORROBORATED_TIER:
        return "corroborated structural edge (survived held-out falsification)"
    if t == PREDICTIVE:
        return "predictive association (allocation only; no causal claim)"
    return "rejected (falsified)"
