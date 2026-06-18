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
PYTHONHASHSEED=0 python3 demo_aether_field.py          # Stage D: generator field · Magnus-2 · meta-layer
PYTHONHASHSEED=0 python3 tests/test_aether_field.py    # 11 unit tests (Stage-D field + meta-observability)
PYTHONHASHSEED=0 python3 demo_aether_coherence.py      # Stage E: spectral observability over SPD
PYTHONHASHSEED=0 python3 tests/test_aether_coherence.py # 11 unit tests (Stage-E spectral layer)
PYTHONHASHSEED=0 python3 demo_aether_predictive.py     # Stage-E hardening: incremental predictive-value gate
PYTHONHASHSEED=0 python3 tests/test_aether_predictive.py # 4 unit tests (held-out predictive gate)
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

## Stage D — the self-describing generator field A(W,t,θ) + meta-observability

Stages A–C used a **constant** generator, so `[A,A]=0` and the Magnus/BCH bracket `Bτ` was dormant.
Stage D promotes the generator to a structured field `A = A(W,t,θ)`, where `θ` is a **declared, hashed**
parameter bundle. The hard causal rule: `A` (and `θ`) may read **configuration, schedule, forcing, `W`,
`t`** — but **never** `S`, `G`, `B(t)`, or `M̂`. The forward path stays ghost-blind (enforced by the
`A(W,t)` signature); residual/meta channels read the forward path, never the reverse.

```
field:        A(W,t) = A0 + g(W,t;θ)·B0        # g mixes a state term (k·W[r][c]) and a schedule term
Magnus-2:     Ω = dt·(A_k+A_{k+1})/2 + (dt²/12)[A_k,A_{k+1}]   # the bracket term IS Bτ
hierarchy:    β₁=‖[A_k,A_{k+1}]‖   β₂=‖[A_k,[A_k,A_{k+1}]]‖   β₃=‖[A_{k+1},[A_k,A_{k+1}]]‖
meta-vector:  M̂ = (E/ε, ‖G‖/‖Z‖, B(t), β₁/‖A‖, β₂/(β₁+δ), β₃/(β₁+δ))   # all dimensionless, all observed
```

**Representation pressure (the fourth axis).** `β₂/β₁`, `β₃/β₁` are the truncation-stress of Magnus-2:
small ⇒ second order adequate; growing ⇒ the integrator is losing validity. `regime.classify(M̂)` argmaxes
over four axes — **geometry, quantization, dynamics, representation** — and reports the label **plus its
margin**. The framework now monitors not just the state but *which of its own modelling assumptions is the
dominant error source*. It is **manifold-, metric-, and integrator-independent**, which is why it is the
part most likely to survive architectural generations.

**Invariants held.** `M̂`/regime are **pure telemetry** — classified and recorded, **never** switching the
integrator or any control (no observable gates the runtime; `E` stays the only inline gate). `M̂` is **not**
in `Hₜ` (it is a deterministic function of the already-hashed `(θ,Z,S,W)` — zero new entropy); `θ` **is**
in `Hₜ` (declared bundle, `protocol_version: aether-field/1`). Raw `M` is incommensurable (`E~1e16`,
`β~1e9`) — only the non-dimensionalized `M̂` is classifiable.

**Honest bounds (the Stage-D non-result, kept).**
- The **ghost measures geometric fidelity** (staying on Stiefel), **not** dynamical accuracy. Magnus-2 moves
  the ghost and the representation pressure in **opposite** directions — which is the *proof* that the two
  axes are **non-redundant**, not a defect.
- A clean Magnus-2 **accuracy** win is **not** demonstrated here: applied via the additive `(I+Ω)` map the
  payoff is regime-dependent (`+4%`, `−23%`, `+9%` vs a fine-`dt` reference). A true higher-order win needs
  an exact-orthogonal **Cayley/exp** application (a fixed-point matrix inverse) — a declared deferred
  sub-stage. What is solid is the *observability*: the brackets, `M̂`, and the regime classifier are
  deterministic and report integrator adequacy without ever acting on it. `integrity ≠ truth`.
- `Φ` (a predictive `M̂_{t+1}=Φ(M̂_t)`) is **not** assumed — `M̂(t)` is logged for later analysis; whether
  predictive structure exists is a question to be tested against the record, not built in.

## Stage E — spectral observability over the SPD cone (quantum-*style* diagnostics)

A fifth pressure axis — **state-distribution** — built from a density-like descriptor of the covariance,
NOT the frame:

```
substrate (decided by measurement):  ρ = P / tr(P)   on the SPD cone     (NOT WWᵀ — see below)
purity     P_pur = tr(ρ²) = Σ P_ij² / (Σ P_ii)²        polynomial → EXACT fixed-point
coherence  C     = ‖ρ − diag(ρ)‖_F = ‖offdiag P‖_F/tr P polynomial → EXACT fixed-point
mixedness  1 − P_pur                                    exact fixed-point
entropy    H     = −tr(ρ log ρ)                         eigen+log → FLOAT-only, DEFERRED (not wired)
M̂_E = (E/ε, ‖G‖/‖Z‖, B(t), β₁/‖A‖, β₂/(β₁+δ), β₃/(β₁+δ), 1−P_pur, C)   # TWO new axes (see split)
```

**Why SPD and not the Stiefel frame (measured).** `ρ = WWᵀ/tr(WWᵀ)` from an orthonormal frame is
degenerate: `WᵀW=I` pins `WWᵀ` to a projector with spectrum `{1/k}`, so **purity ≡ 1/k and entropy ≡
log k are constants** — manifold identities, not observables (verified: 0.5000 on every frame). The SPD
covariance carries the anisotropy the layer wants to see, so `ρ_P` is the substrate. (`regime.classify_E`
adds a `spectral-limited` fifth axis.)

**The axis was earned by measurement, not assumed (R1 gate 5).** Before claiming a new regime axis, the
correlation of the spectral series against the existing ones was run on a coupled SPD trajectory (skew
congruence rotates the basis → moves `C`; symmetric drift moves the spectrum → moves purity):

```
corr(C,E)=−0.045   corr(C,B)=0.000   corr(C,β)=−0.203
corr(purity,E)=−0.058  corr(purity,B)=0.000  corr(purity,β)=+0.173     max|corr| = 0.20  ⇒ SEPARATE
```

All `|corr| ≤ 0.2`: the spectral pressure is a **genuinely new observational dimension**, not a
re-coordinatization of `E/G/β`. It is the only family that sees the *internal distribution* of the state
rather than constraint violation or trajectory error — it answers not "is it stable?" but "*what kind* of
stability is it?".

**Two axes, not one (corrected by the analogy, then measured).** The quantum-info structure splits the
Stage-E observables: **purity and entropy are spectral/unitary invariants** (functions of `λ(P)` only —
unchanged under `P → U P Uᵀ`), while **coherence is basis-dependent** (varies under rotation at fixed
spectrum). Verified directly: rotating a fixed-spectrum covariance leaves purity invariant (to
quantization) while coherence swings widely. So `regime.classify_E` exposes **two** distinct axes —
`spectral-limited` = `mixedness` (the λ-invariant) and `coherence-limited` = `C` (basis-dependent, and
empirically the most `β`-coupled). Bundling them, as the first cut did, would have conflated "what is the
eigenvalue distribution" with "how mode-mixed is the working basis." (Response-2's cross-layer
`Ξ = β₁/(C+ε)` is provided as `coherence.cross_coupling` — logged telemetry, a defer-and-log hypothesis.)

**Invariants (hard-locked).** Purity and coherence are exact fixed-point **telemetry**, sitting beside
`E`, `G`, `β` — they **never** gate, **never** enter `Hₜ`, **never** steer `Z`. Entropy is float-only,
deferred to the same status as the SPD log-geodesic and the Cayley step (informative, never structural,
never a control primitive). The correlation hypotheses (does dynamical complexity manifest as spectral
dispersion?) are **logged for later analysis**, not built-in claims. `integrity ≠ truth`: a separating
correlation proves the axis carries independent information, not that it predicts any particular failure.

**Hardening — independent ≠ predictive (measured, and it failed for error, honestly).** Gate 5 proved the
spectral axes carry *independent* information. The stricter question — do they add *forecasting* power for
future error beyond `M̂`? — is the held-out incremental-R² gate (`predictive.py`), the empirical proxy for
`I(spectral ; future residual | existing M̂)`, with a **negative control** (a random feature bounds the
ΔR² any added column can buy) and a **positive control** (the gate must fire on a genuinely predictive
column). Measured, held-out (`H=4`):

```
target              R²_base   +spectral   ΔR²        verdict
future ghost ‖G‖    −0.009    −0.007      +0.002     descriptive   (≈ random control: NO forecasting gain)
future E_SPD        −0.009    −0.006      +0.003     descriptive
future mixedness    −78.4     +0.921      +79.4      predictive    (but = series PERSISTENCE, not error)
future coherence    +0.098    +0.878      +0.78      predictive
```

So for forecasting **error**, the spectral axes are a **descriptive lens, not a predictor** (ΔR² ≈ the
random control). They predict their *own* spectral future only by persistence — a different quantity than
error, which the error pressures are simply blind to. The honest verdict is recorded, not spun: Stage E
sees *what kind* of stable state you are in; it does **not** forecast when error will grow. `integrity ≠
truth` — a separating, even self-predicting, axis is still not a predictor of failure.

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
| `field.py` | **Stage D** generator field `A(W,t,θ)`, `magnus2_omega` (Bτ), `bracket_hierarchy` (β₁,β₂,β₃), `FIELD_PROTOCOL` |
| `regime.py` | **Stage D** meta-layer: `meta_vector` (M̂), `classify` (4-axis), `representation_pressure`; **Stage E** `extend_spectral`, `classify_E` (5-axis) — pure telemetry |
| `coherence.py` | **Stage E** spectral layer over SPD: exact `purity`, `coherence`, `mixedness`; float-deferred `entropy_float`; `correlations` (gate-5 independence); `cross_coupling` (Ξ) |
| `predictive.py` | **Stage-E hardening** held-out incremental predictive-value gate (`incremental_value`, OLS+ridge, negative+positive controls) — float offline analysis |
| `evolve.py` | `evolve_audited` (Stage B); `evolve_spd_audited` (Stage C, adaptive cadence); `evolve_field_audited` (Stage D, Magnus-2 field + meta-observability) |
| `demo_aether_physics.py` | exact gate (A) · 1-ulp truth (B) · 1,000,000-step spinning top (C) · ghostsnap (D) |
| `tests/test_aether_stiefel.py` | 11 unit tests (exact gate, audit, retraction, evolution, crucible stress) |
| `tests/test_aether_ghost.py` | 12 unit tests (ghost closure, fp EMA, observable purity, η_CLT null, structural identity) |
| `demo_aether_spd.py` | Stage C: exact gate · Π_SPD repair · adaptive cadence (calm vs strong drift) · pure ghost |
| `tests/test_aether_spd.py` | 10 unit tests (Cholesky, Sylvester gate, retraction, adaptive cadence, purity, anchor) |
| `demo_aether_field.py` | Stage D: field A(W,t,θ) · Magnus-2 · bracket hierarchy · regime classifier |
| `tests/test_aether_field.py` | 11 unit tests (θ-purity, bracket hierarchy, M̂, regime, θ-in-identity, channel separation) |
| `demo_aether_coherence.py` | Stage E: substrate (SPD vs Stiefel) · exact purity/coherence · correlation independence gate |
| `tests/test_aether_coherence.py` | 11 unit tests (substrate non-degeneracy, exact observables, entropy-deferred, separation, rotation-invariance, telemetry) |
| `demo_aether_predictive.py` | Stage-E hardening: held-out incremental predictive-value table + honest verdict |
| `tests/test_aether_predictive.py` | 4 unit tests (OLS recovers linear, negative+positive controls, error-target descriptive) |
