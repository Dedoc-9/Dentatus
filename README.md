# Reality Engine — Series 300–400 (Dentatus)

Generative reality engine implementing a cellular sheaf state machine over a claim DAG.
State evolution is governed by a fixed operator pipeline with immutable hash-indexed states,
dual ghost channels, and preregistered validity predicates.

**Author**: Daniel J. Dillberg — bigdilly95@gmail.com  
**License**: GNU Affero General Public License v3.0 — see `AGPL-3.0`

---

## Architecture

### State

`engine/state.py` — core state structures.

```
H_t = SHA256(Z_t ⊕ S_t ⊕ W_t ⊕ t ⊕ protocol_version)
G_t = Z_t − Π_{W_t}(Z_t)
S_{t+1} = α·S_t + (1−α)·G_t
```

`MuState` holds the claim DAG (`claims`, `entailments`), active leaf set `W_t`, and EMA ghost `S`.
Every state transition requires `seal()` before the hash `H_t` is accessible.
Dual ghost channels `S_A` (dims 0–7) and `S_C` (dims 8–11) are tracked independently (EXP-306+).

### Operator pipeline

```
μ → Lτ → Bτ → Rτ → Z → S → W → OBS
```

Each operator is stateless and depends only on declared inputs/outputs.
Cross-stage mutation outside the defined mapping is forbidden.

`engine/operators.py` implements:

| Operator | Study | Description |
|----------|-------|-------------|
| `apply_gamma_306` / `_recursive` | EXP-306 | kappa additive: `kappa_child = kappa_parent * ω_i` |
| `apply_gamma_307` / `_recursive` | EXP-307 | shape operator trace: `tr(H_bbox) = Σ 2/l_i` |
| `apply_gamma_308` / `_recursive` | EXP-308 | area-weighted integral curvature; bbox-hash payload |
| `apply_gamma_309` / `_recursive` | EXP-309 | SPRT LOD gating; focal point update; ghost quarantine |
| `apply_gamma_311` / `_recursive` | EXP-311 | G_inject auxiliary residual; dual EMA activation |
| `apply_gamma_312` / `_recursive` | EXP-312 | extents payload + uniform Sector A split; full P_yz symmetry |
| `apply_gamma_313` / `_recursive` | EXP-313 | Zeeman K_bound: softmax-weighted child budgets; P_yz-covariant |
| `apply_gamma_314` / `_recursive` | EXP-314 | Hyperfine ghost: Ω_AC inter-channel precession angle; τ_opt lag |
| `apply_gamma_315` / `_recursive` | EXP-315 | Dual G_inject_A: mass-norm→S_A[0], kappa→S_A[3]; primary arccos path |
| `apply_gamma_316` / `_recursive` | EXP-316 | 3-component G_inject_A: adds y-agg→S_A[1]; τ_opt range {1,2,3}; Series 300 final |
| `apply_gamma_401` / `_recursive` | EXP-401 | d=18 stalk; log-Cholesky Σ (S_D); G_inject_D ∝ B̂⊗B̂·τ_norm; Σ_mir=R·Σ_fwd·Rᵀ |

### Stalk schema — d=12

```
F(v) ∈ ℝ¹²  =  [Sector A (0-3) | Sector B (4-7) | Sector C (8-11)]

Sector A: [mass, r, g, b]          — photometric
Sector B: [x, y, z, w]             — affine position + weight
Sector C: [nx, ny, nz, kappa]      — centroid-outward unit normal + curvature
```

Restriction map `F` is block-diagonal 12×12; no cross-sector coupling.

### Stalk schema — d=18 (EXP-401+)

```
F(v) ∈ ℝ¹⁸  =  [Sector A (0-3) | Sector B (4-7) | Sector C (8-11) | Sector D (12-17)]

Sector D: [log_l11, log_l22, log_l33, l21, l31, l32]  — log-Cholesky covariance
  L[i,i] = exp(log_lii) > 0  always (positive diagonal guaranteed)
  Σ = L·Lᵀ  (positive-definite guaranteed)
```

Sector D is NOT partition-inherited. Child stalks have `stalk[12:18] = 0`.
`S_D` tracks Sector D covariance exclusively via EMA ghost injection.
`is_valid_block_diagonal_306` extended to 18×18: Sector D cross-blocks must be zero.

### Validity predicates (EXP-308, 6 total)

| Predicate | Description |
|-----------|-------------|
| `is_valid` | `F @ stalk_parent == stalk_child` for all entailments |
| `is_valid_b` | Sector B barycentric weights sum to 1; `w=1` |
| `is_unit_norm` | `‖stalk[8:11]‖ = 1.0` for all d≥11 claims |
| `is_spatially_valid` | bbox containment on SPATIAL edges |
| `is_valid_block_diagonal_306` | no cross-sector coupling in F (d=12) |
| `is_valid_kappa_308` | `stalk[11] == kappa_integral(bbox)` for all claims with bbox |

State is valid only when all 6 predicates pass simultaneously.
On failure, execution reverts to the last valid hashed state.

### Ghost channel

```
G_t = Z_t − Π_{W_t}(Z_t)              residual (0 for lossless operators)
S_{t+1} = α·S_t + (1−α)·G_t           EMA accumulation (α = 0.85)

B(t)   = ‖S‖   / (‖Z‖   + ε)          global ghost ratio
B_A(t) = ‖S_A‖ / (‖Z_A‖ + ε)          sector A+B ghost ratio
B_C(t) = ‖S_C‖ / (‖Z_C‖ + ε)          sector C ghost ratio
```

`G_t` is a numeric residual only — not an entity, not directly controlled.
Dual arithmetic (forward Z space vs dual S/G space) is never collapsed.

EXP-401 adds `S_D` (Sector D dual, d=6) tracking log-Cholesky covariance off-diagonals:
```
B_D(t) = ‖S_D‖ / (‖Z_D‖ + ε)          sector D covariance ghost ratio
```

---

## Study series

| Study | Description | declaration_hash (first 16) | Status |
|-------|-------------|----------------------------|--------|
| EXP-301 | R⁴ symbolic generative engine | — | closed |
| EXP-302 | R⁶ pos×col; sum conservation | — | closed |
| EXP-303 | R⁹ pos×col×nrm; Gamma; bbox containment | — | closed |
| EXP-304 | R⁸ dual-sector; Sector B barycentric | — | closed |
| EXP-305 | R¹¹ triple-sector; Sector C unit-norm; P_yz; block-diagonal F | — | closed |
| EXP-306 | R¹² curvature engine; centroid-outward normals; kappa additive; dual ghost S_A/S_C | `5a8e1afc590d8ffb` | closed |
| EXP-307 | R¹² shape operator; kappa = tr(H_bbox); auto-payload recursive Gamma | `8e288c601093e1dd` | closed |
| EXP-308 | R¹² integral curvature; area-weighted mean curvature; η_AC; bbox-hash payload | `ad5215b859de58d5` | closed |
| EXP-309 | SPRT LOD gating; focal point evolution; ghost quarantine | `c2f9b341...` | closed |
| EXP-310 | KSG transfer entropy S_A→S_C; lag-3 coupling confirmed | — | closed |
| EXP-311 | G_inject auxiliary residual; dual EMA activation; single-step P_yz | `10659ed4d37c027a` | closed |
| EXP-312 | Asymmetry Debt closure; full multi-step P_yz invariance | `2e6ccdc20da7aefb` | closed |
| EXP-313 | Zeeman K_bound; anisotropic budget via softmax field alignment | `2431d09f38554a9b` | closed |
| EXP-314 | Hyperfine ghost; Ω_AC precession angle; architecture-driven τ_opt | `5ca52bef5d2a5080` | closed |
| EXP-315 | Dual G_inject_A; primary arccos path active; τ_opt varies with mass/kappa | `e16dd1a01735bc1d` | closed |
| EXP-316 | 3-component G_inject_A; y-agg→S_A[1]; τ_opt range {1,2,3}; Series 300 final | `522ca73148485fdc` | **closed** |
| EXP-401 | d=18 stalk; log-Cholesky Σ via S_D; G_inject_D ∝ B̂⊗B̂·τ_norm; Σ_mir=R·Σ_fwd·Rᵀ | `ff1fb75eb819cf1e` | **open** |

Each study is gate-locked before implementation. `SEED_DECLARATION_*.json` hashes are
immutable structural indices — not semantic labels.

---

## EXP-312 — The Symmetric Budget

**Goal:** close the P_yz Asymmetry Debt — full multi-step leaf-count invariance under reflection x→−x.

**Root causes (both closed):**

| Source | Description | Fix |
|--------|-------------|-----|
| Source 1 | `_bbox_hash_payload` encoded absolute x-coords → K_bound P_yz-variant | `_bbox_hash_payload_312`: f(|hi−lo|) extents only |
| Source 2 | `_orthogonal_decompose(stalk, N)` assigned mass by algebraic index; under P_yz octant i↔i XOR 4 permutes → focal point diverges | uniform split: `stalk_A_i = stalk_A / N` |

**Invariance proof (Fix 2):**

```
stalk_A_i = stalk_A/N  →  all child masses equal
mass-weighted centroid = (1/N)·Σ centroid_i = geometric centroid of bbox
‖P_yz(c) − P_yz(fp)‖ = ‖P_yz(c − fp)‖ = ‖c − fp‖   (isometry)
LOD_fwd(i) = LOD_mir(i XOR 4)  →  identical gating  →  identical tree
```

**Results:**

```
fwd_leaves == mir_leaves == 36    (was 92 vs 99 in EXP-311)
cost delta  = 7.99e-15            (machine epsilon)
norm(S_C):  0.03915037 = 0.03915037
norm(S_A):  1.49806877 = 1.49806877
```

Fork A (`run_seed_exp312.py`): 8/8 PASS
Fork B (`run_p_invariance_exp312.py`): 10/10 PASS

---

## EXP-315 — Dual G_inject_A Activation

**Goal:** activate the primary Ω_AC arccos path by routing two physically distinct quantities into orthogonal dims of `S_A[0:4]`. Closes ghost #6 degeneracy from EXP-314.

**Injection change (EXP-315 vs EXP-314):**

```
EXP-311/312/313/314:
  G_inject_A[7] = alpha_leak * beta_CA * (kappa / kappa_ref)   [sole channel]

EXP-315:
  G_inject_A[0] = alpha_leak * (mass_norm / mass_ref)          [mass-norm coupling, dim 0]
  G_inject_A[3] = alpha_leak * beta_CA * (kappa / kappa_ref)   [kappa coupling, dim 3]
  G_inject_C[3] = alpha_leak * (mass_norm / mass_ref)          [unchanged]
```

**Omega_AC mechanics:**

After EMA from zero: `S_A[0:4] ≈ [S_A0, 0, 0, S_A3]` with `S_C ≈ [0, 0, 0, S_C3]`.

```
v_A = J_AC @ S_A[0:4] = [S_A0, 0, 0, S_A3]

cos(Ω_AC) = S_A3 / sqrt(S_A0² + S_A3²)
Ω_AC      = arctan(S_A0 / S_A3)
           = arctan(mass_norm / (beta_CA · kappa))
```

Primary arccos path active: `‖v_A‖ = sqrt(S_A0² + S_A3²) ~ 6.17 >> 1e-6`. Fallback never triggers.

**Analytical prediction (step 1):**

```
G_inject_A[0] / G_inject_A[3] = (mass_norm/mass_ref) / (beta_CA * kappa/kappa_ref)
For seed stalk: mass_norm=2.0, kappa=2.0, beta_CA=0.3
  ratio = 1/(0.3) = 3.33  →  Ω_AC = arctan(3.33) = 1.28 rad (73.3°)
As tree deepens, kappa grows (more leaves) → ratio → 0 → Ω_AC → 0 → τ_opt → 1
```

**Results:**

```
‖v_A‖ = 6.170405 >> 1e-6  (primary arccos path confirmed)
Ω_AC step 1 = 1.2793 rad   (matches analytical prediction)
Ω_AC final  = 0.0086 rad   (kappa-dominated at depth)
τ_opt varies: {1, 3}        (non-constant across 13 partition steps)
Ω_AC_fwd == Ω_AC_mir  (delta = 1.84e-12)
Full trace: tau_mismatches = 0/13,  max_omega_delta = 2.45e-12
fwd_leaves == mir_leaves == 92
```

Fork A (`run_seed_exp315.py`): 8/8 PASS
Fork B (`run_p_invariance_exp315.py`): 10/10 PASS

---

## EXP-316 — 3-Component G_inject_A (Series 300 Hardening)

**Goal:** promote `v_A` from a 2-component planar vector to a 3-component non-degenerate vector
by adding a y-aggregate injection channel. Full 4D angular resolution of ghost precession.

**Injection change (EXP-316 vs EXP-315):**

```
EXP-315:
  G_inject_A[0] = alpha_leak * (mass_norm / mass_ref)          [dim 0]
  G_inject_A[3] = alpha_leak * beta_CA * (kappa / kappa_ref)   [dim 3]

EXP-316:
  G_inject_A[0] = alpha_leak * (mass_norm / mass_ref)          [dim 0, unchanged]
  G_inject_A[1] = alpha_leak * (|Z_before[5]| / y_ref)         [dim 1, NEW: y-aggregate]
  G_inject_A[3] = alpha_leak * beta_CA * (kappa / kappa_ref)   [dim 3, unchanged]
```

**3-component Ω_AC:**

```
v_A = J_AC @ S_A[0:4] = [S_A0, S_A1, 0, S_A3]

cos(Ω_AC) = S_A3 / sqrt(S_A0² + S_A1² + S_A3²)

‖v_A‖_316 = sqrt(S_A0² + S_A1² + S_A3²) > ‖v_A‖_315
```

**P_yz invariance of S_A[1]:**
`Z_before[5]` = aggregate y-coordinate (Sector B dim 1). Under P_yz, `p_yz_stalk` negates
`stalk[4]` (x) and `stalk[8]` (nx). `stalk[5]` (y) is unchanged → `|Z_before[5]|` P_yz-invariant → S_A[1]_fwd = S_A[1]_mir exactly.

**Interface extension:**
`g_inject_fn` in `apply_gamma_312` now receives `Z_before=Z_before` as keyword arg.
`_g_inject_315` updated to accept `Z_before=None` (ignored). Fully backward-compatible.

**Results (seed stalk, K_budget=2048):**

```
92 leaves, ‖v_A‖ = 6.6065  (vs 6.1704 in EXP-315)
S_A[0] = 0.0533  S_A[1] = 2.3604  S_A[3] = 6.1702
Ω_AC step 1 = 1.31 rad (75.0°)  [vs 1.28 rad EXP-315]
Ω_AC final  = 0.366 rad (20.9°)
τ_opt range = {1, 2, 3}  (vs {1, 3} EXP-315)
Ω_AC_fwd == Ω_AC_mir  (delta = 6.57e-13)
S_A[1] delta fwd/mir = 8.88e-16  (machine precision)
Full trace: tau_mismatches = 0/13,  max_omega_delta = 8.87e-13
fwd_leaves == mir_leaves == 92
```

Fork A (`run_seed_exp316.py`): 10/10 PASS
Fork B (`run_p_invariance_exp316.py`): 13/13 PASS

---

## EXP-313 — The Zeeman K_bound

**Goal:** introduce anisotropic budget allocation via Zeeman-analogue field alignment, with exact P_yz covariance.

**Zeeman weighting:**

```
B_hat = B / ‖B‖
centroids = (bbox_lo + bbox_hi) / 2  for each child octant i
w_i = softmax(beta_Z * centroid_i · B_hat)         # unnormalized Zeeman weight
K_child_i = K_budget * w_i * exp(-LAMBDA_DECAY)    # EMA budget with decay
```

Sorting children by descending `w_i` before recursion ensures consistent ordering
independent of P_yz reflection (octant i ↔ i XOR 4 under x→−x).

**Results:**

```
92 leaves, K_ratio = max(w)/min(w) = 4.73 (anisotropy confirmed)
P_yz: fwd == mir == 92 leaves, cost delta < 1e-8
```

Fork A (`run_seed_exp313.py`): PASS
Fork B (`run_p_invariance_exp313.py`): PASS

---

## EXP-314 — Hyperfine Ghost: Ω_AC

**Goal:** introduce the inter-channel precession observable Ω_AC between S_A and S_C, and derive
τ_opt (architecture-driven lag window) from it.

**Formula:**

```
v_A = J_AC @ S_A[0:4]
Ω_AC = arccos(clip(v_A · S_C / (‖v_A‖·‖S_C‖ + ε), −1, 1))
τ_opt = max(1, round(Ω_AC / π · W_max))
```

**Fallback (NUMERIC_FLOOR = 1e-6):** when `‖v_A‖ < 1e-6` (degenerate case where S_A[0:4] = 0),
fall back to `Ω_AC = 2·arctan2(‖S_C‖, ‖S_A‖)`. This is P_yz-invariant via norm invariance
(proven by EXP-313 Fork B).

**Results:**

```
13 EXP-314 ghost_history entries (4-tuple filter)
Ω_AC range: [0.017, 2.56] rad
τ_opt ∈ {1..7}
Ω_AC P_yz-invariant (delta = 2.00e-14)
```

Fork A (`run_seed_exp314.py`): 8/8 PASS
Fork B (`run_p_invariance_exp314.py`): 9/9 PASS

---

## Ghost dev notes

### Ghost #1 — G_inject auxiliary residual (EXP-311)

`G_inject` is an auxiliary residual orthogonal to `G_t = Z_t − Π_W(Z_t)`. It accumulates
into dual EMA channels `S_A` and `S_C` independently. Not derived from the lossless partition;
introduced via injection parameters `(alpha_leak, beta_CA, mass_ref, kappa_ref)`.

### Ghost #2 — Asymmetric budget (EXP-312 fix)

Root cause: `_bbox_hash_payload` encoded absolute x-coordinates → K_bound P_yz-variant.
Fix: extents-only payload `f(|hi−lo|)`. Confirmed closed EXP-312 Fork B.

### Ghost #3 — Mass-weighted centroid divergence (EXP-312 fix)

Root cause: `_orthogonal_decompose` assigned mass by stalk index; under P_yz octant permutation i↔i XOR 4,
focal point centroid diverged. Fix: uniform split `stalk_A_i = stalk_A / N`. Confirmed closed EXP-312.

### Ghost #4 — kappa P_yz symmetry (EXP-312)

`kappa_integral` uses `|hi − lo|` extents only, not absolute bbox positions.
P_yz: `bbox_mir = (-hi_x, lo_x) × [lo_y, hi_y] × [lo_z, hi_z]` → same extents → same kappa. ✓

### Ghost #5 — LOD_RELAXED validity propagation

`LOD_RELAXED` claims from SPRT gating propagate as leaves without further partition.
They contribute to `active` set and cost accounting but carry no children.
Ghost channels accumulate their stalk contribution via EMA normally.

### Ghost #6 — Ω_AC primary path degeneracy (EXP-314 → EXP-315 → EXP-316)

**EXP-314 (degenerate):** with `G_inject_A[7]` as the sole injection channel, `S_A[0:4] = 0`
in exact arithmetic (lossless partition → `G_A = 0`). The primary arccos path degraded to 0/0
resolved by floating-point noise. A numeric fallback (`Ω_AC = 2·arctan2(‖S_C‖, ‖S_A‖)`) provided
P_yz-invariant τ_opt = 1 but with no variation.

**EXP-315 (ghost #6 resolved):** dual injection `G_inject_A[0] = f(mass_norm)` and `G_inject_A[3] = f(kappa)`
gives `S_A[0:4] ≈ [S_A0, 0, 0, S_A3]` with `‖v_A‖ ~ 6.17 >> 1e-6`. Primary arccos path active.
`Ω_AC = arctan(mass_norm / (beta_CA · kappa))` — measures mass/curvature balance at each tree depth.
`τ_opt ∈ {1, 3}` across partition steps; fully P_yz-invariant (trace delta < 2.5e-12).

**EXP-316 (Series 300 hardening):** triple injection adds `G_inject_A[1] = f(|Z_before[5]|)`,
promoting `v_A` to 3-component `[S_A0, S_A1, 0, S_A3]` with `‖v_A‖ = 6.61`.
`Ω_AC` now resolves the full (mass, y-shear, curvature) angular balance.
`τ_opt ∈ {1, 2, 3}` — expanded range for EXP-401 lag window selection.
`S_A[1]` P_yz-invariant (delta = 8.88e-16). All EXP-315 regression tests pass.

The `g_inject_fn` call in `apply_gamma_312` now passes `Z_before=Z_before` as keyword arg,
enabling downstream experiments to read any aggregate stalk dimension. Default (`g_inject_fn=None`)
preserves all EXP-311/312/313/314/315 behavior exactly (backward-compatible).

### LOD_RELAXED validity class propagation

LOD_RELAXED claims are created when the SPRT test in `apply_gamma_309` decides a claim
does not need further partition. The validity class is propagated from parent to child
claims that do not undergo full partition — they are accepted as-is into the active leaf set.

---

## Running tests

```bash
# Dependencies
pip install numpy scipy

# EXP-401 (current — Series 400 Exp 1)
python run_seed_exp401.py        # Fork A: 10/10 PASS
python run_p_invariance_exp401.py  # Fork B: 10/10 PASS

# EXP-316 (Series 300 final)
python run_seed_exp316.py
python run_p_invariance_exp316.py

# EXP-315
python run_seed_exp315.py
python run_p_invariance_exp315.py

# EXP-314
python run_seed_exp314.py
python run_p_invariance_exp314.py

# EXP-313
python run_seed_exp313.py
python run_p_invariance_exp313.py

# EXP-312
python run_seed_exp312.py
python run_p_invariance_exp312.py
```

---

## Series-300 closure

Series-300 is **closed** as of EXP-316.

| Requirement | Status |
|-------------|--------|
| P_yz multi-step invariance (fwd=mir=92, delta=0) | EXP-312 ✓ |
| Zeeman K_bound P_yz-covariant | EXP-313 ✓ |
| Ω_AC observable + τ_opt derived | EXP-314 ✓ |
| Primary arccos path active; τ_opt varies with depth | EXP-315 ✓ |
| 3-component v_A; τ_opt range {1,2,3}; Series 300 hardened | EXP-316 ✓ |

---

## EXP-401 — Anisotropic Gaussian Covariance (Series 400 Exp 1)

**Status: open** | declaration_hash: `ff1fb75eb819cf1e79e778886ebfdd4291f48e3d2cc7d1dbd0630a603a124323`

### Architecture: d=18 stalk, log-Cholesky Sector D

Stalk extended from d=12 to d=18. Sector D `[12:18]` encodes the lower-triangular
log-Cholesky factor of a 3×3 covariance matrix:

```
L = [[exp(log_l11),  0,            0          ],
     [l21,           exp(log_l22), 0          ],
     [l31,           l32,          exp(log_l33)]]
Σ = L·Lᵀ  (positive-definite by construction)
```

**Architectural choice — d=18 over d=15 (diagonal-only):**
Diagonal-only covariance is an architectural dead end. Zeeman-weighted partitions create
directional pressures that don't respect axis-aligned boundaries. Off-diagonal terms
`l21`, `l31`, `l32` encode the tilt of the covariance ellipsoid. Without them, the Ghost
cannot track correlation between x-variance and y-variance under B-field rotation.

### G_inject_D

```
G_inject_D[3] = α_D · τ_norm · B̂[0]·B̂[1]    (l21: xy coupling)
G_inject_D[4] = α_D · τ_norm · B̂[0]·B̂[2]    (l31: xz coupling)
G_inject_D[5] = α_D · τ_norm · B̂[1]·B̂[2]    (l32: yz coupling)

τ_norm = τ_opt / W_max    (retarded: from prior ghost_history entry)
α_D = 0.05
```

S_D EMA: `S_D_{t+1} = α·S_D_t + (1−α)·G_inject_D`

### P_yz covariance (NOT invariance)

Covariance is a tensor. Under `P_yz` (x→−x):

```
Σ_mir = R·Σ_fwd·Rᵀ    where R = diag(−1, 1, 1)

S_D[3]_mir = −S_D[3]_fwd    (l21: anti-symmetric)
S_D[4]_mir = −S_D[4]_fwd    (l31: anti-symmetric)
S_D[5]_mir =  S_D[5]_fwd    (l32: symmetric)
‖S_D‖ P_yz-invariant → B_D P_yz-invariant
```

### Verified results

| Fork | Assertions | Result |
|------|-----------|--------|
| Fork A (`run_seed_exp401.py`) | 10/10 | **PASS** |
| Fork B (`run_p_invariance_exp401.py`) | 10/10 | **PASS** |

```
leaves=92  ‖v_A‖=6.606456  ‖S_D‖=0.00042123  B_D=1.0000
Σ off-diagonal: s12=0.000350  s13=0.000210  s23=0.000105
min eigval(Σ)=0.999632 (PD ✓)
max|Σ_mir − R·Σ_fwd·Rᵀ| = 0.00e+00 (Fork B ✓)
```

### Ghost notes (EXP-401)

**Ghost #7 — np.empty(d) uninitialized Sector D:**
`apply_gamma_312` used `np.empty(d)`. With d=18, child stalk positions [12:18] contained
garbage. `is_valid` consistency check `‖F@parent − child‖` failed because F[12:18,:]=0
but child[12:18]≠0. Fix: `np.zeros(d)`. Sector D is NOT partition-inherited.

**Ghost #8 — is_valid_block_diagonal_306 skipped 18×18:**
Extended to handle 18×18 F matrices: ABC cross-blocks + Sector D cross-terms must be zero.

**Ghost #9 — NTFS truncation: operators.py at `mu_next._re`:**
Edit tool truncated after replacement boundary. Fixed via Python append script targeting
the truncation marker; forced recompile with `py_compile.compile()`.

### EXP-402 gate — Ghost-Zeeman homeostasis

```
β_Z_eff(t) = β_Z_base · (1 + γ_fb · B_A(t−1))
B_A(t−1)   = ‖S_A(t−1)‖ / (‖Z_A(t−1)‖ + ε)
```
Operator Φ_fb: declared I/O `(S_A_prev, Z_A_prev, β_Z_base, γ_fb) → β_Z_eff`.
P_yz-invariant. Uses S (EMA), not G. Stability: γ_fb ∈ (0, 2.0), β_Z_base=2.0.
Extension: `β_Z_eff_D(t) = β_Z_base·(1 + γ_fb_D·B_D(t−1))` using Sector D ghost ratio.
