# EXP-523 — Validity Witness (Fork ω)

**Protocol** `exp523-v1` · **Declaration hash** `1fc9721cf4e667cbf5c1baa277e639cc85f0471359ca04cc666921ed8987cd2b`
**Scope** NO engine edits. `game/observability/integrity.py` uses `dentatus.core` only. Engine FROZEN.
**Closes Ghost #5.**

---

## A1 — The hole (a coarsened view could claim full integrity)

The EXP-309 SPRT observer classifies a state `FULL_VALID` / `LOD_RELAXED` / `INVALID`: when the viewer
is far from a claim, the κ-curvature predicate is *bypassed* (level-of-detail), and a state that passes
the remaining predicates with ≥1 bypass is `LOD_RELAXED`. But the engine identity
`H_t = HASH(Z ⊕ S ⊕ W ⊕ t)` does **not** include the validity class. Verified directly (Fork A [2]): a
`FULL_VALID` and a `LOD_RELAXED` state of identical geometry produce the **same** `H_t`
(`a1a4733f5ddd`). The hash could not witness that a predicate was bypassed — integrity laundering across
level-of-detail.

## A2 — The containment bound (why it was never exploitable)

The hole is real but unreachable through the clean room (Fork A [7]):
- `Gamma_309` — the only operator that produces `LOD_RELAXED` — is **not** exported by `dentatus.core`,
  so no L1/game path can invoke it.
- `api.observe` (the Series-500 firewall) never references `validity_class`; it only mints `FULL_VALID`
  seed states. Every existing `H_verified` is therefore already full-integrity.

So the defect was *contained* by the architecture but not *closed* by the hash. EXP-523 closes it.

## A3 — The validity witness (the close)

The verified address binds the integrity class to the geometric identity:

```
verified_address(μ):
    INVALID      → None                              (no admissible address)
    FULL_VALID   → H_t                                (UNCHANGED → backward compatible)
    LOD_RELAXED  → SHA256(H_t ⊕ class ⊕ pv)[:16]       (DISTINCT → records the bypass)
```

```python
if vc == "FULL_VALID": return mu.H                    # plain H_t: every Series-500 address unchanged
return sha256("\x1f".join([mu.H, vc, PROTOCOL]))[:16] # relaxed: a different address, cannot launder
```

A `LOD_RELAXED` state can therefore **never share an address** with a `FULL_VALID` one of the same
geometry (Fork A [4], [6]). Backward compatibility is exact: `FULL_VALID → H_t`, so every existing
`H_verified` is bit-unchanged (Fork A [8]). The engine `_compute_H` is untouched (frozen) — the binding
lives entirely in the observability layer.

## A4 — The three facets of identity (completes Charter II.3)

The hash-identity picture is now complete in three orthogonal facets:

| Facet | Carrier | Encodes | P_yz |
|---|---|---|---|
| **Geometric** | `H_t = HASH(Z⊕S⊕W⊕t)` | the realized geometry (position/orientation) | orientation-bearing |
| **Material** | eigenvalue hash (EXP-515/516) | the substance (covariance spectrum) | invariant |
| **Integrity** | `verified_address` (this) | the validity class (was a predicate bypassed?) | label invariant |

The validity class is a geometry-independent label (Fork B [1]); the binding closes laundering in every
orientation (Fork B [3]).

---

## DEV NOTE — Ghost #5 closed; integrity is now a first-class hash facet

The residual is resolved: a relaxed state is no longer hash-confusable with a full-valid one. Two
properties make this safe:
1. **Backward compatibility is total.** `FULL_VALID → H_t` means the close adds *no* new address for any
   state the engine already produces — it only *separates* the (currently unreachable) relaxed states.
   No Series-500 fork can regress.
2. **The bound is documented, not merely relied upon.** Even though `Gamma_309` is unreachable today, a
   future fork that *does* expose LOD partitioning must route admissibility through `verified_address`
   (or `integrity_witness`) so the relaxation is recorded. The registry entry now points here.

A subtlety worth recording: `LOD_RELAXED` is not "invalid" — it is *valid at the declared level of
detail*. The witness does not reject it; it makes the *scale of the claim* part of the claim's identity,
so an observer who later zooms in gets a different address (and must re-verify at the finer scale). This
is the correct semantics for a multi-resolution truth: integrity is relative to the resolution at which
it was checked, and the address now says so.

## Suggested improvements / forks

- **Fork Ϫ (resolution-tagged address).** Extend the witness to carry the *focal distance* / LOD level,
  so the address encodes not just "relaxed" but "valid to resolution r" — a continuous integrity scale.
- **Fork Ϭ (re-verification on zoom).** When the viewer crosses a claim's LOD threshold inward,
  automatically re-run `is_lod_valid_309` and promote `LOD_RELAXED → FULL_VALID` (or `INVALID`),
  re-addressing — closing the loop between viewing scale and verified integrity.

## Foreign-language note (rhetoric → code)

The witness binds the *Gültigkeitsklasse* (validity class) to the *Adresse* (address): a *grob*
(coarse / `LOD_RELAXED`) state, whose κ-*Prädikat* was *umgangen* (bypassed) at *Distanz*, receives a
*verschiedene Adresse* (distinct address) so it cannot *vortäuschen* (feign) the *volle Integrität* (full
integrity) of a *fein geprüfter* (finely-checked) state. Integrity is *auflösungsrelativ* (resolution-
relative); the *Adresse* now *bezeugt die Auflösung* (witnesses the resolution).
