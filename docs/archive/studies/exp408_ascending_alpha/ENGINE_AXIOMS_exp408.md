# ENGINE_AXIOMS_exp408 — Ascending α_bze Schedule (Bootstrap to Maintenance)

**Protocol:** exp408-v1  
**Inherits:** exp407-v1, exp406-v1, exp405-v1, exp404-v1, exp403-v1, exp402-v1, exp401-v1  
**Author:** Daniel J. Dillberg — bigdilly95@gmail.com  
**Declaration hash:** `d1945e6736a284a33cf648ac0d7d06491e0bea704bd6fa69ca7beac277562055`  
**Status:** open  
**Gate source:** EXP-407: bze_407[-1]=11.18 < bze_406[-1]=17.13 (convergence lag from α_min=0.7 floor)

---

## Axiom 1 — Ascending α Operator

`phi_fb_ascending_ema` inverts the EXP-407 inertia direction: α ramps UP from loose to tight.

```
phi_fb_ascending_ema: (S_A, Z_A, S_D, scene_n, bze_ema_prev, params)
  → (β_Z_eff, β_raw, B_A, B_D, g_A, g_D, α_eff)

B_A      = ‖S_A‖ / (‖Z_A‖ + ε)
B_D      = ‖S_D‖ / (‖Z_A‖ + ε)
ramp(n)  = 1 − exp(−n / τ_warmup)     [γ ramps UP, unchanged from EXP-405]
g_A      = γ_∞_A · ramp(n)
β_raw    = max(β_Z_min, β_Z_base · exp(g_A · B_A − g_D · B_D))
α_eff(n) = α_max − (α_max − α_min) · exp(−n / τ_α)   [ramps UP: loose → tight]
β_Z_eff  = max(β_Z_min, α_eff · bze_ema_prev + (1 − α_eff) · β_raw)
```

Parameters (locked): `β_Z_base=2.0`, `γ_∞_A=0.5`, `γ_∞_D=0.5`, `τ_warmup=5.0`,  
`α_min=0.2`, `α_max=0.9`, `τ_α=2.0`, `β_Z_min=0.1`, `ε=1e-15`.

**Timescale decoupling:** `τ_α=2.0 ≠ τ_warmup=5.0`.  
α locks into maintenance mode before γ_eff reaches the bistable β_raw range.

**α schedule:**

| n | α_eff | (1−α)/(1+α) | state |
|---|-------|-------------|-------|
| 0 | 0.200 | 0.667 | loose (80% responsiveness) |
| 1 | 0.475 | 0.357 | transitional |
| 2.2 | 0.667 | 0.200 | crosses α_crit |
| 4 | 0.805 | 0.108 | above α_crit, bistable safe |
| 5 | 0.843 | 0.086 | |
| ∞ | 0.900 | 0.053 | maintenance lock (tightest) |

---

## Axiom 2 — Bistable Safety Constraint

α must exceed α_crit before β_raw enters the bistable range.

```
n_cross = -τ_α · ln((α_max − α_crit) / (α_max − α_min))
         = -2.0 · ln((0.9 − 0.667) / (0.9 − 0.2))
         = -2.0 · ln(0.333) = 2.20

n_bistable ≈ 4  (β_raw first exceeds ~7 from EXP-407 raw_407[4]=8.55)

Safety margin: n_bistable − n_cross = 4 − 2.20 = 1.80 steps
α(n=4) = 0.9 − 0.7·exp(−2) = 0.805 > α_crit=0.667 ✓
```

During n=0–2.2: α < α_crit. This is safe because β_raw ≈ β_Z_base=2.0 (γ_eff≈0), bistable dynamics inactive.

**Gravitational backreaction (bootstrap phase):**

```
Ω_fb(n=5) = |β_Z_eff(5) − β_Z_base| / β_Z_base = |5.99 − 2.0| / 2.0 = 2.00  (200%)
Ω_fb_407(n=5) = |5.96 − 2.0| / 2.0 = 1.98  (≈equal; bootstrap gain marginal at n=5)
```

Bootstrap advantage is concentrated at n=1–4 (ascending α < descending α from EXP-407).

---

## Axiom 3 — Ghost #19: Attraktorwahl (Attractor Selection)

**Observation (N=20 sequential, EXP-408):**

```
lc_408: [92, 106, 127, 127, 113, 113, 106, 106, 106, 64, 64, 106, 64, 64, ..., 64]
         ↑ high resolution climbing                    ↑ locks lc=64 from n=12
bze_408: [2.0, 2.37, 2.98, 4.09, 5.20, 5.99, 6.81, 7.47, 8.17, 8.89,
          8.71, 8.54, 9.47, 9.30, 9.13, 8.99, 8.87, 8.77, 8.69, 8.62]
          ↑ monotone climb to n=9                       ↑ decaying to lc=64 equilibrium
raw_408 at n=10–19: [7.14, 7.08, 17.69, 7.81, 7.60, ..., 8.01]  → settling ≈8
bze_408[-1] = 8.62  (lc=64 equilibrium)  vs  bze_407[-1]=11.18  (lc=71 equilibrium)
```

**Mechanism:**

At n=9, lc switches to 64 (lower-resolution basin). At that point α_eff=0.892 (90% inertia). The EMA absorbs only 10% of raw per step:

```
bze_{t+1} = 0.892·bze_t + 0.108·raw_t
```

With raw ≈ 7–8 at lc=64, bze converges to lc=64 equilibrium (≈8). The system cannot re-escape to the lc=71 basin because bze ≈ 8.6 is insufficient to trigger expansion beyond 64 leaves. High maintenance inertia **prevents basin re-escape** after the initial attractor is selected at n=9.

**Positive feedback loop:**

```
α_eff→0.9 ──→ bze drops slowly toward lc=64 raw≈8
             ──→ lc stays at 64 (bze insufficient for deeper expansion)
             ──→ raw stays ≈8 ──→ [cycle]
```

**Ghost #19 (formal):**  
`Gₜ = Zₜ − Π_W(Zₜ)`. The numeric residual S_A at n=9 encodes lc=64 leaf geometry. With α_eff=0.892, the EMA cannot re-weight toward the lc=71 basin within N=20 steps. Not an entity; a basin-selection artifact of the ascending α schedule. Observable: lc_tail={64} single attractor (vs {71,78} in EXP-406/407).

**Foreign language:** *Attraktorwahl* (German) — attractor selection. The α schedule determines not only convergence rate but WHICH BASIN is captured. Compare: *verrouillage de bassin* (French, basin lock), 吸引子選択 (*kyuuinshi sentaku*, Japanese).

**Contrast with Ghost #18:**  
Ghost #18 (EXP-407 v1): α below α_crit at EQUILIBRIUM → 2-cycle re-emerges within the targeted basin.  
Ghost #19 (EXP-408): α above α_crit, but maintenance lock prevents INTER-BASIN transitions → system converges stably but to the WRONG basin.

---

## Axiom 4 — Bootstrap Advantage (n=1–5)

The ascending schedule leads bze_407 (descending) during the discovery phase:

```
n:       1      2      3      4      5
bze_408: 2.37   2.98   4.09   5.20   5.99
bze_407: 2.10   2.32   2.89   4.08   5.96
Δ:      +0.27  +0.66  +1.20  +1.12  +0.03
```

Bootstrap advantage confirmed for n=1–4; neutralized at n=5. After n=5, α_408 > α_407 (ascending exceeds descending), and bze_408 begins lagging. The Attraktorwahl at n=9 finalizes the trajectory divergence.

**Implication:** bootstrap gain is real but insufficient to overcome the inter-basin transition — the engine reaches the bistable region while still climbing (n=4–9 is the critical window), and the high-α maintenance lock at that moment determines basin capture.

---

## Axiom 5 — Dual Arithmetic Separation

`bze_ema_prev` and `α_eff` are primary-space scalars. `S_A`, `S_D` are dual-space EMA accumulators. `B_A`, `B_D` are observables bridging dual→primary via norm operations. No algebraic collapse between spaces. Attraktorwahl operates entirely in primary space (bze trajectory), with dual-space S_A determining `B_A` → `β_raw` input.

---

## Axiom 6 — P_yz Invariance

`phi_fb_ascending_ema` reads only `‖S_A‖`, `‖Z_A‖`, `‖S_D‖`, `scene_n`, `bze_ema_prev`. All P_yz-invariant. Verified N=20:

```
max|β_Z_eff_fwd(n) − β_Z_eff_mir(n)| = 1.78e-15
max|B_A_fwd(n) − B_A_mir(n)|          = 2.22e-15
max|B_D_fwd(n) − B_D_mir(n)|          = 0.00e+00
leaf_count_fwd(n) = leaf_count_mir(n) for all n=0..19
```

Attraktorwahl is P_yz-symmetric: both forward and mirror trajectories lock to the same lc=64 basin.

---

## Verified Results

| Fork | Assertions | Result |
|------|-----------|--------|
| Fork A (`run_seed_exp408.py`) | 10/10 | **PASS** |
| Fork B (`run_p_invariance_exp408.py`) | 5/5 | **PASS** |

```
[2]  cold start: β_Z_eff=2.0=β_Z_base; α_eff(0)=0.2=α_min ✓
[3]  n=1: α_408=0.475 < α_407=0.864 → bze408=2.010 ≥ bze407=2.003 ✓
[4]  n=100: α_eff=0.900≈α_max ✓
[5]  last5_408=0.368 < last5_407=0.594 (Ghost #19 documented; lc=64 basin) ✓
[6]  tail_range_408=0.931 < tail_range_406=9.173 (α_max=0.9: 2-cycle ratio 5.3%) ✓
[7]  lc_408_tail=[64,106] bounded [30,200] ✓
[8]  saturation_ratio=0.0000 ✓
[9]  overshoot_408=1.099 < overshoot_404=1.33 ✓
[10] gradient monotone: B_A↑ B_D↓ ✓
P_yz: max|bze_fwd−mir|=1.78e-15 ✓
Ω_inertia_max=0.469  (EMA lag at peak climb, n=9-12)
```

---

## EXP-408 Summary Table (Phi_fb Evolution)

| EXP | Operator | α schedule | tail_range | bze[-1] | lc_tail | Ghost |
|-----|----------|-----------|-----------|---------|---------|-------|
| 404 | phi_fb_exp | fixed γ | — | 17.19* | {71} | #15 overshoot=1.33 |
| 405 | phi_fb_adaptive | γ ramp↑ | 14.79 | 21.75 | {71,78} | #16 2-cycle |
| 406 | phi_fb_ema | fixed α=0.5 | 9.17 | 17.13 | {71,78} | #17 lag-overshoot |
| 407 | phi_fb_adaptive_ema | α ramp↓ | 2.71 | 11.18 | {64,71,106} | #18 subcritical |
| **408** | **phi_fb_ascending_ema** | **α ramp↑** | **0.93** | **8.62** | **{64}** | **#19 Attraktorwahl** |

*EXP-404 bze[-1]=17.19 is the settled equilibrium (reached by n=7); EXP-408 converges to lc=64 basin (different attractor).

---

## Ghost Notes

**Ghost #19 — Attraktorwahl (Attractor Selection):** α ascending to 0.9 by n≈7 locks the system into whatever basin it occupies at that moment. When lc switches to 64 at n=9 (within the bistable window), the 90% inertia EMA prevents re-escape. Resolution requires EITHER: (a) delaying maintenance lock until bze has reached the target basin, OR (b) introducing a basin-detection signal to adaptively hold α low until target basin is confirmed.

---

## EXP-409 Gate

**Trigger (proactive):** Ghost #19. Neither descending (EXP-407, α_min=0.7 floor → stable but sluggish) nor ascending (EXP-408, α_max=0.9 → basin-locked) resolves both convergence AND basin-selection simultaneously.

**Options:**
- A: **Hysteresis α**: maintain α_low during climb phase; switch to α_high only after bze crosses a threshold (e.g., β_Z_eff > β_threshold ≈ 12). Basin-conditional inertia.
- B: **Composite schedule**: ascending τ_α=2.0 but α_max=0.7 (not 0.9) — fast lock to EXP-407 floor; neither too loose nor too tight.
- C: **Pareto frontier**: sweep (α_min, α_max, τ_α) over a grid; measure (tail_range, bze[-1], lc_stability) jointly.
- D: **Two-timescale split**: primary α for β_Z_eff smoothing; separate α_lc for a leaf-count EMA to detect basin; couple α to lc stability signal.
