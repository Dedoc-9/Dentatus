# aether — the hardened integer manifold (deterministic physics, exactly constrained)

The DVSM geometry was beautiful but ran on floating point (f32/f64), which drifts across machines and
violates `fuel` strictness. `aether` re-implements the manifold in **fixed-point integers** so the evolution
is bit-for-bit identical on any machine, and it gates the geometry with a **Stiefel auditor**: the residual
energy `E = ||WᵀW − I||²_F` must stay under a strict declared threshold, and when it doesn't, the system
**deterministically self-retracts** back onto the manifold and logs the recovery as a verifiable event.

> The razor-sharp honesty bar: we do **not** claim a fixed-point frame is perfectly orthonormal in real
> arithmetic — that is impossible, fixed point quantizes. We claim that within the integer lattice the
> deviation never exceeds a declared `epsilon`, and that a breach is not a bug but an **event that triggers a
> verified recovery**.

## Run it

```
PYTHONHASHSEED=0 python3 demo_aether_physics.py        # exact gate · the 1-ulp truth · spinning top · ghostsnap
PYTHONHASHSEED=0 python3 tests/test_aether_stiefel.py  # 11 unit tests (gate · audit · retraction)
PYTHONHASHSEED=0 python3 tests/test_aether_ghost.py    # 12 unit tests (Stage-B dual ghost channel)
PYTHONHASHSEED=0 python3 demo_aether_spd.py            # Stage C: SPD cone · adaptive cadence · pure ghost
PYTHONHASHSEED=0 python3 tests/test_aether_spd.py      # 10 unit tests (Stage-C SPD geometry)
```

## Fixed-point is deterministic, not exact (and that's the point)

A real value `v` is stored as `round(v · SCALE)` (`SCALE = 2³²`). `fp_mul` truncates **toward zero** by one
fixed rule, so every machine computes the identical bits — but a multiply carries a bounded quantization
residual. The demo shows it bluntly: the Lie bracket `[A,B]` of two skew matrices, which is exactly `0` in
real arithmetic, comes out as a **1-ulp residual** in fixed point. That single ulp is *why* `aether` gates on
a declared `epsilon` and retracts, instead of pretending the arithmetic is exact.

Two honestly-separated gates:

| gate | for | tolerance |
|---|---|---|
| `is_orthonormal_exact(cols, denom)` | states held in **exact rationals** (`WᵀW == denom²·I`) | **none** — exact or fail-closed |
| `check_orthogonality(W, epsilon)` | an **evolved fixed-point** frame (`E = Σ Rᵢⱼ²`) | a **declared integer** `STIEFEL_EPSILON_INT` (a named cut, not a float eps) |

## The audit / retraction loop

`lie_step` advances a frame under a skew generator (`W ← W + dt·(A@W)`, forward-Euler on the orthogonal
group). `evolve_audited` audits `E` every N steps and, on a breach, runs `gram_schmidt_integer` (modified
Gram-Schmidt in fixed point, exact integer `isqrt`) to force `W` back onto the Stiefel manifold —
`handle_retraction` emits a content-addressed (optionally signed) `RETRACTION` shard `{old_E, new_E,
energy_drift}`. If Gram-Schmidt can't reach `epsilon` (rank failure), it **reverts to the last valid hashed
state**.

The **spinning top** demo evolves a 3×3 frame **1,000,000 fixed-point steps** in ~7s: the auditor
self-retracts on every breach (~500 times), the final frame is provably on-manifold (`E ≤ epsilon`), and a
re-run is **bit-for-bit identical**.

## Stage B — the dual ghost channel (instrumentation, observable-only)

`lie_step` (`Lτ`) pushes the running frame **off** the manifold by a bounded quantization; the retraction
`Π_W` (`gram_schmidt_integer`) projects it back. Stage A *destroyed* that residual. Stage B **preserves it**
as a dual accumulator, separate from the forward arithmetic, so later geometry/dynamics changes can be judged
against a measured baseline instead of a guess.

```
math:  Zₜ = Lτ(Wₜ₋₁)                       # running, off-manifold forward frame   (canonical Z)
       Wₜ = Π_W(Zₜ)                        # its on-manifold projection            (canonical W)
       Gₜ = Zₜ − Π_W(Zₜ)                   # ghost residual (every measured step)
       S_{t+1} = α·Sₜ + (1−α)·Gₜ           # matrix EMA, dual space
       B(t) = ‖S‖_F / (‖Z‖_F + ε)          # backreaction-pressure observable
       η_CLT = √N·(μ̂ − μ₀)                 # zero-mean leak (μ₀=0) vs structured drift
code:  Z = lie_step(W,A,dt); Wp = gram_schmidt_integer(Z)   # Wp = measurement, never written back
       G = sub(Z, Wp); S = ema_matrix(S, G, alpha_fp)       # ghost.py — fp_mul, symmetric trunc
```

**Two contracts.** *Determinism:* `S` accumulates via the **same** symmetric-truncation `fp_mul` and a
fixed-point `α` as the forward path — never native floats — so the EMA is bit-for-bit replayable and the
dual space inherits the sign-symmetry that lets skew structure survive. *Purity:* `S`, `B(t)`, `η_CLT` are
**observables** — measurement runs `Π_W` every `measure_every` steps but **never writes back to `Z`**, and
the **retraction control** still fires only on an `E > epsilon` breach. The forward trajectory and the legacy
`final_hash` are therefore byte-identical to Stage A (proven across configs).

**Structural identity (`protocol_version: aether/2`).** The ghost is first-class state, so it enters the
structural hash: `Hₜ = HASH(μ ⊕ Z ⊕ S ⊕ W ⊕ protocol_version)` (`ghost.structural_hash`). Two runs with equal
`W` but `S¹ ≠ S²` are now **distinct identities**. A parallel `Hₜ_legacy = HASH(W)` (`stiefel.state_hash`) is
retained byte-identical as the regression oracle for historical goldens — so the bump is purely additive.

**Honest bound.** `B(t)` and `η_CLT` measure quantization-leak *pressure* and whether it is unstructured —
**not** that the trajectory is correct, and **never** a control input. New ghost in the aether ledger: the
quantization-leak residual. (Cross-geometry note: `G` is defined relative to `Π_W`; ghost magnitudes are not
directly comparable across different retractions — a Stage-D concern.)

## Stage C — the SPD covariance cone (log-Cholesky) with an E-driven adaptive cadence

Stage B instrumented the Stiefel frame; Stage C adds a **second geometry** — the symmetric
positive-definite cone `P ≻ 0` (the Sector-D covariance manifold) — and an **adaptive** projection policy.
The retraction `Π_W` becomes `Π_SPD`.

```
parametrization:  P = L·Lᵀ,  L lower-triangular, diag(L) > 0          # Cholesky / log-Cholesky
exact gate:       is_spd_exact(P) ⟺ every leading principal minor > 0  # Sylvester, integer, no epsilon
retraction:       Π_SPD(P) = recompose(cholesky_repair(symmetrize(P))) # clamp non-positive pivots ≥ floor
gate signal:      gershgorin_margin(P) = minᵢ(Pᵢᵢ − Σⱼ≠ᵢ|Pᵢⱼ|) ≤ λ_min  # cheap O(n²), no sqrt
```

**E-driven adaptive retraction (the latency idea, purity-preserving).** Each step computes the **cheap
Gershgorin lower bound** on `λ_min` — the *gate* observable. The **expensive** Cholesky retraction `Π_SPD`
fires only when that margin drops below a declared `margin_tol` **or is predicted to cross it within
`horizon` steps** (linear extrapolation of its decrease). Projection effort therefore *tracks geometric
drift*: near-zero retractions when the state sits deep in the cone (demo C: 0 vs a uniform policy's 62),
many when drift genuinely threatens the boundary (demo D: holds the cone where no-retraction breaks it).
The cadence is driven **only** by the gate margin — the ghost `S`/`B(t)`/`η_CLT` are measured every step
but **never** read by the controller (observable purity; no `S → Π_SPD → P → S` feedback loop).

**Honest bounds.**
- `Π_SPD` is idempotent only **up to fixed-point quantization** (a few ulps) — deterministic, not exact.
- The cadence guarantees the **committed** state is on-cone; the forward `Z` may leave the cone by a
  *bounded* amount between steps (captured by the ghost `G = Z − Π_SPD(Z)`), then is repaired.
- This is the log-Cholesky **parametrization** with an exact positivity gate and a Cholesky retraction —
  **not** a full geodesic integrator (the flat log-diagonal metric coordinate needs a fixed-point `ln`,
  deferred). The log-Cholesky metric ≠ the affine-invariant metric; geodesics differ (a declared cut).
- Cross-geometry note: `G` here is relative to `Π_SPD`, so its magnitude is **not** comparable to the
  Stage-B Stiefel ghost. Attribution holds within a fixed projection, never across.

## Ties

| sibling | role |
|---|---|
| `fuel` | the evolution is pure integer — it can run inside the bounded-execution VM |
| `tessera` | a manifold state / retraction is content-addressed and replayable |
| `crucible` | near-degenerate seeds stress the retraction (it must recover within budget) |
| `stasis` | canonicalizes raw input into the fixed-point lattice at the boundary |
| `manifold` | topology gate; `aether` is its exact-geometry companion (manifold hardening) |

## Honest bounds

- Fixed-point is **deterministic and replayable**, not exact — quantization is bounded and reproducible,
  never random or machine-dependent. "No drift" means no *nondeterministic* drift.
- Orthonormality under evolution holds only within the **declared `epsilon`**; exact, epsilon-free
  orthonormality survives only for static rational frames.
- **integrity ≠ truth:** `aether` proves the simulation ran exactly these steps and held the declared
  structural tolerance — never that it models real physics.

## Files

| File | Role |
|---|---|
| `fixedpoint.py` | fixed-point integer arithmetic (`to_fp`, `fp_mul` symmetric trunc, matmul, identity) |
| `stiefel.py` | exact gate, `frobenius_energy`, `check_orthogonality`, `gram_schmidt_integer`, `handle_retraction` |
| `ghost.py` | **Stage B** dual channel: `ghost_residual`, `ema_matrix`, `backreaction` B(t), `clt_eta`, `structural_hash` (Hₜ), `PROTOCOL_VERSION` |
| `spd.py` | **Stage C** SPD cone: `is_spd_exact` (Sylvester), `cholesky_int`, `project_spd` (Π_SPD), `spd_error` (E_SPD), `gershgorin_margin`, `SPD_PROTOCOL` |
| `evolve.py` | `is_skew_symmetric`, `lie_bracket`, `lie_step`, `evolve_raw`, `evolve_audited` (Stage B); `evolve_spd_audited`, `symmetrize_add` (Stage C, E-driven adaptive cadence) |
| `demo_aether_physics.py` | exact gate (A) · 1-ulp truth (B) · 1,000,000-step spinning top (C) · ghostsnap (D) |
| `tests/test_aether_stiefel.py` | 11 unit tests (exact gate, audit, retraction, evolution, crucible stress) |
| `tests/test_aether_ghost.py` | 12 unit tests (ghost closure, fp EMA, observable purity, η_CLT null, structural identity) |
| `demo_aether_spd.py` | Stage C: exact gate · Π_SPD repair · adaptive cadence (calm vs strong drift) · pure ghost |
| `tests/test_aether_spd.py` | 10 unit tests (Cholesky, Sylvester gate, retraction, adaptive cadence, purity, anchor) |
