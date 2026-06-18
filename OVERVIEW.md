# Dentatus/Chronicle — an honest technical overview

> **Repo layout note.** The active project is the **Chronicle workbench**: two frozen cores
> ([`chronicle/`](chronicle/README.md), [`llm_toolkit/`](llm_toolkit/README.md)) plus 22 decoupled
> *sibling* components, gated by one command (`integration/preflight_check.py`). The full legacy Reality
> Engine / Citadel implementation described in the second half of this document now lives under
> [`docs/archive/`](docs/archive/) — run its proofs from there (`cd docs/archive` first). The
> separately-connected game client remains in `Game1/`.

*Plain-English entry point for a technical reader. The `README.md` and `constitution/` are written in an
in-world vocabulary ("Reality Engine," "Citadel," "manifold," "physical law"); this document is the
de-inflated translation. Where the in-world docs and this one disagree on what the system actually
**is**, believe this one.*

---

## What it actually is

At the core, Dentatus/Chronicle is a **deterministic, content-addressed state machine with a cryptographic
audit trail and a discipline for proving invariants about itself.** Concretely:

- Every state is identified by a hash of its full contents (`H_t = SHA256(canonical_bytes(state))`), so the
  identity *is* the state — you cannot change the data without changing the address.
- Nondeterminism (clocks, RNGs, GPU float drift, model calls, external reads) is **captured at the boundary**
  as recorded inputs at write time and **replayed at audit time**, so a workflow re-runs bit-for-bit on any
  machine. Tampering is detected because the re-derived hash won't match.
- Commits are **attested** — HMAC under a server-held secret, or Ed25519 where a third party must verify
  without being able to forge — and a separate test discipline proves invariants about the system itself.

Everything else is that one idea wearing a different hat. The recorder, the replay court, out-of-process
policy enforcement, consensus, a bounded integer VM, reasoning-trace checking, a fixed-point physics
manifold — each is the same canonical-bytes → hash + capture-at-boundary discipline applied to a new domain.

### The workbench today

The `chronicle` core has been extended into a **24-component workbench** (2 frozen cores + 22 siblings,
**284 unit tests across 26 suites**, all gated by one preflight). The siblings are deliberately decoupled —
each imports the cores read-only (the "Sibling Law", verified by a parity proof), each is a small **reference
implementation** of the one idea in a different domain, and **each states its own honest bound in its
README**. They group into families: an audit core; governance & isolation (`guard_server`, `pact`, `quorum`,
`polity`); a three-layer offline-replayable proof stack (`tessera` → `fuel` → `elenchus`); a
hardware-invariant integer workload and its adversary (`syracuse`, `crucible`); real-time and fixed-point
physics (`lockstep`, `aether`, `manifold`); and a boundary layer that admits the messy real world
(`stasis`). None of them is a product; collectively they are a demonstration that one honest primitive
composes across surprisingly different problems. Two **standalone applications** in the repo show the same
composition one level up — `aegis_gate/` (a verifiable transfer & KYC agent; a *mock* bank, proves the audit
trail not the wisdom) `VeriSim/` (a verifiable simulation engine; proves the *test was real*, not that the
model matches reality), and `VeriVerse/` (a verifiable procedural world/physics-engine prototype — a *scaffold*
for a deterministic, cryptographically-replayable physics engine that competes with conventional engines on
bit-exact determinism and verifiability rather than render speed/fidelity) — each importing the cores read-only
via the Sibling Law, none a deployed system.

The single epistemic thread running through all of it: **`integrity ≠ truth`.** A hash certifies that a
record is unforged, reproducible, and rule-faithful — never that the underlying decision was correct, fair,
or wise. The newer siblings apply this recursively: consensus is not truth (a colluding majority agrees on a
falsehood); a reasoning trace that follows the rules is not a true conclusion; a fixed-point manifold is
exactly constrained in integer space, not "perfect" in real space. The system is built *around* that limit
rather than pretending to break it.

## What is genuinely solid (and reproducible)

Each of these is a runnable proof, not a claim. Under `PYTHONHASHSEED=0`:

| Property | Evidence |
|---|---|
| The whole workbench passes one gate — 26/26 suites + coupled/uncoupled parity, run as real subprocesses | `integration/preflight_check.py` → `[FOUNDRY VERIFIED]` |
| Cores have not drifted from a pinned baseline; siblings vendor no core (the Sibling Law) | `selfaudit/` → `workbench_H` |
| Replay court — record, tamper, rule-swap, fail-closed invariant, Ed25519 third-party verify | `chronicle/demo_policy.py` |
| Exact integer consensus + the 2D (lateral×temporal) attestation lattice | `quorum/demo_quorum.py` |
| A bounded integer VM whose run mints an offline-replayable proof shard | `fuel/demo_fuel.py`, `tessera/demo_tessera.py` |
| A 1,000,000-step fixed-point manifold with deterministic self-retraction, no nondeterministic drift | `aether/demo_aether_physics.py` |
| Standalone *applications* compose the stack into products (Sibling Law, read-only imports, own tests) | `aegis_gate/` (verifiable transfer agent, 14 tests), `VeriSim/` (verifiable simulation, 12 tests), `VeriVerse/` (verifiable voxel world+physics, 13 tests) |
| *(legacy, in `docs/archive/`)* differential fuzzing 20k cases 0 violations; hardware-invariant replay; replay immunity; chaos-order invariance | `forge/oracle_fuzz.py`, `forge/duel_determinism_proof.py`, `forge/nonce_proof.py`, `forge/chaos_harness.py` |

## The part that's actually worth showing: engineering judgment

The methodology is more interesting than any feature, and the history shows it under load:

- **Measure before optimizing.** A frame-time profiler was built before any optimization; it showed ~7×
  headroom, so a tempting "v2 kernel" rewrite was *refused* as premature. Later profiling found the real
  bottleneck was redundant hashing (75% of a tick), **not** the eigensolver everyone assumed.
- **Caught fabricated numbers.** Several speculative experiments arrived with pre-written "results." Running
  them disproved the numbers (a claimed 30.92% compression gain was really ~5% and sometimes *negative*; a
  "Klein bottle" boundary had a real topological bug). Each was corrected in the ledger with the measured value.
- **Found and fixed a real determinism leak.** Off-beat commits folded `time.time()` into a committed hash,
  so replay would drift across machines — diagnosed, fixed (frame-derived), and proven.
- **Honest framing enforced continuously.** Across the workbench expansion, marketing-shaped proposals
  ("post-trust," "solves the Halting Problem," "diamond-hard," "100% certainty," a Collatz-indexed
  derivative) were each either re-scoped to what the code proves or refused outright and recorded as a
  non-claim. Every sibling README carries a "honest bounds" section.

## Honest scope — what it is NOT

- **Not a game engine or renderer.** A game was protot