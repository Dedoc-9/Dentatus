# Dentatus/Chronicle — an honest technical overview

> **Repo layout note.** The active project is the **Chronicle workbench**: two frozen cores
> ([`chronicle/`](chronicle/README.md), [`llm_toolkit/`](llm_toolkit/README.md)) plus 27 decoupled
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

The `chronicle` core has been extended into a **29-component workbench** (2 frozen cores + 27 siblings,
**505 unit tests across 36 suites**, all gated by one preflight). The siblings are deliberately decoupled —
each imports the cores read-only (the "Sibling Law", verified by a parity proof), each is a small **reference
implementation** of the one idea in a different domain, and **each states its own honest bound in its
README**. They group into families: an audit core; governance & isolation (`guard_server`, `pact`, `quorum`,
`polity`); a three-layer offline-replayable proof stack (`tessera` → `fuel` → `elenchus`); a
hardware-invariant integer workload and its adversary (`syracuse`, `crucible`); real-time and fixed-point
physics (`lockstep`, `aether`, `manifold`); a boundary layer that admits the messy real world (`stasis`);
and the possibility-aware runtime (`airlock`, `salience`, `consequence`, `causal_runtime`, `intervention`) that
proposes, allocates, spends, and *tests* computation over a deterministic kernel without ever mutating it. None of them is a
product; collectively they are a demonstration that one honest primitive
composes across surprisingly different problems. Two **standalone applications** in the repo show the same
composition one level up — `aegis_gate/` (a verifiable transfer & KYC agent; a *mock* bank, proves the audit
trail not the wisdom), `VeriSim/` (a verifiable simulation engine; proves the *test was real*, not that the
model matches reality), `VeriVerse/` (a verifiable procedural world/physics-engine prototype — a *scaffold*
for a deterministic, cryptographically-replayable physics engine that competes with conventional engines on
bit-exact determinism and verifiability rather than render speed/fidelity), `AetherPulse/` (a Stage-1
deterministic engine kernel + cross-language conformance vectors for a future C++/Rust port), and
`AetherManifold/` (deterministic Riemannian optimization on the Stiefel manifold — proves a *trajectory* was
computed exactly, not that the minimum is global) — each importing the cores read-only via the Sibling Law,
none a deployed system.

The single epistemic thread running through all of it: **`integrity ≠ truth`.** A hash certifies that a
record is unforged, reproducible, and rule-faithful — never that the underlying decision was correct, fair,
or wise. The newer siblings apply this recursively: consensus is not truth (a colluding majority agrees on a
falsehood); a reasoning trace that follows the rules is not a true conclusion; a fixed-point manifold is
exactly constrained in integer space, not "perfect" in real space. The system is built *around* that limit
rather than pretending to break it.

**The possibility-aware runtime (`airlock`, `salience`, `consequence`, `causal_runtime`).** The most recent
layer turns the workbench into a deterministic reality engine an LLM/agent/human integrates with *as an
untrusted proposer*, and then allocates computation over the committed result. `airlock/` is a general
reality-transition membrane: a proposer never mutates state — it emits a bounded candidate transition that
passes `canon → fuel → shadow-apply → validate → witness` before the deterministic kernel commits it, under
two laws (`telemetry ≠ control`, `intent ≠ authority`). Because every *unrealized* transition leaves a trace,
the runtime measures what almost happened — proposal pressure, the lawful-but-unchosen "admissible" set, and
the geometry of that unrealized field — and `salience/` allocates compute by *possibility density* (the
doorway over the quiet valley) under one more law: `possibility → allocation`, never `possibility → physics`.

Downstream of the commit, a **reality/observation domain split** governs *where computation goes* without ever
touching what was committed. `consequence/` is the State-Graph Taint Map: a perturbation's weight is
`Δ · dependency_mass`, not its magnitude (`consequence ≠ magnitude`, the butterfly), and its Causal
Reconstruction Test deletes ~87% of compute while preserving the full future on structured worlds — *bounded*
by graph completeness (an undeclared coupling collapses preservation to 0.414, measured). `causal_runtime/`
composes that into one field, `A = consequence × uncertainty × possibility + G⁺`, and an `AttentionField`
apportions streaming/AI/fidelity/network/validation depth from it. The epistemic axis is fed by a
producer-agnostic novelty seam (`dini` is one producer, crossing a Q16 canon boundary), and the **ghost**
`G⁺ = max(0, observed − predicted)` catches what the graph cannot — an undeclared coupling that moves a node
the model rated zero. The **cardinal invariant** is proven against `AetherPulse`: attaching the observer
leaves the committed hash trajectory byte-identical, under one more law `causal_information → attention`, never
`→ mutation`. When a ghost *persists*, `causal_runtime`'s coupling discovery proposes (never commits) a graph
edge behind four locks, and `intervention/` resolves what observation cannot: an airlock-authorized `do()`
experiment on a discarded shadow world separates true coupling (CONFIRMED) / confounder (REJECTED) / feedback
(CYCLE), under a final law `causal_information → experiment` ALLOWED (shadow-only), never `→ truth`. A persistent ghost is not believed for recurring: it becomes a `StructureProposal` whose status is set by a **held-out falsification gate** (evidence can decay), and only edges that survive may wear structural vocabulary — the system is a **falsifiable structure-maintenance system**, not a causal discoverer (`prediction → truth` FORBIDDEN; `falsification → proposal status` ALLOWED, `→ committed reality` FORBIDDEN). The stack
is a closed epistemic loop that improves the *model* while the committed history never moves. Honest scope:
this is a *reference runtime and a measurement framework*, not a shipping 240fps engine and not a claim about
physical nature — it allocates compute and certainty under the declared structure, never truth, and never that
the structure is correct (`integrity ≠ truth`).

**Native ports (C++/Rust).** Performance-critical pieces (e.g. the `AetherPulse` engine) may be ported to
C++/Rust, but the **Python reference defines the semantics**: a native build is validated strictly against
the Python reference via *conformance vectors* (input world → expected state hashes). The native code never
defines truth; it must reproduce the reference's hashes bit-for-bit, which makes the conformance suite an
anti-UB / anti-drift guard. The native artifact lives in its own folder and does **not** import the workbench.

## What is genuinely solid (and reproducible)

Each of these is a runnable proof, not a claim. Under `PYTHONHASHSEED=0`:

| Property | Evidence |
|---|---|
| The whole workbench passes one gate — 36/36 suites + coupled/uncoupled parity, run as real subprocesses | `integration/preflight_check.py` → `[FOUNDRY VERIFIED]` |
| Cores have not drifted from a pinned baseline; siblings vendor no core (the Sibling Law) | `selfaudit/` → `workbench_H` |
| Replay court — record, tamper, rule-swap, fail-closed invariant, Ed25519 third-party verify | `chronicle/demo_policy.py` |
| Exact integer consensus + the 2D (lateral×temporal) attestation lattice | `quorum/demo_quorum.py` |
| A bounded integer VM whose run mints an offline-replayable proof shard | `fuel/demo_fuel.py`, `tessera/demo_tessera.py` |
| A 1,000,000-step fixed-point manifold with deterministic self-retraction, no nondeterministic drift | `aether/demo_aether_physics.py` |
| Consequence-aware allocation that leaves reality untouched — committed hash byte-identical with/without the observer, the ghost discovers an undeclared low-visibility anomaly distance & consequence both miss, and a persistent ghost is resolved by an airlock `do()` on a shadow world | `causal_runtime/demo_aether_attention.py`, `causal_runtime/ghost_persistence.py`, `intervention/benchmark.py` |
| Standalone *applications* compose the stack into products (Sibling Law, read-only imports, own tests) | `aegis_gate/` (verifiable transfer agent, 14 tests), `VeriSim/` (verifiable simulation, 12 tests), `VeriVerse/` (verifiable voxel world+physics, 13 tests), `AetherPulse/` (deterministic engine kernel + conformance vectors, 15 tests), `AetherManifold/` (deterministic Riemannian optimization, 10 tests) |
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

- **Not a game engine or renderer.** A game was prototyped to exercise the kernel, but the workbench competes
  on *determinism and verifiability*, not frame-rate or fidelity; the 240fps target lives in a native port, not here.
- **Not a truth oracle.** Every proof is `integrity ≠ truth`: it certifies a record is unforged, reproducible,
  and rule-faithful — never that the decision, model, or conclusion is correct, fair, or wise.
- **Not host security.** It bounds *authority to act* and makes tampering *detectable*; on a compromised host
  the same user can still abuse the capture path. It is tamper-evidence, not tamper-proofness.
- **Not a self-modifying system.** The observation/causal layer improves the *model* (attention, proposals,
  interventions); the committed hash trajectory — the territory — is never modified by any of it.
