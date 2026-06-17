"""
run_p_invariance_exp601.py -- Fork B: EXP-601 P_yz under Deterministic Seeding

Protocol: exp601-v1
Declaration hash: f352e458d1e252f4af0fc555e8a76b4bfe7f7182c96d521d95341cfdf36d26fc

Deterministic ids fix the summation order per configuration. Because the id is derived from a
coordinate-free extents payload + octant child_index (isometric-aware), P_yz symmetry is
preserved at machine precision -- and the now-deterministic order makes the observable deltas
exactly 0.0.

Tests [1-5]: see SEED_DECLARATION_exp601.json assertions_fork_B.
"""
import sys, os, json, hashlib
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_503_recursive, phi_ent_observe,
    _ALPHA_DISC_409, _ALPHA_MAINT_409, _BETA_THRESHOLD_409, _GAMMA_INF_A_409, _GAMMA_INF_D_409,
    _TAU_WARMUP_409, _BETA_Z_MIN_409, _BETA_Z_313, _GAMMA_INF_ENT_503,
)
from engine.validity import kappa_integral

DECL_HASH = "f352e458d1e252f4af0fc555e8a76b4bfe7f7182c96d521d95341cfdf36d26fc"
DECL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "studies/exp601_deterministic_seeding/SEED_DECLARATION_exp601.json")
with open(DECL_PATH) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DECL_HASH
print(f"[1] PASS  declaration_hash = {DECL_HASH[:16]}...")

bbox = (np.zeros(3), np.ones(3)); ks = kappa_integral(bbox)
stalk_fwd = np.array([1.,1.,1.,1., 0.5,0.5,0.5,1., 0.6,0.,0.8,ks, 0.,0.,0.,0.,0.,0.])
stalk_mir = stalk_fwd.copy(); stalk_mir[4] = -stalk_fwd[4]
SH = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0, K_budget=2048, depth=0,
          focal_point=np.array([0.5,0.5,0.5]), B=np.array([1.0,0.5,0.3]), J_AC=np.eye(4), W_max=8,
          beta_Z_base=_BETA_Z_313, gamma_inf_A=_GAMMA_INF_A_409, gamma_inf_D=_GAMMA_INF_D_409,
          tau_warmup=_TAU_WARMUP_409, alpha_disc=_ALPHA_DISC_409, alpha_maint=_ALPHA_MAINT_409,
          beta_threshold=_BETA_THRESHOLD_409, beta_Z_min=_BETA_Z_MIN_409, gamma_inf_ent=_GAMMA_INF_ENT_503)
N = 12

def run(stalk0):
    prov = Provenance(parent_ids=(), operator_id="seed_exp601_pyz", timestamp=now_iso())
    c0 = Claim(provenance=prov, payload="scene:exp601:pyz", stalk=stalk0.copy(), t=0, bbox=bbox)
    mu = MuState(t=0, claims={c0.id: c0}, entailments={}, active=frozenset([c0.id]), S=np.zeros(12),
                 alpha=ALPHA, S_A=np.zeros(8), S_C=np.zeros(4), S_D=np.zeros(6))
    bze = float(_BETA_Z_313); maint = False
    bent = []; lam2 = []; ncl = []
    for n in range(N):
        if n > 0:
            prov = Provenance(parent_ids=(), operator_id="seed_exp601_pyz", timestamp=now_iso())
            c0 = Claim(provenance=prov, payload="scene:exp601:pyz", stalk=stalk0.copy(), t=0, bbox=bbox)
            mu = MuState(t=0, claims={c0.id: c0}, entailments={}, active=frozenset([c0.id]), S=np.zeros(12),
                         alpha=ALPHA, S_A=np.array(mu.S_A), S_C=np.array(mu.S_C), S_D=np.array(mu.S_D))
        cid = next(iter(mu.active))
        out = apply_gamma_503_recursive(mu=mu, claim_id=cid, scene_n=n, bze_ema_prev=bze, maint_latched=maint, B_ent_spectral_prev=0.0, **SH)
        mu, bze, maint = out[0], out[3], out[12]
        Zc = {c: np.asarray(mu.claims[c].stalk, float) for c in mu.active}
        bx = {c: mu.claims[c].bbox for c in mu.active}
        g, S_ent, B_ent, Ne, l2, ed = phi_ent_observe(Zc, bx, {c: 0.0 for c in mu.active}, degree_normalize=True)
        bent.append(B_ent); lam2.append(l2); ncl.append(len(mu.active))
    return bent, lam2, ncl

bf, lf, nf = run(stalk_fwd)
bm, lm, nm = run(stalk_mir)

max_b = max(abs(bf[n] - bm[n]) for n in range(N))
assert max_b == 0.0, f"[2] FAIL max|B_ent|={max_b:.2e}"
print(f"[2] PASS  max|B_ent_fwd - B_ent_mir| = {max_b:.1e} (exact P_yz under deterministic ids)")

max_l = max(abs(lf[n] - lm[n]) for n in range(N))
assert max_l <= 1e-14, f"[3] FAIL max|lambda_2|={max_l:.2e}"
print(f"[3] PASS  max|lambda_2_fwd - lambda_2_mir| = {max_l:.1e}")

assert all(nf[n] == nm[n] for n in range(N)), "[4] FAIL leaf-count asymmetry"
print(f"[4] PASS  claim-id set cardinality fwd == mir all n (leaves {nf[-1]})")

assert max_b <= 1e-14 and max_l <= 1e-14
print(f"[5] PASS  deterministic ids preserve P_yz at machine precision (B_ent exact 0.0)")

print(f"\n=== EXP-601 Fork B: 5/5 PASS ===")
print(f"    P_yz exact under deterministic seeding: max|B_ent|={max_b:.1e}, max|lambda_2|={max_l:.1e}")
