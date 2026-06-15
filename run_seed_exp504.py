"""
run_seed_exp504.py -- Fork A: EXP-504 Stateful Seed (temporal manifold smoothing)

Protocol: exp504-v1
Declaration hash: 93201baeac72aac92183da7bdf5c1d9da7fb144abeea66d3b1cca38ecf47530c

Persists the full state vector across scene resets (SeedMemory) so the EXP-503 manifold
restoring force has memory: a tectonic tear in B_ent_spectral decays geometrically (heals)
across scenes instead of being forgotten at each reset. persist_scene_504 is stateless.

Tests [1-10]: see SEED_DECLARATION_exp504.json assertions_fork_A.
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
    _ALPHA_PERSIST_504, _DECAY_AWAY_504, _PRUNE_EPS_504,
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

# [2] cold start
m0 = seed_memory_init_504()
assert (np.allclose(m0["S_A"], 0) and np.allclose(m0["S_C"], 0) and np.allclose(m0["S_D"], 0)
        and m0["S_ent"] == {} and m0["maint_latched"] is False and m0["scene_count"] == 0
        and m0["B_ent_spectral"] == 0.0)
print("[2] PASS  cold-start SeedMemory: sectors zero, S_ent empty, unlatched, scene_count=0")

# [3] hash determinism + sensitivity
h_a = seed_memory_hash_504(seed_memory_init_504())
h_b = seed_memory_hash_504(seed_memory_init_504())
m_chg = seed_memory_init_504(); m_chg["B_ent_spectral"] = 0.123
h_c = seed_memory_hash_504(m_chg)
assert h_a == h_b and h_a != h_c
print(f"[3] PASS  H_seed deterministic ({h_a[:12]}) and sensitive to state change ({h_c[:12]})")

# [4] EMA persistence formula (unit): repeated obs {k:1.0} -> 1 - alpha^n
A = _ALPHA_PERSIST_504; key = (("x",), ("s",))
m = seed_memory_init_504(); preds = []
for n in range(1, 6):
    m = persist_scene_504(m, np.zeros(8), np.zeros(4), np.zeros(6),
                          {key: 1.0}, 0.0, _BETA_Z_313, False, alpha_persist=A)
    preds.append((m["S_ent"][key], 1.0 - A**n))
assert all(abs(a - b) < 1e-12 for a, b in preds), f"[4] FAIL {preds}"
print(f"[4] PASS  EMA persistence S_ent[k] = 1 - alpha^n exact: {[round(a,4) for a,_ in preds]}")

# [5] away-key decay + prune
m = seed_memory_init_504()
m = persist_scene_504(m, np.zeros(8), np.zeros(4), np.zeros(6), {key: 1.0}, 0.0, _BETA_Z_313, False, alpha_persist=A)
v_present = m["S_ent"][key]
m = persist_scene_504(m, np.zeros(8), np.zeros(4), np.zeros(6), {}, 0.0, _BETA_Z_313, False,
                      alpha_persist=A, decay_away=_DECAY_AWAY_504)
v_away = m["S_ent"].get(key, 0.0)
assert abs(v_away - _DECAY_AWAY_504 * v_present) < 1e-12
# prune: decay below eps removes key
m_small = seed_memory_init_504(); m_small["S_ent"] = {key: _PRUNE_EPS_504 * 1.5}
m_small = persist_scene_504(m_small, np.zeros(8), np.zeros(4), np.zeros(6), {}, 0.0, _BETA_Z_313, False, decay_away=_DECAY_AWAY_504)
assert key not in m_small["S_ent"]
print(f"[5] PASS  away-key decay (x{_DECAY_AWAY_504}) {v_present:.4f}->{v_away:.4f} and prune below {_PRUNE_EPS_504}")

# ---- closed-loop tear+heal harness ----
bbox = (np.zeros(3), np.ones(3)); ks = kappa_integral(bbox)
stalk = np.array([1.,1.,1.,1., 0.5,0.5,0.5,1., 0.6,0.,0.8,ks, 0.,0.,0.,0.,0.,0.])
SH = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0, K_budget=2048, depth=0,
          focal_point=np.array([0.5,0.5,0.5]), B=np.array([1.0,0.5,0.3]), J_AC=np.eye(4), W_max=8,
          beta_Z_base=_BETA_Z_313, gamma_inf_A=_GAMMA_INF_A_409, gamma_inf_D=_GAMMA_INF_D_409,
          tau_warmup=_TAU_WARMUP_409, alpha_disc=_ALPHA_DISC_409, alpha_maint=_ALPHA_MAINT_409,
          beta_threshold=_BETA_THRESHOLD_409, beta_Z_min=_BETA_Z_MIN_409, gamma_inf_ent=_GAMMA_INF_ENT_503)
def mk(s, SA=None, SC=None, SD=None):
    p = Provenance(parent_ids=(), operator_id="s504", timestamp=now_iso())
    c = Claim(provenance=p, payload="sc", stalk=s.copy(), t=0, bbox=bbox)
    return MuState(t=0, claims={c.id: c}, entailments={}, active=frozenset([c.id]), S=np.zeros(12), alpha=ALPHA,
        S_A=np.array(SA) if SA is not None else np.zeros(8),
        S_C=np.array(SC) if SC is not None else np.zeros(4),
        S_D=np.array(SD) if SD is not None else np.zeros(6))
def scene(mem):
    mu = mk(stalk, mem["S_A"], mem["S_C"], mem["S_D"]); cid = next(iter(mu.active))
    out = apply_gamma_503_recursive(mu=mu, claim_id=cid, scene_n=mem["scene_count"],
        bze_ema_prev=mem["bze_ema_prev"], maint_latched=mem["maint_latched"],
        B_ent_spectral_prev=mem["B_ent_spectral"], **SH)
    mu, bze, maint = out[0], out[3], out[12]
    Zc = {c: np.array(mu.claims[c].stalk, float) for c in mu.active}
    bx = {c: mu.claims[c].bbox for c in mu.active}
    g, _, Bent, Ne, l2, ed = phi_ent_observe(Zc, bx, {c: 0.0 for c in mu.active}, degree_normalize=True)
    Bsp, lam, fied, gsp = spectral_ent_project(g, ed, list(mu.active), Z_claims=Zc, k_modes=_K_FIEDLER_503)
    sent = {spatial_key_504(bx[c]): g[c] for c in mu.active}
    return mu, bze, maint, Bsp, Bent, sent
N, TEAR_N, TEAR = 14, 5, 0.6
def run(alpha_persist):
    mem = seed_memory_init_504(); persisted = []; gate = []; hashes = []
    for n in range(N):
        mu, bze, maint, Bsp, Bent, sent = scene(mem)
        Bsp_obs = Bsp + (TEAR if n == TEAR_N else 0.0)
        mem = persist_scene_504(mem, mu.S_A, mu.S_C, mu.S_D, sent, Bsp_obs, bze, maint, alpha_persist=alpha_persist)
        persisted.append(mem["B_ent_spectral"]); gate.append(is_manifold_501(Bent)); hashes.append(seed_memory_hash_504(mem))
    return persisted, gate, hashes
on, gate_on, hashes_on = run(_ALPHA_PERSIST_504)
off, gate_off, _ = run(0.0)

base = on[TEAR_N - 1]
excess = [on[TEAR_N + j] - base for j in range(5)]
# [6] strictly decreasing for >=3 scenes
assert all(excess[j] > excess[j+1] for j in range(3)) and excess[0] > 0, f"[6] FAIL {excess}"
print(f"[6] PASS  temporal healing: post-tear excess {[round(e,4) for e in excess]} strictly decreasing")

# [7] decay ratio ~ alpha_persist
ratios = [excess[j+1]/excess[j] for j in range(3)]
assert all(abs(r - _ALPHA_PERSIST_504) < 0.2 for r in ratios), f"[7] FAIL {ratios}"
print(f"[7] PASS  healing decay ratio {[round(r,3) for r in ratios]} ~ alpha_persist={_ALPHA_PERSIST_504}")

# [8] amnesiac contrast
ex_off = [off[TEAR_N + j] - off[TEAR_N - 1] for j in range(3)]
assert abs(ex_off[1]) < 0.1 * abs(ex_off[0]) + 0.05, f"[8] FAIL {ex_off}"
print(f"[8] PASS  amnesiac (alpha=0): excess {[round(e,4) for e in ex_off]} -> forgotten in 1 scene")

# [9] gate admissible + bounded
assert all(gate_on) and max(on) < 1.0, f"[9] FAIL gate={gate_on} max={max(on)}"
print(f"[9] PASS  gate admissible all {N} scenes; persisted B_ent_spectral bounded (max={max(on):.4f})")

# [10] hash continuity: reproducible distinct indices
on2, _, hashes_on2 = run(_ALPHA_PERSIST_504)
assert hashes_on == hashes_on2 and len(set(hashes_on)) >= N - 1
print(f"[10] PASS  hash continuity: {len(set(hashes_on))}/{N} distinct, reproducible across re-run")

print(f"\n=== EXP-504 Fork A: 10/10 PASS ===")
print(f"    SeedMemory persists S_A/S_C/S_D, S_ent(spatial-keyed), bze_ema, maint, B_ent_spectral")
print(f"    temporal healing: tear excess {round(excess[0],3)} -> {round(excess[-1],3)} (ratio~{_ALPHA_PERSIST_504})")
print(f"    amnesiac without memory; alpha_persist={_ALPHA_PERSIST_504} decay_away={_DECAY_AWAY_504}")
print(f"    H_seed structural index; gate admissible; Ghost #26 lifted (memory enables healing)")
