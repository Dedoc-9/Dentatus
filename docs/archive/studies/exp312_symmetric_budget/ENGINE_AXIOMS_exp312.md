# ENGINE_AXIOMS -- EXP-312: The Symmetric Budget
**Protocol version:** exp312-v1
**Inherits:** exp311-v1
**Declaration hash:** e6c4ee25d9f0dca47f2ee0704c007f5772c381a9242d5014c6b00970cdf0e112

---

## A. Problem Statement: P_yz Asymmetry Sources

EXP-311 Fork B confirmed single-step P_yz invariance but deferred multi-step. Diagnostic
(EXP-312 gate) identified two independent asymmetry sources in apply_gamma_311_recursive:

### A.1 Source 1 -- Absolute-coordinate payload

`_bbox_hash_payload(bbox, depth, index)` encodes:
```
SHA256(pack(>ddd, lo[0], lo[1], lo[2]) + pack(>ddd, hi[0], hi[1], hi[2]) + ...)[:16]
```
Under P_yz (x->-x): lo[0], hi[0] negate -> different SHA256 input -> different 16-char hex.
K_bound = len(zlib.compress(payload)) is empirically constant (24 bytes) for any 16-char hex;
the asymmetry propagates via claim ID differences, not K_bound magnitude.

### A.2 Source 2 -- Sector A decompose coupling (root cause of leaf count asymmetry)

For N=8 > d_A=4, apply_gamma_308 uses:
```
full_children = _orthogonal_decompose(parent.stalk, N=8)   # uses ALL 12 dims
stalk_A_children = [c[0:4] for c in full_children]
```
Projection: `alpha_i = basis_col_i.T @ parent.stalk`. Since parent.stalk[4] (Sector B x-coord)
and parent.stalk[8] (Sector C nx) are P_yz-variant, alpha_i differs under P_yz. Child Sector A
masses ||stalk_A_i|| differ -> mass-weighted focal_point diverges -> LOD ratios differ ->
different validity classifications -> different leaf counts.

Empirical: old decompose gives child-0 mass fwd=1.726 vs mir=1.445 (mismatch).

---

## B. Fix 1: _bbox_hash_payload_312

```
_bbox_hash_payload_312(bbox, depth, index):
    ex = abs(hi[0] - lo[0])
    ey = abs(hi[1] - lo[1])
    ez = abs(hi[2] - lo[2])
    return SHA256(pack(>ddd, ex, ey, ez) + pack(>I, depth) + pack(>I, index))[:16]
```

Extents |hi - lo| are unsigned differences, invariant under any coordinate reflection.
All 8 children at each octree depth get identical payloads under P_yz (same extents, same i).
K_bound remains constant (24 bytes per payload).

---

## C. Fix 2: _stalk_A_decompose_312

```
_stalk_A_decompose_312(stalk_A, N, seed=0):
    d_A = len(stalk_A)
    if N <= d_A:
        return _orthogonal_decompose(stalk_A, N, seed=seed)
    padded = zeros(N); padded[:d_A] = stalk_A
    full_children = _orthogonal_decompose(padded, N, seed=seed)
    return [c[:d_A] for c in full_children]
```

Zero-padding Sector A to dim=N before decompose ensures:
1. Input to _orthogonal_decompose depends ONLY on stalk_A (= parent.stalk[0:4]) -- P_yz-invariant
2. Sum conservation: sum(stalk_A_children_i) = sum(c[:d_A] for c in full_children)
   = (sum(full_children))[:d_A] = padded[:d_A] = stalk_A (exact)
3. Child masses ||stalk_A_i|| are identical between P_yz-conjugate runs (machine precision)

Empirical: new decompose gives child-0 mass fwd=0.2531 = mir=0.2531 (match to machine eps).

---

## D. Operator: apply_gamma_312

apply_gamma_312 reimplements the partition kernel (previously delegated to apply_gamma_308
via apply_gamma_309) with fixes B and C applied inline, then adds EXP-311 G_inject EMA:

**Step 1:** Record Z_before = Z_t(mu)
**Step 2:** Run partition kernel with Fix 1 (extents payload) and Fix 2 (Sector A isolation)
**Step 3:** Compute G_inject_C, G_inject_A from Z_before (same as EXP-311)
**Step 4-5:** EMA update S_C, S_A (same as EXP-311)
**Step 6-7:** Propagate G_inject_log, ghost_history from INPUT mu (same as EXP-311)

Partition kernel (steps 2a-2e):
  2a. K-bound check: k_children <= parent.K_bound + C_KBOUND * log(N)
  2b. Backreaction cost: C(1.0, beta, mu.S)
  2c. child_bboxes = _compute_child_bboxes(parent.bbox, partition_key)
  2d. stalk_A_children = _stalk_A_decompose_312(parent.stalk[0:4], N, seed)
  2e. Build child claims: Sector A = stalk_A_i, Sector B = centroid(child_bbox),
      Sector C = [outward_normal, kappa_integral(child_bbox)]
  2f. LOD validity check (SPRT): FULL_VALID or LOD_RELAXED or PartitionError
  2g. Ghost quarantine for LOD_RELAXED
  2h. Update focal_point via next_focal_point()

Returns: (mu_next, cost, validity_class)

---

## E. P_yz Invariance (multi-step)

Theorem: apply_gamma_312_recursive produces identical leaf counts and identical
norm(S_C), norm(S_A) for any P_yz-conjugate initial states, when focal_point is
derived from mu.focal_point_value() (not externally fixed).

Proof sketch:
  - Payload: extents-based -> same payload for P_yz-conjugate bboxes (Fix 1)
  - Sector A children: _stalk_A_decompose_312 -> same masses (Fix 2)
  - Sector B children: centroid(bbox) -> P_yz(centroid_fwd) for mirror (covariant, not invariant)
  - Focal point: next_focal_point() = mass-weighted centroid of Sector B
    Under P_yz: focal_point -> P_yz(focal_point) (covariant)
  - LOD: max_extent / ||centroid_i - focal_point|| = max_extent / ||P_yz(c_i - fp)||
    = max_extent / ||c_i - fp|| (Euclidean norm P_yz-invariant) -> same LOD values
  - G_inject_C: f(||Z[0:4]||) -- Sector A norm, P_yz-invariant (same masses)
  - G_inject_A: f(Z[11]) -- kappa_integral(bbox), P_yz-invariant (extents-based)
  -> S_C, S_A evolve identically under P_yz
  -> Recursion tree structure identical (same LOD, same K_budget decay)
  -> leaf_count_fwd == leaf_count_mir (exact, not just approximate)

---

## F. Dev Notes

**Naming correction:** Prior session called this "K_bound P_yz fix." K_bound itself is not
asymmetric (always 24 bytes for any 16-char hex). The actual source is Sector A decompose
coupling (Source 2). The extents-based payload fix (Source 1) is structurally correct
regardless (ensures payload determinism is coordinate-free).

**Gravitational backreaction:** The Sector A decompose coupling is analogous to a gauge
artifact -- the apparent asymmetry arises from choosing an observer-dependent (absolute
coordinate) basis for the mass distribution. Fix 2 projects to the observer-independent
(extent-only) frame before decomposing.

**EXP-313 gate:** After EXP-312, all three candidates are open:
  Option A: Normalize G_inject by steady-state references (coupling ratio correction)
  Option B: Multi-lag KSG TE (lags 1-5, test lag-3 dominance corr3/corr1=20x)

**Hash continuity:** G_inject_log excluded from H_t (same as EXP-311). H_t remains:
HASH(mu_t + Z_t + S_t + W_t + protocol_version). Ghost injection trace is observable only.

---

## G. Forbidden Operations

```
ghost_direct_control | stalk_collapse | retroactive_confluence_cert
budget_retroactive_adjustment | validity_predicate_shift | post_hoc_rewrite_rule_addition
```
