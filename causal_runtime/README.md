# causal_runtime — causal allocation of computation (the AttentionField)

A deterministic **observation-domain** substrate. It reads three orthogonal fields about a world a kernel
already committed, and recommends **where computation should be spent** — streaming residency, AI tick rate,
animation fidelity, network replication, validation depth. It is structurally incapable of touching state.

```
                 REALITY DOMAIN
        deterministic transition kernel ──▶ immutable history
                          │ (committed state is read-only to everything below)
                          ▼
                 OBSERVATION DOMAIN
        ┌───────────────┬───────────────┐
        ▼               ▼               ▼
   consequence      uncertainty     possibility
   (dependency      (epistemic)     (admissible
    topology)                        freedom)
        └───────────────┼───────────────┘
                        ▼
                 future-surface field
                        ▼
              computation policy (AttentionTokens)
        streaming · AI · fidelity · network · validation
```

## The law it introduces

```
causal_information → computational_attention      ALLOWED
causal_information → reality_mutation             FORBIDDEN
```

Modern engines approximate `importance ≈ distance × visibility × heuristics`. This substrate changes the
primitive to `importance ≈ future dependency surface`: not *how big / how close / how many polygons* but *how
many future states depend on this, how uncertain is it, how expensive is being wrong*. The field is the
**operational** form of the Butterfly Benchmark — a bullet matters not for its energy but for its reachable
futures.

## The composite — dual arithmetic separation (no collapse)

```
                       topology              epistemic            admissible
future_surface(node) = consequence(node)  ×  uncertainty(node)  ×  possibility(node)
```

Three orthogonal axes; the product is stored **with** its components so each stays auditable. `consequence` is
a raw score (e.g. a `consequence.fingerprint` value); `uncertainty`, `possibility ∈ [0,1]` (Q16). This is
`possibility_pressure` (what *could* happen) crossed with `causal_pressure` (what future branches *depend* on
this happening) — a field over **attention**, never a field over physics.

The `AttentionToken` carries the recommendation only: `target, consequence_score, uncertainty_score,
possibility_score, surface, recommended_budget` (Hamilton largest-remainder, integer-exact), `validation_depth`
(batch-relative bucket), `freshness` (recommended refresh interval — high surface ⇒ keep warm), `expires`
(a *scheduling* horizon), `h` (a SHA-256 structural index, no semantics).

## The cardinal invariant — proven against a real Aether application

`demo_aether_attention.py` runs **AetherPulse** twice: plain `kernel.run`, and the identical kernel loop with
the `AttentionField` observing every tick (consequence from body proximity, uncertainty from |Δvel|). Measured:

```
committed hash trajectory identical with/without observer : True
attention non-trivial: varies across bodies = True   over time = True
final validation-depth allocation by body: {1:2, 2:2, 3:2, 4:0, 5:2}   ← cluster gets depth, far loner (4) gets 0
```

The observer never writes back; the world handed to the next `step` is byte-for-byte the kernel's own output.
So causal awareness changed **what we compute about**, not **what happened** — *the outcome hash cannot know the
difference.* (`telemetry ≠ control`, made a hash equality.)

## The Causal Freshness Benchmark — causal cache invalidation (`freshness.py`)

The novel claim is using **future consequence to decide what must stay fresh**. N cache entries, each with a
true importance (future dependency surface) and a visibility (distance heuristic); a fixed refresh budget keeps
some warm each frame; an important transition fires ∝ importance and is *missed* if its node was stale. Two
policies at **equal budget** (lower missed-rate is better):

```
world      missed[visibility]   missed[causal]
aligned    0.843                0.848    ← negative control: visibility≈importance, causal only TIES
hidden     0.855                0.443    ← low-visibility high-consequence switches: causal halves the misses
```

Verdict `causal-freshness-wins-on-hidden-importance`: the gain is real **exactly when** importance is
decorrelated from visibility — the hidden switch that controls door → economy → faction war. uncertainty is
held uniform so the result isolates the consequence-vs-visibility axis (it would only sharpen the win).

## Run it

```
PYTHONHASHSEED=0 python3 demo_causal_runtime.py      # allocation field + freshness benchmark
PYTHONHASHSEED=0 python3 demo_aether_attention.py    # AetherPulse + the cardinal hash-invariant
PYTHONHASHSEED=0 python3 freshness.py                # the benchmark alone
PYTHONHASHSEED=0 python3 tests/test_causal_runtime.py  # 15 unit tests
```

## Honest bound

It allocates **certainty / compute**, never truth. Its consequence input is computed over a *declared*
dependency graph, so it inherits that graph's bound exactly (an undeclared coupling is invisible — see
`consequence/reconstruct.py`). The benchmark is a *measurement of scheduling quality under a model*, not a
claim about physical nature or a shipping 240fps engine. `integrity ≠ truth`; here: `attention ≠ authority`.

## Files

| File | Role |
|---|---|
| `field.py` | `AttentionToken`, `future_surface` (dual-separated composite), `causal_pressure`, Hamilton budget |
| `runtime.py` | `AttentionField` — pure observe → per-channel allocation; no mutation surface; the law |
| `freshness.py` | the **Causal Freshness Benchmark** — consequence×uncertainty vs distance/visibility |
| `demo_causal_runtime.py` | allocation field + freshness verdict |
| `demo_aether_attention.py` | wires the field onto **AetherPulse** + proves the committed-hash invariant |
| `_wb.py` | path shim so demos/tests wire real sources without the core importing across siblings |
| `tests/test_causal_runtime.py` | 15 unit tests (incl. the cardinal invariant) |
