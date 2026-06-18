# AetherManifold — the Manifold-Stable protocol (deterministic Riemannian optimization)

Riemannian gradient descent on the **Stiefel manifold** `St(n,k) = {X ∈ ℝⁿˣᵏ : XᵀX = Iₖ}`, executed entirely
in `aether`'s **fixed-point integers** so the optimization *trajectory* is bit-for-bit reproducible and
attestable. It turns `aether`'s Stiefel auditor into a usable optimizer for high-stakes simulation, robotics
path-planning, or generative-AI latent-space navigation — anywhere you need a result you can *prove* was
computed exactly, not a float artifact.

## The classical problem, solved in integers

On a curved manifold you cannot subtract tangent vectors in different tangent spaces, and naive linear
updates "leak" off the manifold (a frame loses orthonormality). The fix, done with no float anywhere:

```
tangent projection:  P_X(Z) = Z − X·sym(XᵀZ),   sym(A) = (A + Aᵀ)/2     # keep the step in T_X St
retraction:          X ← GramSchmidt_int(X − η·P_X(G))                   # re-anchor onto the manifold
```

Every matmul/transpose/symmetrize is the same fixed-point integer op, so the same seed + learning rate +
steps reaches the **identical** minimum on any machine, and the path is a replayable shard.

## Run it

```
PYTHONHASHSEED=0 python3 demo_manifold_stable.py            # converge · deterministic · two-tier · stability · conformance
PYTHONHASHSEED=0 python3 tests/test_manifold_stable.py      # 10 unit tests
```

The demo fits `X` to a target frame on `St(3,2)`: energy `2.0e-2 → 4.3e-19`, `X → [[0.6,0],[0.8,0],[0,1]]`
(the exact 3-4-5 frame), orthonormality held to ≤ 3 ulp, trajectory bit-for-bit reproducible.

## What's genuinely more advanced here

- **Two-tier manifold protocol.** For manifolds with *rational* points (rational orthogonal frames,
  signed-permutation groups, integer lattices) you stay **exactly** on the manifold with **zero epsilon**
  (`is_orthonormal_exact`). Only when no rational parametrization exists do you fall back to
  fixed-point-with-a-*declared* integer tolerance (held by retraction). Exact when you can; bounded when you
  must — never a hidden float epsilon.
- **Shadowing-distance Lyapunov.** Run the optimizer from `X0` and from a **1-ulp** perturbation; the exact
  integer distance between the two trajectories is the discrete sensitivity, and its mean log-growth is a
  Lyapunov *observable* (> 0 sensitive, ≤ 0 contracting). Because both runs are integer-deterministic, this
  isolates *algorithmic* sensitivity from hardware noise completely. It is a sensor, never a gate.
- **Isolating algorithm from hardware.** Traditional papers blame instability on "floating-point precision."
  Running in fixed-point removes *nondeterministic* drift, so any instability you see is **reproducible and
  attributable** to the algorithm + a *known, fixed* quantization — not random hardware noise. (Note: this is
  determinism, **not** infinite precision.)

## Conformance (the native-port oracle)

`conformance.py` binds an edge-case problem `(A, B, X0, η, steps)` to the reference's `final_hash` +
`merkle_root` over per-step hashes; `export_fixtures()` writes `fixtures/*.json`. A native (C++/Rust int128)
port is conformant iff it reproduces both. Edge cases: `converge`, `near_singular` (nearly-parallel start
columns — retraction must recover), `zero_gradient` (start at the minimum), `aggressive_eta` (large step).

## Honest boundary statement

> This system provides **deterministic verification of manifold optimization**. It proves that a specific
> trajectory was computed exactly according to the defined rules, and is reproducible on any machine. It does
> **not** guarantee the found minimum is the *global* optimum, nor does it prove the physical stability of the
> modelled system *outside* the simulation bounds. **Stability is an observable property of the trace, not a
> derived truth.** A bounded trajectory over N steps is computational *evidence* within those bounds, not a
> universal proof. `integrity ≠ truth`.

## Files

| File | Role |
|---|---|
| `_cores.py` | Sibling-Law shim — imports `aether`/`stasis`/`tessera`/`crucible` read-only |
| `riemann.py` | tangent projection `P_X`, integer retraction, `optimize` (Riemannian GD), `ortho_defect` |
| `objective.py` | sample objectives with exact integer gradients (`procrustes`) |
| `stability.py` | shadowing-distance co-run + Lyapunov estimate (observable) |
| `conformance.py` | edge-case trajectory vectors + `fixtures/*.json` export (native-port oracle) |
| `demo_manifold_stable.py` | converge · deterministic · two-tier · stability · conformance |
| `tests/test_manifold_stable.py` | 10 unit tests |
