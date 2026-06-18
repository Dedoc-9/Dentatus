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
