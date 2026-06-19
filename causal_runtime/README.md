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

## The epistemic axis and the ghost — `A = C × P × U + G⁺` (`novelty.py`)

The third axis (`U`, uncertainty) is fed by a **producer-agnostic** seam: `novelty.py` ingests `{node:
novelty_score}` and `NoveltySignal(source_id, node, novelty_q16, confidence, timestamp)` records, aggregating
across any number of producers (confidence-weighted). **dini** (a hyperbolic novelty compass) is one producer;
model disagreement, prediction error, sensor surprise, and simulation residuals are others — all feed the same
slot. `novelty.py` never imports a producer. Producer floats (e.g. `dini_distance`) cross into the integer
field through a deterministic Q16 **canon boundary**; the float never enters a hash.

The **ghost** closes the loop the hidden-coupling bound opened:

```
G  = observed_divergence − predicted_consequence          (per node)
G⁺ = max(0, G)                                            (rectified: surprise raises attention, never lowers it)
```

An *undeclared* coupling makes a node change with `predicted = 0`, so `G⁺ = full observed` — a pure attention
spike with **no structural cause**: *"something matters here; I don't yet know what."* The final field is the
structural surface plus rectified surprise, `A = C × P × U + G⁺`, under the unchanged law (`A → attention`,
never `A → mutation`). The rectification is the honest asymmetry: the model may not talk itself out of looking.

## The Blind Discovery Benchmark — finding what nothing declared (`discovery.py`)

A hidden node `H`: **consequence 0** (no declared dependency), **low visibility**, but an unusual transition at
`t_anom`. Three policies inspect a budget each frame; measure time-to-discovery:

```
world      distance   consequence   consequence+ghost
hidden     miss       miss          t+0     ← only the ghost (observed−predicted) catches the undeclared anomaly
declared   t+0        t+0           t+0     ← negative control: H is declared/visible, surprise buys nothing
```

Verdict `ghost-discovers-the-undeclared-anomaly`: distance is blind to low visibility, consequence is blind to
the undeclared coupling, and the ghost catches it because the world moved a node the model rated zero. This is
the layer that lets the runtime *allocate computation toward things it does not yet understand* — without ever
touching truth.

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
PYTHONHASHSEED=0 python3 demo_dini_novelty.py        # dini as a novelty producer + ghost, invariant re-proven
PYTHONHASHSEED=0 python3 discovery.py                # the Blind Discovery Benchmark
PYTHONHASHSEED=0 python3 freshness.py                # the Causal Freshness Benchmark
PYTHONHASHSEED=0 python3 tests/test_causal_runtime.py  # 26 unit tests
```

## Honest bound

It allocates **certainty / compute**, never truth. Its consequence input is computed over a *declared*
dependency graph, so it inherits that graph's bound exactly (an undeclared coupling is invisible — see
`consequence/reconstruct.py`). The benchmark is a *measurement of scheduling quality under a model*, not a
claim about physical nature or a shipping 240fps engine. `integrity ≠ truth`; here: `attention ≠ authority`.

## Files

| File | Role |
|---|---|
| `field.py` | `AttentionToken`, `future_surface` (dual-separated composite), `causal_pressure`, Hamilton budget, optional ghost |
| `runtime.py` | `AttentionField` — pure observe → per-channel allocation; no mutation surface; the law |
| `novelty.py` | the **epistemic seam** — producer-agnostic `NoveltySignal` aggregation, `ghost_field`, final `A = C×P×U + G⁺` |
| `freshness.py` | the **Causal Freshness Benchmark** — consequence×uncertainty vs distance/visibility |
| `discovery.py` | the **Blind Discovery Benchmark** — ghost finds the undeclared, low-visibility anomaly |
| `demo_causal_runtime.py` | allocation field + freshness verdict |
| `demo_aether_attention.py` | wires the field onto **AetherPulse** + proves the committed-hash invariant |
| `demo_dini_novelty.py` | **dini** as a novelty producer (Q16 canon boundary) + ghost; invariant re-proven |
| `_wb.py` | path shim so demos/tests wire real sources (AetherPulse, consequence, dini) without the core importing across siblings |
| `tests/test_causal_runtime.py` | 26 unit tests (incl. the cardinal invariant under dini, ghost rectification, blind discovery) |
