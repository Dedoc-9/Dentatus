# ENGINE_AXIOMS — EXP-315: Dual G_inject_A Activation
**Protocol version:** exp315-v1  
**Inherits:** exp314-v1  
**Declaration hash:** e16dd1a01735bc1d6a97100daf2bfb3dfd172e2853b5875a875ccc54ea5933b0

---

## A. Motivation: Degenerate Omega_AC (EXP-314 ghost #6 fix)

EXP-314 introduced Ω_AC as an inter-channel precession observable. However, the G_inject
architecture (EXP-311/312/313/314) injects into `S_A[7]` only. Under lossless partition,
`G_A = Z_A - Π_W(Z_A) = 0` exactly, so `S_A[0:6] = 0` in exact arithmetic.

The primary arccos path requires `‖J_AC @ S_A[0:4]‖ ≥ 1e-6`. With `S_A[0:4] = 0`,
the formula degenerates to 0/0 resolved by floating-point noise — not P_yz-invariant.
EXP-314 fell back to `2·arctan2(‖S_C‖, ‖S_A‖)`, which is invariant but restricted
to `τ_opt = 1` in the normal regime (`‖S_A‖ >> ‖S_C‖`).

EXP-315 closes this by routing two physically distinct quantities into `S_A[0]` and
`S_A[3]`, making `‖v_A‖ >> 1e-6` always and producing a non-trivially time-varying Ω_AC.

---

## B. Dual G_inject_A Injection

**Modified injection (EXP-315):**

```
mass_norm = ‖Z_before[0:4]‖

G_inject_A[0] = alpha_leak * (mass_norm / mass_ref)          ← NEW: mass-norm coupling
G_inject_A[3] = alpha_leak * beta_CA * (kappa / kappa_ref)   ← moved from dim 7
G_inject_A[1] = G_inject_A[2] = G_inject_A[4:8] = 0

G_inject_C[3] = alpha_leak * (mass_norm / mass_ref)          ← unchanged
```

**Parameters (locked):**

| Parameter | Value |
|-----------|-------|
| `alpha_leak` | 0.1 |
| `beta_CA` | 0.3 |
| `mass_ref` | 2.0 |
| `kappa_ref` | 2.0 |
| `alpha_ema` | 0.85 |

---

## C. Omega_AC Mechanics with Dual Injection

After EMA from zero, `S_A[0:4] ≈ [S_A0, 0, 0, S_A3]` where:

```
S_A0 = (1 - alpha_ema) * G_inject_A[0] / (1 - alpha_ema * alpha_ema_306)
     ≈ const * alpha_leak * mass_norm / mass_ref

S_A3 = (1 - alpha_ema) * G_inject_A[3] / (1 - alpha_ema * alpha_ema_306)
     ≈ const * alpha_leak * beta_CA * kappa / kappa_ref
```

`S_C ≈ [0, 0, 0, S_C3]` where `S_C3` accumulates `G_inject_C[3] = G_inject_A[0]` (same source).

```
v_A = J_AC @ S_A[0:4] = [S_A0, 0, 0, S_A3]

v_A · S_C = S_A3 * S_C3

‖v_A‖ = sqrt(S_A0² + S_A3²)

cos(Ω_AC) = S_A3 * S_C3 / (sqrt(S_A0² + S_A3²) * ‖S_C‖)
           ≈ S_A3 / sqrt(S_A0² + S_A3²)        [since ‖S_C‖ ≈ S_C3]

Ω_AC = arccos(S_A3 / sqrt(S_A0² + S_A3²))
     = arctan(S_A0 / S_A3)
     = arctan(mass_norm / (beta_CA * kappa))
```

**Interpretation:** Ω_AC measures the relative injection rates of mass-norm vs kappa.

| Regime | Condition | Ω_AC | τ_opt (W_max=8) |
|--------|-----------|------|-----------------|
| Kappa-dominated | kappa >> mass_norm / beta_CA | → 0 | 1 |
| Balanced | kappa = mass_norm / beta_CA | π/4 | 2 |
| Mass-dominated | mass_norm >> beta_CA * kappa | → π/2 | 4 |

Kappa is an integral over bbox extents; it grows with recursive depth as children have smaller
extents but more of them. The ratio evolves across tree depth → `τ_opt` is non-constant.

---

## D. P_yz Invariance

```
G_inject_A[0] = f(‖Z_before[0:4]‖)   = f(‖Σ stalk_A‖)
  Z_before[0:4] = Σ active stalks [0:4]  = Sector A (mass, r, g, b)
  Under P_yz: stalk[0:4] unchanged (no x-coord)  →  G_inject_A[0] P_yz-invariant ✓

G_inject_A[3] = f(Z_before[11])       = f(kappa)
  kappa = ∫ extents-based curvature   →  P_yz-invariant (EXP-312) ✓

G_inject_C[3] = f(‖Z_before[0:4]‖)   → P_yz-invariant ✓

S_A[0], S_A[3], S_C[3] all accumulate P_yz-invariant injections
  → v_A = [S_A0, 0, 0, S_A3] is P_yz-invariant
  → S_C ≈ [0, 0, 0, S_C3] is P_yz-invariant
  → cos(Ω_AC) = S_A3 / sqrt(S_A0² + S_A3²) is P_yz-invariant
  → τ_opt = max(1, round(Ω_AC/π · W_max)) is P_yz-invariant    QED
```

---

## E. Operator Pipeline

```
apply_gamma_315(mu, claim_id, partition_key, payloads, beta, budget, spent,
                focal_point, B, beta_Z, J_AC, W_max, thresholds,
                alpha_leak, beta_CA, mass_ref, kappa_ref)
```

**Step 1:** Call `apply_gamma_312(g_inject_fn=_g_inject_315)`:
  - Partition kernel unchanged (bbox, stalk decomposition, F, validity)
  - G_inject overridden: `G_inject_A[0] = f(mass_norm)`, `G_inject_A[3] = f(kappa)`

**Step 2:** Retrieve `S_A`, `S_C` from result.

**Step 3:** Compute `v_A = J_AC @ S_A[0:4]`.

**Step 4:** Compute `Ω_AC = arccos(clip(v_A · S_C / (‖v_A‖·‖S_C‖ + ε), −1, 1))`.
  Primary path active: `‖v_A‖ ~ sqrt(S_A0² + S_A3²) >> 1e-6`.

**Step 5:** Compute `τ_opt = max(1, round(Ω_AC / π · W_max))`.

**Step 6:** Append `(‖S_A‖, ‖S_C‖, Ω_AC, τ_opt)` to `ghost_history`.

**Return:** `(mu_next, cost, validity_class)`

---

## F. Dual Arithmetic Separation

```
Primary space:   Z_t dynamics under Lτ / Bτ / Rτ (unchanged)
Dual space:      S_A[0], S_A[3], S_C[3] EMA + Ω_AC coupling

No algebraic reduction. J_AC acts only on S_A[0:4] → scalar Ω_AC in ghost_history.
Orthogonality maintained: G_inject modifies only dual EMA, not Z_t or stalk values.
```

---

## G. Dev Notes

**Ghost #6 closure (EXP-315):** The numeric degeneracy of EXP-314 is resolved by routing two
physically distinct quantities (mass-norm and kappa) into orthogonal dims of `S_A[0:4]`. The
resulting `v_A = [S_A0, 0, 0, S_A3]` has `‖v_A‖ ~ O(0.1)` — well above the fallback threshold.

**Gravitational backreaction interpretation:** `S_A[0]` accumulates the mass-field injection
rate (analogous to source term in Einstein field equations). `S_A[3]` accumulates the curvature
injection rate (analogous to Ricci curvature response). Ω_AC = arctan(source/curvature) is the
phase angle between them — exactly the backreaction cross-term in linearized GR:
`δG_μν = 8πG δT_μν` where `δT` (mass perturbation) leads `δG` (curvature response) by a
retarded time `τ_opt = f(Ω_AC)`.

**EXP-401 readiness:** With `τ_opt` now varying meaningfully across tree depth (encodes local
mass/kappa balance), the anisotropic covariance alignment in EXP-401 can use the per-node
`τ_opt` to select the lag window for the Gaussian splatting kernel. This closes the EXP-310
open limit entirely.

**Forward pivot (EXP-316, optional):** inject `G_inject_A[1]` from `Z_before[5]` (y-coordinate
sum — P_yz-invariant) to activate `S_A[1]`, making `v_A` a 3-component non-degenerate vector.
This enables full 4D angular resolution of the ghost precession, not just the 2D planar angle
from EXP-315.

---

## H. Forbidden Operations

```
ghost_direct_control | stalk_collapse | retroactive_confluence_cert
budget_retroactive_adjustment | validity_predicate_shift | post_hoc_rewrite_rule_addition
```
