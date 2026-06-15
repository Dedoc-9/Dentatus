# ENGINE_AXIOMS_exp505 — Persistent World-State across Moving Claims

**Protocol:** exp505-v1
**Series:** 500
**Inherits:** exp504-v1 and all prior
**Author:** Daniel J. Dillberg — bigdilly95@gmail.com
**Declaration hash:** `6885720d383ca77565ad5bf9091f38da27a678574617c35edb7bdeffd07d873a`
**Status:** open
**Gate source:** EXP-504 Ghost #28 — spatial-key drift loses localized manifold memory under motion

---

## Axiom 1 — The Drift Problem (Ghost #28)

EXP-504 keys `S_ent` by absolute position (`spatial_key_504`). When claims move, the absolute
key of a given feature changes every scene: the old key becomes an "away" key that decays, the
new position is a fresh key with no memory. Localized manifold memory is destroyed by motion
even though the underlying claim persists. Measured: under rigid world drift `V`, raw-key
continuity = 0 (no claim's key survives scene-to-scene).

---

## Axiom 2 — Motion-Compensated World Frame

The fix re-references claims to a world frame that moves with the scene. The inter-scene global
translation is estimated from the centroid-of-centroids shift (exact for rigid motion):

```
estimate_global_motion_505:  δ = mean(curr_centroids) − mean(prev_centroids)
cumulative_motion:           M_n = M_{n-1} + δ_n           (caller-tracked primary scalar)
world_frame_key_505(bbox):   key on (round(center − M_n, 6), round(|hi−lo|, 6))
```

Under rigid motion the world-frame key of a feature is invariant across scenes → a **stable
track id**. Measured: `estimate_global_motion_505` recovers `V` to <1e-12; world-frame key of a
leaf is identical at scene 0 and scene 5 under motion.

---

## Axiom 3 — Track Correspondence DAG

`track_correspondence_505` links current claims to persistent tracks by world-frame key and
emits a hash-indexed correspondence DAG:

```
claim_to_track[ci] = world_frame_key(bbox_ci, M_n)
edge (prev_key, track_key, claim)   matched if track_key ∈ prior tracks, else a birth
```

`S_ent` is then keyed by track id (world-frame key) in `persist_scene_504`, so per-claim memory
follows the moving claim. Track count == leaf count (one track per claim; no explosion).

**Code/Math correspondence:**

| Math | Code |
|------|------|
| `δ = mean(curr) − mean(prev)` | `estimate_global_motion_505` |
| `key(center − M_n, size)` | `world_frame_key_505` |
| `{ci → track_key}, DAG edges` | `track_correspondence_505` |

---

## Axiom 4 — Results (Ghost #28 resolved)

Fixed octree (64 leaves) rigidly drifting by `V = [0.07, 0.03, 0]` per scene, N=16:

| Metric | RAW504 (absolute keys) | TRACK505 (world frame) |
|--------|:---:|:---:|
| continuity under motion | 0.00 | 1.00 |
| per-track S_ent memory | flat (no EMA buildup) | EMA buildup +14.9 |
| localized tear healing | lost | decays ratio ≈ α_persist=0.5 |

A localized tear on a moving track (excess `[6.0, 3.0, 1.5, 0.78, 0.41]`, ratios `≈0.5`) heals
geometrically as the claim moves — the EXP-504 temporal smoothing now operates on moving claims.
Gate `is_manifold_501` admissible throughout.

---

## Axiom 5 — Structural Index and P_yz Invariance

`track_dag_hash_505` indexes the correspondence DAG from edge counts and the sorted multiset of
world-frame **sizes** (`|hi−lo|`, P_yz-invariant). Track-key centers (signed x) are excluded, so
the index is P_yz-invariant (consistent with the Ghost #27 norm-based hashing principle).

True P_yz (reflect bbox about x=0, negate Sector B x and Sector C nx, reflect motion `V_x→−V_x`):
verified `track_continuity_fwd == mir`, sorted `S_ent` multiset delta `0.0`, `B_ent_spectral`
and healing-curve delta `0.0`, `H_dag_fwd == H_dag_mir` all scenes, `gate_fwd == gate_mir`.

---

## Ghost Notes

**Ghost #28 — Spatial-key Drift (RESOLVED):** motion-compensated world-frame keying (Axioms 2–3).

**Ghost #29 — Non-rigid / Independent Motion (OPEN, EXP-506):** the centroid-shift estimate
assumes a single global translation. Claims moving independently (different velocities) are not
separated by a global δ. EXP-506 target: nearest-neighbor association within the gate radius
`r_gate` using the coarse spatial-hash cells (`_GRID_505`, reserved here), with per-track velocity
prediction. The `_R_GATE_505 / _GRID_505` constants are declared in EXP-505 for that gate.

---

## EXP-505 Scope

Adds `estimate_global_motion_505`, `world_frame_key_505`, `track_correspondence_505`,
`track_dag_hash_505` (operators). `SeedMemory` gains caller-tracked `cumulative_motion` and
`prev_mean`. No change to phi_ent_observe, phi_fb_manifold, persist_scene_504, is_manifold_501,
or the EXP-409 path. All Series 400 and EXP-501–504 assertions remain valid.
