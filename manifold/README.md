# manifold — a topology-gated engine on the Chronicle workbench

This component expresses computational state as a **graph embedded in a manifold** and makes the cryptographic
identity of the engine its **topology**. It is a sibling component of the workbench, built on the frozen [`chronicle`](../chronicle/README.md)
core — imported read-only, never modified. See the [workbench overview](../README.md).

## The honest split (the whole design)

| Layer | What | Where it runs |
|---|---|---|
| **Identity** | `world_H` = hash of the integer Laplacian / edge set — *topology is identity* | in the commit hash (deterministic) |
| **Diamond-hard gate** | EXACT graph predicates: union-find **connectivity**, **bridge** detection | the precommitted Chronicle invariant (exact, O(N+E), replay-safe) |
| **Spectral margin** | Fiedler value λ₂ (algebraic connectivity) via numpy | a **captured observable** — recorded for audit, **never** in `world_H` |

Why the split: a float eigensolver is **not** bit-reproducible across BLAS/LAPACK builds or architectures,
and the Fiedler eigenvector's sign is only defined up to ±1. Putting it in the commit path would fork
content addresses between machines and break the Replay Court. So the *gate* is exact integer topology;
the *spectrum* is a soft early-warning margin, captured (like any nondeterministic read) so replay stays
bit-perfect. "Would this transition fragment a critical subsystem?" is answered exactly — `λ₂ → 0` merely
corroborates it in the record.

## Run it

```bash
PYTHONHASHSEED=0 python3 demo_manifold.py        # record, gate-on-bisection, replay, tamper
PYTHONHASHSEED=0 python3 tests/test_manifold.py  # 9 tests
```

The demo: benign edits commit; removing the bridge `(2,3)` would split the graph into two triangles, so the
exact gate **refuses the commit** (captured `λ₂` collapses to 0); the Replay Court re-verifies the chain
**with no numpy on the replay path**; a tampered topology is caught as REPLAY drift.

## Files

| File | Role |
|---|---|
| `manifold_core.py` | `world_hash` (topology→identity), exact `is_connected`/`bridges` gate, `fiedler_value` (captured λ₂); imports frozen Chronicle read-only |
| `demo_manifold.py` | topology-gated commits + replay + tamper, wired into `chronicle.Recorder` |
| `tests/test_manifold.py` | topology, exact gate, captured λ₂, gated-ledger + replay/tamper |

## Honest scope (carried up from the workbench)

`λ₂ > 0` proves the **graph you built** is connected — not that the system is safe. The gate is only as
honest as the graph construction and the predicate; **integrity is not truth**. depends on the frozen
`chronicle` core (sibling folder); numpy is used **only** for the
captured spectral margin, never in the commit/replay path. The signer here is `HmacSigner` for the demo —
swap in `Ed25519Signer` or `chronicle/hardware_signing.HardwareSigner` (Tier 1/2) unchanged for
third-party / hardware-sealed tickets.
