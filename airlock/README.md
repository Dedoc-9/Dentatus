# airlock — the LLM→kernel membrane (transitions-only)

The LLM is a **proposer**; the kernel is the **authority**; this is the **membrane** between them. It is the
seam that turns the workbench from a sophisticated simulator into a *governed creative workspace*: humans and
LLMs explore freely above the membrane, while reality below it changes only through **auditable, reproducible,
bounded** operations.

Two architectural laws, enforced **structurally** (not by convention):

```
telemetry ≠ control     observables (R_p, aether metrics) are computed but NEVER read by any gate
intent    ≠ authority    claims / provenance never commit state; only mechanical, bounded checks do
```

## The pipeline (one-way; reject at any gate → evidence, never mutation)

```
p = { transition, claims, constraints, provenance, budget }
  → CANON       stasis Iron Canon: no floats/sets/non-str keys; well-formed schema      ─reject→ shard
  → SCHEMA      transition.op ∈ ALLOWED_OPS                                              ─reject→ shard
  → BUDGET      fuel: cost ≤ max_cost                                                    ─reject→ shard
  → SHADOW      world' = adapter.apply(world, txn)   [PURE — no write-back]              ─reject→ shard (APPLY)
                ‖Δ‖ ≤ max_delta                                                          ─reject→ shard (BUDGET)
  → VALIDATE    adapter.validate(world', constraints)  (mechanical admissibility)        ─reject→ shard
  → [telemetry] R_p = ‖Δ_proposed − Δ_real‖ + claim mismatches   (computed; gates NOTHING)
  → WITNESS     ≥k independent re-derivations reproduce hash(world')                     ─diverge→ shard
  → COMMIT      world_{t+1} = world'  +  hash-chained, optionally-signed commit shard
```

`R_p` is the **proposal residual — the LLM's "ghost"**: the part of the proposal the deterministic kernel
could not honor, measured with the same discipline as `aether`'s ghost, and (like it) **observable-only**.

## Transitions, not goals

The kernel admits only a small set of **declared, bounded** transitions — never free-form code or goals:

| op | meaning | budgeted by |
|---|---|---|
| `spawn` | add a box body | body count / `‖Δ‖` |
| `impulse` | add a velocity delta to a body | `‖dv‖` |
| `advance` | step the kernel `n` ticks | tick count |

A **goal** (`"make it bounce forever"`) is *not* a transition — it is rejected at the schema. Goal-direction
lives **outside** the membrane as untrusted planning that must *decompose to transitions* before entering
(see `demo_airlock.py`). Mechanism in the core; normativity at the edge.

## Run it

```
PYTHONHASHSEED=0 python3 demo_airlock.py            # a goal decomposed → commits + rejections + telemetry
PYTHONHASHSEED=0 python3 tests/test_airlock.py      # 15 unit tests (both laws, gates, witness, determinism)
```

## Honest bounds

- A commit proves the transition was **applied exactly and admissibly** — never that it was a *good* idea.
  `integrity ≠ truth`.
- Rejections become **immutable, auditable evidence** (an append-only ledger), not training signal: the kernel
  stays **memoryless** w.r.t. rejections; any learning is offline, never inline (telemetry ≠ control).
- Witness is **reproduction-admission** (≥k independently re-derive the same candidate hash), *not* a vote on
  merit — witnesses confirm determinism, they do not vote reality into existence.
- The membrane is **kernel-agnostic**; the AetherPulse adapter is one world. Reference seam, not a shipping
  engine.

## Files

| File | Role |
|---|---|
| `_wb.py` | read-only workbench shim (`chronicle`, `stasis`) — Sibling Law |
| `membrane.py` | the kernel-agnostic pipeline: `propose`, `Ledger`, commit/rejection shards, the two laws |
| `adapters.py` | the AetherPulse world adapter — typed ops (`spawn`/`impulse`/`advance`), `R_p`, validate |
| `demo_airlock.py` | a goal decomposed → membrane → commits/rejections/telemetry |
| `tests/test_airlock.py` | 15 unit tests |
