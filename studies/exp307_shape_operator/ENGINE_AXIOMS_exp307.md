# ENGINE AXIOMS -- EXP-307 Shape Operator Engine (Series 300, seventh study)

**Preregistration status**: GATE LOCKED
**Protocol version**: exp307-v1
**Inherits from**: exp306-v1 -> exp305-v1 -> exp304-v1 -> exp301-v1
**Workspace**: Reality_Engine/studies/exp307_shape_operator/
**declaration_hash**: `8e288c601093e1dd786ee112c1451f0fa60a2b1cb898ea17a91f63b4a5c89060`

---

## 0. Motivation

EXP-306 closed with three documented limits:

**E-306-001 (kappa semantics)**: kappa dim 11 carried an additive split (kappa_child = kappa_parent * omega_i)
but was not constrained to any geometric quantity. The split preserved the sum but allowed
arbitrary kappa values inconsistent with the bounding box geometry.

**E-306-002 (S_A/S_C projection)**: G_A and G_C used W_basis sliced to sector rows (correct), but
no test verified that G_A ⊥ G_C. The per-sector projection structure was present but unaudited.

**E-306-003 (recursive payload generation)**: payload_fn was user-supplied, introducing an
uncontrolled external parameter into the recursive Gamma operator. Auto-generation closes
this by making payloads deterministic functions of the state tuple.

EXP-307 resolves all three simultaneously.

---

## 1. Stalk Schema -- d=12 (unchanged)

    F(v) in R^12 = [Sector A | Sector B | Sector C]

    Sector A (dims 0-3): [mass, r, g, b]     -- unchanged from EXP-306
    Sector B (dims 4-7): [x, y, z, w]        -- unchanged from EXP-306
    Sector C (dims 8-11): [nx, ny, nz, kappa]
      dims 8-10: centroid-outward unit normal -- unchanged from EXP-306
      dim 11:    kappa = tr(H_bbox)           -- CHANGED from EXP-306

    seed_stalk = [1,1,1,1,  0.5,0.5,0.5,1,  0,0,1,6]
                  A          B              n   kappa
    seed kappa = tr(H) = 2/1 + 2/1 + 2/1 = 6.0  (unit cube [0,1]^3)

---

## 2. kappa as Shape Operator Trace

### 2.1 Definition

For a rectangular bounding box with extents l_i = hi[i] - lo[i] in R^3:

    kappa(bbox) = tr(H_bbox) = sum_{i=0}^{2} (2 / l_i)

This is the trace of the mean curvature tensor (shape operator) for an ellipsoid
inscribed in the bbox with semi-axes r_i = l_i / 2:

    H_bbox = diag(1/r_0, 1/r_1, 1/r_2)  =>  tr(H) = 2/l_0 + 2/l_1 + 2/l_2

**Degenerate case**: l_i -> 0 in any dimension -> kappa -> +inf.
For numerical stability: if l_i < 1e-12, treat as infinity; clamped to kappa_max = 1e9.

### 2.2 Restriction Map (F[11,11])

    kappa_child_i = kappa(bbox_child_i)   (recomputed from child bbox geometry)
    F[11,11] = kappa_child_i / kappa_parent   (geometric coupling ratio)

    Satisfies is_valid: F[11,11] * kappa_parent = kappa_child_i  (exact by construction)

### 2.3 Conservation Law

kappa is NOT conserved additively. Under uniform octree (8 children, each [0,0.5]^3):
    kappa_parent = 6.0
    kappa_child  = 12.0  (each octant has half-extents in all dims)
    F[11,11] = 2.0

Sum: sum_i kappa_child_i = 8 * 12 = 96 != 6 = kappa_parent.
The quantity kappa * vol(bbox) = constant IS conserved:
    kappa_parent * vol_parent = 6.0 * 1.0 = 6.0
    kappa_child * vol_child  = 12.0 * 0.125 = 1.5  (per child)
    sum = 8 * 1.5 = 12 != 6  (NOT conserved either)

Note: kappa is a point-wise geometric quantity, not an integral. No sum law applies.

### 2.4 P_yz Invariance

Under P_yz (x -> -x), bbox extents are preserved:
    l_0 = |hi[0] - lo[0]|  ->  |-lo[0] - (-hi[0])| = |hi[0] - lo[0]| = l_0

Therefore kappa_mirror = kappa_fwd for all corresponding children.
P_yz invariance of kappa is exact.

---

## 3. Operators

### 3.1 Phi_C_307 -- Sector C Partition (updated kappa rule)

**Normal sub-field (dims 8-10)**: identical to EXP-306.

    n_child_i = normalize(centroid_child_i - centroid_parent)
    F_C.normal[8:11, 8:11] = outer(n_child_i, stalk_C.normal_parent) / ||stalk_C.normal_parent||^2

**Kappa sub-field (dim 11):**

    kappa_child_i = kappa(bbox_child_i) = sum_j (2 / (bbox_child_i.hi[j] - bbox_child_i.lo[j]))
    F_C.kappa[11, 11] = kappa_child_i / kappa_parent

    If kappa_parent == 0: F_C.kappa[11,11] = 0 (degenerate; is_valid_kappa will flag seed if kappa=0)

**Full restriction map**: block-diagonal (12x12), unchanged structure from EXP-306.

### 3.2 apply_gamma_307 -- Shape-operator partition

Replaces apply_gamma_306. Identical except:
  - kappa_child = kappa_from_bbox(child_bbox)  [geometric, not omega * kappa_parent]
  - F[11,11] = kappa_child / kappa_parent
  - Post-validates: 6 predicates including is_valid_kappa

### 3.3 apply_gamma_307_recursive -- Auto-payload recursive Gamma

Replaces apply_gamma_306_recursive. Identical except:

**Auto-payload generation:**

    payload_i = SHA256(parent_id + ":" + partition_key + ":" + str(depth) + ":" + str(i))[:16]

This is a pure function of (parent_id, partition_key, depth, i) — no external input.
Payload string format: 16-character lowercase hex (e.g., "a3f2e1d0c9b8a7f6").

K_bound for auto-payload is fixed: len(zlib.compress(payload.encode())) ≈ 20 bytes.
K-budget check uses this K_bound per child at each recursive level.

---

## 4. Validity Predicates

Seven predicates (6 inherited + 1 new):

    is_valid(mu):                   entailment consistency (F @ stalk_parent = stalk_child)
    is_valid_b(mu):                 Sector B barycentric + w=1
    is_unit_norm(mu):               ||stalk[8:11]||_2 = 1.0 for d>=11 claims
    is_spatially_valid(mu):         bbox containment on SPATIAL edges
    is_valid_block_diagonal_306(mu): no cross-sector coupling in F (d=12)
    is_valid_kappa(mu):             NEW -- stalk[11] == kappa(bbox) for all claims with bbox

### 4.1 is_valid_kappa (new)

    For every claim with bbox not None and stalk.shape[0] > 11:
      kappa_geom = sum_i (2 / (hi[i] - lo[i]))  for i in {0,1,2}
      | stalk[11] - kappa_geom | < tol  (tol = 1e-8)

    Claims without bbox (root seed if bbox not set, or pure symbolic claims): skipped.
    Empty graph: trivially valid.

---

## 5. Dual Ghost Architecture (verified)

Inherited from EXP-306. EXP-307 explicitly verifies per-sector orthogonality:

    G_A in R^8  (dims 0:8);  G_C in R^4  (dims 8:12)
    Orthogonality test: G_A . G_C == 0 (always, since they live in orthogonal subspaces of R^12)

    Note: G_A and G_C are projections in their respective subspace slices;
    concatenation [G_A, G_C] is NOT the same as G = Z - Pi_W(Z) over full R^12.
    This separation is the dual arithmetic requirement.

With geometric kappa: B_C(t) > 0 after first partition (kappa_child != kappa_parent
-> G_C carries a non-zero residual). This closes E-306-002 observationally.

---

## 6. Recursive Gamma Parameters (inherited)

    lambda          = 0.6931471805599453
    K_MIN_PARTITION = 16
    K_budget_0      = 256
    depth_max       = 4
    payload_generation = auto

---

## 7. Mirror Operator P_yz (inherited + kappa verified)

    P_yz: x -> -x (polar dim 4), nx -> -nx (axial dim 8)
    Bbox reflection: mirror_lo[0] = -hi[0], mirror_hi[0] = -lo[0]
    kappa: INVARIANT (extents preserved under yz-reflection)

**Expected P_yz test results for EXP-307:**
    Sector C normals: n_mirror = P_yz(n_fwd) at correspondence (inherited from EXP-306)
    kappa_mirror = kappa_fwd at all correspondence pairs (exact, per §2.4)
    det_sign: +1 for uniform bbox children

---

## 8. Known Limits of EXP-307

| limit | description | resolution path |
|-------|-------------|-----------------|
| H_bbox approximation | shape operator uses uniform bbox extents; real curvature requires surface sampling | EXP-308: kappa = integral of mean curvature over bbox face normals |
| kappa degenerate | l_i -> 0 gives kappa -> inf; clamped at 1e9 but not principled | EXP-308: regularized shape operator with minimum extent floor |
| G_A orthogonality | G_A . G_C = 0 by construction but not yet used as a signal | EXP-308: use ||G_A x G_C|| as a coupling observable |
| auto-payload K_bound | fixed ~20 bytes; does not adapt to depth or geometry | EXP-308: payload encodes bbox hash for variable K_bound |

---

## 9. Commitment Chain

EXP-301 (R^4 symbolic) ->
EXP-302 (R^6 pos*col; sum conservation) ->
EXP-303 (R^9 pos*col*nrm; Gamma; bbox containment) ->
EXP-304 (R^8 dual-sector; A sum; B barycentric+w=1) ->
EXP-305 (R^11 triple-sector; C unit-norm; P_yz; block-diagonal F) ->
EXP-306 (R^12 curvature engine; centroid-outward normals; kappa additive; dual ghost S_A/S_C; recursive Gamma) ->
**EXP-307 (R^12 shape operator; kappa = tr(H_bbox); is_valid_kappa; auto-payload recursive Gamma;
           per-sector ghost orthogonality verified)**
