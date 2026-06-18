# Dentatus/Chronicle — a verifiable-computation workbench

A set of small, deterministic, content-addressed components that make consequential automated decisions
**auditable and reproducible by construction** — and then audit the *audits themselves*. The cores are
standard-library only; `cryptography` is an optional add-on for asymmetric (Ed25519) attestation, never a
hard dependency of a core path.

The whole workbench reduces to **one idea and one discipline**. The idea: a tiny deterministic core —
*canonical bytes → SHA-256 content hash* — so a record's identity *is* its content and cannot be changed
without changing its address. The discipline: **capture nondeterminism at the boundary, never fake it
away** — clocks, RNGs, GPU float drift, model calls, and external reads are recorded as inputs at write
time and replayed at audit time, so a workflow re-runs bit-for-bit on any machine. Everything else — the
replay court, signed verdicts, out-of-process policy enforcement, the quality meta-audit, topology gates,
match forensics, portable proof-shards, a bounded integer VM, reasoning-trace interrogation, exact integer
consensus, ruleset governance, and a fixed-point physics manifold — is that one idea wearing a different hat.

Two principles keep it honest. *Build for extraction, not just execution:* every component is decoupled
enough to lift out and stand alone (a parity proof guarantees it). And *integrity is not truth:* these
tools prove a record is unforged, exactly reproducible, and rule-faithful — never that the underlying
decision was correct, fair, or wise.

In practice this changes your role on an AI project. Treat the LLM as a high-velocity but untrusted
*engine* and the frozen cores as a rigid *chassis*: it generates fast while the workbench — not your
attention — tracks determinism, structural purity, privilege isolation, and resource budgets.
`integration/preflight_check.py` runs the whole 26-suite contract and `selfaudit/` proves the cores
have not drifted, so your review shifts from line-by-line diff-reading to the one thing a machine
cannot certify: whether the new logic is actually *right*. (Honest bound: it catches the regressions
its checks cover, not arbitrary badness — integrity is not truth.)

### The families, at a glance

Twenty-four components group into a few families, each a different hat on the one idea. **The audit core**
(`chronicle`, `llm_toolkit`) records and replays. **Governance & isolation** (`guard_server`, `polity`,
`pact`, `quorum`) decide *who may act* and *what becomes true* across parties. **The Axiom triad**
(`tessera` → `fuel` → `elenchus`) proves *the log is real*, *the machine ran*, and *the trace followed the
declared rules* — three layers of a single offline-replayable proof. **The Collatz pair** (`syracuse`,
`crucible`) supplies a hardware-invariant integer workload and a deterministic adversary that forges the
hardest seeds to break it. **Real-time & physics** (`lockstep`, `aether`, `manifold`) separate truth-rate
from frame-rate and harden manifold geometry in fixed-point integers. **The boundary** (`stasis`) admits the
messy real world — canonicalizing inputs, classifying drift-vs-lie, batching verification. Every one is
decoupled enough to lift out and stand alone, and every one states its own honest bound.

### The 2D Attestation Lattice — bounding an untrusted runtime on two axes

Deploying Sibling 13 (`quorum/`) alongside `pact/` composes a **2D attestation lattice** for an untrusted
LLM runtime. The **lateral** axis is multi-witness agreement at a tick `t` (k-of-n independently-keyed
nodes must produce the *same* exact 256-bit state hash); the **temporal** axis is covenant continuity
across `t → t+1` (`pact` binds each round's certified state to the prior). An action is admissible only if
it survives **both** axes — reproduces a local invariant *vertically* and matches independent witnesses
*horizontally* — or it is refused fail-closed. This is **bounded authority, not a "cage":** it does not
make a model safe; it strips a single jailbroken or hallucinating instance of the power to act alone. Four
classes of leverage follow for an enterprise putting an agent behind real authority:

- **Containment of autonomous financial/operational agents.** To force an unauthorized action (a B2B wire,
  an infra mutation, a record update), an attacker must *both* jailbreak the local model *and* get ≥k
  independent, separately-keyed witnesses to agree on the same malicious hash in the same round. A local
  invariant breach fails vertically; a cross-instance divergence fails laterally. (Honest bound: if the
  witnesses are not actually independent — same operator, shared image — the protection collapses toward a
  single node; independence is a *trust input*, not a proven property.)

- **Catching the silent-hallucination / drift exploit.** Because the tally is exact integer counting with
  no float epsilon, agreement is binary (`h_i == h_j` or not). Run N independently-seeded paths — or
  *different* models (e.g. node 1 Claude, node 2 another vendor, node 3 a local GGUF) — as witnesses; if one
  suffers a reasoning slip or a float-reassociation drift, its hash forks from the majority and the lattice
  isolates the exact node and input and refuses the commit (rollback = decline to adopt) before it reaches a
  production store. (Honest bound: this catches divergence *among* witnesses, not an error they all share.)

- **Tamper-evidence against insider/log tampering.** Every state change sits in a grid where rows need a
  k-quorum of independent signatures and columns need unbroken `pact` covenant. A rogue admin with root can
  still *destroy* data, but cannot silently *rewrite history* undetectably: altering one byte breaks the
  cross-attested chain, and a third party holding only the pinned public keys can verify the whole 2D trail.
  This is **tamper-evident, not tamper-proof**, and **verifiable under the pinned-key assumption** — not
  "100% certainty," and never proof the decision itself was right.

- **Ghost radar — early warning of systemic model drift.** Rather than discard the outvoted minority,
  `quorum` keeps it as a dissent *ghost* and `ghost.py` accumulates it across rounds into a slow pressure
  `S_{t+1} = αS_t + (1−α)g_t`. When an upstream vendor quietly ships a weight update, honest nodes begin
  registering dissenting hashes and `S_t` rises — a measurable drift signal before a hard failure. (Honest
  bound: `S_t` is a *sensor, never a gate*; a rising ghost flags disagreement, not which side is correct.)

The operating posture this enables: let the LLM generate and orchestrate at maximum velocity while the
lattice — not your attention — holds the containment boundary, so you and the model spend review on whether
the logic is *right* rather than on diffing for hidden regressions. The standing caveat survives intact:
consensus is a stronger, fully-attributable claim than a single integrity — and still **not truth** (a
colluding ≥k majority agrees on a falsehood just as cleanly).

**Author:** Daniel J. Dillberg · **Contact:** [bigdilly95@gmail.com](mailto:bigdilly95@gmail.com)
**License:** dual-licensed (AGPL-3.0 open track / commercial closed track) — see [`DUAL_LICENSE.md`](DUAL_LICENSE.md).

## Start here

[`chronicle/`](chronicle/README.md) — the foundational piece: a tamper-evident "flight recorder + replay
court" for any consequential decision. Replays a decision bit-for-bit, proves the record and the rules
were not altered, and refuses unsafe ones at write time.

```bash
cd chronicle && PYTHONHASHSEED=0 python3 demo_policy.py
```

## The twenty-four components

| Component | What it is | Run |
|---|---|---|
| [`chronicle/`](chronicle/README.md) | verifiable decision recorder — content-addressing, hash chaining, HMAC/Ed25519 attestation, determinism capture, pluggable append-only storage | `PYTHONHASHSEED=0 python3 demo_policy.py` |
| [`llm_toolkit/`](llm_toolkit/README.md) | the pattern lifted onto LLM orchestration — captures prompt/tokens/logprobs/seed at the model boundary so agent runs replay bit-for-bit; Ed25519 precommitted guardrails, fail-closed | `PYTHONHASHSEED=0 python3 demo_agent_pipeline.py` |
| [`guard_server/`](guard_server/README.md) | a localhost **Policy Enforcement Point** — server-pinned policy + signing key behind a boundary the agent calls but cannot weaken; returns signed, request-bound verdicts | `PYTHONHASHSEED=0 python3 demo_guard_server.py` |
| [`integration/`](integration/README.md) | the **coupled full stack** — capture + PEP + ledger, with a separation-of-powers proof, plus a coupled-vs-uncoupled parity proof | `PYTHONHASHSEED=0 python3 demo_integration.py` |
| [`assay/`](assay/README.md) | the **meta-audit layer** — makes "correct / fair / wise" judgments first-class, recomputable (metrics) or attributable (signed opinions), tamper-evident | `PYTHONHASHSEED=0 python3 demo_assay.py` |
| [`manifold/`](manifold/README.md) | **topology-gated commits** — state as a graph; the commit gate is *exact* connectivity/bridges, the Fiedler λ₂ spectrum is a *captured* margin (never in the hash) | `PYTHONHASHSEED=0 python3 demo_manifold.py` |
| [`anti_cheat/`](anti_cheat/README.md) | **server-authoritative match forensics** — exact occlusion gate refuses impossible (wallbang/teleport) hits; culling defeats wallhacks; sealed, replayable ticks | `PYTHONHASHSEED=0 python3 demo_anti_cheat.py` |
| [`glitch/`](glitch/README.md) | **deterministic state-space explorer** — finds latent sequence-dependent invariant bugs; dedups states by content hash; shrinks to a minimal, signed, replayable counterexample | `PYTHONHASHSEED=0 python3 demo_glitch.py` |
| [`dini/`](dini/README.md) | **hyperbolic novelty compass** — embeds the execution DAG in the Poincare disk; a captured `dini_distance` sensor gives an agent novelty-seeking + drift-anomaly signals (never a gate; **dual-use** — see its README's responsible-use note) | `PYTHONHASHSEED=0 python3 demo_dini.py` |
| [`selfaudit/`](selfaudit/README.md) | **the workbench evaluates itself** — determinism/parity/frozen-core/Sibling-Law checks sealed via `assay`, replayed by the assay court; emits a `workbench_H` baseline | `PYTHONHASHSEED=0 python3 evaluate.py` |
| [`wobble/`](wobble/README.md) | **verifiable synthetic-gene design** — protein is the content identity (synonymous codons collapse); exact GC/homopolymer/restriction gate; CAI as a captured observable | `PYTHONHASHSEED=0 python3 demo_wobble.py` |
| [`ration/`](ration/README.md) | **deterministic resource clamps** — gates on exact integer *logical steps* (hardware-invariant); physical CPU/memory cost is a captured observable; fail-closed `QuotaBreached` | `PYTHONHASHSEED=0 python3 demo_ration.py` |
| [`stride/`](stride/README.md) | **epistemic state-transport** — receiver verifies its environment fingerprint exactly matches the sender (`EnvironmentMismatch` else); network telemetry captured; replay without re-transmit | `PYTHONHASHSEED=0 python3 demo_stride.py` |
| [`pact/`](pact/README.md) | **multi-agent cross-attestation covenant** — pinned peer registry; binds each agent's state hash to the prior agent's; multi-chain audit isolates the exact deviating agent (no blockchain) | `PYTHONHASHSEED=0 python3 demo_pact.py` |
| [`quorum/`](quorum/README.md) | **exact integer consensus** — k-of-n independently-keyed witnesses must agree on the same content hash; equivocation caught, dissent kept as a ghost; `lattice.py` binds it to `pact` into a 2D (lateral×temporal) attestation lattice | `PYTHONHASHSEED=0 python3 demo_quorum.py` |
| [`lockstep/`](lockstep/README.md) | **what becomes truth at frame rates** — decouples an integer, content-addressed truth-tick stream from the render rate; 240fps frames are exact interpolated *observables*, never gated; revert-to-last-valid-hash rollback converges clients | `PYTHONHASHSEED=0 python3 demo_lockstep.py` |
| [`syracuse/`](syracuse/README.md) | **Collatz map as integrity≠truth** — pure-integer orbits, content-addressed and replayable; verify any trajectory exactly, refuse the conjecture structurally; a hardware-invariant reference workload for `ration`/`lockstep` | `PYTHONHASHSEED=0 python3 demo_syracuse.py` |
| [`tessera/`](tessera/README.md) | **portable replayable proof shard** — `{seed, rule, path_hash}` a stranger replays offline to confirm a deterministic computation's exact process history; trustless replay, signed authorship, immutable lineage, exact divergence locator | `PYTHONHASHSEED=0 python3 demo_tessera.py` |
| [`crucible/`](crucible/README.md) | **reverse-Collatz adversary** — grows the pre-image tree upward to forge deterministic hard seeds (stopping time = reverse depth) and fires them at `ration`/`tessera`; controlled chaos, no RNG; content-addressed difficulty manifest | `PYTHONHASHSEED=0 python3 demo_crucible.py` |
| [`fuel/`](fuel/README.md) | **the Absolute Integer Standard** — deterministic bounded-execution VM; halting is exact integer *fuel* (no float gas), fail-closed on out-of-fuel/div0; every run mints a replayable `tessera` shard | `PYTHONHASHSEED=0 python3 demo_fuel.py` |
| [`elenchus/`](elenchus/README.md) | **reasoning-trace interrogator** — replays a claimed derivation against a pinned exact rule-set; names the exact FABRICATED / GAP / UNKNOWN step; verdict is itself a `tessera`. Checks footprints vs declared rules — not the model's mind, not truth | `PYTHONHASHSEED=0 python3 demo_elenchus.py` |
| [`polity/`](polity/README.md) | **deterministic governance** — governors vote (via `quorum`) to ratify a new ruleset version; mints a content-addressed constitution lineage so frozen rulesets can evolve without breaking custody. Proves the vote, never the wisdom | `PYTHONHASHSEED=0 python3 demo_polity.py` |
| [`stasis/`](stasis/README.md) | **the boundary layer** — Iron Canon (strict canonical bytes, rejects ambiguous/float types), Divergence Ledger (gate-vs-observable: lie→FAIL, drift→WARN), Lazy Lattice (Merkle batch + on-demand proofs). Hardens the order zone against real-world chaos | `PYTHONHASHSEED=0 python3 demo_stasis.py` |
| [`aether/`](aether/README.md) | **hardened integer manifold** — DVSM geometry in fixed-point integers (bit-exact, replayable); Stiefel auditor gates `E=‖WᵀW−I‖²_F` under a declared epsilon and deterministically self-retracts (Gram-Schmidt), logging recovery. A 1,000,000-step spinning top with no nondeterministic drift | `PYTHONHASHSEED=0 python3 demo_aether_physics.py` |

All twenty-four refuse to run without `PYTHONHASHSEED=0`. Test suites total **284 unit tests across 26 suites**
(chronicle 19 + hardware 5, llm_toolkit 18, guard_server 10 + isolated_pep 11, integration 5, assay 10,
manifold 9, anti_cheat 9, glitch 8, dini 9, selfaudit 11, wobble 15, ration 8, stride 6, pact 7, quorum 17, lockstep 13, syracuse 15, tessera 12, crucible 10, fuel 12, elenchus 11, polity 8, stasis 15, aether 11) — `integration/preflight_check.py` runs them all and prints `[FOUNDRY VERIFIED]` only if green.

## The Sibling Law — how the workbench grows

The cores (`chronicle`, `llm_toolkit`) are **frozen**. New capability is never added by editing them; it
is added as a **new sibling component** that *imports* the frozen primitives read-only — exactly how
`guard_server`, `integration`, `assay`, and `manifold` were built. The rule:

1. **Never edit a frozen core to add a feature.** If you need new behavior, add a sibling that composes the
   existing `sign()/verify()`, canonicalization, capture seam, and recorder. (`chronicle` and `llm_toolkit`
   each vendor their own primitives so they stay independently extractable; siblings import them.)
2. **A new component is "in" only when** its own test suite passes, it is added to
   `integration/preflight_check.py`, and the cores' tests + `parity_proof.py` still pass unchanged. A core
   whose hashes shifted means you edited something you shouldn't have.
3. **Determinism boundary holds at the seam.** Anything nondeterministic a new component introduces (a
   float eigensolver, a clock, a model call) goes through the capture seam or is computed with exact
   arithmetic — never into the commit hash. (`manifold` is the worked example: the *gate* is exact integer
   topology; the Fiedler λ₂ *spectrum* is a captured observable.)

This is "build for extraction, not just execution" stated as a growth rule: the tool stays a closed,
immutable instrument while the workbench around it keeps gaining purpose-built parts.

## Three structural guarantees an LLM or agent framework can't give you alone

A model and a standard agent framework, by themselves, can't provide these — not because they're badly
built, but because the guarantees live *outside* the model, at the host boundary.

**1. Host-enforced, fail-closed invariants.** Standard LLM safety is *soft*: prompt rules or an auxiliary
classifier that a jailbreak, token fragmentation, or an exploit can route around. Here, safety is
host-side Python checked at the ledger's commit boundary. If a generation would breach a precommitted
rule — leak PII, escape an allow-listed folder, exceed a budget ceiling — the state machine **refuses to
commit and rolls back** (`InvariantViolation` / `TransitionRefused`), and the out-of-process PEP only
hands back signed, action-bound tickets the agent cannot forge. The model can hallucinate freely; it has
no *authority to commit* an action the gate rejects. (Honest bound: the gate catches exactly what the
precommitted predicate encodes — not unsafety you never wrote down.)

**2. Forensic replay over model drift.** A deployed agent is non-deterministic: an upstream vendor model
swap, an API-latency shift, or GPU float reassociation can make Monday's working prompt fail on Friday,
and ordinary logs only tell you *that* it failed. `capture.py` freezes the boundary — exact prompt, system
context, seed, token logprobs, generated strings — into the ledger. The Replay Court then re-runs the
whole workflow against that frozen telemetry, **without touching the live API or GPU**, so you debug agent
loops line-by-line with bit-perfect reproducibility. (The key move: you replay the *captured output*, so
you never need the model itself to be deterministic — which it isn't.)

**3. Non-repudiable, asymmetric audit trails.** Application logs (Splunk, Datadog, a database table) are
editable by an insider or a malicious local process covering its tracks. Here, every state transition is
linked into a SHA-256 hash chain sealed by a pluggable signer. With a **Tier 1 hardware token** (TPM /
YubiKey via PKCS#11) the private key never enters your program's memory at all; with **Tier 2** software
Ed25519 it is encrypted at rest and in RAM only during the signing call. Either way a jailbroken agent
cannot harvest the key to forge its own history, and a third party can verify the chain with only the
**public** key — turning passive text logs into independently checkable proofs. (Honest bound: this proves
the record was not altered after capture — not that the captured action was honest; see §3 of
[`AGENTS.md`](AGENTS.md) on the single-host capture-path limit. Integrity is not truth.)

## System architecture

```
                 [ UNTRUSTED MODEL LAYER ]
        LLM / agent — volatile, non-deterministic, jailbreak-prone
                            |
      prompts . tokens . logprobs . side-effects . proposed actions
                            v   (intercepted at the boundary)
  +----------------------------------------------------------------+
  |                CHRONICLE HOST-ENFORCEMENT LAYER                 |
  +----------------------------------------------------------------+
  |  (1) FAIL-CLOSED INVARIANTS  -> guard_server/ PEP + commit gate |
  |  (2) FORENSIC REPLAY         -> capture seam (capture.py)       |
  |  (3) ASYMMETRIC AUDIT        -> TPM / Ed25519 SHA-256 chaining  |
  +----------------------------------------------------------------+
                            |  commit ONLY if the gate allows
                            v
            [ IMMUTABLE, SIGNED LEDGER ]  -->  assay/ meta-audit
             chronicle . llm_toolkit            (correct / fair / wise:
             (record + Replay Court)             recomputed or attributed)
```

`integration/` wires these layers into one coupled stack and demonstrates *separation of powers* (the
recorder attests what happened; it cannot manufacture authorization). `parity_proof.py` proves the
primitives extract losslessly, so any layer lifts out as a standalone component unchanged.

## Launch sequence

One command verifies the whole workbench before you build on it. It runs the 26 suites **and** the parity
proof as subprocesses under `PYTHONHASHSEED=0`, and prints a green status **only if everything actually
passed**:

```bash
python3 integration/preflight_check.py
```

On success it *emits* the status below — this is earned output from a real run, **not** a banner you paste
by hand to assert state (asserting "26/26 green" without running it is exactly the integrity-theater this
project refuses):

```
[FOUNDRY VERIFIED]
  - 26/26 suites green; primitive parity holds (parity_proof.py)
  - Out-of-process policy clamps + tiered hardware signer present and tested
  - Cognitive modesty acknowledged: integrity != truth
Proceed with refactoring bounds secured.
```

If any check fails it prints `[FOUNDRY BLOCKED]` and exits non-zero. The rule (AGENTS.md §6): fix the
change, not the test.

## Using this in a project — when to run, and how to document for review

The workbench is only useful if verification happens at the right moments and the result is written down
in a form a second person can check. Below is the practice.

### When to run it

| Trigger | Run | A reviewer should see |
|---|---|---|
| Any change to decision logic, an invariant, a policy, or a signer | `python3 integration/preflight_check.py` | `[FOUNDRY VERIFIED]` + the old/new `ruleset_hash` (a rule change MUST be a deliberate, noted version bump) |
| Every pull request (CI gate) | `preflight_check.py` (non-zero exit fails the build) | green preflight attached to the PR |
| Model / policy / rubric version bump | the affected component's `demo_*` + `preflight_check.py` | new `policy_hash` / `guardrail_hash` recorded, and prior ledgers still replay |
| Before a release or deploy | full preflight + a fresh `demo` run | signer **tier + algo** in use (Ed25519 for third-party audit; HMAC is single-trust-domain only) |
| Re-verifying an archived ledger (drift / tamper sweep) | `PYTHONHASHSEED=0 python3 chronicle/court.py <ledger.json>` | `VERIFIED` (or the exact step it fails at) |
| Incident / dispute review | `court` replay of the ledger in question with the public key | bit-for-bit replay verdict, named failure point if any |

Rule of thumb: run it **before** you call a change done (it is the §6 verification contract in `AGENTS.md`),
and **again** whenever someone needs to trust a past record they did not personally produce.

### How to document the result for review

Hand the reviewer a short, self-contained record. An auditor needs only the **public** material — never a
private key or HMAC secret. Capture this alongside the change (PR description, audit log, or a file next to
the ledger):

```markdown
## Verification Record — <change / decision id> — <date>

- Command:            PYTHONHASHSEED=0 python3 integration/preflight_check.py
- Preflight result:   [FOUNDRY VERIFIED]  (26/26 suites + PARITY HOLDS)   # paste the real tail, or BLOCKED
- Replay Court:        VERIFIED — N records reproduced bit-for-bit       # or: REJECTED at seq <k> (<reason>)
- ruleset/policy hash: <before> -> <after>   (changed? yes/no; if yes, why + version)
- Signer:              algo=<ed25519|hmac-sha256>  tier=<1 hardware | 2 soft | 3 symmetric>
- Public key:          <hex>     # for independent third-party re-verification (Ed25519 only)
- Reviewed by:         <name>    Date: <date>
- Scope acknowledged:  integrity != truth — this attests the record + enforced rules are honest and
                       reproducible, NOT that the decision itself was correct, fair, or wise.
```

### What a reviewer should reject on

- `[FOUNDRY BLOCKED]` / any non-zero preflight — *fix the change, not the test.*
- A `ruleset_hash` / `policy_hash` that changed **without** a deliberate, documented version bump (logic
  was edited; prior attestations are now invalid — see the `source_hash` note below).
- `algo=hmac-sha256` where the record claims **third-party** auditability (HMAC is symmetric; the verifier
  can forge — only valid inside a single trust domain).
- A verdict verified against a key taken from the payload rather than a **pinned** key (`AGENTS.md §3`).
- A new core path that imports `cryptography` (or anything non-stdlib) with no fallback (`AGENTS.md §4`).

A green record proves the **record** is honest and reproducible and the declared rules were enforced. It
does not discharge the reviewer's own judgment about whether those rules were the *right* ones — that
decision stays human. (`assay/` can record *that* judgment too, signed and attributed, but still does not
make it true.)

## Compliance mapping — evidence toward, not "satisfaction of"

**This workbench does not "satisfy" SOC 2 or the EU AI Act, and any claim that code *instantly* does is
false.** SOC 2 Type II is an opinion a licensed CPA firm issues about an *organization's* controls operating
over a months-long period; the EU AI Act is a legal regime (risk management, data governance, technical
documentation, human oversight, conformity assessment) whose high-risk obligations reach full application on
**2 August 2026**. Code is, at most, *one technical control* contributing *evidence* toward specific
requirements. And `integrity ≠ truth`: a tamper-evident ledger proves the record is honest and reproducible,
**not** that the underlying decision complied with anything. With that stated plainly, here is the honest map.

### SOC 2 — Processing Integrity (PI1.1–PI1.5)

| Criterion (what it asks) | Evidence this workbench provides | What it does **not** cover |
|---|---|---|
| **PI1.1** processing requirements are defined | `ruleset_hash` binds the exact decision/invariant **source** into every receipt — "correct processing" is pinned and provable | writing/approving the business requirements themselves |
| **PI1.2** inputs are complete & valid | fail-closed invariants + the PEP's pinned policy reject malformed/out-of-policy inputs at the commit boundary | upstream data-quality / source-of-record controls |
| **PI1.3** processing is accurate; errors caught | the Replay Court re-derives each decision bit-for-bit; any drift/tamper fails at the exact step | correctness of the logic *itself* (integrity ≠ truth) |
| **PI1.4** output is delivered to the right place intact | signed, hash-chained receipts; third-party (Ed25519) verification of output integrity | transport/delivery infrastructure, access control |
| **PI1.5** records & logs retained and protected | append-only `JsonlStore` (fsync'd) + WORM adapter sketches; hardware/Ed25519 attestation resists tampering | a durable retention *policy*, backups, the production WORM store, key management |

Auditors trace the *full lifecycle* of transactions and look for a tamper-evident record of every event —
which is precisely what the ledger + Replay Court produce as evidence. They still need the observation
period, change management, access control, monitoring, and the auditor's opinion; none of those are code.

### EU AI Act — Article 12 (record-keeping / automatic logging / traceability)

Article 12 requires high-risk systems to **automatically record events over their lifetime**, with
traceability appropriate to purpose, supporting risk identification, post-market monitoring, and operation
monitoring. The workbench's ledger is a strong fit for that *logging* obligation:

| Article 12 asks for | Evidence this workbench provides |
|---|---|
| automatic, lifetime event logging | every state transition is recorded as a signed, hash-chained receipt |
| tamper-evident, retrievable records | content-addressed chain; the Replay Court detects any post-hoc edit |
| traceability to operation & changes | `ruleset_hash`/`policy_hash` version-bind the logic in force at each event |
| (biometric systems) period of use, inputs, persons involved | capture these as recorded inputs via the capture seam |

**It addresses the Article 12 *slice* only.** The Act also requires risk management (Art. 9), data
governance (Art. 10), technical documentation (Art. 11), transparency (Art. 13), human oversight (Art. 14),
accuracy/robustness (Art. 15), and a conformity assessment. This is record-keeping infrastructure, not
conformity.

### Non-claims (read before quoting any of the above)

- **Not a certification, not an attestation, not legal advice.** No SOC 2 report or AI Act conformity is
  conferred by running this code.
- **Nothing is "instant" or automatic.** Both frameworks require organizational process, an audit/assessment,
  and (for SOC 2 Type II) an observation period.
- **Integrity is not truth.** A perfectly sealed, replayable receipt can record a *non-compliant* decision.
  This proves the record's honesty, not the decision's compliance.
- **Verify the specifics yourself.** Criteria and article numbers/dates above are summarized from public
  sources (linked below) as of mid-2026; confirm against the authoritative texts with your auditor/counsel.

## Use case — a verifiable floor for the reproducibility crisis

Across computational science — biophysics, climate, ML — a published result is rarely bit-for-bit
reproducible by an external peer: hardware differences, silent float reassociation across library updates,
and missing provenance make it hard to even *re-run* a computation, let alone audit it. The workbench
attacks the **computational-reproducibility** half of that crisis directly. It does **not** address the
other half — whether the finding is *true* (see the boundary below); these are different problems and
conflating them is the mistake to avoid.

**1. Hard laws vs. fluid hypotheses, kept separate.** Physical invariants (mass/charge balance, integer
stoichiometry, topological connectivity, an exact translation table) get tangled with speculative empirical
models in ordinary scripts, so a model tweak silently breaks an invariant. The **exact-gate / captured-
observable split** forces them apart: *gates* are the non-negotiable laws in exact integer/string logic
(`manifold` connectivity, `wobble` translation); *observables* are the model-dependent metrics frozen at
the boundary. A researcher can re-parameterize a speculative model freely without ever risking a silent
breach of a foundational invariant — the gate is unyielding, and *which* model produced a number stays on
the record.

**2. A forensics court for computational peer review.** Today a reviewer gets a PDF and a link to a messy
repo, and cannot tell whether a figure came from *that exact code on those exact inputs* or was nudged
afterward. Here every transition, seed, and rule version is locked into a content-addressed hash chain,
optionally sealed by a hardware signer. A reviewer drops the public receipt into the Replay Court
(`court.py`): it re-runs the workflow bit-for-bit, confirms the rules did not change mid-run (`source_hash`),
and shows the published output is the exact, untampered consequence of the *recorded* inputs. *Bound:* this
proves the **computation** is reproducible and unaltered — not that the model, assumptions, or conclusion
are *correct*.

**3. High-velocity AI co-piloting under regression control.** A lab can hand an LLM agent a long leash to
mutate sequences or run optimization loops fast, because `selfaudit` continuously proves the workbench's own
structural laws against a pinned `workbench_H` baseline and the host-side gates fail closed: a one-character
serialization drift or a breached biochemistry constraint is caught, logged, and rolled back. *Bound:*
`selfaudit` catches **core drift** plus the suite's regressions; it does not catch a logic bug in new code
that still passes every check, and the rollback enforces only the precommitted predicate.

**The honest leap.** This shifts a digital scientific claim from "trust our methods text" to "verify our
frozen execution trail" — a **checkable floor** for computational integrity: reproducible, tamper-evident,
provenance-complete, so reviewers stop chasing vanished reproducibility. It is a *floor, not a ceiling*: a
bit-perfectly reproducible result can still be wrong science. Integrity is not truth.

## Use case — orchestration: resource, transport, and multi-agent accountability

These layers extend the same primitive — *canonical bytes → content hash* — from a single machine onto
resource budgeting, cross-machine migration, multi-party agreements, and multi-witness agreement. Each
keeps the exact-gate / captured-observable split and states its bound.

**Hardware-invariant resource budgets (`ration/`).** OS timeouts and cgroups key off the system clock, so
an autonomous loop or a `glitch/` fuzzer fails on a slow box and passes on a fast one — breaking
reproducibility. `ration` gates on **exact integer logical steps** (iterations, tokens, mutations, nodes)
against a pinned ceiling; a runaway loop is refused fail-closed (`QuotaBreached`), and an audit on a
decade-old laptop resolves the identical budget-exhaustion point as an enterprise array. Physical CPU/memory
cost is a captured observable, never the gate. *Bound:* it stops *logical* runaway and is bit-identical
across machines — it does **not** prevent an OS OOM-kill if the ceiling is set too loose.

**Verifiable cross-machine migration (`stride/`).** Moving a deterministic computation to cloud/edge via raw
snapshots leaks environment drift — a different library or arch forks the replayed path. `stride` makes the
receiver verify its **environment fingerprint exactly matches the sender's** (e.g. `selfaudit`'s
`workbench_H`) before accepting any state; a single byte of drift raises `EnvironmentMismatch` and the
inbound path refuses to start. Network telemetry is captured, so a post-migration audit replays from the
record without reopening a socket. *Bound:* proves *structural* environment identity and exact recorded
inputs — **not** transport security (wrap TLS externally) and **not** that the remote hardware is honest.

**Multi-agent accountability without a blockchain (`pact/`).** When independent agents or companies exchange
state, a malicious party can inject corruption that's impossible to attribute. `pact` has each agent verify
its peer against a **pinned registry** and sign a cross-attestation binding its new state hash to the
prior agent's — so a later injection or rule breach is isolatable to the **exact agent and link**, even when
that agent holds a legitimate key. *Bound:* non-repudiation **under the pinned-key assumption** and forensic
attribution; it does **not** force a peer to be honest, and there is no broadcast or consensus — a breach is
self-evident to anyone who verifies with the pinned keys, not "to the whole network." Not a blockchain.

**Multi-witness agreement — operational truth from many integrities (`quorum/`).** A single verified ledger
is honest but possibly *wrong*; nothing in it can catch an honest-but-mistaken or singly-compromised node,
because integrity-alone has no second opinion. `quorum` defines operational truth as the exact state hash
on which a **k-of-n quorum of independently-keyed, integrity-holding witnesses coincide** — exact integer
consensus on 256-bit hashes (no epsilon, so no arbitrary tolerance; the only declared cut is the threshold
`k`). Equivocation (a witness double-signing one round) is caught and named; the dissenting minority is
kept as a recorded *ghost*, never allowed to flip a certificate. `lattice.py` composes it with `pact` into
a 2D attestation lattice: each round must reach quorum (lateral) **and** the certified rounds must form an
unbroken covenant (temporal), with the two faults reported on separate axes. *Bound:* a quorum tally, not
asynchronous BFT (no leader, no liveness under partition); witness independence is a trust input, not
proven (no Sybil defense); a colluding ≥k majority certifies a falsehood — consensus is not truth either.

## The boundary that runs through everything — and one level up

**Integrity is not truth.** chronicle / llm_toolkit / guard_server / integration prove a record is
*unforged, exactly reproducible, and rule-faithful*, and that an authorization was *genuinely granted
under a pinned policy*. They do **not** claim the underlying decision was correct, fair, or wise.

`assay` then applies the same discipline to the *judgments about* those decisions. It still does not
certify truth — it makes a quality judgment a first-class, recomputable (metrics) or attributable (signed
opinion) artifact, so a claim of "correct / fair / wise" is itself auditable, not asserted.

`quorum` is the **other half of that boundary**. `integrity ⊬ truth` is one clause — a lone verified
record is honest and can still be wrong. `quorum` supplies the complementary clause that defines the
truth you *can* operate on: `Truth_op := the exact hash on which a k-quorum of independent integrities
coincide`. The two only close together — integrity is necessary per-witness; operational truth is the
emergent agreement across witnesses. It is **analytic** (the coincidence *is* the truth), not correspondent
(it is never checked against an external world), and it is honest about its ceiling: a colluding majority
agrees on a falsehood just as cleanly. Consensus is a stronger, fully-attributable claim than integrity —
and still not truth.
