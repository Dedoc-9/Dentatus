# pact — multi-agent cross-attestation covenant (forensic dispute resolution, no blockchain)

A Sibling-Law component: it imports the frozen [`chronicle`](../chronicle/README.md) + `llm_toolkit`
primitives read-only and lets independent agents (or companies) make and verify agreements without a
blockchain or a central single-writer database.

## How it works

When Agent A hands a state to Agent B, B verifies A's signature against a **pinned peer registry**, checks
the incoming state against B's own invariant, then signs a **cross-attestation** that binds B's new state
hash to A's prior hash. Chaining these yields a multi-party trail where any later injection or rule breach
is attributable to the **exact agent + link**.

| Layer | What |
|---|---|
| **Gate** (fail-closed) | A is in the pinned registry; A's signature verifies under A's pinned key; the incoming state satisfies B's precommitted invariant — then B emits a signed `{from,from_hash}→{to,to_hash}` binding |
| **Observable** (captured) | inter-agent latency, message arrival order, per-model confidence — soft metrics, never gated |

## Run it

```bash
PYTHONHASHSEED=0 python3 demo_pact.py        # covenant / audit / forgery / injection-isolation
PYTHONHASHSEED=0 python3 tests/test_pact.py  # 7 tests
```

The demo builds an A→B→C covenant, audits it on pinned public keys (VERIFIED), rejects a rogue key
impersonating A, and — the key result — when an operator holding **B's real key** injects a state that
breaks the covenant rule, the multi-chain audit isolates the **exact link and agent** that deviated.

## Honest bound

This gives **non-repudiation under the pinned-key trust assumption** and forensic attribution — proving who
signed what, when, and what state they claimed. It does **not** force a peer to be honest, and there is
**no** automatic broadcast or distributed consensus: a breach is self-evident to anyone who verifies with
the pinned public keys, not "to the whole network" by magic. Not a blockchain. Integrity is not truth.

## Files

| File | Role |
|---|---|
| `covenant.py` | `state_receipt`, `verify_receipt`, `cross_attest` (binding + fail-closed), `audit_covenant` (fault isolation) |
| `demo_pact.py` | covenant / audit / forgery / injection-isolation |
| `tests/test_pact.py` | clean covenant, unknown/impersonation/tamper rejection, invariant-breach isolation, broken binding |
