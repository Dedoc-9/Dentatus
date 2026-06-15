"""
run_p_invariance_exp404.py — Fork B: EXP-404 P_yz Invariance

Protocol: exp404-v1
declaration_hash: e7447ec6a65022a25d426a8f0b796ef18292d6cf3f85047c2239b004d225e67c

P_yz reflection: R = diag(-1, 1, 1) on Sector B (stalk[4] -> -stalk[4]).
phi_fb_exp reads ||S_A||, ||Z_A||, ||S_D|| — all norms are P_yz-invariant.
Therefore phi_fb_exp is P_yz-invariant by construction.

Tests [1-5]:
  [1]  declaration_hash
  [2]  beta_Z_eff_fwd(n) == beta_Z_eff_mir(n) for all n=0..N-1 (phi_fb_exp P_yz-invariant)
  [3]  B_A_fwd(n) == B_A_mir(n) for all n (S_A P_yz-invariant)
  [4]  B_D_fwd(n) == B_D_mir(n) for all n (S_D norm P_yz-invariant)
  [5]  leaf_count_fwd(n) == leaf_count_mir(n) for all n (expansion P_yz-symmetric)
"""
import sys, os, json, hashlib
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_404_recursive,
    _GAMMA_FB_A_404, _GAMMA_FB_D_404, _BETA_Z_MIN_404,
    _BETA_Z_313, SECTOR_C_KAPPA_DIM,
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

stalk_fwd = np.array([1., 1., 1., 1.,
                       0.5,  0.5, 0.5, 1.,
                       0.6,  0.,  0.8, kappa_seed,
                       0.,   0.,  0.,  0., 0., 0.])
stalk_mir = stalk_fwd.copy()
stalk_mir[4] = -stalk_fwd[4]   # P_yz: x -> -x

B_field = np.array([1.0, 0.5, 0.3])
J_AC    = np.eye(4)
W_MAX   = 8
K_BUD   = 2048

SHARED = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0,
              K_budget=K_BUD, depth=0, focal_point=np.array([0.5, 0.5, 0.5]),
              B=B_field, J_AC=J_AC, W_max=W_MAX,
              beta_Z_base=_BETA_Z_313,
              gamma_fb_A=_GAMMA_FB_A_404, gamma_fb_D=_GAMMA_FB_D_404,
              beta_Z_min=_BETA_Z_MIN_404)

N_STEPS = 20


def make_mu_stalk(stalk, S_A_init=None, S_C_init=None, S_D_init=None, S_init=None):
    prov  = Provenance(parent_ids=(), operator_id="seed_exp404_pyz", timestamp=now_iso())
    claim = Claim(provenance=prov, payload="scene:exp404:pyz",
                  stalk=stalk.copy(), t=0, bbox=bbox)
    return MuState(
        t=0, claims={claim.id: claim}, entailments={},
        active=frozenset([claim.id]),
        S=np.array(S_init,   dtype=float) if S_init   is not None else np.zeros(12),
        alpha=ALPHA,
        S_A=np.array(S_A_init, dtype=float) if S_A_init is not None else np.zeros(8),
        S_C=np.array(S_C_init, dtype=float) if S_C_init is not None else np.zeros(4),
        S_D=np.array(S_D_init, dtype=float) if S_D_init is not None else np.zeros(6),
    )


bze_fwd_traj, bze_mir_traj = [], []
BA_fwd_traj,  BA_mir_traj  = [], []
BD_fwd_traj,  BD_mir_traj  = [], []
lc_fwd_traj,  lc_mir_traj  = [], []

mu_fwd = make_mu_stalk(stalk_fwd)
mu_mir = make_mu_stalk(stalk_mir)

for n in range(N_STEPS):
    if n > 0:
        mu_fwd = make_mu_stalk(stalk_fwd,
            S_A_init=mu_fwd.S_A, S_C_init=mu_fwd.S_C,
            S_D_init=mu_fwd.S_D, S_init=mu_fwd.S)
        mu_mir = make_mu_stalk(stalk_mir,
            S_A_init=mu_mir.S_A, S_C_init=mu_mir.S_C,
            S_D_init=mu_mir.S_D, S_init=mu_mir.S)

    cid_f = next(iter(mu_fwd.active))
    cid_m = next(iter(mu_mir.active))

    mu_fwd, _, _, bze_f, BA_f, BD_f = apply_gamma_404_recursive(
        mu=mu_fwd, claim_id=cid_f, **SHARED)
    mu_mir, _, _, bze_m, BA_m, BD_m = apply_gamma_404_recursive(
        mu=mu_mir, claim_id=cid_m, **SHARED)

    bze_fwd_traj.append(bze_f); bze_mir_traj.append(bze_m)
    BA_fwd_traj.append(BA_f);   BA_mir_traj.append(BA_m)
    BD_fwd_traj.append(BD_f);   BD_mir_traj.append(BD_m)
    lc_fwd_traj.append(len(mu_fwd.active))
    lc_mir_traj.append(len(mu_mir.active))

print(f"\n  P_yz sequential N={N_STEPS} (phi_fb_exp):")
print(f"  bze_fwd: {[round(b,2) for b in bze_fwd_traj]}")
print(f"  bze_mir: {[round(b,2) for b in bze_mir_traj]}")
print(f"  lc_fwd: {lc_fwd_traj}")
print(f"  lc_mir: {lc_mir_traj}")

# ── [2] beta_Z_eff P_yz-invariant ─────────────────────────────────────────────
max_bze = max(abs(bze_fwd_traj[n] - bze_mir_traj[n]) for n in range(N_STEPS))
assert max_bze < 1e-10, f"[2] FAIL: max|bze_fwd-bze_mir|={max_bze:.2e}"
print(f"[2] PASS  max|bze_fwd-bze_mir| = {max_bze:.2e} (phi_fb_exp P_yz-invariant)")

# ── [3] B_A P_yz-invariant ────────────────────────────────────────────────────
max_BA = max(abs(BA_fwd_traj[n] - BA_mir_traj[n]) for n in range(N_STEPS))
assert max_BA < 1e-10, f"[3] FAIL: max|B_A_fwd-B_A_mir|={max_BA:.2e}"
print(f"[3] PASS  max|B_A_fwd-B_A_mir| = {max_BA:.2e} (S_A P_yz-invariant)")

# ── [4] B_D P_yz-invariant ────────────────────────────────────────────────────
max_BD = max(abs(BD_fwd_traj[n] - BD_mir_traj[n]) for n in range(N_STEPS))
assert max_BD < 1e-10, f"[4] FAIL: max|B_D_fwd-B_D_mir|={max_BD:.2e}"
print(f"[4] PASS  max|B_D_fwd-B_D_mir| = {max_BD:.2e} (S_D norm P_yz-invariant)")

# ── [5] Leaf count P_yz-symmetric ─────────────────────────────────────────────
for n in range(N_STEPS):
    assert lc_fwd_traj[n] == lc_mir_traj[n], \
        f"[5] FAIL: step {n} lc_fwd={lc_fwd_traj[n]} != lc_mir={lc_mir_traj[n]}"
print(f"[5] PASS  leaf_count_fwd(n)==leaf_count_mir(n) for all n=0..{N_STEPS-1}")

print("\n=== EXP-404 Fork B: 5/5 PASS ===")
