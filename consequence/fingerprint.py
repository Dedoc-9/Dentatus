"""
consequence/fingerprint.py — the FutureSensitivityToken: a node's consequence as a hash-indexed observable.

CORRECTION-OF-SPEC (dev note, Ghost in the design). The proposed fingerprint was

    C = dependency_mass × propagation_depth × branching_factor × uncertainty

but `dependency_mass` (graph.dependency_mass) is ALREADY a bounded BFS that integrates propagation depth and
branching factor and edge weights. Re-multiplying them double-counts the same topology. The information-bearing
decomposition keeps DUAL ARITHMETIC SEPARATION — forward/structural ⟂ dual/epistemic, no collapse:

    C(node, Δ) =   Δ                ×   dependency_mass(node)   ×   uncertainty(node)
                   perturbation         structural topology         epistemic unknown
                   (extractor)          (already depth×branch)      (orthogonal new axis)

Only `uncertainty` carries information `dependency_mass` does not already contain. uncertainty ∈ [0, SCALE]
is supplied by the caller (e.g. variance of the node's recent deltas, model disagreement, sensor noise) — it
is NEVER derived from magnitude or position, and it weights ATTENTION only (consequence -> allocation, never
consequence -> truth).

The token is content-addressed: h = SHA256 over its full tuple, a STRUCTURAL INDEX (it identifies the token,
it does not encode any semantic interpretation). `expires` is a SCHEDULING horizon (a frame budget), never a
physical lifetime. Deterministic integer math; stdlib only.
"""
import hashlib
from collections import namedtuple

from graph import SCALE, dependency_mass

FutureSensitivityToken = namedtuple(
    "FutureSensitivityToken",
    "entity impact mass reachable_dependents uncertainty score expires h",
)


def _canon_int(x):
    return str(int(x)).encode()


def fingerprint(graph, node, magnitude, uncertainty=SCALE, now=0, ttl=240,
                reachable_dependents=0, depth=6, decay=(9, 10)):
    """Build the FutureSensitivityToken for `node` under a perturbation of size `magnitude`.

        score = magnitude · dependency_mass · uncertainty   (both extra factors are Q16 -> shift back twice)

    uncertainty defaults to SCALE (=1.0, maximally unsure -> pure structural consequence). `now`/`ttl` set the
    scheduling-horizon expiry. `reachable_dependents` is the frontier size (from propagation.region_size);
    it is recorded as telemetry, not multiplied in. h indexes the token. Deterministic."""
    if isinstance(magnitude, float) or isinstance(uncertainty, float):
        raise TypeError("consequence.fingerprint: float input refused (canonical integers only)")
    mass = dependency_mass(graph, node, depth, decay)               # Q16 structural
    u = max(0, min(int(uncertainty), SCALE))
    score = int(magnitude) * mass // SCALE * u // SCALE             # dual product, requantized
    expires = int(now) + int(ttl)
    payload = b"|".join([
        b"FST", str(node).encode(),
        _canon_int(magnitude), _canon_int(mass), _canon_int(reachable_dependents),
        _canon_int(u), _canon_int(score), _canon_int(expires),
    ])
    h = hashlib.sha256(payload).hexdigest()
    return FutureSensitivityToken(
        entity=node, impact=int(magnitude), mass=mass,
        reachable_dependents=int(reachable_dependents), uncertainty=u,
        score=score, expires=expires, h=h,
    )


def consequence_score(graph, node, magnitude, uncertainty=SCALE, depth=6, decay=(9, 10)):
    """The bare dual-separated consequence value (no token wrapper). magnitude·mass·uncertainty, requantized."""
    mass = dependency_mass(graph, node, depth, decay)
    u = max(0, min(int(uncertainty), SCALE))
    return int(magnitude) * mass // SCALE * u // SCALE
