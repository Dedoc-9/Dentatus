# ENGINE_AXIOMS — EXP-401: Anisotropic Gaussian Covariance (Series 400, Exp 1)
**Protocol version:** exp401-v1  
**Inherits:** exp316-v1  
**Declaration hash:** ff1fb75eb819cf1e79e778886ebfdd4291f48e3d2cc7d1dbd0630a603a124323

---

## A. Motivation: Full Covariance Geometry

EXP-316 established 3-component ghost precession `v_A = [S_A0, S_A1, 0, S_A3]` with
`τ_opt ∈ {1,2,3}`. The Zeeman field `B` defines a preferred spatial direction, but
the partition tree has no encoding of the correlation geometry along that direction.

EXP-401 extends the stalk from d=12 to d=18, adding Sector D:

```
stalk[12:18] = [log_l11, log_l22, log_l33, l21, l31, l32]
```

This encodes a 3×3 log-Cholesky covariance matrix `Σ = L·Lᵀ` where:

```
L = [[exp(log_l11),     0,          0      ],
     [l21,          exp(log_l22),   0      ],
     [l31,          l32,        exp(log_l33)]]
```

Positive-definiteness is guaranteed by log-Cholesky: `L[i,i] = exp(log_lii) > 0` always.
`S_D` (dual EMA) accumulates ghost injections `G_inject_D` aligned to `B̂ ⊗ B̂` modulated
by retarded `τ_opt` from prior `ghost_history`.

**Architectural justification for d=18 over d=15 (diagonal-only):**
Diagonal covariance (d=15) is an architectural dead end. Zeeman-weighted partitions
create directional pressures that don't respect axis-aligned boundaries. Off-diagonal
terms `l21`, `l31`, `l32` encode the tilt of the covariance ellipsoid relative to
the partition grid. Without them, the Ghost cannot track correlation between x-variance
and y-variance under B-field rotation.

---

## B. Stalk Extension: Sector D

| Index | Name      | Encoding                        |
|-------|-----------|----------------------------------|
| 12    | log_l11   | log Cholesky diagonal [0,0]     |
| 13    | log_l22   | log Cholesky diagonal [1,1]     |
| 14    | log_l33   | log Cholesky diagonal [2,2]     |
| 15    | l21       | lower off-diagonal [1,0] (xy)   |
| 16    | l31       | lower off-diagonal [2,0] (xz)   |
| 17    | l32       | lower off-diagonal [2,1] (yz)   |

**Ghost EMA (dual space, NOT partition-inherited):**

```
G_inject_D[3] = α_D · τ_norm · B̂[0] · B̂[1]   (l21: xy coupling)
G_inject_D[4] = α_D · τ_norm · B̂[0] · B̂[2]   (l31: xz coupling)
G_inject_D[5] = α_D · τ_norm · B̂[1] · B̂[2]   (l32: yz coupling)

τ_norm = τ_opt / W_max  (retarded: from prior ghost_history entry)

S_D_{t+1} = α · S_D_t + (1−α) · G_inject_D
```

Parameters (locked): `α_D = 0.05`, `α_EMA = 0.85`, `W_max = 8`.

**Child stalk initialization:** Sector D zeros in all partition children.
`apply_gamma_312` initializes child stalks with `np.zeros(d)` — Sector D is NOT
partitioned (it is not a spatially-local quantity; it lives in `S_D` only).

**Consistency predicate:** `F[12:18, :] = 0` in restriction map; `child_stalk[12:18] = 0`.
`is_valid` check: `F @ parent_stalk[12:18] = 0 = child_stalk[12:18]` ✓.

---

## C. P_yz Covariance Proof

Under `P_yz` (x → −x): `B̂[0] → −B̂[0]`, `B̂[1]` and `B̂[2]` unchanged.

```
G_inject_D[3] ∝ B̂[0]·B̂[1] → −(B̂[0]·B̂[1])  => S_D[3]_mir = −S_D[3]_fwd  (l21 anti-sym)
G_inject_D[4] ∝ B̂[0]·B̂[2] → −(B̂[0]·B̂[2])  => S_D[4]_mir = −S_D[4]_fwd  (l31 anti-sym)
G_inject_D[5] ∝ B̂[1]·B̂[2] → unchanged        => S_D[5]_mir =  S_D[5]_fwd  (l32 symmetric)
```

Let `R = diag(−1, 1, 1)` be the P_yz reflection on ℝ³. Then:

```
Σ_mir = R · Σ_fwd · Rᵀ
```

Proof: L_mir has negated off-diagonals in x-rows/columns:
- `l21_mir = −l21_fwd`, `l31_mir = −l31_fwd`, `l32_mir = l32_fwd`
- `L_mir = R · L_fwd` (row sign flip on row 0 = x-row)
- `Σ_mir = L_mir · L_mirᵀ = (R·L_fwd)·(R·L_fwd)ᵀ = R·L_fwd·L_fwdᵀ·Rᵀ = R·Σ_fwd·Rᵀ` ✓

**This is NOT invariance — it is tensor covariance.** The covariance ellipsoid reflects
correctly under spatial reflection. `‖S_D‖` is P_yz-invariant (norm is invariant under
sign flip of components), so `B_D(t) = ‖S_D‖/(‖Z_D‖+ε)` is P_yz-invariant.

**Verified (Fork B):**
- `S_D[3]_fwd = 0.00034981`, `S_D[3]_mir = −0.00034981` (sum = 0.00e+00)
- `S_D[4]_fwd = 0.00020989`, `S_D[4]_mir = −0.00020989` (sum = 0.00e+00)
- `S_D[5]_fwd = S_D[5]_mir = 0.00010494` (delta = 0.00e+00)
- `max|Σ_mir − R·Σ_fwd·Rᵀ| = 0.00e+00`

---

## D. Verified Results (Fork A)

**Seed:** d=18, B=[1.0, 0.5, 0.3], K_budget=2048, 92 leaves.

| Observable | Value |
|------------|-------|
| leaves | 92 |
| `‖v_A‖` | 6.606456 (EXP-316 inherited) |
| `τ_opt` range | {1, 2, 3} |
| `‖S_D‖` | 0.00042123 |
| `B_D = ‖S_D‖/(‖Z_D‖+ε)` | 1.0000 |
| Σ diagonal | [1.0, 1.0, 1.0] (near-identity at seed depth) |
| Σ off-diagonal s12 | 0.000350 (l21 active) |
| Σ off-diagonal s13 | 0.000210 (l31 active) |
| Σ off-diagonal s23 | 0.000105 (l32 active) |
| min eigval(Σ) | 0.999632 (PD ✓) |

**G_inject_D modulation by τ_opt:**
```
τ_opt=1: G_D[3]=0.002332  G_D[4]=0.001399  G_D[5]=0.000700  (τ_norm=0.125)
τ_opt=2: G_D[3]=0.004664  G_D[4]=0.002799  G_D[5]=0.001399  (τ_norm=0.250)
τ_opt=3: G_D[3]=0.006996  G_D[4]=0.004198  G_D[5]=0.002099  (τ_norm=0.375)
```

---

## E. Operator Pipeline Extension

```
apply_gamma_401_recursive(mu, claim_id, partition_key, beta, budget, spent, K_budget,
                          depth, focal_point, B, beta_Z, J_AC, W_max, thresholds,
                          alpha_leak, beta_CA, mass_ref, kappa_ref, y_ref, alpha_D)
```

**Step 1:** Run `apply_gamma_316_recursive` → `mu_next` (S_A, S_C, ghost_history updated).

**Step 2:** Extract retarded `τ_opt` from last 4-tuple in `ghost_history`.

**Step 3:** Compute `G_inject_D` via `_g_inject_401(... B=B, tau_opt=τ_opt_final ...)`.

**Step 4:** EMA update: `S_D_new = α·S_D_init + (1−α)·G_D`.

**Step 5:** `mu_next._replace_S_D(S_D_new)` → reseals hash with S_D included.

**Hash:** `Hₜ = HASH(μₜ ⊕ Zₜ ⊕ Sₜ ⊕ Wₜ ⊕ protocol_version)` where `Sₜ` now includes
`[S_A ‖ S_C ‖ S_D]`.

---

## F. Infrastructure Changes (EXP-401 Ghost Notes)

**Ghost #7 — np.empty(d) uninitialized Sector D:**
`apply_gamma_312` used `np.empty(d)` for child stalks. With d=18, positions [12:18]
contained garbage. `is_valid` consistency check (`‖F@parent − child‖ < TOL`) failed
because `F[12:18,:] = 0` but `child[12:18] ≠ 0`. Fix: `np.zeros(d)`. Safe for d=12
(no-op). Sector D is NOT partition-inherited — it is a dual EMA quantity in S_D only.

**Ghost #8 — is_valid_block_diagonal_306 skipped 18×18:**
The function skipped F matrices not matching 11×11 or 12×12. Extended to check 18×18:
ABC cross-blocks + Sector D cross-terms `F[12:18, 0:12]` and `F[0:12, 12:18]` must
be zero (satisfied by np.zeros construction).

**Ghost #9 — stale .pyc after operators.py/validity.py edits:**
NTFS Edit tool truncated operators.py at `mu_next._re`. Restored via Python append
script finding the truncation marker and rewriting the tail. Forced recompile via
`py_compile.compile()`.

---

## G. Dual Arithmetic Separation

```
Primary space:   Z dynamics under Lτ/Bτ/Rτ (d=18 stalk, partitioned spatially)
Dual space A/C:  S_A[0,1,3], S_C[3] EMA + Ω_AC, τ_opt  (EXP-314/315/316)
Dual space D:    S_D[0:6] EMA + G_inject_D (B̂⊗B̂ modulated by τ_opt)

No algebraic reduction. S_D reads only from B̂ and τ_opt (declared I/O).
Sector D cross-term in F is zero: no write-back to Z_t or stalk values.
Orthogonality: Sector D lives only in S_D. It does not enter Z or partition logic.
```

---

## H. EXP-402 Gate Spec

```
EXP-402: Ghost-Zeeman Homeostasis (EXP-317 implementation)

β_Z_eff(t) = β_Z_base · (1 + γ_fb · B_A(t−1))
B_A(t−1)   = ‖S_A(t−1)‖ / (‖Z_A(t−1)‖ + ε)

New declared operator Φ_fb: Z → β_Z_eff(t) (inserted between Z computation and Bτ).
Stability bound: γ_fb ∈ (0, 2.0) for β_Z_base = 2.0.
P_yz invariant: ‖S_A‖ and ‖Z_A‖ are both norms → B_A is P_yz-invariant.
Also extends to B_D: β_Z_eff_D(t) = β_Z_base · (1 + γ_fb_D · B_D(t−1)).
```

---

## I. Forbidden Operations

```
ghost_direct_control | stalk_collapse | retroactive_confluence_cert
budget_retroactive_adjustment | validity_predicate_shift | post_hoc_rewrite_rule_addition
```
