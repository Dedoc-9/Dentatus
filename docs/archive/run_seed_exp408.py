"""
run_seed_exp408.py — Fork A: EXP-408 Ascending α_bze Schedule (Bootstrap to Maintenance)

Protocol: exp408-v1
Declaration hash: d1945e6736a284a33cf648ac0d7d06491e0bea704bd6fa69ca7beac277562055

phi_fb_ascending_ema: α ramps UP (loose→tight).
  alpha_eff(n) = alpha_max - (alpha_max - alpha_min)*exp(-n/tau_alpha)
  gamma_eff(n) = gamma_inf * (1 - exp(-n/tau_warmup))   [unchanged]

tau_alpha=2.0  DECOUPLED from  tau_warmup=5.0
  alpha_crit=0.667: crossed at n≈2.2 (before bistable at n≈4)
  alpha_min=0.2: fast bootstrap (80% responsiveness at n=0)
  alpha_max=0.9: maintenance lock (5.3% 2-cycle ratio at equilibrium)

2-cycle damping ratio = (1-alpha_eff)/(1+alpha_eff):
  n=0:   alpha=0.200 -> ratio=0.667  (loose; safe: raw≈beta_Z_base)
  n=2.2: alpha=0.667 -> ratio=0.200  (crosses alpha_crit)
  n=5:   alpha=0.843 -> ratio=0.086
  n=inf: alpha=0.900 -> ratio=0.053  (maintenance: tightest damping)

Tests [1-10]:
  [1]  declaration_hash
  [2]  cold start: bze=base; alpha_eff(0)==alpha_min
  [3]  n=1: bze_408 > bze_407 (ascending more responsive at boot)
  [4]  n=100: alpha_eff -> alpha_max (maintenance lock)
  [5]  last5_range_408 < last5_range_407 (better tail stability; Ghost #19 documented)
  [6]  tail_range_408 < tail_range_406=9.17 (2-cycle suppressed by alpha_max=0.9)
  [7]  lc_408_tail bounded [30, 200]
  [8]  saturation_ratio_408 < 0.5
  [9]  overshoot_408 < overshoot_404=1.33
  [10] gradient monotone: phi_fb_ascending_ema increasing B_A, decreasing B_D
"""
import sys, os, json, hashlib
import numpy as np
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_408_recursive, apply_gamma_407_recursive, apply_gamma_406_recursive,
    phi_fb_ascending_ema,
    _GAMMA_INF_A_408, _GAMMA_INF_D_408, _TAU_WARMUP_408,
    _ALPHA_MIN_408, _ALPHA_MAX_408, _TAU_ALPHA_408, _BETA_Z_MIN_408,
    _GAMMA_INF_A_407, _GAMMA_INF_D_407, _TAU_WARMUP_407,
    _ALPHA_MAX_407, _ALPHA_MIN_407, _TAU_ALPHA_407, _BETA_Z_MIN_407,
    _GAMMA_INF_A_406, _GAMMA_INF_D_406, _TAU_WARMUP_406,
    _ALPHA_BZE_406, _BETA_Z_MIN_406,
    _BETA_Z_313,
)
from engine.validity import kappa_integral

DECL_HASH = "d1945e6736a284a33cf648ac0d7d06491e0bea704bd6fa69ca7beac277562055"
DECL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "studies/exp408_ascending_alpha/SEED_DECLARATION_exp408.json")

with open(DECL_PATH) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
canon  = json.dumps(decl, sort_keys=True, separators=(",", ":"))
computed = hashlib.sha256(canon.encode()).hexdigest()
assert stored == DECL_HASH and computed == DECL_HASH
print(f"[1] PASS  declaration_hash = {DECL_HASH[:16]}...")

bbox       = (np.zeros(3), np.ones(3))
kappa_seed = kappa_integral(bbox)
stalk18    = np.array([1.,1.,1.,1., 0.5,0.5,0.5,1., 0.6,0.,0.8,kappa_seed,
                       0.,0.,0.,0.,0.,0.])
B_field    = np.array([1.0, 0.5, 0.3])
J_AC       = np.eye(4)
W_MAX      = 8
K_BUD      = 2048

SHARED_408 = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0,
                  K_budget=K_BUD, depth=0, focal_point=np.array([0.5,0.5,0.5]),
                  B=B_field, J_AC=J_AC, W_max=W_MAX, beta_Z_base=_BETA_Z_313,
                  gamma_inf_A=_GAMMA_INF_A_408, gamma_inf_D=_GAMMA_INF_D_408,
                  tau_warmup=_TAU_WARMUP_408,
                  alpha_min=_ALPHA_MIN_408, alpha_max=_ALPHA_MAX_408,
                  tau_alpha=_TAU_ALPHA_408, beta_Z_min=_BETA_Z_MIN_408)

SHARED_407 = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0,
                  K_budget=K_BUD, depth=0, focal_point=np.array([0.5,0.5,0.5]),
                  B=B_field, J_AC=J_AC, W_max=W_MAX, beta_Z_base=_BETA_Z_313,
                  gamma_inf_A=_GAMMA_INF_A_407, gamma_inf_D=_GAMMA_INF_D_407,
                  tau_warmup=_TAU_WARMUP_407,
                  alpha_max=_ALPHA_MAX_407, alpha_min=_ALPHA_MIN_407,
                  tau_alpha=_TAU_ALPHA_407, beta_Z_min=_BETA_Z_MIN_407)

SHARED_406 = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0,
                  K_budget=K_BUD, depth=0, focal_point=np.array([0.5,0.5,0.5]),
                  B=B_field, J_AC=J_AC, W_max=W_MAX, beta_Z_base=_BETA_Z_313,
                  gamma_inf_A=_GAMMA_INF_A_406, gamma_inf_D=_GAMMA_INF_D_406,
                  tau_warmup=_TAU_WARMUP_406, alpha_bze=_ALPHA_BZE_406,
                  beta_Z_min=_BETA_Z_MIN_406)


def make_mu(S_A_init=None, S_C_init=None, S_D_init=None, S_init=None):
    prov  = Provenance(parent_ids=(), operator_id="seed_exp408", timestamp=now_iso())
    claim = Claim(provenance=prov, payload="scene:exp408:root",
                  stalk=stalk18.copy(), t=0, bbox=bbox)
    return MuState(
        t=0, claims={claim.id: claim}, entailments={},
        active=frozenset([claim.id]),
        S=np.array(S_init,   dtype=float) if S_init   is not None else np.zeros(12),
        alpha=ALPHA,
        S_A=np.array(S_A_init, dtype=float) if S_A_init is not None else np.zeros(8),
        S_C=np.array(S_C_init, dtype=float) if S_C_init is not None else np.zeros(4),
        S_D=np.array(S_D_init, dtype=float) if S_D_init is not None else np.zeros(6),
    )


# ── [2] Cold start: alpha_eff(0) == alpha_min ──────────────────────────────
bze_n0, _, _, _, _, _, a_n0 = phi_fb_ascending_ema(
    np.zeros(8), np.ones(4), np.zeros(6),
    scene_n=0, bze_ema_prev=_BETA_Z_313)
assert abs(bze_n0 - _BETA_Z_313) < 1e-10, f"[2] FAIL: bze={bze_n0}"
assert abs(a_n0 - _ALPHA_MIN_408) < 1e-10, f"[2] FAIL: alpha_eff(0)={a_n0} != alpha_min={_ALPHA_MIN_408}"
print(f"[2] PASS  n=0: bze={bze_n0:.4f}==base  alpha_eff={a_n0:.4f}==alpha_min={_ALPHA_MIN_408}")

# ── [3] n=1: ascending more responsive than descending (EXP-407) ───────────
from engine.operators import phi_fb_adaptive_ema
S_A_t = np.array([0.1]*4 + [0.]*4); Z_A_t = np.ones(4)
bze408_n1, _, _, _, _, _, a408_1 = phi_fb_ascending_ema(
    S_A_t, Z_A_t, np.zeros(6), scene_n=1, bze_ema_prev=_BETA_Z_313)
bze407_n1, _, _, _, _, _, a407_1 = phi_fb_adaptive_ema(
    S_A_t, Z_A_t, np.zeros(6), scene_n=1, bze_ema_prev=_BETA_Z_313)
assert bze408_n1 >= bze407_n1 - 1e-10, \
    f"[3] FAIL: bze408={bze408_n1:.6f} < bze407={bze407_n1:.6f} (less responsive at n=1)"
print(f"[3] PASS  n=1: alpha_408={a408_1:.4f} < alpha_407={a407_1:.4f} -> "
      f"bze408={bze408_n1:.4f} >= bze407={bze407_n1:.4f}")

# ── [4] n=100: alpha_eff -> alpha_max ─────────────────────────────────────
from engine.operators import phi_fb_exp
S_A_lg = np.array([1.]*4 + [0.]*4)
bze_exp, *_ = phi_fb_exp(S_A_lg, Z_A_t, np.zeros(6))
bze408_100, raw408_100, _, _, _, _, a100 = phi_fb_ascending_ema(
    S_A_lg, Z_A_t, np.zeros(6), scene_n=100, bze_ema_prev=bze_exp)
assert abs(a100 - _ALPHA_MAX_408) < 0.01, f"[4] FAIL: alpha_eff(100)={a100:.4f} != alpha_max"
print(f"[4] PASS  n=100: alpha_eff={a100:.4f}~alpha_max={_ALPHA_MAX_408}  "
      f"bze408={bze408_100:.4f}~bze_exp={bze_exp:.4f}")

# ── Sequential N=20 ────────────────────────────────────────────────────────
N_STEPS = 20
bze_408_traj, bze_407_traj, bze_406_traj = [], [], []
raw_408_traj, alpha_traj                 = [], []
lc_408_traj, lc_407_traj, lc_406_traj   = [], [], []
lag_408_traj                             = []
sat_408 = 0

mu_408 = make_mu(); mu_407 = make_mu(); mu_406 = make_mu()
bze_ema8 = float(_BETA_Z_313)
bze_ema7 = float(_BETA_Z_313)
bze_ema6 = float(_BETA_Z_313)

for n in range(N_STEPS):
    if n > 0:
        mu_408 = make_mu(S_A_init=np.array(mu_408.S_A), S_C_init=np.array(mu_408.S_C),
                         S_D_init=np.array(mu_408.S_D), S_init=np.array(mu_408.S))
        mu_407 = make_mu(S_A_init=np.array(mu_407.S_A), S_C_init=np.array(mu_407.S_C),
                         S_D_init=np.array(mu_407.S_D), S_init=np.array(mu_407.S))
        mu_406 = make_mu(S_A_init=np.array(mu_406.S_A), S_C_init=np.array(mu_406.S_C),
                         S_D_init=np.array(mu_406.S_D), S_init=np.array(mu_406.S))

    cid8 = next(iter(mu_408.active))
    cid7 = next(iter(mu_407.active))
    cid6 = next(iter(mu_406.active))

    mu_408, _, _, bze8, raw8, BA8, BD8, gA8, gD8, aeff8 = apply_gamma_408_recursive(
        mu=mu_408, claim_id=cid8, scene_n=n, bze_ema_prev=bze_ema8, **SHARED_408)
    mu_407, _, _, bze7, raw7, BA7, BD7, gA7, gD7, aeff7 = apply_gamma_407_recursive(
        mu=mu_407, claim_id=cid7, scene_n=n, bze_ema_prev=bze_ema7, **SHARED_407)
    mu_406, _, _, bze6, raw6, BA6, BD6, gA6, gD6 = apply_gamma_406_recursive(
        mu=mu_406, claim_id=cid6, scene_n=n, bze_ema_prev=bze_ema6, **SHARED_406)

    bze_ema8 = bze8; bze_ema7 = bze7; bze_ema6 = bze6

    bze_408_traj.append(bze8); bze_407_traj.append(bze7); bze_406_traj.append(bze6)
    raw_408_traj.append(raw8); alpha_traj.append(aeff8)
    lc_408_traj.append(len(mu_408.active))
    lc_407_traj.append(len(mu_407.active))
    lc_406_traj.append(len(mu_406.active))
    lag_408_traj.append(abs(bze8 - raw8) / (raw8 + 1e-15))
    if abs(bze8 - _BETA_Z_MIN_408) < 1e-10:
        sat_408 += 1

saturation_ratio_408 = sat_408 / N_STEPS
overshoot_ratio_408  = max(bze_408_traj) / bze_408_traj[-1] if bze_408_traj[-1] > 0 else float('inf')
overshoot_ratio_404  = 1.33

tail_range_408  = max(bze_408_traj[10:]) - min(bze_408_traj[10:])
tail_range_407  = max(bze_407_traj[10:]) - min(bze_407_traj[10:])
tail_range_406  = max(bze_406_traj[10:]) - min(bze_406_traj[10:])
last5_range_408 = max(bze_408_traj[-5:]) - min(bze_408_traj[-5:])

# alpha_crit crossing point (analytical)
import math
n_cross = -_TAU_ALPHA_408 * math.log((_ALPHA_MAX_408 - 2/3) / (_ALPHA_MAX_408 - _ALPHA_MIN_408))
alpha_at_n4 = _ALPHA_MAX_408 - (_ALPHA_MAX_408 - _ALPHA_MIN_408) * math.exp(-4 / _TAU_ALPHA_408)

print(f"\n  Sequential N={N_STEPS}:")
print(f"  bze_408: {[round(b,2) for b in bze_408_traj]}")
print(f"  raw_408: {[round(b,2) for b in raw_408_traj]}")
print(f"  bze_407: {[round(b,2) for b in bze_407_traj]}")
print(f"  bze_406: {[round(b,2) for b in bze_406_traj]}")
print(f"  alpha:   {[round(a,3) for a in alpha_traj]}")
print(f"  lc_408:  {lc_408_traj}")
print(f"  lc_407:  {lc_407_traj}")
print(f"  lc_406:  {lc_406_traj}")
print(f"  n_cross(alpha_crit)={n_cross:.2f}  alpha(n=4)={alpha_at_n4:.3f}")
print(f"  overshoot_408={overshoot_ratio_408:.4f}  overshoot_404={overshoot_ratio_404:.2f}")
print(f"  tail_range_408={tail_range_408:.4f}  tail_range_407={tail_range_407:.4f}  tail_range_406={tail_range_406:.4f}")
print(f"  last5_range_408={last5_range_408:.4f}")
print(f"  bze_408[-1]={bze_408_traj[-1]:.4f}  bze_407[-1]={bze_407_traj[-1]:.4f}  bze_406[-1]={bze_406_traj[-1]:.4f}")
print(f"  lc_408_tail={sorted(set(lc_408_traj[10:]))}")
print(f"  saturation_ratio_408={saturation_ratio_408:.4f}")

# ── [5] Tail stability; Ghost #19 documented ──────────────────────────────
# Ghost #19 (Attraktorwahl — attractor selection):
# Ascending alpha locks to alpha_max=0.9 by n≈7. When lc switches to 64 at n=9
# (raw≈7-8, lower basin), the 90% EMA inertia anchors bze near 8-9 permanently.
# System cannot re-escape to lc=71/78 basin (bze too low to trigger deeper expansion).
# Bootstrap DID work (bze_408 led bze_407 for n=1-5), but Attraktorwahl at n=9
# overrode the convergence advantage. bze_408 converges to lc=64 equilibrium (~8),
# not the lc=71/78 equilibrium (~11-17). Trade: stability >> resolution.
last5_range_407_val = max(bze_407_traj[-5:]) - min(bze_407_traj[-5:])
assert last5_range_408 < last5_range_407_val, \
    f"[5] FAIL: last5_range_408={last5_range_408:.4f} >= last5_range_407={last5_range_407_val:.4f}"
print(f"[5] PASS  last5_408={last5_range_408:.4f} < last5_407={last5_range_407_val:.4f} "
      f"(Ghost #19: lc=64 basin lock; bze_408[-1]={bze_408_traj[-1]:.2f} vs bze_407[-1]={bze_407_traj[-1]:.2f})")

# ── [6] 2-cycle suppressed vs EXP-406 ─────────────────────────────────────
assert tail_range_408 < tail_range_406, \
    f"[6] FAIL: tail_range_408={tail_range_408:.4f} >= tail_range_406={tail_range_406:.4f}"
print(f"[6] PASS  tail_range_408={tail_range_408:.4f} < tail_range_406={tail_range_406:.4f} "
      f"(alpha_max=0.9 damps 2-cycle)")

# ── [7] Leaf count bounded ─────────────────────────────────────────────────
lc408_tail = sorted(set(lc_408_traj[10:]))
assert all(30 <= v <= 200 for v in lc408_tail), \
    f"[7] FAIL: lc_408_tail={lc408_tail} out of bounds"
print(f"[7] PASS  lc_408_tail={lc408_tail} bounded [30,200]")

# ── [8] Saturation gate ───────────────────────────────────────────────────
assert saturation_ratio_408 < 0.5, \
    f"[8] FAIL: sat_ratio={saturation_ratio_408:.4f}"
print(f"[8] PASS  saturation_ratio_408={saturation_ratio_408:.4f} < 0.5")

# ── [9] Overshoot bounded below EXP-404 ──────────────────────────────────
assert overshoot_ratio_408 < overshoot_ratio_404, \
    f"[9] FAIL: overshoot_408={overshoot_ratio_408:.4f} >= overshoot_404={overshoot_ratio_404:.2f}"
print(f"[9] PASS  overshoot_408={overshoot_ratio_408:.4f} < overshoot_404={overshoot_ratio_404:.2f}")

# ── [10] Gradient monotone ────────────────────────────────────────────────
B_vals = [0.0, 0.1, 0.5, 1.0, 2.0, 5.0]
bze_BA = [phi_fb_ascending_ema(np.full(8,b/np.sqrt(8)), np.ones(4), np.zeros(6),
                               scene_n=10, bze_ema_prev=_BETA_Z_313)[0] for b in B_vals]
bze_BD = [phi_fb_ascending_ema(np.zeros(8), np.ones(4), np.full(6,b/np.sqrt(6)),
                               scene_n=10, bze_ema_prev=_BETA_Z_313)[0] for b in B_vals]
assert all(bze_BA[i] <= bze_BA[i+1] for i in range(len(bze_BA)-1)), \
    f"[10] FAIL: B_A not monotone: {bze_BA}"
assert all(bze_BD[i] >= bze_BD[i+1] for i in range(len(bze_BD)-1)), \
    f"[10] FAIL: B_D not monotone: {bze_BD}"
print(f"[10] PASS  gradient monotone: B_A-> {[round(b,3) for b in bze_BA]}")

Omega_inertia_max = max(lag_408_traj)
print(f"\n=== EXP-408 Fork A: 10/10 PASS ===")
print(f"    alpha_min={_ALPHA_MIN_408}  alpha_max={_ALPHA_MAX_408}  tau_alpha={_TAU_ALPHA_408}")
print(f"    n_cross(alpha_crit)={n_cross:.2f}  alpha(n=4)={alpha_at_n4:.3f}")
print(f"    Ghost #19 (Attraktorwahl): lc=64 basin lock at n=9; bze->8 not 17")
print(f"    overshoot_408={overshoot_ratio_408:.4f}  (vs 404: {overshoot_ratio_404:.2f})")
print(f"    tail_range_408={tail_range_408:.4f}  tail_range_406={tail_range_406:.4f}  ratio={tail_range_408/(tail_range_406+1e-15):.3f}")
print(f"    last5_408={last5_range_408:.4f}  last5_407={last5_range_407_val:.4f}")
print(f"    bze_408[-1]={bze_408_traj[-1]:.4f}  bze_407[-1]={bze_407_traj[-1]:.4f}  bze_406[-1]={bze_406_traj[-1]:.4f}")
print(f"    lc_408_tail={lc408_tail}  Omega_inertia_max={Omega_inertia_max:.4f}")
