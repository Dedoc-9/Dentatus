# Dentatus/Chronicle — a verifiable-computation workbench

A set of small, deterministic, content-addressed components for making consequential automated decisions
**auditable and reproducible by construction** — then for auditing the *audits themselves*. Stdlib-only
cores; optional `cryptography` for asymmetric attestation. One idea runs through all of it: a tiny
deterministic core (canonical bytes → content hash), plus one discipline — **capture nondeterminism at
the boundary, never fake it away.** Everything else (replay court, signed verdicts, policy enforcement,
quality assessment) is that idea wearing different hats. Philosophy: *build for extraction, not just
execution.*

## Start here

[`chronicle/`](chronicle/README.md) — the foundational piece: a tamper-evident "flight recorder + replay
court" for any consequential decision. Replays a decision bit-for-bit, proves the record and the rules
were not altered, and refuses unsafe ones at write time.

```bash
cd chronicle && PYTHONHASHSEED=0 python3 demo_policy.py
```

## The seven components

| Component | What it is | Run |
|---|---|---|
| [`chronicle/`](chronicle/README.md) | verifiable decision recorder — content-addressing, hash chaining, HMAC/Ed25519 attestation, determinism capture, pluggable append-only storage | `PYTHONHASHSEED=0 python3 demo_policy.py` |
| [`llm_toolkit/`](llm_toolkit/README.md) | the pattern lifted onto LLM orchestration — captures prompt/tokens/logprobs/seed at the model boundary so agent runs replay bit-for-bit; Ed25519 precommitted guardrails, fail-closed | `PYTHONHASHSEED=0 python3 demo_agent_pipeline.py` |
| [`guard_server/`](guard_server/README.md) | a localhost **Policy Enforcement Point** — server-pinned policy + signing key behind a boundary the agent calls but cannot weaken; returns signed, request-bound verdicts | `PYTHONHASHSEED=0 python3 demo_guard_server.py` |
| [`integration/`](integration/README.md) | the **coupled full stack** — capture + PEP + ledger, with a separation-of-powers proof, plus a coupled-vs-uncoupled parity proof | `PYTHONHASHSEED=0 python3 demo_integration.py` |
| [`assay/`](assay/README.md) | the **meta-audit layer** — makes "correct / fair / wise" judgments first-class, recomputable (metrics) or attributable (signed opinions), tamper-evident | `PYTHONHASHSEED=0 python3 demo_assay.py` |
| [`manifold/`](manifold/README.md) | **topology-gated commits** — state as a graph; the diamond-hard gate is *exact* connectivity/bridges, the Fiedler λ₂ spectrum is a *captured* margin (never in the hash) | `PYTHONHASHSEED=0 python3 demo_manifold.py` |
| [`anti_cheat/`](anti_cheat/README.md) | **server-authoritative match forensics** — exact occlusion gate refuses impossible (wallbang/teleport) hits; culling defeats wallhacks; sealed, replayable ticks | `PYTHONHASHSEED=0 python3 demo_anti_cheat.py` |

All seven refuse to run without `PYTHONHASHSEED=0`. Test suites total **96 unit tests across 9 suites**
(chronicle 19 + hardware 5, llm_toolkit 18, guard_server 10 + isolated_pep 11, integration 5, assay 10,
manifold 9, anti_cheat 9) — `integration/preflight_check.py` runs them all and prints `[FOUNDRY VERIFIED]` only if green.

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

One command verifies the whole workbench before you build on it. It runs the 7 suites **and** the parity
proof as subprocesses under `PYTHONHASHSEED=0`, and prints a green status **only if everything actually
passed**:

```bash
python3 integration/preflight_check.py
```

On success it *emits* the status below — this is earned output from a real run, **not** a banner you paste
by hand to assert state (asserting "78/78 green" without running it is exactly the integrity-theater this
project refuses):

```
[FOUNDRY VERIFIED]
  - 7/7 suites green; primitive parity holds (parity_proof.py)
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
- Preflight result:   [FOUNDRY VERIFIED]  (7/7 suites + PARITY HOLDS)   # paste the real tail, or BLOCKED
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

## The boundary that runs through everything — and one level up

**Integrity is not truth.** chronicle / llm_toolkit / guard_server / integration prove a record is
*unforged, exactly reproducible, and rule-faithful*, and that an authorization was *genuinely granted
under a pinned policy*. They do **not** claim the underlying decision was correct, fair, or wise.

`assay` then applies the same discipline to the *judgments about* those decisions. It still does not
certify truth — it makes a quality judgment a first-class, signed, (for metrics) recomputable record. You
cannot prove a decision was fair, but you can prove **nobody fudged the fairness report**, that a
correctness check really ran against the stated ground truth, and that a "this was wise" verdict is
attributable to a named reviewer under a named rubric. Integrity, all the way up.

## Coupled and uncoupled — both, on purpose

The workbench deliberately shows both architectural styles and proves they are interchangeable. The
dependency edges:

```
chronicle      (standalone — vendors its own primitives)
llm_toolkit     (standalone — vendors its own primitives)
guard_server  → llm_toolkit
integration   → llm_toolkit, guard_server
assay         → llm_toolkit
```

[`integration/parity_proof.py`](integration/parity_proof.py) runs the coupled (imported) and uncoupled
(vendored) primitives over a battery of awkward payloads and asserts byte-identical `canonical_bytes`,
`state_hash`, `source_hash`, and an identical Ed25519 signature: `PARITY HOLDS`. So import-vs-vendor is
purely a packaging choice — no content address changes either way, and a test fails loudly if the two
ever diverge.

## Notes that aren't obvious from the tree

These are the load-bearing design decisions a reader (or future maintainer) would otherwise trip on:

- **`PYTHONHASHSEED=0` is a discipline guard, not a load-bearing dependency of the hashing.** The content
  hashes use SHA-256 over `sort_keys` JSON, which is *not* affected by Python's randomized `hash()`. The
  demos refuse to run without the flag on purpose — to enforce the reproducible-invocation habit and match
  the documented run command — but chronicle's own integrity does not silently depend on it. (One real
  exception: `llm_toolkit`'s `MockLLMClient` uses `hash()` for pseudo-generation; that only affects demo
  *content*, never the ledger, because what gets hashed is the **captured** payload.)

- **Two cores are duplicated on purpose.** `chronicle` and `llm_toolkit` each carry their own copy of the
  canonicalization/signing primitives so either can be lifted out as an independent repo. That duplication
  is intentional, not drift — `parity_proof.py` is the regression guard that keeps the copies identical.

- **`source_hash` binds logic by its exact source text** (`inspect.getsource`). This is what proves "the
  rules didn't change" — but it also means reformatting, renaming, or even re-commenting a decision/guard
  function changes its hash and **invalidates prior attestations**. Treat rule functions as frozen once
  recorded; version them deliberately.

- **Float canonicalization is `format(x, ".12g")` — a 12-significant-digit floor.** Values that need more
  precision (money, high-precision scores) should be carried as integers / fixed-point, not floats, or
  they may canonicalize identically when they shouldn't.

- **The trust boundaries depend on *pinned* keys, never on keys taken from inputs.** `guard_server`'s
  separation-of-powers and `assay`'s anti-impersonation both work only because the verifier checks against
  a public key pinned in config (`TRUSTED_PEP_PUBKEY`, the trusted-assessor registry). Verifying against a
  key supplied in the payload would defeat the whole property.

- **HMAC fallback silently weakens the model from asymmetric to symmetric.** If `cryptography` is absent,
  signing degrades to HMAC (with a loud stderr warning): tamper-evidence survives, but third-party
  *verify-without-forge* is lost because the verifier then also holds the signing power. Install
  `cryptography` for any third-party-audit claim.

- **Demos write artifacts** (`ledger.json`, `ledger_store.jsonl`) into their own folders; these are
  gitignored. The PEP and integration demos start a loopback HTTP server on an ephemeral port.

- **Honest scope is repo-wide:** every component is a reference implementation, not a hardened product —
  no access control, throughput tuning, TLS, or scale testing. The genuinely hard part of any real
  deployment is making the decision logic deterministic; the capture seams lower that cost but do not
  remove it.

## Contributing / editing this repo

Read [`AGENTS.md`](AGENTS.md) first — the system-context & handoff contract every change must honor (determinism, privilege-PEP, integrity≠truth, stdlib core + tiered cryp