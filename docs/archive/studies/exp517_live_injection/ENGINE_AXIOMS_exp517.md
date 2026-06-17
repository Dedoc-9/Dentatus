# EXP-517 — Live MuState Injection (Fork ρ)

**Protocol** `exp517-v1` · **Declaration hash** `082b4a773bb23dfc2fe573d3c2d34010d5efd252e19707b0604b50d262338656`
**Scope** NO engine edits. `game/agency/injection.py` uses `dentatus.core`
(`MuState`, `Claim`, `Provenance`, `seal`, `next_S`) + `game.agency.phase_change`. Engine FROZEN.
Closes Ghost #50.

---

## A1 — The Lineage becomes the State

EXP-516 recorded transitions as an audit DAG separate from the live world. Fork ρ injects the melted
claim into the running `MuState`:

    active' = (active − {parent_leaf}) ∪ {melted_child}
    μ' = MuState(t+1, claims ∪ {child}, active', S')   →   seal()  →  H_after

Because `H_t = HASH(Z ⊕ S ⊕ W ⊕ t)` and `Z = Σ active stalks`, swapping the leaf's material changes
`Z`, so the engine's own `seal()` advances `H_before → H_after` as one continuous chain (Fork A [2],
[3]). The provenance edge (`child.provenance.parent_ids = (parent.id,)`,
`operator_id="PhaseChange:minimal"`) and the live state are now the **same** object — the record is the
reality.

## A2 — Interference resolved by optimistic concurrency (the design answer)

The hazard: the Agency computes an intent against a **solid** world; a phase change melts it to
**fluid**; the stale, solid-assumption intent must not be applied. The resolution is the discipline
content-addressing already gives — **compare-and-swap on H**, no locks:

```python
intent = make_intent(mu, ...)          # stamps basis_H = mu.H (the world it was computed against)
# ... a phase change advances the world H_before -> H_after ...
apply_intent_517(mu_fluid, intent)     # basis_H (H_before) != mu.H (H_after) -> rejected: stale_basis
rebase_intent(mu_fluid, intent)        # re-stamp against live H; Agency recomputes material-dependent
                                       # fields against the FLUID material, then resubmits
```

Verified (Fork A [5], [6]): the solid intent on the fluid world is rejected (`stale_basis`); the
rebased pulse is accepted. Injection itself is the same CAS (`expected_H`): a concurrent writer that
advanced the world makes a stale injection fail (Fork A [4]). The hash is the single source of truth;
any actor with a superseded basis is forced to re-read. This is the "Reality First" concurrency model —
lock-free, deterministic, hash-versioned.

## A3 — Purity, no-op outcomes, determinism

The injection is **functional**: it returns a new `MuState` and never mutates the input (Fork A [8] —
`mu0.H` still `H0`, parent still active, child absent). It only advances the chain on a `melted`
outcome; `stable` and `unsurvivable` return the world unchanged (Fork A [9]). `H_after` and the child id
are bit-stable (Fork A [10]).

## A4 — Two hashes, two roles (be precise)

- **Engine `H_t`** hashes the raw `Z` vector, which carries orientation, so it is **not**
  P_yz-invariant. That is correct: it is the *live geometric* chain — a reflected world is a different
  realized state.
- **Material lineage witness** (`material_H_before/after` = eigenvalue hashes, `χ_after`, the child id
  whose payload is the material-H) **is** P_yz-invariant (Fork B). The *identity of the material* and
  the *transition verdict* do not depend on orientation; the *placement in space* does.

This two-hash split is the resolution of "is the engine P_yz-invariant?": invariant where identity
lives, orientation-bearing where geometry lives.

---

## DEV NOTE — Ghost #51: the injection ghost & inactive-claim accumulation

1. **Injection ghost.** Re-declaration is a discontinuity in the forward channel: `Z` jumps by
   `ΔZ = stalk_melted − stalk_parent` (here `‖ΔZ‖ = 2.045`). Per the ghost discipline this residual is
   not hidden — it is absorbed into `S` via the engine's own `next_S()` (`S' = αS + (1−α)G` on the new
   geometry), so the dual channel accounts for the transition rather than the forward geometry
   silently swallowing it. The injection ghost is the dual-space signature of a phase change; an agency
   watching `‖S‖` will see a spike exactly at each melt — a usable telemetry of "the world just
   transitioned."

2. **Inactive-claim accumulation.** The pre-melt claim is retained in `claims` (inactive) for lineage
   but no longer in `active`, so it does not enter `Z`. Over many transitions the `claims` dict grows
   with history nodes. This is deliberate (the lineage is the point) but is a memory residual: a
   long-running world needs a *compaction* policy that prunes inactive claims from the working set while
   preserving their hashes in the provenance DAG (the EXP-606 LRU discipline applied to history). That
   is Fork υ.

## Suggested improvements / forks

- **Fork υ (history compaction).** Evict inactive claims from the live `claims` dict (LRU, as EXP-606)
  while keeping their ids + witnesses in the EXP-516 provenance DAG — bounded working set, unbounded
  auditable history.
- **Fork φ (multi-leaf worlds & partial melt).** Inject when only *some* active leaves breach: melt the
  affected section's claims, leave the rest, re-seal — ties to the EXP-506/507 sectioned architecture
  and EXP-514 per-section Citadel (Fork ι).
- **Fork χ (intent queue with rebase loop).** A standing Agency queue where rejected pulses auto-rebase
  and recompute against the live material, so the loop self-heals through phase changes.

## Foreign-language note (rhetoric → code)

Injection makes the *Stammbaum* (lineage) the *lebende Welt* (live world): the *Übergang* is *eingespeist*
(injected), advancing the *Zustandskette* (state chain) `H_before → H_after` *lückenlos* (gaplessly).
Interference is resolved by *optimistische Nebenläufigkeitskontrolle* (optimistic concurrency control):
an intent with a *veraltete Grundlage* (stale basis) is rejected and must *neu abgeglichen* (rebased)
against the *flüssige* (fluid) world. The *Einspritzungsgeist* (injection ghost) of Ghost #51 is the
`ΔZ` residual absorbed into `S`.
