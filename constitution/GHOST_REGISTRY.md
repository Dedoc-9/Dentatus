# DENTATUS GHOST REGISTRY
## Catalogue of residuals

A **ghost** (Article III) is a numeric residual, never an entity. This registry names every residual
encountered so it can be reasoned about and not silently absorbed. Status: ✓ resolved · ◐ managed/
guarded · ○ open. The defining residual `G_t = Z_t − Π_{W_t}(Z_t)` underlies them all.

## Series 300 — substrate (abridged)

| # | Name | Status |
|---|---|---|
| 1 | `G_inject` auxiliary residual (EXP-311) | ✓ |
| 2 | Asymmetric budget (EXP-312) | ✓ |
| 3 | Mass-weighted centroid divergence | ✓ |
| 4 | κ P_yz symmetry | ✓ |
| 5 | LOD_RELAXED validity propagation | ◐ |
| 6 | Ω_AC primary-path degeneracy | ✓ |
| 7–8 | numerical / block-diagonal skips | ◐ |
| 9 | **Stale file write (NTFS Edit/Write truncation)** — tooling: use direct writes + `py_compile` | ◐ |
| 14–19 | EMA warmup overshoot, parametric resonance, Attraktorwahl | ◐ |
| 21 | Zusammenhang stiffness (ε_manifold calibration floor) | ◐ |

## Series 400/500 — manifold & firewall

| # | Name | Status | Where |
|---|---|---|---|
| 22 | Neighbor explosion (degree-normalize G_ent) | ✓ | 502 |
| 23 | Temporal decoherence (Stateful Seed precursor) | ✓ | 504 |
| 24 | Cold-reset vs accumulation | ✓ | 504 |
| 25 | Manifold-induced latch evasion (maintenance-gating) | ✓ | 503 |
| 26 | Equilibrium stiffness | ✓ | 504 |
| 27 | Claim-id-order nondeterminism | ✓ | 504/601 |
| 28 | Spatial-key drift (moving claims) | ✓ | 505 |
| 29 | Non-rigid / independent motion | ✓ | 506/510 |
| 31 | Verdict leakage (observable purity) | ◐ guarded | 508 |
| 32 | Cross-process hash-seed nondeterminism (HASHSEED pin) | ✓ | 602 |
| 33 | Outer-loop backreaction (Agency Latch) | ✓ | 603 |
| 34 | Sector D stress realization-inert | ◐ | 509-precursor |
| 35 | Agency Attraktorwahl (local stress minimum) | ◐ | 603 |
| 36 | Fiedler sign ambiguity | ◐ | 506 |
| 37 | Budget self-satisfaction | ◐ | 508 |
| 38 | Coarse-grid resolution (section-boundary fault) | ◐ | 506 |
| 39 | Coarse Laplacian density (streamable) | ◐ | 507 |
| 40 | Moving sections (multi-velocity) | ✓ | 510 |
| 41 | Coarse history depth | ✓ | 606 |
| 42 | LRU sizing vs working set | ◐ | 606 |
| 43 | Calibration vs autonomy (`a₀` fixed engine constant) | ◐ | 509 |

## Series 510+ — kinetic (new this arc)

| # | Name | Definition | Status | Where |
|---|---|---|---|---|
| 44 | Kinematic residual & octant-assignment churn | `G_kin = C_match − Ĉ`; section-boundary reassignment is a coarse-graining artifact | ◐ managed | 510 |
| 45 | Mass-churn / count-vs-volume | leaf-count is a discretization artifact; mass ≡ integrated **volume**, EMA-stabilized vs churn | ✓ | 511 |
| 46 | ε_ref scale-relativity | dimensional strain made ε_ref per-world; closed by non-dimensionalisation | ✓ | 512→513 |
| 47 | Vorticity singularity | Weissenberg `strain/‖Ω‖` divergent at ‖Ω‖→0; **floor** (not additive ε) preserves exact scale-invariance | ✓ | 513 |
| 48 | Compliance-not-stiffness inversion | bounded multiplier must be *compliance* (χ≤1, narrows only); wiring as "stiffness" inverts the firewall | ✓ guard | 514 |
| 49 | Melt hysteresis (entropy ratchet) | enacted melt was one-way; **closed** by EXP-521 re-crystallisation (distinct lower cooling threshold → true hysteresis, chatter-free) | ✓ | 515→521 |
| 50 | Audit-vs-live gap; destination-confluence | DAG recorded valid nodes not in live state (closed by 517); path lives in edges, not node id | ✓ | 516→517 |
| 51 | Injection ghost & inactive-claim accumulation | re-declaration jumps `Z` by `ΔZ`, absorbed into `S` via `next_S`; inactive claims accrue (→ compaction) | ✓ | 517→518 |
| 52 | Compaction shadow & hot/cold undo asymmetry | `η_CLT` preserved only via permanently-retained sufficient statistics; undo O(1) hot, replay-cost cold | ◐ managed | 518 |
| 53 | Checkpoint cadence & unbounded command log | `K` trades memory for replay latency (warm tail); the command log is the minimal unbounded tier; `verify_history` is a continuous determinism monitor | ◐ managed | 520 |
| 54 | Amorphous lock | a fully isotropic (total-melt) state has no residual order to amplify; **closed** by EXP-522 oriented nucleation (re-crystallise along the strain principal axis). Residual `no_orienting_field` case (isotropic stress) is symmetry-correct, not a lock | ✓ | 521→522 |

## Principle

> When a state space is coarse-grained into discrete segments, the resulting event boundaries are
> essentially arbitrary constructs of the model rather than inherent limits. Several ghosts (#38, #44,
> #47, #49) are exactly such boundary artifacts; the registry exists so they are treated as numeric
> residuals — surfaced, bounded, and never reified.
