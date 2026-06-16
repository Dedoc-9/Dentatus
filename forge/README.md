# forge/ — the L1 production hardening layer

Additive, non-normative robustness tooling that treats the **frozen Dentatus core as a behavioral
oracle**. Nothing here edits `engine/`; `forge/` is an external guard + verification layer. Discipline of
record (Annex I): these tools certify **integrity** of a well-formed transition, never truth.

## Components
- **`clamps.py`** — fail-closed property clamps for the live L1 commit boundary. Pure predicates over
  declared operator outputs (`chi ∈ [0.05,1]`, Bethe envelope: `frac∈[0,1]`, `E*_eff≥0`, strain may only
  *narrow* the window, `dS_cit` finite, `survivable` is bool, hash-continuity/advancement). A breach
  raises `ClampViolation`; the boundary reverts to the last valid hash. Calibrated against 20k oracle
  outputs with zero false positives.
- **`nonce_proof.py`** — EXP-528 rolling nonce-chaining property proof: backward-compat (nonce=None == legacy),
  replay-reproducibility (EXP-520), replay immunity (stale frame rejected), forge resistance, fork sensitivity.
  All 5 PASS, 0 violations. The nonce is a deterministic hash-ratchet over the sealed-H sequence; the secret
  never enters it; replay immunity = nonce bound into `session_attest` + strictly-monotone accepted seq.
- **`chaos_harness.py`** — EXP-529 network sabotage engine. A deterministic L1 reducer (tick-batched NET
  superposition + seal + EXP-528 nonce) fed through a seeded chaos transport (drop-cascade 30%, jitter-reorder,
  latency-spike past the rebase window). Proves the committed `H_verified` timeline is a pure function of the
  accepted set + server seq — independent of arrival order. 5/5 PASS: arrival-order invariance, chaos
  determinism, bounded-rebase rejection (stale deterministic), drop resilience, liveness (no lock).
  Honest scope: bounded-window order-invariance + deterministic stale-rejection — NOT zero-latency re-proof.
- **`oracle_fuzz.py`** — differential / metamorphic fuzzer. Seeded-random well-formed inputs into the
  real operators, asserting: (1) clamps; (2) **metamorphic** relations needing no ground truth —
  `strain↑ ⇒ E*_eff↓`, `chi↑ ⇒ dS_cit↑` (EXP-514); (3) **determinism** — identical input ⇒ bit-identical
  output; seal supra-quantum **sensitivity** and sub-quantum **stability**. Mines observed invariant ranges.
  Deterministic (fixed seed). `python3 forge/oracle_fuzz.py [N]` — exit 0 ⟺ 0 violations.

## Campaign of record (N=20000, seed 9671566)
```
clamps + metamorphic invariants ......... 0 violations
seal determinism ........................ 400/400
seal supra-quantum sensitivity (1e-9) ... 400/400
seal sub-quantum stability (1e-18) ...... 400/400
mined: chi [0.050, 0.982]  dS_cit [-8.322, 20.721]  E*_eff [0, 29.788]  frac [0,1]
```
**First find:** the fuzzer pinned the `seal` canonicalisation floor at ≈1e-15 (full float significand) —
the EXP-602 bit-stability boundary. `H` is sensitive to any change above it and stable below
representability. This is now codified as two standing properties, not an assumption.

- **`invariant_synthesis.py`** + **`../constitution/INVARIANT_REGISTRY.json`** — EXP-530 propose/license
  pipeline (MCL_OBS2 separation of powers). Forge mines candidates (constitutional vs empirical basis);
  a human licenses exact fingerprints into the registry with a `failure_condition`; L1 `active_clamps()`
  enforces only licensed + fingerprint-intact + engine-matching entries. Empirical bounds: monitor-only.
  7/7 gate properties PASS. Mining proposes; the registry licenses; L1 enforces — nothing self-activates.

## Roadmap (grounded)
- **Rolling nonce-chaining** at L1: a per-commit nonce chained into `session_attest` so a valid signed
  frame cannot be replayed out of order. Additive, safe, next.
- **Network chaos injection**: drop / delay / reorder intents at the L1 enqueue boundary; assert the
  bounded-rebase window + determinism hold (replay stays bit-exact). Additive.
- **Automated invariant synthesis**: promote mined ranges (above) into candidate clamps under a
  registry precommitment (MCL_OBS2 discipline) before they become assertions — mining proposes, the
  registry licenses.
- **GPU / SIMD — quarantined, NOT on the committed path.** Bit-exact hashing is the foundation; GPU and
  wide-SIMD floating-point reassociation is platform-nondeterministic and would silently break
  `H_verified` cross-platform. SIMD/GPU may accelerate **rendering and client prediction only**; the L1
  truth-tick math stays scalar/ordered (or fixed-point) so the oracle remains bit-reproducible. This is a
  hard constraint, not a preference.
