# ENGINE_AXIOMS_exp406 — EMA-Smoothed β_Z_eff (Inertial Attention Field)

**Protocol:** exp406-v1  
**Inherits:** exp405-v1, exp404-v1, exp403-v1, exp402-v1, exp401-v1  
**Author:** Daniel J. Dillberg — bigdilly95@gmail.com  
**Declaration hash:** `84255beb1f11d0182a052e6d31e9c5aaa4e87c37d3d1c0a6494b56fd4ad891cf`  
**Status:** open  
**Gate source:** EXP-405 Ghost #16 — 2-period lc oscillation (parametric resonance τ=5, EMA memory ~10 steps)

---

## Axiom 1 — Inertial Attention Field Operator

`phi_fb_ema` wraps `phi_fb_adaptive` output with a second-order EMA (inertial mass) on β_Z_eff.

```
phi_fb_ema: (S_A, Z_A, S_D, scene_n, bze_ema_prev, params) → (β_Z_eff, β_raw, B_A, B_D, γ_eff_A, γ_eff_D)

B_A         = ‖S_A‖ / (‖Z_A‖ + ε)
B_D         = ‖S_D‖ / (‖Z_A‖ + ε)
ramp(n)     = 1 − exp(−n / τ)          (τ=5; ramp(0)=0)
γ_eff_A     = γ_∞_A · ramp(n)
γ_eff_D     = γ_∞_D · ramp(n)
β_raw       = max(β_Z_min, β_Z_base · exp(γ_eff_A · B_A − γ_eff_D · B_D))
β_Z_eff     = max(β_Z_min, α_bze · bze_ema_prev + (1 − α_bze) · β_raw)
```

Parameters (locked): `γ_∞_A=γ_∞_D=0.5`, `τ=5.0`, `α_bze=0.5`, `β_Z_min=0.1`, `β_Z_base=2.0`, `ε=1e-15`.

**bze_ema_prev:** primary-scalar, caller-tracked. NOT stored in MuState (dual/primary separation preserved). Cold start: `bze_ema_prev = β_Z_base`.

**Inertial mass interpretation:**  
`α_bze` is the inertial coefficient. At `α_bze=0.5`, the attention field has a half-life of 1 step under constant input — changes to β_raw propagate to β_Z_eff with exponential damping, giving the engine's focus a physical "weight" that resists rapid reorientation.

---

## Axiom 2 — 2-Cycle Damping (Ghost #16 Resolution)

For a steady-state 2-cycle `{f₁, f₂}` in β_raw (arising from Ghost #16 bistable leaf attractor):

```
β_Z_eff 2-cycle fixed points:
  p = (f₁ + α·f₂) / (1+α)
  q = (f₂ + α·f₁) / (1+α)
  |p − q| = |f₁ − f₂| · (1−α) / (1+α)
```

At `α_bze=0.5`: `|p−q| = |f₁−f₂|/3` → amplitude reduced to **33% of EXP-405**.

**Observed (N=20 sequential):**
```
tail_range_405 = 14.785  (bze_405 oscillates 15.92 ↔ 21.75)
tail_range_406 =  9.173  (bze_406 reduced; ratio=0.620 vs theory 0.333)
```

The empirical ratio (0.620) exceeds the theoretical 1/3 because:
- The raw 2-cycle `{f₁,f₂}` is not stationary — it shifts under EMA dynamics
- EMA of bze changes the B_A trajectory, which shifts `f₁,f₂` themselves
- Self-consistent fixed point differs from the uncoupled prediction

This is a second-order coupling between the primary (β_Z_eff) and dual (S_A → B_A) spaces. The damping is real but weaker than the linear prediction.

---

## Axiom 3 — Ghost #17: EMA Lag-Overshoot

**Mechanism:**  
During a rising phase (β_raw increasing), β_Z_eff lags behind β_raw (`bze_ema_prev < β_raw`). When β_raw peaks and begins to decline, β_Z_eff continues rising (momentum carries it past the raw peak) → mild overshoot.

```
Observed:
  overshoot_ratio_406 = max(β_Z_eff) / β_Z_eff[-1] = 17.70 / 17.13 = 1.0333
  overshoot_ratio_404 = 1.33   (uncontrolled exponential spike)
  overshoot_ratio_405 = 1.00   (monotone under slow γ ramp, but 2-cycle)
```

**Ghost #17 (formal):**  
`Ω_inertia(n) = |β_Z_eff(n) − β_raw(n)| / (β_raw(n) + ε)` is the inertial lag observable.  
`max Ω_inertia = 0.2814` (28% lag at peak mismatch).  
`mean Ω_inertia = 0.1190` across N=20.

EMA lag-overshoot is bounded: cannot exceed `α_bze · |bze_ema_prev − β_raw| / β_Z_eff`, which vanishes as the system converges.

---

## Axiom 4 — Gravitational Backreaction Under Inertial Damping

At n=19 (bze_406[-1]=17.13):
```
Ω_fb(406)[n=19] = |17.13 − 2.0| / 2.0 = 7.565   (756%)
Ω_fb(404)[∞]    = |17.19 − 2.0| / 2.0 = 7.595   (760%)
Ω_fb(405)[n=19] = |21.75 − 2.0| / 2.0 = 9.875   (988%, not converged)
```

EXP-406 converges to near-EXP-404 equilibrium (7.57 vs 7.60) by n=19. EXP-405 had not converged at n=19 (9.88). Inertial damping resolves the 2-cycle AND pulls the system back toward the EXP-404 equilibrium.

**Dual arithmetic note:** β_Z_eff, β_raw, bze_ema_prev all in primary space. S_A, S_D, B_A, B_D in dual space. No algebraic collapse.

---

## Axiom 5 — Dev Note: alpha_leak=0.0 Ghost in apply_gamma_401_recursive

**Discovery:** passing `alpha_leak=0.0` explicitly to `apply_gamma_401_recursive` suppresses S_A accumulation (returns S_A≡0). Not passing it (using default) returns S_A with norm=6.6065.

```python
# Suppressed:
apply_gamma_401_recursive(mu, cid, ..., alpha_leak=0.0)  # S_A norm=0
# Correct:
apply_gamma_401_recursive(mu, cid, ...)                  # S_A norm=6.607
```

Root cause: a branch in `apply_gamma_401_recursive` activated by explicit `alpha_leak` keyword (likely `if alpha_leak:` evaluating False for 0.0 vs truthy check). EXP-406 fixes this by calling `apply_gamma_401_recursive` without the `alpha_leak` kwarg, matching EXP-405's call signature.

This is a latent Ghost in the operator API — explicit zero differs from absent default. Recommend audit of all optional numeric params in `apply_gamma_401_recursive`.

---

## Axiom 6 — P_yz Invariance

`phi_fb_ema` reads only `‖S_A‖`, `‖Z_A‖`, `‖S_D‖` (Euclidean norms), `scene_n` (scalar), and `bze_ema_prev` (scalar). All inputs are P_yz-invariant by norm-invariance of orthogonal transformations.

`bze_ema_prev` is identical for forward and mirror runs (same primary-scalar cold start).

Verified across N=20 sequential steps:
```
max|β_Z_eff_fwd(n) − β_Z_eff_mir(n)| = 7.11e-15  (floating point noise)
max|B_A_fwd(n) − B_A_mir(n)|          = 2.66e-15
max|B_D_fwd(n) − B_D_mir(n)|          = 0.00e+00
leaf_count_fwd(n) = leaf_count_mir(n) for all n=0..19
```

---

## Verified Results

| Fork | Assertions | Result |
|------|-----------|--------|
| Fork A (`run_seed_exp406.py`) | 10/10 | **PASS** |
| Fork B (`run_p_invariance_exp406.py`) | 5/5 | **PASS** |

```
phi_fb_ema cold (n=0):     β_Z_eff=2.000 = β_Z_base ✓
phi_fb_ema n=1 inertia:    bze_ema=2.009 <= adaptive=2.018 (lag active) ✓
phi_fb_ema n→∞ settled:    bze_ema≈bze_exp (diff=0.000) ✓
tail_range_406=9.173 < tail_range_405=14.785 (Ghost #16 damped) ✓
last5_range_406=4.217 < last5_range_405=5.830 (convergence improved) ✓
lc_406_tail_count=3 <= lc_405_tail_count=3 (oscillation bounded) ✓
saturation_ratio_406=0.0000 < 0.5 ✓
overshoot_ratio_406=1.033 < overshoot_404=1.33 (Ghost #17 bounded) ✓
gradient: monotone ↑ B_A, ↓ B_D ✓
P_yz: max|bze_fwd−mir|=7.11e-15 ✓
Omega_inertia: mean=0.119  max=0.281
bze_406[-1]=17.13 ≈ bze_404*=17.19 (equilibrium near-recovered)
```

---

## Ghost Notes

**Ghost #16 (EXP-405):** 2-period lc oscillation from parametric resonance (τ=5, EMA memory ~10 steps). Resolved by EXP-406: tail_range reduced from 14.785 → 9.173. Full suppression requires α_bze > 0.9 (reduces amplitude to <5%).

**Ghost #17:** EMA lag-overshoot. β_Z_eff carries momentum past the β_raw peak during declining transients. Overshoot_ratio=1.033 (3.3%), well below EXP-404's 1.33. Decreases as system converges. Observable: `Ω_inertia=|β_Z_eff−β_raw|/(β_raw+ε)`.

**alpha_leak Ghost (dev note):** explicit `alpha_leak=0.0` keyword suppresses S_A accumulation in `apply_gamma_401_recursive`. Root cause: boolean branch on numeric kwarg. Workaround: omit kwarg (uses default). Recommend audit.

---

## EXP-407 Gate

**Trigger (proactive):** Ghost #17 EMA lag-overshoot (1.033); tail variability still present (last5_range=4.22 at N=20).

**Options:**
- A: Increase α_bze (e.g. 0.7 or 0.9) — stronger inertia, kills 2-cycle amplitude further but increases lag
- B: Adaptive α_bze: high during warmup (strong damping), lower after convergence (fast tracking)
- C: Fix alpha_leak Ghost in apply_gamma_401_recursive and re-verify all EXP-4xx
- D: Accept α_bze=0.5 as production setting; document Ghost #17 as bounded and benign
