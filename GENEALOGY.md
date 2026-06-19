# GENEALOGY — a maintained epistemic ledger

> Engineering history *and* semantic contract. This file does two jobs and keeps them separate: it records
> **what happened** (the history) and it states **what is actually claimed** (laws vs findings, survivors vs
> dead branches). The most valuable artifact here may not be any module — it is the record of *what assumption
> broke, what constraint that forced, and which implementation currently discharges it* (implementations are
> replaceable; the constraints and the dead branches are not).

## The method that generated everything

The architecture did not grow by asking "what feature next?" It grew by asking, repeatedly:

> **"What assumption just broke, and how do I make that breakage observable?"**

Every layer is one turn of the same loop — and the loop forces a *constraint*, not a specific solution:

```
Observation → Abstraction → Benchmark → FAILURE → CONSTRAINT → Implementation → (Observation…)
```

The benchmark is load-bearing: an abstraction is only kept after a falsification attempt is built *for it* and
it survives. Several did not survive unchanged (see **Failed or Frozen Paths**). The signal of the project is
therefore not the accumulation of mechanisms but the **accumulation of explicit constraints and dead branches.**

## The chain — failure → constraint → implementation

Each layer is recorded as three separable things. The **constraint** is the durable lesson; the
**implementation** is replaceable without violating it. (A future contributor may swap the held-out gate for a
better falsifier — but may not reintroduce evidence that can only increase.)

```
Trace → Salience → Possibility → Consequence → Ghost → Coupling-discovery → Intervention → Falsification → LOD
```

| Layer | Failure observed | Constraint it forces (durable) | Implementation (replaceable) |
|---|---|---|---|
| **salience** | uniform / distance-based compute misses the doorway over the quiet valley | spend effort where the future can branch, not by proximity | possibility density, cached as a Possibility Atlas |
| **possibility** | the realized trajectory hides the lawful-but-unchosen set that shaped it | the unrealized must be *measurable*, not discarded | admissible-set geometry; proposal pressure `R_p` |
| **consequence** | magnitude and importance diverge (~37× hub vs leaf) | weight by structural future-dependence, not size | `Δ · dependency_mass` (the State-Graph Taint Map) |
| **ghost** | a declared graph can be incomplete; consequence goes blind to undeclared couplings | model error must *surface as an observable*, not hide | `G⁺ = max(0, observed − predicted)` |
| **coupling_discovery** | a self-modifying learner drifts toward reducing its own surprise | structure change must be *proposed*, never self-committed | `CouplingRegistry` behind four locks |
| **intervention** | correlation that survives observation can still be confounded | a causal claim needs a controlled test that *never touches reality* | airlock-authorized `do()` on a shadow world |
| **falsification** | evidence that can only increase builds self-sealing models | evidence must be falsifiable and *able to decay* | held-out corroboration track record |
| **lod** | **future consequence *alone* does not determine render priority**, and a future-aware renderer could leak hidden information | render priority must combine future relevance *with legally-visible perceptibility*, and may never reveal the unseen | `render_priority = future_surface × perceptual_sensitivity`; occlusion-gated; `fairness_invariant` |

## Architectural Laws (design constraints — never weakened by new data)

These are *chosen* directional constraints. New data does not get to relax them; if a measurement seems to
require relaxing one, the design is wrong, not the law. They are enforced structurally (in types and gates),
not by discipline.

```
integrity            → truth                 FORBIDDEN     (the root: a hash certifies form, never correctness)
telemetry            → control               FORBIDDEN
intent               → authority             FORBIDDEN
possibility          → physics               FORBIDDEN     (possibility → allocation ALLOWED)
consequence          → committed truth       FORBIDDEN     (consequence → allocation/validation ALLOWED)
causal_information   → reality_mutation      FORBIDDEN     (→ attention ALLOWED)
ghost / proposal     → actual graph edge     FORBIDDEN     (→ proposed edge ALLOWED, external review only)
prediction           → truth                 FORBIDDEN
falsification        → committed reality      FORBIDDEN     (→ proposal status ALLOWED)
causal_information   → experiment            ALLOWED *only* shadow-only, airlock-authorized
future_surface       → fidelity allocation   ALLOWED       (smoother animation, sharper shading, more triangles)
future_surface       → hidden information     FORBIDDEN     (the renderer must never become a gameplay oracle)
```

Restated as the project's standing inequalities, these are the ones that are **laws**: `proposal ≠ authority`,
`model improvement ≠ world modification`, `telemetry ≠ control`, `intent ≠ authority`, and — for the renderer —
`future relevance ≠ hidden information` (fidelity may rise; what a player can *see or know* may not).

## Empirical Findings (results — always challengeable by new data)

These *arose from benchmarks* and could be overturned by a better one. They must never be promoted to laws;
mixing the two makes the epistemology fuzzy. Each names the benchmark that produced it.

```
consequence ≠ magnitude            — the same delta is ~37× more consequential at a hub than a leaf   (Butterfly)
distance/visibility are structurally blind to hidden dependency chains                                 (Blind Discovery)
an undeclared coupling collapses reconstruction (0.94 → 0.41 future-divergence preserved)              (Causal Reconstruction)
evidence that only increases is self-sealing; a confounder & a regime-fluke pass the naive test        (Self-Confirmation)
observation alone cannot separate a true edge from a confounder; intervention can                       (Causal Intervention)
consequence ≠ visibility; future consequence ALONE is insufficient for render priority                  (LOD Falsification)
possibility-aware attention MATCHES hand-authored importance (automatically, at scale) — it does NOT beat it  (CCR)
```

The last one is a deliberate **non-superiority** finding kept on the record: the value of possibility-attention
is automation + determinism + self-update, not that it outperforms a hand-tuned heuristic.

## Three things that must not be conflated

The architecture's strength is in exactly one of these, and the claims are only honest if the three stay
separate:

```
1. Simulation truth          — what actually happened (the committed hash trajectory; singular, deterministic)
2. Computation allocation    — where the engine spends finite effort (THIS is where the explicit bounds work)
3. Player-visible rasterization — what is drawn, at what fidelity, from information already legally available
```

A competitive player does not benefit because the engine "knows causality." They benefit if the engine spends
its finite budget — compute, network, validation, AI, *and* triangles — on the state likely to affect the next
few seconds of play. The rasterization claim is therefore **not** "render causality"; it is "spend rendering
budget according to expected future gameplay relevance" — and only on information the player may already see.
A tiny objective door can be strategically dominant; a distant sniper can be about to become the most important
object in your future; a thousand-pixel waterfall can have zero gameplay consequence. Future-surface allocation
re-weights fidelity toward the first two — but it may never reveal the third claim's forbidden case (an enemy
through a wall). That is the fairness law, and `causal_runtime/lod.py`'s `fairness_invariant` tests it: an
occluded enemy with the *largest* future_surface in the scene receives exactly **zero** render budget under
every policy, because the field multiplies by legal visibility.

## The one idea the chain converges on

Every layer is the same move applied to a new consumer:

> **Allocate resources according to future branching, rather than present magnitude.**

Applied to **compute** (salience), **validation depth** (consequence/airlock), **network priority**, **AI
attention** (causal_runtime), and — as a *hypothesis under test* — **rasterization** (`causal_runtime/lod.py`).
The renderer is simply the last major consumer of the same `future_surface` field.

## Failed or Frozen Paths (history of *survived* ideas, not *successful* ones)

The credibility of a falsification-first project comes from recording the branches that died, tied a baseline,
or were refused. Each entry: hypothesis → benchmark → result → lesson retained.

**Spectral predictive gate — `aether/predictive.py` — STATUS: FROZEN.**
*Hypothesis:* spectral-coherence pressure over the SPD manifold predicts integration error and could drive
adaptive cadence. *Benchmark:* a held-out incremental-value gate (does it add out-of-sample predictive value
beyond the existing signal?). *Result:* **negative** — ΔR² ≈ 0; the pressure is *descriptive*, not predictive of
error. *Lesson retained:* an in-sample correlation is not kept unless it adds *held-out* value. The layer was
frozen as a monitor, not extended. **This is where the held-out-gate philosophy was first earned** — it later
became `falsification.py`.

**Magnus-2 integrator — `aether/field.py` — STATUS: OPTION, NOT DEFAULT.**
*Hypothesis:* a Magnus-2 step beats Euler on the generator field. *Benchmark:* accuracy payoff vs Euler under
the ghost channel. *Result:* **inconclusive** with the additive `(I + Ω)` form — no clear win. *Lesson
retained:* complexity is not promoted to the default path without a measured payoff; kept as an option.

**Possibility-attention superiority — `salience/ccr.py` — STATUS: CLAIM DOWNGRADED.**
*Hypothesis:* possibility-aware attention *beats* hand-authored importance. *Benchmark:* Consequence Capture
Ratio vs a hand-authored baseline. *Result:* it **matches** (automatically, deterministically, at scale) but
does **not** beat it. *Lesson retained:* the README claim was downgraded from "beats" to "matches at scale,
self-updating"; the win is automation, not superiority.

**Fabricated pre-written results — legacy era — STATUS: REJECTED, CORRECTED IN LEDGER.**
Several speculative experiments arrived with results already written. Running them disproved the numbers (a
claimed 30.92% compression gain measured to ~5%, sometimes *negative*; a "Klein bottle" boundary had a real
topological bug). *Lesson retained:* a proposed number is run before it is believed, and the ledger records the
*measured* value.

**"v2 kernel" rewrite — legacy era — STATUS: REFUSED AS PREMATURE.**
*Hypothesis:* a kernel rewrite is the optimization. *Benchmark:* a frame-time profiler, built *first* — it
showed ~7× headroom, and the real cost was redundant hashing (~75% of a tick), not the eigensolver everyone
assumed. *Lesson retained:* measure before optimizing; refuse the rewrite the profile does not justify.

**Overscoped claims — ongoing — STATUS: RE-SCOPED OR RECORDED AS NON-CLAIMS.**
"post-trust," "solves the Halting Problem," "diamond-hard," "100% certainty," a Collatz-indexed derivative —
each was re-scoped to what the code proves or recorded as a non-claim. *Lesson retained:* every component states
its honest bound; a marketing-shaped claim is a non-claim.

## Proven vs Hypothesis (current ledger)

- **Proven (runnable benchmarks, each with a negative control):** the field improves *compute / validation /
  network / AI* allocation (Butterfly, Causal Freshness, Blind Discovery, Self-Confirmation, Causal
  Intervention). The committed hash trajectory is byte-identical with every observation layer attached (the
  cardinal invariant).
- **Hypothesis under test (the deeper one):** the renderer is *not the destination* of the field — it is merely
  another consumer. The real hypothesis is that a **single future-surface field can coordinate simulation,
  networking, validation, AI attention, and rasterization** so that limited resources are spent on
  future-relevant state rather than present magnitude — and for a competitive shooter the larger win may be
  in **network bandwidth / rollback history / tick precision / validation depth** (where the chain has
  repeatedly found the real bottleneck) *before* it ever reaches triangles. If it proves out, the benefit is
  not that players see more pixels; it is that **at the same hardware budget the engine preserves more of the
  information that determines what happens next.** The narrow, testable instance is that a *renderer* driven by
  `future_surface × perceptual_sensitivity`
  preserves more future-relevant visual fidelity per triangle than distance- or screen-space-driven LOD. The
  **LOD Falsification Bench** (`causal_runtime/lod.py`) is the first evidence — at equal triangle budget on a
  hidden-importance world, future-surface LOD drives future-relevant visual error to ~0 where distance/screen
  starve the far future-critical object, and spends nothing extra on a high-future, ~0-coverage switch. But it
  is a *policy* bench, **not a renderer**: it allocates a triangle budget and measures error; it does not draw
  pixels. Until a real renderer consuming the field passes the same test, the rasterization benefit is a
  hypothesis. When it passes, that is the moment the trace reaches the image.
