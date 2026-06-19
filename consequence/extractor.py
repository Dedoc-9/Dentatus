"""
consequence/extractor.py — the PURE Δstate observer.

Operator OBS in the pipeline ... -> POST STATE -> [extractor] -> changed-set. Given two immutable state
snapshots (pre, post), it returns ONLY the set of changed node-ids and a magnitude per change. It holds no
handle that can mutate either state: `cause-field -> state` is FORBIDDEN here as a TYPE property, not a
discipline (the function's signature cannot write back). This is the operational entry point that makes the
consequence field native: the runtime diffs each committed transition, never the proposer.

State model (adapter-light): a `state` is a mapping {node_id: int}. Magnitude of a change is the integer
metric |post - pre| for numeric values, or SCALE for appear/disappear (a structural change of full size).
Deterministic: changed-set iteration is sorted by str(node). Stdlib only.
"""
SCALE_BITS = 16
SCALE = 1 << SCALE_BITS


def delta_magnitude(a, b):
    """Integer change metric between two node values. |b-a| if both int; SCALE if one side is absent
    (None) -> appear/disappear is a full-size structural change. Refuses floats (Iron Canon: no drift)."""
    if isinstance(a, float) or isinstance(b, float):
        raise TypeError("consequence.extractor: float state value refused (canonical integers only)")
    if a is None or b is None:
        return SCALE
    return abs(int(b) - int(a))


def extract(pre, post):
    """PURE diff. Returns (changed, magnitudes):
        changed    : frozenset of node-ids whose value differs (or appeared/disappeared)
        magnitudes : {node_id: int magnitude} over exactly that changed set
    No mutation of pre/post; no feedback path. Deterministic."""
    keys = set(pre.keys()) | set(post.keys())
    magnitudes = {}
    for n in sorted(keys, key=str):
        a = pre.get(n)
        b = post.get(n)
        if a == b:
            continue
        m = delta_magnitude(a, b)
        if m > 0:
            magnitudes[n] = m
    return frozenset(magnitudes.keys()), magnitudes
