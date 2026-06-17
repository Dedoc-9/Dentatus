# tessera — the portable shard that breaks trust (without breaking honesty)

In Rome a *tessera hospitalis* was a token two parties broke and later rematched to prove a prior
agreement. Here a `tessera` is a tiny record that lets **anyone replay a declared deterministic-integer
computation offline and confirm it took exactly the claimed path** — trusting no producer, no central
validator, no log file. It is the first child of the Axiom build order; `fuel` and `elenchus` stand on it.

A shard is small: `{ruleset_hash, seed, steps, terminus, path_hash, prev, signature}`. It carries **no
path** — the verifier reconstructs the whole trajectory from the seed and the pinned rule and recomputes a
rolling hash of every bit-flip. The record is the proof; the replay is the validation.

## What it proves — and the exact line it does not cross

- **Replay-correctness is trustless.** Same pinned rule + seed → re-run the integer trajectory, recompute
  the rolling `path_hash`. If it matches, the claimed step count, terminus, and bit-flip history are exactly
  real. No trust in the producer is required for this half.
- **Authorship is *not* trustless.** The optional Ed25519 signature attributes the shard to a key;
  confirming *who* minted it still needs that signer's pinned public key — the same bound as `pact` /
  `chronicle`. (The public key can ride inside the shard, but trusting it is a separate decision.)

## Run it

```
PYTHONHASHSEED=0 python3 demo_tessera.py          # mint · offline replay · tamper · divergence · lineage
PYTHONHASHSEED=0 python3 tests/test_tessera.py    # 12 unit tests
```

## How it works

The producer mints over a pinned rule (a deterministic `step` + a `done` predicate, both source-bound into
`ruleset_hash`):

```
roll:   h₀ = H(seed)
        hₖ = H(hₖ₋₁ ‖ state_hash(stateₖ))     for each integer step   (the bit-flip history, chained)
shard:  { ruleset_hash, seed, steps, terminus, path_hash = h_final, prev, signature? }
```

`verify(shard, rule, done)` re-runs the same rule from the seed and names the precise failure if any:
`RULESET` (a different rule), `STEPS` (wrong count / didn't terminate in the claim), `TERMINUS` (wrong
end-state), `PATH` (the bit-flip history differs), or `SIGNATURE` (forged authorship). The compact shard
verifies match/no-match; given a producer's full claimed **scroll**, `locate_divergence` names the **exact
step index** where the claim first stops being reproducible — the forensic "which step is the lie."

### Immutable lineage

`link(prev, …)` mints a new shard whose seed continues from the prior terminus and whose `prev` binds to
the prior `path_hash`. `verify_lineage` checks each shard *and* that each binds to its predecessor — a
hash-linked chain of replayable computations (pact, but for computation steps), with a broken link located
to the exact index.

## Honest bounds (do not oversell)

- **Not cryptography in the secrecy sense.** There is no preimage resistance; anyone can mint a valid
  tessera for their *own* computation. The value is that forging the **process history of a declared
  computation** is detectable — not that results are secret, and not that a result cannot be recomputed.
- **Not a proxy for unrelated work.** A tessera proves the path of the *declared rule from the seed*.
  Replaying a cheap orbit says nothing about a separate expensive job unless that job *is* the declared
  deterministic computation. (The proxy fallacy is rejected by construction.)
- **integrity ≠ truth.** It certifies the steps were taken, never that the computation's result is correct,
  wise, or meaningful. The unproven Collatz conjecture (via `syracuse`) is the architectural ceiling, not a
  bug: we prove the finite instance, never the infinite rule.

## Files

| File | Role |
|---|---|
| `shard.py` | rolling path-hash; `mint` / `verify` (trustless replay); `locate_divergence`; signed authorship; `link` / `verify_lineage` |
| `demo_tessera.py` | mint + offline replay (A) · tamper (B) · forensic divergence (C) · immutable lineage (D), over a `syracuse` orbit |
| `tests/test_tessera.py` | 12 unit tests (mint/verify, tamper, divergence, lineage) |
