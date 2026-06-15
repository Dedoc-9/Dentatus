# ENGINE_AXIOMS_exp601 — Deterministic Seeding (kill Ghost #27)

**Protocol:** exp601-v1
**Series:** 600 (Interface & Agency)
**Inherits:** exp505-v1 and all prior
**Author:** Daniel J. Dillberg — bigdilly95@gmail.com
**Declaration hash:** `f352e458d1e252f4af0fc555e8a76b4bfe7f7182c96d521d95341cfdf36d26fc`
**Status:** open
**Gate source:** Series 600 API requires content-addressable, bitwise-reproducible state hashes

---

## Axiom 1 — The change (state.py only)

`Claim.id` previously hashed the full provenance including the wall-clock `timestamp`, so the
same `SEED_DECLARATION` produced different child ids each run. The sorted-id summation order in
the gamma recursion then varied, injecting ~1e-14 noise into the carried `S_A/S_C/S_D` (Ghost #27).

```
before:  id = SHA256(provenance{parent_ids, operator_id, timestamp} ⊕ payload ⊕ t ⊕ protocol)[:16]
after:   id = SHA256({parent_ids, operator_id} ⊕ payload ⊕ t ⊕ protocol)[:16]    (timestamp EXCLUDED)
```

This is the **only** engine change (operators, validity, confluence are byte-identical to HEAD).
`timestamp` remains on the `Provenance` dataclass for audit; it is simply not part of identity.

## Axiom 2 — Why this is `f(parent.id, child_index)` already

The gamma recursion already creates every child as:

```
Provenance(parent_ids=(claim_id,), operator_id=f"Gamma:{partition_key}:{i}", timestamp=now_iso())
```

So `parent.id ∈ parent_ids` and the `child_index i ∈ operator_id`. Excluding the timestamp makes
`id` a deterministic function of exactly those — no Provenance restructuring needed.

## Axiom 3 — Isometric-aware identity (P_yz)

The `payload` is the coordinate-free extents hash `_bbox_hash_payload_312` (P_yz-invariant since
EXP-312), and the child index is a topological octant label (under P_yz octant `i ↔ i XOR 4`).
The id therefore carries no absolute x-coordinate. With a deterministic per-configuration
summation order, P_yz symmetry is preserved at machine precision — and the now-fixed order makes
the observable deltas **exactly 0.0** (verified Fork B: `max|B_ent_fwd − mir| = 0.0`,
`max|λ₂_fwd − mir| = 0.0`).

## Axiom 4 — Results

```
bitwise H_t:        same SEED_DECLARATION run twice -> identical (W, Z, S_A) digest   [Fork A 4]
S_A bitwise:        carried intra-claim ghost identical across runs (max diff 0e+00)  [Fork A 8]
claim-id set:       bit-stable across runs; 106 distinct ids                          [Fork A 5/6]
seed_memory_hash:   now bitwise reproducible (the EXP-504 6-digit coarsening is no    [Fork A 9]
                    longer required as a workaround — it remains as defense in depth)
P_yz:               exact 0.0 (was ~1e-14)                                            [Fork B 2/3]
no regression:      EXP-409/501..505 Fork A/B all green (501 cold-reset made explicit)
```

## Ghost Notes

**Ghost #27 — Claim-id-order Nondeterminism (RESOLVED):** timestamp excluded from identity.

**EXP-501 cold-reset (side effect, resolved):** EXP-501's per-step S_ent cold-reset was happening
*accidentally* because timestamp-churn made every step's ids unique. With deterministic ids the
octree keeps identical ids across steps, so the reset is now explicit in `run_seed_exp501.py`
(`S_ent_prev_n = {cid: 0.0 ...}`) — honoring the documented "cold-start reset" scope. Runner-only
change; engine untouched.

**Determinism enables content-addressing (EXP-602 gate):** bitwise `H_t` is the prerequisite for
a content-addressed reality store — `GET /v1/state/{H_t}` is now a true immutable dedup key.

## Scope

`engine/state.py` Claim.id only. No operator, validity, or schema change. All Series 400/500
assertions remain valid; P_yz tightened from ~1e-14 to exact.
