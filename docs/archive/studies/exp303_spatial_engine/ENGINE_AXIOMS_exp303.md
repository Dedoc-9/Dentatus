# ENGINE AXIOMS — EXP-303 Spatial Engine (Series 300, third study)

**Preregistration status**: GATE LOCKED — commit before Seed_0_spatial declaration.
**Protocol version**: exp303-v1
**Inherits from**: exp302-v1 → exp301-v1
**Workspace**: Reality_Engine/studies/exp303_spatial_engine/

---

## 0. Relationship to EXP-301/302

EXP-303 adds one new operator (Γ) and one new validity predicate (bbox containment).
All EXP-301 operators (Φ/Ψ/Ω), validity (E-301-003), and interchange laws (R1/R2/R3)
are inherited unchanged. The algebraic channel is structurally identical to EXP-301.

Key architectural decision (preregistered):
  Algebraic channel (stalk, Z, G, S, B, backreaction) and geometric channel (bbox)
  are SEPARATE. Stalk conservation law (Σᵢ stalk_i = stalk_parent) is unchanged.
  Bbox containment is an additional predicate, not a replacement.
  This preserves dual arithmetic separation from EXP-301 §4.

---

## 1. Geometric Stalk Schema

    F(v) ∈ ℝ^9 = [x, y, z,  r, g, b,  nx, ny, nz]

    dims 0–2: position centroid in ℝ^3
    dims 3–5: color (RGB, normalised [0,1]^3)
    dims 6–8: surface normal (unit vector)

    seed_stalk    = [0.5, 0.5, 0.5,  1.0, 1.0, 1.0,  0.0, 0.0, 1.0]
    seed_bbox_lo  = [0.0, 0.0, 0.0]
    seed_bbox_hi  = [1.0, 1.0, 1.0]

d=9 satisfies the _orthogonal_decompose precondition d ≥ N for all
registered keys including octree_split (N=8 ≤ 9).

---

## 2. Γ Operator — Spatial Subdivision

**Signature**: `Γ(v, partition_key) → {v_1, ..., v_N} | PartitionError`

**Preconditions**:
- v ∈ W_t
- partition_key ∈ SPATIAL_KEYS
- mu.claims[v].bbox is not None
- K-bound: Σᵢ K(payload_i) ≤ K(payload_v) + C_KBOUND·log(N)  (E-301-002)
- dim check: d ≥ N  (from _orthogonal_decompose)

**Two independent channels**:

Algebraic channel (unchanged from Φ):
    stalk(child_i) via _orthogonal_decompose(stalk_parent, N)
    Σᵢ stalk(child_i) = stalk_parent  (sum conservation)
    Restriction map: F(parent→child_i) = outer(stalk_i, stalk_parent)/||stalk_parent||²

Geometric channel (new):
    bbox(child_i) computed by _compute_child_bboxes(bbox_parent, key)
    Stored as Claim.bbox field — spatial metadata, NOT part of id hash
    Entailment type: SPATIAL (distinct from PARTITION/SYNTHESIS)

**Spatial partition keys (preregistered)**:

| key | N | bisection |
|-----|---|-----------|
| axis_bisect_x | 2 | bisect along x at mid_x=(lo_x+hi_x)/2 |
| axis_bisect_y | 2 | bisect along y at mid_y |
| axis_bisect_z | 2 | bisect along z at mid_z |
| octree_split  | 8 | bisect all three axes; children in Morton order |

Octree child bbox ordering (bit2=x, bit1=y, bit0=z):

    i=0: lo=[lo_x, lo_y, lo_z]  hi=[mid_x, mid_y, mid_z]
    i=1: lo=[lo_x, lo_y, mid_z] hi=[mid_x, mid_y, hi_z]
    i=2: lo=[lo_x, mid_y, lo_z] hi=[mid_x, hi_y,  mid_z]
    i=3: lo=[lo_x, mid_y, mid_z] hi=[mid_x, hi_y, hi_z]
    i=4: lo=[mid_x, lo_y, lo_z]  hi=[hi_x, mid_y, mid_z]
    i=5: lo=[mid_x, lo_y, mid_z] hi=[hi_x, mid_y, hi_z]
    i=6: lo=[mid_x, mid_y, lo_z] hi=[hi_x, hi_y,  mid_z]
    i=7: lo=[mid_x, mid_y, mid_z] hi=[hi_x, hi_y, hi_z]

**Post-conditions**:
- is_valid(new_state): forward entailment consistency on algebraic stalks
- is_spatially_valid(new_state): bbox(child_i) ⊆ bbox(parent) for all SPATIAL edges

**Cost**: C₀ = 1.0 (same as Φ), with backreaction exp(β·||S_t||).

---

## 3. Validity Predicate Extension

Two predicates now run after every Γ:

    is_valid(μ_t)           [inherited E-301-003 — algebraic channel]
    is_spatially_valid(μ_t) [EXP-303 — geometric channel]

Both must pass. Failure in either triggers PartitionError and state revert.

is_spatially_valid:
    for each (src→tgt) ∈ E_t with etype=SPATIAL:
      if both claims have bbox:
        assert bbox(tgt).lo ≥ bbox(src).lo  (component-wise, tol=1e-10)
        assert bbox(tgt).hi ≤ bbox(src).hi

The two predicates are orthogonal:
  is_valid checks algebraic stalk consistency (restriction maps)
  is_spatially_valid checks geometric containment (bbox metadata)
Neither implies the other.

---

## 4. Bbox field on Claim

    Claim.bbox: Optional[Tuple[np.ndarray, np.ndarray]]
                = (lo ∈ ℝ^3, hi ∈ ℝ^3)

bbox is NOT included in Claim.id hash (it is spatial metadata, not claim identity).
Claim.id = HASH(provenance ⊕ payload ⊕ t ⊕ protocol_version) — unchanged.

Seed_0_spatial bbox is declared in SEED_DECLARATION_exp303.json and assigned
at Claim construction time. All Γ children inherit bbox from _compute_child_bboxes.
Φ/Ψ children (non-spatial operators) have bbox=None unless explicitly assigned.

---

## 5. Known Limits of EXP-303

| limit | description | resolution path |
|-------|-------------|-----------------|
| stalk pos ≠ bbox centroid | algebraic stalk components are not constrained to bbox interior | EXP-304: affine restriction maps or explicit centroid encoding |
| normal dims not normalized post-Phi | _orthogonal_decompose may produce non-unit normals | EXP-304: post-Gamma normal renormalization operator |
| G_t = 0 for lossless Gamma | E-301-004 invariant persists; path-coherence residuals only source | inherited |
| single-level octree tested | deeper recursive Gamma not tested in EXP-303 | EXP-304 |
| K-bound fanout constraint | Σᵢ K(payload_i) grows as O(N·K_per_child); slack C_KBOUND·log(N) grows as O(log N); for large N, per-child payload must satisfy K_per_child ≤ K(parent)/N + C_KBOUND·log(N)/N | EXP-304: payload compression protocol or adaptive C_KBOUND(N) |

---

## 6. Commitment Chain

EXP-302 (ℝ^6 position×color) →
**EXP-303 (ℝ^9 position×color×normal; Γ operator; bbox containment)**
