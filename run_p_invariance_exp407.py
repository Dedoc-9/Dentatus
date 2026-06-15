"""
run_p_invariance_exp407.py — Fork B: EXP-407 P_yz Invariance

Protocol: exp407-v1
Declaration hash: 2dc29bcfbb1d7b02f65549f4d4750ac9b7af5603d4a726a3fa53347e67773f87

phi_fb_adaptive_ema reads ||S_A||, ||Z_A||, ||S_D|| (norms), scalar scene_n,
scalar bze_ema_prev. All inputs are P_yz-invariant -> phi_fb_adaptive_ema is
P_yz-invariant by construction. bze_ema_prev and alpha_eff are primary scalars:
same values for fwd and mir runs given identical cold start.

Tests [1-5]:
  [1]  declaration_hash
  [2]  bze_fwd(n) == bze_mir(n) for all n (phi_fb_adaptive_ema P_yz-invariant)
  [3]  B_A_fwd(n) == B_A_mir(n) for all n
  [4]  B_D_fwd(n) == B_D_mir(n) for all n
  [5]  leaf_count_fwd(n) == leaf_count_mir(n) for all n
"""
import sys, os, json, hashlib
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_407_recursive,
    _GAMMA_INF_A_407, _GAMMA_INF_D_407, _TAU_WARMUP_407,
    _ALPHA_MAX_407, _ALPHA_MIN_407, _TAU_ALPHA_407,
    _BETA_Z_MIN_407, _BETA_Z_313,
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
stalk_fwd  = np.array([1.,1.,1.,1., 0.5,0.5,0.5,1., 0.6,0.,0.8,kappa_seed,
                        0.,0.,0.,0.,0.,0.])
stalk_mir  = stalk_fwd.copy(); stalk_mir[4] = -stalk_fwd[4]   # P_yz: x -> -x

SHARED = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0,
              K_budget=2048, depth=0, focal_point=np.array([0.5,0.5,0.5]),
              B=np.array([1.0,0.5,0.3]), J_AC=np.eye(4), W_max=8,
              beta_Z_base=_BETA_Z_313,
              gamma_inf_A=_GAMMA_INF_A_407, gamma_inf_D=_GAMMA_INF_D_407,
              tau_warmup=_TAU_WARMUP_407,
              alpha_max=_ALPHA_MAX_407, alpha_min=_ALPHA_MIN_407,
              tau_alpha=_TAU_ALPHA_407, beta_Z_min=_BETA_Z_MIN_407)

N_STEPS = 20


def make_mu_stalk(stalk, S_A_init=None, S_C_init=None, S_D_init=None, S_init=None):
    prov  = Provenance(parent_ids=(), operator_id="seed_exp407_pyz", timestamp=now_iso())
    claim = Claim(provenance=prov, payload="scene:exp407:pyz",
                  stalk=stalk.copy(), t=0, bbox=(np.zeros(3), np.ones(3)))
    return MuState(
        t=0, claims={claim.id: claim}, entailments={},
        active=frozenset([claim.id]),
        S=np.array(S_init,   dtype=float) if S_init   is not None else np.zeros(12),
        alpha=ALPHA,
        S_A=np.array(S_A_init, dtype=float) if S_A_init is not None else np.zeros(8),
        S_C=np.array(S_C_init, dtype=float) if S_C_init is not None else np.zeros(4),
        S_D=np.array(S_D_init, dtype=float) if S_D_init is not None else np.zeros(6),
    )


bze_f_traj, bze_m_traj = [], []
BA_f_traj,  BA_m_traj  = [], []
BD_f_traj,  BD_m_traj  = [], []
lc_f_traj,  lc_m_traj  = [], []

mu_fwd = make_mu_stalk(stalk_fwd)
mu_mir = make_mu_stalk(stalk_mir)
bze_ema_f = float(_BETA_Z_313)   # primary scalar, fwd
bze_ema_m = float(_BETA_Z_313)   # primary scalar, mir (same cold start)

for n in range(N_STEPS):
    if n > 0:
        mu_fwd = make_mu_stalk(stalk_fwd,
            S_A_init=np.array(mu_fwd.S_A), S_C_init=np.array(mu_fwd.S_C),
            S_D_init=np.array(mu_fwd.S_D), S_init=np.array(mu_fwd.S))
        mu_mir = make_mu_stalk(stalk_mir,
            S_A_init=np.array(mu_mir.S_A), S_C_init=np.array(mu_mir.S_C),
            S_D_init=np.array(mu_mir.S_D), S_init=np.array(mu_mir.S))

    cid_f = next(iter(mu_fwd.active)); cid_m = next(iter(mu_mir.active))

    mu_fwd, _, _, bze_f, raw_f, BA_f, BD_f, _, _, aeff_f = apply_gamma_407_recursive(
        mu=mu_fwd, claim_id=cid_f, scene_n=n, bze_ema_prev=bze_ema_f, **SHARED)
    mu_mir, _, _, bze_m, raw_m, BA_m, BD_m, _, _, aeff_m = apply_gamma_407_recursive(
        mu=mu_mir, claim_id=cid_m, scene_n=n, bze_ema_prev=bze_ema_m, **SHARED)

    bze_ema_f = bze_f; bze_ema_m = bze_m

    bze_f_traj.append(bze_f); bze_m_traj.append(bze_m)
    BA_f_traj.append(BA_f);   BA_m_traj.append(BA_m)
    BD_f_traj.append(BD_f);   BD_m_traj.append(BD_m)
    lc_f_traj.append(len(mu_fwd.active)); lc_m_traj.append(len(mu_mir.active))

print(f"\n  P_yz sequential N={N_STEPS} (phi_fb_adaptive_ema):")
print(f"  bze_fwd: {[round(b,2) for b in bze_f_traj]}")
print(f"  bze_mir: {[round(b,2) for b in bze_m_traj]}")
print(f"  lc_fwd:  {lc_f_traj}")
print(f"  lc_mir:  {lc_m_traj}")

max_bze = max(abs(bze_f_traj[n]-bze_m_traj[n]) for n in range(N_STEPS))
assert max_bze < 1e-10, f"[2] FAIL: max|bze_fwd-bze_mir|={max_bze:.2e}"
print(f"[2] PASS  max|bze_fwd-bze_mir|={max_bze:.2e} (phi_fb_adaptive_ema P_yz-invariant)")

max_BA = max(abs(BA_f_traj[n]-BA_m_traj[n]) for n in range(N_STEPS))
assert max_BA < 1e-10, f"[3] FAIL: max|B_A_fwd-B_A_mir|={max_BA:.2e}"
print(f"[3] PASS  max|B_A_fwd-B_A_mir|={max_BA:.2e}")

max_BD = max(abs(BD_f_traj[n]-BD_m_traj[n]) for n in range(N_STEPS))
assert max_BD < 1e-10, f"[4] FAIL: max|B_D_fwd-B_D_mir|={max_BD:.2e}"
print(f"[4] PASS  max|B_D_fwd-B_D_mir|={max_BD:.2e}")

for n in range(N_STEPS):
    assert lc_f_traj[n] == lc_m_traj[n], \
        f"[5] FAIL: n={n} lc_fwd={lc_f_traj[n]} != lc_mir={lc_m_traj[n]}"
print(f"[5] PASS  leaf_count_fwd(n)==leaf_count_mir(n) for all n=0..{N_STEPS-1}")

print(f"\n=== EXP-407 Fork B: 5/5 PASS ===")
print(f"    max|bze_fwd-bze_mir|={max_bze:.2e}")
print(f"    max|B_A_fwd-B_A_mir|={max_BA:.2e}")
print(f"    max|B_D_fwd-B_D_mir|={max_BD:.2e}")
print(f"    alpha_min={_ALPHA_MIN_407}  alpha_max={_ALPHA_MAX_407}  tau_alpha={_TAU_ALPHA_407}")
