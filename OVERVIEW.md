# Dentatus — an honest technical overview

> **Repo layout note.** The active, recommended artifact is [`chronicle/`](chronicle/README.md) — a
> small, dependency-light verifiable decision recorder distilled from this project. The full legacy
> Reality Engine / Citadel implementation described below now lives under [`docs/archive/`](docs/archive/);
> run its proofs from there (`cd docs/archive` first). The separately-connected game client remains in `Game1/`.

*Plain-English entry point for a technical reader. The `README.md` and `constitution/` are written in an
in-world vocabulary ("Reality Engine," "Citadel," "manifold," "physical law"); this document is the
de-inflated translation. Where the in-world docs and this one disagree on what the system actually
**is**, believe this one.*

---

## What it actually is

Dentatus is a **deterministic, content-addressed state machine with a cryptographic audit trail and a
discipline for proving invariants about itself.** Concretely:

- Every state is identified by a hash of its full contents (`H_t = SHA256(state ⊕ protocol)`), so the
  identity *is* the state — you cannot change the data without changing the address.
- State evolves through a fixed, stateless operator pipeline; every committed transition is recorded in
  an **event-sourced command log** and can be **replayed and re-verified bit-for-bit** from that log
  plus periodic checkpoints. Tampering with the log is detected (the re-derived hash won't match).
- Commits are **attested** (HMAC under a server-held secret) and **replay-protected** (a deterministic
  rolling nonce chain), and the governance config that controls runtime invariants is **Ed25519-signed**.
- A separate test layer (`forge/`) **fuzzes the frozen core, asserts metamorphic/property invariants,
  injects network chaos, and gates new invariants through a propose → human-license → enforce pipeline.**

Stripped of the game and physics metaphor, that is the whole thing. The novel-sounding parts
("thermodynamic firewall," spectral graph "physics") are **one decorative application** of generic
validity predicates; they are not the core value and probably don't transfer.

## What is genuinely solid (and reproducible)

Each of these is a runnable proof, not a claim. From the repo root, under `PYTHONHASHSEED=0`:

| Property | Evidence |
|---|---|
| Frozen core, clean-room layered (game/ never imports engine/*) | `engine/` def-counts `37/83/13/29`; `forge/*` have 0 engine imports |
| Differential fuzzing of real operators, 20k cases, 0 violations; pinned the hash canonicalization floor at ~1e-15 | `forge/oracle_fuzz.py` |
| **Hardware-invariant determinism** — same inputs + random wall-clock sleeps → bit-identical hash chain | `forge/duel_determinism_proof.py` |
| Replay immunity — rolling nonce; stale frame rejected; backward-compatible | `forge/nonce_proof.py` |
| Arrival-order invariance under 30% drop / jitter / latency | `forge/chaos_harness.py` |
| Invariant licensing with precommitment + Ed25519 signing; tamper/forge/unauthorized-key fail closed | `forge/invariant_synthesis.py`, `forge/signature_proof.py` |
| Verified replay / "time-travel" reconstruction of any prior state | `game/agency/replay.py` |

## The part that's actually worth showing: engineering judgment

The methodology is more interesting than any feature, and the repo's history shows it under load:

- **Measure before optimizing.** A frame-time profiler was built before any optimization; it showed the
  system had ~7× headroom at the working scale, so a tempting "v2 kernel" rewrite was *refused* as
  premature. When scaling was later considered, profiling found the real bottleneck was redundant
  hashing (75% of a tick), **not** the eigensolver everyone assumed — so the proposed "better math"
  was the wrong target.
- **Caught fabricated numbers.** Several speculative experiments arrived with pre-written "results."
  Running them disproved the numbers (a claimed 30.92% compression gain was really ~5% and sometimes
  *negative*; a claimed 40.62% fractal porosity was really 37.57%; a "Klein bottle" boundary had a real
  topological bug). Each was corrected in the ledger with the measured value.
- **Found and fixed a real determinism leak.** Off-beat commits folded `time.time()` into a committed
  hash, so replay would drift across machines — diagnosed, fixed (frame-derived), and proven.
- **Epistemic honesty as a hard rule** (`MCL_OBS2` witness protocol): *a chain hash certifies integrity,
  never truth.* The system refuses to emit verdict-shaped outputs and requires a falsification condition
  before any experiment is registered. The capstone self-critique (`docs/archive/constitution/ANNEX_I_AXIOMATIC_
  METABOLISM.md`) argues *against* the project's own grander claims.

## Honest scope — what it is NOT

- **Not a game engine or renderer.** A game was prototyped as a cheap test and the test concluded the
  system is a verification backend, not a game. (The 2D client exists only to exercise the server.)
- **Not decentralized / not Web3.** Authority rests on a server-held secret — the *opposite* of trustless
  consensus. Earlier framing that suggested a blockchain-like role was wrong.
- **Not high-throughput.** Single-writer Python at ~10 Hz with O(N³) steps in places; fine for the scales
  shown, not a database.
- **Not production-hardened.** Single-developer research artifact: no load testing at scale, no security
  audit, the "physics" layer is exploratory.

## How to evaluate it in ten minutes

```
cd docs/archive                                          # legacy implementation now lives here
PYTHONHASHSEED=0 python3 forge/oracle_fuzz.py            # 0 violations over 20k fuzzed cases
PYTHONHASHSEED=0 python3 forge/duel_determinism_proof.py # hardware-invariant replay
PYTHONHASHSEED=0 python3 forge/nonce_proof.py            # replay immunity
PYTHONHASHSEED=0 python3 walkthrough_genesis.py          # end-to-end self-verifying lifecycle
```

Then read `docs/archive/constitution/ANNEX_I_AXIOMATIC_METABOLISM.md` for the project's own honest verdict on what it
did and did not achieve.

## One-line summary

A deterministic, content-addressed, cryptographically-auditable state machine, built with an unusually
disciplined "measure / prove / stay honest" methodology — a demonstration of high-assurance engineering,
not a product and not a game.
