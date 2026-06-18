# polity — deterministic governance for evolving rulesets

The rulesets that `elenchus`, `fuel`, and the policy layers enforce are **frozen** — pinned by content
hash, changeable only by editing code. That is safe but brittle: the system rots the moment a rule is
wrong. `polity` adds the missing primitive — a deterministic way to **ratify a new ruleset version** — while
keeping the chain of custody intact. It is the first of the governance siblings (infrastructure before
application).

A ruleset is governed only by its **content hash**; `polity` never needs the rule semantics. Governors (a
pinned key registry) vote on a proposal; the vote is tallied by `quorum` (exact integer count, no float); if
a **k-quorum** ratifies, a new **constitution version** is minted that binds to the prior one — a
`pact`-style content-addressed lineage. The active ruleset is whatever the latest ratified version names.

## Run it

```
PYTHONHASHSEED=0 python3 demo_polity.py            # genesis · ratify · reject · lineage
PYTHONHASHSEED=0 python3 tests/test_polity.py      # 8 unit tests
```

## How it works

```
genesis_constitution(rh)         -> v0 {ruleset_hash: rh, prev: GENESIS}          founding ruleset, by fiat
propose(prev, new_rh, proposer)  -> a proposal binding new_rh to the current constitution
cast(gov, signer, prop, yea|nay) -> a signed ballot (quorum.witness_vote on a ratify/reject state)
ratify(prev, prop, ballots, k)   -> tally via quorum; if >=k agree on RATIFY, mint v(n+1) bound to v(n)
verify_lineage(chain)            -> each version content-addresses, binds to its predecessor, index contiguous
active_ruleset(chain)            -> the ruleset hash named by the latest version
```

A `nay` ballot is authenticated and counted as *present* (it shows up in the certificate's `n`) but signs a
distinct reject hash, so it does **not** add to the ratify tally — `quorum` only certifies when ≥ k governors
agree on the *same* ratify hash. An outsider's ballot (a key not in the pinned registry) is rejected and
never counted. A proposal short of quorum is refused fail-closed; the active ruleset is unchanged.

## Honest bounds (do not oversell)

- It proves the **vote happened** and the tally is **exact** under the pinned governor keys. It does **not**
  prove the new ruleset is better, correct, or wise. (integrity ≠ truth.)
- Governor **independence is a trust input** — the same Sybil bound as `quorum`. A colluding ≥ k governing
  majority ratifies a bad rule just as cleanly as a good one; the certificate proves agreement among the
  **named keys**, nothing more.
- It governs **which** content-addressed ruleset is active; it does **not** execute or validate the rules —
  that is `elenchus` / `fuel`'s job against the hash `polity` ratifies.

## Where it sits

| sibling | role |
|---|---|
| `quorum` | tallies the governors' ballots (exact integer consensus) |
| `pact` / lineage | the constitution is a content-addressed version chain bound to its predecessor |
| `elenchus` / `fuel` | enforce *against* the ruleset hash that `polity` makes active |

## Files

| File | Role |
|---|---|
| `constitution.py` | `genesis_constitution`, `propose`, `cast`, `ratify` (quorum tally), `verify_lineage`, `active_ruleset` |
| `demo_polity.py` | genesis (A) · ratify (B) · reject (C) · lineage + forged link (D) |
| `tests/test_polity.py` | 8 unit tests (ratify, reject, nay/outsider handling, lineage, tamper) |
