# fuel — the Absolute Integer Standard (bounded execution, exact halting)

`fuel` is a deterministic, integer-only bounded-execution engine. No float ever touches a value or a
halting decision. Execution is a pure integer register machine; every instruction costs integer **fuel**;
when the remaining fuel is less than the next instruction's cost the machine **halts fail-closed at the last
completed step**. Halting is therefore not an estimate ("approximately finished") — it is exact integer
arithmetic, identical on every machine. It is the third child of the Axiom build order, after `tessera`
(the witness) — and a fuel run *mints a tessera shard*, so a stranger can replay the whole execution offline.

## Run it

```
PYTHONHASHSEED=0 python3 demo_fuel.py             # exact execution · fail-closed · determinism · crucible · proof
PYTHONHASHSEED=0 python3 tests/test_fuel.py       # 12 unit tests
```

## The engine

A small integer op-set with **weighted integer costs** (no float "gas estimation"):

```
set/add/sub  cost 1     mul/div/mod  cost 2     jz/jnz/jmp/halt  cost 1
```

`vm_step(state)` executes one instruction as a pure function (new state, never mutates). It fails closed on
**out of fuel** (`fuel < next cost` → halt at the last completed step), **division by zero**, a **bad jump**,
or an **unknown op**. `run(program, init_regs, fuel_limit)` executes to halt and reports the exact
`steps`, `fuel_used`, `fuel_left`, and final registers. Because every op costs ≥ 1 fuel, a run **always
terminates** — even `[["jmp", 0]]` (an infinite loop) halts cleanly as *out of fuel*.

The flagship program computes a number's compressed-Syracuse stopping time entirely in integers, so feeding
it a `crucible` hard seed exercises the engine on the most chaotic deterministic workload available — and
the result is exact: `n=27 → s=70` matching `syracuse`, `fuel_used=868`, byte-identical across runs.

## Proof — a run emits a `tessera` shard

`vm_step` / `vm_done` are written as a `tessera` rule, and the program rides inside the seed state (so it is
content-addressed). `fuel.prove(program, init, fuel_limit, signer)` therefore mints a real `tessera` shard;
`fuel.verify_proof(shard)` re-runs the same VM step from the same seed and confirms the program ran exactly
these steps, used exactly this fuel, and halted exactly here — trusting no executor. Tampering with the
claimed steps, the program, or the inputs is caught precisely.

## The triangle, completed and fired

`syracuse` (the law) → `crucible` (reverse-generates a hard seed) → `fuel` (executes it to an exact halt) →
`tessera` (proves the run offline). The demo runs that whole chain end to end on `n=7615` (altitude 32×).

## Honest bounds (do not oversell)

- This is a **small** deterministic VM with a fixed integer op-set — **not** a production smart-contract VM,
  not Turing-complete-with-guarantees beyond what is implemented. "No float drift" is real and total *within
  this engine*; it does **not** by itself create distributed consensus (compose with `quorum` for that).
- **Exact fuel is exact accounting of this op-set's costs** — it bounds *logical* work, not wall-clock or
  RAM. An OS can still OOM; that is `ration`'s honest bound too.
- **integrity ≠ truth:** a proof shows the program ran exactly these steps, never that the program is
  correct, safe, or meaningful.

## Files

| File | Role |
|---|---|
| `vm.py` | the integer register machine; `vm_step` / `vm_done` (tessera rule), weighted fuel, fail-closed halts, `run` |
| `programs.py` | label-resolving `assemble`; `syracuse_program`, `sum_to_program` |
| `proof.py` | `prove` / `verify_proof` — a fuel run as a replayable `tessera` shard |
| `demo_fuel.py` | exact execution (A) · fail-closed (B) · determinism (C) · crucible hammer (D) · proof (E) |
| `tests/test_fuel.py` | 12 unit tests (engine, fail-closed, determinism, crucible, proof) |
