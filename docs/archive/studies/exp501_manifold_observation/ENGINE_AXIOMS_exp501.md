# ENGINE_AXIOMS_exp501 — Manifold Observation (Sheaf Coboundary G_ent)

**Protocol:** exp501-v1  
**Series:** 500  
**Inherits:** exp409-v1 and all prior  
**Author:** Daniel J. Dillberg — bigdilly95@gmail.com  
**Declaration hash:** `bfbf52c2977f436a78f1136555a0e46d00eae43eb95344fc679223961fa60a8b`  
**Status:** open  
**Gate source:** EXP-409 closure — Phi_fb sub-series complete; Series 500 target: inter-claim G-coupling

---

## Axiom 1 — Pipeline Extension

Series 400 pipeline (single-claim):
```
μ → Lτ → [Phi_fb → Bτ] → Rτ → Z → S → W → OBS
```

Series 500 pipeline (multi-claim manifold):
```
μ → Lτ → [Phi_fb → Bτ] → Rτ → Z → [Φ_ent → G_ent → S_ent] → S → W → OBS
```

`Φ_ent` is a stateless operator on the full active leaf set W_t. It reads Z values from all claims simultaneously after Rτ, before EMA accumulation. Insertion point invariant: S does not exist at insertion; W has not been confirmed; cross-stage mutation outside the declared mapping is prohibited.

`phi_ent_observe` signature:
```
phi_ent_observe(Z_claims, bboxes, S_ent_prev, alpha_ent, eps)
  → (G_ent_per_claim, S_ent, B_ent, N_edges, lambda_2)

inputs:
  Z_claims:    dict[claim_id → stalk ∈ ℝ^18]   (all active leaves)
  bboxes:      dict[claim_id → (lo, hi)]
  S_ent_prev:  dict[claim_id → float]           (per-claim EMA, caller-tracked)
  alpha_ent:   float = 0.5
  eps:         float = 1e-15

outputs:
  G_ent_per_claim:  dict[claim_id → float]   (local entanglement residual norm)
  S_ent:            dict[claim_id → float]   (updated EMA)
  B_ent:            float                    (global entanglement ratio)
  N_edges:          int                      (number of face-adjacent pairs)
  lambda_2:         float                    (Fiedler value of L_sheaf)
```

EXP-501 is **observation only**: no modification to Z, S, W, or Phi_fb dynamics. All Series 400 assertions remain valid.

---

## Axiom 2 — Face Adjacency (6-Connected)

Two claims i and j with bboxes (lo_i, hi_i), (lo_j, hi_j) are face-adjacent iff there exists exactly one axis k ∈ {0,1,2} such that:

```
|hi_i[k] − lo_j[k]| < tol  OR  |hi_j[k] − lo_i[k]| < tol        (touching faces)
AND  lo_i[d] < hi_j[d] − tol  AND  lo_j[d] < hi_i[d] − tol       (overlap in other two dims d≠k)
```

`tol = 1e-9`. Returns `(True, k)` or `(False, −1)`. 6-connected (face neighbors only; no edge or vertex adjacency). For K=92 leaves in a cubic octree: N_edges ≈ 3·K^(2/3) ≈ 60 pairs.

```python
def face_adjacent(bbox_i, bbox_j, tol=1e-9):
    lo_i, hi_i = bbox_i; lo_j, hi_j = bbox_j
    for k in range(3):
        touch = (abs(hi_i[k]-lo_j[k]) < tol) or (abs(hi_j[k]-lo_i[k]) < tol)
        if touch:
            others = [d for d in range(3) if d != k]
            overlap = all(lo_i[d] < hi_j[d]-tol and lo_j[d] < hi_i[d]-tol
                          for d in others)
            if overlap:
                return True, k
    return False, -1
```

---

## Axiom 3 — Restriction Maps F_ij (All Sectors)

For face-adjacent claims i and j sharing face normal axis k, the restriction map F_ij encodes the expected value of stalk_j as seen from claim i's boundary. Perfect glue condition: `F_ij · stalk_j = stalk_i` for all neighbor pairs.

F_ij is 18×18 block-diagonal: `F_ij = block_diag(F^A, F^B, F^C_k, F^D_k)`.

**Sector A [0:4] — (mass, r, g, b):** scalar fields, continuity condition.
```
F^A = I_4     G^A_ij = stalk_j[0:4] − stalk_i[0:4]
```

**Sector B [4:8] — (x, y, z, w):** position fields, continuity condition.
```
F^B = I_4     G^B_ij = stalk_j[4:8] − stalk_i[4:8]
```

**Sector C [8:12] — (nx, ny, nz, κ):** outward normals are anti-parallel at a shared face; curvature κ is a scalar (continuous).
```
F^C_k = diag(c_0, c_1, c_2, 1)   where c_d = −1 if d==k else +1

G^C_ij = F^C_k · stalk_j[8:12] − stalk_i[8:12]
```

Perfect glue: `n_j[k] = −n_i[k]`, `n_j[d≠k] = n_i[d≠k]`, `κ_j = κ_i`.

**Sector D [12:18] — (log_l11, log_l22, log_l33, l21, l31, l32):** log-Cholesky covariance factors. Gaussian ellipsoids must be mirror images across the shared face (see Axiom 4).

---

## Axiom 4 — Sector D XOR Sign Rule (Derivation)

The boundary condition for Sector D is `Σ_i = R_k · Σ_j · R_k^T` where `R_k = diag(−1 if d==k else +1)`. This is the same reflection applied in EXP-401 Fork B, now applied between neighboring claims rather than between forward/mirror trajectories.

**Derivation:**  L is the lower-triangular Cholesky factor, Σ = L·L^T.

```
Σ_mirror = R_k · Σ · R_k^T = (R_k · L) · (R_k · L)^T
```

`R_k · L` has negative diagonal entry at position k. To restore the positive-diagonal Cholesky form, right-multiply by `D_k = diag(−1 at position k, +1 elsewhere)`:

```
L_mirror = R_k · L · D_k                  [positive diagonal restored]
Verify: L_mirror · L_mirror^T = R_k · L · D_k · D_k · L^T · R_k^T = R_k · Σ · R_k^T  ✓
```

Column j of L is multiplied by `R_k[j,j] · D_k[j,j]`:
- Column j ≠ k: `R_k[j,j] · D_k[j,j] = (+1)·(+1) = +1` → unchanged
- Column k: `R_k[k,k] · D_k[k,k] = (−1)·(−1) = +1` → unchanged for diagonal entry

For off-diagonal entry L[p,q] (p > q, coupling axes p and q):
- Sign = `R_k[p,p] · D_k[q,q]`
- `R_k[p,p] = −1 if p==k else +1`
- `D_k[q,q] = −1 if q==k else +1`
- Combined: sign flips iff exactly one of {p,q} equals k — the **XOR rule**.

**XOR sign table (verified max error = 0.00e+00 for all k):**

| Parameter | k=0 (x-face) | k=1 (y-face) | k=2 (z-face) | Coupled axes |
|-----------|:---:|:---:|:---:|------|
| log_l11   | +1 | +1 | +1 | — (invariant: diagonal) |
| log_l22   | +1 | +1 | +1 | — (invariant: diagonal) |
| log_l33   | +1 | +1 | +1 | — (invariant: diagonal) |
| l21 (xy)  | −1 | −1 | +1 | {0,1}: flips for k=0,1 |
| l31 (xz)  | −1 | +1 | −1 | {0,2}: flips for k=0,2 |
| l32 (yz)  | +1 | −1 | −1 | {1,2}: flips for k=1,2 |

**Involution property:** `F^D_k(F^D_k(stalk, k), k) == stalk` for all k. Each face-adjacent pair has a unique shared face normal k; applying the restriction map twice recovers the original. Verified for k=0,1,2.

Physical interpretation: the three log-diagonal entries (log-variances) are scalars — equal on both sides of any face. The three off-diagonal entries (covariance tilts) are pseudo-vectors — they flip sign when crossing the face they couple to. This is the Dentatus *Zusammenhang* (German: differential-geometric connection on the fiber bundle of covariance ellipsoids).

**Code:**
```python
_XOR_SIGNS_D = {0: [1,1,1,-1,-1,1], 1: [1,1,1,-1,1,-1], 2: [1,1,1,1,-1,-1]}
_XOR_SIGNS_C = {0: [-1,1,1,1], 1: [1,-1,1,1], 2: [1,1,-1,1]}

def apply_F_ij_D(stalk_D, face_axis):
    return np.array(stalk_D) * np.array(_XOR_SIGNS_D[face_axis])

def apply_F_ij_C(stalk_C, face_axis):
    return np.array(stalk_C) * np.array(_XOR_SIGNS_C[face_axis])

def apply_F_ij(stalk, face_axis):
    """Full 18-dim restriction map for face normal axis k."""
    s = stalk.copy()
    s[8:12]  = apply_F_ij_C(stalk[8:12],  face_axis)   # Sector C
    s[12:18] = apply_F_ij_D(stalk[12:18], face_axis)   # Sector D
    return s  # Sectors A, B: identity
```

---

## Axiom 5 — Sheaf Coboundary and Entanglement Ghost

The entanglement ghost per directed edge (i→j) is the coboundary δ_0:

```
G_ij^{ent} = F_ij · stalk_j − stalk_i   ∈ ℝ^18

δ_0(Z)_e = G_ij^{ent}  for edge e = (i,j)
```

For the undirected neighbor graph, use canonical ordering (id_i < id_j). The sheaf Laplacian:

```
L_sheaf = δ_0^T · δ_0     (N_claims × N_claims, scalar approximation)
Z^T L_sheaf Z = ‖δ_0(Z)‖^2 = Σ_{(i,j)∈E} ‖G_ij^{ent}‖^2    (total deformation cost)
```

Per-claim local entanglement residual:
```
G_ent_i = ‖ Σ_{j∈N(i)} G_ij^{ent} ‖                          (sum then norm)
```

EMA accumulation (primary-space scalar, caller-tracked per claim):
```
S_ent_i(t+1) = alpha_ent · S_ent_i(t) + (1−alpha_ent) · G_ent_i(t)
```

Global observable:
```
B_ent(t)    = ‖S_ent‖ / (‖Z_active‖ + ε)                     [entanglement ratio]
Ω_ent(t)    = Z^T L_sheaf Z / (‖Z‖^2 + ε)                    [Rayleigh quotient]
lambda_2(t) = second smallest eigenvalue of L_sheaf            [Fiedler: algebraic connectivity]
```

**Dual arithmetic:** `G_ent_i` and `S_ent_i` are dual-space scalars (residuals of the inter-claim restriction maps). `B_ent` bridges dual→primary via norm operations. No algebraic collapse with intra-claim `G_t = Z_t − Π_W(Z_t)`. The inter-claim and intra-claim ghost channels are **orthogonal**:

```
S_intra ∈ ℝ^{d_stalk}   (EXP-401: S_A, S_D per single claim)
S_ent   ∈ ℝ^{N_claims}  (EXP-501: per-claim entanglement EMA)
```

---

## Axiom 6 — P_yz Invariance

Under P_yz (x→−x), the face-adjacent graph maps: pair (i,j) with face_axis k maps to pair (P(i), P(j)) with the same face_axis k. Proof: P_yz negates x-coordinates; bbox adjacency is determined by `|hi[k] − lo[k]|` extents and overlap — both P_yz-invariant.

For the restriction maps under P_yz:
- Sectors A, B (identity): trivially invariant.
- Sector C: `apply_F_ij_C(R_pyz · stalk_C, k) = R_pyz · apply_F_ij_C(stalk_C, k)` — the normal-flip and P_yz commute because both are diagonal sign operators on the same 3D normal vector.
- Sector D: `apply_F_ij_D(R_D · stalk_D, k) = R_D · apply_F_ij_D(stalk_D, k)` where `R_D = diag(1,1,1,−1,−1,1)` (EXP-401 covariance P_yz transform). The XOR and covariance transforms commute because both are diagonal sign operators on ℝ^6.

Therefore `‖G_ij^{ent}‖ = ‖G_{P(i)P(j)}^{ent}‖` and `B_ent_fwd = B_ent_mir` exactly.

**Lambda_2 P_yz invariance:** L_sheaf is constructed from the adjacency graph; graph isomorphism under P_yz → identical eigenvalues → `lambda_2_fwd = lambda_2_mir`.

---

## Axiom 7 — Geometric Interpretation

**Global section (ker δ_0):** The set of claim assignments Z where G_ij^{ent}=0 for all edges — the manifold is perfectly continuous. `Ω_ent = 0`.

**Fiedler value λ_2:** The smallest non-zero eigenvalue of L_sheaf. Measures algebraic connectivity of the neighbor graph. For a 2×2×1 face-adjacent grid: λ_2=2 (verified). For the full K=92 octree: λ_2 depends on tree depth and Zeeman field. `λ_2/N_claims = ε_manifold_crit` (critical elastic limit — EXP-502 calibration target).

**Gravitational backreaction (manifold):**
```
Ω_fb_ent = B_ent / (1 + B_ent)    [bounded: 0 ≤ Ω_fb_ent < 1]
```

Distinguished from intra-claim Ω_fb = |β_Z_eff − β_Z_base| / β_Z_base (unbounded). The entanglement backreaction is bounded because the per-claim projection normalizes by N_edges.

---

## Ghost Notes

**Ghost #21 — Zusammenhang Stiffness:** If ε_manifold_crit (calibrated from B_ent tail in EXP-502) is set below the natural B_ent baseline, `is_manifold_501` will fail on every step — the octree is structurally over-coupled. Observable: `B_ent_median` from EXP-501 Fork A gives the lower bound for valid ε_manifold.

**Ghost #22 — Neighbor Explosion:** At K=92 leaves, N_edges≈60. S_ent_i accumulates contributions from degree(i) neighbors. High-degree claims (corner octants) accumulate more signal. The per-claim norm `‖Σ_j G_ij^{ent}‖` is not normalized by degree — claims with more neighbors have higher intrinsic G_ent. Observable: `max_degree / mean_degree` (degree heterogeneity ratio).

**Ghost #23 — Temporal Decoherence (Stateful Seed precursor):** S_ent_prev is caller-tracked and reinitialized to zero at cold start. Across scenes, the entanglement EMA must be either reset (losing manifold memory) or transferred (requiring the Stateful Seed protocol from EXP-504). EXP-501 uses cold-start reset; the decoherence cost `α_ent^T_away` is an observable for EXP-504 design.

---

## EXP-501 Scope (Observation Only)

EXP-501 adds `phi_ent_observe` as a pure measurement operator. No modification to Phi_fb, Bτ, Rτ, S, or W. The existing `apply_gamma_409_recursive` call chain is unchanged. B_ent and lambda_2 appear in OBS output only.

**New caller state (primary scalars):**
- `S_ent_prev`: dict[claim_id → float], initialized {id: 0.0 for id in active}
- `alpha_ent = 0.5` (fixed; tune in EXP-503)

**EXP-502 gate:** B_ent baseline from EXP-501 Fork A → calibrate ε_manifold → write `is_manifold_501` validity predicate.

**EXP-503 gate:** is_manifold_501 stable → introduce Phi_fb_manifold: `β_Z_eff = f(B_A, B_D, B_ent)` — Zeeman as physical restoring force for manifold tears.

**EXP-504 gate:** Phi_fb_manifold stable → Stateful Seed: SectorMemory struct persisting `{S_A, S_D, S_ent, bze_ema_prev, maint_latched}` across scenes with exponential decay for inactive sectors.

---

## Pioneer: Spectral Feedback (EXP-503+ Option)

Instead of scalar B_ent, project G_ent per claim onto the k Fiedler eigenvectors of L_sheaf:

```python
V_k = eigvecs(L_sheaf)[:, 1:k+1]           # skip λ=0 (rigid translation)
G_ent_spectral = V_k.T @ G_ent_per_claim    # (k,) slow-mode projection
B_ent_spectral = norm(G_ent_spectral) / (norm(Z_active) + eps)
```

Phi_fb_manifold responds only to large-scale (low-eigenvalue) manifold deformations — tectonic shifts — not local surface noise. High-frequency modes are suppressed. The Fiedler vector bisects the claim manifold along its natural fault line.

Cost: L_sheaf eigendecomposition per step (O(N^3), N≤200 at K_budget=2048). Amortizable: L_sheaf changes only when the active leaf set W_t changes, which is bounded by lc_transition events (rare at EMA equilibrium).
