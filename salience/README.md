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
PYTHONHASHSEED=0 python3 demo_bench.py               # Distance vs Cheap vs True falsification (cheap-wins)
PYTHONHASHSEED=0 python3 tests/test_salience.py      # 15 unit tests
```

## The Truth / Attention scheduler split (multiplayer-safe)

For competitive integrity, the engine is two schedulers that never mix:

```
TRUTH scheduler      authoritative · NEVER possibility-aware · physics, anti-cheat, state identity, replay
ATTENTION scheduler  possibility-aware · controls ONLY non-authoritative detail: AI depth, streaming,
                     animation, rendering, audio, NPC cognition, tooling
```

The truth scheduler decides *reality*; the attention scheduler decides *detail*. `possibility → allocation`
governs only the attention scheduler. Authoritative gameplay compute stays full-rate for every match-relevant
entity; salience may only demote the **provably irrelevant** (and a demoted region still enforces the hard
gates — `anti_cheat` occlusion, `airlock` bounds — at a lower update rate). The possibility field is computed
server-authoritatively, so attention cannot be adversarially steered.

## The Possibility Atlas (possibility is terrain, not a per-frame quantity)

True possibility costs ~56× a sim step — fatal per frame. So possibility is **cached like terrain**:
`atlas.py` holds an estimate per region (built, sampled O(1), refreshed incrementally under a maintenance
budget). A cheap O(local) predictor (`predictor.py`) estimates possibility from local features, calibrated by
*occasional* expensive `horizon` rollouts. The 240 Hz allocator only *samples* the atlas.

## Falsification: Distance vs Cheap vs True (`demo_bench.py`)

The decisive question is not "does possibility beat distance" (trivially yes) but **can a cheap predictor
approximate possibility well enough to beat distance after overhead?** Measured on 60 regions (held-out 30):

```
cheap predictor:  Spearman 0.69, but TOP-20% ranking = 1.00 (gets the high-possibility regions right)
quality (compute landed on true possibility):  true 0.118 · cheap 0.118 · distance 0.034
  → cheap keeps 100% of true's quality and 3.4× distance's quality
cost/region:  distance 0.07us · cheap 0.46us · true 609us  (cheap = 0.08% of true)
atlas freshness @50us/frame:  cheap refreshes all in 1 frame · true takes 366  → VERDICT: cheap-wins
```

The honest correction the prototype forced: naive `ROA = impactful/cost` *over-rewards the cheapest* signal
(distance), so the right frame is the **atlas** — per-frame all signals are O(1) lookups; the differentiators
are *quality* (does compute land on possibility) and *freshness* (can the atlas be refreshed cheaply enough
to stay current). Cheap wins both; distance loses quality; true loses freshness.

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
| `predictor.py` | the **cheap O(local) possibility predictor** — local features, calibrated vs true `horizon` |
| `atlas.py` | the **Possibility Atlas** — possibility cached as terrain (build · sample O(1) · budgeted refresh) |
| `bench.py` | the **Distance vs Cheap vs True falsification** — accuracy, quality, cost, freshness, ROA verdict |
| `demo_bench.py` | the decisive experiment over real `horizon` ground truth |
| `demo_salience.py` | the full pipeline: physics → possibility geometry → compute budget |
| `tests/test_salience.py` | 15 unit tests |
