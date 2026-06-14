# ENGINE AXIOMS -- EXP-309 LOD Observer Engine (Series 300, ninth study)

**Preregistration status**: GATE LOCKED
**Protocol version**: exp309-v1
**Inherits from**: exp308-v1 -> exp307-v1 -> exp306-v1 -> exp305-v1 -> exp301-v1
**Workspace**: Reality_Engine/studies/exp309_lod_observer/
**declaration_hash**: `1c3f709e924ca7a053f39666bfe6efbd0e40269918b33a31083e8b381fcca86c`

---

## 0. Motivation

EXP-308 closed with four documented limits:

**E-308-001 (kappa face model)**: inscribed curvature κ_i = 2/l_i is a flat-face
approximation; actual curvature of rounded bbox requires surface sampling.

**E-308-002 (eta_AC interpretation)**: eta_AC measures coefficient alignment, not
information flow. Directed mutual information I(S_A;S_C) across time is unmeasured.

**E-308-003 (bbox-hash K_bound)**: K_bound is spatially varying but not used to gate
partition depth. Budget termination is depth-only.

**E-308-004 (G_C non-zero signal)**: kappa_integral != kappa_parent means G_C != 0 only
if W_C cannot reconstruct Z_C. No explicit non-lossless operator produces persistent G_C.

EXP-309 introduces a different axis: **observer-awareness**. Instead of refining the
curvature formula, it makes the validity protocol itself spatial. Claims far from the
observer focal point have expensive predicates (is_valid_kappa_308, is_unit_norm) deferred
to a lower validity class. This creates a Synchronous Predicate Relaxation Tier (SPRT)
without async non-determinism.

---

## 1. Stalk Schema -- d=12 (unchanged from EXP-308)

    F(v) in R^12 = [Sector A | Sector B | Sector C]
    seed_stalk = [1,1,1,1, 0.5,0.5,0.5,1, 0,0,1,2]

---

## 2. LOD Operator

### 2.1 Definition

    LOD(bbox, f, eps=1e-12):
        c  = (lo + hi) / 2.0          centroid of bbox
        l  = max(lx, ly, lz)          characteristic scale
        return l / (||c - f||_2 + eps)

    f in R^3: focal point (mass-weighted centroid of active leaves, see §4)

LOD is dimensionless. LOD -> inf as bbox approaches focal point (fully validated).
LOD -> 0 as bbox recedes from focal point (predicates bypassed).

### 2.2 Bypass Thresholds (locked)

    tau_kappa   = 0.05   is_valid_kappa_308: bypass when LOD < 0.05
    tau_norm    = 0.10   is_unit_norm:       bypass when LOD < 0.10
    tau_spatial = 0.01   is_spatially_valid: bypass when LOD < 0.01

    NON_BYPASSABLE: is_valid, is_valid_b, is_valid_block_diagonal_306

### 2.3 Bypass Distance Interpretation

    LOD < tau  <=>  dist(centroid, f) > max(l) / tau

    tau=0.10: normal validation bypassed when dist > 10x bbox size.
    Bypass threshold is depth-adaptive: smaller leaves (deeper recursion)
    survive closer to focal region before bypassing. Scale-invariant.

### 2.4 P_yz Invariance of LOD (exact proof)

Under P_yz: mirror_bbox has lo'[0]=-hi[0], hi'[0]=-lo[0]; mirror_focal f'=(-f[0],f[1],f[2]).

    centroid_mirror = (-cx, cy, cz)
    ||centroid_mirror - f'||_2 = ||(f[0]-cx, cy-f[1], cz-f[2])||_2
                               = ||centroid_fwd - f||_2       [exact]

    max(lx',ly',lz') = max(|hi[0]-lo[0]|, ly, lz)
                     = max(lx, ly, lz)                        [exact]

    LOD(mirror_bbox, mirror_f) = LOD(fwd_bbox, fwd_f)         [exact, machine precision]

---

## 3. Synchronous Predicate Relaxation Tier (SPRT)

### 3.1 Validity Classes

    FULL_VALID:   all 6 predicates pass synchronously at seal()
                  cacheable=True, revert_target=True, partition_source=True

    LOD_RELAXED:  {is_valid, is_valid_b, is_valid_block_diagonal_306} pass
                  >=1 of {is_valid_kappa_308, is_unit_norm, is_spatially_valid} bypassed
                  cacheable=False, revert_target=False, partition_source=False

    INVALID:      any NON_BYPASSABLE predicate fails -> revert to last FULL_VALID H_t

validity_class is an annotation field on MuState; NOT included in H_t hash computation.
H_t = HASH(Z_t + S_t + W_t + t + protocol_version) [unchanged from EXP-308].

### 3.2 Partition Guard

LOD_RELAXED claims MUST NOT be partition sources. apply_gamma_309 raises PartitionError
if called on a claim whose validity_class is LOD_RELAXED.

    if mu.validity_class(claim_id) == 'LOD_RELAXED':
        raise PartitionError("GAMMA309_LOD_GUARD: LOD_RELAXED claim cannot be partitioned")

### 3.3 Hash Continuity

Only FULL_VALID states are revert targets. On INVALID: revert to last FULL_VALID H_t.
LOD_RELAXED states carry their H_t as a structural index only; never used for revert.

---

## 4. Focal Point f_t

### 4.1 Strong Formulation (mass-weighted centroid)

    f_{t+1} = sum_{cid in W_t} pos_cid * mass_cid  /  sum mass_cid

    pos_cid  = stalk_B[cid][0:3]   (dims 4,5,6 -- x,y,z)
    mass_cid = ||stalk_A[cid]||_2  (dims 0:4 -- mass,r,g,b norm)

    Fallback (sum mass_cid < 1e-12):
        f = geometric centroid of all active bbox centroids

### 4.2 Convergence Predicate

    ||f_{t+1} - f_t||_2 < eps_convergence   (eps_convergence = 1e-8)

f_t is a pure numeric observable -- shape (3,), not stored in stalk, not in H_t.
Stored as mu.focal_point annotation field.

### 4.3 P_yz Invariance of f_t

Under P_yz (x -> -x): stalk_B[4] -> -stalk_B[4]; mass norm unchanged.
    f_mirror[0] = -f_fwd[0],  f_mirror[1] = f_fwd[1],  f_mirror[2] = f_fwd[2]
    LOD(mirror_bbox, mirror_f) = LOD(fwd_bbox, fwd_f)  [from §2.4]

---

## 5. Ghost Quarantine

When any active claim has is_valid_kappa_308 in its bypass set, stalk[11] may not equal
kappa_integral(bbox). This contaminates G_C = Z_C - Pi_W(Z_C) with a validity artifact.

Quarantine rules (applied in next_S_C_309):

    CASE 1 (kappa bypassed):    freeze S_C entirely -- return S_C unchanged
    CASE 2 (only norm bypassed): freeze S_C[0:3] (normal dims); update S_C[3] (kappa dim)
    CASE 3 (no bypass):         full EMA update (standard EXP-308 behavior)

This ensures B_C(t) = ||S_C|| / (||Z_C|| + eps) reports genuine geometric residual only,
not bypass artifacts.

Under CASE 1 freeze: B_C changes only due to Z_C variation (partition changes active
stalks), not due to ghost accumulation. Observable purity maintained.

---

## 6. Operators

### 6.1 apply_gamma_309

Replaces apply_gamma_308 for EXP-309 studies. Identical except:
    - Takes focal_point parameter (f in R^3)
    - After partition: computes LOD for each child claim
    - Assigns validity_class to output MuState
    - Partition guard: raises PartitionError if source claim is LOD_RELAXED
    - Updates mu.focal_point to next_focal_point()

Post-validates: FULL_VALID requires all 6 predicates; LOD_RELAXED allows bypass per §3.1.

### 6.2 apply_gamma_309_recursive

Recursive Gamma with LOD gating:
    - K_budget decay: K_budget * exp(-LAMBDA_DECAY * depth)  [unchanged from EXP-308]
    - LOD guard: if child.validity_class == LOD_RELAXED -> skip recursion into that child
    - Focal point update: after each partition, update mu.focal_point
    - S_C quarantine: apply next_S_C_309 quarantine at each level

---

## 7. Validity Predicates (6 + 1 new)

    is_valid, is_valid_b, is_unit_norm, is_spatially_valid,
    is_valid_block_diagonal_306, is_valid_kappa_308:  inherited from EXP-308.

    is_lod_valid_309(mu, focal_point, thresholds):   NEW
        Returns (bool, validity_class_str).
        True + 'FULL_VALID':   all 6 pass; no bypass active.
        True + 'LOD_RELAXED':  non-bypassed pass; bypassed predicates skipped.
        False + 'INVALID':     any non-bypassed predicate fails.

---

## 8. Fork Structure

    Fork A (run_seed_exp309.py):
        - LOD values at unit cube focal=[0.5,0.5,0.5]: LOD=inf (seed at focal)
        - LOD values at distant focal=[100,100,100]: verify bypass assignment
        - FULL_VALID vs LOD_RELAXED correct assignment
        - Focal point convergence: ||f_{t+1} - f_t|| < 1e-8 after octree depth 4
        - S_C quarantine: B_C frozen during bypass, resumes after FULL_VALID
        - LOD_RELAXED partition guard: PartitionError on bypass claim

    Fork B (run_p_invariance_exp309.py):
        - LOD(mirror_bbox, mirror_f) == LOD(fwd_bbox, fwd_f): max_err < 1e-14
        - validity_class P_yz invariant: FULL_VALID <-> FULL_VALID, RELAXED <-> RELAXED
        - f_mirror = P_yz(f_fwd): f_mirror[0] = -f_fwd[0]
        - B_C quarantine invariant under P_yz

---

## 9. Known Limits of EXP-309

| limit | description | resolution path |
|-------|-------------|-----------------|
| LOD threshold fixed | tau values are locked constants; no adaptive threshold | EXP-310: tau(depth) = tau_0 * exp(-mu*depth) |
| temporal cache deferred | FULL_VALID caching not yet implemented | EXP-310: Dict[H_t -> MuState] with TTL |
| kappa_eff deferred | gravitational backreaction on kappa_integral not yet a predicate | EXP-310: kappa_eff = kappa_integral * (1 + gamma/LOD) |
| focal P_yz only | f_t invariance proven for P_yz; other symmetries (rotations) untested | EXP-310: SO(3) invariance of LOD under rigid rotation of bbox+focal |
| LOD_RELAXED terminal | relaxed claims are leaves only; no coarse-to-fine refinement | EXP-310: refine LOD_RELAXED claim when focal moves close |

---

## 10. Commitment Chain

EXP-301 -> EXP-302 -> EXP-303 -> EXP-304 -> EXP-305 -> EXP-306 -> EXP-307 -> EXP-308 ->
**EXP-309 (SPRT; LOD operator; focal_point mass-weighted centroid; ghost quarantine;
           FULL_VALID/LOD_RELAXED validity classes; LOD P_yz invariance)**
