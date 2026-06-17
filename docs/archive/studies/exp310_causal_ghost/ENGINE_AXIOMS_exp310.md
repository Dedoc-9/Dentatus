# ENGINE AXIOMS -- EXP-310 Causal Ghost (Series 300, tenth study)

**Preregistration status**: GATE LOCKED
**Protocol version**: exp310-v1
**Inherits from**: exp309-v1 -> exp308-v1 -> ... -> exp301-v1
**Workspace**: Reality_Engine/studies/exp310_causal_ghost/
**declaration_hash**: `767cd60f165a131d8ad738c2256c0654961d31a7e193d4bb1cc0318dcd9b3666`

---

## 0. Motivation

EXP-309 introduced the SPRT LOD observer and ghost quarantine. Open limits logged:

**E-309-001 (S_C quarantine unobservable)**: For lossless operators G_C = 0 → S_C = 0
always. The quarantine architecture is structurally correct but produces no observable signal
under current operators.

**E-309-002 (η_AC static)**: η_AC = cosine_similarity(λ_A, λ_C) measures coefficient
alignment at one instant. It cannot distinguish whether S_A drives S_C or vice versa.

**E-308-003 (inherited)**: eta_AC measures coefficient alignment, not information flow.

EXP-310 replaces η_AC with Transfer Entropy (TE), a nonparametric directed MI estimate
that measures causal information flow from S_A ghost to S_C ghost and vice versa.

---

## 1. Mathematical Framework

### 1.1 Transfer Entropy (Schreiber 2000)

    T_{A->C}(t,W) = I(c_t ; a_{t-1} | c_{t-1})

where:
    a_t = ||S_A_t||_2    (scalar ghost magnitude, Sector A+B)
    c_t = ||S_C_t||_2    (scalar ghost magnitude, Sector C)

Equivalent decomposition via chain rule:

    T_{A->C} = I(c_t ; [a_{t-1}, c_{t-1}]) - I(c_t ; c_{t-1})

Physical interpretation: T_{A->C} is the reduction in uncertainty about c_t given
knowledge of a_{t-1}, beyond what c_{t-1} already provides. Nonzero iff S_A causally
influences S_C at lag 1.

### 1.2 Gravitational Backreaction Analogy

In linearized GR, the geometric perturbation h_μν backreacts on T_μν:

    δT_μν^{(2)} = -(1/8πG) δG_μν^{(2)}[h]

The two-way coupling generates second-order corrections to both sides. Here, S_C
(curvature/geometry) and S_A (mass/energy) are coupled through the shared claim DAG.
Transfer entropy measures the information-theoretic backreaction:

    delta_T_AC = T_{A->C} - T_{C->A}

delta_T_AC > 0: mass ghost leads  (S_A -> S_C, mass drives curvature residual)
delta_T_AC < 0: curvature ghost leads (S_C -> S_A, geometry backreacts on mass)
delta_T_AC = 0: symmetric coupling or decoupled

### 1.3 KSG Estimator (Kraskov et al. 2004, Algorithm 1)

For I(X ; Y) with X, Y scalar, N samples:

    I_KSG(X;Y) = psi(k) - < psi(n_X+1) + psi(n_Y+1) > + psi(N)

where:
    k     = 5 (fixed, preregistered)
    eps_i = kth-neighbor Chebyshev distance in joint (X,Y) space for point i
    n_X   = |{j : |X_j - X_i| <= eps_i}| - 1   (marginal count, L-inf)
    n_Y   = |{j : |Y_j - Y_i| <= eps_i}| - 1
    psi   = digamma function

TE via conditional MI decomposition:

    T_{A->C} = I_KSG(c_now ; [a_prev, c_prev]) - I_KSG(c_now ; c_prev)

### 1.4 Accuracy Characterization

AR(1) ground truth: a_t ~ N(0,1), c_t = gamma * a_{t-1} + N(0,1), gamma=0.5
True T_{a->c} = 0.5 * ln(1 + gamma^2) = 0.5 * ln(1.25) = 0.111572 nats

Verified: KSG estimate at N=1998 gives 5.9% error. Sign of delta_T_AC correct at N>=32.
KSG magnitude is biased ~20-50% at small N (W=32). Sign is the reliable statistic.

### 1.5 Normalization

    T_norm = T_{A->C} / H_KSG(c_t | c_{t-1})    in [0, 1]

H_KSG(c_t | c_{t-1}) = H_KSG(c_now, c_prev) - H_KSG(c_prev) estimated via KSG entropy.
Returns NaN if H_KSG(c_t | c_{t-1}) < eps (degenerate: S_C frozen or zero).

---

## 2. State Extension

### 2.1 Ghost History Buffer

New field on MuState (not included in H_t hash):

    ghost_history: deque(maxlen=32) of (||S_A_t||, ||S_C_t||) pairs

Updated after each sealed state. Circular buffer; oldest entry dropped when full.

### 2.2 Observable Computation

    te_A_to_C(mu) -> float | nan    (requires len(ghost_history) >= 32)
    te_C_to_A(mu) -> float | nan
    delta_T_AC(mu) -> float | nan   = te_A_to_C - te_C_to_A
    T_norm(mu) -> float | nan

Observables are pure numeric outputs. No interpretation, no causal attribution in
observable values themselves. Observable purity is satisfied.

---

## 3. Validity Class Predictions (preregistered)

| Regime | T_{A->C} | T_{C->A} | delta_T_AC |
|--------|----------|----------|------------|
| FULL_VALID lossless | ~0 | ~0 | ~0 (S_A=S_C=0, degenerate distribution) |
| LOD_RELAXED kappa bypass | suppressed | ~0 | delta < 0 or ~0 (S_C frozen, no c_t variation) |
| Non-lossless operator | >0 | variable | sign encodes causal lead |

---

## 4. Operator Pipeline (unchanged)

    mu -> Ltau -> Btau -> Rtau -> Z -> S -> W -> OBS

No new operators. TE is an observable computed post-pipeline from ghost_history.
Ghost history update is append-only; no retroactive modification.

---

## 5. Fork Structure

**Fork A** (`run_seed_exp310.py`):
  1. KSG ground truth verification: AR(1) synthetic data, N=2000, confirm TE sign correct.
  2. Lossless engine: accumulate ghost_history over recursive EXP-309 expansion.
     Verify T ~ 0 both directions (degenerate case: S_A = S_C = 0 always).
  3. Injected ghost test: manually set S_A/S_C sequences with known AR(1) structure.
     Verify KSG recovers correct causal direction.

**Fork B** (`run_p_invariance_exp310.py`):
  1. P_yz invariance of TE: T_{A->C}(fwd) == T_{A->C}(mirror) (both see same ||S|| magnitudes).
  2. LOD_RELAXED suppression: T_{A->C} drops when S_C frozen (kappa bypass active).

---

## 6. Known Limits

| limit | description | resolution |
|-------|-------------|------------|
| Degenerate lossless | S_A=S_C=0 -> TE undefined; estimator returns ~0 by construction | EXP-311: non-lossless operator |
| Small N bias | KSG TE magnitude biased ~50% at N=W=32 | Use sign(delta_T_AC); increase W for magnitude |
| Lag-1 Markov | Captures only first-order causal lag | EXP-311: multi-lag TE |
| Scalar projection | ||S_A|| and ||S_C|| lose directional info | EXP-311: vector TE with PCA |
| ghost_history not hashed | Not part of H_t; cannot revert to exact history | By design: history is auxiliary |

---

## 7. Commitment Chain

EXP-301 -> EXP-302 -> EXP-303 -> EXP-304 -> EXP-305 -> EXP-306 -> EXP-307 ->
EXP-308 -> EXP-309 ->
**EXP-310 (Transfer Entropy; delta_T_AC causal direction; KSG estimator; ghost history buffer)**
