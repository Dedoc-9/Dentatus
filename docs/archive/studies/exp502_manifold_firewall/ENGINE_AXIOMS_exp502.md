# ENGINE_AXIOMS_exp502 — Manifold Firewall (is_manifold_501)

**Protocol:** exp502-v1
**Series:** 500
**Inherits:** exp501-v1 and all prior
**Author:** Daniel J. Dillberg — bigdilly95@gmail.com
**Declaration hash:** `0979f7f520421a28bc37a7e7aec9e8f7e946f4adb459f55b64718188ea966af8`
**Status:** open
**Gate source:** EXP-501 closure — B_ent baseline established; Ghost #22 degree bias; calibrate ε_manifold

---

## Axiom 1 — Degree Normalization (Ghost #22 fix)

EXP-501 accumulated the per-claim entanglement residual as `G_ent_i = ‖Σ_j G_ij^{ent}‖`,
which is monotone in `deg(i)`: corner/high-degree octants accumulate more signal purely from
having more neighbors, not from greater physical deformation. EXP-502 removes this bias:

```
G_ent_i = ‖ Σ_{j∈N(i)} G_ij^{ent} ‖ / sqrt(deg(i))        (degree_normalize=True)
```

`deg(i)` = number of incident face-adjacent edges. Implemented as a backward-compatible
keyword on `phi_ent_observe`; `degree_normalize=False` preserves EXP-501 byte-identically
(hash continuity of the landed EXP-501 study is not disturbed).

**P_yz invariance:** `deg(i)` is a graph-isomorphism invariant under P_yz (Axiom 6 of EXP-501:
adjacency depends only on `|hi−lo|` extents and overlap). Dividing by `sqrt(deg)` is therefore
P_yz-covariant and Fork B symmetry holds at machine precision.

---

## Axiom 2 — Elastic Limit ε_manifold (Calibration)

```
B_ent_normalized = ‖S_ent‖ / (‖Z_active‖ + ε)            with degree_normalize=True
```

Measured baselines (seed octree, 71 leaves, ~198 edges):

| Quantity | Value |
|----------|-------|
| B_ent un-normalized median (EXP-501) | ≈ 0.678 |
| B_ent degree-normalized median (EXP-502) | ≈ 0.52 |
| Preregistered ε_manifold | **0.8** |
| margin ε / normalized baseline | ≈ 1.5× (mildly permissive) |

ε_manifold = 0.8 is a **declared constant** (preregistration). Against the degree-normalized
baseline it admits the natural octree with ~1.5× headroom and rejects a deformation excursion
above 0.8. The normalized median printed by Fork A is the lower bound for any future tightening
(Ghost #21 — Zusammenhang Stiffness: setting ε below the natural baseline fails every step).

---

## Axiom 3 — The Firewall Predicate

```
is_manifold_501(B_ent_normalized, ε_manifold = 0.8) :=  (B_ent_normalized ≤ ε_manifold)
```

State admissible iff the gate returns True. A state whose normalized inter-claim deformation
exceeds ε_manifold is structurally torn ("the skin breaks") and is rejected; per protocol the
engine reverts to the last valid hashed state. Pure scalar predicate — no MuState mutation,
observable purity preserved.

**Per-claim strict variant** (`is_manifold_501_perclaim`): admissible iff
`max_i g_i/(‖Z_active‖+ε) ≤ ε_manifold`. Catches a single localized tear that a global average
masks (Ghost #22 corollary). Use alongside the global gate for high-fidelity scenes.

---

## Axiom 4 — EXP-503 Scaffold (Spectral, landed observation-only)

`spectral_ent_project` and `build_L_sheaf_503` are landed in this study as observation-only
helpers, NOT wired into β_Z_eff. They project the per-claim residual onto the k lowest
non-trivial Fiedler modes of L_sheaf:

```
V_k = eigvecs(L_sheaf)[:, 1:k+1]            # skip λ_0 (rigid translation)
g_spectral = V_k^T · G_ent                  # (k,) slow-mode coefficients
B_ent_spectral = ‖g_spectral‖ / (‖Z_active‖ + ε)
```

Measured (k=3, seed octree): `λ_modes = [0.316, 0.808, 0.940]`, `B_ent_spectral ≈ 0.125`.
The Fiedler vector (λ_2 eigenvector) bisects the claim manifold along its natural fault line.
EXP-503 proper will make `β_Z_eff = f(B_A, B_D, B_ent_spectral)` so the Zeeman focus responds
to tectonic (low-mode) deformation rather than surface noise. Affordable because L_sheaf changes
only on lc-transition events, which the EXP-409 hysteresis latch makes rare.

---

## Ghost Notes

**Ghost #22 — Neighbor Explosion (RESOLVED here):** degree normalization removes the corner-octant
bias. Residual observable: degree heterogeneity `max_deg/mean_deg` for monitoring.

**Ghost #21 — Zusammenhang Stiffness (OPEN, calibration-bound):** ε_manifold must stay ≥ the
degree-normalized baseline (~0.52). 0.8 satisfies this. If a future scene raises the baseline
above 0.8, retune ε here in `validity.EPS_MANIFOLD_502`, not in the operator.

**Ghost #24 — Cold-reset vs accumulation (NEW):** the firewall reads B_ent under the same
S_ent protocol used to calibrate it. Fork A cold-resets S_ent per step (EXP-501 scope); a
stateful-seed transfer (EXP-504) will shift the baseline and require recalibration of ε.

---

## EXP-502 Scope

Adds degree normalization (operator flag) + `is_manifold_501` firewall (validity predicate)
+ EXP-503 spectral scaffold (operators). No change to Phi_fb, Bτ, Rτ, S, W dynamics. All
Series 400 and EXP-501 assertions remain valid.
