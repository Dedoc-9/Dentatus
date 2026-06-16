# ENGINE_AXIOMS_exp506 — Stitched Local Fiedler (galactic-scale fault)

**Protocol:** exp506-v1 · **Series:** 500 · **Inherits:** exp505-v1
**Primary architect:** Daniel J. Dillberg — bigdilly95@gmail.com
**Declaration hash:** `d69b59b3ad635e16a0194e5087fa0aaa6773f378565570d3bedb46cac8d397ed`
**Status:** open · **Location:** `game/observability/sectioned_fiedler.py` (decoupled)

---

## Axiom 1 — The disjointedness trap

The global Fiedler vector is O(N³). At scale we section the world and compute LOCAL spectral
structure. But local Fiedler vectors are independent objects with arbitrary sign, scale, AND
mode (the section's own connectivity mode ≠ the restriction of the global mode). Butting them
together gives **disjoint, spurious fault seams** — measured: a naive per-section approach put
**21** spurious fault edges on section boundaries.

## Axiom 2 — Two-level Galerkin coarsening

```
coarse:  L_c = Pᵀ L P,   M_c = Pᵀ P   (P = section membership)
         generalized eigenproblem L_c c = λ M_c c  ->  per-section coarse field c
```

`c` is the GLOBAL fault at section resolution — a genuine global mode, O(S³). Verified: **100%
section-sign agreement** with the global Fiedler (the coarse field puts every section on the
correct side of the world-fault).

## Axiom 3 — Partition-of-unity stitch with a dynamic spectral-diameter halo

The coarse field is interpolated to leaves by a Gaussian partition of unity over section
centroids, giving a C⁰ field whose zero-set is the continuous fault line. The Gaussian width per
section is the **halo**:

```
σ_s = κ · spectral_diameter(s) · section_extent,   clamped to [1 leaf, section extent]
spectral_diameter(s) = 1 / sqrt(λ₂^local(s))
```

The halo is **dynamic — a fraction of the section's spectral diameter**, not a fixed leaf count:
wide where the local fault mode is gentle (small λ₂, long correlation), tight where it is steep.
The **1-leaf floor** guarantees the halo contains the δ₀ inter-section edges (EXP-501); the
section-extent cap bounds it. On a uniform octree λ₂^local≈1 so the halo clamps to the floor —
the method correctly chooses minimal overlap, beating a fixed halo that over-smooths.

## Axiom 4 — Results

```
                       agreement   spurious seams   fault edges   cost
naive independent          —             21             —          —
fixed halo (σ=0.30)       90%             2             42        17x cheaper
DYNAMIC spectral halo     99%             0             32        17x cheaper   <- == global's 32
```

The dynamic stitch reproduces the global fault **exactly** (32 fault edges, 0 spurious seams) at
O(S³ + Σ n_s³) ≈ 17× cheaper than O(N³). Fork A 10/10, Fork B 5/5 (fault structure P_yz-invariant).

## Ghost Notes

**Ghost #38 — Coarse-grid resolution:** at grid (2,2,2) the fault runs along section boundaries
(100% section agreement). Too-fine a grid fragments the coarse mode (agreement drops); the grid
should match the fault's natural scale. Adaptive grid refinement along the fault is the extension.

## Scope

`dentatus/core.py` exposes `face_adjacent_501`/`build_L_sheaf_503`; the stitch lives in
`game/observability/sectioned_fiedler.py`. No engine logic change. `PYTHONHASHSEED=0`.
