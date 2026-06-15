# ENGINE_AXIOMS_exp504 — Stateful Seed (Temporal Manifold Smoothing)

**Protocol:** exp504-v1
**Series:** 500
**Inherits:** exp503-v1 and all prior
**Author:** Daniel J. Dillberg — bigdilly95@gmail.com
**Declaration hash:** `93201baeac72aac92183da7bdf5c1d9da7fb144abeea66d3b1cca38ecf47530c`
**Status:** open
**Gate source:** EXP-503 Ghost #26 — equilibrium stiffness: a reflex without memory cannot heal

---

## Axiom 1 — SeedMemory and persist_scene_504

The EXP-503 manifold restoring force is instantaneous: it reacts to the current scene's
deformation but forgets it at each reset. EXP-504 adds cross-scene memory. `SeedMemory` is a
caller-tracked primary-state struct (like `bze_ema_prev`, `maint_latched` already are):

```
SeedMemory = { S_A, S_C, S_D, S_ent(spatial-keyed), bze_ema_prev, maint_latched,
               B_ent_spectral, scene_count }
```

`persist_scene_504` is a STATELESS pure function `(memory_in, observations) → memory_out`:

```
active key k:   S_ent[k] ← α·S_ent_mem[k] + (1−α)·S_ent_obs[k]
away   key k:   S_ent[k] ← decay_away · S_ent_mem[k]   (prune if |·| < prune_eps)
B_ent_spectral ← α·B_ent_spectral_mem + (1−α)·B_ent_spectral_obs        temporal smoothing
```

Parameters: `α_persist = 0.5`, `decay_away = 0.5`, `prune_eps = 1e-6`, `spatial_ndigits = 6`.

The persisted `B_ent_spectral` feeds the NEXT scene's `phi_fb_manifold`, closing the temporal
loop: manifold stress is carried and decayed across scenes rather than reset.

---

## Axiom 2 — Spatial Keying (cross-scene claim correspondence)

Claim ids change every scene (fresh octree). To transfer per-claim `S_ent` memory across
resets, `S_ent` is keyed by a spatial signature instead of claim id:

```
spatial_key_504(bbox) = (round(center, 6), round(size, 6))
```

Octants at the same spatial location across scenes share a key → memory transfers. Keys are
built from `|hi−lo|` extents and centers (P_yz-equivariant). The dual-arithmetic separation
holds: `S_ent` (inter-claim dual, R^N) is persisted orthogonally to `S_A/S_C/S_D` (intra-claim
dual) and to `bze_ema / B_ent_spectral` (primary). No collapse.

---

## Axiom 3 — Temporal Healing (resolves Ghost #26)

A synthetic tectonic tear (external manifold perturbation) raises observed `B_ent_spectral`
at one scene. With memory, the persisted value decays geometrically back to baseline:

```
excess(n) = B_ent_spectral_persisted(tear+n) − baseline
excess ≈ excess(0) · α_persist^n          (geometric healing curve)
```

Measured: post-tear excess `[0.297, 0.162, 0.078, 0.047, 0.037]`, decay ratios
`[0.544, 0.484, 0.607] ≈ α_persist = 0.5`. Memoryless (`α_persist = 0`): excess
`[0.6, 0.031, 0.0]` — a delta spike forgotten in one scene (no smoothing).

This is **temporal manifold smoothing**: the engine's internal manifold-stress estimate
decays smoothly across scenes, so the EXP-503 restoring force acts over time rather than only
instantaneously. The gate `is_manifold_501` stays admissible throughout (the tear, smoothed,
never exceeds the elastic limit).

**Dual math / code:**

| Math | Code |
|------|------|
| `S_ent[k] ← α·mem + (1−α)·obs` | active-key branch of `persist_scene_504` |
| `S_ent[k] ← decay·mem; prune` | away-key branch |
| `excess ≈ excess₀·α^n` | healing-curve assertion (Fork A [6]/[7]) |

---

## Axiom 4 — Structural Index H_seed

```
H_seed = HASH(‖S_A‖ ⊕ ‖S_C‖ ⊕ ‖S_D‖ ⊕ S_ent_by_key ⊕ bze_ema ⊕ maint ⊕ B_ent_spectral ⊕ protocol)
```

A structural index only — never a semantic interpretation. Hashed at 6-decimal resolution.

**Ghost #27 — Claim-id-order nondeterminism (resolved here):** the landed gamma recursion sums
child contributions in claim-id (timestamp-seeded) order, so carried `S_A/S_C/S_D` *components*
vary ~1e-14 run-to-run. Hashing raw components at fine resolution hits rounding boundaries and
breaks reproducibility. Fix: hash intra-claim sectors by **norm** (stable to ~1e-14 and
P_yz-invariant); `S_ent` is bit-identical across runs. The index is therefore reproducible and,
being built entirely from P_yz-invariant quantities, **P_yz-invariant** (`H_seed_fwd = H_seed_mir`,
verified Fork B [5]).

---

## Axiom 5 — P_yz Invariance

All persisted quantities derive from P_yz-invariant observables: spatial keys (extents/centers),
per-claim `G_ent` norms, sector norms, and primary scalars. Hence persisted `B_ent_spectral`,
`S_ent`, the healing curve, the gate, and `H_seed` are P_yz-invariant.

Verified (Fork B, N=20→14): `max|B_ent_spectral_fwd−mir| = 6.94e-16`, `max|S_ent_fwd−mir| = 0.0`,
healing-curve delta `3.75e-16`, `H_seed_fwd == H_seed_mir` all scenes, `gate_fwd == gate_mir`.

---

## Ghost Notes

**Ghost #26 — Equilibrium Stiffness (RESOLVED):** memory lets the restoring force act across
scenes; a tear now heals on a geometric curve (Axiom 3).

**Ghost #27 — Claim-id-order Nondeterminism (RESOLVED for the index):** norm-based intra-claim
hashing (Axiom 4). Note: the underlying ~1e-14 component noise persists in the engine; it is
below all observable tolerances but should be remembered if bitwise state reproducibility is
ever required (deterministic claim-id seeding would be the EXP-50x fix).

**Ghost #28 — Spatial-key Drift (OPEN, EXP-505):** spatial keying assumes claims at the same
location across scenes correspond. Under genuinely moving claims (streaming worlds) keys drift;
a spatial-hash DAG linkage is required (EXP-505 target).

---

## EXP-504 Scope

Adds `persist_scene_504`, `seed_memory_init_504`, `seed_memory_hash_504`, `spatial_key_504`
(operators). No change to phi_ent_observe, phi_fb_manifold, is_manifold_501, S, W, or the
EXP-409 path. All Series 400, EXP-501/502/503 assertions remain valid.
