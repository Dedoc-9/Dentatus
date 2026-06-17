"""
run_p_invariance_exp505.py -- Fork B: EXP-505 P_yz Invariance (Moving Claims)

Protocol: exp505-v1
Declaration hash: 6885720d383ca77565ad5bf9091f38da27a678574617c35edb7bdeffd07d873a

True P_yz: the fixed octree is reflected about x=0 (negate x-extents) and the stalks undergo
p_yz (negate Sector B x = stalk[4] and Sector C nx = stalk[8]); world motion reflects V_x->-V_x.
The mirror is then a genuine reflection of the forward moving world. Track continuity, the
sorted per-track S_ent multiset, B_ent_spectral, the healing-under-motion curve, the DAG hash,
and the gate are all P_yz-invariant.

Tests [1-5]: see SEED_DECLARATION_exp505.json assertions_fork_B.
"""
import sys, os, json, hashlib
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_503_recursive, phi_ent_observe, spectral_ent_project,
    persist_scene_504, seed_memory_init_504,
    track_correspondence_505, track_dag_hash_505,
    _ALPHA_DISC_409, _ALPHA_MAINT_409, _BETA_THRESHOLD_409,
    _GAMMA_INF_A_409, _GAMMA_INF_D_409, _TAU_WARMUP_409,
    _BETA_Z_MIN_409, _BETA_Z_313, _GAMMA_INF_ENT_503, _K_FIEDLER_503, _ALPHA_PERSIST_504,
)
from engine.validity import kappa_integral, is_manifold_501

DECL_HASH = "6885720d383ca77565ad5bf9091f38da27a678574617c35edb7bdeffd07d873a"
DECL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "studies/exp505_moving_claims/SEED_DECLARATION_exp505.json")
with open(DECL_PATH) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DECL_HASH
print(f"[1] PASS  declaration_hash = {DECL_HASH[:16]}...")

bbox0 = (np.zeros(3), np.ones(3)); ks = kappa_integral(bbox0)
stalk = np.array([1.,1.,1.,1., 0.5,0.5,0.5,1., 0.6,0.,0.8,ks, 0.,0.,0.,0.,0.,0.])
SH = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0, K_budget=2048, depth=0,
          focal_point=np.array([0.5,0.5,0.5]), B=np.array([1.0,0.5,0.3]), J_AC=np.eye(4), W_max=8,
          beta_Z_base=_BETA_Z_313, gamma_inf_A=_GAMMA_INF_A_409, gamma_inf_D=_GAMMA_INF_D_409,
          tau_warmup=_TAU_WARMUP_409, alpha_disc=_ALPHA_DISC_409, alpha_maint=_ALPHA_MAINT_409,
          beta_threshold=_BETA_THRESHOLD_409, beta_Z_min=_BETA_Z_MIN_409, gamma_inf_ent=_GAMMA_INF_ENT_503)
N, TEAR_N, TEAR = 16, 8, 12.0
def cent(bb): return (bb[0] + bb[1]) / 2.0

prov = Provenance(parent_ids=(), operator_id="seed505p", timestamp=now_iso())
c0 = Claim(provenance=prov, payload="sc", stalk=stalk.copy(), t=0, bbox=bbox0)
mu0 = MuState(t=0, claims={c0.id: c0}, entailments={}, active=frozenset([c0.id]), S=np.zeros(12),
              alpha=ALPHA, S_A=np.zeros(8), S_C=np.zeros(4), S_D=np.zeros(6))
mu0 = apply_gamma_503_recursive(mu=mu0, claim_id=c0.id, scene_n=10, bze_ema_prev=13.0,
                                maint_latched=True, B_ent_spectral_prev=0.12, **SH)[0]
FWD = [(np.array(mu0.claims[cc].stalk, float),
        (np.asarray(mu0.claims[cc].bbox[0], float), np.asarray(mu0.claims[cc].bbox[1], float)))
       for cc in mu0.active]

def p_yz_reflect(st, bb):
    """True P_yz: reflect bbox about x=0 and negate Sector B x (stalk[4]) and Sector C nx (stalk[8])."""
    lo, hi = bb
    lo2 = np.array([-hi[0], lo[1], lo[2]]); hi2 = np.array([-lo[0], hi[1], hi[2]])
    s2 = st.copy(); s2[4] = -s2[4]; s2[8] = -s2[8]
    return s2, (lo2, hi2)
MIR = [p_yz_reflect(st, bb) for st, bb in FWD]

def run(leaves, V):
    nl = len(leaves)
    mem = seed_memory_init_504(); mem["cumulative_motion"] = np.zeros(3); mem["prev_mean"] = None
    cont = []; bsp = []; watch = None; watch_series = []; hashes = []; gates = []; sent_sorted = []
    for n in range(N):
        M = V * n
        Zc = {f"l{i}": leaves[i][0] for i in range(nl)}
        bx = {f"l{i}": (leaves[i][1][0] + M, leaves[i][1][1] + M) for i in range(nl)}
        g, _, Bent, Ne, l2, ed = phi_ent_observe(Zc, bx, {k: 0.0 for k in Zc}, degree_normalize=True)
        Bsp, _, _, _ = spectral_ent_project(g, ed, list(Zc), Z_claims=Zc, k_modes=_K_FIEDLER_503)
        cc = [cent(bx[k]) for k in Zc]
        if mem["prev_mean"] is not None:
            mem["cumulative_motion"] = mem["cumulative_motion"] + (np.mean(cc, axis=0) - mem["prev_mean"])
        c2t, dag, nm, nn = track_correspondence_505(set(mem["S_ent"].keys()), bx, mem["cumulative_motion"])
        if watch is None: watch = c2t["l0"]
        sent = {c2t[k]: g[k] for k in Zc}
        if n == TEAR_N: sent[watch] = sent.get(watch, 0.0) + TEAR
        pm = np.mean(cc, axis=0); cm = mem["cumulative_motion"]
        mem = persist_scene_504(mem, np.zeros(8), np.zeros(4), np.zeros(6), sent, Bsp, 13.0, True, alpha_persist=_ALPHA_PERSIST_504)
        mem["cumulative_motion"] = cm; mem["prev_mean"] = pm
        cont.append(nm / nl); bsp.append(mem["B_ent_spectral"]); gates.append(is_manifold_501(Bent))
        hashes.append(track_dag_hash_505(dag, nm, nn)); watch_series.append(mem["S_ent"].get(watch, 0.0))
        sent_sorted.append(sorted(round(v, 9) for v in mem["S_ent"].values()))
    return dict(cont=cont, bsp=bsp, watch=watch_series, hashes=hashes, gates=gates, sent=sent_sorted)

f = run(FWD, np.array([0.07, 0.03, 0.0]))
m = run(MIR, np.array([-0.07, 0.03, 0.0]))

assert all(abs(f["cont"][n] - m["cont"][n]) < 1e-12 for n in range(N)), "[2] FAIL continuity"
print(f"[2] PASS  track_continuity_fwd == track_continuity_mir all {N} scenes (mean={np.mean(f['cont'][1:]):.3f})")

max_s = max(max(abs(x - y) for x, y in zip(f["sent"][n], m["sent"][n])) for n in range(N))
assert max_s < 1e-10, f"[3] FAIL {max_s:.2e}"
print(f"[3] PASS  sorted S_ent values fwd == mir (max delta={max_s:.2e})")

max_b = max(abs(f["bsp"][n] - m["bsp"][n]) for n in range(N))
heal = max(abs(f["watch"][n] - m["watch"][n]) for n in range(N))
assert max_b < 1e-10 and heal < 1e-10, f"[4] FAIL bsp={max_b:.2e} heal={heal:.2e}"
print(f"[4] PASS  B_ent_spectral & healing-under-motion fwd == mir (bsp {max_b:.2e}, heal {heal:.2e})")

assert f["hashes"] == m["hashes"], "[5] FAIL H_dag not P_yz-invariant"
assert all(f["gates"][n] == m["gates"][n] for n in range(N)), "[5] FAIL gate"
print(f"[5] PASS  H_dag_fwd == H_dag_mir all scenes (size+count index P_yz-invariant); gate_fwd==gate_mir")

print(f"\n=== EXP-505 Fork B: 5/5 PASS ===")
print(f"    true reflection (bbox about x=0 + p_yz stalk + reflected motion)")
print(f"    continuity, sorted S_ent, B_ent_spectral, healing, H_dag all P_yz-invariant (max {max_s:.1e})")
