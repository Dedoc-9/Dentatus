# ENGINE AXIOMS -- EXP-308 Integral Curvature Engine (Series 300, eighth study)

**Preregistration status**: GATE LOCKED
**Protocol version**: exp308-v1
**Inherits from**: exp307-v1 -> exp306-v1 -> exp305-v1 -> exp301-v1
**Workspace**: Reality_Engine/studies/exp308_integral_curvature/
**declaration_hash**: `ad5215b859de58d5a57916ee907cb6c69a692e7fac083d111a9ed251c9608304`

---

## 0. Motivation

EXP-307 closed with three documented limits:

**E-307-001 (kappa approximation)**: kappa = tr(H_bbox) = Σᵢ 2/lᵢ is the trace of the diagonal
curvature tensor at the center of a sphere fitting each axis independently. It does not weight
the contribution of each face by its area. On anisotropic bboxes (lx ≠ ly ≠ lz), the largest
face (highest area) contributes the least to tr(H), which is physically incorrect.

**E-307-002 (kappa degenerate)**: When lᵢ → 0, kappa → ∞ without a principled floor.
The clamp (kappa_max = 1e9) in is_valid_kappa is arbitrary.

**E-307-003 (η_AC undefined)**: The coupling observable between Sector A and Sector C ghost
channels was named but not implemented. Ghost orthogonality was confirmed as a subspace
identity (always 0), but the non-trivial coupling — alignment of the per-sector projection
coefficient vectors λ_A and λ_C — was not tracked.

**E-307-004 (bbox-hash payload)**: Auto-payload used parent_id + partition_key + depth + index.
K_bound is therefore constant across all leaves regardless of geometry. A bbox-hash payload
encodes actual spatial position, enabling variable K_bound as a geometric signal.

EXP-308 resolves all four simultaneously.

---

## 1. Stalk Schema -- d=12 (unchanged)

    F(v) in R^12 = [Sector A | Sector B | Sector C]

    Sectors A and B: unchanged from EXP-307.

    Sector C (dims 8-11): [nx, ny, nz, kappa]
      dims 8-10: centroid-outward unit normal -- unchanged
      dim 11:    kappa = kappa_integral(bbox)  -- CHANGED from EXP-307

    seed_stalk = [1,1,1,1,  0.5,0.5,0.5,1,  0,0,1,2]
    seed kappa = kappa_integral([0,1]^3) = 2*(1+1+1)/(1+1+1) = 2.0

---

## 2. Integral Curvature Formula

### 2.1 Derivation

For a rectangular bbox with extents lx, ly, lz:
- Face ±x: area = ly·lz, inscribed curvature κ_x = 2/lx (cylinder with radius lx/2)
- Face ±y: area = lx·lz, inscribed curvature κ_y = 2/ly
- Face ±z: area = lx·ly, inscribed curvature κ_z = 2/lz

Area-weighted mean curvature over the full surface:

    A_total = 2*(lx*ly + ly*lz + lx*lz)

    kappa_integral = (κ_x * 2*ly*lz  +  κ_y * 2*lx*lz  +  κ_z * 2*lx*ly) / A_total
                   = (2/lx * 2*ly*lz  +  2/ly * 2*lx*lz  +  2/lz * 2*lx*ly) / (2*(lx*ly+ly*lz+lx*lz))
                   = 2*(ly*lz/lx + lx*lz/ly + lx*ly/lz) / (lx*ly + ly*lz + lx*lz)

### 2.2 Regularization

    eps_rel = 1e-9
    eps     = max(lx, ly, lz) * eps_rel        [relative floor, scale-invariant]
    l_i_reg = max(l_i, eps)                     [applied per-axis independently]
    kappa_integral applies l_i_reg in place of l_i

Rationale: absolute floor (1e-6) and relative floor are identical for all
normal extents >= 1e-3. For degenerate extents < 1e-7, the relative floor
preserves scale-relative precision and avoids over-clamping. Splinter behavior
is invariant under rescaling of the entire bbox, which abs floor is not.

No hard clamp. The formula is continuous and bounded by:
    kappa_integral >= 2  (attained at cube, by AM-GM: each term >= 1 when lx=ly=lz)

### 2.3 Key Values

| bbox | lx | ly | lz | kappa_integral |
|------|----|----|----|---------------|
| unit cube [0,1]^3 | 1 | 1 | 1 | 2.000 |
| bisect_x [0,0.5]x[0,1]^2 | 0.5 | 1 | 1 | 3.000 |
| octant [0,0.5]^3 | 0.5 | 0.5 | 0.5 | 4.000 |
| deep [0,0.25]^3 | 0.25 | 0.25 | 0.25 | 8.000 |
| slab [0,0.1]x[0,1]^2 | 0.1 | 1 | 1 | ~11.18 |

Note: kappa_integral = 2/l for a cube of side l (scales as 2/l, not 6/l as in tr(H)).
Under uniform octree depth D: kappa(D) = 2 * 2^D.

### 2.4 P_yz Invariance

kappa_integral depends only on extents lx, ly, lz = |hi[i]-lo[i]|.
P_yz reflects x-axis: lo[0] -> -hi[0], hi[0] -> -lo[0].
Extents preserved: lx = |hi[0]-lo[0]| unchanged.
Therefore kappa_integral(mirror) = kappa_integral(fwd). Exact.

### 2.5 Restriction Map

    F[11,11] = kappa_child / kappa_parent  (geometric ratio, as in EXP-307)

For axis_bisect_x: F[11,11] = 3.0/2.0 = 1.5
For octree_split:  F[11,11] = 4.0/2.0 = 2.0

---

## 3. Operators

### 3.1 apply_gamma_308

Replaces apply_gamma_307. Identical except:
    kappa_child_i = kappa_integral(child_bbox_i)  [uses integral formula with relative eps_rel=1e-9]
    F[11,11] = kappa_child_i / kappa_parent

Post-validates: 6 predicates including is_valid_kappa_308.

### 3.2 apply_gamma_308_recursive with bbox-hash payload

Replaces apply_gamma_307_recursive. Payload generation:

    bbox_lo_bytes = struct.pack('>ddd', lo[0], lo[1], lo[2])  (IEEE 754 big-endian)
    bbox_hi_bytes = struct.pack('>ddd', hi[0], hi[1], hi[2])
    depth_bytes   = struct.pack('>I', depth)
    index_bytes   = struct.pack('>I', index)
    payload_i = SHA256(bbox_lo_bytes + bbox_hi_bytes + depth_bytes + index_bytes)[:16]

K_bound varies with geometry: payloads encoding different bbox coordinates will have
different compressed sizes. This makes K_bound a spatially varying constraint.

---

## 4. Validity Predicates (6 total)

    is_valid, is_valid_b, is_unit_norm, is_spatially_valid, is_valid_block_diagonal_306:
        unchanged from EXP-307.

    is_valid_kappa_308 (replaces is_valid_kappa):
        For every claim with stalk.shape[0] > 11 AND bbox not None:
          kappa_geom = kappa_integral(claim.bbox)
          | stalk[11] - kappa_geom | < tol  (tol = 1e-8)

---

## 5. η_AC Coupling Observable

### 5.1 Definition

For MuState mu with >= 2 active claims:

    W = mu.W_basis()          shape (12, |W_t|)
    W_A = W[0:8, :]           sector A+B rows
    W_C = W[8:12, :]          sector C rows
    Z_A = mu.Z()[0:8]
    Z_C = mu.Z()[8:12]

    lambda_A = lstsq(W_A, Z_A)    shape (|W_t|,)   coefficient vector for sector A
    lambda_C = lstsq(W_C, Z_C)    shape (|W_t|,)   coefficient vector for sector C

    eta_AC = |lambda_A . lambda_C| / (||lambda_A|| * ||lambda_C|| + eps)

eta_AC = 0: sector A and C ghosts are driven by independent combinations of active stalks.
eta_AC = 1: both sectors reconstruct Z from identical stalk weightings (fully coupled).

### 5.2 Expected Behavior

For lossless centroid-outward octree:
  - lambda_A is determined by _orthogonal_decompose (deterministic, seed-based)
  - lambda_C is determined by centroid geometry (systematic, geometric)
  - These are independent by construction -> eta_AC should be near 0 but not exactly 0
    (both use the same set of active stalks)

eta_AC != 0 does not indicate a violation. It is an observable for monitoring sector coupling
over deep recursive partitions. High eta_AC at depth D > 2 indicates stalk A and stalk C
content are aligning geometrically.

### 5.3 Implementation

New method MuState.eta_AC() in state.py.
Returns float in [0, 1]. Returns 0.0 if |W_t| < 2.

---

## 6. Dual Ghost Architecture (inherited, eta_AC added)

Same S_A/S_C EMA architecture as EXP-306/307.
B_A(t), B_C(t) inherited.
eta_AC(t) added as third dual-space observable.

---

## 7. Recursive Gamma Parameters (inherited)

    lambda = ln(2), K_MIN_PARTITION = 16, K_budget_0 = 256, depth_max = 4
    payload_generation: bbox_hash (replaces EXP-307 auto-payload)

---

## 8. Known Limits of EXP-308

| limit | description | resolution path |
|-------|-------------|-----------------|
| kappa face model | inscribed curvature κ_i = 2/l_i is a flat-face approximation; actual curvature of rounded bbox varies | EXP-309: kappa via Monte Carlo surface sampling |
| eta_AC interpretation | eta_AC measures coefficient alignment, not information flow | EXP-309: directed mutual information I(S_A;S_C) across time |
| bbox-hash K_bound | K_bound now spatially varying but not used to gate partition depth | EXP-309: K_bound(depth) feeds recursive termination directly |
| G_C non-zero signal | kappa_integral != kappa_308 parent means G_C != 0 only if W_C cannot reconstruct Z_C | EXP-309: design explicit non-lossless operator to generate persistent G_C |

---

## 9. Commitment Chain

EXP-301 -> EXP-302 -> EXP-303 -> EXP-304 -> EXP-305 -> EXP-306 -> EXP-307 ->
**EXP-308 (R^12 integral curvature; kappa=area-weighted mean curvature; is_valid_kappa_308;
           eta_AC coupling observable; bbox-hash payload)**
