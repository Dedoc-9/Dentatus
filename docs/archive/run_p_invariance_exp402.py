"""
run_p_invariance_exp402.py — Fork B: EXP-402 P_yz Invariance

Protocol: exp402-v1
declaration_hash: d933ad3ba860b601137cf7159b2485b2e86e1fc12b8939bce9bc1a08c3678407

P_yz invariance chain for Phi_fb:
  B_A = norm(S_A)/(norm(Z_A)+eps) — norm is P_yz-invariant
  B_D = norm(S_D)/(norm(Z_A)+eps) — norm(S_D) P_yz-invariant (EXP-401 Fork B)
  => beta_Z_eff P_yz-invariant
  => Zeeman weights identical under fwd/mir
  => All EXP-401 tensor covariance properties inherited

Tests [1-5]:
  [1]  declaration_hash
  [2]  beta_Z_eff_fwd == beta_Z_eff_mir (delta < 1e-12)
  [3]  fwd_leaves == mir_leaves
  [4]  Omega_AC P_yz-invariant (inherited EXP-316)
  [5]  S_D tensor covariance: S_D[3]_mir=-S_D[3]_fwd, S_D[4]_mir=-S_D[4]_fwd, S_D[5]_mir=S_D[5]_fwd
"""
import sys, os, json, hashlib
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_402_recursive, p_yz_stalk_401,
    _GAMMA_FB_A_402, _GAMMA_FB_D_402, _BETA_Z_MIN_402, _ALPHA_D_401,
    _BETA_Z_313, SECTOR_C_KAPPA_DIM,
)
from engine.validity import kappa_integral

DECL_HASH = "d933ad3ba860b601137cf7159b2485b2e86e1fc12b8939bce9bc1a08c3678407"
DECL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "studies/exp402_zeeman_homeostasis/SEED_DECLARATION_exp402.json")

with open(DECL_PATH) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
canon  = json.dumps(decl, sort_keys=True, separators=(",", ":"))
assert hashlib.sha256(canon.encode()).hexdigest() == DECL_HASH
print(f"[1] PASS  declaration_hash = {DECL_HASH[:16]}...")

bK         = SECTOR_C_KAPPA_DIM
B_FWD      = np.array([1.0, 0.5, 0.3])
B_MIR      = np.array([-1.0, 0.5, 0.3])
R_pyz      = np.diag([-1.0, 1.0, 1.0])
bbox_fwd   = (np.zeros(3), np.ones(3))
bbox_mir   = (np.array([-1.,0.,0.]), np.array([0.,1.,1.]))
fp_fwd     = np.array([0.5, 0.5, 0.5])
fp_mir     = np.array([-0.5, 0.5, 0.5])
kappa_seed = kappa_integral(bbox_fwd)

stalk_fwd = np.array([1.,1.,1.,1., 0.5,0.5,0.5,1., 0.6,0.,0.8,kappa_seed, 0.,0.,0.,0.,0.,0.])
stalk_mir = p_yz_stalk_401(stalk_fwd)
stalk_mir[bK] = kappa_integral(bbox_mir)

SHARED = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0,
              K_budget=2048, depth=0, J_AC=np.eye(4), W_max=8,
              alpha_leak=0.1, beta_CA=0.3, mass_ref=2.0, kappa_ref=2.0,
              y_ref=1.0, alpha_D=_ALPHA_D_401,
              beta_Z_base=_BETA_Z_313,
              gamma_fb_A=_GAMMA_FB_A_402, gamma_fb_D=_GAMMA_FB_D_402,
              beta_Z_min=_BETA_Z_MIN_402)

def make_mu(stalk, bbox, label):
    prov  = Provenance(parent_ids=(), operator_id=f"seed_{label}", timestamp=now_iso())
    claim = Claim(provenance=prov, payload=label, stalk=stalk.copy(), t=0, bbox=bbox)
    mu    = MuState(t=0, claims={claim.id: claim}, entailments={},
                    active=frozenset([claim.id]),
                    S=np.zeros(12), alpha=ALPHA, S_A=np.zeros(8), S_C=np.zeros(4),
                    S_D=np.zeros(6))
    mu.seal()
    return mu, claim.id

mu_f0, root_f = make_mu(stalk_fwd, bbox_fwd, "fwd")
mu_m0, root_m = make_mu(stalk_mir, bbox_mir, "mir")

r_f = apply_gamma_402_recursive(mu=mu_f0, claim_id=root_f, focal_point=fp_fwd, B=B_FWD, **SHARED)
r_m = apply_gamma_402_recursive(mu=mu_m0, claim_id=root_m, focal_point=fp_mir, B=B_MIR, **SHARED)

mu_f, _, w_f, bze_f, BA_f, BD_f = r_f
mu_m, _, w_m, bze_m, BA_m, BD_m = r_m

S_D_f = mu_f.S_D if mu_f.S_D is not None else np.zeros(6)
S_D_m = mu_m.S_D if mu_m.S_D is not None else np.zeros(6)
gh_f  = [h for h in (getattr(mu_f, 'ghost_history', []) or []) if len(h) >= 4]
gh_m  = [h for h in (getattr(mu_m, 'ghost_history', []) or []) if len(h) >= 4]

print(f"  fwd: bze={bze_f:.8f}  B_A={BA_f:.8f}  B_D={BD_f:.8f}  leaves={len(mu_f.active)}")
print(f"  mir: bze={bze_m:.8f}  B_A={BA_m:.8f}  B_D={BD_m:.8f}  leaves={len(mu_m.active)}")
print(f"  S_D_fwd={S_D_f}")
print(f"  S_D_mir={S_D_m}")

# [2] beta_Z_eff P_yz-invariant
d_bze = abs(bze_f - bze_m)
assert d_bze < 1e-12, f"beta_Z_eff P_yz violation: fwd={bze_f:.10f} mir={bze_m:.10f} delta={d_bze:.2e}"
print(f"[2] PASS  beta_Z_eff P_yz-invariant: {bze_f:.10f} = {bze_m:.10f}  delta={d_bze:.2e}")

# [3] leaf count
assert len(mu_f.active) == len(mu_m.active), f"leaves: fwd={len(mu_f.active)} mir={len(mu_m.active)}"
print(f"[3] PASS  fwd_leaves == mir_leaves == {len(mu_f.active)}")

# [4] Omega_AC P_yz-invariant
assert len(gh_f) > 0 and len(gh_m) > 0
omega_f = gh_f[-1][2]; omega_m = gh_m[-1][2]
d_omega = abs(omega_f - omega_m)
assert d_omega < 1e-10, f"Omega_AC P_yz violation: delta={d_omega:.2e}"
print(f"[4] PASS  Omega_AC P_yz-invariant: {omega_f:.8f} = {omega_m:.8f}  delta={d_omega:.2e}")

# [5] S_D tensor covariance
d_l21 = abs(S_D_f[3] + S_D_m[3])
d_l31 = abs(S_D_f[4] + S_D_m[4])
d_l32 = abs(S_D_f[5] - S_D_m[5])
assert d_l21 < 1e-8, f"l21 anti-sym violation: {d_l21:.2e}"
assert d_l31 < 1e-8, f"l31 anti-sym violation: {d_l31:.2e}"
assert d_l32 < 1e-8, f"l32 sym violation: {d_l32:.2e}"
print(f"[5] PASS  S_D tensor covariance:")
print(f"      l21: fwd={S_D_f[3]:.8f}  mir={S_D_m[3]:.8f}  sum={d_l21:.2e} (anti-sym)")
print(f"      l31: fwd={S_D_f[4]:.8f}  mir={S_D_m[4]:.8f}  sum={d_l31:.2e} (anti-sym)")
print(f"      l32: fwd={S_D_f[5]:.8f}  mir={S_D_m[5]:.8f}  delta={d_l32:.2e} (sym)")

print(f"\n  OBS: beta_Z_eff={bze_f:.6f}  B_A={BA_f:.8f}  B_D={BD_f:.8f}")
print(f"  OBS: Omega_AC={omega_f:.4f} rad  leaves={len(mu_f.active)}")
print(f"  OBS: B_FWD={B_FWD}  B_MIR={B_MIR}")

print(f"\nFork B: ALL TESTS PASSED")
print(f"  EXP-402: beta_Z_eff P_yz-invariant. B_A=B_D=0 at seed (S_A=S_D=0).")
print(f"  Phi_fb operator: P_yz-invariant. Tensor covariance inherited from EXP-401.")
