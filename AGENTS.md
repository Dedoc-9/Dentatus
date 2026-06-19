```
================================================================================
        CHRONICLE WORKBENCH — SYSTEM CONTEXT & LLM / AGENT HANDOFF
================================================================================
```

**To any human or model editing this repository:** this is a high-assurance,
deterministic, content-addressed workbench ("Dentatus/Chronicle"). Code you add
is bound by the contract below. The boundaries are enforced by 437 tests across 35
suites and by the Replay Court / Parity Proof — violate them and the regression
suite fails. Equally binding is the *epistemic* rule: **never oversell what the
code protects.**

This file is the canonical handoff. For narrative depth see [`README.md`](README.md),
[`OVERVIEW.md`](OVERVIEW.md), and [`docs/LESSONS.md`](docs/LESSONS.md).

---

## 0. The one idea (read this first)

A tiny deterministic core — **canonical bytes → SHA-256 content hash** — plus one
discipline: **capture nondeterminism at the boundary; never fake it away.**
Everything else (replay court, signed verdicts, policy enforcement, quality
assay, hardware signing) is that idea wearing a different hat. If a change does
not reduce to those two things, it probably does not belong.

---

## 1. Determinism (reproducibility-by-construction)

- State logic must be a **pure function of its recorded inputs**. No raw
  `time.time()`, no `random`/`uuid`, no reliance on dict/set iteration order, no
  un-isolated network or disk reads inside the logic.
- Route every side-effect through a **capture seam** (`chronicle/capture.py`,
  `llm_toolkit/agent_capture.py`): at record time the effect runs and its result
  is captured *into the inputs*; at replay the captured value is replayed. Replay
  must never touch the live clock/model/network.
- Canonicalize floats explicitly via `format(x, ".12g")` so GPU/architecture
  float reassociation cannot fork a hash. **Caveat:** this is a *12-significant-
  digit floor* — carry money / high-precision values as integers or fixed-point,
  not floats.
- **Honest note on `PYTHONHASHSEED=0`:** it is a *discipline guard*, not a
  load-bearing dependency of the hashing. The content hashes use SHA-256 over
  `sort_keys` JSON and are **not** affected by Python's randomized `hash()`. The
  demos refuse to run without the flag on purpose (to enforce the reproducible-
  invocation habit), but do **not** add security controls that *key off* this
  env var — that is cargo-culting (see §5).
- `verify_determinism()` / `verify_replay_determinism()` are leak detectors: run
  the logic N times; if outputs differ, a side-effect escaped the seam. Use them.

## 2. Privilege isolation (out-of-process PEP)

- Do **not** write naked filesystem mutations or shell/exec calls from agent or
  generation logic. Every consequential or disk-writing action must request a
  signed authorization ticket from the out-of-process PEP
  ([`guard_server/isolated_pep.py`](guard_server/isolated_pep.py)).
- The PEP enforces a **directory allow-list clamp** (e.g. strictly under
  `~/projects/design/`), pre-resolving `..` traversal and symlink escapes via
  deepest-existing-ancestor `realpath` (fail-closed on anything unresolvable).
- Every verdict (`allow`/`deny`) is **bound to the SHA-256 of the exact action**
  and Ed25519-signed. The agent cannot alter a verdict, replay it for a different
  action, or forge an `allow` (it lacks the key). Denials append to a fsync'd
  append-only log.
- Run the PEP under a **separate OS user** from the agent for real separation;
  the code warns if it detects same-uid / root.
- **What this protects / does NOT:** bounded authority + tamper-evidence — *not*
  host tamper-proofness. On a single compromised host the same user can abuse the
  capture path; the PEP bounds *authority to act*, it does not make a compromised
  host honest.

## 3. Cognitive modesty — integrity ≠ truth

- Treat the generation layer (LLM) as **inherently untrusted and volatile.** Do
  not write wrappers that try to make the model "smarter" or soft-classify safety
  inside the prompt. Safety lives in **host-side, precommitted validity
  predicates at the ledger commit boundary**, not in the model's good intentions.
- If generated content violates a precommitted invariant, the state machine must
  **fail closed**: reject the commit, roll back, log. (`InvariantViolation`,
  `TransitionRefused`.)
- Every component proves a record is *unforged, exactly reproducible, and
  rule-faithful* — **never** that the decision was correct, fair, or wise.
  [`assay/`](assay/README.md) extends this one level up: it makes quality
  judgments recomputable (metrics) or attributable (signed opinions), but still
  does **not** certify truth. State the narrowest claim your mechanism supports.
- Trust boundaries verify against **pinned** keys held in config — never a key
  taken from the payload/inputs. (PEP trust anchor, `assay` assessor registry.)
  Verifying against an input-supplied key silently defeats the property.

## 4. Extractability, dependencies, and crypto tiers

- **Build for extraction, not just execution.** Keep modules decoupled. Core
  logic is **standard-library only**; `cryptography` is an *optional* enhancement
  (asymmetric attestation), never a hard import in a core path.
- **Sibling Law:** add capability as a NEW sibling component that imports the frozen cores read-only;
  never edit a core to add a feature. A new component is "in" only when its suite passes, it is in
  `integration/preflight_check.py`, and the cores' tests + `parity_proof.py` still pass. (See README -> *The Sibling Law*.)
- `chronicle/` and `llm_toolkit/` deliberately **vendor** their own copy of the
  primitives so each lifts out as a standalone repo. That duplication is
  intentional; [`integration/parity_proof.py`](integration/parity_proof.py) is
  the regression guard proving the copies are byte-identical. `guard_server/`,
  `integration/`, and `assay/` are *coupled* (import `llm_toolkit`).
- Signing is tiered and degrades **loudly, never silently**
  ([`chronicle/hardware_signing.py`](chronicle/hardware_signing.py)):
  - **Tier 1** `pkcs11-ecdsa-p256` — TPM 2.0 / YubiKey via `ctypes` PKCS#11; key
    never enters RAM. *(Implemented to PKCS#11 v2.40; not exercisable without a
    physical token.)*
  - **Tier 2** `ed25519-soft` — asymmetric; private key **AES-GCM encrypted at
    rest under a scrypt KEK**, in RAM only during the signing call.
  - **Tier 3** `hmac-scrypt` — stdlib-only, **symmetric** last resort. No
    third-party non-repudiation; the warning says so.
  scrypt's role is *key hardening* (at-rest encryption / derivation), never a
  "signing primitive."
- `sign()` returns a **hex string** (it must round-trip through the JSON ledger);
  raw bytes are not serializable. Match this convention in any new signer.
- `source_hash` (a.k.a. `ruleset_hash`) binds logic by its **exact source text**
  via `inspect.getsource`. This proves "the rules didn't change" — but it also
  means reformatting, renaming, or re-commenting a rule/guard function changes its
  hash and **invalidates prior attestations**. Treat recorded rule functions as
  frozen; version them deliberately.

---

## 5. Anti-patterns (these fail review)

- A security control that keys off `PYTHONHASHSEED` (it is a determinism guard).
- Verifying a signature against a public key taken from inputs instead of pinned config.
- A `cryptography` import in a core path with no stdlib fallback.
- Mutating files / running commands without a PEP-signed, action-bound ticket.
- Reading a clock / RNG / network inside state logic instead of via the capture seam.
- Claiming a record proves a decision is correct/fair/safe. It proves integrity, not truth.
- "Improving" determinism by hand-rolling crypto or collapsing the dual (coupled/uncoupled) representations.
- Reporting a change as *done* — or emitting any green/`[FOUNDRY]` status — without actually running
  `integration/preflight_check.py`. A status you did not earn by running is integrity-theater.

---

## 6. The verification contract

Before proposing a change as done, all suites must pass under the flag:

```bash
export CHRONICLE_SIGNER_PASSPHRASE=...        # for the Tier-2/3 signer tests
for t in chronicle/tests/test_chronicle.py chronicle/tests/test_hardware_signing.py \
         llm_toolkit/tests/test_llm_toolkit.py guard_server/tests/test_guard_server.py \
         guard_server/tests/test_isolated_pep.py integration/tests/test_integration.py \
         assay/tests/test_assay.py; do
  PYTHONHASHSEED=0 python3 "$t" || echo "FAIL: $t"
done
PYTHONHASHSEED=0 python3 integration/parity_proof.py   # must print: PARITY HOLDS
```

**Current verification state: 437 tests passing across 35 suites (+ coupled/uncoupled parity proof).**

| Suite | Tests | Guards |
|---|---|---|
| `chronicle/tests/test_chronicle.py` | 19 | chain, replay, rule-binding, fail-closed, Ed25519/HMAC, capture, store |
| `chronicle/tests/test_hardware_signing.py` | 5 | Tier-2/3 signer round-trip, at-rest encryption, drop-in recorder |
| `llm_toolkit/tests/test_llm_toolkit.py` | 18 | capture replay, guardrails, Ed25519 audit, HMAC fallback |
| `guard_server/tests/test_guard_server.py` | 10 | pinned policy, request-bound verdicts, tamper/forge |
| `guard_server/tests/test_isolated_pep.py` | 11 | path clamp, traversal/symlink escape, verdict binding, append-only log |
| `integration/tests/test_integration.py` | 5 | coupled stack, separation of powers, coupled/uncoupled parity |
| `assay/tests/test_assay.py` | 10 | recomputable metrics, attributed judgments, fudge/forgery |
| `manifold/tests/test_manifold.py` | 9 | topology->world_H, exact connectivity/bridge gate, captured λ₂ |
| `anti_cheat/tests/test_anti_cheat.py` | 9 | pinned visibility, occlusion gate, culling, replay/tamper |
| `glitch/tests/test_glitch.py` | 8 | state-space explore, content-hash dedup, shrink, seal+replay |
| `dini/tests/test_dini.py` | 9 | hyperbolic embedding sensor (captured observable, never a gate) |

### Definition of done

A change is not complete until **all three** hold — anything less is not "done":

1. `integration/preflight_check.py` prints `[FOUNDRY VERIFIED]` (it actually ran the 35 suites + parity).
2. A **Verification Record** is produced for review — the copy-paste template, run triggers, and reject
   criteria live in `README.md` -> *"Using this in a project"*. Hand a reviewer only **public** material
   (ledger + public key + hashes); never a private key or HMAC secret.
3. Any `ruleset_hash` / `policy_hash` / `guardrail_hash` that changed is a **deliberate, documented**
   version bump (editing rule/guard source invalidates prior attestations — see §4 `source_hash`).

Do not state "done" or paste a green status you did not earn by running the contract.

### Use case — reflexive self-audit & core-drift detection

`selfaudit/evaluate.py` is how "the cores are frozen" stops being a promise and becomes a *checkable,
signed fact*. It turns the workbench on its own cores: it pins a SHA-256 baseline of every frozen-core
file in `selfaudit/core_baseline.json`, grades a battery of mechanical checks (determinism, coupled/
uncoupled parity, cores-unchanged-vs-baseline, no-core-copied-under-another-name), seals each grade as an
`assay` metric assessment, and the assay court replays the whole report. It also runs a *drift-caught
demonstration* (forges a baseline entry and confirms the detector flags it), so the audit proves the
detector detects — not just that the happy path is green.

Operational scenario:

1. **Establish the baseline once.** `PYTHONHASHSEED=0 python3 selfaudit/evaluate.py` with no baseline
   present writes `core_baseline.json`. Commit it. That file is now the pinned definition of "frozen".
2. **Detect drift on every change / in CI.** Re-running compares each core file against the pinned
   baseline; **any** change to a frozen-core file (or a frozen core copied under a new filename in a
   sibling) makes the audit exit non-zero. This enforces §4's Sibling Law mechanically.
3. **Intentionally changing a core is a deliberate, documented act.** On the rare occasion a frozen core
   *must* change, re-establish the baseline (delete `core_baseline.json`, re-run, commit) and record why —
   exactly like a deliberate `ruleset_hash` version bump (§4). An *un-documented* baseline change in a diff
   is a red flag a reviewer should reject.

Honest bound (integrity ≠ truth, inward): this proves the cores are byte-stable vs the pinned baseline and
that the audit is reproducible — **not** that the workbench is correct, useful, or good. A system grading
itself is not a judge of its own value.

### Use case — high-velocity LLM ("vibe") coding, safely

The reflexive architecture lets you run an LLM coding partner at high generation velocity while the
*workbench*, not your attention, holds the line on the failure modes LLMs reliably introduce: silent core
drift, float/serialization changes that break reproducibility, duplicated utilities, folder-isolation
escapes, patched-over edge cases. The honest claim is narrow and real: **the workbench mechanically catches
the classes of regression its checks cover, so you stop re-reading diffs for those.** It does NOT make
arbitrary generated code correct — integrity ≠ truth: a green foundry means *no regressions + frozen cores
+ lawful structure*, not "the code is good."

Four mechanisms, each with its real bound (state the bound; don't oversell):

1. **Bounded-authority autonomy (`guard_server/isolated_pep.py`).** Run the PEP under a separate OS user
   and route every disk write / command through it; the symlink-proof directory clamp confines the agent to
   an allow-listed folder and verdicts are signed + action-bound, so the agent cannot forge an `allow`.
   *Bound:* OS privilege separation, not magic — it only holds if the PEP truly runs as a different user AND
   the agent has no filesystem path that bypasses it. On a single user it is bounded authority + tamper-
   evidence, not "physical impossibility" (§2/§3). Wire it; don't assume it.

2. **Core-drift detection (`selfaudit/` + `parity_proof.py`).** After the agent edits code, run the
   preflight; a touched frozen core mismatches the pinned `core_baseline.json`, the audit fails, and the
   assay court won't replay — the math names the drifted file instead of you reading the diff. *Bound:*
   catches changes to the **frozen cores** and coupled/uncoupled parity plus whatever the suites assert; it
   does NOT catch a logic bug in NEW sibling code that still passes every check.

3. **Geometric navigation (`dini/`).** The agent reads `dini_distance` as a compact novelty/structure
   sensor instead of dumping huge directory listings into its context. *Bound:* a sensor, never a gate;
   dual-use (see dini's responsible-use note); a captured float, never in a commit hash.

4. **Fail-closed generation (`chronicle` invariants).** Have the agent precommit a Chronicle validity
   predicate FIRST; if its later code produces a state that breaches the predicate, the recorder refuses the
   write (`InvariantViolation`), the agent gets an explicit error to self-correct, and the state rolls back
   to the last valid hash. *Bound:* the gate enforces exactly what the predicate encodes — not unsafety you
   never wrote down (§3).

**The loop:** the LLM is the engine; the frozen cores are the chassis; `integration/preflight_check.py` is
the gate. Run the preflight as the agent loop's definition-of-done (§6) — it is the thing that stops a
session on a regression, and only because it actually ran (not because a banner says so, §5). Used this
way the attention tax drops on everything the checks cover, and your review goes where a machine cannot
certify: whether the new logic is actually *right*.

### Use case — streamlining the project itself (beyond a single coding loop)

The same primitives that secure one decision also remove whole categories of project overhead. Each item
states the leverage *and* its bound — the point is throughput you can actually trust, not a faster way to be
wrong (§3).

1. **One replayable gate instead of a CI matrix (`integration/preflight_check.py` + `parity_proof.py`).**
   The preflight *is* the definition of done: it runs all 35 suites + the coupled/uncoupled parity proof as
   subprocesses under `PYTHONHASHSEED=0` and names the exact failing suite/file. You stop maintaining a
   sprawling pipeline and a pile of green-banner screenshots. *Bound:* it asserts what the suites assert —
   no regressions + frozen cores + lawful structure — not that uncovered new logic is correct.

2. **Parallel exploration with exact dedup (`quorum/` + `glitch/`).** Fan an LLM (or several) across N
   branches of a design space, content-address each candidate's resulting state, and let `quorum`'s exact
   integer tally collapse the ones that truly converge while isolating the genuine forks — redundant work is
   identified mechanically instead of by re-reading every diff. *Bound:* agreement is on exact hashes, not
   semantic equivalence; two correct-but-differently-canonicalized outputs read as divergent (and a
   colluding-style shared bug agrees just as cleanly — consensus ≠ truth).

3. **Hardware-invariant budgets & benchmarks (`ration/` + `stride/` + `lockstep/`).** `ration` gates on
   exact integer *logical steps*, so a runaway loop or a benchmark passes/fails identically on a decade-old
   laptop and an enterprise array; `stride` refuses a migrated computation whose environment fingerprint
   doesn't match; `lockstep` decouples the truth-tick from wall-clock so timing variance never changes the
   outcome. Reproducible perf work without a reference machine. *Bound:* logical determinism, not physical
   cost — it won't stop an OS OOM-kill or model real latency; those stay captured observables.

4. **Multi-model arbitration to shrink review (`quorum/`).** Route a refactor or a decision through several
   independently-seeded paths or different vendors as witnesses, commit only on quorum agreement, and let the
   dashboard surface the rounds that forked. Review shifts from "read every diff" to "look only where the
   models disagreed." *Bound:* catches divergence *among* witnesses, not an error they all share; the gate is
   agreement, not correctness.

5. **Audit-ready by construction for regulated work (`chronicle/` + `assay/` + `pact/`).** Because every
   consequential decision is recorded, replayable, and signed as it runs, the audit trail is a *byproduct of
   execution*, not a separate documentation phase bolted on before a review. `assay` makes the quality
   judgments themselves recomputable; `pact` attributes multi-party steps to the exact agent. *Bound:*
   evidence *toward* a standard (SOC 2 / EU AI Act traceability), not *satisfaction* of it; integrity ≠ truth.

6. **Real-time/game projects get determinism up front, not retrofitted (`lockstep/` + `anti_cheat/`).**
   Separating the integer truth-tick from the render rate at the start means netcode rollback, bit-exact
   replay, and server-authoritative anti-cheat all read one authoritative stream — you never rebuild
   determinism after the fact when 1440p/240fps presentation and a 120 Hz simulation have to agree. *Bound:*
   `lockstep` is the reconciliation core, not a GPU renderer; it produces the stream a render thread consumes.

### The velocity equation — why this accelerates an LLM project

The point of the 28-component workbench is to move the bottleneck from human code-review to automated
verification: you offload tracking of determinism, structural purity, privilege isolation, and resource
budgets to the math, and spend your attention only on what a machine cannot judge. Four concrete speedups,
each bounded:

1. **Refactoring-drift detection (`selfaudit/` + `parity_proof.py`).** When an LLM optimizes or refactors,
   it reliably introduces silent decay — changed iteration order, float/serialization drift, duplicated
   utilities. Run the preflight: a touched frozen core mismatches the pinned `workbench_H` baseline, the
   audit fails closed and *names the drifted file*, and parity breaks if a primitive changed. You stop
   reading diffs for structural purity. (`dini/` gives a structural map as an observable — it is not the
   detector; `selfaudit`/parity are.) *Bound:* catches core drift + parity + suite regressions, not a logic
   bug in new code that still passes every check.

2. **Model-drift debugging (`llm_toolkit/` + `court.py`).** An upstream vendor model swap can break Friday
   what worked Monday; ordinary logs only say *that* it failed. `capture.py` freezes the boundary (prompt,
   seed, logprobs); the Replay Court re-runs the workflow against the frozen telemetry **without the live
   API/GPU**, isolating *your* logic bug from an upstream change. *Bound:* you replay the captured output —
   it does not re-derive the model.

3. **Zero-trust sandboxing (`guard_server/isolated_pep.py`).** Let an agent write/run files fast under an
   out-of-process PEP on a separate OS user; the symlink-proof `realpath` clamp + signed action-bound
   tickets confine it to the workspace. *Bound:* this is OS privilege separation, **not** "physically
   barred" — it holds only if the PEP runs as a different user and the agent has no bypass path (§2/§3).

4. **Fail-closed coding loops (`chronicle/` invariants).** Have the agent write a strict validity predicate
   FIRST; if its later code produces a breaching state, the recorder refuses the write (`InvariantViolation`)
   and the agent gets the exact error to self-correct, with rollback to the last valid hash. *Bound:* the
   gate enforces exactly what the predicate encodes — not unsafety you never wrote down.

```
[ Traditional flow ]  Code -> manual review -> debug non-determinism -> slow deploy
[ Workbench flow ]    Generate -> preflight (35 suites) -> replay verification -> fast deploy
```

The role-shift: you go from anxious code supervisor to systems architect — the LLM is the engine, the
frozen cores are the chassis, the preflight is the gate. The honest version of the claim is narrow and
real: this removes the attention tax on everything the checks cover. It is *not* "the code is correct" —
integrity is not truth (§3).

### The foundry at a glance

```
[ THE CHRONICLE FOUNDRY WORKBENCH ]
   |
   |-- chronicle/      --> [CORE 1] Immutable ledger, Replay Court, tiered signers (TPM/Ed25519/HMAC)
   |-- llm_toolkit/    --> [CORE 2] Deterministic orchestration & API capture seams
   |
   |-- guard_server/   --> Sibling 1:  OS-level privilege-isolation PEP server
   |-- integration/    --> Sibling 2:  Stack interop, master preflight, coupled/uncoupled parity proof
   |-- assay/          --> Sibling 3:  Meta-audit quality review (recomputable metrics + signed opinions)
   |-- manifold/       --> Sibling 4:  Topological connectivity gate (exact union-find / bridges)
   |-- anti_cheat/     --> Sibling 5:  Server-authoritative match flight-log (occlusion gate + culling)
   |-- glitch/         --> Sibling 6:  Deterministic state-space fuzzer (content-hash dedup + shrinking)
   |-- dini/           --> Sibling 7:  Hyperbolic coverage compass (Poincare/Mobius) -- sensor, dual-use
   |-- selfaudit/      --> Sibling 8:  Reflexive drift & parity detector (pinned workbench_H baseline)
   |-- wobble/         --> Sibling 9:  Verifiable synthetic-gene structural design log
   |-- ration/         --> Sibling 10: Integer-based complexity resource budgeting (hardware-invariant)
   |-- stride/         --> Sibling 11: Environment-isolated cross-boundary state transport
   |-- pact/           --> Sibling 12: Cross-attested multi-agent forensic covenant engine
   |-- quorum/         --> Sibling 13: Exact integer consensus (k-of-n) + 2D pact lattice (lateral x temporal)
   |-- lockstep/       --> Sibling 14: Truth-rate vs frame-rate reconciliation (integer ticks + rollback)
   |-- syracuse/       --> Sibling 15: Collatz/Syracuse map -- integrity != truth, hardware-invariant integer workload
   |-- tessera/        --> Sibling 16: Portable replayable proof-shard (offline replay, signed authorship, lineage)
   |-- crucible/       --> Sibling 17: Reverse-Collatz adversary -- deterministic hard-seed generator (the crucible)
   |-- fuel/           --> Sibling 18: Absolute Integer Standard -- bounded-execution VM, exact integer fuel, emits tessera
   |-- elenchus/       --> Sibling 19: Reasoning-trace interrogator -- replays a derivation vs pinned rules (footprints, not the mind)
   |-- polity/         --> Sibling 20: Deterministic governance -- quorum-ratified, content-addressed ruleset constitution lineage
   |-- stasis/         --> Sibling 21: Boundary layer -- Iron Canon + Divergence Ledger (gate/observable) + Lazy Merkle Lattice
   |-- aether/         --> Sibling 22: Hardened integer manifold -- Stiefel/SPD/field + ghost/spectral/predictive instrument panel
   |-- airlock/        --> Sibling 23: Reality-transition membrane -- propose->canon->fuel->shadow->validate->witness->commit (telemetry!=control, intent!=authority)
   |-- salience/       --> Sibling 24: Possibility-aware allocation field -- compute follows possibility density (possibility->allocation, never possibility->physics)
   |-- consequence/    --> Sibling 25: State-Graph Taint Map -- shared what-matters-next field (consequence != magnitude; never consequence->truth)
   `-- causal_runtime/ --> Sibling 26: Causal allocation of computation -- consequence x uncertainty x possibility -> AttentionField (causal_information->attention, never ->mutation; proven hash-identical vs AetherPulse)
```

Cores are frozen; the twenty-six siblings import them read-only (the Sibling Law, S4). `selfaudit/` keeps
the two cores honest against a pinned baseline; `integration/preflight_check.py` runs all 35 suites + the
parity proof as the one gate.

If your change breaks Replay Court, Parity Proof, or privilege separation, it is
wrong by definition here — fix the change, not the test.

### The children — a deep dive by family, and how they compose in real use cases

The twenty-five siblings are not a flat list; they fall into families that compose. Each entry states what it
*is*, what it *proves*, and its honest bound. The use-case flows below show them working together — that
composition is the actual product.

**Audit core — record & replay.**
- `chronicle` (Core 1): the verifiable decision recorder — content-addressing, hash-chaining, HMAC/Ed25519
  attestation, capture seam, append-only store. Proves a record is unforged, reproducible, rule-faithful.
- `llm_toolkit` (Core 2): the same discipline on LLM orchestration — captures prompt/tokens/logprobs/seed at
  the model boundary so an agent run replays bit-for-bit. *Bound:* replay is exact only for captured reads.

**Governance & isolation — who may act, and what becomes true.**
- `guard_server` (S1): an out-of-process Policy Enforcement Point — server-pinned policy + key behind a
  boundary the agent calls but cannot weaken; signed, request-bound verdicts. *Bound:* OS privilege
  separation only holds if the PEP truly runs as a separate user.
- `pact` (S12): multi-agent cross-attestation — each agent binds its new state hash to the prior agent's, so
  a later injection is attributable to the exact agent/link. *Bound:* non-repudiation under pinned keys; no
  broadcast/consensus.
- `quorum` (S13): exact integer consensus — k-of-n independently-keyed witnesses must agree on the same
  hash; dissent kept as a ghost; `lattice.py` binds it to `pact` into the 2D (lateral×temporal) lattice.
  *Bound:* a colluding ≥k majority certifies a falsehood; independence is a trust input.
- `polity` (S20): deterministic governance — governors vote (via `quorum`) to ratify a new ruleset version,
  minting a content-addressed constitution lineage so frozen rulesets evolve without breaking custody.
  *Bound:* proves the vote, never the wisdom.

**The Axiom triad — three layers of one offline-replayable proof.**
- `tessera` (S16): a portable proof-shard `{seed, rule, path_hash}` a stranger replays offline to confirm a
  deterministic computation's exact process history; signed authorship, immutable lineage, exact divergence
  locator. *Bound:* proves the declared computation's path, not a proxy for unrelated work; not secrecy crypto.
- `fuel` (S18): a bounded-execution integer VM — halting is exact integer fuel (no float gas), fail-closed on
  out-of-fuel / div-zero; every run mints a `tessera`. *Bound:* a small VM, not a production smart-contract VM.
- `elenchus` (S19): a reasoning-trace interrogator — replays a claimed derivation against a pinned exact
  rule-set and names the exact FABRICATED / GAP / UNKNOWN step; verdict is itself a `tessera`. *Bound:* checks
  the emitted trace vs declared rules — not the model's mind, not whether the conclusion is true.

**The Collatz pair — a hardware-invariant workload and its adversary.**
- `syracuse` (S15): the Collatz/Syracuse map as `integrity ≠ truth` made runnable — pure-integer orbits,
  content-addressed, verify any trajectory exactly, refuse the conjecture structurally. *Bound:* not crypto;
  a reference workload, not a proof for all integers.
- `crucible` (S17): the reverse-Collatz adversary — grows the pre-image tree upward to forge deterministic
  hard seeds (stopping time = reverse depth) and fires them at `ration`/`tessera`/`fuel`. *Bound:* maps the
  difficulty landscape; does not find the globally hardest seed, does not solve Collatz.

**Real-time & physics — truth-rate vs frame-rate, and hardened geometry.**
- `lockstep` (S14): decouples an integer, content-addressed truth-tick stream from the render rate; 240fps
  frames are exact interpolated *observables*, never gated; revert-to-last-valid-hash rollback converges
  clients. *Bound:* the reconciliation core, not a GPU renderer.
- `manifold` (S4): topology-gated commits — exact connectivity/bridges as the gate, Fiedler λ₂ as a captured
  observable. *Bound:* gates topology, not semantic correctness.
- `aether` (S22): the hardened integer manifold — DVSM geometry in fixed-point integers (bit-exact,
  replayable); the Stiefel auditor gates `E = ‖WᵀW − I‖²_F` under a *declared* epsilon and deterministically
  self-retracts (integer Gram-Schmidt), logging recovery. *Bound:* fixed-point is deterministic, not exact;
  orthonormality holds only within the declared epsilon.

**The boundary, sensors, and domain siblings.**
- `stasis` (S21): the Iron Canon (strict canonical bytes, rejects ambiguous/float types), the Divergence
  Ledger (gate-vs-observable: lie→FAIL, drift→WARN), the Lazy Merkle Lattice (batch + on-demand proofs).
- `ration` (S10) integer step budgets · `stride` (S11) environment-fingerprinted transport · `assay` (S3)
  recomputable quality judgments · `glitch` (S6) deterministic state-space fuzzer · `dini` (S7) hyperbolic
  novelty sensor (dual-use) · `anti_cheat` (S5) server-authoritative match forensics · `wobble` (S9)
  verifiable synthetic-gene design · `selfaudit` (S8) the workbench evaluating itself · `integration` (S2)
  the coupled full stack + parity proof.

#### Use case — a verifiable autonomous transaction (finance / operations)

A regulated agent approves a wire. `stasis` canonicalizes the request into integer-clean bytes; `guard_server`
confirms the agent holds authority it cannot self-grant; the decision is gated by exact integer logic and
recorded in `chronicle`; `ration` bounds the agent's logical steps so a prompt-injection loop is refused
fail-closed; `quorum` requires k independent witnesses to agree on the resulting state hash, and `tessera`
makes the whole trail replayable offline by a regulator holding only the public keys. *What it gives:* an
unforgeable, attributable, offline-verifiable transaction trail. *What it does not:* prove the loan was wise.

#### Use case — catching a silent model regression across a fleet

An upstream vendor quietly ships a weight update. Each node runs the same task; `stasis` classifies any
divergence — gated-field drift is a `LOGIC_ERROR` (FAIL, goes to `elenchus`), observable-only drift is benign
(WARN). `quorum` tallies the nodes; honest outvoted nodes register dissent and `ghost.py`'s `S_t` pressure
rises as an early drift radar — *before* a production failure. *Bound:* a rising ghost flags disagreement,
not which side is correct.

#### Use case — a self-correcting physics / simulation run

`crucible` forges near-degenerate manifold seeds; `aether` evolves them in fixed-point integers; the Stiefel
auditor trips when `E` exceeds the declared epsilon and self-retracts, logging each recovery as a shard;
`fuel` bounds the work so a runaway never hangs; `tessera` makes the entire 1,000,000-step trajectory
replayable bit-for-bit. *What it gives:* a deterministic, attestable simulation with no nondeterministic
drift. *What it does not:* claim the simulation models real physics.

#### Applications on the workbench (downstream products, not siblings)

The Sibling Law scales from components to whole products: a standalone app imports the frozen cores + siblings
read-only via a path shim, without being a sibling or entering the suite count. In-repo examples:
`aegis_gate/` (a verifiable transfer & KYC agent over exact gates + `ration` + `quorum` + `tessera`; a **mock**
bank, 14 tests), `VeriSim/` (a verifiable simulation engine over `aether`/`fuel`/`tessera`/`stasis` that emits a
replayable Shard; proves the *test was real*, not that the model is *true*; 12 tests), `VeriVerse/` (a
verifiable procedural world/physics engine — deterministic integer terrain + content-addressed chunks,
Collatz feature provenance, signed chunk shards, stdlib viewer; a *scaffold* for a deterministic-and-verifiable
physics engine that competes on provable determinism, not render speed; 13 tests), `AetherPulse/` (a Stage-1
deterministic engine kernel — 3-D fixed-point rigid bodies + the L1/L2/L3 render seam + cross-language
conformance vectors a C++/Rust port must hash-match; 15 tests), and `AetherManifold/` (deterministic
Riemannian optimization on the Stiefel manifold — fixed-point tangent projection + integer retraction,
two-tier exact/approx, shadowing-Lyapunov observable; 10 tests). When you build
one, the same rules apply — decoupled, content-addressed, fail-closed, and explicit about non-claims. **Native ports** (C++/Rust for performance, e.g. `AetherPulse/`) follow a stricter rule: the Python stays the
*reference / source of truth*, and the native build is validated against it via **conformance vectors**
(input → expected state hashes) — the native code reproduces the reference's hashes bit-for-bit or fails;
it never defines semantics, lives in its own folder, and does not import the workbench.

#### Use case — evolving the rules without breaking the chain of custody

A rule in `elenchus` or a threshold in `fuel` turns out wrong. Instead of an unaudited code edit, `polity`
runs a `quorum` vote among pinned governors; a ratified amendment mints a new constitution version bound to
the prior by content hash. Downstream, `elenchus`/`fuel` enforce against the newly-active ruleset hash. The
whole evolution is itself replayable. *Bound:* proves the vote and the lineage, never that the new rule is
better.


---

## 7. Acknowledgement (machine-parseable)

```
ACK: deterministic-capture=enforced  privilege-pep=required  integrity!=truth=acknowledged
     stdlib-core=required  crypto=optional-tiered  parity=must-hold  fail-closed=required
     done=preflight-green+verification-record  status=earned-not-pasted
```

Proceed under these constraints.
