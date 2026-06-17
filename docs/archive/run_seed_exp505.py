"""
run_seed_exp505.py -- Fork A: EXP-505 Persistent World-State across Moving Claims

Protocol: exp505-v1
Declaration hash: 6885720d383ca77565ad5bf9091f38da27a678574617c35edb7bdeffd07d873a

Solves Ghost #28: under motion, EXP-504 absolute spatial keys drift and localized manifold
memory is lost. EXP-505 re-references claims to a motion-compensated WORLD FRAME (motion
estimated from the centroid shift), keying S_ent by world-frame position so memory follows
moving claims. A hash-indexed correspondence DAG links prior tracks to current claims.

Demonstration: a fixed octree rigidly drifts by V per scene (pure motion). RAW504 raw keys
-> continuity 0, no memory buildup. TRACK505 world-frame keys -> continuity 1, EMA buildup,
localized tear heals across motion.

Tests [1-10]: see SEED_DECLARATION_exp505.json assertions_fork_A.
"""
import sys, os, json, hashlib
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import (
    apply_gamma_503_recursive, phi_ent_observe, spectral_ent_project,
    persist_scene_504, seed_memory_init_504, spatial_key_504,
    estimate_global_motion_505, world_frame_key_505, track_correspondence_505, track_dag_hash_505,
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

# ---- build ONE fixed octree (stationary partition; pure motion isolates Ghost #28) ----
bbox0 = (np.zeros(3), np.ones(3)); ks = kappa_integral(bbox0)
stalk = np.array([1.,1.,1.,1., 0.5,0.5,0.5,1., 0.6,0.,0.8,ks, 0.,0.,0.,0.,0.,0.])
SH = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0, K_budget=2048, depth=0,
          focal_point=np.array([0.5,0.5,0.5]), B=np.array([1.0,0.5,0.3]), J_AC=np.eye(4), W_max=8,
          beta_Z_base=_BETA_Z_313, gamma_inf_A=_GAMMA_INF_A_409, gamma_inf_D=_GAMMA_INF_D_409,
          tau_warmup=_TAU_WARMUP_409, alpha_disc=_ALPHA_DISC_409, alpha_maint=_ALPHA_MAINT_409,
          beta_threshold=_BETA_THRESHOLD_409, beta_Z_min=_BETA_Z_MIN_409, gamma_inf_ent=_GAMMA_INF_ENT_503)
prov = Provenance(parent_ids=(), operator_id="seed505", timestamp=now_iso())
c0 = Claim(provenance=prov, payload="scene:exp505:seed", stalk=stalk.copy(), t=0, bbox=bbox0)
mu0 = MuState(t=0, claims={c0.id: c0}, entailments={}, active=frozenset([c0.id]), S=np.zeros(12),
              alpha=ALPHA, S_A=np.zeros(8), S_C=np.zeros(4), S_D=np.zeros(6))
mu0 = apply_gamma_503_recursive(mu=mu0, claim_id=c0.id, scene_n=10, bze_ema_prev=13.0,
                                maint_latched=True, B_ent_spectral_prev=0.12, **SH)[0]
LEAVES = [(np.array(mu0.claims[cc].stalk, float),
           (np.asarray(mu0.claims[cc].bbox[0], float), np.asarray(mu0.claims[cc].bbox[1], float)))
          for cc in mu0.active]
NLEAF = len(LEAVES)
V = np.array([0.07, 0.03, 0.0]); N = 16; TEAR_N = 8; TEAR = 12.0
def cent(bb): return (bb[0] + bb[1]) / 2.0
print(f"  fixed octree: {NLEAF} leaves; world drift V={V.tolist()} per scene over N={N}")

def run(mode):
    mem = seed_memory_init_504(); mem["cumulative_motion"] = np.zeros(3); mem["prev_mean"] = None
    cont = []; max_sent = []; watch = None; watch_series = []; hashes = []; gates = []; ntracks = []
    for n in range(N):
        M = V * n
        Zc = {f"l{i}": LEAVES[i][0] for i in range(NLEAF)}
        bx = {f"l{i}": (LEAVES[i][1][0] + M, LEAVES[i][1][1] + M) for i in range(NLEAF)}
        g, _, Bent, Ne, l2, ed = phi_ent_observe(Zc, bx, {k: 0.0 for k in Zc}, degree_normalize=True)
        Bsp, _, _, _ = spectral_ent_project(g, ed, list(Zc), Z_claims=Zc, k_modes=_K_FIEDLER_503)
        cc = [cent(bx[k]) for k in Zc]
        if mode == "raw504":
            keys = {k: spatial_key_504(bx[k]) for k in Zc}
            matched = sum(1 for k in Zc if keys[k] in set(mem["S_ent"].keys()))
            sent = {keys[k]: g[k] for k in Zc}; hsh = ""
        else:
            if mem["prev_mean"] is not None:
                mem["cumulative_motion"] = mem["cumulative_motion"] + (np.mean(cc, axis=0) - mem["prev_mean"])
            c2t, dag, nm, nn = track_correspondence_505(set(mem["S_ent"].keys()), bx, mem["cumulative_motion"])
            matched = nm; sent = {c2t[k]: g[k] for k in Zc}
            hsh = track_dag_hash_505(dag, nm, nn)
            if watch is None: watch = c2t["l0"]
        if mode == "track505" and n == TEAR_N:
            sent[watch] = sent.get(watch, 0.0) + TEAR
        pm = np.mean(cc, axis=0); cm = mem["cumulative_motion"]
        mem = persist_scene_504(mem, np.zeros(8), np.zeros(4), np.zeros(6), sent, Bsp, 13.0, True, alpha_persist=_ALPHA_PERSIST_504)
        mem["cumulative_motion"] = cm; mem["prev_mean"] = pm
        cont.append(matched / NLEAF); max_sent.append(max(mem["S_ent"].values()))
        gates.append(is_manifold_501(Bent)); ntracks.append(len(mem["S_ent"]))
        if mode == "track505": watch_series.append(mem["S_ent"].get(watch, 0.0))
        hashes.append(hsh)
    return dict(cont=cont, max_sent=max_sent, watch=watch_series, hashes=hashes, gates=gates, ntracks=ntracks)

raw = run("raw504"); trk = run("track505")

# [2] motion estimate exact
c_prev = [cent((LEAVES[i][1][0], LEAVES[i][1][1])) for i in range(NLEAF)]
c_curr = [cent((LEAVES[i][1][0] + V, LEAVES[i][1][1] + V)) for i in range(NLEAF)]
v_est = estimate_global_motion_505(c_prev, c_curr)
assert np.max(np.abs(v_est - V)) < 1e-12, f"[2] FAIL {v_est}"
print(f"[2] PASS  estimate_global_motion_505 -> {np.round(v_est,4).tolist()} == V (err<1e-12)")

# [3] world-frame key stable under motion
k_s0 = world_frame_key_505((LEAVES[0][1][0], LEAVES[0][1][1]), np.zeros(3))
k_s5 = world_frame_key_505((LEAVES[0][1][0] + V*5, LEAVES[0][1][1] + V*5), V*5)
assert k_s0 == k_s5, "[3] FAIL world-frame key not stable"
print(f"[3] PASS  world_frame_key_505 stable across scenes under motion (leaf 0)")

# [4]/[5] continuity
craw = float(np.mean(raw["cont"][1:])); ctrk = float(np.mean(trk["cont"][1:]))
assert craw < 0.05, f"[4] FAIL raw continuity {craw}"
print(f"[4] PASS  RAW504 continuity under motion = {craw:.3f} ~ 0 (Ghost #28: memory lost)")
assert ctrk > 0.95, f"[5] FAIL track continuity {ctrk}"
print(f"[5] PASS  TRACK505 continuity under motion = {ctrk:.3f} ~ 1 (memory follows moving claims)")

# [6] localized memory buildup
raw_flat = max(raw["max_sent"]) - min(raw["max_sent"])
trk_grow = trk["max_sent"][6] - trk["max_sent"][0]
assert raw_flat < 1e-6 and trk_grow > 1.0, f"[6] FAIL raw_flat={raw_flat} trk_grow={trk_grow}"
print(f"[6] PASS  TRACK505 per-track EMA buildup (+{trk_grow:.2f}); RAW504 flat (range {raw_flat:.1e})")

# [7] healing under motion
steady = trk["watch"][TEAR_N - 1]
exc = [trk["watch"][TEAR_N + j] - steady for j in range(5)]
ratios = [exc[j+1]/exc[j] for j in range(3)]
assert all(exc[j] > exc[j+1] for j in range(3)) and all(abs(r - _ALPHA_PERSIST_504) < 0.15 for r in ratios), f"[7] FAIL exc={exc}"
print(f"[7] PASS  healing under motion: tear excess {[round(e,2) for e in exc]} decays ratio~{_ALPHA_PERSIST_504} {[round(r,3) for r in ratios]}")

# [8] DAG hash reproducible
assert run("track505")["hashes"] == trk["hashes"]
print(f"[8] PASS  DAG hash reproducible across re-run ({trk['hashes'][1][:12]}...)")

# [9] gate admissible
assert all(trk["gates"]) and all(raw["gates"])
print(f"[9] PASS  is_manifold_501 admissible all {N} scenes")

# [10] track count == leaf count (bounded)
assert trk["ntracks"][-1] == NLEAF, f"[10] FAIL ntracks={trk['ntracks'][-1]} != {NLEAF}"
print(f"[10] PASS  track count == leaf count = {NLEAF} (one track per claim; no explosion)")

print(f"\n=== EXP-505 Fork A: 10/10 PASS ===")
print(f"    moving world: RAW504 continuity {craw:.2f} (Ghost #28) -> TRACK505 {ctrk:.2f} (resolved)")
print(f"    localized memory survives motion (+{trk_grow:.1f} EMA); tear heals across motion (ratio~{_ALPHA_PERSIST_504})")
print(f"    world-frame re-referencing + hash-indexed correspondence DAG; {NLEAF} tracks, bounded")
