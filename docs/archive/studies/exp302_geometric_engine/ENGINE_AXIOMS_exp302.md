# ENGINE AXIOMS — EXP-302 Geometric Reality Engine (Series 300, second study)

**Preregistration status**: GATE LOCKED — commit before Seed_0_geo declaration.
**Protocol version**: exp302-v1
**Inherits from**: exp301-v1 (all operators Φ/Ψ/Ω, validity predicate, E-301-001 through E-301-004)
**Workspace**: Reality_Engine/studies/exp302_geometric_engine/

---

## 0. Relationship to EXP-301

EXP-302 extends EXP-301 by changing the stalk interpretation from symbolic (ℝ^4,
semantically unspecified) to geometric (ℝ^6 = position × color). All operators,
validity predicates, and interchange laws from EXP-301 are inherited unchanged.
The only additions are geometric partition keys and spatial consistency predicates.

No EXP-301 code is modified. EXP-302 runs via the same engine/operators.py,
engine/state.py, engine/validity.py, and engine/confluence.py.

---

## 1. Geometric Stalk Schema

    F(v) ∈ ℝ^6 = [x, y, z, r, g, b]

    dims 0–2: position centroid of the claim's spatial region
    dims 3–5: color (RGB, normalised [0,1]^3)

    seed_stalk = [0.5, 0.5, 0.5, 1.0, 1.0, 1.0]
      → unit cube [0,1]^3, white (1,1,1)

Stalk operations (inherited from EXP-301):
    Φ: _orthogonal_decompose(stalk, N) in ℝ^6 — orthogonal split of the 6D vector.
       Position conservation: Σᵢ pos(child_i) = pos(parent)  (same as stalk conservation)
       Color conservation:    Σᵢ col(child_i) = col(parent)
    Ψ: stalk(v_new) = Σᵢ αᵢ · stalk(v_i)  (weighted centroid in position; blend in color)
    Restriction maps: identical to EXP-301 (outer product projection for Φ; αᵢI for Ψ)

---

## 2. Spatial Partition Keys (preregistered)

### 2.1 axis_bisect_x / axis_bisect_y / axis_bisect_z

N=2 partition along a single axis. The _orthogonal_decompose seed is derived from
the axis key to ensure axis-aligned decomposition:

    seed = hash("axis_bisect_x" + PROTOCOL_VERSION) % 2^31

Conservation law identical to EXP-301 §2.1. K-bound constant C_KBOUND = 150 (E-301-002).

### 2.2 octree_split

N=8 partition bisecting all three axes simultaneously.
Precondition: d ≥ N → d=6 ≥ 8 FALSE.

    BLOCKED: octree_split requires N=8, but d=6 < 8.
    PartitionError DIM_INSUFFICIENT raised by _orthogonal_decompose.
    
    Resolution: declare Seed_1_geo with d ≥ 8 (e.g., d=9: [x,y,z,r,g,b,nx,ny,nz]).
    octree_split is preregistered as a future key; execution deferred to d ≥ 8 state.

### 2.3 spatial_blend (synthesis key)

Weighted centroid synthesis:
    pos(v_new) = Σᵢ αᵢ · pos(v_i)    (weighted average of position components)
    col(v_new) = Σᵢ αᵢ · col(v_i)    (weighted average of color components)

Both are covered by the existing Ψ operator: stalk(v_new) = Σᵢ αᵢ · stalk(v_i).

---

## 3. Spatial Consistency Predicate

Inherited directly from EXP-301 E-301-003 (forward entailment consistency):

    is_valid(μ_t) iff for each target v ∈ V_t:
      ||Σᵢ F(uᵢ→v)(stalk_{uᵢ}) − stalk_v|| < 1e-8

No additional spatial predicate is required. The restriction map
F(parent→child) = outer(stalk_child, stalk_parent)/||stalk_parent||²
already encodes the geometric relationship between parent and child regions.

Optional future extension (not preregistered for EXP-302):
    face_compatibility: for adjacent spatial claims u, v sharing a boundary face,
      ||F(u→v)(stalk_u)[pos_dims] − stalk_v[pos_dims]|| < eps_face
    This requires a new edge type SPATIAL_ADJACENCY and a new partition schema
    that tracks bounding box metadata. Deferred to EXP-303.

---

## 4. Operator Notes (geometric interpretation)

### 4.1 Φ (Partition — geometric)

_orthogonal_decompose in ℝ^6 produces children whose stalks sum to the parent stalk.
Position interpretation: the child centroids sum to the parent centroid (not subdivide it).
This is a CENTROID CONSERVATION, not a region subdivision.

Note: centroid conservation ≠ region subdivision. A full spatial subdivision (each child
covers a sub-region of the parent's bounding box) would require a different partition
operator that tracks bounding box metadata alongside the stalk. This is outside EXP-302
scope; the stalk captures centroids only.

Implication: EXP-302 tests geometric stalk dynamics, not spatial tiling. Spatial tiling
(each child covers exactly 1/N of the parent volume) is EXP-303.

### 4.2 Ψ (Synthesis — geometric)

Weighted centroid of child centroids + blended color. Meaningful as spatial interpolation
when weights represent area fractions (equal weights = uniform blend).

### 4.3 Ω (Observation — geometric)

Artifact.stalk = [x, y, z, r, g, b] is the observed centroid + color of the claim.
K_synthesis_gain from R3 measures the payload compression of the spatial description.

---

## 5. Rewrite Laws (inherited)

R1, R2, R3 inherited from EXP-301 §5.5. No new laws added.

---

## 6. Seed_0_geo Declaration Requirements

| parameter | value |
|-----------|-------|
| seed_stalk | [0.5, 0.5, 0.5, 1.0, 1.0, 1.0] |
| d | 6 |
| stalk_schema | {dims: [x,y,z,r,g,b], position_dims: [0,1,2], feature_dims: [3,4,5]} |
| partition_schema | axis_bisect_x / axis_bisect_y / axis_bisect_z / octree_split (blocked) |
| synthesis_schema | spatial_blend |
| protocol_version | exp302-v1 |
| declaration_hash | SHA-256(above fields, sorted) |

---

## 7. Known Limits of EXP-302

| limit | description | resolution path |
|-------|-------------|-----------------|
| d=6 < 8 | octree_split (N=8) blocked | EXP-303: d ≥ 8 |
| centroid conservation only | no bounding box tracking | EXP-303: SPATIAL_ADJACENCY edge type |
| no face compatibility check | adjacent claims not constrained at shared faces | EXP-303: face_compatibility predicate |
| ghost G_t = 0 for lossless ops | E-301-004: path-coherence residuals only | inherited from EXP-301 |
| algebraic-geometric conflation | pos dims (0–2) use sum conservation (Σ pos_i = pos_parent); child positions are algebraic coordinates summing to parent, not geometric sub-centroids; negative position components are valid outputs of _orthogonal_decompose and carry no geometric violation | EXP-304: Sector B [x,y,z,w] with barycentric conservation (Σ ω_i · pos_i = pos_parent, Σ ω_i = 1) enforced via homogeneous w=1 constraint |
| chiral decomposition basis | _orthogonal_decompose derives orthonormal basis from hash(stalk_parent, N); basis is deterministic but reflection-arbitrary: a mirror-image parent stalk does not produce mirror-image child stalks; chirality is a property of the stalk decomposition only — bbox geometry (axis_bisect_*, octree_split) is reflection-invariant by construction | EXP-304: Sector B uses affine restriction maps F_B ∈ GL(4); det(F_B) sign tracked as Entailment metadata; P-invariant predicates possible once Sector B is isolated |

---

## 8. Commitment Chain

EXP-301 (Series 300 genesis, symbolic stalks ℝ^4) →
**EXP-302 (Series 300, geometric stalks ℝ^6 = position × color)** →
EXP-303 (ℝ^9 = position × color × normal; Γ operator; bbox containment) →
EXP-304 (ℝ^8 affine split: Sector A [mass,r,g,b] sum-conserved; Sector B [x,y,z,w] barycentric; P-invariant restriction maps)
