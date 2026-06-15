"""
run_p_invariance_exp504.py -- Fork B: EXP-504 P_yz Invariance (Stateful Seed)

Protocol: exp504-v1
Declaration hash: 93201baeac72aac92183da7bdf5c1d9da7fb144abeea66d3b1cca38ecf47530c

The persisted state is built from P_yz-invariant quantities: spatial keys (|hi-lo| extents
and centers), per-claim G_ent norms, sector norms, and primary scalars. Therefore the persisted
B_ent_spectral, S_ent, the healing curve, and the norm-based H_seed are all P_yz-invariant.

Tests [1-5]: see SEED_DECLARATION_exp504.json assertions_fork_B.
"""
import sys, os, json, hashlib
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_503_recursive, phi_ent_observe, spectral_ent_project,
    persist_scene_504, seed_memory_init_504, seed_memory_hash_504, spatial_key_504,
    _ALPHA_DISC_409, _ALPHA_MAINT_409, _BETA_THRESHOLD_409,
    _GAMMA_INF_A_409, _GAMMA_INF_D_409, _TAU_WARMUP_409,
    _BETA_Z_MIN_409, _BETA_Z_313, _GAMMA_INF_ENT_503, _K_FIEDLER_503,
    _ALPHA_PERSIST_504,
)
from engine.validity import kappa_integral, is_manifold_501

DECL_HASH = "93201baeac72aac92183da7bdf5c1d9da7fb144abeea66d3b1cca38ecf47530c"
DECL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "studies/exp504_stateful_seed/SEED_DECLARATION_exp504.json")
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
N, TEAR_N, TEAR = 14, 5, 0.6

def mk(s, SA, SC, SD):
    p = Provenance(parent_ids=(), operator_id="s504p", timestamp=now_iso())
    c = Claim(provenance=p, payload="sc", stalk=s.copy(), t=0, bbox=(np.zeros(3),np.ones(3)))
    return MuState(t=0, claims={c.id: c}, entailments={}, active=frozenset([c.id]), S=np.zeros(12), alpha=ALPHA,
        S_A=np.array(SA), S_C=np.array(SC), S_D=np.array(SD))

def run(stalk0):
    mem = seed_memory_init_504(); bsp = []; gate = []; hashes = []; sent_hist = []
    for n in range(N):
        mu = mk(stalk0, mem["S_A"], mem["S_C"], mem["S_D"]); cid = next(iter(mu.active))
        out = apply_gamma_503_recursive(mu=mu, claim_id=cid, scene_n=mem["scene_count"],
            bze_ema_prev=mem["bze_ema_prev"], maint_latched=mem["maint_latched"],
            B_ent_spectral_prev=mem["B_ent_spectral"], **SH)
        mu, bze, maint = out[0], out[3], out[12]
        Zc = {c: np.array(mu.claims[c].stalk, float) for c in mu.active}
        bx = {c: mu.claims[c].bbox for c in mu.active}
        g, _, Bent, Ne, l2, ed = phi_ent_observe(Zc, bx, {c: 0.0 for c in mu.active}, degree_normalize=True)
        Bsp, lam, fied, gsp = spectral_ent_project(g, ed, list(mu.active), Z_claims=Zc, k_modes=_K_FIEDLER_503)
        sent = {spatial_key_504(bx[c]): g[c] for c in mu.active}
        mem = persist_scene_504(mem, mu.S_A, mu.S_C, mu.S_D, sent, Bsp + (TEAR if n == TEAR_N else 0.0), bze, maint, alpha_persist=_ALPHA_PERSIST_504)
        bsp.append(mem["B_ent_spectral"]); gate.append(is_manifold_501(Bent))
        hashes.append(seed_memory_hash_504(mem)); sent_hist.append(dict(mem["S_ent"]))
    return bsp, gate, hashes, sent_hist

bf, gf, hf, sf = run(stalk_fwd)
bm, gm, hm, sm = run(stalk_mir)

max_b = max(abs(bf[n] - bm[n]) for n in range(N))
assert max_b < 1e-10, f"[2] FAIL {max_b:.2e}"
print(f"[2] PASS  max|B_ent_spectral_persisted_fwd-mir|={max_b:.2e}")

max_s = 0.0
for n in range(N):
    keys = set(sf[n]) & set(sm[n])
    if keys:
        max_s = max(max_s, max(abs(sf[n][k] - sm[n][k]) for k in keys))
assert max_s < 1e-10, f"[3] FAIL {max_s:.2e}"
print(f"[3] PASS  max|S_ent_persisted_fwd[k]-mir[k]|={max_s:.2e} (per-key norm P_yz-invariant)")

base_f = bf[TEAR_N-1]; base_m = bm[TEAR_N-1]
heal = max(abs((bf[TEAR_N+j]-base_f) - (bm[TEAR_N+j]-base_m)) for j in range(5))
assert heal < 1e-10, f"[4] FAIL {heal:.2e}"
print(f"[4] PASS  healing curve fwd==mir (max excess delta={heal:.2e})")

assert hf == hm, "[5] FAIL H_seed not P_yz-invariant"
assert all(gf[n] == gm[n] for n in range(N)), "[5] FAIL gate asymmetry"
print(f"[5] PASS  H_seed_fwd==H_seed_mir all {N} scenes (norm-based index P_yz-invariant); gate_fwd==gate_mir")

print(f"\n=== EXP-504 Fork B: 5/5 PASS ===")
print(f"    max|B_ent_spectral_fwd-mir|={max_b:.2e}")
print(f"    max|S_ent_fwd-mir|={max_s:.2e}  healing curve delta={heal:.2e}")
print(f"    structural index H_seed P_yz-invariant; gate P_yz-symmetric")
