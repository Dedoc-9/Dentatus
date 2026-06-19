"""
toolkit.attention — the external surface.

    from toolkit import attention
    field  = attention.observe(world)                       # default scorer = policies.future_surface
    budget = field.allocate(resources=1000, policy="future_surface")

Swap the scorer to make this "resource allocation under uncertainty", not a "future_surface library":

    from toolkit import attention
    field  = attention.observe(world, scorer=my_scorer)     # any callable item -> int
    budget = field.allocate(resources=1000)                 # ranks by the field's scorer by default

The scorer's __name__ becomes the policy column, so the score is named and inspectable, never hidden.
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
        return (f"Budget(policy={self.policy!r}, funded={len(self.chosen)}/{len(self.items)}, "
                f"spent={self.spent}/{self.resources})")


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
        """Allocate the budget. `policy` defaults to the field's scorer; pass a column name to compare
        against a baseline (e.g. "magnitude", "uniform", or "M" for the oracle upper bound)."""
        policy = policy or self.score_key
        chosen, spent = _allocate(self.items, resources, policy)
        return Budget(self.items, chosen, spent, resources, policy)


class _Attention:
    def observe(self, world, scorer=policies.future_surface):
        """Take a plain list-of-dicts world and a scorer; return a scored Field. Inputs are copied,
        not mutated — the caller's world is left untouched."""
        return Field([dict(o) for o in world], scorer)


attention = _Attention()
