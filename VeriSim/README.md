# VeriSim — the verifiable simulation engine

> **We prove the test was real, not that it predicts the future.**
> *If you can't replay it, it didn't happen.*

VeriSim runs a deterministic simulation inside the Dentatus/Chronicle workbench's integer engine and emits a
**Shard**: a content-addressed, offline-replayable record that *this scenario* was run, with *these inputs*,
under *these exact rules*, producing *this exact* final state and step history. A stranger downloads the
Shard, replays the integer math on their own machine, and confirms it bit-for-bit — no drift, no hidden
RNGs, no "model luck."

## The honest differentiator (read this first)

Most simulators try to prove their *predictions* are right. VeriSim admits it cannot do that. A Shard proves
the **simulation was real and replayable** — it does **not** prove:

- that the model matches reality,
- that the model is *correct*,
- or that any real-world system is *safe*.

`integrity ≠ truth`, applied to simulation: **a verifiable simulation is not a verified reality.** The toy
scenarios here (1-D braking, 1-D projectile) are illustrative kinematic models — *not* validated vehicle,
medical, or financial models. A clean replay says the *test* was honest, nothing about the *world*.

## Run it

```
PYTHONHASHSEED=0 python3 demo_verisim.py            # run · replay court · tamper/drift · spot-check · bounded
PYTHONHASHSEED=0 python3 tests/test_verisim.py      # 12 unit tests
```

## How it works — and which workbench sibling does what

VeriSim is a **standalone** project that imports the workbench siblings **read-only** (the Sibling Law):
`_cores.py` puts their directories on the path and never edits or vendors them.

| step | sibling | role |
|---|---|---|
| run the physics | `aether` (`fixedpoint`) | fixed-point integer state — bit-exact, replayable, no float drift |
| bound the run | `fuel` discipline | a step budget halts a runaway; nothing hangs |
| prove the path | `tessera` | the run mints an offline-replayable proof shard (signed authorship) |
| canonicalize + classify | `stasis` | Iron Canon rejects float pollution; Divergence Ledger splits a *logic change* from benign *observable drift*; Merkle root enables O(log n) per-step spot-checks |
| stress it | `crucible` | adversarial parameter seeds push runs to the budget edge (the "find the drift" challenge) |

A **Shard** is `{scenario, ruleset_hash, input_data_hash, steps, final_state, merkle_root, tessera}`. The
**Replay Court** (`court.replay`) re-runs the scenario under the same source-hashed rules and recomputes both
the `tessera` path hash and the `stasis` Merkle root — so neither the path nor the per-step history can be
faked. `classify_final` separates a real `LOGIC_ERROR` (a gated field changed → FAIL) from benign
`OBSERVABLE_DRIFT` (only non-gated fields differ → WARN). `spot_check_step` proves a single step is in the
run with an O(log n) Merkle proof.

## What it gives, and what it does not

**Gives:** trustless, offline, bit-for-bit verification that a declared simulation was actually run — drift
vs logic-change classification, per-step spot-checks, signed authorship, and a fuel-bounded guarantee it
terminates. The trail is verifiable by anyone holding only the public key.

**Does not:** validate the model against reality, certify physical/financial/medical safety, predict an
outcome, or make the result *true*. Those are out of scope by construction, not by omission.

## Roadmap (honest framing)

1. **Toy validator (this MVP):** deterministic kinematic scenarios → Shards → local Replay Court.
2. **Model-agnostic harness:** plug any deterministic integer/fixed-point model in as a scenario; the proof
   machinery is unchanged.
3. **Browser Replay Court:** a WebAssembly port of the integer engine so a Shard verifies in-page. *(Not yet
   built — the current court is a local Python re-run.)*

The framing stays the same at every phase: VeriSim makes a simulation's **process** auditable and replayable.
Whether the model is *right* remains the modeller's claim to defend — VeriSim just makes sure they can't fake
having run it.

## Files

| File | Role |
|---|---|
| `_cores.py` | Sibling-Law shim — imports `aether`/`tessera`/`stasis`/`fuel`/`crucible` read-only |
| `scenarios.py` | deterministic fixed-point toy scenarios (`brake_1d`, `projectile_1d`) + registry |
| `runner.py` | `run_simulation` → a `Shard` (tessera proof + stasis Merkle root) |
| `court.py` | the Replay Court — `replay`, `classify_final` (drift), `spot_check_step` |
| `demo_verisim.py` | run · replay · tamper/drift · spot-check · bounded |
| `tests/test_verisim.py` | 12 unit tests |
