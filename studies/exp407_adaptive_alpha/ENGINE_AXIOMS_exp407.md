# ENGINE_AXIOMS_exp407 — Adaptive α_bze Schedule (Synchronized Dual Warmup)

**Protocol:** exp407-v1  
**Inherits:** exp406-v1, exp405-v1, exp404-v1, exp403-v1, exp402-v1, exp401-v1  
**Author:** Daniel J. Dillberg — bigdilly95@gmail.com  
**Declaration hash:** `2dc29bcfbb1d7b02f65549f4d4750ac9b7af5603d4a726a3fa53347e67773f87`  
**Status:** open  
**Gate source:** EXP-406 Ghost #17 — EMA lag-overshoot (Ω_inertia_max=0.281); fixed α=0.5 provides equal damping at all stages

---

## Axiom 1 — Adaptive α Operator

`phi_fb_adaptive_ema` extends `phi_fb_ema` (EXP-406) with a time-varying inertia schedule synchronized to the γ warmup ramp.

```
phi_fb_adaptive_ema: (S_A, Z_A, S_D, scene_n, bze_ema_prev, params)
  → (β_Z_eff, β_raw, B_A, B_D, g_A, g_D, α_eff)

B_A      = ‖S_A‖ / (‖Z_A‖ + ε)
B_D      = ‖S_D‖ / (‖Z_A‖ + ε)
ramp(n)  = 1 − exp(−n / τ_warmup)     for n ≥ 1;   ramp(0) = 0
g_A      = γ_∞_A · ramp(n)
g_D      = γ_∞_D · ramp(n)
β_raw    = max(β_Z_min, β_Z_base · exp(g_A · B_A − g_D · B_D))
α_eff(n) = α_min + (α_max − α_min) · exp(−n / τ_α)
β_Z_eff  = max(β_Z_min, α_eff · bze_ema_prev + (1 − α_eff) · β_raw)
```

Parameters (locked): `β_Z_base=2.0`, `γ_∞_A=0.5`, `γ_∞_D=0.5`, `τ_warmup=5.0`,  
`α_max=0.9`, `α_min=0.7`, `τ_α=5.0`, `β_Z_min=0.1`, `ε=1e-15`.

**Synchronization:** `τ_warmup == τ_α == 5.0`. At n=τ: γ_eff=0.316·γ_∞, α_eff=0.774.

**α schedule:**

| n | α_eff | 2-cycle ratio (1−α)/(1+α) |
|---|-------|--------------------------|
| 0 | 0.900 | 0.053 (near-frozen) |
| 1 | 0.864 | 0.074 |
| 5 | 0.774 | 0.127 |
| 10 | 0.727 | 0.158 |
| 20 | 0.704 | 0.174 |
| ∞ | 0.700 | 0.176 (below α_crit floor) |

All values remain above `α_crit = 2/3` → 2-cycle damping ratio < 1/5 at all n.

---

## Axiom 2 — Critical Damping Threshold

**Derivation of α_crit:**

The 2-cycle in β_Z_eff arises when the EMA-filtered signal alternates between two basin attractors (lc=64 vs lc=71). Denote the two EMA-smoothed values as p and q:

```
p = α·q + (1−α)·f₁
q = α·p + (1−α)·f₂
```

Steady-state amplitude:

```
|p − q| = (1−α)/(1+α) · |f₁ − f₂|
```

From EXP-407 data: `|f₁−f₂|_raw ≈ 5.0` (raw signal 2-cycle amplitude). For leaf-count switching to be suppressed (`|p−q| < Δ_lc_threshold ≈ 1`):

```
(1−α)/(1+α) < 1/5   →   α > 2/3
```

**α_crit = 2/3 ≈ 0.667.**

EXP-407 uses `α_min=0.7 > α_crit` → damping ratio ≤ 0.176 < 0.2 at all n.

**Gravitational backreaction under adaptive inertia:**

```
Ω_fb(n)      = |β_Z_eff(n) − β_Z_base| / β_Z_base
Ω_inertia(n) = |β_Z_eff(n) − β_raw(n)| / (β_raw(n) + ε)

At n=5  (α≈0.774): Ω_inertia ≈ 0.52  (high inertia — slow response)
At n=20 (α≈0.704): Ω_inertia ≈ 0.07  (reduced inertia — tracking signal)
```

The adaptive schedule reduces lag-overshoot without surrendering the stability floor.

---

## Axiom 3 — Ghost #18: Alpha Subcritical Failure (Documented, Resolved)

**Observation (EXP-407 v1, α_min=0.2):**

```
alpha_traj: [0.9, 0.773, 0.669, 0.584, 0.515, 0.458, 0.411, 0.373, 0.341, 0.316,
             0.295, 0.278, 0.264, 0.252, 0.243, 0.235, 0.229, 0.223, 0.219, 0.216]
bze_407: [2.0, 2.16, 2.69, 4.3, 6.59, 7.99, 9.61, 7.38, 11.45, 9.01,
          7.52, 14.27, 17.39, 15.46, 18.75, 16.35, 19.78, 16.98, 16.38, 20.58]
tail_range_407=13.07 >= tail_range_406=9.17   [5] FAIL
```

**Mechanism:** α_min=0.2 < α_crit=0.667. At n≥15, α_eff ≈ 0.22, giving 2-cycle damping ratio = 0.64. The equilibrium 2-cycle (Ghost #16) is a PERSISTENT feature of the attractor dynamics, not a transient. Reducing inertia after warmup REMOVES the damping that EXP-406's fixed α=0.5 sustained. Result: 2-cycle re-amplified in tail, tail_range WORSE than EXP-406.

**Ghost #18 (formal):**  
`Gₜ = Zₜ − Π_W(Zₜ)`. Numeric residual S_A under `α_min < α_crit` allows bze_ema to decouple from the equilibrium attractor, oscillating with amplitude `|p−q| = (1−α_eff)/(1+α_eff)·|f₁−f₂|`. Not an entity; a numeric instability triggered by inertia reduction below the critical threshold.

**Resolution:** raise `α_min` from 0.2 to 0.7 (above α_crit=0.667). This is a parameter revision within the same operator design, requiring hash update of SEED_DECLARATION.

---

## Axiom 4 — Dual Arithmetic Separation

`bze_ema_prev` and `α_eff` are **primary-space scalars**: caller-tracked, not stored in MuState dual fields.

`S_A`, `S_D` are **dual-space accumulators**: EMA residuals under the protocol pipeline `μ → Lτ → Bτ → Rτ → Z → S → W → OBS`.

`B_A = ‖S_A‖/(‖Z_A‖+ε)` and `B_D = ‖S_D‖/(‖Z_A‖+ε)` are observables computed from dual norms. They enter `phi_fb_adaptive_ema` as scalar inputs to primary-space arithmetic. No algebraic reduction collapses the two spaces.

**Dual warmup synchronization (τ_warmup = τ_α = 5.0):**

```
γ_eff(n) = γ_∞ · (1 − exp(−n/5))    [dual gain ramp UP]
α_eff(n) = 0.7 + 0.2 · exp(−n/5)    [primary inertia ramp DOWN]
```

At n=5: γ_eff = 0.316·γ_∞; α_eff = 0.774. Both schedules share the same timescale, keeping the dual→primary coupling approximately constant during warmup.

---

## Axiom 5 — P_yz Invariance

`phi_fb_adaptive_ema` reads only `‖S_A‖`, `‖Z_A‖`, `‖S_D‖` (Euclidean norms), `scene_n` (scalar), and `bze_ema_prev` (primary scalar). All inputs are P_yz-invariant. Therefore `phi_fb_adaptive_ema` is P_yz-invariant by construction.

Verified across N=20 sequential steps (fwd: x=+0.5, mir: x=−0.5):

```
max|β_Z_eff_fwd(n) − β_Z_eff_mir(n)| = 7.11e-15  (floating point noise)
max|B_A_fwd(n) − B_A_mir(n)|          = 1.78e-15
max|B_D_fwd(n) − B_D_mir(n)|          = 0.00e+00
leaf_count_fwd(n) = leaf_count_mir(n) for all n=0..19
```

---

## Verified Results

| Fork | Assertions | Result |
|------|-----------|--------|
| Fork A (`run_seed_exp407.py`) | 10/10 | **PASS** |
| Fork B (`run_p_invariance_exp407.py`) | 5/5 | **PASS** |

```
[2]  cold start: β_Z_eff=2.0000=β_Z_base; α_eff(0)=0.9=α_max ✓
[3]  n=1: α_407=0.864 > 0.5 → bze407=2.0025 ≤ bze406=2.0091 ✓
[4]  n=100: α_eff=0.7000≈α_min; bze407=bze_exp (diff=0.0000) ✓
[5]  tail_range_407=2.7114 < tail_range_406=9.1732 (ratio=0.296) ✓
[6]  last5_range_407=0.5939 < last5_range_406=4.2170 ✓
[7]  lc_407_tail=[64,71,106] (3 vals) ≤ lc_406_tail=[71,78,106] (3 vals) ✓
[8]  saturation_ratio_407=0.0000 < 0.5 ✓
[9]  overshoot_ratio_407=1.0083 < overshoot_404=1.33 ✓
[10] gradient monotone: B_A↑ B_D↓ ✓
P_yz: max|bze_fwd−mir|=7.11e-15 ✓
```

---

## Ghost Notes

**Ghost #16:** (inherited from EXP-405) 2-period oscillation in leaf_count and β_Z_eff from bistable (β_Z_eff, lc) dynamics. EXP-407 suppresses this via sustained α_eff > α_crit throughout N=20: tail_range reduced from 14.79 (EXP-405) to 2.71.

**Ghost #17:** (inherited from EXP-406) EMA lag-overshoot at fixed α=0.5. EXP-407 reduces lag via lower steady-state α (0.7 vs 0.5 would give HIGHER lag; but higher α earlier gives LOWER overshoot spike). overshoot_407=1.008 vs overshoot_406≈1.033.

**Ghost #18:** Adaptive α subcritical. α_min < α_crit=2/3 causes inertia reduction below the 2-cycle damping threshold, reintroducing Ghost #16 at n≥10. Observable: tail_range regression vs EXP-406. Resolution: α_min ≥ 0.7. Unique to adaptive schedules that couple inertia reduction to warmup convergence.

---

## EXP-408 Gate

**Trigger (proactive):** bze_407[-1]=11.18 < bze_406[-1]=17.13. The high inertia floor (α_min=0.7) slows convergence to the equilibrium β_Z_eff. The system is better damped but approaches equilibrium more slowly.

**Options:**
- A: Increase τ_α (e.g. 10.0) to extend the warmup before α settles — allows higher early-phase damping over more steps
- B: Two-phase schedule: fast decay α: 0.9→0.7 over τ=5, then fixed at α_min=0.7 (equivalent to current but cleaner formulation)
- C: Asymmetric schedule: γ_eff ramps UP with τ=5; α_eff ramps DOWN with larger τ=20 (decouple the timescales)
- D: Measure the convergence-damping Pareto frontier: (tail_range, convergence_speed) as α_min varies in [0.667, 0.95]
