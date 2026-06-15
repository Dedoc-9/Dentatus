# Reality Engine — Series 300–500 (Dentatus)

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
| `apply_gamma_402` / `_recursive` + `phi_fb` | EXP-402 | Ghost-Zeeman homeostasis; β_Z_eff=max(β_min, β_base·(1+γ_A·B_A−γ_D·B_D)); B_A=B_D equilibrium |

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
B_D(t) = ‖S_D‖ / (‖Z_A‖ + ε)          sector D covariance ghost ratio (Z_A denom; Ghost #10)
```
EXP-402 adds `Phi_fb` (declared operator between Z and Bτ):
```
β_Z_eff(t) = max(β_min, β_base·(1 + γ_A·B_A(t−1) − γ_D·B_D(t−1)))
```
Equilibrium: B_A* = B_D* at γ_A = γ_D. Engine self-regulates Zeeman field strength.

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
| EXP-401 | d=18 stalk; log-Cholesky Σ via S_D; G_inject_D ∝ B̂⊗B̂·τ_norm; Σ_mir=R·Σ_fwd·Rᵀ | `ff1fb75eb819cf1e` | **closed** |
| EXP-402 | Phi_fb dual pullback; β_Z_eff=max(β_min,β_base·(1+γ_A·B_A−γ_D·B_D)); B_A/B_D equilibrium | `d933ad3ba860b601` | **closed** |
| EXP-403 | Sequential scene refinement; EMA warmup across N=20 scenes; β_Z_eff* convergence; saturation gate | `b2cfdf2e16e1617e` | **closed** |
| EXP-404 | Exponential phi_fb; saturation_ratio 0.60→0.20; β_Z_eff*=17.19; Ω_fb=760%; Ghost #14/#15 | `e7447ec6a65022a2` | **closed** |
| EXP-405 | Adaptive γ warmup; ramp(n)=1−exp(−n/τ); overshoot eliminated; Ghost #16 2-cycle | `6e498f656aeb0fce` | **closed** |
| EXP-406 | EMA-smoothed β_Z_eff (inertial attention); 2-cycle damped 38%; Ghost #17 lag | `84255beb1f11d018` | **closed** |
| EXP-407 | Adaptive α_bze ramp↓ (α_min=0.7>α_crit=2/3); tail_range 2.71; Ghost #18 | `2dc29bcfbb1d7b02` | **closed** |
| EXP-408 | Ascending α_bze ramp↑; tail_range 0.93; Ghost #19 Attraktorwahl (basin lock) | `d1945e6736a284a3` | **closed** |
| EXP-409 | Hysteresis α latch (β_threshold=12.0); convergence+basin jointly resolved; Series 400 close | `32a0fbef5f6e5e1e` | **closed** |
| EXP-501 | Manifold Observation; Sheaf Coboundary δ₀ G_ent; Sector D XOR connection; λ₂ Fiedler | `bfbf52c2977f436a` | **open** |
| EXP-502 | Manifold Firewall is_manifold_501 (ε=0.8); degree-normalized G_ent (Ghost #22); EXP-503 spectral scaffold | `0979f7f520421a28` | **open** |
| EXP-503 | Spectral manifold feedback Phi_fb_manifold; β_Z_eff=f(B_A,B_D,B_ent_spectral); bounded Ω_ent_sp; Ghost #25 | `16f3e47232a3a84e` | **open** |

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

# EXP-404 (current — Series 400 Exp 4)
python run_seed_exp404.py          # Fork A: 10/10 PASS
python run_p_invariance_exp404.py  # Fork B: 5/5 PASS

# EXP-403 (Series 400 Exp 3)
python run_seed_exp403.py          # Fork A: 10/10 PASS
python run_p_invariance_exp403.py  # Fork B: 5/5 PASS

# EXP-402 (Series 400 Exp 2)
python run_seed_exp402.py          # Fork A: 10/10 PASS
python run_p_invariance_exp402.py  # Fork B: 5/5 PASS

# EXP-401 (Series 400 Exp 1)
python run_seed_exp401.py          # Fork A: 10/10 PASS
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

## Series-400 closure

Series-400 (Homeostatic Metabolism) is **closed** as of EXP-409.

| Requirement | Status |
|-------------|--------|
| d=18 log-Cholesky Σ; Sector D dual ghost S_D | EXP-401 ✓ |
| Φ_fb Ghost-Zeeman homeostasis; B_A/B_D equilibrium | EXP-402 ✓ |
| Sequential N=20 scene refinement; β_Z_eff* convergence | EXP-403 ✓ |
| Exponential Φ_fb; saturation resolved (0.60→0.20) | EXP-404 ✓ |
| Overshoot eliminated (adaptive γ / EMA / α schedules) | EXP-405–408 ✓ |
| Hysteresis latch (β_threshold=12.0); convergence + basin jointly | EXP-409 ✓ |

Engine ground truth: a stabilized **71-leaf octree** with **~198 face-adjacent edges**
(N_edges ∈ {198, 219}; median 198), λ₂ ≈ 0.32, machine-precision P_yz symmetry (δ ≈ 10⁻¹⁴–10⁻¹⁶).

---

## Series-500 status (Manifold Integration — OPEN)

| Study | Role | Status |
|-------|------|--------|
| EXP-501 | Manifold Observation — sheaf coboundary δ₀, Sector D XOR *Zusammenhang*, λ₂ Fiedler | observation-only ✓ |
| EXP-502 | Manifold Firewall — `is_manifold_501` (ε_manifold=0.8) + degree-normalized G_ent (Ghost #22) | landed ✓ |
| EXP-503 | Spectral Manifold Feedback — `phi_fb_manifold` β_Z_eff=f(B_A,B_D,B_ent_spectral); bounded restoring force, maintenance-gated | landed ✓ |

Measured baselines (71-leaf seed octree): B_ent un-normalized median ≈ 0.678;
degree-normalized median ≈ 0.52; firewall ε_manifold = 0.8 (≈1.5× margin, mildly permissive).
EXP-503 spectral feedback is scaffolded (`spectral_ent_project`, `build_L_sheaf_503`,
observation-only): Fiedler modes [0.316, 0.808, 0.940], B_ent_spectral(k=3) ≈ 0.125.

Fork results: EXP-501 A 10/10 · B 5/5 — EXP-502 A 10/10 · B 5/5 — EXP-503 A 10/10 · B 5/5 (P_yz δ ≤ 8.9e-15).

EXP-503 wires the spectral scaffold into the Zeeman field: `β_Z_eff = f(B_A, B_D, B_ent_spectral)` with a bounded restoring term `Ω_ent_sp = B_ent_spectral/(1+B_ent_spectral) ∈ [0,1)`, gated to the maintenance phase so the EXP-409 discovery latch stays byte-identical (Ghost #25 — manifold-induced latch evasion). EXP-504 target: Stateful Seed for cross-scene tectonic-tear damping (Ghost #26 equilibrium stiffness).

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

### EXP-402 gate — COMPLETE

EXP-402 implemented and verified. See EXP-402 section below.
---

## EXP-402 — Ghost-Zeeman Homeostasis (Series 400 Exp 2)

**Status: open** | declaration_hash: `d933ad3ba860b601137cf7159b2485b2e86e1fc12b8939bce9bc1a08c3678407`

### Operator Phi_fb

Stateless operator inserted between Z-computation and Bτ (Zeeman weights).

```
Phi_fb: (S_A_prev, Z_A_prev, S_D_prev, params) → β_Z_eff  (scalar)

B_A = ‖S_A‖ / (‖Z_A‖ + ε)                  [precession ghost ratio]
B_D = ‖S_D‖ / (‖Z_A‖ + ε)                  [covariance ghost ratio; Z_A denom]
β_Z_eff = max(β_Z_min, β_Z_base · (1 + γ_A·B_A − γ_D·B_D))
```

Parameters (locked): `β_Z_base=2.0`, `γ_A=0.5`, `γ_D=0.5`, `β_Z_min=0.5`.

### Homeostatic balance

B_A ("desire") and B_D ("cost") form a push-pull pair:
- B_A > B_D → β_Z_eff > β_Z_base → tighter Zeeman → more focused partitioning → reduces B_A
- B_D > B_A → β_Z_eff < β_Z_base → looser Zeeman → more diffuse partitioning → reduces B_D

Equilibrium: B_A* = B_D* (equal ghost ratios). At γ_A = γ_D = 0.5:
engine "inhales" when scene is simple, "exhales" when covariance stress is high.

**Ghost #10 prevention:** `Z_D = stalk[12:18] = 0` in all partition children.
Using ε alone gives B_D = ‖S_D‖/ε → ∞ at t=1. Fix: B_D uses ‖Z_A‖ denominator.
B_D ∈ [0, 1) at seed depth; homeostasis arms after EMA warmup (S_A, S_D ≠ 0).

### Verified results

| Fork | Assertions | Result |
|------|-----------|--------|
| Fork A (`run_seed_exp402.py`) | 10/10 | **PASS** |
| Fork B (`run_p_invariance_exp402.py`) | 5/5 | **PASS** |

```
phi_fb(B_A active): β_Z_eff = 2.057879  (amplification ✓)
phi_fb(B_D active): β_Z_eff = 1.942121  (pullback ✓)
beta_Z_eff P_yz-invariant: delta = 0.00e+00  (Fork B ✓)
EXP-401 regression: 92 leaves at feedback-off ✓
```

### EXP-403 gate — COMPLETE

EXP-403 implemented and verified.

### Verified results

| Fork | Assertions | Result |
|------|-----------|--------|
| Fork A (`run_seed_exp403.py`) | 10/10 | **PASS** |
| Fork B (`run_p_invariance_exp403.py`) | 5/5 | **PASS** |

```
β_Z_eff trajectory (N=20): 2.000 → 5.303 → 7.139 → 6.813 → ... → 6.809 (converged)
B_A*=4.811  B_D*=0.0013  Ω_fb(∞)=2.405  (240% backreaction)
leaf_count: 92 (cold) → 113 (n=1) → 106 (n≥2, stable)
Ghost #11: np.array copy on S_A/S_D inheritance ✓
Ghost #12: n=0 cold start, n≥1 inherits terminal EMA ✓
Ghost #13: B_A>>B_D scene-structural; equilibrium=EMA channel stability ✓
Saturation gate: forced (S_D_init=[2]*6, γ_D=2.0) → sat_ratio=0.60 ✓
P_yz: max|β_Z_eff_fwd−mir|=2.66e-15 ✓
```

### EXP-404 gate — COMPLETE

EXP-404 implemented and verified.

---

## EXP-404 — Exponential Phi_fb (Series 400 Exp 4)

**Status: open** | declaration_hash: `e7447ec6a65022a25d426a8f0b796ef18292d6cf3f85047c2239b004d225e67c`

**Gate:** EXP-403 Fork A [10] forced sat_ratio=0.60 > 0.50

### Operator phi_fb_exp

```
β_Z_eff = max(β_Z_min_exp, β_Z_base · exp(γ_A·B_A − γ_D·B_D))
β_Z_min_exp = 0.1   (vs linear β_Z_min = 0.5)
```

Properties: always positive; fixed point β_Z_base at γ_A·B_A=γ_D·B_D; linearises to EXP-402 for |x|≪1.

### Saturation comparison (forced: γ_A=0, γ_D=2.0, S_D=[2]×6)

| Operator | sat_ratio | resolved? |
|---|---|---|
| EXP-402 linear | 0.60 | no (gate source) |
| EXP-404 exponential | 0.20 | **yes** ✓ |

### Ghost #14 — Exponential amplification

B_A*=4.81 (scene-structural) → `exp(0.5×4.81)=11.07 → β_Z_eff*=17.19` (vs EXP-402: 6.81).
Leaf count drops 106→71 (stronger Zeeman → tighter budget → fewer but more focused leaves).
Ω_fb=760% backreaction (vs 240% linear).

### Ghost #15 — Transient overshoot

β_Z_eff trajectory: [2.00, 10.43, 12.64, 15.13, **22.88**, 17.38, 17.19, ...]
Peak at n=4 (33% overshoot before settling). EXP-405 gate: if overshoot_ratio > 1.5.

### Verified results

| Fork | Assertions | Result |
|------|-----------|--------|
| Fork A (`run_seed_exp404.py`) | 10/10 | **PASS** |
| Fork B (`run_p_invariance_exp404.py`) | 5/5 | **PASS** |

```
phi_fb_exp neutral=2.000; floor=0.100; linearisation err=6.26e-6 ✓
sat_ratio_404=0.20 < sat_ratio_402=0.60 (gate resolved ✓)
bze*=17.19  leaf*=71  Omega_fb=7.60 (760%)
overshoot_ratio=1.33 (EXP-405 gate inactive)
P_yz: max|bze_fwd−mir|=2.13e-14 ✓
```

### EXP-405 gate

Trigger: `overshoot_ratio = max(β_Z_eff) / β_Z_eff* > 1.5` (currently 1.33, inactive).
Options: damped exponential, adaptive γ schedule, or second-order EMA smoothing of β_Z_eff.

---

## EXP-405 — Adaptive Gamma Warmup Schedule

**Gate:** EXP-404 Ghost #15 (proactive; overshoot_ratio=1.33, threshold=1.5).  
**Declaration hash:** `6e498f656aeb0fce5b7bfb588642ebef935e6df154b3d5195f907213a07ca889`  
**Files:** `studies/exp405_adaptive_gamma/`  
**Author:** Daniel J. Dillberg — bigdilly95@gmail.com

### Operator: phi_fb_adaptive

```
ramp(n) = 1 − exp(−n / τ)        (τ=5; ramp(0)=0)
γ_eff_A = γ_∞_A · ramp(n)
γ_eff_D = γ_∞_D · ramp(n)
β_Z_eff = max(β_Z_min, β_Z_base · exp(γ_eff_A · B_A − γ_eff_D · B_D))
```

Parameters: `γ_∞_A=γ_∞_D=0.5`, `τ=5.0`, `β_Z_min=0.1`.  
At n=0: γ_eff=0 → cold start (no feedback).  
As n→∞: γ_eff→γ_∞ → reduces to `phi_fb_exp` (EXP-404).

### Transient comparison (N=20)

```
bze_404: [2.00, 10.43, 12.64, 15.13, 22.88, 17.38, 17.19, ...]  overshoot_ratio=1.33
bze_405: [2.00,  2.70,  4.77,  6.87,  7.53,  9.15,  5.59, ...]  overshoot_ratio=1.00
```

Overshoot eliminated (spike suppressed 3.9×). However, slow ramp induces Ghost #16.

### Ghost #16 — 2-Period Leaf Count Oscillation

Adaptive ramp traverses bistable region (β_Z_eff≈14–20) slowly. EMA memory (α=0.1, ≈10 steps) couples to ramp timescale (τ=5) → parametric 2-cycle.

```
lc_405 tail (n≥11): oscillates {71, 78}   (2-cycle)
lc_404 tail (n≥5):  stable     {71}       (single attractor)
```

bze_405 at n=20: 21.75 (not converged; EXP-404 settled at 17.19 by n=7).  
Ω_fb(405)[n=20] = |21.75−2.0|/2.0 = 988% (transient; exceeds settled EXP-404 value of 760%).

### Saturation comparison

| Operator | sat_ratio | Ghost | Status |
|---|---|---|---|
| EXP-402 linear | 0.60 | — | gate source |
| EXP-404 exp | 0.20 | #15 overshoot | resolved ✓ |
| EXP-405 adaptive | 0.00 | #16 2-cycle | EXP-406 gate |

### Verified results

| Fork | Assertions | Result |
|------|-----------|--------|
| Fork A (`run_seed_exp405.py`) | 10/10 | **PASS** |
| Fork B (`run_p_invariance_exp405.py`) | 5/5 | **PASS** |

```
phi_fb_adaptive cold (n=0):  β_Z_eff=2.000 = β_Z_base ✓
phi_fb_adaptive n=1:         bze_405=2.018 < bze_404=2.103 (γ_eff < γ_inf) ✓
phi_fb_adaptive n→∞:         converges to phi_fb_exp (diff < 0.1) ✓
overshoot_ratio_405=1.0000 < 1.33 ✓  saturation_ratio=0.0000 ✓
Ghost #16: lc 2-cycle {71,78}; bze range=16.15 at N=20 (not converged)
P_yz: max|bze_fwd−mir|=1.78e-14 ✓
```

### EXP-406 gate

**Trigger:** Ghost #16 (2-cycle instability; β_Z_eff not converged at N=20).  
Options:
- A: EMA smoothing of β_Z_eff (second-order damping breaks 2-cycle)
- B: Larger τ_warmup (avoid bistable crossing during ramp)
- C: Non-monotone ramp (fast to 0.3·γ_∞, plateau, then slower rise to γ_∞)

---

## EXP-406 — EMA-Smoothed β_Z_eff (Inertial Attention Field)

**Gate:** EXP-405 Ghost #16 (2-period lc oscillation; parametric resonance τ=5 × EMA memory ~10 steps).  
**Declaration hash:** `84255beb1f11d0182a052e6d31e9c5aaa4e87c37d3d1c0a6494b56fd4ad891cf`  
**Files:** `studies/exp406_ema_bze/`  
**Author:** Daniel J. Dillberg — bigdilly95@gmail.com

### Operator: phi_fb_ema

```
β_raw      = max(β_Z_min, β_Z_base · exp(γ_eff_A·B_A − γ_eff_D·B_D))   [phi_fb_adaptive]
β_Z_eff    = max(β_Z_min, α_bze · bze_ema_prev + (1−α_bze) · β_raw)     [EMA inertia]
```

`bze_ema_prev`: primary-scalar, caller-tracked (NOT in MuState dual state). Cold start = β_Z_base.  
Parameters: `α_bze=0.5`, `γ_∞=0.5`, `τ=5.0`, `β_Z_min=0.1`.

2-cycle damping: steady-state amplitude `|p−q| = |f₁−f₂|·(1−α)/(1+α) = |f₁−f₂|/3` at α=0.5.

### Trajectory comparison (N=20)

```
bze_404: [2.00, 10.43, 22.88↑, 17.19, ...]  overshoot=1.33  settled n=7  (single attractor)
bze_405: [2.00,  2.70,  4.77, ..., 21.75]   overshoot=1.00  2-cycle {71,78} lc
bze_406: [2.00,  2.35,  3.21, ..., 17.13]   overshoot=1.033 Ghost #17 lag  (converging)
```

### Ghost #17 — EMA Lag-Overshoot

EMA momentum carries β_Z_eff past the β_raw peak during declining transient.  
`overshoot_ratio_406=1.033` (3.3%); `Ω_inertia_max=0.281` (28% peak lag).  
Bounded well below EXP-404's 1.33. Decays as system converges.

### Dev note: alpha_leak=0.0 Ghost

Passing `alpha_leak=0.0` explicitly to `apply_gamma_401_recursive` suppresses S_A accumulation (boolean branch `if alpha_leak:` is False for 0.0). EXP-406 workaround: omit kwarg. Recommend audit of all EXP-4xx callers.

### Verified results

| Fork | Assertions | Result |
|------|-----------|--------|
| Fork A (`run_seed_exp406.py`) | 10/10 | **PASS** |
| Fork B (`run_p_invariance_exp406.py`) | 5/5 | **PASS** |

```
alpha_bze=0.5  tau_warmup=5.0
tail_range_406=9.173 < tail_range_405=14.785 (Ghost #16 damped 38%) ✓
last5_range_406=4.217 < last5_range_405=5.830 ✓
bze_406[-1]=17.13 ≈ bze_404*=17.19 (equilibrium near-recovered) ✓
saturation_ratio=0.0000  overshoot=1.033  Omega_inertia_max=0.281
P_yz: max|bze_fwd−mir|=7.11e-15 ✓
```

### EXP-407 gate

**Trigger:** Ghost #17 (lag-overshoot 1.033); tail variability at N=20.  
Options: increase α_bze (stronger inertia), adaptive α_bze schedule, or fix alpha_leak Ghost.

---

## EXP-407 — Adaptive α_bze Schedule (Synchronized Dual Warmup)

**Declaration hash:** `2dc29bcfbb1d7b02f65549f4d4750ac9b7af5603d4a726a3fa53347e67773f87`  
**Gate source:** EXP-406 Ghost #17 — EMA lag-overshoot (fixed α=0.5 provides equal damping at all stages)

### Operator: phi_fb_adaptive_ema

EXP-407 extends `phi_fb_ema` (EXP-406) with a time-varying inertia schedule synchronized to the γ ramp.

```
α_eff(n) = α_min + (α_max − α_min) · exp(−n / τ_α)
β_Z_eff  = max(β_Z_min, α_eff · bze_ema_prev + (1−α_eff) · β_raw)
```

Parameters: `α_max=0.9`, `α_min=0.7`, `τ_α=5.0` (synchronized with `τ_warmup=5.0`).

**Synchronized dual warmup:** γ_eff ramps UP as α_eff ramps DOWN — both on timescale τ=5.

### Critical Damping Threshold (α_crit = 2/3)

For the EMA-filtered 2-cycle with raw amplitude `|f₁−f₂|≈5`:

```
2-cycle amplitude = (1−α)/(1+α) · |f₁−f₂|
Suppressed when: (1−α)/(1+α) < 1/|f₁−f₂| ≈ 0.2   →   α > 2/3
```

`α_min=0.7 > α_crit=0.667` ensures persistent 2-cycle suppression at all n.

### Ghost #18 — Alpha Subcritical Failure

EXP-407 v1 used `α_min=0.2`. At n≥15, α_eff≈0.22 — below α_crit. Ghost #16 2-cycle was reintroduced with tail_range=13.07 (WORSE than EXP-406's 9.17). Ghost #16 is a persistent equilibrium feature; inertia must be sustained above α_crit at all n. Resolution: `α_min=0.7`.

```
|p−q| / |f₁−f₂| = (1−α)/(1+α):
  α=0.20 → 0.667  (above lc-switching threshold — 2-cycle active)
  α=0.50 → 0.333  (EXP-406 floor — marginal)
  α=0.70 → 0.176  (EXP-407 floor — suppressed)
```

### Trajectory (N=20 sequential, α_min=0.7)

```
bze_407: [2.0, 2.1, 2.32, 2.89, 4.08, 5.96, 7.43, 8.64, 8.08, 9.87,
          9.13, 8.56, 11.13, 11.19, 11.24, 10.67, 10.98, 11.27, 10.78, 11.18]
bze_406: [2.0, 2.35, 3.21, ..., 17.13]   fixed α=0.5
alpha:   [0.9, 0.864, 0.834, ..., 0.704]  (decays to α_min=0.7)
tail_range_407=2.71  vs  tail_range_406=9.17  (70% reduction) ✓
last5_range_407=0.59 vs  last5_range_406=4.22 (7× tighter) ✓
overshoot_407=1.008                            (vs 404: 1.33) ✓
```

Note: bze_407[-1]=11.18 < bze_406[-1]=17.13 — convergence rate reduced by high inertia floor. EXP-408 gate triggered.

### Verified results

| Fork | Assertions | Result |
|------|-----------|--------|
| Fork A (`run_seed_exp407.py`) | 10/10 | **PASS** |
| Fork B (`run_p_invariance_exp407.py`) | 5/5 | **PASS** |

```
α_max=0.9  α_min=0.7  τ_α=5.0  (α_crit=0.667)
tail_range_407=2.7114 < tail_range_406=9.1732 ✓
last5_range_407=0.5939 < last5_range_406=4.2170 ✓
overshoot_407=1.0083 < overshoot_404=1.33 ✓
saturation_ratio=0.0000  lc_tail={64,71,106}
P_yz: max|bze_fwd−mir|=7.11e-15 ✓
```

### EXP-408 gate

**Trigger (proactive):** bze_407[-1]=11.18 < bze_406[-1]=17.13 — high α_min floor reduces convergence rate. Convergence-damping Pareto frontier not yet explored.  
Options: (A) increase τ_α (slower decay, higher early damping), (B) decouple τ_warmup ≠ τ_α, (C) Pareto sweep (tail_range, convergence_speed) vs α_min ∈ [0.667, 0.95].

---

## EXP-408 — Ascending α_bze Schedule (Bootstrap to Maintenance)

**Declaration hash:** `d1945e6736a284a33cf648ac0d7d06491e0bea704bd6fa69ca7beac277562055`  
**Gate source:** EXP-407: bze_407[-1]=11.18 < bze_406[-1]=17.13 (convergence lag from α_min=0.7 floor)

### Operator: phi_fb_ascending_ema

Inverts EXP-407's direction: α ramps UP from loose to tight.

```
α_eff(n) = α_max − (α_max − α_min) · exp(−n / τ_α)
```

Parameters: `α_min=0.2`, `α_max=0.9`, `τ_α=2.0` (decoupled from `τ_warmup=5.0`).

**Timescale decoupling:** τ_α=2.0 < τ_warmup=5.0 — α locks above α_crit=0.667 at n≈2.2, before the bistable β_raw range activates at n≈4 (safety margin=1.8 steps).

### Ghost #19 — Attraktorwahl (Attractor Selection)

The ascending schedule's heavy maintenance inertia (α→0.9 by n=7) locks the system into whatever basin it occupies at the bistable transition. At n=9, lc switches to 64; α=0.892 → only 10% of raw per step. System converges stably to lc=64 equilibrium (bze→8) and cannot re-escape to lc=71 basin within N=20.

```
bze_408: monotone climb n=0-9; decaying from 8.89 to 8.62 (lc=64 basin)
lc_408_tail=[64]   (single-attractor — but WRONG basin vs EXP-406/407)
tail_range_408=0.93   (tightest of all experiments)
bze_408[-1]=8.62  vs  bze_407[-1]=11.18  vs  bze_406[-1]=17.13
```

Bootstrap DID work (bze_408 led bze_407 for n=1-4, advantage up to Δ=+1.20 at n=3), but Attraktorwahl at n=9 overrode the early gain. The α schedule controls not only convergence rate but WHICH BASIN is captured.

**Contrast:**
- Ghost #18 (EXP-407 v1): α below α_crit at equilibrium → 2-cycle within the targeted basin  
- Ghost #19 (EXP-408): α above α_crit, but maintenance lock prevents inter-basin transitions

### Phi_fb Evolution Table

| EXP | α schedule | tail_range | bze[-1] | lc_tail | Ghost |
|-----|-----------|-----------|---------|---------|-------|
| 404 | fixed γ | — | 17.19 | {71} | #15 overshoot=1.33 |
| 405 | γ ramp↑ | 14.79 | 21.75 | {71,78} | #16 2-cycle |
| 406 | fixed α=0.5 | 9.17 | 17.13 | {71,78} | #17 lag |
| 407 | α ramp↓ (min=0.7) | 2.71 | 11.18 | {64,71,106} | #18 subcritical |
| **408** | **α ramp↑ (max=0.9)** | **0.93** | **8.62** | **{64}** | **#19 Attraktorwahl** |

### Verified results

| Fork | Assertions | Result |
|------|-----------|--------|
| Fork A (`run_seed_exp408.py`) | 10/10 | **PASS** |
| Fork B (`run_p_invariance_exp408.py`) | 5/5 | **PASS** |

```
α_min=0.2  α_max=0.9  τ_α=2.0  n_cross(α_crit)=2.20  α(n=4)=0.805
tail_range_408=0.931 < tail_range_406=9.173 ✓  (2-cycle ratio=5.3% at α_max)
last5_408=0.368 < last5_407=0.594 ✓
overshoot_408=1.099 < overshoot_404=1.33 ✓
Ω_inertia_max=0.469
P_yz: max|bze_fwd−mir|=1.78e-15 ✓
```

### EXP-409 gate

**Trigger (proactive):** Ghost #19. Neither descending (stable but sluggish) nor ascending (basin-locked) resolves convergence + basin-selection jointly.  
Options: (A) hysteresis α — hold low until bze crosses basin threshold; (B) ascending to α_max=0.7 only (EXP-407 floor, not 0.9); (C) Pareto sweep (α_min, α_max, τ_α) vs (tail_range, bze[-1]); (D) two-timescale split with lc-stability signal.
