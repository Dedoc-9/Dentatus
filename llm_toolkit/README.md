# llm_toolkit — reproducible-by-construction LLM orchestration

A standalone toolkit on the Dentatus/Chronicle workbench that makes LLM-driven agent actions **fully
auditable and bit-for-bit reproducible**, and binds them with **precommitted, signed safety guardrails**.
Stdlib-only core; optional `cryptography` for asymmetric attestation. Philosophy: *build for extraction,
not just execution.*

## Why

LLM calls are the most non-deterministic step in any pipeline — temperature sampling, GPU floating-point
reassociation across hardware, server-side model swaps, variable latency. Enterprise workflows (legal
compliance, automated underwriting, medical triage routing) still need every model-driven action to be
auditable, reproducible, and bound by safety/fairness rules fixed *before* deployment. This toolkit gets
there not by making the model deterministic, but by **capturing** its output at the system boundary and
locking it into a verifiable ledger.

## Run it

```bash
PYTHONHASHSEED=0 python3 demo_agent_pipeline.py     # AI refund agent: live, replay, tamper, guard, profile
PYTHONHASHSEED=0 python3 tests/test_llm_toolkit.py  # 18 unit tests
```

`demo_agent_pipeline.py` **refuses to run** without `PYTHONHASHSEED=0` — reproducible hashing is the
premise of the replay court. The demo shows: a valid refund sealed + verified, a corrupted captured prompt
caught at the exact step, an unsafe generation (PII leak / low alignment) blocked fail-closed, and a
profile contrasting the canonical-hashing layer (~1 ms) against LLM flight time (~140 ms) — the integrity
layer is ~0.01× the model call.

## The four files

| File | Role |
|---|---|
| `agent_core.py` | deterministic content-addressed agent state machine: float-stable canonicalization, hash chaining, HMAC attestation, `audit_chain` replay court, `Profiler`, `PYTHONHASHSEED` guard |
| `agent_capture.py` | `LLMCapture` seam — records prompt, system, model, seed, response tokens, logprobs, fingerprint at live time; replays them at audit time with **no live model / GPU**. Includes an isolated `MockLLMClient` (swap for a thin openai/anthropic wrapper of the same dict shape) |
| `agent_guard.py` | precommitted `Guardrail`: constraints (forbidden-PII regex, alignment-score threshold) source-hashed into a `guardrail_hash`, signed with Ed25519 (HMAC fallback). Fail-closed `clamp` refuses the commit + rolls back on violation |
| `demo_agent_pipeline.py` | end-to-end AI Customer-Support Refund Agent harness |

## What it proves — and what it does not

For each transition the replay court re-derives, in order: chain link, seq continuity, ruleset binding
(transition + guard source hash unchanged), bit-exact replay of the captured call, guardrail re-check, and
the committed-hash + signature. A tampered prompt/token/logprob, a reordered or deleted step, a swapped
ruleset, or a wrong signing key each fails at the exact step.

**Integrity is not truth.** This guarantees the *record* — the exact prompt the model received, the exact
tokens it produced, the guardrails enforced at that instant — is 100% untampered and cryptographically
reproducible. It does **not** claim the model's output was correct, smart, or safe in any absolute sense.
That narrow, honest claim is what makes it usable to an auditor or a court.

## Reproducibility & honest scope

The seam, not the model, carries determinism: route every model call through `LLMCapture` and the
surrounding agent logic is untouched. `verify_replay_determinism()` flags any model call you forgot to
route. This is a reference implementation — no persistence/access-control/scale hardening — and it inherits
chronicle's float/iteration-order/clock determinism defenses. See `../chronicle/RELATED_WORK.md` for the
prior art these primitives stand on, and `../docs/LESSONS.md` for the design discipline behind them.
