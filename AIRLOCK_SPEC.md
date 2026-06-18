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
