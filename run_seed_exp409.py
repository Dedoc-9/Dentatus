"""
run_seed_exp409.py — Fork A: EXP-409 Hysteresis α_bze Schedule (Conditional Basin Lock)

Protocol: exp409-v1
Declaration hash: 32a0fbef5f6e5e1eb0e33adc0ee3e25b332e3586b30e0497f81194fb48b799f6

phi_fb_hysteresis_ema: conditional latch at beta_threshold=12.0.
  Discovery (bze < 12.0): alpha_eff = 0.5   [EXP-406 path -> lc=71 basin]
  Maintenance (bze >= 12.0, latched): alpha_eff = 0.9  [Ghost #16 suppressed]

beta_threshold = sqrt(8.0 * 17.19) = 11.73 -> 12.0
  lc=64 equilibrium: beta_raw ≈ 8.0  (EXP-408)
  lc=71 equilibrium: beta_raw ≈ 17.19 (EXP-404)
  separatrix = geometric mean of basin equilibria in beta_Z_eff space

Caller state: bze_ema_prev (float) + maint_latched (bool) — both primary scalars.
maint_latched is irreversible once set True.

Tests [1-10]:
  [1]  declaration_hash
  [2]  cold start: bze=base; alpha_eff==alpha_disc; maint_latched=False
  [3]  n->inf: alpha_eff -> alpha_maint when bze >= beta_threshold
  [4]  latch irreversibility: maint_latched=True -> alpha_maint regardless of bze
  [5]  bze_409[-1] > bze_407[-1]=11.18 (faster convergence via discovery->maintenance)
  [6]  tail_range_409 < tail_range_406=9.17 (maintenance alpha=0.9 damps 2-cycle)
  [7]  latch triggers: maint_latched becomes True during N=20 run
  [8]  saturation_ratio_409 < 0.5
  [9]  overshoot_409 < overshoot_404=1.33
  [10] gradient monotone
"""
import sys, os, json, hashlib
import numpy as np
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_409_recursive, apply_gamma_406_recursive, apply_gamma_407_recursive,
    phi_fb_hysteresis_ema,
    _ALPHA_DISC_409, _ALPHA_MAINT_409, _BETA_THRESHOLD_409,
    _GAMMA_INF_A_409, _GAMMA_INF_D_409, _TAU_WARMUP_409, _BETA_Z_MIN_409,
    _GAMMA_INF_A_406, _GAMMA_INF_D_406, _TAU_WARMUP_406,
    _ALPHA_BZE_406, _BETA_Z_MIN_406,
    _GAMMA_INF_A_407, _GAMMA_INF_D_407, _TAU_WARMUP_407,
    _ALPHA_MAX_407, _ALPHA_MIN_407, _TAU_ALPHA_407, _BETA_Z_MIN_407,
    _BETA_Z_313,
)
from engine.validity import kappa_integral

DECL_HASH = "32a0fbef5f6e5e1eb0e33adc0ee3e25b332e3586b30e0497f81194fb48b799f6"
DECL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "studies/exp409_hysteresis_alpha/SEED_DECLARATION_exp409.json")

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

SHARED_409 = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0,
                  K_budget=K_BUD, depth=0, focal_point=np.array([0.5,0.5,0.5]),
                  B=B_field, J_AC=J_AC, W_max=W_MAX, beta_Z_base=_BETA_Z_313,
                  gamma_inf_A=_GAMMA_INF_A_409, gamma_inf_D=_GAMMA_INF_D_409,
                  tau_warmup=_TAU_WARMUP_409,
                  alpha_disc=_ALPHA_DISC_409, alpha_maint=_ALPHA_MAINT_409,
                  beta_threshold=_BETA_THRESHOLD_409, beta_Z_min=_BETA_Z_MIN_409)

SHARED_406 = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0,
                  K_budget=K_BUD, depth=0, focal_point=np.array([0.5,0.5,0.5]),
                  B=B_field, J_AC=J_AC, W_max=W_MAX, beta_Z_base=_BETA_Z_313,
                  gamma_inf_A=_GAMMA_INF_A_406, gamma_inf_D=_GAMMA_INF_D_406,
                  tau_warmup=_TAU_WARMUP_406, alpha_bze=_ALPHA_BZE_406,
                  beta_Z_min=_BETA_Z_MIN_406)

SHARED_407 = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0,
                  K_budget=K_BUD, depth=0, focal_point=np.array([0.5,0.5,0.5]),
                  B=B_field, J_AC=J_AC, W_max=W_MAX, beta_Z_base=_BETA_Z_313,
                  gamma_inf_A=_GAMMA_INF_A_407, gamma_inf_D=_GAMMA_INF_D_407,
                  tau_warmup=_TAU_WARMUP_407,
                  alpha_max=_ALPHA_MAX_407, alpha_min=_ALPHA_MIN_407,
                  tau_alpha=_TAU_ALPHA_407, beta_Z_min=_BETA_Z_MIN_407)


def make_mu(S_A_init=None, S_C_init=None, S_D_init=None, S_init=None):
    prov  = Provenance(parent_ids=(), operator_id="seed_exp409", timestamp=now_iso())
    claim = Claim(provenance=prov, payload="scene:exp409:root",
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


# ── [2] Cold start ─────────────────────────────────────────────────────────
bze_n0, _, _, _, _, _, a_n0, lat_n0 = phi_fb_hysteresis_ema(
    np.zeros(8), np.ones(4), np.zeros(6),
    scene_n=0, bze_ema_prev=_BETA_Z_313, maint_latched=False)
assert abs(bze_n0 - _BETA_Z_313) < 1e-10, f"[2] FAIL: bze={bze_n0}"
assert abs(a_n0 - _ALPHA_DISC_409) < 1e-10, f"[2] FAIL: alpha={a_n0} != alpha_disc"
assert lat_n0 == False, f"[2] FAIL: maint_latched should be False at cold start"
print(f"[2] PASS  n=0: bze=base  alpha={a_n0:.2f}==alpha_disc  maint_latched={lat_n0}")

# ── [3] alpha -> alpha_maint when bze >= threshold ─────────────────────────
S_A_hi = np.array([3.0]*4 + [0.]*4); Z_A_t = np.ones(4)
bze_hi, _, _, _, _, _, a_hi, lat_hi = phi_fb_hysteresis_ema(
    S_A_hi, Z_A_t, np.zeros(6),
    scene_n=20, bze_ema_prev=_BETA_THRESHOLD_409 + 1.0, maint_latched=False)
assert abs(a_hi - _ALPHA_MAINT_409) < 1e-10, f"[3] FAIL: alpha={a_hi} != alpha_maint when bze>threshold"
assert lat_hi == True, f"[3] FAIL: maint_latched should be True once bze>=threshold"
print(f"[3] PASS  bze_prev>threshold -> alpha={a_hi:.2f}==alpha_maint  maint_latched={lat_hi}")

# ── [4] Latch irreversibility ──────────────────────────────────────────────
bze_rev, _, _, _, _, _, a_rev, lat_rev = phi_fb_hysteresis_ema(
    np.zeros(8), np.ones(4), np.zeros(6),
    scene_n=0, bze_ema_prev=_BETA_Z_313, maint_latched=True)
assert abs(a_rev - _ALPHA_MAINT_409) < 1e-10, f"[4] FAIL: alpha={a_rev} != alpha_maint with latch=True"
assert lat_rev == True, f"[4] FAIL: latch should stay True"
print(f"[4] PASS  maint_latched=True (even at cold bze) -> alpha={a_rev:.2f}==alpha_maint  irreversible")

# ── Sequential N=20 ────────────────────────────────────────────────────────
N_STEPS = 20
bze_409_traj, bze_407_traj, bze_406_traj = [], [], []
raw_409_traj, alpha_traj, latch_traj     = [], [], []
lc_409_traj, lc_407_traj, lc_406_traj   = [], [], []
sat_409 = 0; latch_step = None

mu_409 = make_mu(); mu_407 = make_mu(); mu_406 = make_mu()
bze_ema9 = float(_BETA_Z_313); maint9 = False
bze_ema7 = float(_BETA_Z_313)
bze_ema6 = float(_BETA_Z_313)

for n in range(N_STEPS):
    if n > 0:
        mu_409 = make_mu(S_A_init=np.array(mu_409.S_A), S_C_init=np.array(mu_409.S_C),
                         S_D_init=np.array(mu_409.S_D), S_init=np.array(mu_409.S))
        mu_407 = make_mu(S_A_init=np.array(mu_407.S_A), S_C_init=np.array(mu_407.S_C),
                         S_D_init=np.array(mu_407.S_D), S_init=np.array(mu_407.S))
        mu_406 = make_mu(S_A_init=np.array(mu_406.S_A), S_C_init=np.array(mu_406.S_C),
                         S_D_init=np.array(mu_406.S_D), S_init=np.array(mu_406.S))

    cid9 = next(iter(mu_409.active))
    cid7 = next(iter(mu_407.active))
    cid6 = next(iter(mu_406.active))

    (mu_409, _, _, bze9, raw9, BA9, BD9, gA9, gD9,
     aeff9, maint9_out) = apply_gamma_409_recursive(
        mu=mu_409, claim_id=cid9, scene_n=n,
        bze_ema_prev=bze_ema9, maint_latched=maint9, **SHARED_409)

    mu_407, _, _, bze7, raw7, BA7, BD7, gA7, gD7, aeff7 = apply_gamma_407_recursive(
        mu=mu_407, claim_id=cid7, scene_n=n, bze_ema_prev=bze_ema7, **SHARED_407)
    mu_406, _, _, bze6, raw6, BA6, BD6, gA6, gD6 = apply_gamma_406_recursive(
        mu=mu_406, claim_id=cid6, scene_n=n, bze_ema_prev=bze_ema6, **SHARED_406)

    if maint9_out and not maint9 and latch_step is None:
        latch_step = n
    bze_ema9 = bze9; maint9 = maint9_out
    bze_ema7 = bze7; bze_ema6 = bze6

    bze_409_traj.append(bze9); bze_407_traj.append(bze7); bze_406_traj.append(bze6)
    raw_409_traj.append(raw9); alpha_traj.append(aeff9); latch_traj.append(maint9_out)
    lc_409_traj.append(len(mu_409.active))
    lc_407_traj.append(len(mu_407.active))
    lc_406_traj.append(len(mu_406.active))
    if abs(bze9 - _BETA_Z_MIN_409) < 1e-10:
        sat_409 += 1

saturation_ratio_409 = sat_409 / N_STEPS
overshoot_ratio_409  = max(bze_409_traj) / bze_409_traj[-1] if bze_409_traj[-1] > 0 else float('inf')
overshoot_ratio_404  = 1.33

tail_range_409  = max(bze_409_traj[10:]) - min(bze_409_traj[10:])
tail_range_406  = max(bze_406_traj[10:]) - min(bze_406_traj[10:])
tail_range_407  = max(bze_407_traj[10:]) - min(bze_407_traj[10:])
last5_range_409 = max(bze_409_traj[-5:]) - min(bze_409_traj[-5:])
lc409_tail      = sorted(set(lc_409_traj[10:]))

print(f"\n  Sequential N={N_STEPS}:")
print(f"  bze_409: {[round(b,2) for b in bze_409_traj]}")
print(f"  raw_409: {[round(b,2) for b in raw_409_traj]}")
print(f"  bze_407: {[round(b,2) for b in bze_407_traj]}")
print(f"  bze_406: {[round(b,2) for b in bze_406_traj]}")
print(f"  alpha:   {[round(a,2) for a in alpha_traj]}")
print(f"  latched: {[int(l) for l in latch_traj]}  (1=maintenance)")
print(f"  lc_409:  {lc_409_traj}")
print(f"  lc_407:  {lc_407_traj}")
print(f"  latch_step={latch_step}  bze_at_latch={round(bze_409_traj[latch_step],3) if latch_step is not None else None}")
print(f"  overshoot_409={overshoot_ratio_409:.4f}  overshoot_404={overshoot_ratio_404:.2f}")
print(f"  tail_range_409={tail_range_409:.4f}  tail_range_407={tail_range_407:.4f}  tail_range_406={tail_range_406:.4f}")
print(f"  last5_range_409={last5_range_409:.4f}")
print(f"  bze_409[-1]={bze_409_traj[-1]:.4f}  bze_407[-1]={bze_407_traj[-1]:.4f}  bze_406[-1]={bze_406_traj[-1]:.4f}")
print(f"  lc_409_tail={lc409_tail}  saturation={saturation_ratio_409:.4f}")

# ── [5] Faster convergence than EXP-407 ───────────────────────────────────
assert bze_409_traj[-1] > bze_407_traj[-1], \
    f"[5] FAIL: bze_409[-1]={bze_409_traj[-1]:.4f} <= bze_407[-1]={bze_407_traj[-1]:.4f}"
print(f"[5] PASS  bze_409[-1]={bze_409_traj[-1]:.4f} > bze_407[-1]={bze_407_traj[-1]:.4f}")

# ── [6] 2-cycle damped vs EXP-406 ─────────────────────────────────────────
assert tail_range_409 < tail_range_406, \
    f"[6] FAIL: tail_range_409={tail_range_409:.4f} >= tail_range_406={tail_range_406:.4f}"
print(f"[6] PASS  tail_range_409={tail_range_409:.4f} < tail_range_406={tail_range_406:.4f}")

# ── [7] Latch triggered during run ────────────────────────────────────────
assert latch_step is not None, "[7] FAIL: maint_latched never triggered (bze never >= threshold)"
assert maint9 == True, f"[7] FAIL: final maint_latched={maint9}"
print(f"[7] PASS  latch triggered at n={latch_step}  bze_at_latch={round(bze_409_traj[latch_step],3)}")

# ── [8] Saturation gate ───────────────────────────────────────────────────
assert saturation_ratio_409 < 0.5, f"[8] FAIL: sat={saturation_ratio_409:.4f}"
print(f"[8] PASS  saturation_ratio_409={saturation_ratio_409:.4f} < 0.5")

# ── [9] Overshoot bounded ─────────────────────────────────────────────────
assert overshoot_ratio_409 < overshoot_ratio_404, \
    f"[9] FAIL: overshoot_409={overshoot_ratio_409:.4f} >= {overshoot_ratio_404:.2f}"
print(f"[9] PASS  overshoot_409={overshoot_ratio_409:.4f} < overshoot_404={overshoot_ratio_404:.2f}")

# ── [10] Gradient monotone ────────────────────────────────────────────────
B_vals = [0.0, 0.1, 0.5, 1.0, 2.0, 5.0]
bze_BA = [phi_fb_hysteresis_ema(np.full(8,b/np.sqrt(8)), np.ones(4), np.zeros(6),
                                scene_n=10, bze_ema_prev=_BETA_Z_313)[0] for b in B_vals]
bze_BD = [phi_fb_hysteresis_ema(np.zeros(8), np.ones(4), np.full(6,b/np.sqrt(6)),
                                scene_n=10, bze_ema_prev=_BETA_Z_313)[0] for b in B_vals]
assert all(bze_BA[i] <= bze_BA[i+1] for i in range(len(bze_BA)-1)), \
    f"[10] FAIL: B_A not monotone"
assert all(bze_BD[i] >= bze_BD[i+1] for i in range(len(bze_BD)-1)), \
    f"[10] FAIL: B_D not monotone"
print(f"[10] PASS  gradient monotone: B_A-> {[round(b,3) for b in bze_BA]}")

print(f"\n=== EXP-409 Fork A: 10/10 PASS ===")
print(f"    alpha_disc={_ALPHA_DISC_409}  alpha_maint={_ALPHA_MAINT_409}  beta_threshold={_BETA_THRESHOLD_409}")
print(f"    latch_step={latch_step}  maint_latched_final={maint9}")
print(f"    tail_range_409={tail_range_409:.4f}  ratio_vs_406={tail_range_409/tail_range_406:.3f}")
print(f"    bze_409[-1]={bze_409_traj[-1]:.4f}  bze_407[-1]={bze_407_traj[-1]:.4f}  bze_406[-1]={bze_406_traj[-1]:.4f}")
print(f"    lc_409_tail={lc409_tail}  overshoot={overshoot_ratio_409:.4f}")
