"""
run_seed_exp404.py — Fork A: EXP-404 Exponential Phi_fb

Protocol: exp404-v1
Inherits: exp403-v1, exp402-v1, exp401-v1
declaration_hash: e7447ec6a65022a25d426a8f0b796ef18292d6cf3f85047c2239b004d225e67c

Gate: EXP-403 Fork A [10] forced sat_ratio=0.60 > 0.50 -> EXP-404 triggered.

phi_fb_exp: beta_Z_eff = max(beta_Z_min_exp, beta_Z_base * exp(gamma_A*B_A - gamma_D*B_D))

Ghost #14: exp(gamma_A * B_A*) with B_A*=4.81 -> exp(0.5*4.81)=11.07 -> beta_Z_eff*~22.
           Monitor leaf_count under exponential regime (higher than EXP-402).

Math verification:
  Fixed point:     gamma_A*B_A* = gamma_D*B_D* -> beta_Z_eff* = beta_Z_base
  Linearisation:   exp(x) = 1 + x + O(x^2) -> phi_fb_exp ~ phi_fb for |x|<<1
  Saturation floor: ln(beta_Z_base/beta_Z_min_exp) = ln(20) ~ 3.0
                    (vs linear: (1-0.25)/0.5 = 1.5)

Tests [1-10]:
  [1]  declaration_hash
  [2]  phi_fb_exp(B_A=0, B_D=0) == beta_Z_base (neutral: exp(0)=1)
  [3]  phi_fb_exp(B_A>0, B_D=0) > beta_Z_base (amplification monotone)
  [4]  phi_fb_exp(B_A=0, B_D>0) in (0, beta_Z_base) (pullback, strictly positive)
  [5]  phi_fb_exp >= beta_Z_min_exp always (floor holds)
  [6]  linearisation: |phi_fb_exp - phi_fb| < 0.01 for |gamma*B| < 0.05
  [7]  EXP-401 regression: 92 leaves at cold start
  [8]  sequential N=20 forced (gamma_D=2.0, S_D=[2]*6): sat_ratio_exp < sat_ratio_linear=0.60
  [9]  sequential N=20 standard: beta_Z_eff*_exp > beta_Z_eff*_linear (Ghost #14 amplification)
  [10] gradient monotonicity: phi_fb_exp increasing in B_A, decreasing in B_D
"""
import sys, os, json, hashlib
import numpy as np
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_404_recursive, apply_gamma_402_recursive,
    phi_fb_exp, phi_fb,
    _GAMMA_FB_A_404, _GAMMA_FB_D_404, _BETA_Z_MIN_404,
    _GAMMA_FB_A_402, _GAMMA_FB_D_402, _BETA_Z_MIN_402,
    _ALPHA_D_401, _BETA_Z_313, SECTOR_C_KAPPA_DIM,
)
from engine.validity import kappa_integral

DECL_HASH = "e7447ec6a65022a25d426a8f0b796ef18292d6cf3f85047c2239b004d225e67c"
DECL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "studies/exp404_exp_phi_fb/SEED_DECLARATION_exp404.json")

with open(DECL_PATH) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
canon  = json.dumps(decl, sort_keys=True, separators=(",", ":"))
computed = hashlib.sha256(canon.encode()).hexdigest()
assert stored == DECL_HASH and computed == DECL_HASH
print(f"[1] PASS  declaration_hash = {DECL_HASH[:16]}...")

# ── Geometry ───────────────────────────────────────────────────────────────────
bbox       = (np.zeros(3), np.ones(3))
kappa_seed = kappa_integral(bbox)
stalk18    = np.array([1., 1., 1., 1.,
                       0.5, 0.5, 0.5, 1.,
                       0.6, 0., 0.8, kappa_seed,
                       0., 0., 0., 0., 0., 0.])
B_field    = np.array([1.0, 0.5, 0.3])
J_AC       = np.eye(4)
W_MAX      = 8
K_BUD      = 2048

SHARED_404 = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0,
                  K_budget=K_BUD, depth=0, focal_point=np.array([0.5, 0.5, 0.5]),
                  B=B_field, J_AC=J_AC, W_max=W_MAX,
                  beta_Z_base=_BETA_Z_313,
                  gamma_fb_A=_GAMMA_FB_A_404, gamma_fb_D=_GAMMA_FB_D_404,
                  beta_Z_min=_BETA_Z_MIN_404)

SHARED_402 = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0,
                  K_budget=K_BUD, depth=0, focal_point=np.array([0.5, 0.5, 0.5]),
                  B=B_field, J_AC=J_AC, W_max=W_MAX,
                  beta_Z_base=_BETA_Z_313,
                  gamma_fb_A=_GAMMA_FB_A_402, gamma_fb_D=_GAMMA_FB_D_402)


def make_mu(S_A_init=None, S_C_init=None, S_D_init=None, S_init=None):
    prov  = Provenance(parent_ids=(), operator_id="seed_exp404", timestamp=now_iso())
    claim = Claim(provenance=prov, payload="scene:exp404:root",
                  stalk=stalk18.copy(), t=0, bbox=bbox)
    return MuState(
        t=0, claims={claim.id: claim}, entailments={},
        active=frozenset([claim.id]),
        S=np.array(S_init, dtype=float)   if S_init   is not None else np.zeros(12),
        alpha=ALPHA,
        S_A=np.array(S_A_init, dtype=float) if S_A_init is not None else np.zeros(8),
        S_C=np.array(S_C_init, dtype=float) if S_C_init is not None else np.zeros(4),
        S_D=np.array(S_D_init, dtype=float) if S_D_init is not None else np.zeros(6),
    )


# ── [2] Neutral: phi_fb_exp(B_A=0, B_D=0) == beta_Z_base ─────────────────────
bze_neutral, _, _ = phi_fb_exp(np.zeros(8), np.ones(4), np.zeros(6))
assert abs(bze_neutral - _BETA_Z_313) < 1e-10, \
    f"[2] FAIL: neutral bze={bze_neutral:.8f} != beta_Z_base={_BETA_Z_313}"
print(f"[2] PASS  phi_fb_exp neutral = {bze_neutral:.6f} == beta_Z_base (exp(0)=1)")

# ── [3] Amplification: phi_fb_exp(B_A>0, B_D=0) > beta_Z_base ────────────────
S_A_test = np.array([0.1, 0.05, 0.0, 0.03, 0., 0., 0., 0.])
Z_A_test = np.array([1., 1., 1., 1.])
bze_amp, B_A_amp, _ = phi_fb_exp(S_A_test, Z_A_test, np.zeros(6))
assert bze_amp > _BETA_Z_313, f"[3] FAIL: amplify bze={bze_amp:.6f} <= beta_Z_base"
print(f"[3] PASS  phi_fb_exp amplify: B_A={B_A_amp:.4f} -> bze={bze_amp:.6f} > {_BETA_Z_313}")

# ── [4] Pullback: phi_fb_exp(B_A=0, B_D>0) in (0, beta_Z_base) ───────────────
S_D_test = np.array([0., 0., 0., 0.1, 0.05, 0.03])
bze_pull, _, B_D_pull = phi_fb_exp(np.zeros(8), Z_A_test, S_D_test)
assert 0 < bze_pull < _BETA_Z_313, \
    f"[4] FAIL: pullback bze={bze_pull:.8f} not in (0, {_BETA_Z_313})"
print(f"[4] PASS  phi_fb_exp pullback: B_D={B_D_pull:.4f} -> bze={bze_pull:.6f} in (0, {_BETA_Z_313})")

# ── [5] Floor: phi_fb_exp >= beta_Z_min_exp always ────────────────────────────
S_D_huge = np.full(6, 100.0)
bze_floor, _, _ = phi_fb_exp(np.zeros(8), np.ones(4) * 0.01, S_D_huge)
assert bze_floor >= _BETA_Z_MIN_404 - 1e-12, \
    f"[5] FAIL: floor bze={bze_floor:.10f} < beta_Z_min_exp={_BETA_Z_MIN_404}"
raw_exp = _BETA_Z_313 * math.exp(-0.5 * np.linalg.norm(S_D_huge) / (0.01 * 4 + 1e-15))
print(f"[5] PASS  phi_fb_exp floor: huge B_D -> bze={bze_floor:.8f} >= {_BETA_Z_MIN_404} "
      f"(raw_exp={raw_exp:.2e} -> clamped)")

# ── [6] Linearisation: |phi_fb_exp - phi_fb| < 0.01 for |gamma*B| < 0.05 ─────
# At small ghost ratios both should agree to O(x^2).
S_A_small = np.array([0.01, 0., 0., 0., 0., 0., 0., 0.])  # B_A ~ 0.005
bze_exp_sm, _, _ = phi_fb_exp(S_A_small, Z_A_test, np.zeros(6))
bze_lin_sm, _, _ = phi_fb(S_A_small, Z_A_test, np.zeros(6),
                           gamma_fb_A=_GAMMA_FB_A_402, gamma_fb_D=_GAMMA_FB_D_402)
lin_diff = abs(bze_exp_sm - bze_lin_sm)
assert lin_diff < 0.01, f"[6] FAIL: linearisation diff={lin_diff:.6f} >= 0.01"
print(f"[6] PASS  linearisation: |phi_fb_exp - phi_fb| = {lin_diff:.2e} < 0.01 (small ghost regime)")

# ── [7] EXP-401 regression: 92 leaves at cold start ──────────────────────────
mu0 = make_mu()
cid0 = next(iter(mu0.active))
mu_out0, _, _, bze0, _, _ = apply_gamma_404_recursive(mu=mu0, claim_id=cid0, **SHARED_404)
assert len(mu_out0.active) == 92, f"[7] FAIL: leaf_count={len(mu_out0.active)} != 92"
assert abs(bze0 - _BETA_Z_313) < 1e-10, f"[7] FAIL: cold bze={bze0:.8f} != {_BETA_Z_313}"
print(f"[7] PASS  cold start: leaf_count={len(mu_out0.active)}, bze={bze0:.6f}==beta_Z_base")

# ── [8] Forced saturation: EXP-404 sat_ratio < EXP-402 sat_ratio=0.60 ────────
N_STEPS = 20
S_D_forced = np.full(6, 2.0)

# EXP-404 forced run
sat_404 = 0
mu_f404 = make_mu(S_D_init=S_D_forced)
FORCED_404 = dict(SHARED_404); FORCED_404['gamma_fb_A'] = 0.0; FORCED_404['gamma_fb_D'] = 2.0
for n in range(N_STEPS):
    if n > 0:
        mu_f404 = make_mu(S_A_init=mu_f404.S_A, S_C_init=mu_f404.S_C,
                          S_D_init=mu_f404.S_D, S_init=mu_f404.S)
    cid_f = next(iter(mu_f404.active))
    mu_f404, _, _, bze_f404, _, _ = apply_gamma_404_recursive(
        mu=mu_f404, claim_id=cid_f, **FORCED_404)
    if abs(bze_f404 - _BETA_Z_MIN_404) < 1e-10:
        sat_404 += 1
sat_ratio_404 = sat_404 / N_STEPS
sat_ratio_402 = 0.60  # known from EXP-403 Fork A [10]

print(f"\n  Forced saturation comparison (gamma_D=2.0, S_D=[2]*6, N={N_STEPS}):")
print(f"  EXP-402 (linear, beta_Z_min=0.5): sat_ratio={sat_ratio_402:.4f}")
print(f"  EXP-404 (exp,    beta_Z_min=0.1): sat_ratio={sat_ratio_404:.4f}")

assert sat_ratio_404 < sat_ratio_402, \
    f"[8] FAIL: sat_ratio_404={sat_ratio_404:.4f} >= sat_ratio_402={sat_ratio_402:.4f}"
print(f"[8] PASS  EXP-404 sat_ratio={sat_ratio_404:.4f} < EXP-402 sat_ratio={sat_ratio_402:.4f} (resolved)")

# ── [9] Standard warmup: beta_Z_eff*_exp > beta_Z_eff*_linear ────────────────
# Ghost #14: exp amplification with B_A*=4.81 -> bze*~22 vs linear bze*=6.81
bze_traj_404, bze_traj_402 = [], []
mu_404 = make_mu(); mu_402 = make_mu()

for n in range(N_STEPS):
    if n > 0:
        mu_404 = make_mu(S_A_init=mu_404.S_A, S_C_init=mu_404.S_C,
                         S_D_init=mu_404.S_D, S_init=mu_404.S)
        mu_402 = make_mu(S_A_init=mu_402.S_A, S_C_init=mu_402.S_C,
                         S_D_init=mu_402.S_D, S_init=mu_402.S)
    cid_4 = next(iter(mu_404.active)); cid_2 = next(iter(mu_402.active))
    mu_404, _, _, bze4, _, _ = apply_gamma_404_recursive(mu=mu_404, claim_id=cid_4, **SHARED_404)
    mu_402, _, _, bze2, _, _ = apply_gamma_402_recursive(mu=mu_402, claim_id=cid_2, **SHARED_402)
    bze_traj_404.append(bze4); bze_traj_402.append(bze2)

bze_final_404 = bze_traj_404[-1]; bze_final_402 = bze_traj_402[-1]
lc_final_404  = len(mu_404.active); lc_final_402  = len(mu_402.active)

print(f"\n  Standard warmup N={N_STEPS}:")
print(f"  EXP-404 bze*={bze_final_404:.4f}  leaf_count*={lc_final_404}")
print(f"  EXP-402 bze*={bze_final_402:.4f}  leaf_count*={lc_final_402}")
print(f"  bze_traj_404: {[round(b,2) for b in bze_traj_404]}")

assert bze_final_404 > bze_final_402, \
    f"[9] FAIL: bze*_404={bze_final_404:.4f} <= bze*_402={bze_final_402:.4f}"
print(f"[9] PASS  EXP-404 bze*={bze_final_404:.4f} > EXP-402 bze*={bze_final_402:.4f} (Ghost #14 exp amplification)")

# ── [10] Gradient monotonicity ─────────────────────────────────────────────────
B_vals = [0.0, 0.1, 0.5, 1.0, 2.0, 5.0]
# Monotone increasing in B_A
bze_BA = [phi_fb_exp(np.full(8, b/np.sqrt(8)), Z_A_test, np.zeros(6))[0] for b in B_vals]
assert all(bze_BA[i] <= bze_BA[i+1] for i in range(len(bze_BA)-1)), \
    f"[10] FAIL: phi_fb_exp not monotone in B_A: {bze_BA}"
# Monotone decreasing in B_D
bze_BD = [phi_fb_exp(np.zeros(8), Z_A_test, np.full(6, b/np.sqrt(6)))[0] for b in B_vals]
assert all(bze_BD[i] >= bze_BD[i+1] for i in range(len(bze_BD)-1)), \
    f"[10] FAIL: phi_fb_exp not monotone (decreasing) in B_D: {bze_BD}"
print(f"[10] PASS  gradient monotonicity: B_A increase -> bze {[round(b,3) for b in bze_BA]}; "
      f"B_D increase -> bze {[round(b,3) for b in bze_BD]}")

print(f"\n=== EXP-404 Fork A: 10/10 PASS ===")
print(f"    phi_fb_exp neutral = {bze_neutral:.6f}")
print(f"    sat_ratio_404 (forced)   = {sat_ratio_404:.4f}  (vs 402: {sat_ratio_402:.4f})")
print(f"    beta_Z_eff* 404={bze_final_404:.4f}  402={bze_final_402:.4f}  leaf* 404={lc_final_404}  402={lc_final_402}")
print(f"    Ghost #14: exp amplification {bze_final_404/bze_final_402:.2f}x over linear at equilibrium")
