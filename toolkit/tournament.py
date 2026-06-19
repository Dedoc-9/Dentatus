"""
toolkit.tournament — a policy competition harness.

The central question of the toolkit is not "is future_surface true?" It is "used as an allocator,
does this policy outperform alternatives under stated conditions?" `compare` answers exactly that:
it runs every policy on the SAME worlds, the SAME budget, and the SAME hidden objective M, then ranks
them by average captured M as a percentage of the oracle.

    from toolkit import compare, future_surface, magnitude, random_priority
    print(compare([future_surface, magnitude, random_priority], worlds=1000).table())

Deterministic: each world has a distinct seed; integer math; stdlib only.
"""
from __future__ import annotations

from .attention import attention
from . import benchmarks


class Result:
    def __init__(self, rows, worlds, budget):
        self.rows = rows            # list of (policy_name, pct_of_oracle), ranked desc
        self.worlds = worlds
        self.budget = budget

    def rank(self):
        return [name for name, _ in self.rows]

    def pct(self, name):
        return dict(self.rows).get(name)

    def table(self):
        out = ["policy                 avg captured M (%% of oracle, %d worlds)" % self.worlds,
               "-" * 58, "  %-20s %3d%%" % ("oracle", 100)]
        for name, pct in self.rows:
            out.append("  %-20s %3d%%" % (name, pct))
        return "\n".join(out)

    def __repr__(self):
        return "Result(worlds=%d, top=%r)" % (self.worlds, self.rows[0] if self.rows else None)


def compare(policies, worlds=1000, world_fn=None, budget=1000, base_seed=0):
    """Run each policy over `worlds` distinct worlds; rank by mean captured M as %% of the oracle.
    `policies` is a list of callables item->int. `world_fn(seed=...)` defaults to benchmarks.make_world."""
    world_fn = world_fn or benchmarks.make_world
    totals = {p.__name__: 0 for p in policies}
    oracle_total = 0
    for s in range(base_seed, base_seed + worlds):
        w = world_fn(seed=s)
        oracle_total += attention.observe(w).allocate(budget, policy="M").captured("M")
        for p in policies:
            totals[p.__name__] += attention.observe(w, scorer=p).allocate(budget).captured("M")
    rows = sorted((((100 * tot) // max(1, oracle_total), name) for name, tot in totals.items()),
                  reverse=True)
    return Result([(name, pct) for pct, name in rows], worlds, budget)
