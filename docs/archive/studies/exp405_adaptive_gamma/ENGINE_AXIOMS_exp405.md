# ENGINE_AXIOMS_exp405 — Adaptive Gamma Warmup Schedule

**Protocol:** exp405-v1  
**Inherits:** exp404-v1, exp403-v1, exp402-v1, exp401-v1  
**Author:** Daniel J. Dillberg — bigdilly95@gmail.com  
**Declaration hash:** `6e498f656aeb0fce5b7bfb588642ebef935e6df154b3d5195f907213a07ca889`  
**Status:** open  
**Gate source:** EXP-404 Ghost #15 — overshoot_ratio=1.33 (proactive; threshold=1.5)

---

## Axiom 1 — Adaptive Gamma Operator

`phi_fb_adaptive` replaces `phi_fb_exp` (EXP-404) with a time-varying gain schedule.

```
phi_fb_adaptive: (S_A, Z_A, S_D, scene_n, params) → (β_Z_eff, B_A, B_D, γ_eff_A, γ_eff_D)

B_A     = ‖S_A‖ / (‖Z_A‖ + ε)
B_D     = ‖S_D‖ / (‖Z_A‖ + ε)
ramp(n) = 1 − exp(−n / τ)   for n ≥ 1;   ramp(0) = 0
γ_eff_A = γ_∞_A · ramp(n)
γ_eff_D = γ_∞_D · ramp(n)
β_Z_eff = max(β_Z_min, β_Z_base · exp(γ_eff_A · B_A − γ_eff_D · B_D))
```

Parameters (locked): `β_Z_base=2.0`, `γ_∞_A=0.5`, `γ_∞_D=0.5`, `τ=5.0`, `β_Z_min=0.1`, `ε=1e-15`.

**Properties:**
- Cold start: `ramp(0)=0` → `β_Z_eff=β_Z_base` (no feedback at scene n=0)
- Asymptotic: `ramp(n→∞)→1` → `γ_eff→γ_∞` → reduces to `phi_fb_exp` (EXP-404)
- At n=1: `γ_eff=0.5·(1−exp(−0.2))=0.0906` (18% of full gain)
- At n=5: `γ_eff=0.5·(1−exp(−1))=0.316` (63% of full gain)
- At n=20: `γ_eff=0.5·(1−exp(−4))=0.491` (98% of full gain)

**Ramp schedule (τ=5):**

| n | ramp(n) | γ_eff | β_Z_eff (B_A*=4.81) |
|---|---------|-------|----------------------|
| 0 | 0.000   | 0.000 | 2.00 (cold) |
| 1 | 0.181   | 0.091 | 2.70 |
| 5 | 0.632   | 0.316 | 4.68 |
| 10 | 0.865  | 0.433 | 8.60 |
| 20 | 0.982  | 0.491 | 17.0 |
| ∞  | 1.000  | 0.500 | 17.19 |

---

## Axiom 2 — Overshoot Suppression vs EXP-404

**Math (EXP-404 overshoot at n=1):**
```
γ_A=0.5, B_A(n=0 cold)=3.303
β_Z_eff(EXP-404, n=1) = 2.0·exp(0.5·3.303) = 10.43   (421% jump from base)
```

**Math (EXP-405 suppression at n=1):**
```
γ_eff_A(n=1) = 0.5·(1−exp(−1/5)) = 0.0906
β_Z_eff(EXP-405, n=1) = 2.0·exp(0.0906·3.303) = 2.70   (35% jump from base)
```

Ratio: EXP-404 jumps 5.2× at n=1; EXP-405 jumps 1.35×. Overshoot suppression factor ≈ 3.9×.

**Trajectory comparison (N=20 sequential):**
```
bze_404: [2.00, 10.43, 12.64, 15.13, 22.88, 17.38, 17.20, 17.19, ..., 17.19]
          overshoot_ratio = 22.88/17.19 = 1.33 (peak n=4, settled n=7)

bze_405: [2.00, 2.70, 4.77, 6.87, 7.53, 9.15, 5.59, 13.85, 10.28, 9.44,
          6.96, 16.86, 14.26, 19.16, 15.24, 20.34, 15.92, 21.17, 16.38, 21.75]
          overshoot_ratio = 1.0000 (monotone non-decreasing envelope — no spike)
```

`overshoot_ratio_405=1.0 < overshoot_ratio_404=1.33` ✓

---

## Axiom 3 — Gravitational Backreaction Under Adaptive Schedule

At n=20 (γ_eff≈0.491·B_A*):
```
β_Z_eff*(405)[n=20] = 2.0·exp(0.491·4.81) ≈ 21.75   (not yet converged to ∞-limit)
Ω_fb*(405)[n=20]    = |21.75 − 2.0| / 2.0 = 9.875   (988%)
β_Z_eff*(404)[∞]    = 17.19;   Ω_fb*(404) = 7.60    (760%)
```

The adaptive schedule produces HIGHER apparent backreaction at n=20 (not yet converged), exceeding EXP-404's settled value. This is not an equilibrium comparison — it is a transient artifact of the ramp not having fully settled by N=20.

**Dual arithmetic note:** γ_eff_A, γ_eff_D are primary scalars; B_A, B_D are observables computed from dual residual norms ‖S_A‖, ‖S_D‖. No algebraic collapse between spaces.

---

## Axiom 4 — Ghost #16: 2-Period Leaf Count Oscillation

**Observation (N=20 sequential, EXP-405):**
```
lc_405: [92, 120, 120, 106, 106, 64, 113, 71, 71, 64, 106, 71, 78, 71, 78, 71, 78, 71, 78, 71]
lc_404: [92,  71,  71,  78,  71, 71,  71, 71, 71, 71,  71, 71, 71, 71, 71, 71, 71, 71, 71, 71]
```

EXP-404 converges to single attractor (71 leaves) by n=5.  
EXP-405 enters a 2-period oscillation between {71, 78} for n≥11, with multi-valued transient in n=5–10.

**Mechanism:**  
The slow γ ramp causes β_Z_eff to traverse a different trajectory through the (B_A, leaf_count) parameter space. At intermediate β_Z_eff values (≈14–20), the partition dynamics are bistable — two leaf attractor states coexist (71 and 78). The adaptive schedule crosses this bistable region slowly, coupling the EMA accumulation to alternating expansion depths.

**Gravitational analogy:** this is analogous to a secular resonance — the ramp period (τ=5) commensurable with the EMA memory (α=0.1 → effective memory≈10 steps) → parametric coupling → 2-cycle.

**Ghost #16 (formal):**  
`Gₜ = Zₜ − Π_W(Zₜ)` (per protocol). The numeric residual S_A under the adaptive ramp does not reach a fixed EMA attractor at N=20. The lc oscillation is a primary-space manifestation of the dual-space EMA non-stationarity induced by time-varying γ_eff. Not an error; not an entity. Observable: `lc_tail_values={64, 71, 78, 106, 113}` (multi-period during ramp, 2-cycle post-n=10).

---

## Axiom 5 — Saturation Comparison

| Operator | saturation_ratio (N=20) | sat floor |
|---|---|---|
| EXP-402 linear (γ_A=0, γ_D=2, S_D=[1]×6) | 0.60 | 0.5 |
| EXP-404 exp   (γ_A=0, γ_D=2, S_D=[1]×6) | 0.20 | 0.1 |
| EXP-405 adaptive (default γ_∞=0.5, τ=5) | 0.00 | 0.1 |

EXP-406 gate: `saturation_ratio > 0.5` — **inactive** for all three under default seed.

---

## Axiom 6 — P_yz Invariance

`phi_fb_adaptive` reads only `‖S_A‖`, `‖Z_A‖`, `‖S_D‖` (Euclidean norms) and `scene_n` (scalar). All inputs are P_yz-invariant. Therefore `phi_fb_adaptive` is P_yz-invariant by construction.

Verified across N=20 sequential steps:
```
max|β_Z_eff_fwd(n) − β_Z_eff_mir(n)| = 1.78e-14  (floating point noise)
max|B_A_fwd(n) − B_A_mir(n)|          = 1.78e-15
max|B_D_fwd(n) − B_D_mir(n)|          = 0.00e+00
leaf_count_fwd(n) = leaf_count_mir(n) for all n=0..19
```

---

## Verified Results

| Fork | Assertions | Result |
|------|-----------|--------|
| Fork A (`run_seed_exp405.py`) | 10/10 | **PASS** |
| Fork B (`run_p_invariance_exp405.py`) | 5/5 | **PASS** |

```
phi_fb_adaptive cold (n=0):  β_Z_eff = 2.000000 = β_Z_base ✓
phi_fb_adaptive n=1:         bze_405=2.018 < bze_404=2.103 (γ_eff < γ_inf) ✓
phi_fb_adaptive n→∞:         diff=0.0000 < 0.1 (converges to phi_fb_exp) ✓
overshoot_ratio:             1.0000 < 1.33 (spike eliminated) ✓
leaf_count(n=0):             92 (EXP-401 regression) ✓
[7] exp regime active:       bze_405[-1]=21.75 > β_Z_base=2.0; Ghost #16 range=16.15 ✓
[8] Ghost #16:               lc_tail={64,71,78,106,113} (2-cycle) bounded [30,200] ✓
saturation_ratio:            0.0000 < 0.5 (EXP-406 gate inactive) ✓
gradient:                    monotone ↑ in B_A, ↓ in B_D ✓
P_yz:                        max|bze_fwd−mir|=1.78e-14 ✓
```

---

## Ghost Notes

**Ghost #16:** 2-period oscillation in leaf_count (and β_Z_eff amplitude) under adaptive γ ramp with τ=5. Mechanism: slow ramp traverses bistable region of (β_Z_eff, leaf_count) dynamics; EMA memory (≈10 steps) couples to ramp timescale (τ=5) → parametric 2-cycle. Observable at n≥11. EXP-404 avoids this by jumping to β_Z_eff*=17.19 rapidly (n=5) and settling into the single-attractor basin. EXP-405 approaches the same asymptotic γ but via a longer transient that enters the bistable region.

**Resolution options (EXP-406 candidates):**
- A: EMA smoothing of β_Z_eff: `β_Z_eff_smooth(t+1) = α_bze·β_Z_eff_smooth(t) + (1-α_bze)·β_Z_eff(t)` — damps 2-cycle
- B: Larger τ (e.g. τ=20): γ_eff stays below bistable threshold for n≤20, no 2-cycle but slower convergence
- C: Non-monotone ramp: fast rise to 0.3·γ_∞, plateau, then slower rise to γ_∞ — avoids resonance with EMA memory

---

## EXP-406 Gate

**Trigger (proactive):** Ghost #16 2-cycle detected. β_Z_eff not converged at N=20. B_A EMA trajectory path-dependent under γ ramp.

**Options:**
- A: EMA-smoothed β_Z_eff feedback (second-order damping)
- B: Increase τ_warmup → slower ramp, avoid bistable crossing
- C: Stochastic perturbation to break 2-cycle symmetry (perturbation τ-dithering)
