# AetherPulse — a deterministic engine kernel (Stage 1 reference)

> The logic core for a 256-bit-deterministic game/sim engine. The renderer is fast and float; the **logic**
> is exact and integer — and the renderer only ever draws what the integer logic *decides* and the hash
> *verifies*.

This folder is **Stage 1**: the deterministic 3-D fixed-point rigid-body **reference kernel** and its
**conformance contract**. It is the slow, obviously-correct oracle a fast native (Rust/C++ SIMD) port must
reproduce bit-for-bit. See [`STAGE1_SPEC.md`](STAGE1_SPEC.md) for the full architecture spec and the honest
roadmap (proven now vs. targets for later stages).

## Run it

```
PYTHONHASHSEED=0 python3 demo_aetherpulse.py            # two cubes collide · determinism · gravity · conformance · stress
PYTHONHASHSEED=0 python3 tests/test_aetherpulse.py      # 11 unit tests
```

## What's real here

- A **deterministic 3-D fixed-point kernel** (`kernel.py`): boxes with integer position/velocity, gravity,
  wall + pairwise AABB collisions, integer restitution — pure integer, no float anywhere in the state hash.
- **Bit-for-bit determinism**: the same world yields identical per-tick hashes on any machine and re-run
  (the "same result on Intel and ARM" goal, in reference form). The kernel even caught and fixed its own
  determinism leak (a shared mutable vector), now guarded by a regression test.
- **Conformance vectors** (`conformance.py`): bind `(world, ticks)` to the exact `final_hash` + Merkle root a
  native port must reproduce — the optimization oracle. Optionally Ed25519-signed.

## What's a target, not a claim (read this)

The proposal's Stages 2–5 — Rust/AVX-512 vectorization, GPU compute-shader hashing, 1440p/240fps, 1M
entities, 1,000-player P2P, "90% bandwidth", "perfect anti-cheat" — are an **honest roadmap with unvalidated
targets**, not results. Nothing here is benchmarked at those numbers, and Python is the *reference*, not the
performance engine. The honest claims this kernel actually supports:

- determinism + verification make exploits **detectable/rejectable** and runs **replayable** — not state
  "immutable," not lag "eliminated";
- fixed-point is a **trade** (provability over continuous precision), not strictly "better" than float;
- `integrity ≠ truth`: a conformance vector proves the sim ran exactly so, never that it models real physics.

## Where it sits

Standalone product (Sibling Law): imports `aether` (fixed-point), `tessera`/`chronicle` (signed conformance
proofs), `stasis` (Iron Canon + Merkle) read-only. It is the engine-grade sibling to `VeriVerse` (verifiable
voxel worlds) and `aether` (fixed-point manifold geometry).

## The C++/Rust port discipline

The performance engine will be C++ (or Rust) — Python is too slow for 240fps, but it is the **reference /
source of truth**. The rule: **the native engine never defines semantics; it must reproduce the Python
reference's conformance hashes.** Workflow: write the logic in `kernel.py` → `export_vectors.py` emits JSON
fixtures → the native engine runs them → it is verified iff `final_hash` and `merkle_root` match. The
conformance suite is the **anti-UB guard**: a compiler optimization or pointer-aliasing bug that changes the
result fails the test. The native port lives in its own folder (e.g. `engine_cpp/`), **does not import the
Python workbench** (zero binary bloat), and depends on it only for the semantic definition (the fixtures).
See [`STAGE1_SPEC.md`](STAGE1_SPEC.md) §5b for the exact hashing format it must match.

## Files

| File | Role |
|---|---|
| `_cores.py` | Sibling-Law shim — imports `aether`/`tessera`/`stasis` read-only |
| `kernel.py` | the deterministic 3-D fixed-point rigid-body kernel + state hashing |
| `conformance.py` | conformance vectors (`make_vector` / `verify_vector`) — the native-port oracle |
| `demo_aetherpulse.py` | two cubes · determinism · gravity · conformance · stress |
| `export_vectors.py` | emits language-agnostic conformance fixtures (`fixtures/*.json`) for a C++/Rust harness |
| `fixtures/*.json` | conformance vectors: input world + expected `final_hash` / `merkle_root` |
| `tests/test_aetherpulse.py` | 12 unit tests |
| `STAGE1_SPEC.md` | the Stage-1 architecture spec + honest roadmap (proven vs. target) |
