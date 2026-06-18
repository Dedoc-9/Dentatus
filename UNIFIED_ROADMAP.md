# Unified Roadmap — the deterministic Reality Engine an LLM can integrate with

> Re-anchor + **hardening** doc. The aether line grew a deep self-observability research tree (Stages A–E).
> The hardening here is **not new architecture** — it is a set of *locks* that stop capability drift and
> point the remaining work at the one unfinished seam. The realignment IS the hardening step.

## The one goal (stated honestly)

A **deterministic, cryptographically-verifiable 2D/3D reality engine** — the *logic core* of a game/sim
engine where world-state is bit-exact reproducible and content-addressed (`canonical bytes → SHA-256`),
built so an **LLM integrates as an untrusted, high-velocity proposer behind a verification airlock**. It
competes on **determinism, verifiability, replayability** — NOT render fidelity or speed. (Reference kernel
+ verification spine. No "Better UE5 graphics," no "galactic MMORPG" as a claim.)

## The risk this doc closes

The failure mode after Stages B–E is **not missing capability — it is capability drift.** The observability
stack became interesting enough to expand indefinitely while the actual engine seam stayed unfinished. The
inversion that prevents this:

```
aether observability  →  instrument panel      (KEEP)
aether observability  →  the product           (REJECT)
```

## The hardened spine (and the one directional law)

```
LLM  →  Airlock  →  AetherPulse Kernel  →  Proof / State Hash  →  Telemetry
                                              │
            observability attaches as:        ▼
                              Kernel trajectory  →  Aether metrics        (ALLOWED)
                              Aether metrics     →  Kernel behavior        (FORBIDDEN)
```

The arrow only ever points **kernel → metrics**. The reverse is the breach the whole branch exists to
forbid.

## The five locks

**Lock 1 — Freeze the pressure axes.** `M̂_E = (geometry, residual, dynamics, representation, spectral,
coherence)` is now a **measurement surface, not a research target.** No new axis is added unless it answers
a *concrete engine failure mode*. Stage E's predictive-gate negative is the natural boundary; the
instrument is complete.

**Lock 2 — The engine contract.** The LLM **never directly mutates state.** It emits a *candidate
transition*, and only the kernel commits:

```
LLM proposal  →  deterministic delta  →  validation  →  commit
```

**Lock 3 — `telemetry ≠ control` is an AetherPulse architectural law.** aether may *report* geometry,
residual, dynamics, and spectral pressure; the kernel decides **solely** by its declared transition rules.
No observable — ghost, regime, coherence, or any future metric — may gate, steer, or branch the runtime.
(This is the same purity rule proven across Stages B–E, promoted from a module invariant to an engine law.)

**Lock 4 — The airlock is the research frontier (not the manifold).** The open question is no longer "can
the manifold become smarter?" It is: **"can a non-deterministic proposer participate in a deterministic
world model without contaminating state identity?"** The seam takes a typed proposal object

```
p = ( Δ, intent, constraints, provenance )
```

through the pipeline

```
fuel (bounded, deterministic apply)  →  apply  →  hash  →  witness (quorum k-of-n)  →  commit (tessera shard)
```

with `elenchus`/`polity` deciding admissibility before commit. `intent`/`provenance` are *captured at the
boundary* (recorded inputs), never trusted as truth — `integrity ≠ truth`.

**Lock 5 — Research is parked, not abandoned — they are downstream consumers.**

| Branch | Becomes | Direction |
|---|---|---|
| `AetherManifold` | a specialized **optimizer source** (pose/IK/calibration), pulled in on demand | downstream |
| aether Stages B–E | **diagnostics** on the kernel trajectory | downstream |
| `aether` SPD / coherence / regime | **explainability & debugging** surfaces | downstream |
| `VeriSim` | **demonstration / validation** of the verifiable-sim claim | downstream |

None is dead; each consumes the kernel's trajectory, never feeds its decisions.

## Branch role map (critical path vs. supporting)

| Branch | Role | Critical path? |
|---|---|---|
| **`AetherPulse/`** | **The engine spine** — deterministic 3-D fixed-point kernel + conformance + native-port contract | **Yes** |
| `aether/` (fixedpoint, stiefel, spd) | shared deterministic **math/geometry substrate** | Yes — substrate |
| `aether/` (ghost, field, regime, coherence, predictive) | **instrument panel** (frozen at depth, Lock 1) | Supporting — monitor |
| `VeriSim/` | **verifiable-simulation product face** | Yes — product surface |
| airlock siblings (`fuel`, `elenchus`, `guard_server`, `polity`, `quorum`, `tessera`, `stasis`) | **the LLM-integration boundary** (already built) | Yes |
| `AetherManifold/` | **parked optimizer source** | No — on demand |

## The single next build (the only unfinished seam)

**[DONE — `airlock/`]** The LLM-airlock seam — Lock 2 + Lock 4 realized: a `propose → validate →
commit` path where a typed proposal `p = (Δ, intent, constraints, provenance)` passes `fuel` (bounded,
deterministic apply) + `elenchus`/`polity` (admissible?) + `quorum` (witness the post-delta state hash)
**before** the kernel commits, emitting a `tessera` shard. aether `regime` reads the committed trajectory
as **read-only telemetry** (Lock 3). Reuses every existing component; adds no research surface. The next
meaningful uncertainty is not mathematical — it is whether a non-deterministic proposer can interact with
the deterministic kernel while preserving the integrity model the stages spent their effort proving.


## Hardening lock — two execution regimes, one world identity (Stage F/G governance)

The vision can expand into a creative/dev platform AND a physics engine. To stop these becoming *competing
products*, the hardening rule: **one deterministic world model, two execution regimes, the novel physics as
the integrity SUBSTRATE — never the runtime burden.**

```
            INTEGRITY (how hard you check)  — severity dial, validator depth
                    ▲
   scientific-grade │  maximize truth · invariants · replay · proofs   (offline / audit / physics-grade mode)
                    │
   world-engine     │  maximize responsiveness · scale · iteration      (real-time / game mode)
                    └──────────────────────────────────────────────►  FIDELITY (where you look / render)
```

**Locks:**
- **`fidelity ⟂ integrity`** — independent axes. A game may be visually extreme, physically approximate, and
  still deterministic + auditable; a simulation may drop visual load and raise validation. Same world model.
  (Proven: `airlock/demo_fidelity.py` — multi-fidelity per region via a severity *policy*; near-zone strict,
  far-field cheap, one world.)
- **Physics = integrity substrate, not runtime burden.** The novel work (deterministic world identity,
  constraint-aware transitions, severity audits) is the *foundation*; it never slows the hot path unless a
  policy raises severity there.
- **`intent ≠ authority` survives the creative layer.** Vibe-coding / scene-gen / agents live ABOVE the
  membrane as proposers; the product experience is `intent → possibility → verified reality`, but the kernel
  remains the only authority. The creative layer must never become the authority layer.
- **Layer separation (the product shape):**
  `human/LLM intent → creative workspace → airlock membrane → deterministic kernel → observability (aether)`.

**Parked (future, NOT built — explicitly, to prevent drift):** the *Creative Reality Interface* (vibe-coding
UI, scene generation), and the broader *World Fidelity Layer* (temporal abstraction — what must simulate vs
interpolate vs reconstruct; perceptual abstraction — what the player sees vs the kernel knows vs the auditor
verifies). These are *richer severity policies and adapters over the existing membrane*, not new substrate.
The pioneering research question stays narrow: **can one deterministic world model support creative
generation, real-time simulation, and scientific audit without changing the identity of the world?**
