# ENGINE AXIOMS — EXP-304 Affine Reality Engine (Series 300, fourth study)

**Preregistration status**: GATE LOCKED
**Protocol version**: exp304-v1
**Inherits from**: exp303-v1 → exp302-v1 → exp301-v1
**Workspace**: Reality_Engine/studies/exp304_affine_engine/
**declaration_hash**: `a369ce20f55674f14476a6a56f785e4496baa35c2c8a7a72ba95577adb1c230b`

---

## 0. Motivation (from EXP-302 §7 Known Limits)

EXP-302 identified two limits surfaced during execution:

1. **Algebraic-geometric conflation**: position dims (0–2 in ℝ^6) obey sum conservation
   (Σ pos_i = pos_parent), producing child centroids that are algebraic coordinates summing
   to the parent rather than geometric sub-centroids. Negative position components are
   algebraically valid but geometrically uninterpretable.

2. **Chiral decomposition basis**: `_orthogonal_decompose` derives its orthonormal frame
   from `hash(stalk_parent, N)`. The basis is deterministic but reflection-arbitrary. A
   mirror-image parent stalk does not produce mirror-image child stalks. Chirality lives
   in the stalk decomposition only; bbox geometry is already P-invariant.

EXP-304 resolves both by splitting the stalk into two sectors with distinct conservation
laws and restriction map classes.

---

## 1. Stalk Schema — Dual Sector Architecture

    F(v) ∈ ℝ^8  =  [Sector A | Sector B]

    Sector A (dims 0–3): [mass, r, g, b]
      - mass: scalar non-negative weight (total claim mass)
      - r, g, b: color (RGB, normalised [0,1]^3)
      - Conservation: SUM    Σᵢ stalk_A(child_i) = stalk_A(parent)

    Sector B (dims 4–7): [x, y, z, w]
      - x, y, z: spatial centroid in ℝ^3
      - w: homogeneous coordinate, fixed = 1.0 for all valid claims
      - Conservation: BARYCENTRIC    Σᵢ ωᵢ · stalk_B(child_i) = stalk_B(parent)
        where Σᵢ ωᵢ = 1,  ωᵢ > 0
        Invariant: stalk_B[3] = w = 1.0  (homogeneous normalisation)

    seed_stalk = [1.0, 1.0, 1.0, 1.0,  0.5, 0.5, 0.5, 1.0]
                  mass  r    g    b      x    y    z    w

The two sectors are algebraically orthogonal: no cross-sector terms in any operator.
Dual arithmetic separation (EXP-301 §4) is preserved.

---

## 2. Operators

### 2.1 Φ_A — Sector A Partition (inherited, renamed for clarity)

Applies `_orthogonal_decompose(stalk_A_parent, N)` to dims 0–3.
Sum conservation: Σᵢ stalk_A(child_i) = stalk_A(parent).
Restriction map: F_A(parent→child_i) = outer(stalk_A_i, stalk_A_parent) / ||stalk_A_parent||²
Cost: C₀ · exp(β · ||S_t||) unchanged.

### 2.2 Φ_B — Sector B Partition (new)

**Signature**: `Φ_B(v, N, weights=None) → {v_1,...,v_N}`

**Inputs**:
- stalk_B_parent ∈ ℝ^4 with stalk_B_parent[3] = 1.0
- weights: optional list of N positive floats (default: uniform 1/N each)
  Normalised: ωᵢ = weights[i] / Σ weights[j]

**Output stalks (Sector B)**:

    stalk_B(child_i) = F_B(parent→child_i) · stalk_B_parent

where F_B ∈ GL(4) is an affine map satisfying:

    Σᵢ ωᵢ · F_B(parent→child_i) · stalk_B_parent = stalk_B_parent

For uniform subdivision (ωᵢ = 1/N), F_B assigns:

    stalk_B(child_i) = [centroid_x(bbox_i), centroid_y(bbox_i), centroid_z(bbox_i), 1.0]

i.e., child Sector B centroid = geometric centroid of its bounding box.
Barycentric constraint: Σᵢ (1/N) · stalk_B(child_i) = centroid(parent_bbox) = stalk_B(parent)[0:3].
This holds iff parent_bbox centroid = parent stalk_B centroid (enforced at seed declaration).

**Restriction map**:

    F_B(parent→child_i) = [diag(1,1,1,ωᵢ) | translation_to_bbox_centroid_i]
    F_B ∈ GL(4), det(F_B) = ωᵢ

**Chirality tracking**:
det_sign = sign(det(F_B)) = +1 for all uniform bbox splits (ωᵢ > 0).
Stored as `Entailment.det_sign: int ∈ {-1, +1}`.
det_sign = -1 indicates a reflection was applied (legal but flagged).

**Cost**: same as Φ_A (backreaction applied to combined ||S_t||).

### 2.3 Γ (inherited from EXP-303)

Geometric channel: bbox split via `_compute_child_bboxes` — unchanged.
Algebraic channel: now uses Φ_A (Sector A) + Φ_B (Sector B) in sequence.
ωᵢ for Φ_B set to vol(bbox_child_i) / vol(bbox_parent) (volume-proportional weights).

### 2.4 Ψ, Ω (inherited unchanged)

Ψ: stalk(v_new) = Σᵢ αᵢ · stalk(v_i) over full ℝ^8.
  Sector B constraint: if Σᵢ αᵢ = 1, then w-component is automatically conserved.
Ω: artifact.stalk = stalk ∈ ℝ^8; K_bound unchanged.

---

## 3. Validity Predicates

Three predicates, all must pass after every state update:

    is_valid_A(μ_t):
      for each PARTITION edge (src→tgt):
        ||Σ F_A(uᵢ→v)(stalk_A_{uᵢ}) − stalk_A_v|| < 1e-8
      [inherited E-301-003, restricted to Sector A dims]

    is_valid_B(μ_t):
      for each PARTITION edge (src→tgt):
        |stalk_B(tgt)[3] − 1.0| < 1e-10          [homogeneous invariant]
        |Σᵢ ωᵢ · stalk_B(child_i) − stalk_B(parent)| < 1e-8  [barycentric]

    is_spatially_valid(μ_t):
      [inherited from EXP-303 — bbox containment on SPATIAL edges]

Neither predicate implies the other. All three are independent.

---

## 4. Ghost Channel (full d=8)

    Z_t = Σ_{v ∈ W_t} stalk(v)  ∈ ℝ^8
    G_t = Z_t − Π_{W_t}(Z_t)      [base ghost, over full 8 dims]
    S_{t+1} = α·S_t + (1−α)·G_t   [EMA, α inherited]
    B(t) = ||S_t|| / (||Z_t|| + ε) [observable]

Sector separation in the ghost channel is NOT applied: G_t is a single ℝ^8 residual.
Ghost closure: Gₜ is numeric residual only; no interpretation, no direct control.

Backreaction:
    C(Op, t) = C₀ · exp(β · ||S_t||)
Applied uniformly to Φ_A, Φ_B, Γ cost. Ψ and Ω cost unchanged (free or fixed).

---

## 5. Entailment Schema Extension

New fields on `Entailment` (for PARTITION edges involving Φ_B):

    omega: float          # barycentric weight ωᵢ for this child; default 1/N
    det_sign: int         # sign(det(F_B)); +1 or -1; +1 for all non-reflective maps

These fields are NOT included in the state hash H_t.
H_t = HASH(μ_t ⊕ Z_t ⊕ S_t ⊕ W_t ⊕ protocol_version) — unchanged.

---

## 6. Conservation Law Comparison (Series 300)

| experiment | sector | conservation law | operator | geometric interpretation |
|------------|--------|-----------------|----------|-------------------------|
| EXP-301 | ℝ^4 (unified) | sum: Σ stalk_i = stalk | Φ | none (symbolic) |
| EXP-302 | ℝ^6 pos×col | sum: Σ stalk_i = stalk | Φ | centroid sum (unphysical) |
| EXP-303 | ℝ^9 pos×col×nrm | sum: Σ stalk_i = stalk | Φ + Γ | bbox splits physical; stalk unphysical |
| **EXP-304** | **Sector A ℝ^4** | **sum** | **Φ_A** | **mass/color additive** |
| **EXP-304** | **Sector B ℝ^4** | **barycentric: Σ ω_i·s_i = s** | **Φ_B** | **centroid stays in convex hull of parent** |

---

## 7. Known Limits of EXP-304

| limit | description | resolution path |
|-------|-------------|-----------------|
| normal vector dropped | EXP-303 had nx,ny,nz (dims 6–8); EXP-304 replaces with w=1 | EXP-305: d=12 [mass,r,g,b,x,y,z,w,nx,ny,nz,κ] |
| ωᵢ = vol ratio only for uniform bbox | non-uniform subdivision requires explicit weight schedule | EXP-305: adaptive weight allocation from bbox volume ratios |
| single Φ_B implementation | barycentric map assumes bbox centroid assignment; non-centroid child positions require custom F_B | EXP-305: general affine F_B with PCA-seeded child centroids |
| det_sign tracking not yet enforced as validity predicate | det_sign stored but no predicate asserts det_sign consistency across R1/R2 | EXP-305: P-invariance test: check det_sign(Φ_B(mirror(v))) = det_sign(Φ_B(v)) |
| ghost channel not sector-split | G_t computed over full ℝ^8; Sector A and B ghost components not separated | EXP-305: dual ghost G_A, G_B with independent EMA tracks |

---

## 8. Commitment Chain

EXP-301 (ℝ^4 symbolic) →
EXP-302 (ℝ^6 pos×col; sum conservation; chirality noted in §7) →
EXP-303 (ℝ^9 pos×col×nrm; Γ operator; bbox containment) →
**EXP-304 (ℝ^8 dual-sector; Sector A sum; Sector B barycentric+homogeneous; P-invariant affine maps)**
