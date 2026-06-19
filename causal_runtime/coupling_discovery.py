"""
causal_runtime/coupling_discovery.py — turn a persistent ghost into a PROPOSED graph edge, never a real one.

This is the bridge between the two asymmetries the runtime now has:

    declared structure → consequence → attention      (known causality)
    unknown structure  → ghost       → attention      (observed mismatch)

The question it answers: WHEN does a repeated ghost become evidence that the declared dependency graph is
incomplete? It does NOT answer it by editing the graph. It accumulates evidence and emits a proposal for an
external authority (human/tool) to review.

THE EPISTEMIC TRAP (of self-modifying systems) and the four locks that close it
-------------------------------------------------------------------------------
A system that learns its own model can drift: the learning loop adapts toward whatever reduces its own
surprise, which can mean *inventing* structure or suppressing inconvenient observations — the discovery
mechanism corrupts the model it was meant to improve. This module quarantines discovery to a proposal channel:

  (1) PROPOSE, NEVER COMMIT  — the registry holds NO handle to any consequence.Graph; no method writes an edge.
                               `ghost → proposed coupling` ALLOWED; `ghost → actual coupling` FORBIDDEN (type-level).
  (2) EVIDENCE, NOT AUTHORITY — accumulate INTEGER frequency + ghost_total across DISTINCT contexts; never a
                               `confidence += ghost` float that silently becomes a control path.
  (3) EXTERNAL REVIEW GATE    — promotion of a candidate to a real edge happens only through review (the airlock
                               pattern, `intent ≠ authority`); this module produces the queue, not the verdict.
  (4) REALITY UNTOUCHED       — even an ACCEPTED proposal updates a *model* (the consequence graph); the
                               committed world hash is unaffected (`graph improvement ≠ world modification`).

A ghost is evidence of MODEL FAILURE, not a new fact about the world. Deterministic integer math. Stdlib only.
"""
import hashlib
from collections import namedtuple

CouplingCandidate = namedtuple(
    "CouplingCandidate",
    "source target frequency ghost_total contexts first_seen last_seen h",
)


def _hash(source, target, frequency, ghost_total, contexts, first_seen, last_seen):
    payload = b"|".join([b"COUP", str(source).encode(), str(target).encode(),
                         str(int(frequency)).encode(), str(int(ghost_total)).encode(),
                         str(int(contexts)).encode(), str(int(first_seen)).encode(),
                         str(int(last_seen)).encode()])
    return hashlib.sha256(payload).hexdigest()


class CouplingRegistry:
    """Append-only accumulator of coupling EVIDENCE. It is structurally incapable of mutating a graph: it stores
    only candidate records and exposes read/propose verbs. There is no `apply`, `commit`, or graph reference."""

    def __init__(self):
        self._c = {}                                   # (source, target) -> mutable evidence dict

    def observe(self, changed_sources, ghost, declared_parents=None, context="", now=0):
        """Record one frame of evidence. For every target with a positive ghost (it moved more than the declared
        model predicted), every co-changed node that is NOT already a declared parent (and not the target
        itself) becomes/with-increments a CouplingCandidate. PURE w.r.t. the world: reads plain dicts, writes
        only this registry. `context` tags the situation (distinct contexts are the noise filter)."""
        declared_parents = declared_parents or {}
        for t in sorted(ghost.keys(), key=str):
            if ghost[t] <= 0:
                continue
            parents = set(declared_parents.get(t, ()))
            for s in sorted(changed_sources, key=str):
                if s == t or s in parents:
                    continue                            # already declared, or self -> not a candidate
                key = (s, t)
                rec = self._c.get(key)
                if rec is None:
                    rec = {"frequency": 0, "ghost_total": 0, "contexts": set(),
                           "first_seen": int(now), "last_seen": int(now)}
                    self._c[key] = rec
                rec["frequency"] += 1
                rec["ghost_total"] += int(ghost[t])
                rec["contexts"].add(context)
                rec["last_seen"] = int(now)

    def candidate(self, source, target):
        rec = self._c.get((source, target))
        if rec is None:
            return None
        nctx = len(rec["contexts"])
        return CouplingCandidate(
            source=source, target=target, frequency=rec["frequency"], ghost_total=rec["ghost_total"],
            contexts=nctx, first_seen=rec["first_seen"], last_seen=rec["last_seen"],
            h=_hash(source, target, rec["frequency"], rec["ghost_total"], nctx,
                    rec["first_seen"], rec["last_seen"]),
        )

    def candidates(self):
        """All accumulated candidates, sorted by (−frequency, −ghost_total, str(key)). Evidence, not verdicts."""
        out = [self.candidate(s, t) for (s, t) in self._c]
        return sorted(out, key=lambda c: (-c.frequency, -c.ghost_total, str((c.source, c.target))))

    def proposals(self, min_frequency=3, min_contexts=2):
        """The review queue: candidates that REPRODUCE — frequency ≥ min_frequency AND seen across ≥
        min_contexts distinct contexts. The distinct-context requirement rejects a single repeated anomaly.
        These are PROPOSED couplings for external review; this method does not promote anything."""
        return [c for c in self.candidates()
                if c.frequency >= min_frequency and c.contexts >= min_contexts]
