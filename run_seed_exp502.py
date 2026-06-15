"""
run_seed_exp502.py -- Fork A: EXP-502 Manifold Firewall (is_manifold_501)

Protocol: exp502-v1
Declaration hash: 0979f7f520421a28bc37a7e7aec9e8f7e946f4adb459f55b64718188ea966af8

Adds (1) degree normalization to phi_ent_observe (Ghost #22 fix:
G_ent_i = ||sum_j G_ij|| / sqrt(deg_i)), and (2) the is_manifold_501 elastic-limit
firewall at epsilon_manifold = 0.8. Observation/gating only -- no change to EXP-409 dynamics.

Tests [1-10]:
  [1]  declaration_hash
  [2]  degree_normalize=True lowers B_ent vs False (Ghost #22 bias removed)
  [3]  B_ent_normalized median in (0, epsilon_manifold)
  [4]  is_manifold_501 == True at baseline for all n
  [5]  is_manifold_501 rejects a synthetic over-coupled state (B_ent > epsilon)
  [6]  global section: B_ent_normalized == 0 and gate True
  [7]  per-claim worst_ratio <= epsilon_manifold at baseline
  [8]  EXP-501 back-compat: default flag == explicit degree_normalize=False (exact)
  [9]  degree-normalization preserves global-section zero
  [10] epsilon_manifold == 0.8 (preregistered)
"""
import sys, os, json, hashlib, statistics
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_409_recursive,
    phi_ent_observe, apply_F_ij_501,
    _ALPHA_DISC_409, _ALPHA_MAINT_409, _BETA_THRESHOLD_409,
    _GAMMA_INF_A_409, _GAMMA_INF_D_409, _TAU_WARMUP_409,
    _BETA_Z_MIN_409, _BETA_Z_313, _ALPHA_ENT_501,
)
from engine.validity import (
    kappa_integral, is_manifold_501, is_manifold_501_perclaim, EPS_MANIFOLD_502,
)

DECL_HASH = "0979f7f520421a28bc37a7e7aec9e8f7e946f4adb459f55b64718188ea966af8"
DECL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "studies/exp502_manifold_firewall/SEED_DECLARATION_exp502.json")
with open(DECL_PATH) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
canon = json.dumps(decl, sort_keys=True, separators=(",", ":"))
computed = hashlib.sha256(canon.encode()).hexdigest()
assert stored == DECL_HASH and computed == DECL_HASH, f"hash mismatch {stored[:16]}/{computed[:16]}"
print(f"[1] PASS  declaration_hash = {DECL_HASH[:16]}...")

bbox = (np.zeros(3), np.ones(3))
kappa_seed = kappa_integral(bbox)
stalk_seed = np.array([1.,1.,1.,1., 0.5,0.5,0.5,1., 0.6,0.,0.8,kappa_seed, 0.,0.,0.,0.,0.,0.])

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
    prov = Provenance(parent_ids=(), operator_id="seed_exp502", timestamp=now_iso())
    claim = Claim(provenance=prov, payload="scene:exp502:seed", stalk=stalk.copy(), t=0, bbox=bbox)
    return MuState(t=0, claims={claim.id: claim}, entailments={}, active=frozenset([claim.id]),
        S=np.array(S, dtype=float) if S is not None else np.zeros(12), alpha=ALPHA,
        S_A=np.array(S_A, dtype=float) if S_A is not None else np.zeros(8),
        S_C=np.array(S_C, dtype=float) if S_C is not None else np.zeros(4),
        S_D=np.array(S_D, dtype=float) if S_D is not None else np.zeros(6))

# Build a populated active set via EXP-409
mu = make_mu(stalk_seed); bze = float(_BETA_Z_313); maint = False
for n in range(N_STEPS):
    if n > 0:
        mu = make_mu(stalk_seed, S_A=np.array(mu.S_A), S_C=np.array(mu.S_C),
                     S_D=np.array(mu.S_D), S=np.array(mu.S))
    cid = next(iter(mu.active))
    (mu, *_rest, maint) = apply_gamma_409_recursive(
        mu=mu, claim_id=cid, scene_n=n, bze_ema_prev=bze, maint_latched=maint, **SHARED)
    bze = _rest[2]
N_leaves = len(mu.active)

Z_claims = {cid: np.array(mu.claims[cid].stalk, float) for cid in mu.active}
bboxes   = {cid: mu.claims[cid].bbox for cid in mu.active}
Z_active_norm = float(np.linalg.norm([np.linalg.norm(Z_claims[c]) for c in sorted(Z_claims)]))

# Sequential observation: raw (501) vs degree-normalized (502)
b_raw, b_norm, gates, worst = [], [], [], []
Sp_raw = {c: 0.0 for c in mu.active}
Sp_norm = {c: 0.0 for c in mu.active}
last_g_norm, last_edges, last_Ne, last_l2 = None, None, None, None
for n in range(N_STEPS):
    g_raw, Sp_raw, B_raw, Ne, l2, ed = phi_ent_observe(Z_claims, bboxes, Sp_raw, degree_normalize=False)
    g_nrm, Sp_norm, B_nrm, _, _, _   = phi_ent_observe(Z_claims, bboxes, Sp_norm, degree_normalize=True)
    b_raw.append(B_raw); b_norm.append(B_nrm)
    gates.append(is_manifold_501(B_nrm))
    ok, _wc, wr = is_manifold_501_perclaim(g_nrm, Z_active_norm)
    worst.append(wr)
    last_g_norm, last_edges, last_Ne, last_l2 = g_nrm, ed, Ne, l2

print(f"\n  N_leaves={N_leaves}  N_edges={last_Ne}  lambda_2={last_l2:.4f}")
print(f"  B_ent raw  median={statistics.median(b_raw):.4f}  last={b_raw[-1]:.4f}")
print(f"  B_ent norm median={statistics.median(b_norm):.4f}  last={b_norm[-1]:.4f}  (eps={EPS_MANIFOLD_502})")

assert statistics.median(b_norm) < statistics.median(b_raw), "[2] FAIL"
print(f"[2] PASS  degree-normalized B_ent {statistics.median(b_norm):.4f} < raw {statistics.median(b_raw):.4f}")

med = statistics.median(b_norm)
assert 0.0 < med < EPS_MANIFOLD_502, f"[3] FAIL median={med}"
print(f"[3] PASS  B_ent_norm median={med:.4f} in (0, {EPS_MANIFOLD_502})")

assert all(gates), f"[4] FAIL gates={gates}"
print(f"[4] PASS  is_manifold_501 == True for all {N_STEPS} steps (baseline admitted)")

# [5] synthetic over-coupled pair (large Sector A mismatch on x-face)
si = np.zeros(18); si[0:4] = [0.,0.,0.,1.]; si[7]=1.; si[8:11]=[1.,0.,0.]
sj = np.zeros(18); sj[0:4] = [10.,10.,10.,1.]; sj[7]=1.; sj[8:11]=[-1.,0.,0.]
bi = (np.array([0.,0.,0.]), np.array([0.5,1.,1.]))
bj = (np.array([0.5,0.,0.]), np.array([1.,1.,1.]))
prov = Provenance(parent_ids=(), operator_id="oc", timestamp=now_iso())
ci = Claim(provenance=prov, payload="oc_i", stalk=si, t=0, bbox=bi).id
cj = Claim(provenance=prov, payload="oc_j", stalk=sj, t=0, bbox=bj).id
Zoc = {ci: si, cj: sj}; Boc = {ci: bi, cj: bj}; Spoc = {ci:0.0, cj:0.0}
B_oc = 0.0
for _ in range(15):
    _g, Spoc, B_oc, _ne, _l2, _ed = phi_ent_observe(Zoc, Boc, Spoc, degree_normalize=True)
assert not is_manifold_501(B_oc), f"[5] FAIL: over-coupled B_ent={B_oc:.4f} not rejected"
print(f"[5] PASS  over-coupled state B_ent={B_oc:.4f} > {EPS_MANIFOLD_502} -> gate rejects (manifold torn)")

# [6] global section
params_i = np.array([0.3,-0.1,0.1,0.7,-0.3,0.4])
sgi = np.concatenate([[1.,1.,1.,1.],[0.5,0.5,0.5,1.],[0.,0.,1.,kappa_seed],params_i])
bgi = (np.array([0.,0.,0.]), np.array([0.5,1.,1.])); bgj=(np.array([0.5,0.,0.]),np.array([1.,1.,1.]))
sgj = apply_F_ij_501(sgi, 0)
cgi = Claim(provenance=prov, payload="gs_i", stalk=sgi, t=0, bbox=bgi).id
cgj = Claim(provenance=prov, payload="gs_j", stalk=sgj, t=0, bbox=bgj).id
Zgs={cgi:sgi,cgj:sgj}; Bgs={cgi:bgi,cgj:bgj}
_g, _S, B_gs, _ne, _l2, _ed = phi_ent_observe(Zgs, Bgs, {cgi:0.0,cgj:0.0}, degree_normalize=True)
assert B_gs < 1e-10 and is_manifold_501(B_gs), f"[6] FAIL B_gs={B_gs:.2e}"
print(f"[6] PASS  global section B_ent_norm={B_gs:.2e} -> gate admits")

assert max(worst) <= EPS_MANIFOLD_502, f"[7] FAIL worst={max(worst):.4f}"
print(f"[7] PASS  per-claim worst_ratio max={max(worst):.4f} <= {EPS_MANIFOLD_502}")

# [8] back-compat: default flag == explicit False (exact)
gA, _, BA, _, _, _ = phi_ent_observe(Z_claims, bboxes, {c:0.0 for c in mu.active})
gB, _, BB, _, _, _ = phi_ent_observe(Z_claims, bboxes, {c:0.0 for c in mu.active}, degree_normalize=False)
assert BA == BB and gA == gB, "[8] FAIL back-compat"
print(f"[8] PASS  default flag == explicit degree_normalize=False (B_ent {BA:.6f} exact)")

# [9] global-section zero preserved under normalization
assert B_gs == 0.0 or B_gs < 1e-12
print(f"[9] PASS  degree-normalization preserves global-section zero ({B_gs:.2e})")

assert EPS_MANIFOLD_502 == 0.8
print(f"[10] PASS  epsilon_manifold = {EPS_MANIFOLD_502} (preregistered)")

print(f"\n=== EXP-502 Fork A: 10/10 PASS ===")
print(f"    N_leaves={N_leaves}  N_edges={last_Ne}  lambda_2={last_l2:.4f}")
print(f"    B_ent_norm median={med:.4f}  eps_manifold={EPS_MANIFOLD_502}  margin={EPS_MANIFOLD_502/med:.2f}x")
print(f"    firewall admits baseline; rejects over-coupled (B_ent={B_oc:.3f})")
print(f"    Ghost #22 degree-normalized; P_yz preserved (see Fork B)")
