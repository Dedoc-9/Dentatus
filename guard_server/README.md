# guard_server — a localhost Policy Enforcement Point (server-side LLM guardrails)

The server-side companion to [`../llm_toolkit`](../llm_toolkit/README.md). Where `agent_guard.py` runs
guardrails *inside the agent's process*, this moves the policy and the signing key **behind a boundary the
agent calls but cannot control**. The agent submits a request; the server evaluates it against one pinned
policy and returns a **signed verdict bound to the request hash**.

The security property, stated precisely:

> The agent cannot obtain a valid **allow** for a request the policy would deny, and cannot forge any
> verdict without the server's key. The enforced **policy version is server-pinned and provable.**

## Run it

```bash
PYTHONHASHSEED=0 python3 demo_guard_server.py        # allow / deny / preflight / tamper / no-forge
PYTHONHASHSEED=0 python3 tests/test_guard_server.py  # 10 unit tests
```

The demo starts the PEP on a loopback port, then shows: a clean refund **allowed** (verdict verifies and
is request-bound), PII and low-alignment outputs **denied** by the server, an injection prompt denied at
**pre-flight** before any model call, an agent **flipping a deny to allow** caught by signature check, and
an agent's **self-signed allow rejected** because it lacks the server key.

## Files

| File | Role |
|---|---|
| `policy.py` | source-hashed, version-pinned policy; deterministic `evaluate(stage, payload)` (pre-flight injection check, post-flight PII + alignment threshold) |
| `policy_server.py` | stdlib `http.server` PEP holding the Ed25519 key + pinned policy; `POST /evaluate` returns a signed, request-bound verdict; `GET /policy` publishes version/hash/public key |
| `client.py` | agent-side stub (`urllib`): submit a request, `verify_verdict` (signature + request binding), `is_allowed` |
| `demo_guard_server.py` | the end-to-end scenario above |
| `tests/test_guard_server.py` | policy, verdict-binding, tamper/forge, and live-HTTP tests |

## What it is — and is NOT (honest scope)

**Is:** out-of-process enforcement, a server-pinned `policy_version` + `policy_hash`, and signed verdicts
bound to the exact request. With Ed25519 a third party verifies a verdict from the public key alone and
cannot forge one. Verdicts are deterministic (no clock), so they can be stored in a chronicle/llm_toolkit
ledger and re-verified later.

**Is NOT:** OS/container/network isolation, caller authentication, rate limiting, or TLS. This is a
reference PEP on `127.0.0.1`. Production adds those layers — the cryptographic guarantee above holds
regardless of them. And as everywhere on this workbench: **integrity is not truth.** A signed `allow`
proves the output cleared the pinned policy at that instant, not that the underlying decision was correct.

## Dependency

Reuses `../llm_toolkit` for canonicalization and the Ed25519/HMAC primitives (it is that toolkit's
server-side half, not a standalone island). Falls back to HMAC with a loud warning if `cryptography` is
absent — but third-party verification then requires holding the secret.
