"""
toolkit.attention — the external surface.

Smallest path (you never name the internal metric):

    from toolkit import attention
    budget = attention.allocate(world, resources=1000)      # observe + allocate, default scorer

Explicit path (inspect the scored field, swap the scorer):

    field  = attention.observe(world, scorer=my_scorer)     # any callable item -> int
    budget = field.allocate(resources=1000)                 # ranks by the field's scorer by default

The scorer's __name__ becomes the policy column, so the score is named and inspectable, never hidden.

Two gates protect the allocator from over-claiming:
  eligibility   an item with eligible=False (or visible=False) gets ZERO budget regardless of score
                -- importance != eligibility.
  coherence     Field.tick() ages the field's confidence; a stale field loses to the floor past its
                coherence horizon (benchmarks.coherence) -- attention requires coherence time.

The contract:   score -> allocation ,   allocation != truth.
"""
from __future__ import annotations

from .allocation import allocate as _allocate, captured as _captured
from . import policies


class Budget:
    """Result of an allocation: which items were funded, what it cost, and what it captured."""
    def __init__(self, items, chosen, spent, resources, policy):
        self.items, self.chosen, self.spent = items, chosen, spent
        self.resources, self.policy = resources, policy

    def captured(self, objective="M"):
        return _captured(self.items, self.chosen, objective)

    def __repr__(self):
        return ("Budget(policy=%r, funded=%d/%d, spent=%d/%d)"
                % (self.policy, len(self.chosen), len(self.items), self.spent, self.resources))


def _is_eligible(o):
    """The fairness gate: importance is not eligibility. Default eligible unless explicitly gated."""
    return bool(o.get("eligible", True)) and bool(o.get("visible", True))


class Field:
    """A scored view of the world. The scorer is explicit; baselines are carried for comparison."""
    def __init__(self, items, scorer):
        self.items = items
        self.scorer = scorer
        self.score_key = getattr(scorer, "__name__", "score")
        for o in items:
            o[self.score_key] = scorer(o)
            o.setdefault("magnitude", o.get("consequence", 1))
            o["uniform"] = 1                                 # cheapest-first floor, always available

    def allocate(self, resources, policy=None):
        """Allocate the budget. policy defaults to the field's scorer; pass a column name to compare
        against a baseline ("magnitude", "uniform", or "M" for the oracle). Ineligible items are
        excluded before ranking -- a high score never buys budget an item is not entitled to."""
        policy = policy or self.score_key
        eligible = [o for o in self.items if _is_eligible(o)]
        chosen, spent = _allocate(eligible, resources, policy)
        return Budget(self.items, chosen, spent, resources, policy)

    def tick(self, decay_num=4, decay_den=5):
        """Age the field one step: confidence (uncertainty) decays and the field is re-scored. A stale
        field's priorities flatten; past the coherence horizon it loses to the floor. Returns a NEW
        Field (pure) so the original is untouched."""
        aged = []
        for o in self.items:
            c = dict(o)
            c["uncertainty"] = max(1, (o.get("uncertainty", 1) * decay_num) // decay_den)
            aged.append(c)
        return Field(aged, self.scorer)


class _Attention:
    def observe(self, world, scorer=policies.future_surface):
        """Take a plain list-of-dicts world and a scorer; return a scored Field. Inputs are copied,
        not mutated -- the caller's world is left untouched."""
        return Field([dict(o) for o in world], scorer)

    def allocate(self, world, resources, scorer=policies.future_surface, policy=None):
        """Smallest path: observe + allocate in one call, without naming the internal metric."""
        return self.observe(world, scorer).allocate(resources, policy)


attention = _Attention()
