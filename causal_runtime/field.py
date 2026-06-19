"""
causal_runtime/field.py — the AttentionToken and the future-surface field.

OBSERVATION-DOMAIN primitive. It composes three orthogonal observables of a deterministic world and emits a
recommendation for where computation should be spent. It NEVER touches state. The directional law (enforced
structurally: these functions take plain numbers and return plain records, holding no handle to any world):

    causal_information -> computational_attention      ALLOWED
    causal_information -> reality_mutation             FORBIDDEN

The composite (DUAL ARITHMETIC SEPARATION — three orthogonal axes, product kept WITH its components, never
collapsed, so each remains independently auditable):

    future_surface(node) =  consequence(node)  ×  uncertainty(node)  ×  possibility(node)
                            ─────────────────     ────────────────     ────────────────
                            dependency topology   epistemic unknown    admissible freedom
                            (how many futures     (how unsure we are   (how much lawful
                             depend on it)         of its future)       variation it has)

`consequence` is a raw score (e.g. consequence.fingerprint score). `uncertainty`, `possibility` ∈ [0, SCALE]
(Q16 fractions; possibility omitted -> treated as 1.0). The token carries the recommendation only:

    AttentionToken(target, consequence_score, uncertainty_score, possibility_score, surface,
                   recommended_budget, validation_depth, freshness, expires, h)

`recommended_budget` apportions a fixed compute budget across nodes (Hamilton largest-remainder, integer-exact,
sum == budget). `validation_depth` is a batch-relative bucket in [0, depth_levels]. `freshness` is the
recommended refresh interval in frames (high surface -> small interval -> keep warm) — a SCHEDULING horizon,
never a physical lifetime. `h = SHA256` over the tuple is a structural index (no semantics). Stdlib only.
"""
import hashlib
from collections import namedtuple

SCALE_BITS = 16
SCALE = 1 << SCALE_BITS

AttentionToken = namedtuple(
    "AttentionToken",
    "target consequence_score uncertainty_score possibility_score surface "
    "recommended_budget validation_depth freshness expires h",
)


def _q(x):
    """Clamp an integer to [0, SCALE] (a Q16 fraction)."""
    return max(0, min(int(x), SCALE))


def future_surface(consequence, uncertainty, possibility=None):
    """The composite future-surface field {node: surface}. consequence is a raw integer score; uncertainty
    and possibility are Q16 fractions in [0,SCALE] (possibility None => 1.0). Product requantized; components
    are NOT discarded (the token keeps them)."""
    out = {}
    for n in sorted(consequence.keys(), key=str):
        c = int(consequence[n])
        u = _q(uncertainty.get(n, SCALE)) if uncertainty else SCALE
        p = _q(possibility.get(n, SCALE)) if possibility else SCALE
        out[n] = c * u // SCALE * p // SCALE
    return out


def causal_pressure(surface):
    """Normalized causal pressure ‰ per node = surface / Σsurface (in per-mille, integer). A unitless shape of
    where future structure concentrates. Σ over nodes ~ 1000 (largest-remainder safe; telemetry only)."""
    tot = sum(surface.values())
    if tot <= 0:
        return {n: 0 for n in surface}
    return {n: surface[n] * 1000 // tot for n in sorted(surface, key=str)}


def _hamilton(weights, budget):
    """Integer largest-remainder apportionment of `budget` over `weights` {k:w>=0}. Sum of result == budget
    (if budget>=0). Deterministic tie-break by str(key)."""
    keys = sorted(weights.keys(), key=str)
    tot = sum(max(0, weights[k]) for k in keys)
    budget = max(0, int(budget))
    if tot <= 0 or budget == 0:
        base = {k: 0 for k in keys}
        for i in range(budget):                       # nothing to weight by -> spread evenly, deterministically
            base[keys[i % len(keys)]] += 1 if keys else 0
        return base
    quota = {k: (max(0, weights[k]) * budget) / tot for k in keys}
    floor = {k: int(quota[k]) for k in keys}
    used = sum(floor.values())
    rem = budget - used
    order = sorted(keys, key=lambda k: (-(quota[k] - floor[k]), str(k)))
    for i in range(rem):
        floor[order[i % len(order)]] += 1
    return floor


def attention_tokens(consequence, uncertainty=None, possibility=None,
                     budget=1000, depth_levels=4, base_fresh=240, now=0):
    """Build {node: AttentionToken} from the three substrates. recommended_budget = Hamilton(surface, budget);
    validation_depth = batch-relative bucket in [0, depth_levels]; freshness = base_fresh // (depth+1)
    (higher surface -> refresh sooner). Pure & deterministic."""
    surface = future_surface(consequence, uncertainty or {}, possibility)
    alloc = _hamilton(surface, budget)
    smax = max(surface.values()) if surface else 0
    tokens = {}
    for n in sorted(surface, key=str):
        s = surface[n]
        depth = (s * depth_levels // (smax + 1)) if smax > 0 else 0
        fresh = max(1, base_fresh // (depth + 1))
        u = _q(uncertainty.get(n, SCALE)) if uncertainty else SCALE
        p = _q(possibility.get(n, SCALE)) if possibility else SCALE
        payload = b"|".join([b"ATT", str(n).encode()] +
                            [str(int(x)).encode() for x in
                             (consequence[n], u, p, s, alloc[n], depth, fresh, now + fresh)])
        tokens[n] = AttentionToken(
            target=n, consequence_score=int(consequence[n]), uncertainty_score=u,
            possibility_score=p, surface=s, recommended_budget=alloc[n],
            validation_depth=depth, freshness=fresh, expires=now + fresh,
            h=hashlib.sha256(payload).hexdigest(),
        )
    return tokens
