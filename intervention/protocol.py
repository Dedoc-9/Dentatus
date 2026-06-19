"""
intervention/protocol.py — an intervention is a QUESTION, not a mutation.

Observation tells you what correlates; intervention tells you what survives when the world is deliberately
perturbed under controlled rules. This module defines the request object and the airlock authorization gate.
It NEVER runs an experiment and NEVER touches state — it only forms and admits questions.

An InterventionCandidate does not assert "A causes C". It asks: "if A is held constant for one controlled
counterfactual, does C still diverge?" The airlock decides whether that question is legal, bounded, and
admissible before any experiment is allowed to run (in experiment.py, on a discarded shadow world).

    causal_information → attention    ALLOWED
    causal_information → proposal     ALLOWED
    causal_information → experiment   ALLOWED (airlock-authorized, shadow-only)
    causal_information → truth        FORBIDDEN

Deterministic. Stdlib only.
"""
import hashlib
from collections import namedtuple

InterventionCandidate = namedtuple(
    "InterventionCandidate",
    "source target hypothesis expected_effect allowed_scope rollback_boundary h",
)
AuthVerdict = namedtuple("AuthVerdict", "admitted reason candidate_h")


def _hash(source, target, hypothesis, expected_effect, allowed_scope, rollback_boundary):
    payload = b"|".join([b"IVN", str(source).encode(), str(target).encode(), hypothesis.encode(),
                         str(int(expected_effect)).encode(), str(int(allowed_scope)).encode(),
                         str(int(rollback_boundary)).encode()])
    return hashlib.sha256(payload).hexdigest()


def make(source, target, hypothesis=None, expected_effect=0, allowed_scope=1, rollback_boundary=8):
    """Form an intervention request. `allowed_scope` = how many nodes the experiment may hold/observe;
    `rollback_boundary` = how many steps the counterfactual may run before it must be discarded."""
    hypothesis = hypothesis or ("does do(%s) change %s?" % (source, target))
    h = _hash(source, target, hypothesis, expected_effect, allowed_scope, rollback_boundary)
    return InterventionCandidate(source, target, hypothesis, int(expected_effect),
                                 int(allowed_scope), int(rollback_boundary), h)


def from_coupling(coupling_candidate, allowed_scope=1, rollback_boundary=8):
    """Bridge: a persistent CouplingCandidate (source, target, ghost_total) becomes the QUESTION 'does
    do(source) change target?'. The ghost magnitude is recorded as the expected_effect prior, nothing more."""
    return make(coupling_candidate.source, coupling_candidate.target,
                expected_effect=getattr(coupling_candidate, "ghost_total", 0),
                allowed_scope=allowed_scope, rollback_boundary=rollback_boundary)


def authorize(candidate, scope_limit=4, max_rollback=64):
    """The airlock gate. An experiment runs ONLY if its question is legal, bounded, and rollback-safe. This is
    the membrane pattern (intent ≠ authority): the request cannot authorize itself. Pure verdict, no run."""
    if candidate.source == candidate.target:
        return AuthVerdict(False, "source == target (not an intervention)", candidate.h)
    if candidate.allowed_scope <= 0 or candidate.allowed_scope > scope_limit:
        return AuthVerdict(False, "scope %d outside (0, %d]" % (candidate.allowed_scope, scope_limit), candidate.h)
    if candidate.rollback_boundary <= 0 or candidate.rollback_boundary > max_rollback:
        return AuthVerdict(False, "rollback_boundary %d outside (0, %d]" % (candidate.rollback_boundary, max_rollback), candidate.h)
    return AuthVerdict(True, "admitted", candidate.h)
