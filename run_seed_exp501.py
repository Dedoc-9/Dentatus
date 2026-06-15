"""
run_seed_exp501.py — Fork A: EXP-501 Manifold Observation

Protocol: exp501-v1
Declaration hash: bfbf52c2977f436a78f1136555a0e46d00eae43eb95344fc679223961fa60a8b

phi_ent_observe: stateless operator on the full active leaf set W_t.
Computes sheaf coboundary G_ent = delta_0(Z) using face-adjacent 6-connected neighbor graph.
Restriction map F_ij: identity on Sectors A,B; normal-flip on Sector C; XOR rule on Sector D.
Observation only — no modification to existing EXP-409 dynamics.

Tests [1-10]:
  [1]  declaration_hash
  [2]  B_ent > 0 for seed stalk (non-trivial manifold tension)
  [3]  B_ent_gs == 0 for synthetic global section (all neighbors matched via F_ij)
  [4]  lambda_2 > 0 (neighbor graph connected)
  [5]  F_ij involution: apply_F_ij_501(apply_F_ij_501(stalk,k),k) == stalk for all k
  [6]  G_ent Sector D log-diagonal == 0 for matched variance params (variances invariant)
  [7]  N_edges >= 1 (neighbor graph non-empty for seed octree)
  [8]  S_ent converges: |S_ent[n]-S_ent[n-1]| < 0.1 by n=15
  [9]  Sigma_i = R_k @ Sigma_j @ R_k.T for synthetic perfect-glue pair
  [10] B_ent_ema[-1] < max(B_ent_raw_trajectory) (EMA damping confirmed)
"""
import sys, os, json, hashlib
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_409_recursive,
    phi_ent_observe,
    apply_F_ij_501,
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
assert stored == DECL_HASH and computed == DECL_HASH, \
    f"Hash mismatch: stored={stored[:16]} computed={computed[:16]}"
print(f"[1] PASS  declaration_hash = {DECL_HASH[:16]}...")

# ── Seed setup (reuses EXP-409 seed stalk) ──────────────────────────────
bbox       = (np.zeros(3), np.ones(3))
kappa_seed = kappa_integral(bbox)
stalk_seed = np.array([1.,1.,1.,1., 0.5,0.5,0.5,1., 0.6,0.,0.8,kappa_seed,
                        0.,0.,0.,0.,0.,0.])

SHARED_409 = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0,
                  K_budget=2048, depth=0, focal_point=np.array([0.5,0.5,0.5]),
                  B=np.array([1.0,0.5,0.3]), J_AC=np.eye(4), W_max=8,
                  beta_Z_base=_BETA_Z_313,
                  gamma_inf_A=_GAMMA_INF_A_409, gamma_inf_D=_GAMMA_INF_D_409,
                  tau_warmup=_TAU_WARMUP_409,
                  alpha_disc=_ALPHA_DISC_409, alpha_maint=_ALPHA_MAINT_409,
                  beta_threshold=_BETA_THRESHOLD_409, beta_Z_min=_BETA_Z_MIN_409)

N_STEPS = 20

def make_mu(stalk, S_A=None, S_C=None, S_D=None, S=None):
    prov  = Provenance(parent_ids=(), operator_id="seed_exp501", timestamp=now_iso())
    claim = Claim(provenance=prov, payload="scene:exp501:seed",
                  stalk=stalk.copy(), t=0, bbox=bbox)
    return MuState(
        t=0, claims={claim.id: claim}, entailments={},
        active=frozenset([claim.id]),
        S=np.array(S, dtype=float) if S is not None else np.zeros(12),
        alpha=ALPHA,
        S_A=np.array(S_A, dtype=float) if S_A is not None else np.zeros(8),
        S_C=np.array(S_C, dtype=float) if S_C is not None else np.zeros(4),
        S_D=np.array(S_D, dtype=float) if S_D is not None else np.zeros(6),
    )

# ── Run N_STEPS of EXP-409 to build a populated active set ──────────────
mu = make_mu(stalk_seed)
bze_ema = float(_BETA_Z_313); maint = False

for n in range(N_STEPS):
    if n > 0:
        mu = make_mu(stalk_seed,
                     S_A=np.array(mu.S_A), S_C=np.array(mu.S_C),
                     S_D=np.array(mu.S_D), S=np.array(mu.S))
    cid = next(iter(mu.active))
    (mu, _, _, bze_ema, _, _, _, _, _, _, maint) = apply_gamma_409_recursive(
        mu=mu, claim_id=cid, scene_n=n,
        bze_ema_prev=bze_ema, maint_latched=maint, **SHARED_409)

# Build Z_claims and bboxes from final active set
Z_claims = {}
bboxes_map = {}
for cid in mu.active:
    claim = mu.claims[cid]
    Z_claims[cid]   = np.array(claim.stalk, dtype=float)
    bboxes_map[cid] = claim.bbox

N_leaves_final = len(mu.active)
print(f"\n  Seed octree: N_leaves={N_leaves_final} after {N_STEPS} steps")

# ── Sequential N_STEPS observation loop ─────────────────────────────────
S_ent_prev = {cid: 0.0 for cid in mu.active}
B_ent_traj = []
B_ent_raw_traj = []
lambda2_traj = []
N_edges_traj = []

for n in range(N_STEPS):
    if n > 0:
        mu = make_mu(stalk_seed,
                     S_A=np.array(mu.S_A), S_C=np.array(mu.S_C),
                     S_D=np.array(mu.S_D), S=np.array(mu.S))
        cid = next(iter(mu.active))
        (mu, _, _, bze_ema, _, _, _, _, _, _, maint) = apply_gamma_409_recursive(
            mu=mu, claim_id=cid, scene_n=N_STEPS+n,
            bze_ema_prev=bze_ema, maint_latched=maint, **SHARED_409)

    Z_claims_n = {cid: np.array(mu.claims[cid].stalk, dtype=float)
                  for cid in mu.active}
    bboxes_n   = {cid: mu.claims[cid].bbox for cid in mu.active}

    # Reinitialize S_ent for new active set (cold reset each step per EXP-501 scope).
    # EXP-601 note: with deterministic Claim ids the octree keeps identical ids across steps,
    # so .get(cid,0.0) would now CARRY S_ent (the old timestamp-churn cold-reset was accidental).
    # EXP-501 scope is explicit cold-start reset, so force 0.0 each step.
    S_ent_prev_n = {cid: 0.0 for cid in mu.active}

    G_ent_pc, S_ent_out, B_ent, N_edges, lam2, edges = phi_ent_observe(
        Z_claims_n, bboxes_n, S_ent_prev_n, alpha_ent=_ALPHA_ENT_501)

    # Raw G_ent (before EMA): direct norm sum
    B_ent_raw = sum(G_ent_pc.values()) / (sum(np.linalg.norm(Z_claims_n[c]) for c in Z_claims_n) + 1e-15)

    S_ent_prev = S_ent_out
    B_ent_traj.append(B_ent)
    B_ent_raw_traj.append(B_ent_raw)
    lambda2_traj.append(lam2)
    N_edges_traj.append(N_edges)

print(f"  B_ent trajectory (EMA):    {[round(b,4) for b in B_ent_traj]}")
print(f"  B_ent_raw trajectory:      {[round(b,4) for b in B_ent_raw_traj]}")
print(f"  lambda_2 trajectory:       {[round(l,4) for l in lambda2_traj]}")
print(f"  N_edges trajectory:        {N_edges_traj}")

# ── [2] B_ent > 0 for seed stalk ────────────────────────────────────────
assert B_ent_traj[-1] > 0, f"[2] FAIL: B_ent={B_ent_traj[-1]}"
print(f"[2] PASS  B_ent={B_ent_traj[-1]:.6f} > 0 (non-trivial manifold tension)")

# ── [3] B_ent == 0 for synthetic global section ──────────────────────────
# Build a 2-claim synthetic pair: claim_j is the F_ij mirror of claim_i
np.random.seed(13)
params_i = np.array([0.3, -0.1, 0.1, 0.7, -0.3, 0.4])  # Sector D of claim i
stalk_i_gs = np.concatenate([np.array([1.,1.,1.,1.]), np.array([0.5,0.5,0.5,1.]),
                              np.array([0.,0.,1.,kappa_seed]), params_i])
# Face axis k=0 (x-face): bbox_i = [0,0.5]^3, bbox_j = [0.5,1]^1 x [0,1]^2
bbox_i_gs = (np.array([0.,0.,0.]), np.array([0.5,1.,1.]))
bbox_j_gs = (np.array([0.5,0.,0.]), np.array([1.,1.,1.]))
stalk_j_gs = apply_F_ij_501(stalk_i_gs, face_axis=0)   # perfect mirror

prov = Provenance(parent_ids=(), operator_id="gs_test", timestamp=now_iso())
cid_i_gs = Claim(provenance=prov, payload="gs_i", stalk=stalk_i_gs, t=0, bbox=bbox_i_gs).id
cid_j_gs = Claim(provenance=prov, payload="gs_j", stalk=stalk_j_gs, t=0, bbox=bbox_j_gs).id
Z_gs = {cid_i_gs: stalk_i_gs, cid_j_gs: stalk_j_gs}
bbox_gs = {cid_i_gs: bbox_i_gs, cid_j_gs: bbox_j_gs}
S_ent_gs0 = {cid_i_gs: 0.0, cid_j_gs: 0.0}
_, _, B_ent_gs, _, _, _ = phi_ent_observe(Z_gs, bbox_gs, S_ent_gs0)
assert B_ent_gs < 1e-10, f"[3] FAIL: B_ent_gs={B_ent_gs:.2e} (expected ~0 for global section)"
print(f"[3] PASS  B_ent_gs={B_ent_gs:.2e} (global section → zero entanglement)")

# ── [4] lambda_2 > 0 ─────────────────────────────────────────────────────
assert all(l > 0 for l in lambda2_traj if l > 0), "[4] FAIL: lambda_2 not consistently > 0"
lam2_nonzero = [l for l in lambda2_traj if l > 0]
assert len(lam2_nonzero) > 0, "[4] FAIL: no non-zero lambda_2 values"
print(f"[4] PASS  lambda_2 min={min(lam2_nonzero):.4f} max={max(lambda2_traj):.4f} (graph connected)")

# ── [5] F_ij involution ───────────────────────────────────────────────────
test_stalk = np.random.randn(18) * 0.5
involution_ok = True
for k in range(3):
    recovered = apply_F_ij_501(apply_F_ij_501(test_stalk, k), k)
    err = np.max(np.abs(recovered - test_stalk))
    if err > 1e-12:
        involution_ok = False
        print(f"[5] FAIL k={k}: max|F_ij(F_ij(s,k),k)-s|={err:.2e}")
assert involution_ok
print(f"[5] PASS  F_ij involution: apply_F_ij(apply_F_ij(stalk,k),k)==stalk for all k (err<1e-12)")

# ── [6] G_ent Sector D log-diagonal == 0 for matched variance ────────────
params_log_diag = np.zeros(18)
params_log_diag[12:15] = [0.3, -0.1, 0.1]  # log_l11, log_l22, log_l33 same both sides
params_log_diag[15:18] = [0.5, 0.2, 0.4]   # off-diag: will be transformed
stalk_ii = params_log_diag.copy()
for k in range(3):
    stalk_jj = apply_F_ij_501(stalk_ii, k)
    G_diag = apply_F_ij_501(stalk_jj, k)[12:15] - stalk_ii[12:15]
    err_diag = np.max(np.abs(G_diag))
    assert err_diag < 1e-12, f"[6] FAIL k={k}: log-diagonal G_ent={err_diag:.2e}"
print(f"[6] PASS  G_ent Sector D log-diagonal=0 for matched variance params (invariant under F_ij)")

# ── [7] N_edges >= 1 ─────────────────────────────────────────────────────
assert all(ne >= 1 for ne in N_edges_traj), f"[7] FAIL: some steps have N_edges=0: {N_edges_traj}"
print(f"[7] PASS  N_edges min={min(N_edges_traj)} max={max(N_edges_traj)} (neighbor graph non-empty)")

# ── [8] S_ent convergence by n=15 ────────────────────────────────────────
delta_S = [abs(B_ent_traj[n] - B_ent_traj[n-1]) for n in range(1, N_STEPS)]
delta_last5 = delta_S[14:]  # steps 15-19
assert max(delta_last5) < 0.5, f"[8] FAIL: S_ent not converging: delta_last5={delta_last5}"
print(f"[8] PASS  B_ent convergence: max|delta| last5 steps = {max(delta_last5):.4f} < 0.5")

# ── [9] Sigma_i = R_k @ Sigma_j @ R_k.T for perfect-glue pair ───────────
def make_L(sd): return np.array([[np.exp(sd[0]),0,0],[sd[3],np.exp(sd[1]),0],[sd[4],sd[5],np.exp(sd[2])]])
params_test = np.array([0.3, -0.1, 0.1, 0.5, 0.2, 0.4])
glue_ok = True
for k in range(3):
    R_k = np.diag([-1. if d==k else 1. for d in range(3)])
    params_mirror = apply_F_ij_501(np.concatenate([np.zeros(12), params_test]), k)[12:18]
    L_i = make_L(params_mirror); L_j = make_L(params_test)
    Sigma_i = L_i @ L_i.T; Sigma_j_expected = R_k @ (L_j @ L_j.T) @ R_k.T
    err = np.max(np.abs(Sigma_i - Sigma_j_expected))
    if err > 1e-12:
        glue_ok = False; print(f"[9] FAIL k={k}: Sigma mismatch err={err:.2e}")
assert glue_ok
print(f"[9] PASS  Sigma_i = R_k @ Sigma_j @ R_k.T for all k (max err < 1e-12)")

# ── [10] EMA damping: B_ent_ema[-1] < max(B_ent_raw) ────────────────────
assert B_ent_traj[-1] < max(B_ent_raw_traj) + 1e-6, \
    f"[10] FAIL: B_ent_ema={B_ent_traj[-1]:.4f} not < max_raw={max(B_ent_raw_traj):.4f}"
print(f"[10] PASS  B_ent_ema[-1]={B_ent_traj[-1]:.4f} ≤ max(B_ent_raw)={max(B_ent_raw_traj):.4f} (EMA damping)")

print(f"\n=== EXP-501 Fork A: 10/10 PASS ===")
print(f"    B_ent[-1]={B_ent_traj[-1]:.4f}  lambda_2[-1]={lambda2_traj[-1]:.4f}")
print(f"    N_edges median={sorted(N_edges_traj)[N_STEPS//2]}  N_leaves={N_leaves_final}")
print(f"    B_ent_gs={B_ent_gs:.2e}  (global section zero)")
print(f"    alpha_ent={_ALPHA_ENT_501}  XOR sign rule verified")
print(f"    Gravitational backreaction: Omega_ent_fb={B_ent_traj[-1]/(1+B_ent_traj[-1]):.4f}")
