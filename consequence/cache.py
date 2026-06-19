"""
consequence/cache.py — bounded, deterministic token cache; turns the field into a frame-budget allocator.

The runtime cannot fingerprint every node every frame (the measured ~56x cost). The cache holds the most
recent FutureSensitivityToken per node, evicts deterministically when full, drops expired tokens on tick(now),
and answers the only question the scheduler asks:

    frontier(budget) -> the top-`budget` nodes by consequence score   (where to spend this frame)

This is a SCHEDULING horizon, not a physical one — an entity outside the budget is not deleted from reality,
it is merely not re-simulated this frame (consequence -> allocation, never consequence -> truth). All ordering
is total and deterministic: sort key is (score DESC, str(entity) ASC); eviction drops the lowest such. Stdlib.
"""


class ConsequenceCache:
    def __init__(self, capacity=4096):
        self.capacity = int(capacity)
        self._tok = {}                                  # entity -> FutureSensitivityToken

    def put(self, token):
        """Insert/replace the token for token.entity, then evict to capacity (lowest score first)."""
        self._tok[token.entity] = token
        if len(self._tok) > self.capacity:
            self._evict()
        return self

    def get(self, entity):
        return self._tok.get(entity)

    def _order(self):
        # total order: high score first, ties broken by str(entity) ascending -> deterministic
        return sorted(self._tok.values(), key=lambda t: (-t.score, str(t.entity)))

    def _evict(self):
        keep = self._order()[: self.capacity]
        self._tok = {t.entity: t for t in keep}

    def tick(self, now):
        """Drop every token whose scheduling horizon has passed (expires <= now). Returns #dropped."""
        before = len(self._tok)
        self._tok = {e: t for e, t in self._tok.items() if t.expires > now}
        return before - len(self._tok)

    def frontier(self, budget):
        """The top-`budget` entities by consequence score — the causal frontier to simulate/validate this
        frame. Deterministic. Returns a list of entities (highest consequence first)."""
        return [t.entity for t in self._order()[: max(0, int(budget))]]

    def scores(self):
        """{entity: score} snapshot — the shared field every consumer reads (render/AI/net/validate)."""
        return {e: t.score for e, t in self._tok.items()}

    def __len__(self):
        return len(self._tok)
