# ration — deterministic resource clamps (complexity-bound accounting)

A Sibling-Law component: it imports the frozen [`chronicle`](../chronicle/README.md) core read-only and
gates resource usage on **exact integer logical steps**, not wall-clock or bytes — so budget enforcement
is bit-identical on any machine.

## Why

OS cgroups and timeouts key off the system clock and physical hardware, so the same path fails on a slow
box and passes on a fast one — breaking hardware-invariant determinism. `ration` divorces the limit from
physics: it counts *logical steps* (loop iterations, tokens, state mutations, graph nodes) as strict
integers and enforces a pinned ceiling fail-closed. An audit on a decade-old laptop resolves the exact
same budget-exhaustion point as an enterprise array.

## The exact / observable split

| Layer | What | Where |
|---|---|---|
| **Gate** | integer logical-step counts vs a precommitted ceiling (`within_budget`) | the recorder's fail-closed invariant — exact, replay-safe |
| **Observable** | physical cost (CPU ms, memory delta, billing) captured at the boundary | a captured value, **never** gated, **never** in the commit hash |

## Run it

```bash
PYTHONHASHSEED=0 python3 demo_ration.py        # within budget / quota breach / hardware-invariant / replay
PYTHONHASHSEED=0 python3 tests/test_ration.py  # 9 tests
```

The demo seals a within-budget run, refuses a runaway loop fail-closed (`QuotaBreached`), shows the same
logical run resolves the identical gate outcome on a "fast" vs "slow" machine (different captured CPU ms,
identical step counts), and the Replay Court reproduces it bit-for-bit.

## Honest bound

This stops a loop from running away *logically* and makes budget enforcement bit-identical across machines.
It does **not** prevent an OS OOM-kill if the ceiling is set too loose, and it does not measure real
wall-clock cost — that's the captured observable, not the gate. Integrity is not truth.

## Files

| File | Role |
|---|---|
| `meter.py` | `StepMeter`, `step_total`, `within_budget` (integer logical-step accounting + pure gate) |
| `demo_ration.py` | within-budget / quota-breach / hardware-invariant / replay |
| `tests/test_ration.py` | metering, budget gate, hardware-invariance, seal + tamper |
