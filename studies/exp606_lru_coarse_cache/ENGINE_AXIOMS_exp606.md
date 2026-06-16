# ENGINE_AXIOMS_exp606 — LRU Coarse Cache (zero-cost state returns)

**Protocol:** exp606-v1 · **Series:** 600 · **Inherits:** exp605-v1
**Primary architect:** Daniel J. Dillberg — bigdilly95@gmail.com
**Declaration hash:** `1bbbccefaec5ec174f95407e7f0abdcabd3e31d489b2b9327e4616fe9149a3d4`
**Status:** open · **Location:** `game/observability/stream.py` + dashboard live client

---

## Axiom 1 — Ghost #41 resolution

EXP-605 content-addressed the coarse channel only against the *immediate* previous `H_coarse`, so
a world returning to an earlier coarse re-sent it. EXP-606 adds a bounded **session LRU** of
`H_coarse → anchors`. The coarse channel now has three levels:

```
(1) H_coarse == prev          -> no coarse event (immediate skip)
(2) H_coarse in LRU (session) -> coarse_ref {H_coarse}   (zero anchor payload)
(3) otherwise                 -> keyframe or delta (adaptive); add to LRU; LRU-evict oldest
```

A return to **any** recently-seen coarse is now free — covering flicker, loops, and oscillation
across the whole session, not just adjacent frames.

## Axiom 2 — Results

```
loop A B A B A B  (two distinct coarse worlds, 148-leaf vs 8-leaf):
   no LRU : 6 keyframes,            coarse 1740 b
   LRU    : 2 keyframes + 4 refs,   coarse  688 b   (2.5x less; each return = 27 b ref)
reconstruction: bit-exact, and LRU field == no-LRU field (same result, fewer bytes)
eviction: lru_size=1 -> 0 refs (window too small) -> graceful re-send; bounded memory
backward-compat: non-looping stream emits 0 coarse_refs (EXP-605 behavior preserved)
```

Fork A 10/10, Fork B 5/5 (stream P_yz-invariant: event counts, refs, bytes, reconstruction).

## Ghost Notes

**Ghost #41 — Coarse history depth (RESOLVED):** bounded session LRU; returns within the window
are zero-cost; beyond it, graceful keyframe re-send.

**Ghost #42 — LRU sizing vs working set:** `lru_size` trades memory for return-coverage. For a
world that cycles among K stable coarse states (the common case at EMA equilibrium with occasional
lc-flicker), `lru_size >= K` makes the steady stream effectively keyframe-free after warm-up.

## Scope

`game/observability/stream.py` (encoder LRU + `coarse_ref`; decoder client LRU) + dashboard
`connectLive()` `coarse_ref` handler. No engine change. `PYTHONHASHSEED=0`.
