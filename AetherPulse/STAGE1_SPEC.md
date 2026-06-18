# AetherPulse — Stage 1 Architecture Spec: the Deterministic Reference Kernel

> **Goal of Stage 1:** define the *exact deterministic semantics* of the engine's logic core, as a runnable
> reference, plus the **conformance contract** a fast native (Rust/C++ SIMD) port must satisfy. Speed is a
> *later* stage; Stage 1 is about getting the determinism unambiguous and testable first.

This Python kernel is **not** the performance engine. It is the **conformance oracle**: the slow, obviously-
correct reference whose state hashes the optimized engine must reproduce bit-for-bit. You cannot make a
deterministic engine fast until you have an unambiguous definition of "deterministic" — this is that
definition.

## 1. State representation (no floats, ever)

- Scalars are **fixed-point integers**: a real value `v` is stored as `round(v · S)`, `S = 2³²` in the
  reference (the native port may use a wider scale, e.g. `2⁴⁰`, as long as the conformance vectors are
  regenerated at that scale). Floats are **refused** at the API boundary (`kernel._fp` raises on a float).
- A **body** is an axis-aligned box: `{id, pos[3], vel[3], half[3], restitution}` — all fixed-point ints.
- A **world** is `{bodies, min[3], max[3], gravity, dt, tick}`.
- The **state hash** is `SHA256(canonical_bytes(world))` via the `stasis` Iron Canon (which itself rejects
  any float that leaks in). Identity *is* the state.

## 2. The tick pipeline (a fixed, total order)

`step(world)` is a pure function (returns a new world; the source is never mutated — see §4). It runs, in this
exact order, over bodies **sorted by id**:

1. **Integrate gravity:** `vel.y -= g·dt`.
2. **Integrate motion:** `pos += vel·dt`.
3. **Wall collisions:** clamp to `[min+half, max−half]` per axis; reflect that axis' velocity with integer
   restitution `vel.ax = −(e · vel.ax)`.
4. **Pairwise AABB resolution:** for each `i<j`, if the boxes overlap on all three axes, separate along the
   **least-penetrating axis** and **swap** that axis' velocities (equal-mass elastic). Deterministic pair
   order.

Every operation is `+ − · >> //` on integers — associative-stable and identical across architectures.

## 3. The conformance contract (how a native port proves itself)

A **conformance vector** binds `(initial world, tick count)` to the reference outputs:

```
vector = { init_hash, ticks, final_hash, merkle_root(per-tick hashes), world0, signature? }
```

A native engine is **AetherPulse-conformant** for that vector iff, starting from `world0`, it reproduces
`final_hash` *and* `merkle_root` exactly. `conformance.verify_vector` *is* that test, run against the
reference. The optimization workflow is therefore: change anything you like in the native engine, then run the
conformance suite — green means you preserved the semantics, red names the first diverging tick.

## 4. Determinism requirements (learned the hard way)

The reference itself shipped a **real determinism leak** that its own test caught: a shallow `dict(body)`
copy shared the `pos`/`vel` lists, so one run mutated the next and re-runs diverged. Fix: deep-copy the
vectors (`kernel._copy_body`). This is the canonical hazard for the native port too — *aliasing of mutable
state across ticks/threads is the determinism killer*, more than the arithmetic. The regression guard is
`test_source_bodies_not_mutated`.

Hard rules for any port:
- no float in any value that reaches a hash (the Iron Canon enforces this on the reference);
- a single, fixed truncation rule for fixed-point multiply (the reference truncates toward zero);
- a fixed iteration order (sorted ids, fixed pair order) — never hash-set/dict iteration order;
- no clock, RNG, or thread-scheduling input to the committed state (capture at the boundary if needed).

## 5. Roadmap — and an honest separation of *proven* vs *target*

| Stage | Proven now (reference) | Target (native, **unvalidated**) |
|---|---|---|
| 1 — Logic core | deterministic 3-D fixed-point rigid bodies; conformance vectors; cross-run identical hashes | Rust/C++ AVX-512 vectorized port; 1,000-player sim; "1M entities @ 240 TPS, <5 ms" is a **goal**, not a measured result |
| 2 — Hybrid render | the kernel emits exact `(pos, vel, hash)`; `stasis` canonicalizes the seam | GPU float *rendering* of integer *logic*; client prediction + snap-to-hash (this is `lockstep` rollback, already honest that it *reconciles*, not "no rubber-banding") |
| 3 — Proc-gen mesh | `crucible`/`syracuse` seeds → content-addressed chunks (see `VeriVerse`) | instant cached loads; `tessera`-keyed asset provenance |
| 4 — Multiplayer | `quorum` micro-elections; divergence localizes the cheater | "1,000+ players, no lag, perfect anti-cheat" → honest: *detectable/rejectable* cheating under the quorum Sybil bound; bandwidth deltas help but "90%" is unmeasured |
| 5 — Tooling | the conformance suite *is* the verified-asset gate | editor, WASM `fuel` build, browser Replay Court |

### The GPU-parallel verification idea (Stage 2+), honestly

Computing a Merkle root of the logical state in a **compute shader** to verify each frame on the GPU is a
sound idea and the right place to put the hashing cost. It is **not built or benchmarked here**; the claim
"verify 240 frames/sec" is a hypothesis for Stage 2, not a result. Stage 1 makes it *possible* by defining
exactly what bytes get hashed.

## 6. Honest bounds (the standing contract)

- Determinism + verification make exploits **detectable and rejectable** and runs **replayable** — they do
  **not** make game state "immutable," and they do **not** eliminate network lag (lag is the network; what
  the engine removes is *nondeterministic divergence* and *unverifiable* outcomes).
- Fixed-point is deterministic, **not** higher-fidelity than float — it is a *different* trade (provability
  over continuous precision).
- This is the **reference semantics**, not the 240fps engine; all performance figures above are **targets**
  to be measured on the native port, never asserted here.
- `integrity ≠ truth`: a conformance vector proves the sim ran exactly so, never that it models real physics
  or that a match outcome is "fair" beyond following the declared rules.

## First milestone (the "Hello World")

`demo_aetherpulse.py` already runs it: **two cubes collide head-on, resolve on an exact tick, and produce a
bit-for-bit identical hash across re-runs** — the reference of the "same pixel on Intel and ARM" goal. The
native Stage-1 task is to reproduce `conformance.make_vector(...)`'s `final_hash` from Rust. When that
matches, Stage 1 is done.
