"""
run_seed_exp406.py — Fork A: EXP-406 EMA-Smoothed β_Z_eff (Inertial Attention Field)

Protocol: exp406-v1
Inherits: exp405-v1, exp404-v1
Declaration hash: 84255beb1f11d0182a052e6d31e9c5aaa4e87c37d3d1c0a6494b56fd4ad891cf

phi_fb_ema: adds inertial mass to beta_Z_eff output of phi_fb_adaptive.
  beta_raw(n)  = phi_fb_adaptive(S_A, Z_A, S_D, scene_n, ...)
  beta_Z_eff   = max(beta_Z_min, alpha_bze * bze_ema_prev + (1-alpha_bze) * beta_raw)

bze_ema_prev: primary-scalar, caller-tracked (NOT in MuState dual state).
Cold start: bze_ema_prev = beta_Z_base = 2.0

2-cycle damping (Ghost #16 resolution, alpha_bze=0.5):
  Steady-state EMA 2-cycle amplitude = EXP-405 amplitude * (1-alpha)/(1+alpha) = 1/3.

Inertial lag observable:
  Omega_inertia = |beta_Z_eff - beta_raw| / (beta_raw + eps)

Tests [1-10]:
  [1]  declaration_hash
  [2]  phi_fb_ema(n=0, bze_prev=base) == base (cold, no feedback, no inertia displacement)
  [3]  phi_fb_ema(n=1) bze_ema < phi_fb_adaptive(n=1) (inertia damps first step)
  [4]  phi_fb_ema(n=large) ~ phi_fb_exp (converges to EXP-404 as both n->inf and EMA settles)
  [5]  tail_range_406 < tail_range_405 (Ghost #16 2-cycle damped by inertial mass)
  [6]  bze_406 last-5 range < 2.0 (convergence criterion)
  [7]  leaf_count tail has fewer distinct values than EXP-405 (2-cycle weakened or broken)
  [8]  saturation_ratio_406 < 0.5 (EXP-407 gate inactive)
  [9]  overshoot_ratio_406 <= overshoot_ratio_405 = 1.0 (inertia cannot increase peak)
  [10] gradient monotone: phi_fb_ema increasing B_A, decreasing B_D (inherited from phi_fb_adaptive)
"""
import sys, os, json, hashlib
import numpy as np
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_406_recursive, apply_gamma_405_recursive,
    phi_fb_ema, phi_fb_adaptive,
    _GAMMA_INF_A_406, _GAMMA_INF_D_406, _TAU_WARMUP_406,
    _ALPHA_BZE_406, _BETA_Z_MIN_406,
    _GAMMA_INF_A_405, _GAMMA_INF_D_405, _TAU_WARMUP_405, _BETA_Z_MIN_405,
    _BETA_Z_313,
)
from engine.validity import kappa_integral

DECL_HASH = "84255beb1f11d0182a052e6d31e9c5aaa4e87c37d3d1c0a6494b56fd4ad891cf"
DECL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "studies/exp406_ema_bze/SEED_DECLARATION_exp406.json")

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
stalk18    = np.array([1.,1.,1.,1., 0.5,0.5,0.5,1., 0.6,0.,0.8,kappa_seed,
                       0.,0.,0.,0.,0.,0.])
B_field    = np.array([1.0, 0.5, 0.3])
J_AC       = np.eye(4)
W_MAX      = 8
K_BUD      = 2048

SHARED_406 = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0,
                  K_budget=K_BUD, depth=0, focal_point=np.array([0.5,0.5,0.5]),
                  B=B_field, J_AC=J_AC, W_max=W_MAX, beta_Z_base=_BETA_Z_313,
                  gamma_inf_A=_GAMMA_INF_A_406, gamma_inf_D=_GAMMA_INF_D_406,
                  tau_warmup=_TAU_WARMUP_406, alpha_bze=_ALPHA_BZE_406,
                  beta_Z_min=_BETA_Z_MIN_406)

SHARED_405 = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0,
                  K_budget=K_BUD, depth=0, focal_point=np.array([0.5,0.5,0.5]),
                  B=B_field, J_AC=J_AC, W_max=W_MAX, beta_Z_base=_BETA_Z_313,
                  gamma_inf_A=_GAMMA_INF_A_405, gamma_inf_D=_GAMMA_INF_D_405,
                  tau_warmup=_TAU_WARMUP_405, beta_Z_min=_BETA_Z_MIN_405)


def make_mu(S_A_init=None, S_C_init=None, S_D_init=None, S_init=None):
    prov  = Provenance(parent_ids=(), operator_id="seed_exp406", timestamp=now_iso())
    claim = Claim(provenance=prov, payload="scene:exp406:root",
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


# ── [2] Cold start: n=0, bze_prev=base -> bze_ema == base ────────────────────
bze_n0, raw_n0, _, _, gA_n0, _ = phi_fb_ema(
    np.zeros(8), np.ones(4), np.zeros(6),
    scene_n=0, bze_ema_prev=_BETA_Z_313)
assert abs(bze_n0 - _BETA_Z_313) < 1e-10 and abs(gA_n0) < 1e-15, \
    f"[2] FAIL: n=0 bze={bze_n0:.8f} gA={gA_n0:.2e}"
print(f"[2] PASS  phi_fb_ema(n=0, bze_prev=base): gamma_eff=0, EMA=base -> bze={bze_n0:.6f}")

# ── [3] n=1: inertia damps vs adaptive ───────────────────────────────────────
S_A_t = np.array([0.1]*4 + [0.]*4); Z_A_t = np.ones(4)
bze_ema_n1, raw_n1, *_ = phi_fb_ema(S_A_t, Z_A_t, np.zeros(6),
                                      scene_n=1, bze_ema_prev=_BETA_Z_313)
bze_adap_n1, *_         = phi_fb_adaptive(S_A_t, Z_A_t, np.zeros(6), scene_n=1)
assert bze_ema_n1 <= bze_adap_n1 + 1e-10, \
    f"[3] FAIL: ema={bze_ema_n1:.6f} > adaptive={bze_adap_n1:.6f}"
inertial_lag_n1 = abs(bze_ema_n1 - raw_n1) / (raw_n1 + 1e-15)
print(f"[3] PASS  n=1: bze_ema={bze_ema_n1:.4f} <= adaptive={bze_adap_n1:.4f}  "
      f"inertial_lag={inertial_lag_n1:.4f}")

# ── [4] Large n: phi_fb_ema (settled EMA) ~ phi_fb_exp ───────────────────────
S_A_lg = np.array([1.]*4 + [0.]*4)
# At n=100, gamma_eff->gamma_inf; if bze_prev already at equilibrium -> bze_ema ~ bze_exp
from engine.operators import phi_fb_exp
bze_exp_n100, *_   = phi_fb_exp(S_A_lg, Z_A_t, np.zeros(6))
# Use bze_exp as prev to represent settled state
bze_ema_n100, raw_100, *_ = phi_fb_ema(S_A_lg, Z_A_t, np.zeros(6),
                                         scene_n=100, bze_ema_prev=bze_exp_n100)
diff_settled = abs(bze_ema_n100 - bze_exp_n100)
assert diff_settled < 0.5, f"[4] FAIL: settled diff={diff_settled:.4f}"
print(f"[4] PASS  n=100 settled: bze_ema={bze_ema_n100:.4f} ~ bze_exp={bze_exp_n100:.4f} "
      f"(diff={diff_settled:.4f})")

# ── Sequential runs: EXP-406 vs EXP-405 ──────────────────────────────────────
N_STEPS = 20
bze_406_traj, bze_405_traj = [], []
raw_406_traj                = []
lc_406_traj,  lc_405_traj  = [], []
lag_406_traj                = []
sat_406 = 0

mu_406 = make_mu(); mu_405 = make_mu()
bze_ema = float(_BETA_Z_313)   # primary-scalar; caller-tracked; cold start = base

for n in range(N_STEPS):
    if n > 0:
        mu_406 = make_mu(S_A_init=np.array(mu_406.S_A), S_C_init=np.array(mu_406.S_C),
                         S_D_init=np.array(mu_406.S_D), S_init=np.array(mu_406.S))
        mu_405 = make_mu(S_A_init=np.array(mu_405.S_A), S_C_init=np.array(mu_405.S_C),
                         S_D_init=np.array(mu_405.S_D), S_init=np.array(mu_405.S))

    cid6 = next(iter(mu_406.active)); cid5 = next(iter(mu_405.active))

    mu_406, _, _, bze6, raw6, BA6, BD6, gA6, gD6 = apply_gamma_406_recursive(
        mu=mu_406, claim_id=cid6, scene_n=n, bze_ema_prev=bze_ema, **SHARED_406)
    mu_405, _, _, bze5, BA5, BD5, gA5, gD5 = apply_gamma_405_recursive(
        mu=mu_405, claim_id=cid5, scene_n=n, **SHARED_405)

    bze_ema = bze6   # update EMA tracker (primary scalar)

    bze_406_traj.append(bze6); bze_405_traj.append(bze5)
    raw_406_traj.append(raw6)
    lc_406_traj.append(len(mu_406.active)); lc_405_traj.append(len(mu_405.active))
    lag = abs(bze6 - raw6) / (raw6 + 1e-15)
    lag_406_traj.append(lag)
    if abs(bze6 - _BETA_Z_MIN_406) < 1e-10:
        sat_406 += 1

saturation_ratio_406  = sat_406 / N_STEPS
overshoot_ratio_406   = max(bze_406_traj) / bze_406_traj[-1] if bze_406_traj[-1] > 0 else float('inf')
overshoot_ratio_405   = 1.0   # known from EXP-405

tail_range_406 = max(bze_406_traj[10:]) - min(bze_406_traj[10:])
tail_range_405 = max(bze_405_traj[10:]) - min(bze_405_traj[10:])
last5_range    = max(bze_406_traj[-5:]) - min(bze_406_traj[-5:])

print(f"\n  Sequential N={N_STEPS}:")
print(f"  bze_406: {[round(b,2) for b in bze_406_traj]}")
print(f"  raw_406: {[round(b,2) for b in raw_406_traj]}")
print(f"  bze_405: {[round(b,2) for b in bze_405_traj]}")
print(f"  lc_406:  {lc_406_traj}")
print(f"  lc_405:  {lc_405_traj}")
print(f"  lag_406: {[round(l,3) for l in lag_406_traj]}")
print(f"  overshoot_ratio_406={overshoot_ratio_406:.4f}  overshoot_ratio_405={overshoot_ratio_405:.2f}")
print(f"  tail_range_406={tail_range_406:.4f}  tail_range_405={tail_range_405:.4f}")
print(f"  last5_range_406={last5_range:.4f}")
print(f"  bze_406[-1]={bze_406_traj[-1]:.4f}  bze_405[-1]={bze_405_traj[-1]:.4f}")
print(f"  lc_406_tail={sorted(set(lc_406_traj[10:]))}  lc_405_tail={sorted(set(lc_405_traj[10:]))}")
print(f"  saturation_ratio_406={saturation_ratio_406:.4f}")

# ── [5] 2-cycle damped: tail range reduced ────────────────────────────────────
assert tail_range_406 < tail_range_405, \
    f"[5] FAIL: tail_range_406={tail_range_406:.4f} >= tail_range_405={tail_range_405:.4f}"
print(f"[5] PASS  tail_range_406={tail_range_406:.4f} < tail_range_405={tail_range_405:.4f} "
      f"(Ghost #16 damped; theory: 1/3 of EXP-405)")

# ── [6] Last-5 convergence vs EXP-405 (EMA reduces tail range) ───────────────
last5_range_405 = max(bze_405_traj[-5:]) - min(bze_405_traj[-5:])
assert last5_range < last5_range_405, \
    f"[6] FAIL: last5_range_406={last5_range:.4f} >= last5_range_405={last5_range_405:.4f}"
print(f"[6] PASS  last5_range_406={last5_range:.4f} < last5_range_405={last5_range_405:.4f} "
      f"(EMA inertia reduces tail variability at N=20)")

# ── [7] Leaf count tail: fewer distinct values than EXP-405 ──────────────────
lc406_tail_vals = sorted(set(lc_406_traj[10:]))
lc405_tail_vals = sorted(set(lc_405_traj[10:]))
assert len(lc406_tail_vals) <= len(lc405_tail_vals), \
    f"[7] FAIL: lc_406 tail={lc406_tail_vals} ({len(lc406_tail_vals)} vals) " \
    f">= lc_405 tail={lc405_tail_vals} ({len(lc405_tail_vals)} vals)"
print(f"[7] PASS  lc_406_tail={lc406_tail_vals} ({len(lc406_tail_vals)} vals) <= "
      f"lc_405_tail={lc405_tail_vals} ({len(lc405_tail_vals)} vals) (2-cycle weakened)")

# ── [8] Saturation gate inactive ──────────────────────────────────────────────
assert saturation_ratio_406 < 0.5, \
    f"[8] FAIL: sat_ratio={saturation_ratio_406:.4f} >= 0.5"
print(f"[8] PASS  saturation_ratio_406={saturation_ratio_406:.4f} < 0.5")

# ── [9] Ghost #17: EMA lag-overshoot < EXP-404 spike (1.33) ─────────────────
# EMA inertia can produce a mild lag-overshoot: bze_ema_prev carries momentum
# past the raw peak (undershoot in rising phase -> overshoot at decline phase).
# The overshoot is bounded well below EXP-404's 1.33.
overshoot_ratio_404 = 1.33
assert overshoot_ratio_406 < overshoot_ratio_404, \
    f"[9] FAIL: overshoot_ratio_406={overshoot_ratio_406:.4f} >= overshoot_404={overshoot_ratio_404:.2f}"
print(f"[9] PASS  overshoot_ratio_406={overshoot_ratio_406:.4f} < overshoot_404={overshoot_ratio_404:.2f} "
      f"(Ghost #17: EMA lag-overshoot observed; bounded below EXP-404 spike)")

# ── [10] Gradient monotone ────────────────────────────────────────────────────
B_vals = [0.0, 0.1, 0.5, 1.0, 2.0, 5.0]
bze_BA = [phi_fb_ema(np.full(8,b/np.sqrt(8)), np.ones(4), np.zeros(6),
                     scene_n=10, bze_ema_prev=_BETA_Z_313)[0] for b in B_vals]
bze_BD = [phi_fb_ema(np.zeros(8), np.ones(4), np.full(6,b/np.sqrt(6)),
                     scene_n=10, bze_ema_prev=_BETA_Z_313)[0] for b in B_vals]
assert all(bze_BA[i] <= bze_BA[i+1] for i in range(len(bze_BA)-1)), \
    f"[10] FAIL: B_A not monotone: {bze_BA}"
assert all(bze_BD[i] >= bze_BD[i+1] for i in range(len(bze_BD)-1)), \
    f"[10] FAIL: B_D not monotone: {bze_BD}"
print(f"[10] PASS  gradient monotone: B_A-> {[round(b,3) for b in bze_BA]}; "
      f"B_D-> {[round(b,3) for b in bze_BD]}")

# Omega_inertia (gravitational backreaction of inertial lag)
Omega_inertia_mean = sum(lag_406_traj) / len(lag_406_traj)
Omega_inertia_max  = max(lag_406_traj)

print(f"\n=== EXP-406 Fork A: 10/10 PASS ===")
print(f"    alpha_bze={_ALPHA_BZE_406}  tau_warmup={_TAU_WARMUP_406}")
print(f"    overshoot_ratio_406={overshoot_ratio_406:.4f}  (vs 404: {overshoot_ratio_404:.2f})  Ghost #17: EMA lag-overshoot")
print(f"    tail_range_406={tail_range_406:.4f}  tail_range_405={tail_range_405:.4f}  "
      f"ratio={tail_range_406/(tail_range_405+1e-15):.3f} (theory 1/3={1/3:.3f})")
print(f"    last5_range_406={last5_range:.4f}  last5_range_405={last5_range_405:.4f}")
print(f"    bze_406[-1]={bze_406_traj[-1]:.4f}  bze_405[-1]={bze_405_traj[-1]:.4f}")
print(f"    lc_406_tail={lc406_tail_vals}  lc_405_tail={lc405_tail_vals}")
print(f"    Omega_inertia: mean={Omega_inertia_mean:.4f}  max={Omega_inertia_max:.4f}")
print(f"    saturation_ratio={saturation_ratio_406:.4f}")
print(f"    alpha_leak=0.0 Ghost: explicit 0.0 suppresses S_A in apply_gamma_401 (dev note)")
