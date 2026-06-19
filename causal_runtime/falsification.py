"""
causal_runtime/falsification.py — the held-out falsification gate. Evidence that can go DOWN.

`coupling_discovery` had a self-sealing asymmetry: a persistent ghost only ever RAISED a candidate's frequency,
so a candidate became monotonically harder to dislodge — a self-confirming loop. This module replaces the
"confidence accumulates" model with a Popperian TRACK RECORD: a StructureProposal is tested on a held-out
window of committed history it was NOT derived from, and a held-out MISS lowers its standing. Corroboration is
"survived attempts to fail it", not "fit the data that generated it".

    StructureProposal:
        source, target
        train_hits, train_misses        # evidence from the window the proposal was derived in
        heldout_hits, heldout_misses     # evidence from a DISJOINT window — heldout_misses can grow
        last_test_epoch
        status                           # PROPOSED | CORROBORATED | DECAYING | REJECTED

Status discipline (the honest part):
    PROPOSED    : not enough held-out tests, OR the held-out window contained NO discriminating opportunity
                  (the cause never varied in a way that could falsify the edge). "Untested" is NOT "survived".
    CORROBORATED: enough held-out hits AND zero held-out misses.
    DECAYING    : had support but a held-out miss appeared — standing is dropping.
    REJECTED    : held-out miss-rate crossed the floor.

Law: `falsification → proposal status` ALLOWED ; `falsification → committed reality` FORBIDDEN.
Deterministic integer logic. Stdlib only.
"""
import hashlib
from collections import namedtuple

StructureProposal = namedtuple(
    "StructureProposal",
    "source target train_hits train_misses heldout_hits heldout_misses last_test_epoch status h",
)

PROPOSED, CORROBORATED, DECAYING, REJECTED = "PROPOSED", "CORROBORATED", "DECAYING", "REJECTED"


def _changed(a, b):
    return a is not None and b is not None and a != b


def test_edge(source, target, history, lag=1):
    """Test the directed prediction 'a change in `source` is followed (after `lag`) by a change in `target`'
    against a window of committed states `history` (list of {node: value}). Returns (hits, misses, opportunities)
    where opportunities = number of source-change events (the discriminating chances the window offered). A
    window with zero opportunities cannot corroborate anything — that is reported, not hidden."""
    hits = misses = opps = 0
    for t in range(len(history) - lag):
        s0 = history[t].get(source)
        s1 = history[t + 1].get(source)
        if not _changed(s0, s1):
            continue                                   # only source-CHANGE events can test the edge
        opps += 1
        c0 = history[t].get(target)
        c1 = history[t + lag].get(target)
        if _changed(c0, c1):
            hits += 1                                   # source changed, target responded -> consistent
        else:
            misses += 1                                 # source changed, target did NOT respond -> falsifier
    return hits, misses, opps


def _status(train_hits, train_misses, ho_hits, ho_misses, min_tests=3, reject_ratio=0.34):
    n = ho_hits + ho_misses
    if n < min_tests:
        return PROPOSED                                 # untested / insufficient discriminating opportunity
    if ho_misses == 0 and ho_hits >= min_tests:
        return CORROBORATED
    if ho_misses / n >= reject_ratio:
        return REJECTED
    return DECAYING


def corroboration_score(p):
    """Survived-tests score: held-out hits minus a DOUBLE penalty for misses (falsification is decisive).
    Can be negative. Train evidence is a tie-breaker only — it never grants standing on its own."""
    return (p.heldout_hits - 2 * p.heldout_misses) * 1000 + (p.train_hits - p.train_misses)


def _hash(*fields):
    return hashlib.sha256("|".join(str(x) for x in ("SP",) + fields).encode()).hexdigest()


def make_proposal(source, target, train_hits=0, train_misses=0):
    st = _status(train_hits, train_misses, 0, 0)
    return StructureProposal(source, target, train_hits, train_misses, 0, 0, 0, st,
                             _hash(source, target, train_hits, train_misses, 0, 0, 0))


def apply_heldout(p, hits, misses, epoch, min_tests=3, reject_ratio=0.34):
    """Fold a held-out test result into a proposal -> a NEW proposal with recomputed status. heldout_misses
    accumulates: this is the channel through which evidence DECREASES."""
    hh = p.heldout_hits + int(hits)
    hm = p.heldout_misses + int(misses)
    st = _status(p.train_hits, p.train_misses, hh, hm, min_tests, reject_ratio)
    return StructureProposal(p.source, p.target, p.train_hits, p.train_misses, hh, hm, int(epoch), st,
                             _hash(p.source, p.target, p.train_hits, p.train_misses, hh, hm, epoch))
