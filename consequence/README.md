# consequence — the State-Graph Taint Map (the shared "what matters next?" field)

A general-purpose deterministic primitive for **consequence-aware runtimes**. The world is a dependency
graph — *node* = an entity/state element, *edge* `u→v` = how strongly `v` depends on `u`, a node's
**future sensitivity** = its downstream weighted reachability. From it falls one **consequence field** that
every subsystem reads with the same question — *what matters next?*

## The law it introduces — `consequence ≠ magnitude`

```
consequence(node, Δ) = Δ · dependency_mass(node)  ≈  physical_delta · state_dependency · future_branching
```

A *tiny* delta at a high-dependency **hub** outweighs a *large* delta at a **leaf** — the butterfly. Measured:
the *same* perturbation is **~37× more consequential** at a hub than a leaf, and a 10× *smaller* perturbation
at the hub still wins (`demo_consequence.py`). Consequence is not energy, not motion magnitude, not proximity
— it is *position in the dependency graph*.

## One field, many consumers

The per-node consequence field is the substrate the whole runtime shares:

```
rendering → where to spend pixels      AI → where to think          network → what to replicate
physics   → where to validate (depth)  streaming → what is resident
```

so `salience` (compute), `airlock/impact` (validation depth), network priority, and AI attention all read the
**same** field instead of each inventing its own proximity heuristic.

## The standing law

```
consequence → allocation · validation depth · network priority · AI attention      ALLOWED
consequence → committed truth                                                       FORBIDDEN
```

Future importance decides where effort goes; it never decides what is true.

## Why it is general (not a game trick)

The same primitive applies wherever the cost of being wrong grows with the consequence of a transition:
**robotics** (verify motor actions by downstream state sensitivity, not motion size), **distributed
databases** (replication/quorum/audit depth by a write's dependency mass — *important things deserve stronger
evidence, not more truth*), **AI agents** (reasoning budget by action consequence), **scientific simulation**
(adaptive mesh / compute where approximation matters). The deterministic runtime allocates *certainty*
according to *future consequence* while preserving invariant state identity.

## Making it operationally native — the pipeline

`graph.py` answers *what matters next?* given declared magnitudes. The runtime layer makes the field native:
it diffs each committed transition and emits a hash-indexed token the scheduler consumes, all pure-observe.

```
POST STATE ──▶ extractor ──▶ propagation ──▶ fingerprint ──▶ cache ──▶ frontier(budget)
  (truth)      Δstate         downstream       Future-          token      where to spend
               (which          affected         Sensitivity      store      this frame
                nodes          region           Token
                changed?)
```

The **causal fingerprint** — a correction of the proposed formula (dev note / Ghost in the design). The spec
`C = dependency_mass × propagation_depth × branching_factor × uncertainty` **double-counts**: `dependency_mass`
already *is* the bounded BFS that integrates depth and branching. The information-bearing decomposition keeps
**dual arithmetic separation** (forward/structural ⟂ dual/epistemic, no collapse):

```
                    forward / structural            dual / epistemic
C(node, Δ)  =   Δ                       ×   dependency_mass(node)   ×   uncertainty(node)
                perturbation (extractor)    topology (depth×branch)     orthogonal unknown ∈[0,1]
```

`uncertainty` is the *only* new multiplicand carrying information `dependency_mass` does not already hold; it
weights attention, never truth, and is never derived from magnitude or position. The token is content-addressed
(`h = SHA256` over its tuple — a structural index, no semantics) and its `expires` is a *scheduling* horizon,
never a physical lifetime.

## Run it

```
PYTHONHASHSEED=0 python3 demo_consequence.py        # butterfly + one field, four consumers
PYTHONHASHSEED=0 python3 demo_butterfly.py          # the Butterfly Benchmark (consequence-wins-on-structure)
PYTHONHASHSEED=0 python3 demo_reconstruct.py        # native pipeline + the Causal Reconstruction Test
PYTHONHASHSEED=0 python3 tests/test_consequence.py  # 28 unit tests
```

## The Causal Reconstruction Test — can the runtime delete compute and keep the future? (`demo_reconstruct.py`)

Same integer cellular world simulated two ways: **FULL** (update every node) vs **CAUSAL** (each step
re-extract the causal frontier and update *only* it, freeze the rest). Metrics, both in [0,1]:
`compute_saved = 1 − Σ|frontier|/(N·|V|)` and `divergence_preserved = 1 − L1(causal,full)/L1(full,init)`.
Four worlds — including a deliberate adversary built to *fail*:

```
world      coupling                compute_saved   divergence_preserved
flat       dense, uniform          0.008           1.000   ← negative control: nothing to skip
chained    thin, declared          0.873           1.000   ← the win: delete 87% compute, lose nothing
trigger    dormant, DECLARED edge  0.929           1.000   ← per-step re-extraction catches the late cascade
hidden     dormant, UNDECLARED     0.978           0.414   ← THE BOUND: the frontier is blind to it
```

The `trigger`/`hidden` pair is the headline. A dormant node `D` ignites a large cascade only when an upstream
key crosses a threshold (small cause → large consequence). When the `key→D` coupling is a **declared** edge,
per-step re-extraction reaches `D` and reconstruction stays exact. When the identical coupling is **undeclared**
(lives in the dynamics but not the graph), the frontier never reaches `D`, it stays frozen, and reconstruction
collapses to 0.414. Verdict `reconstruction-valid-with-declared-bound`.

## Honest bound

A deterministic weighting field over a **declared** dependency graph. It decides where effort goes, never
what is true (`consequence ≠ truth`). The reconstruction is exact **iff the graph declares every real
coupling** — an undeclared coupling is invisible, exactly as the Butterfly Benchmark's bound predicts
(`integrity ≠ graph-truth`). The graph is a *modeling input*, not a fact of nature; consequence is computed
under it, never validated by it.

## The Butterfly Benchmark — when does consequence-aware scheduling matter? (`demo_butterfly.py`)

Two worlds identical in everything a conventional engine sees (node count, physics cost), differing ONLY in
consequence topology; three schedulers allocate an attention budget; the metric is **future-divergence
captured** (not FPS, not polygons). Measured (200 nodes, 10% budget):

```
world     distance   visibility   consequence
flat      0.100      0.100        0.100      ← nothing to find: all tie at the budget fraction (negative control)
chained   0.340      0.343        0.936      ← hidden dependency chain: consequence finds ~94% position misses
```

Verdict `consequence-wins-on-structure`: consequence-aware scheduling adds value **exactly when** a world has
dependency structure decorrelated from position — there, distance/visibility are *structurally blind* to the
hidden chain. On a flat world it ties the baselines (a fair negative control). It is not "always faster"; it
"sees future surface area that proximity cannot." Honest bound: this proves position-blindness, not that the
declared graph is true.

## Files

| File | Role |
|---|---|
| `graph.py` | `Graph`, `dependency_mass`, `consequence`, `field`, `taint` — the deterministic-integer taint map |
| `extractor.py` | pure Δstate observer: `extract(pre,post) → changed-set + magnitudes` (no mutate handle) |
| `propagation.py` | `reached` / `frontier` / `region_size` — downstream affected region of a change |
| `fingerprint.py` | `FutureSensitivityToken` — dual-separated `C = Δ·mass·uncertainty`, hash-indexed, expiring |
| `cache.py` | `ConsequenceCache` — bounded deterministic token store, `frontier(budget)` = where to spend |
| `reconstruct.py` | the **Causal Reconstruction Test** — full vs causal-frontier sim; flat/chained/trigger/hidden |
| `demo_consequence.py` | the butterfly + one field, many consumers |
| `butterfly.py` / `demo_butterfly.py` | the **Butterfly Benchmark** — consequence-wins-on-structure |
| `demo_reconstruct.py` | native pipeline walkthrough + the reconstruction verdict |
| `tests/test_consequence.py` | 28 unit tests |
