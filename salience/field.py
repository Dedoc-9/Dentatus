"""
salience/field.py — a possibility-aware allocation field.

A new scheduling signal. Render/AI/streaming/physics budgets are usually distributed by distance, visibility,
screen size, LOD. This allocates a budget by **possibility density** instead: how many meaningful lawful
futures surround a state (e.g. `airlock/horizon.py`'s possibility pressure). A quiet valley may have enormous
geometric detail but little possibility; a doorway may have little geometry but huge possibility (it changes
quests, AI, combat, economy, narrative). This field puts the compute on the doorway.

THE LAW (a corollary of `telemetry ≠ control`):
    possibility  →  ALLOCATION (compute / attention budget)     ALLOWED
    possibility  →  PHYSICS (what the kernel commits)            FORBIDDEN
Allocation steers *where computation matters*, never *what becomes real*. The committed world is byte-for-byte
identical regardless of how budget is distributed. This makes the system a **possibility-aware runtime**, not
a speculative ontology — and keeps determinism + the integrity laws intact.

`allocate` is exact-integer (Hamilton largest-remainder apportionment): the shares sum EXACTLY to the budget,
deterministically (ties broken by region key). No floats. Stdlib only.
"""


def allocate(weights, budget, floor=0):
    """Distribute an integer `budget` of a compute resource across regions by their density `weights`
    (non-negative ints — e.g. possibility pressure). `floor` = a guaranteed minimum per region. Returns
    {region: allocation} summing EXACTLY to `budget`. Deterministic (largest-remainder, key-ordered ties)."""
    regions = sorted(weights)
    n = len(regions)
    if n == 0:
        return {}
    base = {r: floor for r in regions}
    R = budget - floor * n
    if R < 0:                                   # floors exceed budget: drop floors, apportion the whole budget
        base = {r: 0 for r in regions}
        R = budget
    if R <= 0:
        return base
    w = {r: max(int(weights[r]), 0) for r in regions}
    W = sum(w.values())
    if W == 0:                                  # no possibility anywhere ⇒ apportion the remainder evenly
        w = {r: 1 for r in regions}
        W = n
    quota, rem = {}, {}
    given = 0
    for r in regions:
        prod = R * w[r]
        quota[r] = prod // W
        rem[r] = prod % W
        given += quota[r]
    leftover = R - given
    order = sorted(regions, key=lambda r: (-rem[r], r))   # highest remainder first; key-ordered ties
    for i in range(leftover):
        quota[order[i]] += 1
    return {r: base[r] + quota[r] for r in regions}


def density(pressures):
    """Build the weight map from a {region: possibility_pressure} signal (e.g. horizon.possibility_pressure).
    Pure pass-through with a non-negative-int guard — keeps `salience` decoupled from any specific source."""
    return {r: max(int(p), 0) for r, p in pressures.items()}


def concentration(allocation):
    """A scalar summary of how PEAKED an allocation is (max share · 1000 / total) — high ⇒ compute is focused
    on a few high-possibility regions; low ⇒ spread thin. Pure observability over the allocation itself."""
    tot = sum(allocation.values())
    return (max(allocation.values()) * 1000 // tot) if tot else 0
