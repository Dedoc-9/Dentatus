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

## Run it

```
PYTHONHASHSEED=0 python3 demo_consequence.py        # butterfly + one field, four consumers
PYTHONHASHSEED=0 python3 tests/test_consequence.py  # 8 unit tests
```

## Honest bound

A deterministic weighting field over a **declared** dependency graph. It decides where effort goes, never
what is true (`consequence ≠ truth`). The graph is a *modeling input*, not a fact of nature; consequence is
computed under it, never validated by it. `integrity ≠ truth`.

## Files

| File | Role |
|---|---|
| `graph.py` | `Graph`, `dependency_mass`, `consequence`, `field`, `taint` — the deterministic-integer taint map |
| `demo_consequence.py` | the butterfly + one field, many consumers |
| `tests/test_consequence.py` | 8 unit tests |
