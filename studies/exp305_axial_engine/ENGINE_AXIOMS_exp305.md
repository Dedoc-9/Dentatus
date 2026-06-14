# ENGINE AXIOMS — EXP-305 Axial Restoration Engine (Series 300, fifth study)

**Preregistration status**: GATE LOCKED
**Protocol version**: exp305-v1
**Inherits from**: exp304-v1 -> exp303-v1 -> exp301-v1
**Workspace**: Reality_Engine/studies/exp305_axial_engine/
**declaration_hash**: `2a05be65524a8ce244ea9597917a5a3f771094a2bc25fd33f801ad1c6cc99e64`

---

## 0. Motivation

EXP-303 introduced [nx,ny,nz] at d=9 but used sum conservation for all dims, producing
non-unit child normals after _orthogonal_decompose. EXP-304 replaced [nx,ny,nz] with
homogeneous w to establish the Sector B barycentric architecture.

EXP-305 restores the normal vector field as a third sector (Sector C) with:
  1. Unit-norm conservation predicate (||n||=1) in place of sum conservation
  2. Correct pseudo-vector mirror operator (P_yz) for P-invariance testing
  3. Block-diagonal restriction map predicate to enforce Sector A/B/C decoupling

EXP-306 (deferred): curvature kappa, dual ghost G_A/G_B, recursive Gamma with
soft-decay K-budget.

---

## 1. Stalk Schema — Triple Sector Architecture

    F(v) in R^11 = [Sector A | Sector B | Sector C]

    Sector A (dims 0-3): [mass, r, g, b]
      conservation: SUM    sum_i stalk_A(child_i) = stalk_A(parent)
      operator:     Phi_A  (_orthogonal_decompose on dims 0-3, inherited)

    Sector B (dims 4-7): [x, y, z, w]
      conservation: BARYCENTRIC    sum_i omega_i * stalk_B(child_i) = stalk_B(parent)
      constraint:   w = 1.0 (homogeneous coordinate)
      operator:     Phi_B  (outer-product F_B, inherited from EXP-304)

    Sector C (dims 8-10): [nx, ny, nz]
      conservation: UNIT_NORM    ||stalk_C(child_i)||_2 = 1.0 for all i
      vector type:  axial pseudo-vector
      operator:     Phi_C  (see §2.3)

    seed_stalk = [1.0, 1.0, 1.0, 1.0,  0.5, 0.5, 0.5, 1.0,  0.0, 0.0, 1.0]
                  mass  r    g    b      x    y    z    w      nx   ny   nz

Note: sum conservation does NOT apply to Sector C. ||n||=1 replaces it.
Sector C is not additive — normals are orientation vectors, not mass-like quantities.

---

## 2. Operators

### 2.1 Phi_A (inherited, sum conservation on dims 0-3)

Unchanged from EXP-304. _orthogonal_decompose(stalk_A, N).

### 2.2 Phi_B (inherited, barycentric on dims 4-7)

Unchanged from EXP-304. outer-product F_B, omega_i, w=1 invariant.

### 2.3 Phi_C — Sector C Normal Partition (new)

**Signature**: Phi_C(stalk_C_parent, N) -> {n_child_1, ..., n_child_N}

**Algorithm**:

    Step 1: raw_children = _orthogonal_decompose_slice(stalk_parent, N, dims=[8,9,10])
            OR for N > 3: raw_children = _orthogonal_decompose(stalk_parent, N)[8:11]
            (use full-stalk decompose when N > d_C=3, same pattern as EXP-304 Sector A)

    Step 2: n_child_i = raw_children[i] / ||raw_children[i]||_2   (L2 normalize)
            Degenerate case (||raw|| < 1e-12): n_child_i = stalk_C_parent / ||stalk_C_parent||
            (inherit parent direction — no information from a zero vector)

    Step 3: F_C(parent->child_i) = outer(n_child_i, stalk_C_parent) / ||stalk_C_parent||^2
            Satisfies: F_C @ stalk_C_parent = n_child_i  (exact, by construction)

**Restriction map (full d=11 block)**:
    F[0:4,   0:4]   = F_A block (outer product, Sector A)
    F[4:8,   4:8]   = F_B block (outer product, Sector B)
    F[8:11,  8:11]  = F_C block (outer product, normalized, Sector C)
    All off-diagonal sector blocks = 0

**Post-condition**: is_unit_norm(new_state) AND is_valid_block_diagonal(new_state)

### 2.4 apply_gamma_305 (Gamma operator for EXP-305)

Extends apply_gamma_304 with Sector C channel:

    Channel 1 — Geometric:   _compute_child_bboxes(bbox_parent, key)
    Channel 2A — Sector A:   Phi_A
    Channel 2B — Sector B:   Phi_B (centroid of child bbox, omega_i)
    Channel 2C — Sector C:   Phi_C (normalize child normals)

Post-conditions: is_valid AND is_valid_b AND is_unit_norm AND is_spatially_valid
                 AND is_valid_block_diagonal

---

## 3. Validity Predicates

Four predicates, all must pass after every state update:

    is_valid(mu):               forward entailment consistency (inherited E-301-003)
    is_valid_b(mu):             Sector B barycentric + w=1 (inherited EXP-304)
    is_spatially_valid(mu):     bbox containment on SPATIAL edges (inherited EXP-303)

    is_unit_norm(mu, tol=1e-8):
      for each claim with stalk.shape[0] >= 11:
        assert | ||stalk[8:11]||_2 - 1.0 | < tol
      Trivially true for claims with d < 11.

    is_valid_block_diagonal(mu, tol=1e-7):
      for each (src->tgt) in entailments where etype in {PARTITION, SPATIAL}:
        F = entailment.restriction   (shape 11x11)
        assert ||F[0:4,  4:11]|| < tol   (A -> B,C cross blocks)
        assert ||F[4:8,  0:4 ]|| < tol   (B -> A cross block)
        assert ||F[4:8,  8:11]|| < tol   (B -> C cross block)
        assert ||F[8:11, 0:8 ]|| < tol   (C -> A,B cross blocks)

All five predicates are independent. None implies any other.

---

## 4. Mirror Operator P_yz (preregistered)

    P_yz: reflection in the yz-plane  (x -> -x, y -> y, z -> z)

    Transformation on stalk:
      dim 4  (x):  multiply by -1   [polar vector, component orthogonal to yz-plane]
      dim 8  (nx): multiply by -1   [axial pseudo-vector, same component flips under P_yz]
      dims 0-3, 5-7, 9-10: unchanged

    Rationale: Under a reflection P in a plane with unit normal n_hat:
      polar vector v:  v_parallel unchanged, v_perp -> -v_perp
      axial vector a:  a_perp unchanged,     a_parallel -> -a_parallel
    For P_yz (n_hat = x_hat):
      polar x-component flips, axial x-component also flips (different rule from inversion).

    This definition is FIXED at preregistration. All P-invariance tests must use
    exactly this operator. Using spatial inversion (x,y,z -> -x,-y,-z) instead
    would produce incorrect results for Sector C.

---

## 5. P-Invariance Test (Fork B, preregistered)

File: run_p_invariance_exp305.py

    1. Build Seed_0_axial and mu0.
    2. Build mu_mirror by applying P_yz to seed stalk.
    3. Run apply_gamma_305(mu0, ...) -> mu1, extract det_sign for each child.
    4. Run apply_gamma_305(mu_mirror, ...) -> mu1_mirror, extract det_sign.
    5. Assert: det_sign(mu1_mirror[child_i]) == det_sign(mu1[child_i]) for all i.

    Expected result: PASS for uniform bbox subdivision (all omegas equal, no reflective maps).
    A FAIL would indicate the restriction map F_B or F_C introduces chirality
    that depends on the input orientation rather than the subdivision geometry.

This test is DEFERRED to after run_seed_exp305.py passes (Fork A first, Fork B second).

---

## 6. Known Limits of EXP-305

| limit | description | resolution path |
|-------|-------------|-----------------|
| normal not geometrically linked to bbox | Sector C normal is derived from stalk decomposition, not face orientation of child bbox | EXP-306: assign child normals from outward face normals of bbox |
| K-bound fanout N > d_C=3 | octree (N=8) uses full d=11 stalk for decompose, same workaround as EXP-304 | EXP-306: dedicated normal decompose for N > 3 |
| single ghost track | G_t over full R^11; Sector C ghost not isolated | EXP-306: dual ghost G_A (dims 0-7) + G_C (dims 8-10) with independent EMA |
| no recursive Gamma | depth limited to single-level subdivisions | EXP-306: soft-decay K_budget(depth) = K_budget_0 * exp(-lambda*depth) |
| curvature absent | kappa not modeled | EXP-306: d=12, dim 11 = kappa, Sector C extended to [nx,ny,nz,kappa] |

---

## 7. Commitment Chain

EXP-301 (R^4 symbolic) ->
EXP-302 (R^6 pos*col; sum conservation; chirality noted) ->
EXP-303 (R^9 pos*col*nrm; Gamma operator; bbox containment) ->
EXP-304 (R^8 dual-sector; Sector A sum; Sector B barycentric+w=1; det_sign) ->
**EXP-305 (R^11 triple-sector; Sector C unit-norm; P_yz mirror; is_valid_block_diagonal)**
