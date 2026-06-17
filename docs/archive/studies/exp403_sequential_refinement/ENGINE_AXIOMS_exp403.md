# ENGINE_AXIOMS_exp403 — Sequential Scene Refinement

**Protocol:** exp403-v1  
**Inherits:** exp402-v1, exp401-v1, exp313-v1  
**Author:** Daniel J. Dillberg — bigdilly95@gmail.com  
**Declaration hash:** `b2cfdf2e16e1617e464aca7a9e773f1de2b74f507b48c821f818f1ddb438b626`  
**Status:** open

---

## Axiom 1 — Sequential EMA Inheritance

State variables `(S_A, S_C, S_D, S)` are carry-forward across top-level scene calls.

Let `μ⁰` be the initial state (cold start, all EMA fields zero).  
Let `μⁿ` be the terminal MuState output of call `n`.  
Call `n+1` is initialized with root claim `c_new` and inherited EMA:

```
μⁿ⁺¹_init = MuState(claim=c_new, S_A=μⁿ.S_A, S_C=μⁿ.S_C, S_D=μⁿ.S_D, S=μⁿ.S)
```

**Ghost #11:** All inherited arrays must be copied (`np.array(S_A_prev)`) to prevent aliasing between steps `n` and `n+1`.

**Ghost #12:** Step `n=0` is cold (`S_A=S_D=0`). Step `n≥1` inherits terminal EMA from step `n-1`. Initializing all steps cold breaks EMA continuity and renders the homeostasis loop inoperative.

---

## Axiom 2 — Phi_fb Reads Prior Scene Terminal State

Within each call to `apply_gamma_402_recursive`:

```
Phi_fb reads: S_A_prev = μⁿ_init.S_A  (= μⁿ⁻¹.S_A, inherited)
              S_D_prev = μⁿ_init.S_D  (= μⁿ⁻¹.S_D, inherited)
              Z_A_prev = μⁿ_init.Z()[0:4]  (= root claim stalk[0:4])

β_Z_eff(n) = max(β_min, β_base · (1 + γ_A · B_A(n−1) − γ_D · B_D(n−1)))
```

where:
```
B_A(n−1) = ‖S_A(n−1)‖ / (‖Z_A(n−1)‖ + ε)
B_D(n−1) = ‖S_D(n−1)‖ / (‖Z_A(n−1)‖ + ε)
```

**Temporal indexing:** φ_fb at step `n` uses `B_A(n−1)`, `B_D(n−1)` from the prior scene's terminal EMA.  
The first call (`n=0`) always has `B_A(−1) = B_D(−1) = 0` → `β_Z_eff(0) = β_Z_base`.

---

## Axiom 3 — Equilibrium Analysis

**Definition (equilibrium):** The system is at equilibrium when both EMA channels have stabilised:  
`‖S_A(n) − S_A(n−1)‖ < δ_A` and `‖S_D(n) − S_D(n−1)‖ < δ_D` for small `δ_A, δ_D`.

**Consequence:** At equilibrium, `B_A(n) ≈ B_A(n−1) = B_A*` and `B_D(n) ≈ B_D*`.

```
β_Z_eff* = β_Z_base · (1 + γ_A · B_A* − γ_D · B_D*)
```

**Symmetric case** (`γ_A = γ_D`): equilibrium does NOT require `B_A* = B_D*`.  
It requires the EMA channels to stabilise — which they do when the scene is stationary.

**Ghost #13 (architectural):** `B_A >> B_D` is scene-structural for position-rich inputs.  
Sector A+B ghost (position/mass/color) dominates Sector D ghost (log-Cholesky covariance) because:
- `G_A` is large: partition creates significant mass/color residuals
- `G_D` is small: `G_inject_D ∝ α_D · B̂⊗B̂ · τ_norm` with `α_D = 0.01`

For the seed scene: `B_A* ≈ 4.81`, `B_D* ≈ 0.0013`, `β_Z_eff* ≈ 6.81`.

**Gravitational backreaction** (Ω_fb): The fractional deviation of the effective field from base:
```
Ω_fb(n) = |β_Z_eff(n) − β_Z_base| / β_Z_base
Ω_fb(∞) = |γ_A · B_A* − γ_D · B_D*|  ≈ |0.5 · 4.81 − 0.5 · 0.001| ≈ 2.40
```

The Zeeman field is amplified by 240% from base at equilibrium for this scene — a large backreaction.

---

## Axiom 4 — EMA Decay and Saturation Gate

With stationary scene (fixed root stalk, fixed scene structure):

```
S_A(n) = α · S_A(n−1) + (1−α) · G_A(n)   →   converges to S_A* = G_A* / (1−α) · (1−α^n) → S_A∞
S_D(n) = α · S_D(n−1) + (1−α) · G_D(n)   →   converges to S_D* similarly
```

If `G_A(n)` is approximately constant across scenes:
```
S_A*(∞) = G_A / (1−α)       [geometric series limit]
```

**EMA decay when pre-injected:** If `S_D(0) >> G_D/(1−α)`:
```
‖S_D(n)‖ ≈ α^n · ‖S_D(0)‖ + G_D/(1−α) · (1−α^n)
```
Decays toward its natural steady-state from the injected initial value.

**Saturation gate:**
```
saturation_ratio = count(β_Z_eff(n) == β_Z_min) / N_steps
```
- If `saturation_ratio > 0.5`: exponential `φ_fb` proposed (EXP-404 gate)
- Standard params (`γ_A=γ_D=0.5`, seed scene): `saturation_ratio = 0.0` (B_D too small to saturate)
- Forced params (`γ_D=2.0`, `S_D_init=[2]*6`, norm≈4.90): `saturation_ratio = 0.60 ≥ 0.5`

**Saturation condition:** `B_D > (1 − β_min/β_base) / γ_D = (1 − 0.25) / γ_D = 0.75 / γ_D`

---

## Axiom 5 — P_yz Invariance Across Sequential Steps

P_yz reflection: `R = diag(−1, 1, 1)` applied to Sector B (stalk[4]).

Under P_yz, for all `n`:
```
β_Z_eff_fwd(n) = β_Z_eff_mir(n)         [phi_fb P_yz-invariant]
B_A_fwd(n) = B_A_mir(n)                  [S_A norm P_yz-invariant]
B_D_fwd(n) = B_D_mir(n)                  [S_D norm P_yz-invariant]
leaf_count_fwd(n) = leaf_count_mir(n)    [expansion P_yz-symmetric]
```

Verified: `max |β_Z_eff_fwd(n) − β_Z_eff_mir(n)| = 2.66e−15` (floating point noise).

---

## Verified Results

| Fork | Assertions | Result |
|------|-----------|--------|
| Fork A (`run_seed_exp403.py`) | 10/10 | **PASS** |
| Fork B (`run_p_invariance_exp403.py`) | 5/5 | **PASS** |

```
Standard run (N=20, γ_A=γ_D=0.5):
  β_Z_eff trajectory: [2.000, 5.303, 7.139, 6.813, ..., 6.809]  (converged)
  B_A trajectory:     [0.000, 3.303, 5.140, 4.813, ..., 4.811]  (converged)
  B_D trajectory:     [0.000, 0.000, 0.000, 0.001, ..., 0.001]  (converging)
  leaf_count:         [92, 113, 106, 106, ..., 106]  (stable from n=3)
  saturation_ratio:   0.0000  (EXP-404 gate inactive)
  Ω_fb(∞):           2.4047  (240% backreaction from base)

Forced saturation (S_D_init=[2]*6, γ_A=0, γ_D=2.0):
  saturation_ratio:   0.6000  (EXP-404 gate fires ✓)

P_yz invariance (Fork B):
  max |β_Z_eff_fwd − β_Z_eff_mir|: 2.66e-15  ✓
  max |B_A_fwd − B_A_mir|:          2.66e-15  ✓
  max |B_D_fwd − B_D_mir|:          0.00e+00  ✓
```

---

## Ghost Notes

**Ghost #11:** `np.array(S_A_prev)` copy required on inheritance — reference aliasing between step `n` and step `n+1` would cause in-place mutation of the prior scene's EMA state when the new scene's EMA is updated.

**Ghost #12:** Cold-start (`n=0`) vs. warm-start (`n≥1`) — phi_fb is inoperative at `n=0` by construction (zero EMA inputs). This is correct. Initializing all steps cold (forgetting EMA) would mask the homeostasis effect and is a protocol violation.

**Ghost #13:** `B_A >> B_D` (4.81 vs. 0.001) is scene-structural. Not a defect. Sector A+B ghosts are large because octree partition residuals in position space are large. Sector D ghosts are small because `α_D = 0.01` limits the covariance injection rate. The "equilibrium" is EMA channel stabilisation, not `B_A = B_D`.

---

## EXP-404 Gate

**Trigger:** `saturation_ratio > 0.5` in a production run.

**Proposed change:** Replace linear `φ_fb` with exponential:
```
β_Z_eff_exp = β_Z_base · exp(γ_A · B_A − γ_D · B_D)
```
Properties:
- Always positive (no floor needed)
- At equilibrium (`B_A = B_D`, `γ_A = γ_D`): `β_Z_eff_exp = β_Z_base · exp(0) = β_Z_base`
- Fixed point is `β_Z_base` (not shifted by scene B_A/B_D imbalance)
- Linearisation: `exp(x) ≈ 1 + x` for small `x` → reduces to EXP-402 linear form

**Dual arithmetic note:** exponential parameterisation preserves dual arithmetic separation (S_A, S_D remain in dual space; β_Z_eff remains in primary operator space). No new coupling introduced.
