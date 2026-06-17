# Dentatus/Chronicle — a verifiable-computation workbench

A set of small, deterministic, content-addressed components for making consequential automated decisions
**auditable and reproducible by construction**. Stdlib-only cores; optional `cryptography` for asymmetric
attestation. One idea runs through all of it: a tiny deterministic core (canonical bytes → content hash),
plus one discipline — **capture nondeterminism at the boundary, never fake it away.** Everything else
(replay court, signed verdicts, policy enforcement, separation of powers) is that idea wearing different
hats. Philosophy: *build for extraction, not just execution.*

## Start here

[`chronicle/`](chronicle/README.md) — the foundational piece: a tamper-evident "flight recorder + replay
court" for any consequential decision. Replays a decision bit-for-bit, proves the record and the rules
were not altered, and refuses unsafe ones at write time.

```bash
cd chronicle && PYTHONHASHSEED=0 python3 demo_policy.py
```

## The four components

| Component | What it is | Run |
|---|---|---|
| [`chronicle/`](chronicle/README.md) | verifiable decision recorder — content-addressing, hash chaining, HMAC/Ed25519 attestation, determinism capture, pluggable append-only storage | `PYTHONHASHSEED=0 python3 demo_policy.py` |
| [`llm_toolkit/`](llm_toolkit/README.md) | the pattern lifted onto LLM orchestration — captures prompt/tokens/logprobs/seed at the model boundary so agent runs replay bit-for-bit; Ed25519 precommitted guardrails, fail-closed | `PYTHONHASHSEED=0 python3 demo_agent_pipeline.py` |
| [`guard_server/`](guard_server/README.md) | a localhost **Policy Enforcement Point** — server-pinned policy + signing key behind a boundary the agent calls but cannot weaken; returns signed, request-bound verdicts | `PYTHONHASHSEED=0 python3 demo_guard_server.py` |
| [`integration/`](integration/README.md) | the **coupled full stack** — capture + PEP + ledger, with a separation-of-powers proof, plus a coupled-vs-uncoupled parity proof | `PYTHONHASHSEED=0 python3 demo_integration.py` |

All four refuse to run without `PYTHONHASHSEED=0` (reproducible hashing is the premise of the replay
court). Test suites: **52 unit tests total** (chronicle 19, llm_toolkit 18, guard_server 10, integration 5).

## Coupled and uncoupled — both, on purpose

The workbench deliberately shows both architectural styles, and proves they are interchangeable:

- **Uncoupled** (vendored, standalone): `chronicle/` and `llm_toolkit/` each carry their own copy of the
  primitives — either lifts out as an independent repo, at the cost of small duplication.
- **Coupled** (shared, imported): `guard_server/` and `integration/` import `llm_toolkit` — DRY, single
  source of truth, components travel together.

[`integration/parity_proof.py`](integration/parity_proof.py) runs the coupled (imported) and uncoupled
(vendored) primitives over a battery of awkward payloads and asserts byte-identical `canonical_bytes`,
`state_hash`, `source_hash`, and an identical Ed25519 signature:

```
RESULT: PARITY HOLDS — extraction is lossless; coupling is convenience, not correctness.
```

So import-vs-vendor is purely a packaging choice; no content address changes either way. A test fails
loudly if the two ever diverge — "build for extraction" made checkable.

## The one boundary that runs through every component

**Integrity is not truth.** These tools prove a record is *unforged, exactly reproducible, and
rule-faithful*, and (with the PEP) that an authorization was *genuinely granted under a pinned policy*.
They do **not** claim the underlying decision — a refund, a loan, a model's answer — was correct, fair, or
wise. That narrow, honest claim is exactly what makes the records usable to an auditor or a court.

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
| [`OVERVIEW.md`](OVERVIEW.md) | honest technical overview of the Dentatus lineage |
| [`docs/LESSONS.md`](docs/LESSONS.md) | design retrospective (Dentatus → chronicle) |
| [`docs/archive/`](docs/archive/) | archived Reality Engine / Citadel implementation |
| `Game1/` | archived game client (separately-connected folder) |
| `LICENSE`, `DUAL_LICENSE.md` | licensing |

**Primary architect:** Daniel J. Dillberg — bigdilly95@gmail.com
**License:** dual-licensed (AGPL-3.0 open track / commercial closed track) — see `DUAL_LICENSE.md`.
