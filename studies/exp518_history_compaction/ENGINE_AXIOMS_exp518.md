# EXP-518 — History Compaction (Fork υ)

**Protocol** `exp518-v1` · **Declaration hash** `32c1314a87fbd52301eeba7ddae8be59cc23999f2bb834acff312e794d912fd8`
**Scope** NO engine edits. `game/agency/compaction.py` uses `dentatus.core` (`MuState`) +
`game.agency.injection` + `game.agency.transition_dag`. Engine FROZEN. Resolves the memory residual of
Ghost #51.

---

## A1 — Garbage collection of reality

EXP-517 injection leaves the pre-melt claim inactive in `MuState.claims` (Ghost #51); over many
transitions the working set grows. Compaction evicts inactive claims from the **live** set, keeping the
world bounded, while the EXP-516 provenance DAG keeps every transition hash for unbounded history:
**constant-time live performance, infinite auditable past.**

## A2 — Two inertness guarantees (why eviction is safe)

1. **H-inert.** `H_t = HASH(Z ⊕ S ⊕ W ⊕ t)` with `Z = Σ active stalks`, `W = active`. Inactive claims
   enter none of these, so evicting them leaves `H_t` **bit-identical** (Fork A [2]). Compaction does
   not change the world's identity — it is pure GC.

2. **Observationally inert.** The only observable that reads *all* claims is `η_CLT = √|W|·(μ̂_active −
   μ_grand)`, where `μ_grand` averages over the whole population. Retaining the evicted claims'
   **sufficient statistics** (`Σ‖stalk‖`, count) reconstructs `μ_grand` exactly:

       μ_grand = (Σ_active ‖·‖ + evict_sum) / (|active| + evict_n)

   so `η_CLT` is preserved to the bit (Fork A [5]: matches a non-compacting reference exactly) while the
   claim *objects* are discarded. The other observables (`B`, `ESS`, Fiedler) read only active claims and
   are trivially inert.

```python
def eta_CLT(self):
    mu_hat  = sum_active_norm / n_active
    mu_grand = (sum_active_norm + self._ev_sum) / (n_active + self._ev_n)   # evicted via sufficient stats
    return sqrt(n_active) * (mu_hat - mu_grand)
```

## A3 — Tiered memory (the design answer)

Your either/or resolves to **both, tiered** — the EXP-606 hot/cold pattern:

| Tier | Holds | Purpose | Cost |
|---|---|---|---|
| **Skeleton Lineage** | deque (maxlen N) of `(live μ, evict-stats)` snapshots | **O(1) instant undo** within window | `N · |active|` |
| **Provenance DAG** | every transition's hashes + witness (EXP-516) | unbounded **cold** audit | `O(#transitions)`, hashes only |
| **Replay (Fork τ)** | reconstruct from DAG | look-back **beyond** the window | cold |

Verified: working set constant (`[1,1,1]` over 3 melts, Fork A [3]); history complete (DAG retains all,
[4]); undo restores prior `H` and `η_CLT` in O(1) ([6],[7]); undo past N raises `BeyondWindowError`
([8]) — the explicit boundary where the hot path ends and replay begins.

## A4 — P_yz & determinism

`η_CLT` is built from stalk **norms** (P_yz-invariant) and DAG child ids use material-eigenvalue
payloads, so the compacted observables and the lineage are reflection-invariant (Fork B). The full
chain is bit-stable (Fork A [9]).

---

## DEV NOTE — Ghost #52: the compaction shadow & the hot/cold undo asymmetry

1. **The shadow population.** Observational inertness is bought by carrying the evicted claims'
   sufficient statistics *forever*. These are O(1) in size but **unforgettable**: `η_CLT` depends on a
   shadow of every claim that ever existed. The residual is that the statistics and the live state must
   move *atomically* — the Skeleton Lineage snapshots `(μ, stats)` together precisely so that `undo`
   rolls both back in lockstep (Fork A [7]); a desync would silently corrupt `η_CLT`. The shadow is not
   an entity, only three accumulators, but it is a permanent debt of compaction.

2. **Hot/cold undo asymmetry.** Undo is O(1) within the skeleton window and *replay-cost* beyond it —
   undo latency is tiered, not uniform. `BeyondWindowError` makes the boundary explicit rather than
   silently degrading. Choosing `N` is the usual cache trade: larger `N` = more instant undo, more
   resident memory. `N` is a per-deployment knob (not constitutional — it changes no observable, only
   undo reach).

3. **Skeleton width for multi-leaf worlds.** Each snapshot is `|active|` claims; for the single-leaf
   worlds here that is 1, but a sectioned multi-leaf world (Fork φ) makes snapshots `O(|active|)` — the
   skeleton is bounded but not free. A future refinement stores *deltas* (only the changed leaf) per
   snapshot rather than full `μ` copies.

## Suggested improvements / forks

- **Fork τ (replay / time-travel debugger).** Reconstruct any historical `μ` from the DAG + a periodic
  checkpoint, bridging beyond the skeleton window — turns `BeyondWindowError` into a cold restore.
- **Fork ψ (delta snapshots).** Store per-snapshot leaf deltas instead of full `μ` copies, so the
  skeleton cost is `O(N · changed)` not `O(N · |active|)` — matters for multi-leaf worlds.
- **Fork ω (checkpoint cadence).** Periodic full-state checkpoints in the DAG so replay cost is bounded
  by the checkpoint interval, not the whole history.

## Foreign-language note (rhetoric → code)

Compaction is *Speicherbereinigung* (garbage collection) of the *Stammbaum* (lineage): inactive claims
are *entfernt* (evicted) from the *Arbeitsmenge* (working set) but their *suffiziente Statistik*
(sufficient statistics) is *aufbewahrt* (retained), so `η_CLT` stays *unverändert* (unchanged) — the
*Schatten* (shadow, Ghost #52) of the forgotten population. The *Skelett-Linie* (skeleton lineage) gives
*sofortiges Rückgängigmachen* (instant undo); beyond it lies *kalte* (cold) replay. *Begrenzter
Speicher, unbegrenzte Geschichte* — bounded memory, unbounded history.
