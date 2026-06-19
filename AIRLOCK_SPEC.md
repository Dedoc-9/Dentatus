# Airlock Spec — the contract between a non-deterministic proposer and the deterministic kernel

> The lock. AetherPulse becomes neither a simulator with a chat box nor a goal-deciding agent; it becomes a
> **governed creative workspace** where humans and LLMs explore freely while reality changes only through
> auditable, reproducible, bounded operations. This file is the authoritative contract; `airlock/` implements it.

## The membrane is general (reality ⊋ physics)

The airlock is the **general reality-transition membrane**, not an LLM feature. The LLM is merely the first
uncertain proposer that exercises it; agents and humans are other clients. "Reality" is whatever a
deterministic **adapter** defines — physics, **config/repo state, runtime, deployments, proofs**. The membrane
and both laws are invariant across realities; only the adapter changes. Four pillars keep it a platform:
**typed transition schemas · deterministic adapters · replayable proofs · portable conformance vectors.**

## Two laws (architectural, not advisory)

1. **`telemetry ≠ control`** — observables (`R_p`, aether `regime`/ghost/spectral metrics) may be *reported*;
   the kernel decides **solely** by its declared transition rules. The arrow is one-way:
   `kernel trajectory → metrics` (allowed), `metrics → kernel behavior` (forbidden).
2. **`intent ≠ authority`** — the LLM expresses goals/intent/claims as **untrusted planning context**; none of
   it commits state. Only bounded, canonical, reproducible transitions do.

## What crosses the membrane

A typed proposal, never raw intent and never code:

```
p = ( transition, claims, constraints, provenance, budget )
    transition  — one declared bounded op (spawn | impulse | advance | …)
    claims      — DECLARED expectations; verified-not-trusted; feed R_p only (telemetry)
    constraints — hard admissibility (max_bodies, in_bounds, …); mechanical gates
    provenance  — who/why; captured at the boundary; NEVER authorizes
    budget      — max_cost, max_delta (fuel)
```

## The pipeline (one-way; any reject → evidence, never mutation)

```
CANON → SCHEMA → BUDGET → SHADOW APPLY (pure) → VALIDATE → [R_p telemetry] → WITNESS → COMMIT (shard)
```

- **Shadow apply** is a pure function `Apply(p, state) → state'` (no write-back); only an admissible candidate
  is promoted. `R_p = ‖Δ_proposed − Δ_real‖` is the proposal residual (the LLM's ghost) — telemetry only.
- **Witness** = reproduction-admission: ≥k independent re-derivations reproduce `hash(state')`; witnesses attest
  *determinism*, not merit (`witness ≠ controller`).
- **Commit** emits a content-addressed, hash-chained, optionally-signed shard. Rejections emit proof-of-rejection
  shards into an **append-only** ledger; the kernel stays memoryless w.r.t. them.

## Goals vs transitions (resolved)

The kernel admits **transitions only**. Goal-direction is an **external, untrusted planning layer** that
decomposes a goal into bounded transitions *before* the membrane. A raw goal is rejected at the schema.
**Mechanism in the core; normativity at the edge.** `polity`/`elenchus` remain admissibility *gates* on
transitions, never goal-authors.

## Honest bound

A commit proves a transition was applied **exactly and admissibly**, never that it was correct, fair, or wise.
`integrity ≠ truth`.

## Severity — a toggleable layer, so one engine serves games AND physics

Severity toggles **validator DEPTH, never the kernel.** The deterministic kernel (and renderer) stay fast at
every tier; only the admissibility depth changes, and the heavy checks default to **off the hot path**.

```
tier 0  game/real-time      cheap inline gates (canon·budget·bounds·‖Δ‖)        blocks · frame-rate
tier 1  sim/dev             + conservation/regime as TELEMETRY or low cadence    measured, not gating
tier 2  strict/relativistic + causal/constraint/invariant checks                 inline (offline sim) OR
                                                                                  async physics-court audit (games)
```

Rules that keep the game-engine goal intact:
1. **Severity gates the validator, not the kernel.** Lawful transitions produce the *identical* committed
   world at every severity (verified): severity changes *admissibility*, never deterministic output.
2. **Heavy validation runs off the hot path by default.** At `game` severity the strict validators are
   **deferred**; `membrane.audit()` is the **physics court** — it re-derives a committed transition, runs the
   heavy checks offline, and emits a `FLAG`/`PASS` verdict shard that **references** the commit, never mutates
   it (witness ≠ controller). Inline-strict is opt-in for non-real-time scientific use.
3. **Severity is declared and hashed into the commit** (`shard.severity`); a strict audit is a *separate*
   verdict, not a retro-rewrite.
4. **Fidelity ⟂ severity.** Float/GPU rendering draws what the integer kernel decides; severity is integrity
   depth, not visuals.
5. **Severity may be a POLICY** `(world, txn) → tier`, not just a fixed tier — enabling **multi-fidelity**:
   different regions/objects/times of the SAME world audited at different depth (near-camera strict, far-field
   cheap). Spatial/temporal/perceptual abstraction = a richer policy, not new substrate. (`airlock/demo_fidelity.py`.)

### Stage F (future): the Relativistic Integrity Layer — a strict-tier ADAPTER

GR is **just another adapter** (general-membrane), whose `validate_strict` implements the relativistic laws —
you pay for it only at strict severity / audit:

- **`causality ≠ convenience`** — no transition may violate declared causal structure (light cones, local
  propagation, conservation). *(Today: a toy `c_limit` speed cap stands in — `adapters.validate_strict`.)*
- **`geometry ≠ telemetry`** — curvature, geodesic deviation, invariants are *measured*, never hidden steering
  (the established `telemetry ≠ control`, made physical).
- **`observer ≠ author`** — different coordinate descriptions of the same physical state should converge toward
  **diffeomorphism-invariant** state hashing.

Honest claim: **not** "a 240 fps GR engine." Rather — *a deterministic integrity architecture that can host
general-relativistic simulations while preserving provenance, causal consistency, and human/AI interaction
boundaries*, with severity declared and reproducible. Most engines simulate the equations; few treat the
simulation itself as an auditable physical object. `integrity ≠ truth`.

## Transition space — measuring what almost happened

Most systems record only what happened. This membrane records what *almost* happened — every unrealized
transition leaves a trace (rejection shards, proposal residuals `R_p`, shadow candidates). `admissibility.py`
makes those traces a **first-class observable**: the *geometry of admissibility* a session moved through.

```
States  ⊂  Transitions  ⊂  Admissibility manifold
Reality = a trajectory through a continuously filtered space of candidate transitions.
```

- **Proposal pressure** = unrealized / proposed (per-mille) — how strongly the admissibility structure shaped
  realized history. In ordinary physics it is assumed ≈ 0 (nature instantiates lawful evolution directly). In
  an agent-rich world (humans, LLMs, planners) actors continuously propose trajectories only partially
  realized, so it is **not** zero — and it becomes measurable.
- **Shape of the filter** = the gate histogram (CANON/SCHEMA/BUDGET/APPLY/CONSTRAINT/STRICT/WITNESS) — *where*
  reality rejected candidates.
- It sits alongside the kernel/aether observables (energy, momentum, curvature, entropy, ghost) as the
  membrane's own pressure axis.

**Honest bound:** this is a *modeling lens and an observability surface*, **not** a claim about nature. It is
pure telemetry — it never gates, steers, or enters identity (`telemetry ≠ control`). `integrity ≠ truth`:
proposal pressure measures the filter's *shape*, never whether the filter is *right*. Whether the geometry of
admissibility describes physical systems containing adaptive intelligences is an empirical question this code
does not answer — it only makes the question measurable.

## The lawful possibility space — "arbitrary" made measurable

The rejection ledger sees `possible \ admissible` (the inadmissible). It is blind to `admissible \ realized`
— transitions that were fully LAWFUL but not chosen. That second gap is the mathematician's **"arbitrary"**:

```
possible  ⊋  admissible  ⊋  realized
   (all)      (lawful)       (chosen)

"Let x be arbitrary"  ==  "any member of the admissible set; the choice is free within the structure."
```

`possibility.py` shadow-evaluates a set of candidate proposals against ONE state (no commit; the world never
advances), returning the **admissible set** (the lawful freedom), the **inadmissible** (filtered, by gate),
a **freedom** measure (|admissible|·1000/proposed), and the **admissible-but-unrealized** remainder — the
lawful alternatives every bit as admissible as the one that became real.

"Arbitrary" is therefore not the absence of structure but **freedom constrained by an unseen boundary**: in
mathematics that boundary is the axioms, in physics the laws, in this engine the airlock. The realized world
is a *projection of the possible through constraints*; "Hello, World" is a possibility crossing that boundary
into an actual state.

**Honest bound:** pure analysis — it never commits, gates, or enters identity. It measures the size/shape of
the admissible set *under the declared structure* (airlock + adapter + constraints + severity), never that
the structure is the right one. `integrity ≠ truth`.

## The geometry of the unrealized field — possibility pressure

Counting the unrealized is not measuring it. `horizon.py` measures the **shape** of the admissible-but-
unrealized field *surrounding* a realized state — the deepest idea of the project made operational:

> Reality is not only a trajectory through state space. It is a trajectory through a field of unrealized
> admissible alternatives, and the geometry of that field can itself be measured.

For each admissible-but-unrealized alternative it computes (in shadow) the exact-integer distance of that
alternative's outcome from what became real, then aggregates:

- **reach** — how far the surrounding possibility extends (max distance),
- **dispersion** — how spread the field is (mean absolute deviation),
- **possibility pressure** — Σ distances: the total magnitude of the could-have-been around what-was.

Two states can share the *same realized history* yet sit in wildly different possibility fields (a demo shows
pressure ≈ 77 vs ≈ 2). That difference is what a **player feels** — worlds feel *alive* when the engine knows
not just what happened but what could have; and it is what a **physicist asks** — *why this realization
instead of another admissible one?*. The engine can now count and shape those alternatives.

**Honest bound:** pure shadow telemetry (reality is never touched); the geometry is measured *under the
declared structure*, and "pressure"/"aliveness" are magnitudes, not claims about nature. `integrity ≠ truth`.

## Impact density → validation depth (the resolution law)

The severity dial, made a predicate of consequence. How carefully a *mutable* transition is resolved scales
with how much future it touches — a shot at a wall is cheap; a shot at the artifact-holder is deep — but the
committed result is **invariant** to that depth.

```
impact_density → validation depth (shadow depth · witness strength · rollback budget · network priority)   ALLOWED
impact_density → committed outcome                                                                          FORBIDDEN
```

`airlock/impact.py`: `impact_density` (true downstream divergence, act-vs-natural), `cheap_impact` (the
immediate effect magnitude — an O(apply) predicate), and `validation_policy(threshold)` → an airlock severity
policy. Measured: the cheap predicate ranks transitions by true downstream impact (Spearman 1.00 on kinematic
consequence) and a low-impact transition committed at game / strict / impact-policy severity yields the
**identical** `post_hash` (`airlock/demo_impact.py`). Honest bound: 1.00 holds because kinematic divergence ≈
immediate magnitude in linear-ish dynamics; the hard case (small cause, large downstream consequence — a
trigger / chain reaction / quest unlock) needs nonlinear or game-state dynamics, where a cheap proxy may fail
and fall back to true impact. The mechanism and the law are proven; that robustness is the open question.

### The clean stack

```
kernel
  └─ airlock
       ├─ admissibility    can this happen?        (gate → committed truth)
       └─ consequence field how much does it matter? (telemetry → never truth)
            ├─ salience          where to spend compute      (attention scheduler)
            ├─ validator depth   how much proof              (impact → severity)
            ├─ network priority  what to send first
            └─ AI attention      who gets to think
```

The single constraint that keeps this a runtime architecture and not a predictive simulator: **future
importance can decide where we look; it can never decide what is true.**
