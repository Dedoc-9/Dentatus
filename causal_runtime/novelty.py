"""
causal_runtime/novelty.py — the epistemic seam: novelty producers + the ghost, completing the attention field.

Two epistemic inputs, kept separate (dual arithmetic separation — prior ⟂ posterior):

  U  (uncertainty axis)  : "how little we know"          — PRIOR. Aggregated from one or more producers, each
                            emitting {node: novelty_score ∈ [0,SCALE]}. dini is ONE producer; model
                            disagreement, prediction error, sensor surprise, simulation residuals are others.
                            novelty.py is PRODUCER-AGNOSTIC: it never imports a producer; it ingests scores.

  G⁺ (ghost term)        : "the world surprised the model" — POSTERIOR. ghost = observed_divergence −
                            predicted_consequence, RECTIFIED to max(0, ·). Negative ghost (model over-predicted)
                            must NOT lower attention — the model may not talk itself out of looking. An
                            UNDECLARED coupling makes a node change with predicted=0, so G⁺ = full observed:
                            a pure attention spike with no structural cause ("something matters here; I don't
                            yet know what"). This is the observable the hidden-coupling reconstruction bound
                            demanded.

Final attention (the user's equation, rectified):

    A(node) = C × P × U  +  G⁺           where C×P×U is field.future_surface (normalised), G⁺ ≥ 0

LAW (unchanged): A → computational_attention ALLOWED ; A → reality_mutation FORBIDDEN. Floats from producers
(e.g. dini_distance) are quantised to Q16 at the boundary by the caller (canon/capture); novelty.py is
integer-only. Deterministic. Stdlib only.
"""
from collections import namedtuple

from field import SCALE, future_surface, _q

NoveltySignal = namedtuple("NoveltySignal", "source_id node novelty_q16 confidence timestamp")


def signal(source_id, node, novelty_q16, confidence=SCALE, timestamp=0):
    """Wrap one producer reading as a NoveltySignal. novelty_q16, confidence ∈ [0,SCALE] (Q16)."""
    return NoveltySignal(str(source_id), node, _q(novelty_q16), _q(confidence), int(timestamp))


def ingest(source_id, scores, confidence=SCALE, timestamp=0):
    """Turn a producer's {node: novelty_q16} into NoveltySignals (one source). Deterministic order."""
    return [signal(source_id, n, scores[n], confidence, timestamp) for n in sorted(scores, key=str)]


def aggregate(signals):
    """Combine signals from any number of producers into the uncertainty field {node: U_q16}. Per node, the
    confidence-weighted MAX across producers (surprise from any credible source raises U; a confident producer
    dominates a hesitant one). Deterministic."""
    best = {}
    for s in sorted(signals, key=lambda s: (str(s.node), s.source_id)):
        contrib = s.novelty_q16 * s.confidence // SCALE
        if contrib > best.get(s.node, -1):
            best[s.node] = contrib
    return best


def _normalise(d):
    """Scale a {node: int>=0} map to Q16 [0,SCALE] by its own max (batch-relative). Empty/zero -> zeros."""
    if not d:
        return {}
    m = max(d.values())
    if m <= 0:
        return {n: 0 for n in d}
    return {n: d[n] * SCALE // m for n in d}


def ghost_field(observed_delta, predicted_consequence):
    """G⁺(node) = max(0, observed_norm − predicted_norm), both normalised to Q16 across the batch so the
    subtraction is scale-free. Positive only where the world moved a node MORE than the model predicted
    (the surprise / hidden-coupling signature). {node: ghost_q16 >= 0}."""
    obs = _normalise({n: max(0, int(v)) for n, v in observed_delta.items()})
    pred = _normalise({n: max(0, int(v)) for n, v in predicted_consequence.items()})
    nodes = set(obs) | set(pred)
    return {n: max(0, obs.get(n, 0) - pred.get(n, 0)) for n in sorted(nodes, key=str)}


def attention_field(consequence, possibility=None, uncertainty=None, ghost=None, ghost_gain=SCALE):
    """The final field A = future_surface(C,P,U) + ghost_gain·G⁺. future_surface is normalised to Q16 so it is
    additively commensurate with the Q16 ghost; ghost_gain (Q16, default 1.0) weights surprise vs structure.
    Returns {node: A}. Pure & deterministic."""
    surf = _normalise(future_surface(consequence, uncertainty or {}, possibility))
    g = ghost or {}
    nodes = set(surf) | set(g)
    return {n: surf.get(n, 0) + (_q(g.get(n, 0)) * ghost_gain // SCALE) for n in sorted(nodes, key=str)}
