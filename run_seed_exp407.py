"""
run_seed_exp407.py — Fork A: EXP-407 Adaptive α_bze Schedule (Synchronized Dual Warmup)

Protocol: exp407-v1
Declaration hash: 2dc29bcfbb1d7b02f65549f4d4750ac9b7af5603d4a726a3fa53347e67773f87
Ghost #18 revision: alpha_min raised 0.2->0.7 (>alpha_crit=0.667) for persistent 2-cycle suppression.

phi_fb_adaptive_ema: synchronized dual warmup schedules.
  gamma_eff(n) = gamma_inf * (1 - exp(-n / tau_warmup))   [gain ramps UP]
  alpha_eff(n) = alpha_min + (alpha_max-alpha_min)*exp(-n/tau_alpha)  [inertia ramps DOWN]

tau_warmup == tau_alpha == 5.0: crossing at n=tau -> gamma_eff=0.316*gamma_inf, alpha_eff=0.457.

2-cycle damping ratio = (1-alpha_eff)/(1+alpha_eff):
  n=0:   alpha=0.900 -> ratio=0.053  (5.3% of EXP-405 amplitude)
  n=5:   alpha=0.457 -> ratio=0.373  (37% — same as EXP-406 at peak)
  n=inf: alpha=0.700 -> ratio=0.176  (17.6% — above alpha_crit=0.667, 2-cycle suppressed)

Tests [1-10]:
  [1]  declaration_hash
  [2]  phi_fb_adaptive_ema(n=0, bze_prev=base) == base AND alpha_eff(0)==alpha_max
  [3]  phi_fb_adaptive_ema(n=1) bze_407 < bze_406 (alpha=0.773 vs 0.5 -> more inertia)
  [4]  phi_fb_adaptive_ema(n->inf): alpha_eff -> alpha_min; bze_ema ~ bze_raw
  [5]  tail_range_407 < tail_range_406 (Ghost #17 reduced; 2-cycle further damped)
  [6]  last5_range_407 < last5_range_406 (convergence criterion relative)
  [7]  leaf_count tail: single or fewer distinct values than EXP-406
  [8]  saturation_ratio_407 < 0.5 (EXP-408 gate inactive)
  [9]  overshoot_ratio_407 < overshoot_ratio_404=1.33 (bounded below EXP-404 spike)
  [10] gradient monotone: phi_fb_adaptive_ema increasing B_A, decreasing B_D
"""
import sys, os, json, hashlib
import numpy as np
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_407_recursive, apply_gamma_406_recursive,
    phi_fb_adaptive_ema, phi_fb_ema,
    _GAMMA_INF_A_407, _GAMMA_INF_D_407, _TAU_WARMUP_407,
    _ALPHA_MAX_407, _ALPHA_MIN_407, _TAU_ALPHA_407, _BETA_Z_MIN_407,
    _GAMMA_INF_A_406, _GAMMA_INF_D_406, _TAU_WARMUP_406,
    _ALPHA_BZE_406, _BETA_Z_MIN_406,
    _BETA_Z_313,
)
from engine.validity import kappa_integral

DECL_HASH = "2dc29bcfbb1d7b02f65549f4d4750ac9b7af5603d4a726a3fa53347e67773f87"
DECL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "studies/exp407_adaptive_alpha/SEED_DECLARATION_exp407.json")

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
    prov  = Provenance(parent_ids=(), operator_id="seed_exp407", timestamp=now_iso())
    claim = Claim(provenance=prov, payload="scene:exp407:root",
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


# ── [2] Cold start ─────────────────────────────────────────────────────────────
bze_n0, _, _, _, gA_n0, _, a_n0 = phi_fb_adaptive_ema(
    np.zeros(8), np.ones(4), np.zeros(6),
    scene_n=0, bze_ema_prev=_BETA_Z_313)
assert abs(bze_n0 - _BETA_Z_313) < 1e-10, f"[2] FAIL: bze={bze_n0}"
assert abs(a_n0 - _ALPHA_MAX_407) < 1e-10, f"[2] FAIL: alpha_eff(0)={a_n0}"
print(f"[2] PASS  n=0: bze={bze_n0:.4f}==base  alpha_eff={a_n0:.4f}==alpha_max={_ALPHA_MAX_407}")

# ── [3] n=1: more inertia than EXP-406 ────────────────────────────────────────
S_A_t = np.array([0.1]*4 + [0.]*4); Z_A_t = np.ones(4)
bze407_n1, _, _, _, _, _, a1 = phi_fb_adaptive_ema(
    S_A_t, Z_A_t, np.zeros(6), scene_n=1, bze_ema_prev=_BETA_Z_313)
bze406_n1, *_ = phi_fb_ema(S_A_t, Z_A_t, np.zeros(6),
                            scene_n=1, bze_ema_prev=_BETA_Z_313)
assert bze407_n1 <= bze406_n1 + 1e-10, \
    f"[3] FAIL: bze407={bze407_n1:.6f} > bze406={bze406_n1:.6f}"
print(f"[3] PASS  n=1: alpha_407={a1:.4f} > 0.5 -> bze407={bze407_n1:.4f} <= bze406={bze406_n1:.4f}")

# ── [4] Large n: alpha_eff -> alpha_min; bze_ema ~ bze_raw ────────────────────
S_A_lg = np.array([1.]*4 + [0.]*4)
from engine.operators import phi_fb_exp
bze_exp, *_ = phi_fb_exp(S_A_lg, Z_A_t, np.zeros(6))
# At n=100 settled: alpha_min*bze_prev + (1-alpha_min)*raw -> if bze_prev==raw -> raw
bze407_100, raw407_100, _, _, _, _, a100 = phi_fb_adaptive_ema(
    S_A_lg, Z_A_t, np.zeros(6), scene_n=100, bze_ema_prev=bze_exp)
diff_settled = abs(bze407_100 - bze_exp)
assert diff_settled < 0.5, f"[4] FAIL: settled diff={diff_settled:.4f}"
assert abs(a100 - _ALPHA_MIN_407) < 0.01, f"[4] FAIL: alpha_eff(100)={a100:.4f} != alpha_min"
print(f"[4] PASS  n=100: alpha_eff={a100:.4f}~alpha_min  bze407={bze407_100:.4f}~bze_exp={bze_exp:.4f} "
      f"(diff={diff_settled:.4f})")

# ── Sequential N=20 ────────────────────────────────────────────────────────────
N_STEPS = 20
bze_407_traj, bze_406_traj = [], []
raw_407_traj, alpha_traj    = [], []
lc_407_traj,  lc_406_traj  = [], []
lag_407_traj                = []
sat_407 = 0

mu_407 = make_mu(); mu_406 = make_mu()
bze_ema7 = float(_BETA_Z_313)
bze_ema6 = float(_BETA_Z_313)

for n in range(N_STEPS):
    if n > 0:
        mu_407 = make_mu(S_A_init=np.array(mu_407.S_A), S_C_init=np.array(mu_407.S_C),
                         S_D_init=np.array(mu_407.S_D), S_init=np.array(mu_407.S))
        mu_406 = make_mu(S_A_init=np.array(mu_406.S_A), S_C_init=np.array(mu_406.S_C),
                         S_D_init=np.array(mu_406.S_D), S_init=np.array(mu_406.S))

    cid7 = next(iter(mu_407.active)); cid6 = next(iter(mu_406.active))

    mu_407, _, _, bze7, raw7, BA7, BD7, gA7, gD7, aeff7 = apply_gamma_407_recursive(
        mu=mu_407, claim_id=cid7, scene_n=n, bze_ema_prev=bze_ema7, **SHARED_407)
    mu_406, _, _, bze6, raw6, BA6, BD6, gA6, gD6 = apply_gamma_406_recursive(
        mu=mu_406, claim_id=cid6, scene_n=n, bze_ema_prev=bze_ema6, **SHARED_406)

    bze_ema7 = bze7; bze_ema6 = bze6

    bze_407_traj.append(bze7); bze_406_traj.append(bze6)
    raw_407_traj.append(raw7); alpha_traj.append(aeff7)
    lc_407_traj.append(len(mu_407.active)); lc_406_traj.append(len(mu_406.active))
    lag = abs(bze7 - raw7) / (raw7 + 1e-15)
    lag_407_traj.append(lag)
    if abs(bze7 - _BETA_Z_MIN_407) < 1e-10:
        sat_407 += 1

saturation_ratio_407 = sat_407 / N_STEPS
overshoot_ratio_407  = max(bze_407_traj) / bze_407_traj[-1] if bze_407_traj[-1] > 0 else float('inf')
overshoot_ratio_404  = 1.33

tail_range_407  = max(bze_407_traj[10:]) - min(bze_407_traj[10:])
tail_range_406  = max(bze_406_traj[10:]) - min(bze_406_traj[10:])
last5_range_407 = max(bze_407_traj[-5:]) - min(bze_407_traj[-5:])
last5_range_406 = max(bze_406_traj[-5:]) - min(bze_406_traj[-5:])

print(f"\n  Sequential N={N_STEPS}:")
print(f"  bze_407: {[round(b,2) for b in bze_407_traj]}")
print(f"  raw_407: {[round(b,2) for b in raw_407_traj]}")
print(f"  bze_406: {[round(b,2) for b in bze_406_traj]}")
print(f"  alpha:   {[round(a,3) for a in alpha_traj]}")
print(f"  lc_407:  {lc_407_traj}")
print(f"  lc_406:  {lc_406_traj}")
print(f"  overshoot_ratio_407={overshoot_ratio_407:.4f}  overshoot_ratio_404={overshoot_ratio_404:.2f}")
print(f"  tail_range_407={tail_range_407:.4f}  tail_range_406={tail_range_406:.4f}")
print(f"  last5_range_407={last5_range_407:.4f}  last5_range_406={last5_range_406:.4f}")
print(f"  bze_407[-1]={bze_407_traj[-1]:.4f}  bze_406[-1]={bze_406_traj[-1]:.4f}")
print(f"  lc_407_tail={sorted(set(lc_407_traj[10:]))}  lc_406_tail={sorted(set(lc_406_traj[10:]))}")
print(f"  saturation_ratio_407={saturation_ratio_407:.4f}")

# ── [5] 2-cycle further damped ────────────────────────────────────────────────
assert tail_range_407 < tail_range_406, \
    f"[5] FAIL: tail_range_407={tail_range_407:.4f} >= tail_range_406={tail_range_406:.4f}"
print(f"[5] PASS  tail_range_407={tail_range_407:.4f} < tail_range_406={tail_range_406:.4f} "
      f"(adaptive alpha damps 2-cycle further)")

# ── [6] Last-5 convergence vs EXP-406 ────────────────────────────────────────
assert last5_range_407 < last5_range_406, \
    f"[6] FAIL: last5_range_407={last5_range_407:.4f} >= last5_range_406={last5_range_406:.4f}"
print(f"[6] PASS  last5_range_407={last5_range_407:.4f} < last5_range_406={last5_range_406:.4f}")

# ── [7] Leaf count: fewer or equal distinct values ────────────────────────────
lc407_tail = sorted(set(lc_407_traj[10:]))
lc406_tail = sorted(set(lc_406_traj[10:]))
assert len(lc407_tail) <= len(lc406_tail), \
    f"[7] FAIL: lc_407 tail={lc407_tail} ({len(lc407_tail)} vals) > lc_406 tail={lc406_tail}"
print(f"[7] PASS  lc_407_tail={lc407_tail} ({len(lc407_tail)} vals) <= "
      f"lc_406_tail={lc406_tail} ({len(lc406_tail)} vals)")

# ── [8] Saturation gate ───────────────────────────────────────────────────────
assert saturation_ratio_407 < 0.5, \
    f"[8] FAIL: sat_ratio={saturation_ratio_407:.4f}"
print(f"[8] PASS  saturation_ratio_407={saturation_ratio_407:.4f} < 0.5")

# ── [9] Overshoot bounded below EXP-404 ──────────────────────────────────────
assert overshoot_ratio_407 < overshoot_ratio_404, \
    f"[9] FAIL: overshoot_407={overshoot_ratio_407:.4f} >= overshoot_404={overshoot_ratio_404:.2f}"
print(f"[9] PASS  overshoot_ratio_407={overshoot_ratio_407:.4f} < overshoot_404={overshoot_ratio_404:.2f}")

# ── [10] Gradient monotone ────────────────────────────────────────────────────
B_vals = [0.0, 0.1, 0.5, 1.0, 2.0, 5.0]
bze_BA = [phi_fb_adaptive_ema(np.full(8,b/np.sqrt(8)), np.ones(4), np.zeros(6),
                              scene_n=10, bze_ema_prev=_BETA_Z_313)[0] for b in B_vals]
bze_BD = [phi_fb_adaptive_ema(np.zeros(8), np.ones(4), np.full(6,b/np.sqrt(6)),
                              scene_n=10, bze_ema_prev=_BETA_Z_313)[0] for b in B_vals]
assert all(bze_BA[i] <= bze_BA[i+1] for i in range(len(bze_BA)-1)), \
    f"[10] FAIL: B_A not monotone: {bze_BA}"
assert all(bze_BD[i] >= bze_BD[i+1] for i in range(len(bze_BD)-1)), \
    f"[10] FAIL: B_D not monotone: {bze_BD}"
print(f"[10] PASS  gradient monotone: B_A-> {[round(b,3) for b in bze_BA]}")

Omega_inertia_max = max(lag_407_traj)
print(f"\n=== EXP-407 Fork A: 10/10 PASS ===")
print(f"    alpha_max={_ALPHA_MAX_407}  alpha_min={_ALPHA_MIN_407}  tau_alpha={_TAU_ALPHA_407}")
print(f"    overshoot_407={overshoot_ratio_407:.4f}  (vs 404: {overshoot_ratio_404:.2f})")
print(f"    tail_range_407={tail_range_407:.4f}  tail_range_406={tail_range_406:.4f}  "
      f"ratio={tail_range_407/(tail_range_406+1e-15):.3f}")
print(f"    last5_407={last5_range_407:.4f}  last5_406={last5_range_406:.4f}")
print(f"    bze_407[-1]={bze_407_traj[-1]:.4f}")
print(f"    lc_407_tail={lc407_tail}  lc_406_tail={lc406_tail}")
print(f"    Omega_inertia_max={Omega_inertia_max:.4f}")
print(f"    saturation_ratio={saturation_ratio_407:.4f}")
