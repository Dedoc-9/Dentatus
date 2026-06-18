# conformance_suite — the cross-application regression harness

The workbench preflight (`integration/preflight_check.py`) gates the **26 sibling suites**. This harness gates
the layer *downstream* of them: the **five standalone applications**' content-addressed conformance hashes. It
protects the thing everything else is downstream of — if a change to a frozen core, a sibling, or the
canonical hashing format silently alters an application's output, this catches it and **names the exact app**.

```
PYTHONHASHSEED=0 python3 run.py             # verify — exit 0 if every app matches the pinned baseline, 1 on drift
PYTHONHASHSEED=0 python3 run.py --update     # re-pin the baseline (a deliberate, noted act)
PYTHONHASHSEED=0 python3 tests/test_regression.py   # 4 tests (clean probe, baseline match, drift detected, determinism)
```

## How it works

Each application is probed in an **isolated subprocess** under `PYTHONHASHSEED=0` — they reuse module names
(`conformance`, `kernel`, `world`, `runner`) that would collide in one interpreter, so per-app subprocesses
are the only honest way to run them together (the same pattern the workbench preflight uses for suites). Each
probe regenerates the app's deterministic golden artifact and prints a single `golden` hash:

| App | golden artifact |
|---|---|
| `AetherPulse` | hash over its 3 conformance fixtures (`final_hash` + `merkle_root`) |
| `AetherManifold` | hash over its 4 edge-case trajectory fixtures |
| `VeriSim` | a `brake_1d` Shard's `tessera` path-hash + Merkle root |
| `VeriVerse` | the `world_root` for seed 98247 + a chunk hash |
| `aegis_gate` | the decision verdicts + the committed-hash ledger chain |

`runner.compare` diffs the goldens against `conformance_baseline.json` and returns the exact faulting app and
reason (`DRIFT` / `ERROR` / `UNPINNED` / `MISSING`).

## Honest bound

This detects **drift** — any change that alters a downstream conformance hash — **not correctness**. A drift
may be a *deliberate* improvement, in which case you re-pin the baseline on purpose (`run.py --update`), the
same way a `ruleset_hash` version bump is a noted, intentional act. Drift you did **not** intend is the bug
this exists to surface. (`integrity ≠ truth`: a stable baseline proves the applications still reproduce their
pinned outputs, not that those outputs are *right*.)

## The baseline is pinned to an environment, not just to code

A conformance hash captures *every* deterministic input the run touched — including which signing tier was
available. The `aegis_gate` golden was pinned with **`cryptography` installed**, so its supervisor token is
**Ed25519**. On bare stdlib the token falls back to **HMAC**, the committed-hash chain changes, and the golden
drifts — verified, not assumed: Ed25519 → `10b8188…`, HMAC → `dfa2b00…`. That is a *false* red (the logic is
unchanged; only the environment differs).

The honest fix is to pin the environment alongside the code: the CI gate (`.github/workflows/verify.yml`)
installs `cryptography` so it reproduces the tier the baseline was pinned under. If you ever re-pin on bare
stdlib **on purpose**, that is a deliberate `--update` and a noted tier change — same discipline as a
`ruleset_hash` bump. Determinism is reproducible *given the same declared environment*, never in a vacuum.

## Files

| File | Role |
|---|---|
| `runner.py` | per-app subprocess probes; `collect` / `compare` / `write_baseline` |
| `run.py` | CLI — verify (default) or `--update` the baseline |
| `conformance_baseline.json` | the pinned golden hash per application |
| `tests/test_regression.py` | 4 tests (probe cleanly, match baseline, detect drift, determinism) |
