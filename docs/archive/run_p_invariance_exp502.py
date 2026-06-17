"""
run_p_invariance_exp502.py -- Fork B: EXP-502 P_yz Invariance (degree-normalized firewall)

Protocol: exp502-v1
Declaration hash: 0979f7f520421a28bc37a7e7aec9e8f7e946f4adb459f55b64718188ea966af8

Degree normalization divides by sqrt(deg(i)); deg(i) is a P_yz graph-isomorphism
invariant, so B_ent_normalized, the is_manifold_501 gate, and the per-claim worst
ratio are all P_yz-invariant at machine precision.

Tests [1-5]:
  [1] declaration_hash
  [2] max|B_ent_norm_fwd - B_ent_norm_mir| < 1e-10
  [3] max|lambda_2_fwd - lambda_2_mir| < 1e-10
  [4] is_manifold_501_fwd == is_manifold_501_mir for all n
  [5] max|worst_ratio_fwd - worst_ratio_mir| < 1e-10
"""
import sys, os, json, hashlib
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_409_recursive, phi_ent_observe,
    _ALPHA_DISC_409, _ALPHA_MAINT_409, _BETA_THRESHOLD_409,
    _GAMMA_INF_A_409, _GAMMA_INF_D_409, _TAU_WARMUP_409,
    _BETA_Z_MIN_409, _BETA_Z_313, _ALPHA_ENT_501,
)
from engine.validity import kappa_integral, is_manifold_501, is_manifold_501_perclaim, EPS_MANIFOLD_502

DECL_HASH = "0979f7f520421a28bc37a7e7aec9e8f7e946f4adb459f55b64718188ea966af8"
DECL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "studies/exp502_manifold_firewall/SEED_DECLARATION_exp502.json")
with open(DECL_PATH) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
canon = json.dumps(decl, sort_keys=True, separators=(",", ":"))
assert stored == hashlib.sha256(canon.encode()).hexdigest() == DECL_HASH
print(f"[1] PASS  declaration_hash = {DECL_HASH[:16]}...")

bbox = (np.zeros(3), np.ones(3))
kappa_seed = kappa_integral(bbox)
stalk_fwd = np.array([1.,1.,1.,1., 0.5,0.5,0.5,1., 0.6,0.,0.8,kappa_seed, 0.,0.,0.,0.,0.,0.])
stalk_mir = stalk_fwd.copy(); stalk_mir[4] = -stalk_fwd[4]

SHARED = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0,
              K_budget=2048, depth=0, focal_point=np.array([0.5,0.5,0.5]),
              B=np.array([1.0,0.5,0.3]), J_AC=np.eye(4), W_max=8,
              beta_Z_base=_BETA_Z_313, gamma_inf_A=_GAMMA_INF_A_409, gamma_inf_D=_GAMMA_INF_D_409,
              tau_warmup=_TAU_WARMUP_409, alpha_disc=_ALPHA_DISC_409, alpha_maint=_ALPHA_MAINT_409,
              beta_threshold=_BETA_THRESHOLD_409, beta_Z_min=_BETA_Z_MIN_409)
N_STEPS = 20

def make_mu(stalk, S_A=None, S_C=None, S_D=None, S=None):
    prov = Provenance(parent_ids=(), operator_id="seed_exp502_pyz", timestamp=now_iso())
    claim = Claim(provenance=prov, payload="scene:exp502:pyz", stalk=stalk.copy(), t=0, bbox=(np.zeros(3),np.ones(3)))
    return MuState(t=0, claims={claim.id: claim}, entailments={}, active=frozenset([claim.id]),
        S=np.array(S,float) if S is not None else np.zeros(12), alpha=ALPHA,
        S_A=np.array(S_A,float) if S_A is not None else np.zeros(8),
        S_C=np.array(S_C,float) if S_C is not None else np.zeros(4),
        S_D=np.array(S_D,float) if S_D is not None else np.zeros(6))

mu_f = make_mu(stalk_fwd); mu_m = make_mu(stalk_mir)
bze_f = bze_m = float(_BETA_Z_313); mnt_f = mnt_m = False
for n in range(N_STEPS):
    if n > 0:
        mu_f = make_mu(stalk_fwd, mu_f.S_A, mu_f.S_C, mu_f.S_D, mu_f.S)
        mu_m = make_mu(stalk_mir, mu_m.S_A, mu_m.S_C, mu_m.S_D, mu_m.S)
    cf = next(iter(mu_f.active)); cm = next(iter(mu_m.active))
    (mu_f,_,_,bze_f,_,_,_,_,_,_,mnt_f) = apply_gamma_409_recursive(mu=mu_f, claim_id=cf, scene_n=n, bze_ema_prev=bze_f, maint_latched=mnt_f, **SHARED)
    (mu_m,_,_,bze_m,_,_,_,_,_,_,mnt_m) = apply_gamma_409_recursive(mu=mu_m, claim_id=cm, scene_n=n, bze_ema_prev=bze_m, maint_latched=mnt_m, **SHARED)

Bf_t, Bm_t, l2f_t, l2m_t, gf_t, gm_t, wf_t, wm_t = [], [], [], [], [], [], [], []
Sf = {c:0.0 for c in mu_f.active}; Sm = {c:0.0 for c in mu_m.active}
for n in range(N_STEPS):
    Zf = {c: np.array(mu_f.claims[c].stalk,float) for c in mu_f.active}
    Zm = {c: np.array(mu_m.claims[c].stalk,float) for c in mu_m.active}
    bf = {c: mu_f.claims[c].bbox for c in mu_f.active}
    bm = {c: mu_m.claims[c].bbox for c in mu_m.active}
    Znf = float(np.linalg.norm([np.linalg.norm(Zf[c]) for c in sorted(Zf)]))
    Znm = float(np.linalg.norm([np.linalg.norm(Zm[c]) for c in sorted(Zm)]))
    Gf, Sf, Bf, nef, l2f, edf = phi_ent_observe(Zf, bf, {c:Sf.get(c,0.) for c in mu_f.active}, degree_normalize=True)
    Gm, Sm, Bm, nem, l2m, edm = phi_ent_observe(Zm, bm, {c:Sm.get(c,0.) for c in mu_m.active}, degree_normalize=True)
    _, _, wf = is_manifold_501_perclaim(Gf, Znf)
    _, _, wm = is_manifold_501_perclaim(Gm, Znm)
    Bf_t.append(Bf); Bm_t.append(Bm); l2f_t.append(l2f); l2m_t.append(l2m)
    gf_t.append(is_manifold_501(Bf)); gm_t.append(is_manifold_501(Bm)); wf_t.append(wf); wm_t.append(wm)

max_B = max(abs(Bf_t[n]-Bm_t[n]) for n in range(N_STEPS))
assert max_B < 1e-10, f"[2] FAIL {max_B:.2e}"
print(f"[2] PASS  max|B_ent_norm_fwd-mir|={max_B:.2e}")
max_L = max(abs(l2f_t[n]-l2m_t[n]) for n in range(N_STEPS))
assert max_L < 1e-10, f"[3] FAIL {max_L:.2e}"
print(f"[3] PASS  max|lambda_2_fwd-mir|={max_L:.2e}")
assert all(gf_t[n]==gm_t[n] for n in range(N_STEPS)), "[4] FAIL gate asymmetry"
print(f"[4] PASS  is_manifold_501_fwd == is_manifold_501_mir for all n  (all={all(gf_t)})")
max_W = max(abs(wf_t[n]-wm_t[n]) for n in range(N_STEPS))
assert max_W < 1e-10, f"[5] FAIL {max_W:.2e}"
print(f"[5] PASS  max|worst_ratio_fwd-mir|={max_W:.2e}")

print(f"\n=== EXP-502 Fork B: 5/5 PASS ===")
print(f"    max|B_ent_norm_fwd-mir|={max_B:.2e}")
print(f"    max|lambda_2_fwd-mir|={max_L:.2e}")
print(f"    gate P_yz-symmetric; max|worst_ratio_fwd-mir|={max_W:.2e}")
print(f"    eps_manifold={EPS_MANIFOLD_502}  degree_normalize=True  Ghost #22 P_yz-preserved")
