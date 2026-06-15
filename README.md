# Reality Engine — Series 300 (Dentatus)

Generative reality engine implementing a cellular sheaf state machine over a claim DAG.
State evolution is governed by a fixed operator pipeline with immutable hash-indexed states,
dual ghost channels, and preregistered validity predicates.

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

### Stalk schema — d=12

```
F(v) ∈ ℝ¹²  =  [Sector A (0-3) | Sector B (4-7) | Sector C (8-11)]

Sector A: [mass, r, g, b]          — photometric
Sector B: [x, y, z, w]             — affine position + weight
Sector C: [nx, ny, nz, kappa]      — centroid-outward unit normal + curvature
```

Restriction map `F` is block-diagonal 12×12; no cross-sector coupling.

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
| EXP-315 | Dual G_inject_A; primary arccos path active; τ_opt varies with mass/kappa | `e16dd1a01735bc1d` | **closed** |

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

## EXP-313 — The Zeeman K_bound

**Goal:** introduce anisotropic budget allocation via Zeeman-analogue field alignment, with exact P_yz covariance.

**Zeeman weighting:**

```
B_hat = B / ‖B‖
centroids = (bbox_lo + bbox_hi) / 2  for each child
logits_i  = beta_Z * (centroid_i · B_hat)
w_i       = softmax(logits)_i          (sum = 1)
K_child_i = K_budget * w_i * exp(-LAMBDA_DECAY)
```

**P_yz covariance proof:**

```
B transforms as a polar vector: B_mir = P_yz(B_fwd) = (-B_x, B_y, B_z)
centroid_mir[i^4] = P_yz(centroid_fwd[i])   (octant permutation)

centroid_mir[i^4] · B_mir
= P_yz(centroid_fwd[i]) · P_yz(B_fwd)
= centroid_fwd[i] · B_fwd         (dot product O(3)-invariant)
=> w_fwd[i] = w_mir[i XOR 4]  =>  K_fwd[i] = K_mir[i XOR 4]   QED
```

**Budget formula (no N factor):** `K_child_i = K_budget * w_i * exp(-LAMBDA_DECAY)`. With `N * w_max * exp(-LAMBDA_DECAY) < 1` required for convergence; enforced by `K_budget_root = 2048 = N * 256`.

**Results:**

```
K_fwd[i] == K_mir[i XOR 4]  for all i  (max delta = 0.00e+00)
fwd_leaves == mir_leaves == 92
cost_fwd == cost_mir  (delta < 1e-8)
norm(S_C): 0.03915037 = 0.03915037
norm(S_A): 1.49806877 = 1.49806877
K_ratio (max/min) = 4.7349  (Zeeman splitting active)
```

Fork A (`run_seed_exp313.py`): 8/8 PASS
Fork B (`run_p_invariance_exp313.py`): 9/9 PASS

---

## EXP-314 — The Hyperfine Ghost

**Goal:** measure inter-channel precession angle Ω_AC between dual ghost channels S_A and S_C; derive architecture-driven lag τ_opt for transfer entropy without grid search.

**Coupling observable:**

```
v_A     = J_AC @ S_A[0:4]            (J_AC = 4×4 identity; primary path)
Ω_AC    = arccos(clip(v_A · S_C / (‖v_A‖·‖S_C‖ + ε), −1, 1))
τ_opt   = max(1, round(Ω_AC / π · W_max))
```

**Fallback (numeric degeneracy guard):** Under the current G_inject architecture, `S_A[0:4] = 0` in exact arithmetic (`G_inject_A` targets dim 7; lossless partition gives `G_A = 0`). When `‖v_A‖ < 1e-6`, the fallback activates:

```
Ω_AC    = 2 · arctan2(‖S_C‖, ‖S_A‖)   ∈ (0, π)
τ_opt   = max(1, round(Ω_AC / π · W_max))   [formula unchanged]
```

P_yz-invariant: ‖S_A‖ and ‖S_C‖ proven invariant by EXP-313. The primary arccos path activates automatically if `G_inject_A` is re-targeted to dims in `S_A[0:4]` in future experiments.

**Ghost history extension:** `ghost_history` entries are mixed 2-tuples (from `apply_gamma_312` base layer) and 4-tuples from EXP-314:

```
(‖S_A‖, ‖S_C‖, Ω_AC, τ_opt)   ← EXP-314 entries (4-tuple)
(‖S_A‖, ‖S_C‖)                 ← EXP-312 base entries (2-tuple)
```

**Results:**

```
Ω_AC_fwd = Ω_AC_mir = 0.01727 rad   (delta = 2.00e-14)
τ_opt = 1  (‖S_A‖ >> ‖S_C‖; short-lag regime)
fwd_leaves == mir_leaves == 92
Full trace: max_omega_delta = 6.18e-14  tau_mismatches = 0/13
```

Fork A (`run_seed_exp314.py`): 8/8 PASS
Fork B (`run_p_invariance_exp314.py`): 9/9 PASS

---

## Coordinate conventions

- **Centroid-outward normal**: `n_child = normalize(centroid_child − centroid_parent)` —
  purely geometric, closes E-305-002 (P_yz exact).
- **P_yz mirror**: `x → −x` (polar dim 4), `nx → −nx` (axial dim 8), bbox x-axis reflected.
  `kappa_integral` is P_yz-invariant: extents `|hi[i]−lo[i]|` are preserved under x-reflection.
- **Bbox hash payload (EXP-308–311)**: `SHA256(lo‖hi‖depth‖index)[:16]` — absolute coords,
  P_yz-variant by design.
- **Bbox hash payload (EXP-312+)**: `SHA256(ex‖ey‖ez‖depth‖index)[:16]` — extents only,
  P_yz-invariant.

---

## Running the tests

```bash
# Dependencies
pip install numpy scipy

# EXP-315 (current)
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

# EXP-311
python run_seed_exp311.py
python run_p_invariance_exp311.py

# EXP-308 (regression)
python run_seed_exp308.py
python run_p_invariance_exp308.py
```

All prior study runners (`exp306`, `exp307`, `exp309`) remain executable as regression checks.

---

## Dev notes

### G_t = 0 structural identity

For all lossless centroid-outward octree partitions, `Z_t ∈ span(W_t)` by construction, so
`G_t = Z_t − Π_{W_t}(Z_t) = 0` exactly. This is a mathematical identity, not a bug.
`S_A` and `S_C` accumulate non-zero signal only via the `G_inject` auxiliary channel (EXP-311+).

### G_inject auxiliary residual (EXP-311)

Per-partition auxiliary signal injected into the dual EMA, orthogonal to `G_t`:

```
G_inject_C[3] = alpha_leak * (‖Z_before[0:4]‖ / mass_ref)
G_inject_A[7] = alpha_leak * beta_CA * (Z_before[11] / kappa_ref)
S_C_{t+1} = alpha_ema * S_C_t + (1−alpha_ema) * G_inject_C
S_A_{t+1} = alpha_ema * S_A_t + (1−alpha_ema) * G_inject_A
```

`G_inject` feeds only the dual EMA; it does not modify `Z_t` or any claim stalk.
Gravitational backreaction analogy: `G_inject` is the radiation reaction force on the ghost sector —
draining energy from the mass-curvature coupling asymmetry into the EMA accumulator without
perturbing the geodesic (primary Z trajectory).

### P_yz octant permutation (ghost #4 — EXP-312)

Under P_yz (x→−x), the octree child index permutation is `i ↔ i XOR 4` (the x-bit, weight 4,
flips). Index-based mass assignment breaks focal point covariance across this permutation.
Uniform split is the minimal P_yz-invariant Sector A distribution. Conservation holds:
`Σ stalk_A_i = N·(stalk_A/N) = stalk_A`.

### Zeeman structural anisotropy (ghost #5 — EXP-313)

Budget allocation `K_child_i = K_budget * w_i * exp(-LAMBDA_DECAY)` is spatially anisotropic —
children aligned with `B` receive more budget than anti-aligned children (`K_ratio = 4.7349` for
`B=[1,0.5,0.3]`, `beta_Z=2.0`). The tree structure is directionally biased, but the bias is
P_yz-covariant: `K_fwd[i] = K_mir[i XOR 4]` exactly (max delta = 0, proven analytically and
verified numerically). Child processing is sorted by descending Zeeman weight — this ensures
`Z_before[11]` (kappa aggregate) is identical at each corresponding step in fwd/mir, keeping
`G_inject_A` accumulation P_yz-invariant across the full recursive traversal.

### Hyperfine inter-channel coupling (ghost #6 — EXP-314/315)

`Ω_AC` is the first INTER-channel observable. `B_A`, `B_C` measured each channel independently;
`Ω_AC` measures the precession angle between S_A and S_C in the dual space.

**EXP-314 (degenerate):** with `G_inject_A[7]` as the sole injection channel, `S_A[0:4] = 0`
in exact arithmetic (lossless partition → `G_A = 0`). The primary arccos path degraded to 0/0
resolved by floating-point noise. A numeric fallback (`Ω_AC = 2·arctan2(‖S_C‖, ‖S_A‖)`) provided
P_yz-invariant τ_opt = 1 but with no variation.

**EXP-315 (resolved):** dual injection `G_inject_A[0] = f(mass_norm)` and `G_inject_A[3] = f(kappa)`
gives `S_A[0:4] ≈ [S_A0, 0, 0, S_A3]` with `‖v_A‖ ~ 6.17 >> 1e-6`. Primary arccos path active.
`Ω_AC = arctan(mass_norm / (beta_CA · kappa))` — measures mass/curvature balance at each tree depth.
`τ_opt ∈ {1, 3}` across partition steps; fully P_yz-invariant (trace delta < 2.5e-12).

The `g_inject_fn` parameter in `apply_gamma_312` / `apply_gamma_313` / `apply_gamma_314` /
`apply_gamma_314_recursive` passes through the injection override. Default (`g_inject_fn=None`)
preserves all EXP-311/312/313/314 behavior exactly (backward-compatible).

### LOD_RELAXED validity class propagation

`validity_class` is set on `MuState` (not on individual `Claim` objects). The recursive guard
checks `getattr(mu, "validity_class", "FULL_VALID")`. A `LOD_RELAXED` input blocks all further
expansion; `FULL_VALID` recurses normally.

### Focal point is not hashed

`focal_point` is a dynamic attribute on `MuState`, excluded from `H_t`. It is a mutable observer
parameter. Changing `focal_point` between calls produces different LOD values without invalidating
the hash chain.

### EPS_REL relative floor (EXP-308 rev)

`kappa_integral` uses `eps = max(lx, ly, lz) * 1e-9` as per-axis regularization floor
(scale-invariant under uniform bbox rescaling). For normal extents ≥ 1e-3 identical to the
prior absolute `1e-6` floor.

### NTFS git workaround

`.git/config` may be unreadable from the Linux sandbox between sessions on Windows NTFS.
Fix: open Git Bash in the repo root and run the `commit_exp312.ps1` script (or copy the commands
manually — see **Git Bash instructions** below).

### Forbidden operations

`ghost_direct_control`, `stalk_collapse`, `retroactive_confluence_cert`,
`budget_retroactive_adjustment`, `validity_predicate_shift`, `post_hoc_rewrite_rule_addition`.
Post-execution rule addition is forbidden. All predicates must be declared and locked in
`SEED_DECLARATION_*.json` before any operator is implemented.

---

## Series-300 closure / EXP-401 gate

Series-300 is **closed** as of EXP-315. All prerequisites for EXP-401 satisfied:

| Requirement | Status |
|-------------|--------|
| P_yz multi-step invariance (fwd=mir=92, delta=0) | EXP-312 ✓ |
| Zeeman K_bound P_yz-covariant | EXP-313 ✓ |
| Ω_AC observable + τ_opt derived | EXP-314 ✓ |
| Primary arccos path active; τ_opt varies with depth | EXP-315 ✓ |

EXP-401 prerequisites (anisotropic splatting / differentiable volume clusters):

- Stalk schema extension to d=15 (add 3 Gaussian covariance dims) or d=18 (full 3×3 covariance)
- New validity predicate: `is_valid_covariance_401` — positive-definite Σ on new dims
- `apply_gamma_401` must extend the block-diagonal F to the new covariance block
- P_yz must extend: covariance Σ transforms as `Σ' = R·Σ·Rᵀ` where R=diag(-1,1,1)
- Per-node `τ_opt` from EXP-315 drives anisotropic covariance alignment (no grid search)
- **Optional EXP-316:** inject `G_inject_A[1] = f(Z_before[5])` (y-norm, P_yz-invariant) → full
  3-component `v_A` → 4D angular resolution of ghost precession beyond the planar EXP-315 angle
