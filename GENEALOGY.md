# GENEALOGY — a maintained epistemic ledger

> Engineering history *and* semantic contract. This file does two jobs and keeps them separate: it records
> **what happened** (the history) and it states **what is actually claimed** (laws vs findings, survivors vs
> dead branches). The most valuable artifact here may not be any module — it is the record of *what assumption
> broke, what constraint that forced, and which implementation currently discharges it* (implementations are
> replaceable; the constraints and the dead branches are not).
>
> **The root principle (below):** *the field allocates attention; it does not allocate truth.* Nearly every
> law, finding, and bound here is a consequence of that one distinction.

## ROOT PRINCIPLE

> **The field allocates attention. The field does not allocate truth.**

This is the parent of every law, finding, and bound in this document — including `integrity ≠ truth`, which is
merely its special case for the audit core. A mechanism in this architecture may decide *where to look, what to
test, what to cache, what to validate, what to render, or what to investigate next.* **It may not decide what is
true.** Every paired statement the project has accumulated is that one distinction wearing a different hat:

```
possibility    → attention            ALLOWED        possibility    ≠ truth
consequence    → attention            ALLOWED        consequence    ≠ truth
prediction     → attention            ALLOWED        prediction     ≠ truth
ghost          → attention            ALLOWED        ghost          ≠ truth
proposal       → attention            ALLOWED        proposal       ≠ authority
corroboration  → attention            ALLOWED        corroboration  ≠ truth
future_surface → rendering attention  ALLOWED        future_surface ≠ visibility (hidden information)
```

So each observational layer is, precisely, an **attention engine** for *one kind of uncertainty* — never a
truth engine for it:

| Layer | Is NOT | IS |
|---|---|---|
| `consequence` | a causality engine | an attention engine for **future sensitivity** |
| `ghost` | a discovery engine | an attention engine for **ignorance** |
| `falsification` | a truth engine | an attention engine for **doubt** |
| `intervention` | a causal oracle | an attention engine for **confounding** |
| `salience` / `possibility` | a physics engine | an attention engine for **the unrealized** |
| renderer *(hypothesis)* | a gameplay oracle | an attention engine for **finite triangles** |

The phrase is foundational because it does not describe one sibling — it describes the role *every* observational
layer is permitted to play relative to reality. **The committed hash trajectory is the only thing allowed to be
"true"; everything downstream is allowed only to decide where attention goes.** The renderer is the clean test:
it may spend more budget on an *already-visible* object because it is predicted to matter; it may not reveal a
*hidden* object because it is predicted to matter. The difference between those two is the difference between
attention and truth.

## How success is judged — the burden of proof a ranking system carries

The root principle changes the *evaluation criteria*, and this is the part most likely to be misread. A truth
system is judged by **correspondence** — *is it correct? accurate? did it find what was objectively important?*
An attention system cannot be judged that way and must never be asked to be. It is judged by **comparative
utility under a fixed budget**:

```
a TRUTH     claim requires   correspondence with reality        (often impossible to establish)
an ATTENTION claim requires   comparative utility vs a baseline  (a beatable, falsifiable target)
```

So the only legitimate benchmark question in this architecture is:

> **"Did this allocation policy preserve more future-relevant information than the alternative, under the same
> budget?"**

— never *"did this field correctly identify what was objectively important?"* (that is a truth claim in
disguise, and the system refuses it). A ghost can be entirely **wrong** about the cause of an anomaly and still
**succeed**, if it directed attention to the region where the model is actually failing. A consequence field
need not identify true causation; it need only **rank** future-sensitive state better than a competing
allocator. This is exactly why **every benchmark in this project is comparative and carries a negative control**
(distance vs future-surface, naive vs held-out gate, screen-space vs `render_priority`): the principle forbids
an absolute-correctness claim, so the evidence is always *relative-to-an-alternative*, never
*correspondence-to-reality*.

Two operational restatements, for an engineer reading the code rather than the philosophy:

```
Observational layers may PRIORITIZE.   They may not CERTIFY.
The system may RANK.                    The system may not DECLARE.
```

Seen this way, the architecture is **not a stack of prediction systems — it is a stack of increasingly
sophisticated ranking systems**, every one held to the same rule: *they may influence where finite resources go
next; they may not redefine what happened.* The only thing that certifies reality is the committed trajectory
itself.

## Formal testability — what the math can and cannot decide

The root principle has a precise mathematical reading, and it cleanly separates what is decidable from what is
not. The field is a **scoring function `F`**; three different claims hide inside "the field works", and they do
not share a burden of proof.

**1. The allocation claim — TESTABLE.** Given budget `B`, allocating by `F` captures more *true* importance `M`
than allocating by a baseline. It is a constrained optimization:

```
maximize   Σ aᵢ · Mᵢ            subject to   Σ aᵢ · cᵢ  ≤  B
```

Test: greedy-by-`F` vs greedy-by-baseline (distance, magnitude, screen, random), each *scored on M*. Runnable in
`causal_runtime/allocation.py`.

**2. The predictive claim — TESTABLE.** `F` ranks items by their true future importance:
`Spearman(Fₜ, Mₜ) > Spearman(baseline, Mₜ)` over the next `N` ticks. Ordinary predictive-model evaluation.

**3. The ontology claim — NOT mathematically decidable.** *"`F` captures what truly matters."* Undecidable,
because `M` is not a mathematical primitive — player score, win-probability, future entropy, economic value,
narrative weight, validation risk are all different choices of `M`, and different stakeholders choose different
ones. The math can show `F → M` predicts well; it can **never** show `M` is the correct notion of importance.
So in `allocation.py` **`M` is an explicit, independent parameter** (never the allocator's own score): every
verdict is *"better under this M"*, and swapping `M` can flip it (`test_ontology_verdict_is_relative_to_M`).

The rasterization hypothesis is the same shape — minimize future-weighted visual error at equal budget:

```
minimize   L = Σ Fᵢ · Eᵢ(Tᵢ)     subject to   Σ Tᵢ  ≤  B
```

If future-surface LOD consistently minimizes `L` at equal triangle budget vs distance/screen-space LOD, you have
proven **better resource allocation** — not that future-surface is truth, causality, or *all* importance, only
that it is a better allocator under the chosen objective.

**The non-negotiable: the test must be able to fail the field.** A benchmark that scores `F` on a metric defined
*using* `F` is circular and proves nothing. `allocation.py` is built to falsify: a `future_loses` world (where
`F` is a *bad* estimate of `M`) shows future-surface **losing to distance** — measured, not hidden. A test that
cannot fail the field is not a test. *(Honest note: the earlier `lod.py` bench weights its error by
`future_surface`, so it is a self-consistency check, not an independent-objective test; `allocation.py` is the
independent-`M`, falsifiable form.)*

The whole reduction, in one line: the field is a scoring function, and the only rigorous question is **"does
using it improve decisions under a fixed budget?"** — precise, measurable, falsifiable. Not "is it true?"

## Adversarial boundaries — where the field stops being valid (`adversary.py`)

The most valuable result is not "the field wins" but "here is the exact condition under which it stops being a
valid allocator." Every other benchmark tests future_surface when future-relevance is *already correctly
represented*; these attack that hidden assumption by making the field **late, wrong, or incomplete**. Each shows
the naive field LOSING and names the repair (a measured boundary, not a hidden one):

```
adversary    failure of the field                                   measured boundary / repair
LATE         a correct-but-OLD field allocates to yesterday's        stale field beats fresh distance only up to
             importances                                             staleness ≈ 3 ticks (coherence 12), then LOSES
                                                                     → repair: refresh within the coherence time
WRONG        RAW consequence overspends on high-consequence /        raw=66% vs distance=93% of oracle → RAW LOSES;
             LOW-probability branches ("renders impossible futures") expected value C×p = 100% → repair: × probability
                                                                     (possibility ≠ likelihood — the composite's
                                                                      possibility axis is not a branch probability)
GAMEABLE     an actor inflates its OWN consequence to attract budget raw=56% vs guarded=98% → RAW funds manipulators;
             (self-generated consequence)                            → repair: impact × INDEPENDENT_evidence
                                                                      (proposal ≠ authority, applied to allocation)
```

These connect the adversaries back to the bounds: the WRONG boundary is `possibility ≠ likelihood` (a future
being *lawful* is not a future being *probable* — expected value needs the probability, not just the admissible
set); the GAMEABLE boundary is `proposal ≠ authority` re-derived for allocation (a score an actor can generate
about itself is not evidence — it must be gated by *independent* corroboration, the same discipline as the
held-out gate). The LATE boundary is why `fallback.py`'s reliability signal exists.

**Open adversaries (not yet built — logged so they are not forgotten):** the *perception* gate (visible-tiny-
critical vs visible-huge-irrelevant — needs a saliency model and a real renderer); *(the cross-domain conservation
test is now BUILT — see its own section, Outcome C);* and the *unknown-unknown* test
(a hidden coupling → ghost fires → discovery proposes → attention rises → does allocation reach a thing the
model does not yet understand? — the one that would connect the whole genealogy end to end). The pattern holds:
the next high-value result is the next *boundary*, not the next win.

## Cross-domain conservation — the thesis test (`conservation.py`)

The deepest question the architecture could face: is there a **conserved advantage** from one shared field, or
are we just building good domain-specific heuristics? *Does one coordinating attention field outperform five
specialists at fixed total budget?* The benchmark is built to return **Outcome B/C** (the field losing or being
only a coordinator) honestly, not just Outcome A. The measured result is **Outcome C**:

```
(a) WITHIN-DOMAIN     field=97%  specialist=99% of oracle   →  NO within-domain magic. A specialist that
                                                                estimates its own objective wins in its own domain.
(b) CROSS-DOMAIN      uniform demand      equal=100% field=100%  →  tie (negative control)
    SPLIT             concentrated+good   equal= 35% field=100%  →  the field WINS the budget SPLIT
                      concentrated+DRIFT  equal= 35% field= 15%  →  a wrong estimate LOSES to the equal-split floor
```

So the conserved advantage is **not** per-domain allocation — it is **cross-domain coordination**: specialists
are blind to each other and cannot move the *total* budget to the domain where future-relevance concentrates
this tick; one shared field can. Equal-split is the cross-domain **safe floor** (the analogue of the distance
floor), and the win is **falsifiable** — a drifted/inverted cross-domain estimate loses to it. This fits the
root principle exactly: *the field decides **where** disagreement deserves resources; it does not decide **how**
each subsystem acts.* The field is a **coordination layer, not a universal allocator** — which is the strongest
*honest* version of the transfer hypothesis, and arguably more defensible than "it beats every specialist."

**The capstone triad** (the three tests that interrogate the thesis itself, not a single consumer):
1. **Cross-domain conservation** — *built* (`conservation.py`): Outcome C above.
2. **Semantic drift** — *partially built*: the `concentrated+DRIFT` case is a drift instance (correlations invert
   → the field's estimate is wrong → it loses to the floor). The deeper form — a *learned/cached* field that
   silently keeps using world-A correlations in world B — remains open; the discipline's answer is that the field
   must be **recomputed from current state**, not learned-and-frozen (`attention ≠ understanding`).
3. **Unknown-unknowns** — *partially built* (`consequence/discovery.py` Blind Discovery + `coupling_discovery`):
   the ghost redirects attention to an undeclared coupling; the end-to-end *renderer* version (ghost → discovery
   → attention → rasterization reaching a thing the model does not yet understand) remains open.

The pattern, restated one last time: the highest-value result was never "the field wins." It was finding, for
each layer, the **exact condition where its usefulness ends** — and `conservation.py` ends the central one:
the field's usefulness is *coordination across domains that share a latent future-relevance*; it ends at
orthogonal domains (specialists win) and at a drifted estimate (the floor wins).

## Failure mode — the distance floor (graceful degradation)

The formal test admits the field can *lose*: when `future_surface` becomes a bad estimate of the objective, plain
distance beats it. A runtime therefore needs an answer to *"what do I do when my own field has failed?"* — and
it must answer **without a truth oracle**, because it cannot compare its estimate to the objective `M` at runtime
(`M` is not yet known). `causal_runtime/fallback.py` solves it with the signal already on hand: the **ghost**.
Sustained ghost saturation ("the model is surprised *everywhere*") is a runtime self-estimate that the
structural field is unreliable; past a hysteresis-latched threshold the runtime degrades to the **distance
floor** — the model-free baseline that makes no future claim and so cannot be catastrophically wrong about `M`.

```
future_surface → allocation   while RELIABLE
distance       → allocation   at UNRECOVERABLE failure (sustained low reliability)
```

Two properties make it honest, both measured (Fallback benchmark): across a regime shift the degraded policy
captures **best-of-both** (more `M` than *either* fixed policy — it keeps the field's early edge, then recovers
to distance), and in a **stable** world it never needlessly falls back. "Unrecoverable" means *sustained* (a
transient ghost spike must not drop the smart field) — and the trigger is the field's own doubt, never a check
against reality. The ghost, which began as an attention engine for *ignorance*, is now also the **failure
detector** that decides when to stop trusting the field.

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
| **fallback** | the smart field can be a *worse* estimate of the objective than plain distance when its regime breaks (proven in `allocation.py`) | at *detected, sustained* failure the runtime must degrade to a model-free floor — using a runtime self-signal, never a truth oracle | ghost-saturation `reliability` → hysteresis `DegradationLatch` → **distance floor** |

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

Each law is the *enforcement* that makes a corresponding **epistemic bound** (below) structurally true — e.g.
`future_surface → hidden information FORBIDDEN` is what makes `future relevance ≠ hidden information` hold in
code, not merely in prose. **Laws say what implementations may do; findings say what the benchmarks currently
show; bounds say what a reader may conclude.** These are three different kinds of statement and the rest of this
section keeps them apart.

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
ghost-triggered distance fallback BEATS both fixed policies across a regime shift, and never degrades a stable world (Fallback)
a STALE field loses to fresh distance past a staleness boundary (~3 ticks at coherence 12) — the field needs freshness  (Adversary: late)
RAW consequence overspends on improbable futures (high consequence ⟂ low probability) and loses to distance; ×probability repairs it  (Adversary: wrong)
SELF-generated consequence is gameable — raw funds manipulators; ×independent_evidence repairs it  (Adversary: incomplete)
one shared field does NOT beat domain specialists within-domain (97% vs 99%); its conserved advantage is CROSS-DOMAIN coordination — the budget SPLIT — which wins under concentrated demand and loses to equal-split under estimate drift  (Cross-Domain Conservation: Outcome C)
```

The last one is a deliberate **non-superiority** finding kept on the record: the value of possibility-attention
is automation + determinism + self-update, not that it outperforms a hand-tuned heuristic.

## Epistemic Bounds — claims the system refuses to make

The deepest statements in the project are neither enforcement rules nor benchmark results. They are **limits on
interpretation**: they tell a reader what conclusion they are *forbidden from drawing* from any output. They do
not change with new data or new code — they are the meaning of the whole arc, and arguably its most important
semantics.

```
integrity         ≠ truth                 a hash certifies form, never correctness
possibility       ≠ truth                 "lawful / high-possibility" is not "real"
prediction        ≠ causation             a survived correlation is not a cause
surprise (ghost)  ≠ truth                 "the model was wrong here" is not "here is what is true"
proposal          ≠ authority             a proposed edge is evidence for review, not a fact
corroboration     ≠ truth                 "survived falsification" is not "proven"
model improvement ≠ world modification    the map changed; the territory did not
future relevance  ≠ hidden information     "matters to the future" grants fidelity, never visibility
```

The single sentence the entire chain reduces to:

> **The field allocates attention. The field does not allocate truth.**

Every major correction — trace → salience → possibility → consequence → ghost → falsification → LOD — has been
one more variation of the same refusal:

```
importance     ≠ truth
prediction     ≠ truth
surprise       ≠ truth
proposal       ≠ truth
corroboration  ≠ truth
```

The system gets stronger every time it finds a *new reason not to confuse attention with reality.* Each law
(above) enforces one of these bounds in code; each finding (above) is benchmark evidence *about the world* and is
permitted to be wrong — but a **bound is a promise the system makes about what it will never claim**, and that
promise is not the benchmarks' to revoke.

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
few seconds of play. The rasterization claim is therefore **not** "render what matters" (that smuggles in a truth claim); it is
**"allocate finite rendering budget toward state *predicted* to matter"** — and only over information the player
may already legally see. The hedge is load-bearing: *predicted to matter*, never *matters*.
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

## Proven vs Hypothesis (current ledger) — three tiers

The state of the evidence has three distinct tiers; keeping them apart is the difference between honest and
oversold. (Each ✓ item is a runnable benchmark with a negative control.)

**✓ PROVEN.** Future-surface can *outperform conventional allocation policies in a constrained benchmark while
preserving the anti-wallhack fairness invariant.* The fairness gate strengthens this rather than weakening it:
a critic could say "of course it wins if it renders strategically-important hidden objects" — but the occlusion
gate makes that impossible, so the policy's search space is **visibility-respecting only**, and it still wins.
Evidence: the formal allocation test (`allocation.py`, beats distance/magnitude/random against an *independent*
M, and is *falsifiable* — a bad-estimate world makes it lose); the LOD bench (`lod.py`); the fairness invariant
(`fairness_invariant`: an occluded enemy with the largest future_surface in the scene gets **zero** budget);
graceful degradation (`fallback.py`, beats both fixed policies across a regime shift); and the field winning
across *already-distinct* domain benchmarks — cache/network (Causal Freshness), AI attention (Blind Discovery),
structure-learning (Self-Confirmation), causal evidence (Causal Intervention). Plus the cardinal invariant: the
committed hash trajectory is byte-identical with every observation layer attached.

**✗ NOT YET PROVEN.** That *a real renderer* consuming the field produces measurably better gameplay-relevant
visual fidelity. The current chain stops at an estimate:

```
future_surface → triangle allocation → ESTIMATED error metric          (proven: a policy result)
future_surface → triangle allocation → actual rendered frame → actual perceptual loss   (needed: a rendering result)
```

`lod.py` measures allocation quality, not rendered outcomes. The transition from a **policy proof** to a
**rendering proof** requires a real rasterizer; until one passes the same equal-budget, fairness-respecting
test, the rasterization benefit is a hypothesis.

**◇ THE UNDERLYING HYPOTHESIS (the most important one).** That **future relevance is a useful general-purpose
resource-allocation signal across many domains** — compute, validation, networking, AI attention, *and*
rasterization — so that at a fixed budget the engine preserves more of the information that determines what
happens next. Evidence so far: the *same* future-surface composite already beats domain baselines across the
distinct benchmarks above. What makes the renderer the decisive test is not graphics — it is that distance LOD
and screen-space LOD are **decades-mature baselines** with enormous engineering behind them. Beating them at
equal budget, while respecting the fairness invariant, would be strong evidence that the allocation principle
*transfers* into a very different optimization problem. The renderer is simply the hardest place to test the
real claim. *(Honest bound, unchanged: even if it transfers everywhere, the field still allocates attention,
not truth — see the ROOT PRINCIPLE.)*
