# ENGINE_AXIOMS — EXP-316: 3-Component G_inject_A (Series 300 Hardening)
**Protocol version:** exp316-v1  
**Inherits:** exp315-v1  
**Declaration hash:** 522ca73148485fdc41b7f496ff21c13d34133318fb2ba259040508537f571f1f

---

## A. Motivation: Full 4D Angular Resolution

EXP-315 established a 2-component precession vector `v_A = [S_A0, 0, 0, S_A3]`.
Ω_AC was the planar angle in the (0, 3) subspace of S_A[0:4], tracking mass/kappa balance.

EXP-316 adds a third injection channel — y-aggregate — into `S_A[1]`, promoting
`v_A` to a 3-component non-degenerate vector. Ω_AC now resolves the full 3D angular
position of the precession axis in the (mass, y-shear, curvature) subspace.

This closes the angular degeneracy: any two experiments using different injection
channels cannot accidentally produce the same Ω_AC.

---

## B. Triple G_inject_A Injection

**Modified injection (EXP-316):**

```
mass_norm = ‖Z_before[0:4]‖

G_inject_A[0] = alpha_leak * (mass_norm / mass_ref)                ← EXP-315
G_inject_A[1] = alpha_leak * (|Z_before[5]| / y_ref)              ← NEW: y-agg coupling
G_inject_A[3] = alpha_leak * beta_CA * (kappa / kappa_ref)        ← EXP-315
G_inject_A[2] = G_inject_A[4:8] = 0

G_inject_C[3] = alpha_leak * (mass_norm / mass_ref)               ← unchanged
```

**Parameters (locked):**

| Parameter | Value |
|-----------|-------|
| `alpha_leak` | 0.1 |
| `beta_CA` | 0.3 |
| `mass_ref` | 2.0 |
| `kappa_ref` | 2.0 |
| `y_ref` | 1.0 |
| `alpha_ema` | 0.85 |

**Verified (seed stalk y=0.5, mass_norm=2.0, kappa~2.0):**

```
G_inject_A[0] = 0.100000   (mass-norm)
G_inject_A[1] = 0.050000   (y-aggregate)
G_inject_A[3] = 0.030000   (kappa)
```

---

## C. 3-Component Omega_AC Mechanics

After EMA from zero, `S_A[0:4] ≈ [S_A0, S_A1, 0, S_A3]`:

```
v_A = J_AC @ S_A[0:4] = [S_A0, S_A1, 0, S_A3]

v_A · S_C ≈ S_A3 * S_C3        [S_C ≈ [0,0,0,S_C3]]

‖v_A‖ = sqrt(S_A0² + S_A1² + S_A3²)  > ‖v_A‖_315 = sqrt(S_A0² + S_A3²)

cos(Ω_AC) = S_A3 / sqrt(S_A0² + S_A1² + S_A3²)
```

**Verified results (92 leaves, K_budget=2048):**

| Quantity | EXP-315 | EXP-316 |
|----------|---------|---------|
| `S_A[0]` | 0.0533 | 0.0533 |
| `S_A[1]` | 0.0 | **2.3604** |
| `S_A[3]` | 6.1702 | 6.1702 |
| `‖v_A‖` | 6.1704 | **6.6065** |
| Ω_AC step 1 | 1.28 rad (73.3°) | **1.31 rad (75.0°)** |
| Ω_AC final | 0.009 rad | **0.366 rad (20.9°)** |
| τ_opt range | {1, 3} | **{1, 2, 3}** |

The y-channel S_A[1] dominates the intermediate range: it grows proportional to
y-coordinate aggregates which stabilize at a larger scale than kappa.

---

## D. P_yz Invariance

```
G_inject_A[1] = alpha_leak * |Z_before[5]| / y_ref

Z_before[5] = Σ stalk[5] over active claims = aggregate y-coordinate (Sector B dim 1)

Under P_yz: p_yz_stalk negates stalk[4] (x) and stalk[8] (nx).
            stalk[5] (y) is NOT negated.
=> Z_before[5]_fwd = Z_before[5]_mir
=> |Z_before[5]| P_yz-invariant
=> G_inject_A[1] P_yz-invariant ✓

=> S_A[0], S_A[1], S_A[3], S_C[3] all accumulate P_yz-invariant injections
=> v_A = [S_A0, S_A1, 0, S_A3] is P_yz-invariant component-wise
=> cos(Ω_AC) = S_A3 / sqrt(S_A0² + S_A1² + S_A3²) is P_yz-invariant
=> τ_opt = max(1, round(Ω_AC/π · W_max)) is P_yz-invariant    QED
```

**Verified (Fork B):**
- S_A[1] fwd = S_A[1] mir = 2.360374 (delta = 8.88e-16)
- Ω_AC delta = 6.57e-13
- τ_opt trace: 0/13 mismatches, max_omega_delta = 8.87e-13

---

## E. Operator Pipeline

```
apply_gamma_316(mu, claim_id, partition_key, payloads, beta, budget, spent,
                focal_point, B, beta_Z, J_AC, W_max, thresholds,
                alpha_leak, beta_CA, mass_ref, kappa_ref, y_ref)
```

**Step 1:** Call `apply_gamma_314(g_inject_fn=_g_inject_316)`:
  - Partition kernel unchanged (bbox, stalk decomposition, F, validity)
  - G_inject overridden: G_A[0]=f(mass_norm), G_A[1]=f(|y_agg|), G_A[3]=f(kappa)

**Step 2:** Retrieve `S_A`, `S_C` from result.

**Step 3:** Compute `v_A = J_AC @ S_A[0:4]` — 3-component.

**Step 4:** Compute `Ω_AC = arccos(clip(v_A · S_C / (‖v_A‖·‖S_C‖ + ε), −1, 1))`.

**Step 5:** Compute `τ_opt = max(1, round(Ω_AC / π · W_max))`.

**Step 6:** Append `(‖S_A‖, ‖S_C‖, Ω_AC, τ_opt)` to `ghost_history`.

**Interface extension:** `g_inject_fn` in `apply_gamma_312` now receives `Z_before=Z_before`
as a keyword argument. `_g_inject_315` updated to accept and ignore `Z_before`. Backward-
compatible: all EXP-311/312/313/314/315 tests pass unchanged.

---

## F. Dual Arithmetic Separation

```
Primary space:   Z_t dynamics under Lτ / Bτ / Rτ (unchanged)
Dual space:      S_A[0], S_A[1], S_A[3], S_C[3] EMA + Ω_AC coupling

No algebraic reduction. J_AC acts only on S_A[0:4] → scalar Ω_AC in ghost_history.
Orthogonality maintained: G_inject modifies only dual EMA, not Z_t or stalk values.
S_A[1] injection from |Z_before[5]| reads an aggregate of the primary state
  but outputs only to the dual EMA channel — no write-back to Z_t.
```

---

## G. Dev Notes

**3-component precession geometry:** In EXP-315, `v_A` lay in a 2D plane (dims 0, 3).
The precession angle was the angle between the mass-line and the curvature-line.
In EXP-316, `v_A` spans a 3D subspace (dims 0, 1, 3): mass-norm, y-shear, curvature.
The resulting Ω_AC encodes the full 3-way balance across all partition steps.

**Gravitational backreaction extension:** In EXP-315, Ω_AC = arctan(source/curvature)
was a 2-term backreaction angle. EXP-316 extends this: `S_A[1]` accumulates the
y-aggregate, which is a transverse metric perturbation in the spatial sector.
The 3-component Ω_AC is now analogous to the full angular decomposition of the
stress-energy tensor perturbation `δT_μν` in linearized GR — three independent
channels (mass, shear, curvature) feeding the retarded lag window `τ_opt`.

**y-channel dominance:** `S_A[1] = 2.36` vs `S_A[0] = 0.053`. The y-aggregate
accumulates over the full tree (all active stalk y-coordinates), whereas mass_norm
is normalized to a fixed reference scale. This creates a large S_A[1] that shifts
Ω_AC toward the midrange (20–75°) instead of the near-zero regime of EXP-315.
The expanded τ_opt range ({1,2,3}) provides richer lag window selection for EXP-401.

**EXP-317 gate — Ghost-Zeeman homeostasis:**
```
β_Z_eff(t) = β_Z_base · (1 + γ_fb · B_A(t−1))
B_A(t−1)   = ‖S_A(t−1)‖ / (‖Z_A(t−1)‖ + ε)
```
Valid under protocol: uses S (EMA), not G (raw residual); declared I/O; P_yz-invariant
(‖S_A‖ and ‖Z_A‖ both norms). New declared operator Φ_fb inserted between Z and Bτ.
Stability bound: γ_fb ∈ (0, 2.0) for β_Z_base=2.0. Designated Series 400 Experiment 1.

---

## H. Forbidden Operations

```
ghost_direct_control | stalk_collapse | retroactive_confluence_cert
budget_retroactive_adjustment | validity_predicate_shift | post_hoc_rewrite_rule_addition
```
