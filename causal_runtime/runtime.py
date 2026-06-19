"""
causal_runtime/runtime.py — the AttentionField: a pure-observe substrate that allocates COMPUTE, not reality.

This is the causal-allocation primitive. It ingests three observation-domain fields (consequence, uncertainty,
possibility) for a frame and produces an allocation across computational CHANNELS:

    streaming residency · AI tick rate · animation fidelity · network replication · validation depth

It is structurally incapable of mutating state: `observe()` takes plain dicts and the object stores only
derived tokens — it holds NO reference to any world, kernel, or commit path. This makes the law a property of
the type, not a discipline:

    causal_information -> computational_attention   ALLOWED
    causal_information -> reality_mutation          FORBIDDEN   (no method can reach state)

Channels are independent budgets apportioned from the SAME surface field, so render/AI/network/validation stop
inventing private proximity heuristics and share one future-structure-aware allocation. Deterministic. Stdlib.
"""
from field import attention_tokens, future_surface, _hamilton, SCALE

CHANNELS = ("streaming", "ai_tick", "fidelity", "network", "validation")


class AttentionField:
    """Pure observation -> compute allocation. No mutation surface exists."""

    def __init__(self, budgets=None, depth_levels=4, base_fresh=240):
        # per-channel total compute budget (units are channel-defined; integers)
        self.budgets = dict(budgets or {c: 1000 for c in CHANNELS})
        self.depth_levels = int(depth_levels)
        self.base_fresh = int(base_fresh)
        self._tokens = {}                         # last observed {node: AttentionToken}
        self._surface = {}

    def observe(self, consequence, uncertainty=None, possibility=None, now=0, ghost=None):
        """Ingest the frame's three substrates plus an optional epistemic GHOST (novelty.ghost_field). Returns
        {node: AttentionToken}. Pure: depends only on inputs; no side effect outside this object's telemetry;
        cannot reach any world. With a ghost, surprise pulls compute toward structurally-invisible nodes."""
        self._surface = future_surface(consequence, uncertainty or {}, possibility)
        if ghost:                                          # mirror field: ghost shifts the allocation surface
            smax = max(self._surface.values()) if self._surface else 0
            ref = smax if smax > 0 else SCALE
            from field import _q
            for n in set(self._surface) | set(ghost):
                self._surface[n] = self._surface.get(n, 0) + _q(ghost.get(n, 0)) * ref // SCALE
        self._tokens = attention_tokens(consequence, uncertainty, possibility,
                                        budget=max(self.budgets.values()) if self.budgets else 1000,
                                        depth_levels=self.depth_levels, base_fresh=self.base_fresh, now=now,
                                        ghost=ghost)
        return dict(self._tokens)

    def allocation(self):
        """{channel: {node: budget}} — each channel apportions its own budget over the shared surface field
        (Hamilton, integer-exact). The allocation is a RECOMMENDATION; nothing here applies it to state."""
        return {c: _hamilton(self._surface, self.budgets.get(c, 0)) for c in CHANNELS}

    def frontier(self, channel, k):
        """Top-k targets for a channel by recommended budget (where that channel should spend first)."""
        alloc = _hamilton(self._surface, self.budgets.get(channel, 0))
        return [n for n in sorted(alloc, key=lambda n: (-alloc[n], str(n)))[:max(0, int(k))]]

    def validation_depths(self):
        """{node: validation_depth} — how hard to verify each node's transitions this frame (depth, not truth)."""
        return {n: t.validation_depth for n, t in self._tokens.items()}

    def refresh_intervals(self):
        """{node: freshness} — recommended frames-between-refresh (keep high-surface nodes warm)."""
        return {n: t.freshness for n, t in self._tokens.items()}

    @staticmethod
    def law():
        return ("causal_information -> computational_attention ALLOWED; "
                "causal_information -> reality_mutation FORBIDDEN")
