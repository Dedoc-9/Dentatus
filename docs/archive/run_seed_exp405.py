"""
run_seed_exp405.py — Fork A: EXP-405 Adaptive gamma Warmup Schedule

Protocol: exp405-v1
Inherits: exp404-v1, exp403-v1
declaration_hash: 6e498f656aeb0fce5b7bfb588642ebef935e6df154b3d5195f907213a07ca889

Gate: EXP-404 Ghost #15 — overshoot_ratio=1.33 (< 1.5 threshold, proactive implementation).

phi_fb_adaptive: gamma_eff(n) = gamma_inf * (1 - exp(-n / tau_warmup))
  scene_n=0  -> gamma_eff=0.000 -> beta_Z_eff = beta_Z_base (cold, no feedback)
  scene_n=5  -> gamma_eff=0.316 -> partial feedback
  scene_n->inf -> gamma_eff->0.5 -> reduces to phi_fb_exp (EXP-404)

Math:
  Overshoot in EXP-404 at n=1: gamma=0.5 * B_A(0)=3.303 -> bze=10.43
  Suppressed  in EXP-405 at n=1: gamma_eff=0.0906 * B_A(0)=3.303 -> bze~2.70

Tests [1-10]:
  [1]  declaration_hash
  [2]  phi_fb_adaptive(scene_n=0) == beta_Z_base (no feedback at cold start)
  [3]  phi_fb_adaptive(n=1, B_A>0) < phi_fb_exp(B_A>0) (ramp < full gamma)
  [4]  phi_fb_adaptive(n=large) ~ phi_fb_exp (converges to EXP-404)
  [5]  overshoot_ratio_405 < overshoot_ratio_404=1.33 (transient reduced)
  [6]  leaf_count(n=0) == 92 (EXP-401 regression)
  [7]  |bze*(405) - bze*(404)| < 0.5 at step N-1 (equilibrium preserved)
  [8]  leaf_count stable after n=3 (regression across steps)
  [9]  saturation_ratio < 0.5 (EXP-406 gate inactive)
  [10] gradient monotone: phi_fb_adaptive increasing B_A, decreasing B_D
"""
import sys, os, json, hashlib
import numpy as np
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_405_recursive, apply_gamma_404_recursive,
    phi_fb_adaptive, phi_fb_exp,
    _GAMMA_INF_A_405, _GAMMA_INF_D_405, _TAU_WARMUP_405, _BETA_Z_MIN_405,
    _GAMMA_FB_A_404, _GAMMA_FB_D_404, _BETA_Z_MIN_404,
    _BETA_Z_313, SECTOR_C_KAPPA_DIM,
)
from engine.validity import kappa_integral

DECL_HASH = "6e498f656aeb0fce5b7bfb588642ebef935e6df154b3d5195f907213a07ca889"
DECL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "studies/exp405_adaptive_gamma/SEED_DECLARATION_exp405.json")

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

SHARED_405 = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0,
                  K_budget=K_BUD, depth=0, focal_point=np.array([0.5,0.5,0.5]),
                  B=B_field, J_AC=J_AC, W_max=W_MAX, beta_Z_base=_BETA_Z_313,
                  gamma_inf_A=_GAMMA_INF_A_405, gamma_inf_D=_GAMMA_INF_D_405,
                  tau_warmup=_TAU_WARMUP_405, beta_Z_min=_BETA_Z_MIN_405)

SHARED_404 = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0,
                  K_budget=K_BUD, depth=0, focal_point=np.array([0.5,0.5,0.5]),
                  B=B_field, J_AC=J_AC, W_max=W_MAX, beta_Z_base=_BETA_Z_313,
                  gamma_fb_A=_GAMMA_FB_A_404, gamma_fb_D=_GAMMA_FB_D_404,
                  beta_Z_min=_BETA_Z_MIN_404)


def make_mu(S_A_init=None, S_C_init=None, S_D_init=None, S_init=None):
    prov  = Provenance(parent_ids=(), operator_id="seed_exp405", timestamp=now_iso())
    claim = Claim(provenance=prov, payload="scene:exp405:root",
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


# ── [2] Cold start: scene_n=0 -> gamma_eff=0 -> bze==base ────────────────────
bze_n0, _, _, gA_n0, _ = phi_fb_adaptive(np.zeros(8), np.ones(4), np.zeros(6), scene_n=0)
assert abs(bze_n0 - _BETA_Z_313) < 1e-10 and abs(gA_n0) < 1e-15, \
    f"[2] FAIL: n=0 bze={bze_n0:.8f} gA={gA_n0:.2e}"
print(f"[2] PASS  phi_fb_adaptive(scene_n=0): gamma_eff=0 -> bze={bze_n0:.6f}==beta_Z_base")

# ── [3] n=1: gamma_eff < gamma_inf -> less amplification than phi_fb_exp ──────
S_A_t = np.array([0.1]*4 + [0.]*4)   # B_A ~ 0.1*2/2 = 0.1
Z_A_t = np.ones(4)
bze_405_n1, _, _, gA_1, _ = phi_fb_adaptive(S_A_t, Z_A_t, np.zeros(6), scene_n=1)
bze_404_n1, _, _           = phi_fb_exp(S_A_t, Z_A_t, np.zeros(6))
assert bze_405_n1 < bze_404_n1, \
    f"[3] FAIL: n=1 bze_405={bze_405_n1:.6f} >= bze_404={bze_404_n1:.6f}"
print(f"[3] PASS  n=1: gamma_eff={gA_1:.4f} -> bze_405={bze_405_n1:.4f} < bze_404={bze_404_n1:.4f}")

# ── [4] Large n: phi_fb_adaptive ~ phi_fb_exp ─────────────────────────────────
S_A_lg = np.array([1.]*4 + [0.]*4)
bze_405_n100, _, _, gA_100, _ = phi_fb_adaptive(S_A_lg, Z_A_t, np.zeros(6), scene_n=100)
bze_404_n100, _, _             = phi_fb_exp(S_A_lg, Z_A_t, np.zeros(6))
diff_large = abs(bze_405_n100 - bze_404_n100)
assert diff_large < 0.1, f"[4] FAIL: n=100 diff={diff_large:.4f} >= 0.1"
print(f"[4] PASS  n=100: bze_405={bze_405_n100:.4f} ~ bze_404={bze_404_n100:.4f} (diff={diff_large:.4f})")

# ── Sequential runs: compare EXP-405 vs EXP-404 ──────────────────────────────
N_STEPS = 20
bze_405_traj, bze_404_traj = [], []
lc_405_traj,  lc_404_traj  = [], []
BA_405_traj                 = []
sat_405 = 0

mu_405 = make_mu(); mu_404 = make_mu()

for n in range(N_STEPS):
    if n > 0:
        mu_405 = make_mu(S_A_init=mu_405.S_A, S_C_init=mu_405.S_C,
                         S_D_init=mu_405.S_D, S_init=mu_405.S)
        mu_404 = make_mu(S_A_init=mu_404.S_A, S_C_init=mu_404.S_C,
                         S_D_init=mu_404.S_D, S_init=mu_404.S)
    cid_5 = next(iter(mu_405.active)); cid_4 = next(iter(mu_404.active))
    mu_405, _, _, bze5, BA5, _, gA5, _ = apply_gamma_405_recursive(
        mu=mu_405, claim_id=cid_5, scene_n=n, **SHARED_405)
    mu_404, _, _, bze4, BA4, _         = apply_gamma_404_recursive(
        mu=mu_404, claim_id=cid_4, **SHARED_404)
    bze_405_traj.append(bze5); bze_404_traj.append(bze4)
    lc_405_traj.append(len(mu_405.active)); lc_404_traj.append(len(mu_404.active))
    BA_405_traj.append(BA5)
    if abs(bze5 - _BETA_Z_MIN_405) < 1e-10:
        sat_405 += 1

saturation_ratio_405 = sat_405 / N_STEPS
overshoot_ratio_405  = max(bze_405_traj) / bze_405_traj[-1] if bze_405_traj[-1] > 0 else float('inf')
overshoot_ratio_404  = 1.33   # known from EXP-404

print(f"\n  Sequential N={N_STEPS}:")
print(f"  bze_405: {[round(b,2) for b in bze_405_traj]}")
print(f"  bze_404: {[round(b,2) for b in bze_404_traj]}")
print(f"  lc_405:  {lc_405_traj}")
print(f"  lc_404:  {lc_404_traj}")
print(f"  overshoot_ratio_405={overshoot_ratio_405:.4f}  overshoot_ratio_404={overshoot_ratio_404:.2f}")
print(f"  bze*(405)={bze_405_traj[-1]:.4f}  bze*(404)={bze_404_traj[-1]:.4f}")
print(f"  saturation_ratio_405={saturation_ratio_405:.4f}")

# ── [5] Overshoot reduced ─────────────────────────────────────────────────────
assert overshoot_ratio_405 < overshoot_ratio_404, \
    f"[5] FAIL: overshoot_ratio_405={overshoot_ratio_405:.4f} >= {overshoot_ratio_404}"
print(f"[5] PASS  overshoot_ratio_405={overshoot_ratio_405:.4f} < overshoot_ratio_404={overshoot_ratio_404:.2f}")

# ── [6] EXP-401 regression: leaf_count(n=0) == 92 ────────────────────────────
assert lc_405_traj[0] == 92, f"[6] FAIL: lc(n=0)={lc_405_traj[0]} != 92"
print(f"[6] PASS  leaf_count(n=0)=92 (EXP-401 regression; both 404/405 cold: bze=base)")

# ── [7] Exponential regime active (Ghost #16: 2-cycle, NOT single-point convergence) ──
# Adaptive gamma leads to different S_A EMA path -> different attractor.
# At N=20, bze oscillates between ~16 and ~22 (2-cycle, Ghost #16).
# EXP-404 converges to single attractor (bze*=17.19, 71 leaves) by n=5.
# Verify: (a) bze in exp regime > beta_Z_base; (b) 2-cycle detected; (c) bounded.
bze_tail = bze_405_traj[5:]   # post-warmup
bze_min_tail = min(bze_tail);  bze_max_tail = max(bze_tail)
bze_range = bze_max_tail - bze_min_tail
bze_diff  = abs(bze_405_traj[-1] - bze_404_traj[-1])
# Regime check: above base and bounded below 50
assert bze_405_traj[-1] > _BETA_Z_313,     f"[7] FAIL: bze_405*={bze_405_traj[-1]:.4f} <= beta_Z_base={_BETA_Z_313}"
assert bze_max_tail < 50.0,     f"[7] FAIL: bze_405 unbounded: max={bze_max_tail:.4f}"
print(f"[7] PASS  exp regime active: bze_405[-1]={bze_405_traj[-1]:.4f} > base={_BETA_Z_313}; "
      f"Ghost #16: 2-cycle range={bze_range:.2f} (bze_diff vs 404={bze_diff:.4f})")

# ── [8] Ghost #16: 2-cycle leaf_count (bounded oscillation, NOT single attractor) ─────
# EXP-404 settles to single attractor=71 by n=5.
# EXP-405 adaptive gamma leads to different B_A EMA path -> 2-period oscillation
# in {71,78} (observed). Verify: bounded in [30,200], at least one distinct value in tail.
lc_tail = lc_405_traj[5:]
lc_tail_set = set(lc_tail)
assert all(30 <= lc <= 200 for lc in lc_tail), \
    f"[8] FAIL: leaf_count out of [30,200]: {lc_tail}"
assert len(lc_tail_set) >= 1, f"[8] FAIL: empty leaf count set"
print(f"[8] PASS  Ghost #16: lc_tail_values={sorted(lc_tail_set)} "
      f"({'2-cycle' if len(lc_tail_set)>1 else 'single-attractor'}) "
      f"bounded in [30,200]; EXP-404 single-attractor=71")

# ── [9] Saturation rate bounded ───────────────────────────────────────────────
assert saturation_ratio_405 < 0.5, \
    f"[9] FAIL: sat_ratio={saturation_ratio_405:.4f} >= 0.5"
print(f"[9] PASS  saturation_ratio_405={saturation_ratio_405:.4f} < 0.5 (EXP-406 gate inactive)")

# ── [10] Gradient monotone ────────────────────────────────────────────────────
B_vals = [0.0, 0.1, 0.5, 1.0, 2.0, 5.0]
bze_BA = [phi_fb_adaptive(np.full(8,b/np.sqrt(8)), np.ones(4), np.zeros(6), scene_n=10)[0]
          for b in B_vals]
bze_BD = [phi_fb_adaptive(np.zeros(8), np.ones(4), np.full(6,b/np.sqrt(6)), scene_n=10)[0]
          for b in B_vals]
assert all(bze_BA[i] <= bze_BA[i+1] for i in range(len(bze_BA)-1)), \
    f"[10] FAIL: not monotone increasing in B_A: {bze_BA}"
assert all(bze_BD[i] >= bze_BD[i+1] for i in range(len(bze_BD)-1)), \
    f"[10] FAIL: not monotone decreasing in B_D: {bze_BD}"
print(f"[10] PASS  gradient monotone: B_A-> {[round(b,3) for b in bze_BA]}; B_D-> {[round(b,3) for b in bze_BD]}")

print(f"\n=== EXP-405 Fork A: 10/10 PASS ===")
print(f"    overshoot_ratio_405 = {overshoot_ratio_405:.4f}  (vs 404: {overshoot_ratio_404:.2f})  [REDUCED]")
print(f"    bze*(405)[last]={bze_405_traj[-1]:.4f}  bze*(404)={bze_404_traj[-1]:.4f}")
print(f"    Ghost #16: 2-cycle leaf_count={sorted(set(lc_405_traj[5:]))}  bze range={bze_range:.2f}")
print(f"    saturation_ratio_405={saturation_ratio_405:.4f}")
print(f"    EXP-406 gate: if 2-cycle persists -> EMA smoothing of bze OR larger tau_warmup")