# ENGINE_AXIOMS — EXP-313: The Zeeman K_bound
**Protocol version:** exp313-v1  
**Inherits:** exp312-v1  
**Declaration hash:** 708e7b75be7bbd907568fcbd16a32fa128ceea0e0112dcdc64de38e8480273b4

---

## A. Motivation: Controlled Symmetry Breaking

EXP-312 achieves P_yz invariance in a field-free vacuum — all octants receive equal K_budget.
EXP-313 introduces a declared external field **B** that breaks octant budget symmetry predictably,
analogous to the normal Zeeman effect splitting a spectral line into components under a magnetic field.

In the normal Zeeman effect:
```
E_m = E_0 − g·μ_B·m_l·|B|     m_l ∈ {−l, ..., +l}
```
Energy levels split linearly by projection onto **B**. Selection rules (Δm = 0, ±1) govern
which transitions are allowed. Here, "energy level" = K_budget, "transition" = recursive split.

---

## B. Zeeman K_budget Rule

At each recursive call, child octant `i` receives budget:

```
centroid_i  =  (c_lo_i + c_hi_i) / 2          # spatial centroid of child bbox
B_hat       =  B / ‖B‖                          # unit field direction

p_i         =  centroid_i · B_hat               # Zeeman projection (scalar)
w_i         =  exp(β_Z · p_i) / Σ_j exp(β_Z · p_j)    # softmax weights

K_child_i   =  K_budget · N · w_i · exp(−LAMBDA_DECAY)
```

**Parameters (preregistered, fixed):**

| Parameter | Value | Description |
|-----------|-------|-------------|
| `B` | [1.0, 0.5, 0.3] | External field vector (arbitrary 3D, x-component nonzero) |
| `β_Z` | 2.0 | Softmax temperature |
| `N` | 8 | Octree children |

**Limits:**
- β_Z → 0: `w_i → 1/N`, `K_child_i → K_budget · exp(−LAMBDA_DECAY)` — recovers EXP-312
- β_Z → ∞: all budget flows to child most aligned with **B**
- Sum: `Σ K_child_i = K_budget · N · exp(−LAMBDA_DECAY)` (total scales by N, redistributable)

---

## C. P_yz Field Covariance (Option B)

**B transforms as a polar vector** under P_yz (x → −x):

```
B_fwd = (B_x,  B_y, B_z)
B_mir = (−B_x, B_y, B_z)   =  P_yz(B)
```

**Budget covariance proof:**

```
centroid_mir[i XOR 4] = P_yz(centroid_fwd[i])      (x-bit flips under reflection)

centroid_mir[i XOR 4] · B_mir
= P_yz(centroid_fwd[i]) · P_yz(B)
= centroid_fwd[i] · B                               (dot product ‖·‖ is O(3)-invariant)

=> w_fwd[i] = w_mir[i XOR 4]
=> K_fwd[i] = K_mir[i XOR 4]    for all i ∈ {0..7}    QED
```

This is stronger than leaf-count equality: **per-octant budget is spatially covariant**.

---

## D. Operator Pipeline: apply_gamma_313

```
apply_gamma_313(mu, claim_id, partition_key, payloads, beta, budget, spent,
                focal_point, B, beta_Z, thresholds, alpha_leak, beta_CA, mass_ref, kappa_ref)
```

Delegates the partition kernel to `apply_gamma_312` (Fix1 + Fix2 inherited).
Returns `(mu_next, cost, validity_class)` — identical signature to EXP-312.

`apply_gamma_313_recursive` adds per-child Zeeman budget weighting:

```
Step 1: compute centroid_i for each child bbox
Step 2: compute B_hat = B / ‖B‖
Step 3: p_i = centroid_i · B_hat
Step 4: w_i = softmax(β_Z · p_i)
Step 5: K_child_i = K_budget · N · w_i · exp(−LAMBDA_DECAY)
Step 6: recurse into each child with its individual K_child_i
```

Operator is stateless: B and β_Z are declared inputs, not hidden state.

---

## E. Multi-step P_yz Invariance

From Section C: `K_child_fwd[i] = K_child_mir[i XOR 4]`.

At the next recursion level, child `i` expands its grandchildren with budget `K_child_i`.
In mirror, the spatially corresponding child is `i XOR 4` with the same budget.
By induction: at every depth, spatially paired nodes have identical K_budget.

Since Fix1 + Fix2 (EXP-312) guarantee identical payloads and Sector A masses for spatial pairs,
the LOD gating is identical at every depth. Therefore:

```
fwd_leaves == mir_leaves    (full multi-step P_yz invariance under Zeeman field)
```

---

## F. Observables

```
B(t)   = ‖S‖ / (‖Z‖ + ε)                              global ghost ratio
B_A(t) = ‖S_A‖ / (‖Z_A‖ + ε)
B_C(t) = ‖S_C‖ / (‖Z_C‖ + ε)

K_ratio = max(K_child_i) / min(K_child_i)              Zeeman splitting ratio
K_align = argmax_i(K_child_i)                           dominant octant index
p_range = max(p_i) - min(p_i)                           projection spread
```

---

## G. Dev Notes

**Gravitational backreaction analogy:** The field **B** is the external gauge field. The Zeeman
splitting redistributes recursion energy (K_budget) along field lines without modifying the
primary Z dynamics. The ghost channel (S_A, S_C) is unaffected by **B** — it tracks only the
dual residual, orthogonal to the partition geometry.

**New ghost in system:** The K_budget asymmetry (K_ratio > 1 when β_Z > 0) creates structural
anisotropy in the recursion tree. The resulting leaf distribution is directionally biased but
still P_yz-covariant (paired spatial positions have equal depth). This is ghost #5:
"Zeeman structural anisotropy" — present in the tree topology, not in the stalk values.

**EXP-314 gate:** With directionally biased ghost accumulation (deeper trees along **B**),
the S_A and S_C channels accumulate at different rates in different spatial regions.
This inter-channel phase drift is the signal EXP-314 (hyperfine coupling) will measure via Ω_AC.

---

## H. Forbidden Operations

```
ghost_direct_control | stalk_collapse | retroactive_confluence_cert
budget_retroactive_adjustment | validity_predicate_shift | post_hoc_rewrite_rule_addition
```
