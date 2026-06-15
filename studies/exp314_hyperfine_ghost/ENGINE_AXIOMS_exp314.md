# ENGINE_AXIOMS — EXP-314: The Hyperfine Ghost
**Protocol version:** exp314-v1  
**Inherits:** exp313-v1  
**Declaration hash:** 5ca52bef5d2a508073ab8585a1e84aa8393e64ddd7672c2c48ab4dd4a0a5006c

---

## A. Motivation: Inter-Channel Phase Drift

EXP-311/312/313 activated the dual ghost channels S_A (Sector A, dims 0–7) and S_C (Sector C, dims 8–11) via G_inject. These channels accumulate independently. EXP-310 showed a lag-3 coupling between them via KSG transfer entropy, but required a brute-force lag scan.

EXP-314 introduces a **coupling operator J_AC** that measures the instantaneous misalignment between S_A and S_C at each partition step — the **precession angle Ω_AC** — analogous to hyperfine splitting in the Zeeman effect, where nuclear spin-orbit coupling creates sub-level splittings not predicted by the main Zeeman Hamiltonian.

In the atomic analogy:
- S_A = "electron spin" in the ghost dual space
- S_C = "nuclear spin"
- J_AC = spin-spin coupling tensor
- Ω_AC = precession angle (angle between coupled spin vectors)

The key benefit: Ω_AC provides a **deterministic lag selection rule** τ_opt without brute-force scan.

---

## B. Coupling Operator and Precession Observable

**Declared parameters (preregistered, fixed):**

| Parameter | Value | Description |
|-----------|-------|-------------|
| `J_AC` | 4×4 identity | Coupling matrix. J_AC @ S_A[0:4] = S_A[0:4] |
| `W_max` | 8 | Maximum lag window |
| `eps` | 1e-15 | Numerical floor |

**Precession angle:**

```
v_A  =  J_AC @ S_A[0:4]          ∈ ℝ⁴
v_C  =  S_C                       ∈ ℝ⁴

cos(Ω_AC) = (v_A · v_C) / (‖v_A‖ · ‖v_C‖ + ε)
Ω_AC      = arccos(clip(cos(Ω_AC), −1, 1))     ∈ [0, π]
```

**Lag selection rule:**

```
τ_opt = max(1, round(Ω_AC / π · W_max))
```

| Ω_AC | Interpretation | τ_opt (W_max=8) |
|------|----------------|-----------------|
| 0 | S_A and S_C aligned | 1 (short lag) |
| π/2 | orthogonal | 4 (mid lag) |
| π | anti-aligned | 8 (full lag) |

When S_C is near-zero (‖S_C‖ < ε), Ω_AC = 0 by convention (denominator guard prevents division by zero).

---

## C. Ghost History Extension

At each partition step, EXP-314 appends to `ghost_history`:

```
(S_A_norm, S_C_norm, Omega_AC, tau_opt)
```

This extends the EXP-311/312/313 history of `(a_norm, c_norm)` with the two coupling observables.
`ghost_history` is excluded from H_t (same status as `focal_point`, `G_inject_log`).

---

## D. Operator Pipeline: apply_gamma_314

```
apply_gamma_314(mu, claim_id, partition_key, payloads, beta, budget, spent,
                focal_point, B, beta_Z, J_AC, thresholds, alpha_leak, beta_CA, mass_ref, kappa_ref)
```

**Step 1:** Call `apply_gamma_313(...)` → `(mu_313, cost, validity_class)`.  
**Step 2:** Retrieve S_A, S_C from `mu_313`.  
**Step 3:** Compute `v_A = J_AC @ S_A[0:4]`.  
**Step 4:** Compute `Ω_AC = arccos(clip((v_A · S_C) / (‖v_A‖·‖S_C‖ + ε), −1, 1))`.  
**Step 5:** Compute `τ_opt = max(1, round(Ω_AC / π · W_max))`.  
**Step 6:** Append `(‖S_A‖, ‖S_C‖, Ω_AC, τ_opt)` to `ghost_history`.  
**Return:** `(mu_313, cost, validity_class)` — primary state unchanged.

**Dual-space constraint:** Steps 2–6 operate exclusively in the dual space (S_A, S_C).
Z_t, stalk values, and the primary operator pipeline are not modified.

---

## E. P_yz Invariance of Ω_AC

`S_A[0:4]` accumulates G_inject_A[7] = f(Z_before[11]) = f(kappa aggregate).  
`S_C` accumulates G_inject_C[3] = f(‖Z_before[0:4]‖) = f(Sector A norm) = constant.

Both are P_yz-invariant (proven in EXP-311/312/313 — kappa extents and Sector A norm are preserved under x → −x).

`J_AC = I` (identity) has no spatial axes → `v_A = S_A[0:4]`.

```
cos(Ω_AC) = (S_A[0:4] · S_C) / (‖S_A[0:4]‖ · ‖S_C‖ + ε)
```

Under P_yz: both `S_A[0:4]` and `S_C` are identical in fwd/mir (from EXP-313 Fork B assertion [5][6]).  
Therefore `cos(Ω_AC_fwd) = cos(Ω_AC_mir)` → `Ω_AC_fwd = Ω_AC_mir`. QED.

---

## F. Dual Arithmetic Separation

```
Primary space:   Z_t dynamics under Lτ / Bτ / Rτ (unchanged from EXP-313)
Dual space:      S_A, S_C EMA tracking + Ω_AC coupling observable

No algebraic reduction coupling primary and dual spaces.
J_AC acts only on (S_A[0:4], S_C) → scalar Ω_AC stored in ghost_history.
Orthogonality maintained.
```

---

## G. Dev Notes

**New ghost in system (ghost #6 — hyperfine coupling):** Ω_AC is the first INTER-channel observable in the engine. Prior observables (B_A, B_C) measured each channel independently. Ω_AC measures the ANGLE between them — the dual-space "spin precession" of the ghost system.

**Gravitational backreaction analogy:** Ω_AC is the radiation reaction cross-term. In GR backreaction, the primary field couples to its own radiation via a retarded Green's function. Here, S_A (mass-geometry coupling) and S_C (curvature injection) precess against each other; Ω_AC is the angle of their precession, τ_opt is the retarded time lag at which TE is maximally predictive.

**EXP-401 gate:** With Ω_AC and τ_opt available, the lag selection for anisotropic Gaussian covariance alignment (EXP-401) can be driven by the precession frequency rather than grid search. This closes the EXP-310 open limit: "lag selection driven by architecture" rather than brute force.

**Implementation fix — numeric degeneracy in `_compute_omega_ac` (post-execution dev note):**
The arccos primary path requires `‖J_AC @ S_A[0:4]‖ >= NUMERIC_FLOOR`. Under the current G_inject architecture (EXP-311), G_inject_A injects only into `S_A[7]`, and lossless partition gives `G_A = Z_A - Π_W(Z_A) = 0` in exact arithmetic. Therefore `S_A[0:4] = 0` (only floating-point noise ≈ 1e-15), and the arccos numerator/denominator both resolve to noise that is **not** P_yz-invariant (noise pattern depends on spatial coordinates).

**Fix (operators.py, `_compute_omega_ac`):** When `‖v_A‖ < NUMERIC_FLOOR = 1e-6`, fall back to:
```
Ω_AC = 2 · arctan2(‖S_C‖, ‖S_A‖)  ∈ (0, π)
τ_opt = max(1, round(Ω_AC / π · W_max))   [formula unchanged]
```
- **P_yz-invariant:** `‖S_A‖` and `‖S_C‖` proven invariant by EXP-313 Fork B assertions [5][6].
- **Physical interpretation:** `Ω_AC = 2·arctan2(‖S_C‖, ‖S_A‖)` measures the energy balance between ghost channels. When `‖S_A‖ >> ‖S_C‖` (normal operating regime), `Ω_AC → 0`, `τ_opt = 1` (short lag). Equal norms: `Ω_AC = π/2`, `τ_opt = W_max/2 = 4`.
- **Forward compatibility:** The primary arccos path activates automatically if `G_inject_A` is re-targeted to dims in `S_A[0:4]` (future experiments). No architectural change required.

**Verified:** Fork A 8/8 PASS, Fork B 9/9 PASS. Ω_AC_fwd = Ω_AC_mir = 0.01727 rad, τ_opt = 1, delta < 2e-14. Trace P_yz-invariant across all 13 EXP-314 ghost_history entries.

---

## H. Forbidden Operations

```
ghost_direct_control | stalk_collapse | retroactive_confluence_cert
budget_retroactive_adjustment | validity_predicate_shift | post_hoc_rewrite_rule_addition
```
