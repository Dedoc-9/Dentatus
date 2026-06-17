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
