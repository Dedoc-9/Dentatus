"""
run_p_invariance_exp501.py — Fork B: EXP-501 P_yz Invariance

Protocol: exp501-v1
Declaration hash: bfbf52c2977f436a78f1136555a0e46d00eae43eb95344fc679223961fa60a8b

phi_ent_observe reads only norms and bbox extents (all P_yz-invariant).
F_ij commutes with the P_yz stalk transform (both are diagonal sign operators).
Proof: face adjacency is determined by |hi-lo| extents and overlap — P_yz-invariant.
      F^C_k and F^D_k commute with R_pyz because all three are diagonal on the same dims.

Tests [1-5]:
  [1]  declaration_hash
  [2]  max|B_ent_fwd - B_ent_mir| < 1e-10 for all n
  [3]  max|lambda_2_fwd - lambda_2_mir| < 1e-10 for all n
  [4]  N_edges_fwd == N_edges_mir for all n
  [5]  max|G_ent_norm_fwd - G_ent_norm_mir| < 1e-10 for all n
"""
import sys, os, json, hashlib
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_409_recursive,
    phi_ent_observe,
    _ALPHA_DISC_409, _ALPHA_MAINT_409, _BETA_THRESHOLD_409,
    _GAMMA_INF_A_409, _GAMMA_INF_D_409, _TAU_WARMUP_409,
    _BETA_Z_MIN_409, _BETA_Z_313,
    _ALPHA_ENT_501,
)
from engine.validity import kappa_integral

DECL_HASH = "bfbf52c2977f436a78f1136555a0e46d00eae43eb95344fc679223961fa60a8b"
DECL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "studies/exp501_manifold_observation/SEED_DECLARATION_exp501.json")

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
stalk_mir  = stalk_fwd.copy()
stalk_mir[4] = -stalk_fwd[4]   # P_yz: x → -x  (Sector B x-component)

SHARED = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0,
              K_budget=2048, depth=0, focal_point=np.array([0.5,0.5,0.5]),
              B=np.array([1.0,0.5,0.3]), J_AC=np.eye(4), W_max=8,
              beta_Z_base=_BETA_Z_313,
              gamma_inf_A=_GAMMA_INF_A_409, gamma_inf_D=_GAMMA_INF_D_409,
              tau_warmup=_TAU_WARMUP_409,
              alpha_disc=_ALPHA_DISC_409, alpha_maint=_ALPHA_MAINT_409,
              beta_threshold=_BETA_THRESHOLD_409, beta_Z_min=_BETA_Z_MIN_409)

N_STEPS = 20

def make_mu(stalk, S_A=None, S_C=None, S_D=None, S=None):
    prov  = Provenance(parent_ids=(), operator_id="seed_exp501_pyz", timestamp=now_iso())
    claim = Claim(provenance=prov, payload="scene:exp501:pyz",
                  stalk=stalk.copy(), t=0, bbox=(np.zeros(3), np.ones(3)))
    return MuState(
        t=0, claims={claim.id: claim}, entailments={},
        active=frozenset([claim.id]),
        S=np.array(S, dtype=float) if S is not None else np.zeros(12),
        alpha=ALPHA,
        S_A=np.array(S_A, dtype=float) if S_A is not None else np.zeros(8),
        S_C=np.array(S_C, dtype=float) if S_C is not None else np.zeros(4),
        S_D=np.array(S_D, dtype=float) if S_D is not None else np.zeros(6),
    )

B_ent_f_traj, B_ent_m_traj = [], []
lam2_f_traj,  lam2_m_traj  = [], []
ne_f_traj,    ne_m_traj     = [], []
G_norm_f_traj, G_norm_m_traj = [], []

mu_f = make_mu(stalk_fwd); mu_m = make_mu(stalk_mir)
bze_f = float(_BETA_Z_313); mnt_f = False
bze_m = float(_BETA_Z_313); mnt_m = False

# Warm up EXP-409 dynamics
for n in range(N_STEPS):
    if n > 0:
        mu_f = make_mu(stalk_fwd, S_A=np.array(mu_f.S_A), S_C=np.array(mu_f.S_C),
                       S_D=np.array(mu_f.S_D), S=np.array(mu_f.S))
        mu_m = make_mu(stalk_mir, S_A=np.array(mu_m.S_A), S_C=np.array(mu_m.S_C),
                       S_D=np.array(mu_m.S_D), S=np.array(mu_m.S))
    cf = next(iter(mu_f.active)); cm = next(iter(mu_m.active))
    (mu_f,_,_,bze_f,_,_,_,_,_,_,mnt_f) = apply_gamma_409_recursive(
        mu=mu_f, claim_id=cf, scene_n=n, bze_ema_prev=bze_f, maint_latched=mnt_f, **SHARED)
    (mu_m,_,_,bze_m,_,_,_,_,_,_,mnt_m) = apply_gamma_409_recursive(
        mu=mu_m, claim_id=cm, scene_n=n, bze_ema_prev=bze_m, maint_latched=mnt_m, **SHARED)

# Observation loop
S_ent_f = {cid: 0.0 for cid in mu_f.active}
S_ent_m = {cid: 0.0 for cid in mu_m.active}

for n in range(N_STEPS):
    if n > 0:
        mu_f = make_mu(stalk_fwd, S_A=np.array(mu_f.S_A), S_C=np.array(mu_f.S_C),
                       S_D=np.array(mu_f.S_D), S=np.array(mu_f.S))
        mu_m = make_mu(stalk_mir, S_A=np.array(mu_m.S_A), S_C=np.array(mu_m.S_C),
                       S_D=np.array(mu_m.S_D), S=np.array(mu_m.S))
        cf = next(iter(mu_f.active)); cm = next(iter(mu_m.active))
        (mu_f,_,_,bze_f,_,_,_,_,_,_,mnt_f) = apply_gamma_409_recursive(
            mu=mu_f, claim_id=cf, scene_n=N_STEPS+n,
            bze_ema_prev=bze_f, maint_latched=mnt_f, **SHARED)
        (mu_m,_,_,bze_m,_,_,_,_,_,_,mnt_m) = apply_gamma_409_recursive(
            mu=mu_m, claim_id=cm, scene_n=N_STEPS+n,
            bze_ema_prev=bze_m, maint_latched=mnt_m, **SHARED)

    Zf = {c: np.array(mu_f.claims[c].stalk,dtype=float) for c in mu_f.active}
    Zm = {c: np.array(mu_m.claims[c].stalk,dtype=float) for c in mu_m.active}
    bf = {c: mu_f.claims[c].bbox for c in mu_f.active}
    bm = {c: mu_m.claims[c].bbox for c in mu_m.active}
    Sf_n = {c: S_ent_f.get(c, 0.0) for c in mu_f.active}
    Sm_n = {c: S_ent_m.get(c, 0.0) for c in mu_m.active}

    G_pc_f, S_ent_f, B_f, ne_f, l2_f, edges_f = phi_ent_observe(Zf, bf, Sf_n)
    G_pc_m, S_ent_m, B_m, ne_m, l2_m, edges_m = phi_ent_observe(Zm, bm, Sm_n)

    G_norm_f = sum(G_pc_f.values())
    G_norm_m = sum(G_pc_m.values())

    B_ent_f_traj.append(B_f); B_ent_m_traj.append(B_m)
    lam2_f_traj.append(l2_f); lam2_m_traj.append(l2_m)
    ne_f_traj.append(ne_f);   ne_m_traj.append(ne_m)
    G_norm_f_traj.append(G_norm_f); G_norm_m_traj.append(G_norm_m)

print(f"\n  P_yz sequential N={N_STEPS} (phi_ent_observe):")
print(f"  B_ent_fwd: {[round(b,4) for b in B_ent_f_traj]}")
print(f"  B_ent_mir: {[round(b,4) for b in B_ent_m_traj]}")
print(f"  N_edges_fwd: {ne_f_traj}")
print(f"  N_edges_mir: {ne_m_traj}")

max_B  = max(abs(B_ent_f_traj[n]-B_ent_m_traj[n]) for n in range(N_STEPS))
assert max_B < 1e-10, f"[2] FAIL: max|B_ent_fwd-B_ent_mir|={max_B:.2e}"
print(f"[2] PASS  max|B_ent_fwd-B_ent_mir|={max_B:.2e} (phi_ent_observe P_yz-invariant)")

max_L2 = max(abs(lam2_f_traj[n]-lam2_m_traj[n]) for n in range(N_STEPS))
assert max_L2 < 1e-10, f"[3] FAIL: max|lambda_2_fwd-lambda_2_mir|={max_L2:.2e}"
print(f"[3] PASS  max|lambda_2_fwd-lambda_2_mir|={max_L2:.2e}")

for n in range(N_STEPS):
    assert ne_f_traj[n] == ne_m_traj[n], f"[4] FAIL n={n}: N_edges_fwd={ne_f_traj[n]} != mir={ne_m_traj[n]}"
print(f"[4] PASS  N_edges_fwd==N_edges_mir for all n=0..{N_STEPS-1}")

max_G = max(abs(G_norm_f_traj[n]-G_norm_m_traj[n]) for n in range(N_STEPS))
assert max_G < 1e-10, f"[5] FAIL: max|G_ent_norm_fwd-G_ent_norm_mir|={max_G:.2e}"
print(f"[5] PASS  max|G_ent_norm_fwd-G_ent_norm_mir|={max_G:.2e}")

print(f"\n=== EXP-501 Fork B: 5/5 PASS ===")
print(f"    max|B_ent_fwd-mir|={max_B:.2e}")
print(f"    max|lambda_2_fwd-mir|={max_L2:.2e}")
print(f"    max|G_ent_norm_fwd-mir|={max_G:.2e}")
print(f"    alpha_ent={_ALPHA_ENT_501}  XOR rule P_yz-symmetric")
