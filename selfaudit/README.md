# selfaudit — the workbench evaluates the workbench

The reflexive capstone: it turns the workbench's **own** components on the cores. `chronicle`
content-addressing fingerprints the repo, `assay` grades the checks as recomputable metric assessments,
the parity primitives prove lossless extraction, and `dini` maps the component DAG — and the whole verdict
is sealed into a signed assay ledger that the assay court replays.

## Run it

```bash
PYTHONHASHSEED=0 python3 evaluate.py        # run the workbench against itself
PYTHONHASHSEED=0 python3 tests/test_selfaudit.py
```

It prints a `workbench_H` (a single content address for the whole tree), runs four checks, seals them,
replays them through the assay court, shows the `dini` structural map, and emits the core fingerprint
baseline.

## What it checks (all mechanical, all sealed)

| Check | Proves |
|---|---|
| `core_determinism` | canonicalization + content hashing are stable across recomputation |
| `extraction_parity` | the coupled (imported) and uncoupled (vendored) primitives are byte-identical |
| `frozen_cores_unchanged` | every frozen-core file matches the pinned `core_baseline.json` — drift **fails** the audit |
| `sibling_law_no_core_copies` | no sibling carries a frozen-core copy under **any** filename (content-hash check, no allow-list) |

Plus a **drift-caught demonstration**: the audit forges a baseline entry and confirms the detector flags
it — proving the detector actually detects, not just that the happy path is green.

Each grade is recorded as an `assay` metric assessment bound to `workbench_H`, signed (Ed25519 if
available), and the assay court **recomputes the grade and verifies the signature** — so the self-audit is
itself tamper-evident and replayable. Re-running later detects drift against the sealed baseline.

## The honest bound (integrity ≠ truth, pointed inward)

A self-audit can prove only **mechanical** facts about itself — that its checks are reproducible, that the
cores are byte-stable, that parity holds, that the structure obeys the Sibling Law. It **cannot** certify
the workbench is correct, useful, or good. *A system grading itself is not an unbiased judge of its own
value.* This is a signed, replayable baseline and a drift detector — not self-endorsement.

## Files

| File | Role |
|---|---|
| `evaluate.py` | runs the reflexive checks, seals them via `assay`, maps structure via `dini`, emits `workbench_H` |
| `tests/test_selfaudit.py` | pure drift/copy detectors, live checks, drift-is-caught, sealed self-audit replays |
| `core_baseline.json` | pinned SHA-256 baseline of the frozen-core files; drift against it fails the audit |
