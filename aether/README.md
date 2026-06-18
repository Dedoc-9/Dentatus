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
PYTHONHASHSEED=0 python3 tests/test_aether_stiefel.py  # 11 unit tests
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
| `evolve.py` | `is_skew_symmetric`, `lie_bracket`, `lie_step`, `evolve_raw`, `evolve_audited` |
| `demo_aether_physics.py` | exact gate (A) · 1-ulp truth (B) · 1,000,000-step spinning top (C) · ghostsnap (D) |
| `tests/test_aether_stiefel.py` | 11 unit tests (exact gate, audit, retraction, evolution, crucible stress) |
