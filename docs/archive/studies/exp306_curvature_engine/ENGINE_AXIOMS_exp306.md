# ENGINE AXIOMS -- EXP-306 Curvature Engine (Series 300, sixth study)

**Preregistration status**: GATE LOCKED
**Protocol version**: exp306-v1
**Inherits from**: exp305-v1 -> exp304-v1 -> exp301-v1
**Workspace**: Reality_Engine/studies/exp306_curvature_engine/
**declaration_hash**: `5a8e1afc590d8ffb9dfe33977005eb888798c1ccdc9dd64c59b797eb8d48fe47`

---

## 0. Motivation

EXP-305 closed with two documented limits:

**E-305-002**: Sector C normal direction was derived from _orthogonal_decompose on the
stalk rather than from the subdivision geometry. With seed stalk_C = [0,0,1] and nx=0,
the P_yz reflection left stalk_C_parent unchanged in both forward and mirror passes,
producing identical child normals rather than sign-flipped ones. P_yz symmetry was
satisfied only for Sector B (det_sign gate). Sector C required geometric coupling.

**EXP-305 sec 6 (known limits)**:
  - normal not geometrically linked to bbox
  - single ghost track over full R^11
  - no recursive Gamma
  - curvature absent

EXP-306 resolves all four simultaneously.

---

## 1. Stalk Schema -- Four-Sector Architecture

    F(v) in R^12 = [Sector A | Sector B | Sector C]

    Sector A (dims 0-3): [mass, r, g, b]
      conservation: additive_sum    sum_i stalk_A(child_i) = stalk_A(parent)
      operator:     Phi_A           _orthogonal_decompose (inherited)

    Sector B (dims 4-7): [x, y, z, w]
      conservation: barycentric     sum_i omega_i * stalk_B(child_i) = stalk_B(parent)
      constraint:   w = 1.0         (homogeneous coordinate)
      operator:     Phi_B           bbox centroid + outer-product F_B (inherited)

    Sector C (dims 8-11): [nx, ny, nz, kappa]
      Sub-field C.normal (dims 8-10): [nx, ny, nz]
        conservation: unit_norm     ||stalk_C.normal(child_i)||_2 = 1.0
        convention:   centroid_outward
        formula:      n_child = normalize(centroid_child - centroid_parent)
      Sub-field C.kappa (dim 11): [kappa]
        conservation: additive_sum  sum_i kappa_child_i = kappa_parent
        split:        volume_proportional: kappa_child_i = kappa_parent * omega_i

    seed_stalk = [1,1,1,1,  0.5,0.5,0.5,1,  0,0,1,0]
                  mass r g b   x  y  z  w  nx ny nz kappa

Note: the centroid_outward convention decouples Sector C normals from the
stalk decomposition entirely. n_child is a pure geometric quantity derived
from the child bbox centroid relative to the parent bbox centroid.
This closes E-305-002.

---

## 2. Operators

### 2.1 Phi_A (inherited, sum conservation on dims 0-3)

Unchanged from EXP-305.

### 2.2 Phi_B (inherited, barycentric on dims 4-7)

Unchanged from EXP-305.

### 2.3 Phi_C_306 -- Sector C Partition (new)

**Normal sub-field (dims 8-10):**

    n_child_i = normalize(centroid_child_i - centroid_parent)

    Degenerate case: centroid_child == centroid_parent (zero-volume bbox):
      n_child_i = stalk_C.normal_parent / ||stalk_C.normal_parent||
      (inherit parent normal direction)

    F_C.normal[8:11, 8:11] = outer(n_child_i, stalk_C.normal_parent) / ||stalk_C.normal_parent||^2
      Satisfies: F @ stalk_C.normal_parent = n_child_i  (exact by construction)

**Kappa sub-field (dim 11):**

    kappa_child_i = kappa_parent * omega_i
      where omega_i = vol(bbox_child_i) / vol(bbox_parent)
      For uniform splits: kappa_child_i = kappa_parent / N

    F_C.kappa[11, 11] = omega_i   (scalar block)
    Satisfies: F[11,11] * kappa_parent = kappa_child_i  (exact)
    Sum: sum_i omega_i * kappa_parent = kappa_parent * sum_i omega_i = kappa_parent  (sum omega_i = 1)

**Restriction map (full d=12 block-diagonal):**

    F[0:4,   0:4 ] = F_A  (outer product, Sector A)
    F[4:8,   4:8 ] = F_B  (outer product, Sector B)
    F[8:11,  8:11] = F_C.normal  (outer product, centroid-outward n_child)
    F[11,    11  ] = omega_i  (scalar, kappa volume-proportional)
    All off-diagonal sector blocks = 0

**P_yz correctness (centroid-outward convention):**

    Under P_yz (x -> -x, bbox x-axis reflected):
      centroid_child_mirror = P_yz(centroid_child_forward)  (x-coord negated)
      centroid_parent_mirror = P_yz(centroid_parent_forward)
      direction_mirror = centroid_child_mirror - centroid_parent_mirror
                       = P_yz(centroid_child) - P_yz(centroid_parent)
                       = P_yz(centroid_child - centroid_parent)
      n_mirror = normalize(direction_mirror) = P_yz(n_forward)  (for x-component)

    Closes E-305-002: Sector C normals are now exact P_yz images under bbox reflection.

### 2.4 apply_gamma_306 -- Triple-sector spatial partition with kappa

Extends apply_gamma_305:

    Channel 1 -- Geometric:   _compute_child_bboxes(bbox_parent, key)
    Channel 2A -- Sector A:   Phi_A
    Channel 2B -- Sector B:   Phi_B (centroid + w=1)
    Channel 2C -- Sector C:   Phi_C_306 (centroid-outward n_child + kappa * omega_i)

Post-conditions (6 predicates):
    is_valid AND is_valid_b AND is_unit_norm AND is_spatially_valid
    AND is_valid_block_diagonal AND kappa sum verified via is_valid

### 2.5 apply_gamma_306_recursive -- Recursive Gamma with soft-decay K-budget

    Signature: apply_gamma_306_recursive(mu, claim_id, partition_key, payloads,
                                          beta, budget, spent, K_budget, depth)

    Termination: if K_budget < K_MIN_PARTITION (=16): return mu (no partition)
    K_budget_child = K_budget * exp(-lambda * 1) = K_budget / 2  (lambda = ln(2))
    At depth D from root: K_budget(D) = K_budget_0 * exp(-lambda * D) = 256 / 2^D
    Floor schedule: 256 -> 128 -> 64 -> 32 -> 16 -> STOP (depth_max = 4)

    Each recursive level calls apply_gamma_306 on each active leaf with the
    decayed K_budget. The K_budget is independent of (but additive to) the
    standard backreaction cost budget B0.

---

## 3. Validity Predicates

Six predicates, all must pass after every state update:

    is_valid(mu):               entailment consistency; covers kappa additive per-edge
    is_valid_b(mu):             Sector B barycentric + w=1 (inherited)
    is_unit_norm(mu):           ||stalk[8:11]||_2 = 1.0 for d>=11 claims (inherited)
    is_spatially_valid(mu):     bbox containment on SPATIAL edges (inherited)
    is_valid_block_diagonal(mu): no cross-sector coupling in F (updated for d=12)
    [kappa sum conservation]:   covered by is_valid via per-edge F[11,11]*kappa_parent = kappa_child

Note on kappa coverage by is_valid: is_valid checks F(u->v)(stalk_u) ~= stalk_v for
each SPATIAL edge. For dim 11: F[11,11] * kappa_parent = kappa_child_i (per edge).
Sum sum_i kappa_child_i = kappa_parent follows from sum omega_i = 1, which is enforced
at construction time. No separate is_valid_kappa predicate needed.

**is_valid_block_diagonal update for d=12:**
    Sector boundaries: A=[0:4], B=[4:8], C=[8:12]
    Off-diagonal checks:
      ||F[0:4,  4:12]|| < tol   (A -> B, C)
      ||F[4:8,  0:4 ]|| < tol   (B -> A)
      ||F[4:8,  8:12]|| < tol   (B -> C)
      ||F[8:12, 0:8 ]|| < tol   (C -> A, B)
    The kappa scalar block F[11,11] is within the C sector; no cross-block issue.

---

## 4. Dual Ghost Architecture

**Primary space:**
    Z_t = sum_{v in W_t} stalk(v)  in R^12

**Sector projections:**
    Z_A = Z_t[0:8]   (Sectors A+B combined, dims 0-7)
    Z_C = Z_t[8:12]  (Sector C, dims 8-11)

**Ghost vectors:**
    G_A = Z_A - Pi_{W_t}(Z_A)   (projection residual over Sector A+B subspace)
    G_C = Z_C - Pi_{W_t}(Z_C)   (projection residual over Sector C subspace)

**EMA tracks (independent):**
    S_A_{t+1} = alpha * S_A_t + (1-alpha) * G_A_t   (alpha = 0.85, dim 8)
    S_C_{t+1} = alpha * S_C_t + (1-alpha) * G_C_t   (alpha = 0.85, dim 4)

    Same alpha for both tracks prevents beat frequencies.
    S_A and S_C stored as separate arrays in MuState.

**Observables:**
    B_A(t) = ||S_A|| / (||Z_A|| + eps)   (photometric/mass ghost ratio)
    B_C(t) = ||S_C|| / (||Z_C|| + eps)   (geometric ghost ratio)

**MuState extension:**
    New fields: S_A (shape 8), S_C (shape 4)
    Old field S (shape d=12) retained for backward compatibility;
    S is set to concatenate(S_A, S_C) for hash purposes.

---

## 5. Recursive Gamma Parameters (preregistered)

    lambda          = 0.6931471805599453  (= ln(2); halves K_budget per depth)
    K_MIN_PARTITION = 16                  (atomic floor in bytes)
    K_budget_0      = 256                 (4 levels from root: 256->128->64->32->16->STOP)
    depth_max       = 4                   (= floor(log(K_budget_0/K_MIN_PARTITION)/lambda))

K_budget is passed as a runtime parameter; it does NOT appear in H_t or affect the
state hash. It is an execution constraint, not a state variable.

---

## 6. Mirror Operator P_yz (inherited, extended verification)

    P_yz: x -> -x  (polar dim 4), nx -> -nx  (axial dim 8)
    Bbox reflection: mirror_lo[0] = -hi[0], mirror_hi[0] = -lo[0]
    kappa: invariant under P_yz (kappa is a scalar, not a vector component)

**Expected P_yz test results for EXP-306:**
    Sector C normals: n_mirror_child_j = P_yz(n_fwd_child_i) at P_yz-correspondence
      (resolves E-305-002 -- now verifiable for non-zero nx seeds)
    det_sign: +1 for all uniform bbox children (inherited)
    kappa: kappa_mirror_child = kappa_fwd_child (invariant)

---

## 7. Known Limits of EXP-306

| limit | description | resolution path |
|-------|-------------|-----------------|
| kappa semantics | kappa=additive but geometry not constrained to mean extrinsic curvature | EXP-307: kappa = tr(shape_operator) of bbox face, derived from bbox aspect ratio |
| S_A/S_C projection | G_A, G_C use full W_t basis for projection; cross-sector stalk correlations not fully eliminated | EXP-307: per-sector projection using only sector-relevant stalk dimensions |
| recursive Gamma scope | K_budget controls depth but payloads at each level still user-specified | EXP-307: auto-generated payloads at recursive levels |
| P_yz kappa | kappa invariance under P_yz is asserted but not verified by test | EXP-306 P-invariance test: confirm kappa_mirror == kappa_fwd |

---

## 8. Commitment Chain

EXP-301 (R^4 symbolic) ->
EXP-302 (R^6 pos*col; sum conservation) ->
EXP-303 (R^9 pos*col*nrm; Gamma operator; bbox containment) ->
EXP-304 (R^8 dual-sector; Sector A sum; Sector B barycentric+w=1) ->
EXP-305 (R^11 triple-sector; Sector C unit-norm; P_yz mirror; block-diagonal F) ->
**EXP-306 (R^12 curvature engine; centroid-outward normals; kappa additive;
           dual ghost S_A/S_C; recursive Gamma with soft-decay K-budget)**
