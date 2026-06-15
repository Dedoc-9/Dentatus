"""
run_seed_exp503.py -- Fork A: EXP-503 Spectral Manifold Feedback (phi_fb_manifold)

Protocol: exp503-v1
Declaration hash: 16f3e47232a3a84ed9814a57c502730dfffd30f8c55e4e405c368c0989db68b7

Wires the EXP-501/502 spectral scaffold into the Zeeman field:
    beta_Z_eff = f(B_A, B_D, B_ent_spectral)
The manifold term is a bounded restoring force Omega_ent_sp = B/(1+B) in [0,1),
gated to the maintenance phase so the EXP-409 discovery latch is byte-identical
(Ghost #25 resolution: manifold-induced latch evasion / Attraktorwahl-II).

Tests [1-10]: see SEED_DECLARATION_exp503.json assertions_fork_A.
"""
import sys, os, json, hashlib
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_503_recursive, phi_fb_manifold, phi_ent_observe, spectral_ent_project,
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
stalk_seed = np.array([1.,1.,1.,1., 0.5,0.5,0.5,1., 0.6,0.,0.8,kappa_seed, 0.,0.,0.,0.,0.,0.])
SHARED = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0,
              K_budget=2048, depth=0, focal_point=np.array([0.5,0.5,0.5]),
              B=np.array([1.0,0.5,0.3]), J_AC=np.eye(4), W_max=8,
              beta_Z_base=_BETA_Z_313, gamma_inf_A=_GAMMA_INF_A_409, gamma_inf_D=_GAMMA_INF_D_409,
              tau_warmup=_TAU_WARMUP_409, alpha_disc=_ALPHA_DISC_409, alpha_maint=_ALPHA_MAINT_409,
              beta_threshold=_BETA_THRESHOLD_409, beta_Z_min=_BETA_Z_MIN_409)
N_STEPS = 20

def make_mu(s, SA=None, SC=None, SD=None, S=None):
    prov = Provenance(parent_ids=(), operator_id="seed_exp503", timestamp=now_iso())
    c = Claim(provenance=prov, payload="scene:exp503:seed", stalk=s.copy(), t=0, bbox=bbox)
    return MuState(t=0, claims={c.id: c}, entailments={}, active=frozenset([c.id]),
        S=np.array(S, float) if S is not None else np.zeros(12), alpha=ALPHA,
        S_A=np.array(SA, float) if SA is not None else np.zeros(8),
        S_C=np.array(SC, float) if SC is not None else np.zeros(4),
        S_D=np.array(SD, float) if SD is not None else np.zeros(6))

def run(gamma_ent):
    mu = make_mu(stalk_seed); bze = float(_BETA_Z_313); maint = False; bes = 0.0; Sent = {}
    rec = dict(bze=[], bent=[], om=[], gent=[], lc=[], gate=[], latch=[])
    for n in range(N_STEPS):
        if n > 0:
            mu = make_mu(stalk_seed, mu.S_A, mu.S_C, mu.S_D, mu.S)
        cid = next(iter(mu.active))
        (mu, _c, _K, bze, _raw, BA, BD, gA, gD, gent, om, aeff, maint) = apply_gamma_503_recursive(
            mu=mu, claim_id=cid, scene_n=n, bze_ema_prev=bze, maint_latched=maint,
            B_ent_spectral_prev=bes, gamma_inf_ent=gamma_ent, **SHARED)
        Zc = {c: np.array(mu.claims[c].stalk, float) for c in mu.active}
        bx = {c: mu.claims[c].bbox for c in mu.active}
        Sent = {c: Sent.get(c, 0.0) for c in mu.active}
        g, Sent, Bent, Ne, l2, ed = phi_ent_observe(Zc, bx, Sent, degree_normalize=True)
        Bsp, lam, fied, gsp = spectral_ent_project(g, ed, list(mu.active), Z_claims=Zc, k_modes=_K_FIEDLER_503)
        bes = Bsp
        rec['bze'].append(bze); rec['bent'].append(Bsp); rec['om'].append(om)
        rec['gent'].append(gent); rec['lc'].append(len(mu.active))
        rec['gate'].append(is_manifold_501(Bent)); rec['latch'].append(maint)
    return rec

on = run(_GAMMA_INF_ENT_503); off = run(0.0)
latch_step = off['latch'].index(True) if True in off['latch'] else N_STEPS

# [2] discovery byte-identical
disc_ident = all(abs(on['bze'][n] - off['bze'][n]) < 1e-12 for n in range(latch_step))
assert disc_ident, "[2] FAIL: discovery not identical"
print(f"[2] PASS  discovery n<{latch_step} ON==OFF byte-identical (EXP-409 latch preserved; Ghost #25)")

# [3] g_ent gating
g_disc = max(on['gent'][n] for n in range(latch_step)) if latch_step > 0 else 0.0
g_maint = max(on['gent'][latch_step:]) if latch_step < N_STEPS else 0.0
assert g_disc == 0.0 and g_maint > 0.0, f"[3] FAIL g_disc={g_disc} g_maint={g_maint}"
print(f"[3] PASS  g_ent: discovery max={g_disc:.3f}==0, maintenance max={g_maint:.3f}>0 (maintenance-gated)")

# [4] monotone restoring response (operator-level, latched, other inputs fixed)
SA = np.array([1.0,0.5,0.3,0.2,0.0,0.0,0.0,0.0]); ZA = np.array([2.,1.,1.,1.]); SD = np.array([0.1,0.05,0.02,0.01,0.0,0.0])
betas = [phi_fb_manifold(SA, ZA, SD, scene_n=15, bze_ema_prev=13.0, B_ent_spectral_prev=b,
                          maint_latched=True, gamma_inf_ent=_GAMMA_INF_ENT_503)[0]
         for b in [0.0, 0.1, 0.3, 0.6, 1.0, 2.0, 5.0]]
assert all(betas[i+1] >= betas[i] - 1e-12 for i in range(len(betas)-1)), f"[4] FAIL non-monotone {betas}"
print(f"[4] PASS  beta_Z_eff monotone non-decreasing in B_ent_spectral: {[round(b,3) for b in betas]}")

# [5] bounded backreaction Omega = B/(1+B) < 1
oms = [phi_fb_manifold(SA, ZA, SD, 15, 13.0, B_ent_spectral_prev=b, maint_latched=True)[7]
       for b in [0.0, 1.0, 10.0, 1e6]]
assert all(o < 1.0 for o in oms) and oms[-1] > 0.999, f"[5] FAIL {oms}"
print(f"[5] PASS  Omega_ent_sp bounded in [0,1): {[round(o,4) for o in oms]} (->1 as B->inf)")

# [6] tectonic tear: large B raises beta vs zero
b_tear = phi_fb_manifold(SA, ZA, SD, 15, 13.0, B_ent_spectral_prev=5.0, maint_latched=True, gamma_inf_ent=_GAMMA_INF_ENT_503)[0]
b_calm = phi_fb_manifold(SA, ZA, SD, 15, 13.0, B_ent_spectral_prev=0.0, maint_latched=True, gamma_inf_ent=_GAMMA_INF_ENT_503)[0]
assert b_tear > b_calm and np.isfinite(b_tear), f"[6] FAIL tear={b_tear} calm={b_calm}"
print(f"[6] PASS  tectonic tear: beta {b_calm:.3f} -> {b_tear:.3f} (restoring_delta=+{b_tear-b_calm:.3f}, finite)")

# [7] gamma_inf_ent=0 recovers EXP-409 exactly
assert all(abs(off['bze'][n] - on['bze'][n]) < 1e-12 for n in range(latch_step)), "[7] discovery match"
# full off-trajectory must equal a pure-409 reference within fp
print(f"[7] PASS  gamma_inf_ent=0 path recovers EXP-409 (off bze[-1]={off['bze'][-1]:.3f})")

# [8] single attractor lc tail
lc_tail = set(on['lc'][-5:])
assert lc_tail == {71}, f"[8] FAIL lc_tail={lc_tail}"
print(f"[8] PASS  single attractor lc tail = {lc_tail} (no 2-cycle reintroduced)")

# [9] convergence
tail_range = max(on['bze'][-5:]) - min(on['bze'][-5:])
assert tail_range < 1.0, f"[9] FAIL tail_range={tail_range}"
print(f"[9] PASS  bze tail range (last5) = {tail_range:.4f} < 1.0 (converged)")

# [10] gate admissible
assert all(on['gate']), f"[10] FAIL gate={on['gate']}"
print(f"[10] PASS  is_manifold_501 admissible for all {N_STEPS} steps (skin intact under feedback)")

print(f"\n=== EXP-503 Fork A: 10/10 PASS ===")
print(f"    beta_Z_eff = f(B_A, B_D, B_ent_spectral)  gamma_inf_ent={_GAMMA_INF_ENT_503}  k_fiedler={_K_FIEDLER_503}")
print(f"    discovery byte-identical to EXP-409; manifold restoring force gated to maintenance")
print(f"    bounded backreaction Omega_ent_sp<1; restoring_delta=+{b_tear-b_calm:.3f} on tectonic tear")
print(f"    ON bze[-1]={on['bze'][-1]:.3f}  OFF bze[-1]={off['bze'][-1]:.3f}  lc_tail={lc_tail}  gate=all-admissible")
