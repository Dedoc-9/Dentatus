# ENGINE_AXIOMS_exp409 — Hysteresis α_bze Schedule (Conditional Basin Lock)

**Protocol:** exp409-v1  
**Inherits:** exp408-v1, exp407-v1, exp406-v1, exp405-v1, exp404-v1, exp403-v1, exp402-v1, exp401-v1  
**Author:** Daniel J. Dillberg — bigdilly95@gmail.com  
**Declaration hash:** `32a0fbef5f6e5e1eb0e33adc0ee3e25b332e3586b30e0497f81194fb48b799f6`  
**Status:** open  
**Gate source:** EXP-408 Ghost #19 (Attraktorwahl): neither descending nor ascending α resolves convergence + basin-selection jointly

---

## Axiom 1 — Hysteresis α Operator

`phi_fb_hysteresis_ema` uses a conditional latch rather than a continuous schedule.

```
phi_fb_hysteresis_ema: (S_A, Z_A, S_D, scene_n, bze_ema_prev, maint_latched, params)
  → (β_Z_eff, β_raw, B_A, B_D, g_A, g_D, α_eff, maint_latched_out)

B_A      = ‖S_A‖ / (‖Z_A‖ + ε)
B_D      = ‖S_D‖ / (‖Z_A‖ + ε)
ramp(n)  = 1 − exp(−n / τ_warmup)              [γ ramps UP, unchanged]
g_A      = γ_∞_A · ramp(n)
β_raw    = max(β_Z_min, β_Z_base · exp(g_A · B_A − g_D · B_D))

maint_latched_out = maint_latched OR (bze_ema_prev ≥ β_threshold)   [irreversible]
α_eff    = α_maint if maint_latched_out else α_disc
β_Z_eff  = max(β_Z_min, α_eff · bze_ema_prev + (1 − α_eff) · β_raw)
```

Parameters (locked): `β_Z_base=2.0`, `γ_∞_A=0.5`, `γ_∞_D=0.5`, `τ_warmup=5.0`,  
`α_disc=0.5`, `α_maint=0.9`, `β_threshold=12.0`, `β_Z_min=0.1`, `ε=1e-15`.

**Caller state** (primary scalars, tracked outside MuState):
- `bze_ema_prev`: previous step β_Z_eff output
- `maint_latched`: bool, initialized False, set True irreversibly when bze ≥ β_threshold

**Phase table:**

| Phase | condition | α_eff | 2-cycle ratio | behavior |
|-------|-----------|-------|---------------|----------|
| Discovery | bze < 12.0 AND NOT latched | 0.5 | 0.333 | EXP-406 trajectory → lc=71 basin |
| Maintenance | bze ≥ 12.0 OR latched | 0.9 | 0.053 | 2-cycle suppressed |

---

## Axiom 2 — β_threshold Derivation

The threshold is the separatrix between the lc=64 and lc=71 attractor basins in β_Z_eff space.

**Basin equilibria:**
```
β_raw^(lc=64) ≈ 8.0    (EXP-408 tail: raw→8.01 at lc=64)
β_raw^(lc=71) ≈ 17.19  (EXP-404 settled equilibrium)
```

**Separatrix (geometric mean = arithmetic midpoint of ln(β) space):**
```
β_threshold = √(β_low · β_high) = √(8.0 × 17.19) = √137.5 = 11.73
```

**B_A separatrix cross-check:**
```
B_A^(lc=64) = ln(β_low / β_base) / γ_∞ = ln(4.0) / 0.5 = 2.773
B_A^(lc=71) = ln(β_high / β_base) / γ_∞ = ln(8.595) / 0.5 = 4.302
B_A^sep     = (2.773 + 4.302) / 2 = 3.537
β_sep       = β_base · exp(γ_∞ · B_A^sep) = 2.0 · exp(1.769) = 11.73  ✓
```

Two independent derivations converge: **β_threshold = 11.73 → 12.0** (rounded up, safety margin = 0.27).

**Gravitational backreaction at threshold:**
```
Ω_fb(β_threshold) = |12.0 − 2.0| / 2.0 = 5.0  (500%)
```
The latch engages at 5× the base attention field — firmly outside the cold-start basin.

---

## Axiom 3 — Trajectory Analysis

```
bze_409: [2.0, 2.35, 3.21, 5.28, 6.77, 7.96, 9.35, 7.71, 10.63, 10.09,
          8.53, 12.69, 12.71, 12.75, 12.82, 12.91, 13.02, 13.15, 13.27, 13.40]
alpha:   [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5,
          0.5, 0.5, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9]
latch:   [0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
          0,   0,   1,   1,   1,   1,   1,   1,   1,   1  ]
lc_409:  [92, 106, 127, 113, 106, 106, 64, 106, 71, 64, 106, 71,
          71, 71, 71, 71, 71, 71, 71, 71]
```

**Phase 1 (n=0–11, discovery, α=0.5):** Identical to EXP-406 trajectory (same α). bze climbs from 2.0 through the bistable region; lc oscillates but trends toward lc=71.

**Phase 2 (n=12+, maintenance, α=0.9):** Latch engages at bze=12.69. lc fixes to 71 immediately and stays. bze converges monotonically toward lc=71 equilibrium (~17.19).

**Post-latch convergence rate:**
```
bze_{t+1} = 0.9·bze_t + 0.1·raw_t
raw at lc=71: ~13–15 (still ramping; γ_eff not fully saturated at N=20)

τ_conv = −1/ln(0.9) ≈ 9.5 steps to reach 63% of raw
bze_409[-1] = 13.40  (8 steps post-latch; approaching equilibrium)
```

**Comparison:**

| metric | EXP-406 | EXP-407 | EXP-408 | **EXP-409** |
|--------|---------|---------|---------|-------------|
| bze[-1] | 17.13 | 11.18 | 8.62 | **13.40** |
| tail_range | 9.17 | 2.71 | 0.93 | **4.87** |
| last5_range | 4.22 | 0.59 | 0.37 | **0.49** |
| lc_tail | {71,78} | {64,71,106} | {64} | **{71}** |
| overshoot | 1.033 | 1.008 | 1.099 | **1.000** |
| latch_step | — | — | — | **12** |

EXP-409 achieves: correct basin (lc=71), best overshoot (1.000), highest post-latch convergence, stable last-5 range.

---

## Axiom 4 — Ghost #20: Pre-Latch Discovery Variance

**Observation:** tail_range_409=4.87 includes steps n=10–11 (discovery phase: bze=8.53→12.69). After latch (n=12–19), range is only 13.40−12.71=0.69 — tighter than EXP-407.

The "tail" window (n=10–19) straddles the phase boundary at n=12. The pre-latch discovery steps contribute the majority of tail_range_409.

**Ghost #20 (formal):** `Gₜ = Zₜ − Π_W(Zₜ)`. Numeric residual S_A in discovery mode (n=10–11) retains lc=106/64 geometry from bistable traversal. This contributes high B_A values briefly before the latch, inflating tail_range. Not an error — it is the expected cost of discovery mode operating in the bistable region. Observable: `Δ_pre-latch = bze(n=11) − bze(n=10) = 12.69 − 8.53 = 4.16` (majority of tail variance).

**Post-latch variance:** `range(n=12..19) = 0.69` — 90% reduction vs full-tail metric.

---

## Axiom 5 — Dual Arithmetic Separation

`bze_ema_prev`, `maint_latched`, and `α_eff` are **primary-space scalars**: all caller-managed, none stored in MuState dual fields. The latch is a discontinuous function in primary space — a scalar Boolean operator on the primary scalar `bze_ema_prev`.

`S_A`, `S_D` are dual-space accumulators operating under the standard EMA protocol. The hysteresis operator couples dual→primary only via `B_A = ‖S_A‖/(‖Z_A‖+ε)` and `B_D = ‖S_D‖/(‖Z_A‖+ε)` — norm operations that preserve dual/primary orthogonality.

The latch condition `bze_ema_prev ≥ β_threshold` is a pure primary-space predicate: it reads only the previous EMA output, never the dual residual directly.

---

## Axiom 6 — P_yz Invariance

`phi_fb_hysteresis_ema` reads only `‖S_A‖`, `‖Z_A‖`, `‖S_D‖`, `scene_n`, `bze_ema_prev`, `maint_latched`. All P_yz-invariant (norms and scalars). Verified N=20:

```
max|β_Z_eff_fwd(n) − β_Z_eff_mir(n)| = 1.78e-15
max|B_A_fwd(n) − B_A_mir(n)|          = 8.88e-16
max|B_D_fwd(n) − B_D_mir(n)|          = 0.00e+00
leaf_count_fwd(n) = leaf_count_mir(n) for all n=0..19
latch_fwd(n) == latch_mir(n) for all n  (P_yz-symmetric latch)
```

---

## Verified Results

| Fork | Assertions | Result |
|------|-----------|--------|
| Fork A (`run_seed_exp409.py`) | 10/10 | **PASS** |
| Fork B (`run_p_invariance_exp409.py`) | 5/5 | **PASS** |

```
α_disc=0.5  α_maint=0.9  β_threshold=12.0
latch_step=12  bze_at_latch=12.71  maint_latched_final=True
bze_409[-1]=13.40 > bze_407[-1]=11.18 ✓
tail_range_409=4.87 < tail_range_406=9.17 ✓
last5_range_409=0.49  (post-latch: 0.69 over 8 steps)
overshoot=1.0000 (perfect)  lc_tail={71} (correct basin)
P_yz: max|bze_fwd−mir|=1.78e-15 ✓
```

---

## Ghost Notes

**Ghost #19 (resolved):** Attraktorwahl from EXP-408. Hysteresis latch prevents Attraktorwahl by holding discovery mode (α=0.5) until bze confirms the target basin (≥12.0), then locking maintenance (α=0.9) irreversibly. lc=71 stable from latch_step=12 onward.

**Ghost #20:** Pre-latch discovery variance. The tail window (n=10–19) includes 2 discovery steps where bze traverses the bistable region (8.53→12.69). These contribute tail_range=4.16 out of total 4.87. Post-latch range=0.69. Observable: `Δ_pre-latch = bze(latch_step) − min(bze_tail_pre_latch)`.

---

## EXP-410 Gate

**Trigger (proactive):** bze_409[-1]=13.40 still below EXP-406's 17.13 (post-latch convergence limited by α=0.9 time constant ≈ 9.5 steps). With only 8 post-latch steps in N=20, full convergence requires N≥25.

**Options:**
- A: Extend N from 20 to 30 — verify bze_409 reaches EXP-406 levels given enough steps
- B: Reduce α_maint from 0.9 to 0.75 after confirmed basin (bze > 15.0) — two-level maintenance
- C: Benchmark: characterize (latch_step, bze[-1]) as a function of β_threshold ∈ [10, 14]
- D: Close Series 400 Phi_fb sub-series; promote hysteresis as the canonical operator for EXP-410+ use
