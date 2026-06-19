# salience — a possibility-aware allocation field

A new scheduling signal. Compute budgets (render · AI · streaming · physics · audit) are usually distributed
by **distance, visibility, screen size, LOD**. `salience` distributes them by **possibility density** — how
many meaningful *lawful futures* surround a state (`airlock/horizon.py`'s possibility pressure).

A quiet valley may have enormous geometric detail but almost no possibility. A doorway may have little
geometry but huge possibility — crossing it changes quests, AI, combat, economy, narrative. `salience` puts
the compute on the **doorway**. That is something distance/LOD cannot see.

## The law (a corollary of `telemetry ≠ control`)

```
possibility  →  ALLOCATION (compute / attention budget)     ALLOWED
possibility  →  PHYSICS (what the kernel commits)            FORBIDDEN
```

Allocation steers *where computation matters*, never *what becomes real*. The committed world is byte-for-byte
identical regardless of how budget is distributed — so this is a **possibility-aware runtime**, not a
speculative ontology, and determinism + the integrity laws stay intact. (Structurally: `salience` emits a
budget and has no path to any kernel/state.)

## What it does

`allocate(weights, budget, floor)` apportions an integer budget across regions by their density weights using
**Hamilton largest-remainder** — exact (shares sum to the budget), deterministic (ties broken by region key),
no floats. `density()` builds weights from a `{region: possibility_pressure}` signal; `concentration()`
summarizes how peaked an allocation is.

```
PYTHONHASHSEED=0 python3 demo_salience.py            # physics → horizon → salience: doorway outranks valley
PYTHONHASHSEED=0 python3 tests/test_salience.py      # 8 unit tests
```

## Honest bound

`salience` reallocates *compute*, not reality — it does not make a world more *real*, only more *attended to*
where lawful possibility is densest. The result is not more polygons; it is **more felt potential per frame**
(a player feels exposure to a rich field of unrealized alternatives — "the world felt alive"). It measures
density *under the declared structure* (airlock + adapter + constraints), never that the structure is right.
`integrity ≠ truth`.

## Files

| File | Role |
|---|---|
| `field.py` | `allocate` (exact largest-remainder), `density`, `concentration` — the allocation field |
| `demo_salience.py` | the full pipeline: physics → possibility geometry → compute budget |
| `tests/test_salience.py` | 8 unit tests |
