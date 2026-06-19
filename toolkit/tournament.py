"""
toolkit.tournament — policy competition and robustness.

The central question is never "is future_surface true?" It is "used as an allocator, does this policy
outperform alternatives under stated conditions?" Two harnesses answer it:

  compare(policies, worlds=N)               one regime: rank policies by mean captured M (% of oracle)
  robustness(policies, regimes=..., N)      a policy x regime MATRIX: where does each policy win/lose?

Both hold the experiment fixed -- same worlds, same budget, same hidden objective M -- so the only
variable is the policy. Deterministic: distinct world seeds, integer math, stdlib only.

    from toolkit import compare, robustness, future_surface, magnitude, random_priority
    print(compare([future_surface, magnitude, random_priority], worlds=1000).table())
    print(robustness([future_surface, magnitude, random_priority]).table())
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


def default_regimes():
    """The four standard regimes, each a world_fn(seed): a policy is judged across all of them."""
    return {
        "clean":       benchmarks.make_world,             # signals are noisy views of truth
        "noisy":       benchmarks.make_drift_world,        # signals are pure noise
        "adversarial": benchmarks.make_adversarial_world,  # signals are confidently misleading
        "stale":       benchmarks.make_stale_world,        # signals lag a world that has drifted
    }


class Matrix:
    def __init__(self, cells, policy_names, regime_names, worlds):
        self.cells = cells                  # {regime: {policy_name: pct}}
        self.policy_names = policy_names
        self.regime_names = regime_names
        self.worlds = worlds

    def pct(self, policy, regime):
        return self.cells[regime].get(policy, 0)

    def table(self):
        regs = self.regime_names
        header = "  %-18s" % "policy" + "".join("%12s" % r for r in regs)
        lines = [header, "-" * len(header),
                 "  %-18s" % "oracle" + "".join("%11d%%" % 100 for _ in regs)]
        for p in self.policy_names:
            lines.append("  %-18s" % p + "".join("%11d%%" % self.cells[r].get(p, 0) for r in regs))
        return "\n".join(lines)

    def __repr__(self):
        return "Matrix(policies=%d, regimes=%r)" % (len(self.policy_names), self.regime_names)


def robustness(policies, regimes=None, worlds=200, budget=1000, base_seed=0):
    """policy x regime matrix of mean captured M (%% of oracle). Each regime is a world_fn(seed). The
    point is not a single winner but WHERE each policy wins and loses -- a policy survives only where
    its assumptions hold."""
    regimes = regimes or default_regimes()
    cells = {}
    for rname, wfn in regimes.items():
        res = compare(policies, worlds=worlds, world_fn=wfn, budget=budget, base_seed=base_seed)
        cells[rname] = dict(res.rows)
    return Matrix(cells, [p.__name__ for p in policies], list(regimes.keys()), worlds)
