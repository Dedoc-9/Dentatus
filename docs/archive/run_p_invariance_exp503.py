"""
run_p_invariance_exp503.py -- Fork B: EXP-503 P_yz Invariance (spectral manifold feedback)

Protocol: exp503-v1
Declaration hash: 16f3e47232a3a84ed9814a57c502730dfffd30f8c55e4e405c368c0989db68b7

B_ent_spectral is a projection of P_yz-invariant residuals onto the P_yz-isomorphic
L_sheaf spectrum, hence P_yz-invariant. The bounded manifold term and the EXP-409 latch
are functions of P_yz-invariant scalars, so the entire closed loop is P_yz-symmetric.

Tests [1-5]: see SEED_DECLARATION_exp503.json assertions_fork_B.
"""
import sys, os, json, hashlib
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_503_recursive, phi_ent_observe, spectral_ent_project,
    _ALPHA_DISC_409, _ALPHA_MAINT_409, _BETA_THRESHOLD_409,
    _GAMMA_INF_A_409, _GAMMA_INF_D_409, _TAU_WARMUP_409,
    _BETA_Z_MIN_409, _BETA_Z_313, _GAMMA_INF_ENT_503, _K_FIEDLER_503,
)
from engine.validity import kappa_integral, is_manifold_501

DECL_HASH = "16f3e47232a3a84ed9814a57c502730dfffd30f8c55e4e405c368c0989db68b7"
DECL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "studies/exp503_spectral_feedback/SEED_DECLARATION_exp503.json")
with open(DECL_PATH) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DECL_HASH
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
              beta_threshold=_BETA_THRESHOLD_409, beta_Z_min=_BETA_Z_MIN_409,
              gamma_inf_ent=_GAMMA_INF_ENT_503)
N_STEPS = 20

def make_mu(s, SA=None, SC=None, SD=None, S=None):
    prov = Provenance(parent_ids=(), operator_id="seed_exp503_pyz", timestamp=now_iso())
    c = Claim(provenance=prov, payload="scene:exp503:pyz", stalk=s.copy(), t=0, bbox=(np.zeros(3),np.ones(3)))
    return MuState(t=0, claims={c.id: c}, entailments={}, active=frozenset([c.id]),
        S=np.array(S, float) if S is not None else np.zeros(12), alpha=ALPHA,
        S_A=np.array(SA, float) if SA is not None else np.zeros(8),
        S_C=np.array(SC, float) if SC is not None else np.zeros(4),
        S_D=np.array(SD, float) if SD is not None else np.zeros(6))

def run(stalk0):
    mu = make_mu(stalk0); bze = float(_BETA_Z_313); maint = False; bes = 0.0; Sent = {}
    rec = dict(bze=[], bent=[], om=[], lc=[], gate=[])
    for n in range(N_STEPS):
        if n > 0:
            mu = make_mu(stalk0, mu.S_A, mu.S_C, mu.S_D, mu.S)
        cid = next(iter(mu.active))
        (mu, _c, _K, bze, _raw, BA, BD, gA, gD, gent, om, aeff, maint) = apply_gamma_503_recursive(
            mu=mu, claim_id=cid, scene_n=n, bze_ema_prev=bze, maint_latched=maint,
            B_ent_spectral_prev=bes, **SHARED)
        Zc = {c: np.array(mu.claims[c].stalk, float) for c in mu.active}
        bx = {c: mu.claims[c].bbox for c in mu.active}
        Sent = {c: Sent.get(c, 0.0) for c in mu.active}
        g, Sent, Bent, Ne, l2, ed = phi_ent_observe(Zc, bx, Sent, degree_normalize=True)
        Bsp, lam, fied, gsp = spectral_ent_project(g, ed, list(mu.active), Z_claims=Zc, k_modes=_K_FIEDLER_503)
        bes = Bsp
        rec['bze'].append(bze); rec['bent'].append(Bsp); rec['om'].append(om)
        rec['lc'].append(len(mu.active)); rec['gate'].append(is_manifold_501(Bent))
    return rec

f = run(stalk_fwd); m = run(stalk_mir)

max_b = max(abs(f['bze'][n] - m['bze'][n]) for n in range(N_STEPS))
assert max_b < 1e-10, f"[2] FAIL {max_b:.2e}"
print(f"[2] PASS  max|beta_Z_eff_fwd-mir|={max_b:.2e} (phi_fb_manifold P_yz-invariant)")

max_s = max(abs(f['bent'][n] - m['bent'][n]) for n in range(N_STEPS))
assert max_s < 1e-10, f"[3] FAIL {max_s:.2e}"
print(f"[3] PASS  max|B_ent_spectral_fwd-mir|={max_s:.2e}")

max_o = max(abs(f['om'][n] - m['om'][n]) for n in range(N_STEPS))
assert max_o < 1e-10, f"[4] FAIL {max_o:.2e}"
print(f"[4] PASS  max|Omega_ent_sp_fwd-mir|={max_o:.2e}")

assert all(f['lc'][n] == m['lc'][n] and f['gate'][n] == m['gate'][n] for n in range(N_STEPS)), "[5] FAIL lc/gate asymmetry"
print(f"[5] PASS  lc_fwd==lc_mir and gate_fwd==gate_mir for all n")

print(f"\n=== EXP-503 Fork B: 5/5 PASS ===")
print(f"    max|beta_Z_eff_fwd-mir|={max_b:.2e}")
print(f"    max|B_ent_spectral_fwd-mir|={max_s:.2e}")
print(f"    max|Omega_ent_sp_fwd-mir|={max_o:.2e}")
print(f"    closed manifold loop P_yz-symmetric; gamma_inf_ent={_GAMMA_INF_ENT_503}")
