# integration — the coupled full stack (capture + server-side PEP + verifiable ledger)

Wires the three workbench components together and **proves the coupling choice is safe**:

```
llm_toolkit (capture + ledger)  +  guard_server (PEP)  +  content-addressed replay court
```

## Run it

```bash
PYTHONHASHSEED=0 python3 demo_integration.py     # authorize -> commit -> replay -> deny -> forge-rejected
PYTHONHASHSEED=0 python3 parity_proof.py         # coupled vs uncoupled primitives are byte-identical
PYTHONHASHSEED=0 python3 tests/test_integration.py
```

## What the integration demonstrates

Each refund's model output is authorized by the server-side **Policy Enforcement Point**; the server's
**signed verdict is captured into the transition** and committed to an llm_toolkit ledger only if the PEP
allowed. The replay court then re-derives every transition bit-for-bit **and** re-verifies each embedded
verdict against a pinned server key.

The headline result is **separation of powers**. Two independent keys exist: the *recorder* key attests
"this is what happened"; the *policy-server* key authorizes "this was permitted." An operator who
legitimately holds the recorder key — and even forges a self-signed `allow` — is still caught, because the
guard verifies verdicts against the **pinned** server public key it does not control:

```
D) SEPARATION OF POWERS ... chain signature is valid (real recorder key);
   auditor still runs the pinned PEP guard:
  REJECTED: GUARDRAIL breach on replay  (at step seq 2)
```

The recorder can record, but it cannot manufacture authorization.

## Coupled vs uncoupled — shown side by side

The workbench deliberately contains both architectural styles, and `parity_proof.py` proves they are
interchangeable:

| Style | Where | Trade-off |
|---|---|---|
| **Uncoupled** (vendored, standalone) | `chronicle/`, `llm_toolkit/` carry their own copy of the primitives | lifts out as an independent repo; small duplication |
| **Coupled** (shared, imported) | `guard_server/` and this `integration/` import `llm_toolkit` | DRY, single source of truth; components travel together |

`parity_proof.py` runs the **coupled** (imported `agent_core`) and **uncoupled** (`vendored_core`,
imports nothing) primitives over a battery of awkward payloads and asserts byte-identical
`canonical_bytes`, identical `state_hash`, identical `source_hash`, and an identical Ed25519 signature
over a committed hash:

```
RESULT: PARITY HOLDS — extraction is lossless; coupling is convenience, not correctness.
```

So the decision to import vs. vendor is purely about packaging: a coupled component can be vendored into a
standalone one (or vice-versa) without changing a single content address. That is "build for extraction"
made checkable — `test_integration.py` fails loudly if the two ever diverge.

## Files

| File | Role |
|---|---|
| `pep_agent.py` | coupled refund agent: model via `LLMCapture`, authorization via the PEP, fail-closed `pep_guard` verifying captured verdicts against the **pinned** server key, committed to the ledger |
| `demo_integration.py` | the end-to-end scenario incl. separation-of-powers forge rejection |
| `vendored_core.py` | an **uncoupled** standalone copy of the deterministic primitives (imports nothing from the workbench) |
| `parity_proof.py` | proves coupled and uncoupled produce identical content addresses |
| `tests/test_integration.py` | full-stack + parity tests |

## Honest scope

Loopback PEP, no TLS/authn/isolation; reference keys generated in-process. The cryptographic properties
(no key → no valid authorization; pinned, provable policy version; bit-exact replay) hold regardless of
those production layers. **Integrity is not truth** — this proves what was recorded and which
authorizations were genuinely granted, not that any refund decision was correct.
