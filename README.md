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

## The five components

| Component | What it is | Run |
|---|---|---|
| [`chronicle/`](chronicle/README.md) | verifiable decision recorder — content-addressing, hash chaining, HMAC/Ed25519 attestation, determinism capture, pluggable append-only storage | `PYTHONHASHSEED=0 python3 demo_policy.py` |
| [`llm_toolkit/`](llm_toolkit/README.md) | the pattern lifted onto LLM orchestration — captures prompt/tokens/logprobs/seed at the model boundary so agent runs replay bit-for-bit; Ed25519 precommitted guardrails, fail-closed | `PYTHONHASHSEED=0 python3 demo_agent_pipeline.py` |
| [`guard_server/`](guard_server/README.md) | a localhost **Policy Enforcement Point** — server-pinned policy + signing key behind a boundary the agent calls but cannot weaken; returns signed, request-bound verdicts | `PYTHONHASHSEED=0 python3 demo_guard_server.py` |
| [`integration/`](integration/README.md) | the **coupled full stack** — capture + PEP + ledger, with a separation-of-powers proof, plus a coupled-vs-uncoupled parity proof | `PYTHONHASHSEED=0 python3 demo_integration.py` |
| [`assay/`](assay/README.md) | the **meta-audit layer** — makes "correct / fair / wise" judgments first-class, recomputable (metrics) or attributable (signed opinions), tamper-evident | `PYTHONHASHSEED=0 python3 demo_assay.py` |

All five refuse to run without `PYTHONHASHSEED=0`. Test suites total **62 unit tests** (chronicle 19,
llm_toolkit 18, guard_server 10, integration 5, assay 10).

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

Read [`AGENTS.md`](AGENTS.md) first — the system-context & handoff contract every change must honor (determinism, privilege-PEP, integrity≠truth, stdlib core + tiered crypto, the 78-test verification contract).

## Background / lineage

Distilled from **Dentatus** (the "Reality Engine"). For an honest, de-inflated account of that project,
read [`OVERVIEW.md`](OVERVIEW.md); for the design discipline behind the whole arc, see
[`docs/LESSONS.md`](docs/LESSONS.md). The full legacy implementation is archived under
[`docs/archive/`](docs/archive/); the legacy game client is in `Game1/` (a separately-connected folder).

## Repository map

| Path | What it is |
|---|---|
| [`chronicle/`](chronicle/README.md) | **active** — verifiable decision recorder |
| [`llm_toolkit/`](llm_toolkit/README.md) | **active** — reproducible-by-construction LLM orchestration |
| [`guard_server/`](guard_server/README.md) | **active** — localhost Policy Enforcement Point |
| [`integration/`](integration/README.md) | **active** — coupled full stack + parity proof |
| [`assay/`](assay/README.md) | **active** — meta-audit layer for correct/fair/wise |
| [`OVERVIEW.md`](OVERVIEW.md) | honest technical overview of the Dentatus lineage |
| [`docs/LESSONS.md`](docs/LESSONS.md) | design retrospective (Dentatus → chronicle) |
| [`docs/archive/`](docs/archive/) | archived Reality Engine / Citadel implementation |
| `Game1/` | archived game client (separately-connected folder) |
| `LICENSE`, `DUAL_LICENSE.md` | licensing |

**Primary architect:** Daniel J. Dillberg — bigdilly95@gmail.com
**License:** dual-licensed (AGPL-3.0 open track / commercial closed track) — see `DUAL_LICENSE.md`.
