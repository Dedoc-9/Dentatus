# glitch — deterministic state-space explorer (stateful property fuzzer)

A Sibling-Law component: it imports the frozen [`chronicle`](../chronicle/README.md) core read-only and
hunts for *latent, sequence-dependent* invariant violations — the bugs that no single input reveals.

## What it actually is (honest framing)

It explores interleavings / contradictory inputs over a state machine with breadth-first search, **dedups
states by content hash** (`chronicle.state_hash`) so identical states reached by different paths are
explored once, **shrinks** any violating run to a minimal counterexample, and **seals** it into a signed
ledger that replays bit-for-bit in the Replay Court. The efficiency is real and specific: cost is bounded
by the number of *distinct states*, not the number of paths — which is exactly where many "timelines"
converge.

**What it is NOT** (the pitch that inspired it oversold these — dropped on purpose): not "quantum" or
"super-position"; not "millions of timelines in a single CPU pass" (each distinct state is evaluated once);
not a bytecode injector into the core (it drives the core's *public API* only — the Sibling Law); not
thread-free parallelism via `memoryview`. It is deterministic, single-threaded, and stdlib-only.

It is a **bounded model-check**: it finds counterexamples up to `max_depth`. Finding none at depth k is
**not** a proof of absence — integrity ≠ truth, applied to testing.

## Run it

```bash
PYTHONHASHSEED=0 python3 demo_glitch.py        # find / shrink / seal / replay a latent stacking-discount bug
PYTHONHASHSEED=0 python3 tests/test_glitch.py  # 8 tests
```

The demo's system-under-test has a realistic latent bug — discounts stack *additively*, so two 60%-off
events sum to 120% and yield a negative price. `glitch` finds the minimal trigger
`[discount, discount, purchase] → -200¢`, seals the valid prefix (the `purchase` step is refused
fail-closed), the court reproduces it, and the *fixed* system shows no counterexample within depth 4.

## Files

| File | Role |
|---|---|
| `explorer.py` | `explore` (BFS + content-hash dedup), `shrink` (delta-debug to minimal), `seal_counterexample` (signed, replayable ledger) |
| `demo_glitch.py` | a latent stacking-discount bug found, shrunk, sealed, replayed |
| `tests/test_glitch.py` | exploration, determinism, dedup, shrink minimality, seal + replay |

## Why it fits the workbench

It resurrects Dentatus's content-addressed DAG idea *for testing*: states are nodes keyed by hash, so the
search graph is a DAG and convergent interleavings collapse automatically. Any bug it finds comes with a
minimal, signed, bit-for-bit-replayable counterexample — drop the sealed ledger into the Replay Court and
the failure reproduces exactly. Determinism (the capture seam) is what makes the counterexample stable.
