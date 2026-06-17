# quorum — exact integer consensus (the second half of the tautology)

The workbench's standing modesty is **one** clause:

> `integrity(node) ⊬ truth` — a single replay-verified ledger is honest and reproducible, and can still be
> *wrong*, because its inputs and world-model were never in scope.

That clause is incomplete on its own; it only says what a lone integrity does **not** buy. `quorum` supplies
the complementary clause, which *defines* operational truth by construction:

```
Truth_op(round) := h*   such that   #{ w ∈ Q : authentic(w) ∧ H_w = h* } ≥ k
```

Operational truth is the exact state hash on which a **k-quorum of independently-keyed, integrity-holding
witnesses coincide**. The two clauses only close the epistemic position together: integrity is necessary
per-witness; truth is the emergent fixed point across witnesses. Consensus-truth is *analytic* — the
agreement **is** the truth — not *correspondent* (it is not checked against an external world). That is the
"one half of a tautology": neither clause alone is the position.

## Why "integer" consensus

Agreement is on exact 256-bit state hashes, so the relation is **decidable and tolerance-free**: `h_i == h_j`
or it is not. A float consensus would need an epsilon, and an epsilon is exactly the arbitrary coarse-graining
boundary — a model construct masquerading as a limit. Integer/hash consensus introduces no epsilon. The **one**
declared model construct is the quorum threshold `k` (the cut between consensus and no-consensus); it is a
chosen parameter, named as such, never an inherent limit.

## Run it

```
PYTHONHASHSEED=0 python3 demo_quorum.py            # tally cases A–E + the 2D lattice F
PYTHONHASHSEED=0 python3 tests/test_quorum.py      # 17 unit tests
```

## The tally (lateral axis)

`tally(votes, k, registry, round_id)` does exact integer counting, no float, no tolerance:

1. **authenticate** every vote against the pinned `registry` (unpinned/forged → rejected, never counted);
2. detect **equivocation** — a witness that signed ≥2 distinct hashes for one round is excluded and named
   (the one Byzantine behaviour a tally catches cheaply);
3. **count** one hash per remaining witness; the modal hash with multiplicity `m` is the plurality;
4. **certify** iff `m ≥ k`; else emit the fork set instead of a verdict.

Dual math / code:

```
votes = {(w, h_w)},  h_w ∈ {0,1}²⁵⁶          c = Counter(votes.values())     # exact, no float
c[h]  = Σ_w 1[h_w = h]                        h*, m = c.most_common(1)[0]
h*    = argmax_h c[h];  certify iff m ≥ k     certified = m >= k
G     = {w : h_w ≠ h*}   (dissent residual)   ghost = {w:h for w,h in counted if h != h*}
```

### The ghost (dev note)

`G = {witnesses whose hash ≠ modal}` is the **dissent residual**. In the workbench's ghost formalism
`G_t = Z_t − Π_W(Z_t)`, here `Π_W` is the projection onto the quorum-agreed hash and `Z_t` the full vote
vector, so `G_t` is the part of the vote that does not lie in the agreed subspace. It is **recorded**
(localizing the fork), accumulable as a dissent ratio `divergence = |G|/n`, and **never allowed to flip a
certificate** — a lone honest dissenter may be the only correct one when the majority colludes, so dissent is
preserved, not discarded. This is `integrity ≠ truth` applied recursively: **consensus is not truth either.**

`ghost.py` is the only place the residual *persists* across rounds, as an EMA `S_{t+1} = αS_t + (1−α)g_t` over the per-round divergence ratio `g_t`. `S_t` is a pure **drift-pressure** observable — a slow rise when honest, outvoted witnesses begin disagreeing more often (e.g. a quiet upstream model-weight update forking one node). It is a sensor, never a gate, and it never says *which* side is correct.

### Pure observables

```
agreement_ratio  A_r    = c[h*] / n                       ∈ (0,1];  1 = unanimous
ess_opinions     ESS    = (Σ_h c[h])² / Σ_h c[h]²         ∈ [1, n]; 1 = unanimous … n = total fork
divergence       D      = (n − c[h*]) / n                 the ghost ratio
equivocators     E      = witnesses that double-signed this round
```

`ESS` is the workbench's effective-sample-size formula `(Σw)²/Σw²` applied to vote multiplicities: it reads
out the **effective number of opinion-blocs**, 1 under unanimity and `n` under total disagreement.

## The 2D lattice (lateral ⊕ temporal) — `lattice.py`

`quorum` certifies agreement **at one round**; `pact` certifies an unbroken covenant **across rounds**.
Composed, they form an attestation lattice with two axes that are deliberately **not collapsed**:

```
            witnesses (lateral: quorum, k-of-n must agree)
          w1    w2    w3    w4
round 0 [ h    h     h     h  ]  → certifies → quorum_hash₀  ┐
round 1 [ h    h     h     h  ]  → certifies → quorum_hash₁  │ temporal: pact covenant
round 2 [ h    h     h     h  ]  → certifies → quorum_hash₂  ┘ over the certified spine
```

A **row** is valid iff it reaches quorum; the **certified spine** is valid iff its covenant holds under a
pinned notary key and a precommitted temporal invariant. `evaluate(...)` returns the exact fault and its
axis: `{"axis":"lateral", round, ghost, equivocators}` or `{"axis":"temporal", ...}`. The two failure
residuals — lateral dissent and a broken temporal link — are independent and reported separately.

> Fail-closed: an **uncertified** round **cannot** be bound to the spine — you cannot attest agreement that
> does not exist.

## Honest bounds (must be read)

This is a quorum **tally**, not asynchronous Byzantine agreement — **no leader, no view-change, no liveness
guarantee under partition**. It certifies agreement and localizes divergence; it does not solve BFT under
adversarial scheduling. Witness **independence is a trust input** (pinned keys, out-of-band), not a proven
property — the tally cannot detect a Sybil operator standing behind several "witnesses". A colluding `≥k`
majority (or a colluding notary) certifies a falsehood; the certificate proves agreement among the **named
keys**, nothing more. A bound lattice of integrity + consensus is strictly stronger and fully attributable —
and still **not truth**.

## Relation to the rest of the workbench

| sibling | axis | proves |
|---|---|---|
| `chronicle` / `pact` | per-node / temporal | one ledger is honest; B's state binds to A's prior |
| `quorum` | **lateral** | k independent integrities agree on the exact same world hash |
| `quorum.lattice` | **lateral ⊕ temporal** | every round reaches quorum AND the certified rounds form an unbroken covenant |

## Files

| File | Role |
|---|---|
| `tally.py` | witnesses, pinned registry, signed votes, the exact integer tally, equivocation, ghost, observables, certificate hash |
| `lattice.py` | composes `quorum` (lateral) with `pact` (temporal) into the 2D attestation lattice |
| `ghost.py` | EMA accumulator that persists the per-round dissent ratio as a slow `S_t` drift-pressure observable (never a gate) |
| `demo_quorum.py` | cases A–E (tally) + F (lattice happy / lateral fault / temporal fault) |
| `tests/test_quorum.py` | 17 unit tests (tally, lattice, ghost) |
