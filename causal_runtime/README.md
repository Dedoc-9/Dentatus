# causal_runtime — causal allocation of computation (the AttentionField)

A deterministic **observation-domain** substrate. It reads three orthogonal fields about a world a kernel
already committed, and recommends **where computation should be spent** — streaming residency, AI tick rate,
animation fidelity, network replication, validation depth. It is structurally incapable of touching state.

> **What it is, precisely.** Not a *causal discoverer* — a **falsifiable structure-maintenance system**. A dependency graph is predictive at best; this layer keeps a continuously *falsifiable* model of where its own abstractions fail, and spends compute accordingly.

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

## Coupling discovery — a persistent ghost becomes a *proposed* edge (`coupling_discovery.py`)

The runtime now has the missing asymmetry: `declared structure → consequence → attention` and `unknown
structure → ghost → attention`. The remaining question — *when does a repeated ghost mean the declared graph is
incomplete?* — is the **persistence layer**, and it is the place a self-modifying system usually falls into the
**epistemic trap**: a learning loop that edits its own model drifts toward whatever reduces its surprise,
inventing structure or suppressing inconvenient observations until the discovery mechanism corrupts the model
it was meant to improve. Four structural locks close it:

```
ghost → PROPOSED coupling   ALLOWED        ghost → ACTUAL coupling   FORBIDDEN
```

1. **Propose, never commit** — `CouplingRegistry` holds *no handle to any graph*; no method can write an edge.
2. **Evidence, not authority** — a `CouplingCandidate` accumulates *integer* `frequency` + `ghost_total` across
   *distinct contexts*; never a `confidence += ghost` float that silently becomes a control path.
3. **External review gate** — promotion to a real edge is the airlock pattern (`intent ≠ authority`); this
   module emits the review queue, not the verdict.
4. **Reality untouched** — even an *accepted* proposal updates a *model*; `demo_coupling_discovery.py` proves
   the committed AetherPulse world hash is byte-identical before and after the model learns the edge
   (`graph improvement ≠ world modification`). A ghost is evidence of model failure, not a new fact.

## Falsifiable structure maintenance — the held-out gate, decay, and two tiers (`falsification.py`, `tiers.py`)

`coupling_discovery` had a self-sealing asymmetry: a persistent ghost only ever *raised* a candidate's
frequency, so it became monotonically harder to dislodge. The repair changes the epistemic physics — a
`StructureProposal` keeps a **track record**, not a confidence:

```
StructureProposal: source target  train_hits train_misses  heldout_hits heldout_misses  last_test_epoch status
```

A proposal is tested on a **held-out** window of committed history it was *not* derived from. A held-out
**miss** lowers its standing — `heldout_misses` can grow, so **evidence can go down**. Status is Popperian
(*survived attempts to fail it*, not *fit the data that generated it*): `PROPOSED` (untested, or the held-out
window offered no discriminating opportunity — "no falsification attempt available" is **not** "survived"),
`CORROBORATED` (held-out hits, zero held-out misses), `DECAYING` (a held-out miss appeared), `REJECTED`
(miss-rate crossed the floor).

**The Self-Confirmation Benchmark (`self_confirmation.py`)** is the brutal test — three worlds whose *training*
evidence is identical (A and C correlate, a proposal forms) but whose held-out behaviour is not:

```
world        structure                       held-out            naive     held-out gate
true         A → C                            C follows A         promote   CORROBORATED
confounder   A ← X → C                        A alone, C flat     promote   REJECTED   (the case the old model fails)
regime       A → C only when temp>thr         new regime, C flat  promote   REJECTED   (local regularity, not structure)
```

Verdict `held-out-gate-breaks-self-confirmation`: the naive frequency-only model promotes **all three**; the
gate corroborates **only** the true edge.

**Two tiers (`tiers.py`).** The graph does two jobs with two proof burdens. The **predictive** tier (correlation
/ dependency / association) is *enough* for allocation — salience, validation depth, streaming, attention — and
makes **no causal claim**. The **corroborated** tier is the strict subset of edges that survived the held-out
gate, and **only it may wear structural vocabulary**. Allocation never waits on falsification; the strong claim
is always earned. `vocabulary_for(edge)` enforces the wording so prose cannot overclaim.

### The Ghost Persistence Benchmark (`ghost_persistence.py`)

A hidden coupling `A → C` (A drives C; the declared graph does not say so) plus uncorrelated noise:

```
scenario     ghost on C   proposes A→C
single       fires once   no    ← one-off / noise is not promoted (negative control)
repeatable   fires 20×    YES   ← the reproducing coupling rises above frequency × distinct-context threshold
declared     never        no    ← consequence already predicts C; nothing re-proposed (negative control)
```

Verdict `persistence-proposes-reproducing-coupling-rejects-noise`. The two negative controls are what stop the
system from *learning noise* or re-proposing the known. The benchmark also encodes a real distinction — an
*exogenous root* changing (an input) is not model failure, so its ghost is suppressed. **Honest bound:**
persistence rejects one-off noise but cannot, by observation alone, separate two *consistently* co-occurring
sources — that requires intervention (itself a transition through the airlock). The system becomes causally
aware *about its own ignorance* without the discovery mechanism being able to rewrite either reality or the
model.

## The LOD Falsification Bench — does the field reach the image? (`lod.py`)

Everything above allocates compute, validation, network, AI. Rasterization is the last consumer, and it asks a
*different* question — **which pixels can safely receive less effort?** — so consequence alone cannot drive it:
a mountain is all pixels and no future; a quest switch is all future and 3 pixels. The new bound is
**`consequence ≠ visibility`**, and the render quantity is a product, not a field already built:

```
render_priority(node) = future_surface(node) × perceptual_sensitivity(node)     (≈ screen_coverage)
```

This is a **falsification bench, not a renderer** — it allocates a fixed *triangle budget* across objects by
three policies and measures **future-relevant visual error** at equal budget:

```
world    budget   future-relevant visual error:  distance   screen   future-surface
flat     282      211099     216798     214167     ← negative control: importance ∝ distance ⇒ all tie
hidden   304      420000     380000     0          ← a far, visible, future-critical bridge in near no-future clutter
```

Verdict `future-surface-LOD-preserves-future-relevant-fidelity`. On the hidden-importance world the
future-surface policy funds the far **bridge** (40/40 triangles) that distance- and screen-space LOD both
starve — and spends *nothing extra* on the high-future, 2-pixel **switch** (covered to its trivial 2/2, no more),
because `consequence ≠ visibility`: its detail wouldn't be seen. Honest scope: a *policy* bench that allocates a
triangle budget and measures error; it does **not** draw pixels. Until a real renderer consuming the field
passes the same test, the rasterization benefit is a hypothesis (see [`GENEALOGY.md`](../GENEALOGY.md)).

**Fairness — the renderer must never become a gameplay oracle.** A future-aware allocator could, naively, leak
hidden information ("render the enemy through the wall because they're important"). The product structure
forbids it: `perceptual_sensitivity` is gated by *legal visibility*, so an occluded object scores `future_surface
× 0 = 0`. `fairness_invariant` proves it — in the occlusion world an **occluded sniper with the largest
future_surface in the scene receives zero render budget under every policy**, while the visible bridge is funded.
The law: `future_surface → fidelity` ALLOWED (smoother animation, sharper shading, more triangles); `future_surface
→ hidden information` FORBIDDEN — i.e. `future relevance ≠ hidden information`. The renderer is just *another
consumer* of the field; the deeper hypothesis is that one future-surface field coordinates compute, network,
validation, AI, and rasterization so a fixed hardware budget preserves more of the state that decides what
happens next (see [`GENEALOGY.md`](../GENEALOGY.md)).

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
PYTHONHASHSEED=0 python3 ghost_persistence.py        # the Ghost Persistence Benchmark
PYTHONHASHSEED=0 python3 demo_coupling_discovery.py  # epistemic trap closed (world hash invariant)
PYTHONHASHSEED=0 python3 freshness.py                # the Causal Freshness Benchmark
PYTHONHASHSEED=0 python3 demo_falsification.py       # held-out gate + Self-Confirmation Benchmark + tiers
PYTHONHASHSEED=0 python3 self_confirmation.py        # the Self-Confirmation Benchmark alone
PYTHONHASHSEED=0 python3 lod.py                      # the LOD Falsification Bench (consequence != visibility)
PYTHONHASHSEED=0 python3 allocation.py               # the FORMAL allocation+predictive test (M-parameterized, falsifiable)
PYTHONHASHSEED=0 python3 fallback.py                 # graceful degradation: distance floor at unrecoverable field failure
PYTHONHASHSEED=0 python3 tests/test_causal_runtime.py  # 62 unit tests
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
| `falsification.py` | **the held-out falsification gate** — `StructureProposal` track record; evidence that can DECAY; PROPOSED/CORROBORATED/DECAYING/REJECTED |
| `self_confirmation.py` | the **Self-Confirmation Benchmark** — true / confounder / regime-trap; naive promotes all, the gate does not |
| `tiers.py` | **predictive vs corroborated** split — correlation feeds allocation; only survived edges may claim structure |
| `demo_falsification.py` | the falsifiable-structure layer end to end |
| `coupling_discovery.py` | **persistent ghost → proposed edge** — `CouplingRegistry` (propose-never-commit; no graph handle); the four locks against the epistemic trap |
| `ghost_persistence.py` | the **Ghost Persistence Benchmark** — single (reject) / repeatable (propose A→C) / declared (no re-propose) |
| `demo_coupling_discovery.py` | closes the trap on AetherPulse: an accepted proposal leaves the committed world hash unchanged |
| `demo_causal_runtime.py` | allocation field + freshness verdict |
| `demo_aether_attention.py` | wires the field onto **AetherPulse** + proves the committed-hash invariant |
| `demo_dini_novelty.py` | **dini** as a novelty producer (Q16 canon boundary) + ghost; invariant re-proven |
| `_wb.py` | path shim so demos/tests wire real sources (AetherPulse, consequence, dini) without the core importing across siblings |
| `lod.py` | the **LOD Falsification Bench** — render_priority = future_surface × perceptual_sensitivity; `consequence ≠ visibility` |
| `allocation.py` | the **formal allocation + predictive test** — max Σaᵢ·Mᵢ s.t. Σaᵢ·cᵢ≤B against an *independent* M; falsifiable (a bad-estimate world makes future_surface LOSE); M is a parameter (ontology not decidable) |
| `fallback.py` | **graceful degradation** — ghost-triggered hysteresis latch → **distance floor** at unrecoverable field failure; beats both fixed policies across a regime shift, never degrades a stable world |
| `tests/test_causal_runtime.py` | 62 unit tests (incl. the cardinal invariant under dini, ghost rectification, blind discovery, the epistemic-trap locks) |
