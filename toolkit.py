"""
toolkit.py — a toolkit for uncertainty-aware resource allocation.

The whole external surface is three lines:

    from toolkit import attention

    field  = attention.observe(world)                 # score each item by its future-surface
    budget = field.allocate(resources=1000,           # spend a fixed budget where it matters most
                            policy="future_surface")

`world` is a list of items. Each item is a dict with a `cost` and three integer signals (0..1000):

    consequence  — estimated downstream effect if this item is left unresolved
    uncertainty  — how unsure we are about it right now
    possibility  — how live / reachable it is right now

    future_surface = consequence * uncertainty * possibility

That is the entire idea: under a fixed budget you cannot attend to everything, so attend to the
items that are at once consequential, uncertain, and live. This is a category people already
understand — knapsack allocation under a learned priority — not a "reality engine".

The claim is deliberately narrow and falsifiable:
  (+) when future_surface estimates true consequence, ranking by it captures more realized
      consequence than ranking by raw size, at the SAME budget.
  (-) when the estimate is bad (drift), it MUST lose to an equal-cost floor. A method that cannot
      lose is not a measurement. Both directions are proven in __main__.

Determinism: integer math, ties broken by id, stdlib only. The allocate()/captured() primitives are
identical to the ones proven in causal_runtime/allocation.py.

Run:  PYTHONHASHSEED=0 python3 toolkit.py
"""
from __future__ import annotations
import random


# ── the two proven primitives (same logic as causal_runtime/allocation.py) ──────────────────────

def allocate(items, budget, score_key, cost_key="cost"):
    """Greedy knapsack by score/cost. Returns (chosen id-set, spent). Deterministic; ties break by id."""
    ranked = sorted(items, key=lambda o: (-(o[score_key] * 1000) // max(1, o[cost_key]), str(o["id"])))
    chosen, spent = set(), 0
    for o in ranked:
        if spent + o[cost_key] <= budget:
            chosen.add(o["id"]); spent += o[cost_key]
    return chosen, spent


def captured(items, chosen, objective):
    """Σ over the chosen set of the INDEPENDENT objective — never the allocator's own score."""
    return sum(o[objective] for o in items if o["id"] in chosen)


# ── the external surface ────────────────────────────────────────────────────────────────────────

class Budget:
    """The result of an allocation: which items were funded, what it cost, and what it captured."""
    def __init__(self, items, chosen, spent, resources, policy):
        self.items, self.chosen, self.spent = items, chosen, spent
        self.resources, self.policy = resources, policy

    def captured(self, objective="M"):
        return captured(self.items, self.chosen, objective)

    def __repr__(self):
        return (f"Budget(policy={self.policy!r}, funded={len(self.chosen)}/{len(self.items)}, "
                f"spent={self.spent}/{self.resources})")


class Field:
    """A scored view of the world. The score is future_surface; baselines are carried for comparison."""
    def __init__(self, items):
        self.items = items
        for o in items:
            o["future_surface"] = max(1, (o["consequence"] * o["uncertainty"] * o["possibility"]) // 1_000_000)
            o.setdefault("magnitude", o["consequence"])     # naive baseline: spend on the biggest
            o["uniform"] = 1                                # floor: every item scored alike (cheapest-first)

    def allocate(self, resources, policy="future_surface"):
        chosen, spent = allocate(self.items, resources, policy)
        return Budget(self.items, chosen, spent, resources, policy)


class _Attention:
    def observe(self, world):
        """Take a plain list-of-dicts world and return a scored Field. Inputs are copied, not mutated."""
        return Field([dict(o) for o in world])


attention = _Attention()


# ── ONE use case + ONE benchmark + ONE measurable improvement ───────────────────────────────────
#
# Use case: a fixed simulation/compute budget must choose which world-regions to resolve at full
# fidelity. Most regions are large but inert; a few small regions sit upstream of big cascades (the
# butterfly). "Spend on the biggest" (magnitude) is the obvious policy — and it is wrong.

def make_world(n=60, seed=1, drift=False):
    """Deterministic world. M = realized consequence (the INDEPENDENT objective, never shown to the
    allocator); it is built from hidden truth. The three OBSERVED signals are noisy views of that truth
    in the informative world, and pure noise in the drift world — so a drifted estimate must fail."""
    rng = random.Random(seed)
    world = []
    for i in range(n):
        t_cons = rng.randint(1, 1000)                                 # hidden true consequence
        t_unc  = rng.randint(1, 1000)                                 # hidden true unresolved-ness
        M = max(1, (t_cons * t_unc) // 1000)                          # realized consequence avoided if funded
        size = max(1, 1000 - t_cons + rng.randint(-40, 40))          # butterfly: biggest region = most inert
        if drift:                                                     # observed signals decoupled from truth
            consequence_obs = rng.randint(1, 1000)
            uncertainty_obs = rng.randint(1, 1000)
            possibility_obs = rng.randint(1, 1000)
        else:                                                         # observed signals = noisy views of truth
            consequence_obs = max(1, t_cons + rng.randint(-80, 80))
            uncertainty_obs = max(1, t_unc + rng.randint(-80, 80))
            possibility_obs = rng.randint(300, 1000)
        world.append({
            "id": "region_%02d" % i,
            "cost": rng.randint(20, 100),                 # total demand ~3600 >> budget 1000: real scarcity
            "consequence": consequence_obs,
            "uncertainty": uncertainty_obs,
            "possibility": possibility_obs,
            "magnitude": size,
            "M": M,
        })
    return world


def benchmark(seed=1, budget=1000, drift=False):
    field = attention.observe(make_world(seed=seed, drift=drift))
    out = {}
    for policy in ("future_surface", "magnitude", "uniform", "M"):     # M = oracle upper bound
        out[policy] = field.allocate(budget, policy=policy).captured("M")
    return out


def _pct(x, whole):
    return (100 * x) // max(1, whole)


if __name__ == "__main__":
    BUDGET = 1000

    print("=" * 78)
    print("toolkit — uncertainty-aware resource allocation")
    print("use case: pick which world-regions to simulate at full fidelity under a fixed budget")
    print("=" * 78)

    # ---- the one benchmark: informative world ----
    r = benchmark(seed=1, budget=BUDGET)
    oracle = r["M"]
    fs, mag, floor = r["future_surface"], r["magnitude"], r["uniform"]
    print(f"\nbudget = {BUDGET}   objective M = realized downstream consequence captured")
    print(f"  oracle (allocate by M itself, upper bound) : {oracle:6d}   {_pct(oracle,oracle):3d}% of oracle")
    print(f"  future_surface (uncertainty-aware)         : {fs:6d}   {_pct(fs,oracle):3d}% of oracle")
    print(f"  magnitude      (spend on the biggest)      : {mag:6d}   {_pct(mag,oracle):3d}% of oracle")
    print(f"  uniform        (cheapest-first floor)      : {floor:6d}   {_pct(floor,oracle):3d}% of oracle")

    # ---- the one measurable improvement ----
    ratio = (100 * fs) // max(1, mag)
    print("\nMEASURABLE IMPROVEMENT")
    print(f"  uncertainty-aware allocation captured {ratio/100:.2f}x the realized consequence of")
    print(f"  size-based allocation at IDENTICAL budget "
          f"({_pct(fs,oracle)}% vs {_pct(mag,oracle)}% of the oracle ceiling).")

    # ---- the falsifiability check: a bad estimate must LOSE to the floor ----
    d = benchmark(seed=1, budget=BUDGET, drift=True)
    print("\nFALSIFIABILITY (the method must be able to lose)")
    print(f"  under a drifted estimate: future_surface {_pct(d['future_surface'],d['M'])}% "
          f"vs uniform floor {_pct(d['uniform'],d['M'])}% of oracle "
          f"-> {'LOSES to floor (correct)' if d['future_surface'] <= d['uniform'] else 'beats floor'}")

    # ---- self-check: the two claims hold, or the file fails loudly ----
    assert fs > mag, "informative world: future_surface must beat magnitude"
    assert fs > floor, "informative world: future_surface must beat the floor"
    assert d["future_surface"] <= d["uniform"], "drift world: a bad estimate must NOT beat the floor"
    print("\n[OK] both claims hold: informative -> wins; drift -> loses to floor.")
