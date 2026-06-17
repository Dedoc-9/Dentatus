# stride — epistemic state-transport across a machine boundary

A Sibling-Law component: it imports the frozen [`chronicle`](../chronicle/README.md) core read-only and
migrates a deterministic state machine to another host *without* the environment-drift leaks of raw
snapshots/RPC.

## The exact / observable split

| Layer | What | Where |
|---|---|---|
| **Gate** | the receiver's **environment fingerprint** (an opaque content hash — e.g. `selfaudit`'s frozen-core hashes / `workbench_H`) must **exactly** match the sender's, or `EnvironmentMismatch` refuses the inbound path | fail-closed, before any state is accepted |
| **Observable** | raw network telemetry (latency, jitter, dropped frames, hop count) canonicalized and captured | a captured value, **never** gated, **never** in the commit hash |

The fingerprint is an **opaque string the caller supplies**, so `stride` stays decoupled from any
particular baseline source.

## Run it

```bash
PYTHONHASHSEED=0 python3 demo_stride.py        # migrate / env-mismatch / capture+seal / replay
PYTHONHASHSEED=0 python3 tests/test_stride.py  # 6 tests
```

A matching-environment receiver accepts and continues; a receiver that drifted a single core hash refuses
fail-closed; the volatile network telemetry is captured and sealed; and the Replay Court reproduces the
migrated transition bit-for-bit **without reopening a socket** (it reads telemetry from the record).

## Honest bound

This proves the two environments were **structurally identical** at transport time and that the network
inputs were recorded exactly. It is **not** transport security — wrap TLS externally; it does not encrypt
in transit; and it cannot prove the remote hardware is physically honest. Integrity is not truth.

## Files

| File | Role |
|---|---|
| `transport.py` | `pack` / `receive` (env-match gate, `EnvironmentMismatch`), `capture_link_telemetry` |
| `demo_stride.py` | migrate / mismatch / capture+seal / replay |
| `tests/test_stride.py` | roundtrip, env-mismatch, determinism, sealed migration + tamper |
