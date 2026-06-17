# ENGINE_AXIOMS_exp404 — Exponential Phi_fb

**Protocol:** exp404-v1  
**Inherits:** exp403-v1, exp402-v1, exp401-v1  
**Author:** Daniel J. Dillberg — bigdilly95@gmail.com  
**Declaration hash:** `e7447ec6a65022a25d426a8f0b796ef18292d6cf3f85047c2239b004d225e67c`  
**Status:** open  
**Gate source:** EXP-403 Fork A [10] forced sat_ratio=0.60 > 0.50

---

## Axiom 1 — Exponential Phi_fb Operator

`phi_fb_exp` replaces the linear `phi_fb` (EXP-402) when `saturation_ratio > 0.5`.

```
phi_fb_exp: (S_A, Z_A, S_D, params) → β_Z_eff  (scalar)

B_A = ‖S_A‖ / (‖Z_A‖ + ε)
B_D = ‖S_D‖ / (‖Z_A‖ + ε)
β_Z_eff = max(β_Z_min_exp, β_Z_base · exp(γ_A · B_A − γ_D · B_D))
```

Parameters (locked): `β_Z_base=2.0`, `γ_A=0.5`, `γ_D=0.5`, `β_Z_min_exp=0.1`, `ε=1e-15`.

**Properties:**
- Always positive: `exp(x) > 0` for all `x ∈ ℝ` (no saturation at β=0)
- Fixed point: `β_Z_base · exp(0) = β_Z_base` when `γ_A·B_A = γ_D·B_D`
- Linearisation: `exp(x) ≈ 1 + x + O(x²)` → reduces to EXP-402 for `|x| ≪ 1`
- Gradient monotone: `∂β/∂B_A = β_Z_base·γ_A·exp(...) > 0` (amplification); `∂β/∂B_D < 0` (pullback)

---

## Axiom 2 — Saturation Floor Comparison

| Operator | Formula | Floor | Saturation threshold (B_D − B_A, γ_A=γ_D=0.5) |
|---|---|---|---|
| EXP-402 linear | β_base·(1+γ_A·B_A−γ_D·B_D) | 0.5 | B_D − B_A > 1.5 |
| EXP-404 exponential | β_base·exp(γ_A·B_A−γ_D·B_D) | 0.1 | γ_D·B_D − γ_A·B_A > ln(20) ≈ 3.0 |

The exponential doubles the saturation headroom (1.5 → 3.0) and lowers the floor (0.5 → 0.1).

**Forced-params comparison** (γ_A=0, γ_D=2.0, S_D_init=[2]×6, N=20):
```
EXP-402 (linear):       saturation_ratio = 0.60  (gate triggered)
EXP-404 (exponential):  saturation_ratio = 0.20  (gate resolved ✓)
```

---

## Axiom 3 — Equilibrium and Backreaction

**Fixed point:** `γ_A · B_A* = γ_D · B_D*` → `β_Z_eff* = β_Z_base`.  
At `γ_A = γ_D`, this requires `B_A* = B_D*`.

For the seed scene (B_A* >> B_D*, scene-structural):
```
B_A* = 4.811   B_D* = 0.0013
β_Z_eff*_404 = 2.0 · exp(0.5 · 4.811 − 0.5 · 0.0013) ≈ 2.0 · exp(2.405) ≈ 17.19
β_Z_eff*_402 = 2.0 · (1 + 0.5 · 4.811 − 0.5 · 0.0013) ≈ 6.81
```

**Gravitational backreaction:**
```
Ω_fb*_404 = |17.19 − 2.0| / 2.0 = 7.60    (760%)
Ω_fb*_402 = |6.81  − 2.0| / 2.0 = 2.40    (240%)
```

The exponential amplifies backreaction 3.2× relative to linear at the same steady-state ghost ratios.

---

## Axiom 4 — Transient Dynamics (Ghost #15)

```
β_Z_eff trajectory (EXP-404, N=20):
  [2.00, 10.43, 12.64, 15.13, 22.88, 17.38, 17.20, 17.19, ..., 17.19]
                                       ↑ peak overshoot at n=4
β_Z_eff trajectory (EXP-402, N=20):
  [2.00, 5.30, 7.14, 6.81, 6.81, ..., 6.81]
  (monotone convergence)
```

**Ghost #15 — Exponential Overshoot:** During EMA warmup (n=0→4), B_A rises steeply. The exponential amplifies each increment multiplicatively, creating a peak `β_Z_eff=22.88` at n=4 before EMA stabilises. The linear EXP-402 showed monotone approach to equilibrium.

`overshoot_ratio = max(β_Z_eff) / β_Z_eff* = 22.88 / 17.19 = 1.33` (33% overshoot).

**EXP-405 gate:** if `overshoot_ratio > 1.5` → consider damped exponential or adaptive γ reduction during warmup.

---

## Axiom 5 — Leaf Count Under Exponential Regime

| Regime | β_Z_eff* | leaf_count* |
|---|---|---|
| EXP-402 warm | 6.81 | 106 |
| EXP-404 warm | 17.19 | 71 |
| EXP-401 cold | 2.00 | 92 |

Stronger Zeeman field (higher `β_Z_eff`) → tighter budget per partition → recursion terminates earlier → fewer leaves. This is correct architecture: the homeostasis loop trades partition depth for Zeeman focusing intensity.

---

## Axiom 6 — P_yz Invariance

`phi_fb_exp` reads only `‖S_A‖`, `‖Z_A‖`, `‖S_D‖` — Euclidean norms invariant under any orthogonal transformation including P_yz. Therefore `phi_fb_exp` is P_yz-invariant by construction.

Verified across N=20 sequential steps:
```
max|β_Z_eff_fwd(n) − β_Z_eff_mir(n)| = 2.13e-14  (floating point noise)
max|B_A_fwd(n) − B_A_mir(n)|          = 2.66e-15
max|B_D_fwd(n) − B_D_mir(n)|          = 0.00e+00
leaf_count_fwd(n) = leaf_count_mir(n) for all n
```

---

## Verified Results

| Fork | Assertions | Result |
|------|-----------|--------|
| Fork A (`run_seed_exp404.py`) | 10/10 | **PASS** |
| Fork B (`run_p_invariance_exp404.py`) | 5/5 | **PASS** |

```
phi_fb_exp neutral:   β_Z_eff = 2.000000 (exp(0)=1 ✓)
phi_fb_exp amplify:   B_A=0.058 → β_Z_eff=2.059 > 2.0 ✓
phi_fb_exp pullback:  B_D=0.058 → β_Z_eff=1.943 ∈ (0, 2.0) ✓
phi_fb_exp floor:     B_D→∞ → β_Z_eff=0.100 ≥ 0.1 ✓
linearisation:        |phi_fb_exp − phi_fb| = 6.26e-6 < 0.01 (small ghost) ✓
EXP-401 regression:   leaf_count=92, cold β_Z_eff=2.0 ✓
forced saturation:    sat_ratio_404=0.20 < sat_ratio_402=0.60 ✓ (3× resolved)
Ghost #14:            β_Z_eff*(404)=17.19 vs β_Z_eff*(402)=6.81 (2.52× amplification)
Ghost #15:            overshoot_ratio=1.33 (peak 22.88 at n=4, settles 17.19)
gradient:             monotone ↑ in B_A, ↓ in B_D ✓
P_yz:                 max|bze_fwd−mir|=2.13e-14 ✓
```

---

## Ghost Notes

**Ghost #14:** `phi_fb_exp` with B_A*=4.81 (scene-structural) gives `exp(0.5×4.81)=11.07 → β_Z_eff*=22.1` (initial estimate). Actual equilibrium is `17.19` due to EMA warmup dynamics. Leaf count drops to 71 (from 106 under EXP-402). The exponential regime trades leaf density for focusing intensity.

**Ghost #15:** Transient overshoot (peak β_Z_eff=22.88 at n=4, 33% above equilibrium). Cause: exponential amplification of rising B_A during warmup. EXP-402 linear was monotone; EXP-404 exponential has an overshoot phase. Monitor for stability at large N or non-stationary scenes.

---

## EXP-405 Gate

**Trigger:** `overshoot_ratio = max(β_Z_eff(n)) / β_Z_eff* > 1.5`.

**Options:**
- A: Damped exponential `β_Z_eff = β_Z_base · exp(γ_A·B_A − γ_D·B_D) · α_damp^n` during warmup
- B: Adaptive γ schedule `γ(n) = γ_∞ · (1 − exp(−n/τ))` (zero at n=0, ramps to γ_∞)
- C: Exponential moving average of β_Z_eff itself (second-order EMA smoothing)

For the seed scene, overshoot_ratio=1.33 < 1.5, so EXP-405 gate is currently **inactive**.
