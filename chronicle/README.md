# chronicle — a verifiable decision recorder

A tamper-evident "flight recorder + replay court" for consequential automated decisions (lending,
eligibility, pricing, moderation, model scoring). Stdlib-only Python, ~180 lines. Distilled from the
verification discipline of the [Dentatus](../OVERVIEW.md) project — the determinism and audit core,
without any of the game/physics framing.

## The one-sentence value

> Give me a decision's hash, and I will **replay** the exact computation that produced it, prove the
> record and the rules were **not altered**, and prove it satisfied the safety rules that were
> **committed before deployment** — on a separate machine, line by line.

## What it proves (and what it doesn't)

Run `PYTHONHASHSEED=0 python3 demo_policy.py`. For each recorded decision the court checks five things:

1. **Chain** — prev-hash links + contiguous seq → no past decision can be inserted, deleted, or reordered.
2. **Rule-bound** — the logic the auditor runs is hashed and must equal the recorded `ruleset_hash` → the
   rules did not change after the fact.
3. **Replay** — re-running the logic on the recorded inputs reproduces the recorded outputs bit-for-bit.
4. **Invariant** — the replayed decision still satisfies a precommitted hard rule (e.g. "DTI > 0.50 may
   never be approved"); the recorder **refuses to log** a decision that breaches it (fail-closed).
5. **Attest** — the re-derived content hash + HMAC match the receipt → record/key untampered.

The demo then *breaks* it on purpose: a flipped denial is caught as REPLAY drift, a secretly-loosened
ruleset is caught as RULESET changed, an unsafe decision is refused at record time.

**Honest boundary (integrity ≠ truth).** This proves a decision is *unforged, exactly reproducible, and
rule-faithful*. It does **not** claim the decision was *correct or fair* — only that the record is honest
and the declared rules were the ones applied. That modesty is the credible claim for an auditor or court.

## Files

- `core.py` — the recorder: recursive deterministic canonicalisation (floats stabilised), source-hashed
  rule binding, hash chaining, HMAC attestation, fail-closed invariant gate.
- `court.py` — the verifier: `verify_chain()` + a CLI (`python court.py ledger.json`).
- `demo_policy.py` — end-to-end proof on a rules-based credit-eligibility flow.

## Honest scope / next steps

- Attestation is **HMAC (symmetric)** to stay dependency-free: the key-holder verifies. For true
  *third-party non-repudiation* (an auditor who must not be able to forge), swap in **Ed25519** — the
  exact pattern proven in the parent project's `forge/registry_signing.py`.
- The hard part in any real deployment is making the decision logic **deterministic** (no clocks, no GPU
  float reassociation, no unordered external calls). That discipline — not this library — is the real
  asset; see `OVERVIEW.md` for where it was developed and proven.
- This is a reference MVP, not a product: no persistence layer, access control, or scale testing.
