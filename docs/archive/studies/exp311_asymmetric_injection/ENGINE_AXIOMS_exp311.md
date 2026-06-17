# ENGINE_AXIOMS — EXP-311: The Asymmetric Injection
**Protocol version:** exp311-v1  
**Inherits:** exp310-v1  
**Declaration hash:** 10659ed4d37c027aed4144fd847c3e35986e49e45be596c9cc77b6806d040f35

---

## A. Structural Result: G_t = 0 Identity

For all operators in EXP-308 through EXP-310:

```
Z_t = sum_{i: claim_i active} stalk_i   =   W_t @ ones_N
```

Since `Z_t ∈ span(W_t)` by construction, the orthogonal complement projection vanishes:

```
G_t = Z_t − Π_{W_t}(Z_t) = 0    ∀ t
```

Verified empirically: `G_A_norm = 1.46e-13`, `G_C_norm = 4.27e-11` (machine epsilon).  
Consequence: `S_A = S_C = 0` throughout all EXP-309/310 runs. Ghost channel structurally inactive.

**This is a mathematical identity, not a bug. EXP-311 does not modify this identity.**

---

## B. EXP-311 Resolution: G_inject Auxiliary Residual

EXP-311 introduces `G_inject` as a new auxiliary per-partition residual, **orthogonal to and independent of G_t**.

### B.1 Definition

At each call to `apply_gamma_311`, before the partition:

```
Z_before = Z_t(mu)          # stalk aggregate before child expansion

G_inject_C ∈ ℝ^4:
    G_inject_C[3] = alpha_leak * (||Z_before[0:4]|| / mass_ref)

G_inject_A ∈ ℝ^8:
    G_inject_A[7] = alpha_leak * beta_CA * (Z_before[11] / kappa_ref)
```

Parameters (preregistered, fixed):

| Parameter  | Value | Rationale |
|------------|-------|-----------|
| alpha_leak | 0.1   | Fixed constant. Reynolds-equiv `‖Z‖/(‖S‖+ε)` diverges at S=0 and violates stateless protocol. |
| beta_CA    | 0.3   | C→A coupling factor. Asymmetry: A→C/C→A = 1/0.3 = 3.33× |
| mass_ref   | 2.0   | `‖[1,1,1,1]‖` (unit seed stalk Sector A norm) |
| kappa_ref  | 2.0   | `kappa_integral([0,1]³)` (unit cube kappa) |

### B.2 S Update Rule (EXP-311)

```
S_C_{t+1} = alpha_ema * S_C_t + (1−alpha_ema) * G_inject_C
S_A_{t+1} = alpha_ema * S_A_t + (1−alpha_ema) * G_inject_A
```

`alpha_ema = 0.85` (inherited from EXP-308).  
G_t = 0 identity unchanged; G_inject replaces zero G_t as the EMA input for this experiment only.

---

## C. Operator Pipeline: apply_gamma_311

```
apply_gamma_311(mu, claim_id, partition_key, payloads, beta, budget, spent,
                focal_point, thresholds, alpha_leak, beta_CA, mass_ref, kappa_ref)
```

**Step 1:** Record `Z_before = Z_t(mu)` (stalk aggregate before expansion).  
**Step 2:** Call `apply_gamma_309(...)` → `(mu_309, cost, validity_class)`.  
**Step 3:** Compute `G_inject_C`, `G_inject_A` from `Z_before` per B.1.  
**Step 4:** Update `S_C`: `S_C_new = alpha_ema * mu_309.S_C + (1−alpha_ema) * G_inject_C`.  
**Step 5:** Update `S_A`: `S_A_new = alpha_ema * mu_309.S_A + (1−alpha_ema) * G_inject_A`.  
**Step 6:** Apply `_replace_S_C(S_C_new)` and `_replace_S_A(S_A_new)` on `mu_309`.  
**Step 7:** Append `(G_inject_C[3], G_inject_A[7])` to `mu_next.G_inject_log` (not in H_t hash).  
**Return:** `(mu_next, cost, validity_class)`.

**Operator is stateless:** all inputs explicitly declared. `G_inject_log` is a non-hashed trace field.

---

## D. P_yz Invariance

`G_inject_C[3]` is a function of `‖Z_before[0:4]‖` (Euclidean norm of Sector A).  
`G_inject_A[7]` is a function of `Z_before[11] = kappa_integral(bbox)`.

Both are invariant under P_yz (the reflection x→x, y→−y, z→−z):
- Sector A stalk values (mass, r, g, b) carry no spatial index. Their norm is P_yz-invariant.
- `kappa_integral(bbox)` depends only on box extents `|hi−lo|`, which are unsigned. P_yz-invariant.

Therefore: `‖S_C‖` and `‖S_A‖` are P_yz-invariant under EXP-311 injection.

---

## E. Dual Arithmetic Separation

Primary space: `Z_t` dynamics under `Lτ / Bτ / Rτ` (unchanged from EXP-309).  
Dual space: `S_A`, `S_C` tracking via EMA of `G_inject` (EXP-311 auxiliary channel).

No algebraic reduction coupling primary and dual spaces. `G_inject` feeds only the dual EMA; it does not modify `Z_t` or any claim stalk. Orthogonality maintained.

---

## F. Dev Notes

**New ghost in system:** `G_inject` is a per-partition signal not present in EXP-308–310. It lives in the dual space only (EMA → S), with no feedback into the primary Z dynamics. The gravitational backreaction analogy: `G_inject` is the radiation reaction force on the ghost sector — it drains energy from the mass-curvature coupling asymmetry into the EMA accumulator without modifying the geodesic (primary Z trajectory).

**Lag-3 coupling:** `corr3/corr1 = 20×` (confirmed). With EXP-311 activating non-zero ghost, multi-lag TE with window shift (EXP-312) becomes executable. EXP-311 Fork B will confirm the signal is P_yz symmetric (not an artifact of spatial orientation).

**Hash continuity:** `G_inject_log` excluded from H_t (same status as `focal_point`). H_t remains: `HASH(μ_t ⊕ Z_t ⊕ S_t ⊕ W_t ⊕ protocol_version)`. Ghost injection trace is observable but not identity-determining.

---

## G. Forbidden Operations

The following operations are prohibited and constitute protocol violation requiring revert to last valid H_t:

```
ghost_direct_control | stalk_collapse | retroactive_confluence_cert
budget_retroactive_adjustment | validity_predicate_shift | post_hoc_rewrite_rule_addition
```
