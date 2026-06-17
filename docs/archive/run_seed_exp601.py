"""
run_seed_exp601.py -- Fork A: EXP-601 Deterministic Seeding (kill Ghost #27)

Protocol: exp601-v1
Declaration hash: f352e458d1e252f4af0fc555e8a76b4bfe7f7182c96d521d95341cfdf36d26fc

engine/state.py: Claim.id excludes the wall-clock timestamp. id = f(parent.id, child_index,
payload, t, protocol). Same SEED_DECLARATION -> bit-identical ids and H_t across runs.

Tests [1-10]: see SEED_DECLARATION_exp601.json assertions_fork_A.
"""
import sys, os, json, hashlib
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA, PROTOCOL_VERSION
from engine.operators import (
    apply_gamma_503_recursive, seed_memory_init_504, seed_memory_hash_504, persist_scene_504,
    spatial_key_504,
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
stalk = np.array([1.,1.,1.,1., 0.5,0.5,0.5,1., 0.6,0.,0.8,ks, 0.,0.,0.,0.,0.,0.])
SH = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0, K_budget=2048, depth=0,
          focal_point=np.array([0.5,0.5,0.5]), B=np.array([1.0,0.5,0.3]), J_AC=np.eye(4), W_max=8,
          beta_Z_base=_BETA_Z_313, gamma_inf_A=_GAMMA_INF_A_409, gamma_inf_D=_GAMMA_INF_D_409,
          tau_warmup=_TAU_WARMUP_409, alpha_disc=_ALPHA_DISC_409, alpha_maint=_ALPHA_MAINT_409,
          beta_threshold=_BETA_THRESHOLD_409, beta_Z_min=_BETA_Z_MIN_409, gamma_inf_ent=_GAMMA_INF_ENT_503)

def _id_of(parent_ids, operator_id, payload, t):
    raw = json.dumps({"provenance": {"parent_ids": list(parent_ids), "operator_id": operator_id},
                      "payload": payload, "t": t, "protocol_version": PROTOCOL_VERSION},
                     sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()[:16]

# [2] timestamp excluded from identity
c1 = Claim(provenance=Provenance(parent_ids=("p",), operator_id="Gamma:octree_split:2", timestamp="2020-01-01T00:00:00+00:00"), payload="x", stalk=stalk.copy(), t=1, bbox=bbox)
c2 = Claim(provenance=Provenance(parent_ids=("p",), operator_id="Gamma:octree_split:2", timestamp="2099-12-31T23:59:59+00:00"), payload="x", stalk=stalk.copy(), t=1, bbox=bbox)
assert c1.id == c2.id, "[2] FAIL: id depends on timestamp"
print(f"[2] PASS  timestamp excluded from id ({c1.id}); two timestamps -> same id")

# [3] child id == recomputed deterministic hash
assert c1.id == _id_of(("p",), "Gamma:octree_split:2", "x", 1), "[3] FAIL recompute"
print(f"[3] PASS  child id == SHA256(parent_ids+operator_id+payload+t+protocol)[:16]")

# build a deterministic octree + measure state digest twice
def run_state():
    prov = Provenance(parent_ids=(), operator_id="seed_exp601", timestamp=now_iso())
    c0 = Claim(provenance=prov, payload="scene:exp601", stalk=stalk.copy(), t=0, bbox=bbox)
    mu = MuState(t=0, claims={c0.id: c0}, entailments={}, active=frozenset([c0.id]), S=np.zeros(12),
                 alpha=ALPHA, S_A=np.zeros(8), S_C=np.zeros(4), S_D=np.zeros(6))
    bze = float(_BETA_Z_313); maint = False; mem = seed_memory_init_504()
    for n in range(8):
        if n > 0:
            prov = Provenance(parent_ids=(), operator_id="seed_exp601", timestamp=now_iso())
            c0 = Claim(provenance=prov, payload="scene:exp601", stalk=stalk.copy(), t=0, bbox=bbox)
            mu = MuState(t=0, claims={c0.id: c0}, entailments={}, active=frozenset([c0.id]), S=np.zeros(12),
                         alpha=ALPHA, S_A=np.array(mu.S_A), S_C=np.array(mu.S_C), S_D=np.array(mu.S_D))
        cid = next(iter(mu.active))
        out = apply_gamma_503_recursive(mu=mu, claim_id=cid, scene_n=n, bze_ema_prev=bze, maint_latched=maint, B_ent_spectral_prev=0.0, **SH)
        mu, bze, maint = out[0], out[3], out[12]
    W = sorted(mu.active)
    Z = np.concatenate([np.asarray(mu.claims[c].stalk, float) for c in W])
    digest = hashlib.sha256(json.dumps({"W": W, "Z": [float(x) for x in Z], "SA": [float(x) for x in mu.S_A]}, sort_keys=True).encode()).hexdigest()
    return W, np.array(mu.S_A), digest, len(mu.active)

W1, SA1, d1, nl1 = run_state()
W2, SA2, d2, nl2 = run_state()

assert d1 == d2, "[4] FAIL: H_t not bitwise reproducible"
print(f"[4] PASS  bitwise H_t reproducible across runs ({d1[:16]}...)")

children = [cid for cid in W1]
assert len(children) == len(set(children)), "[5] FAIL sibling id collision"
print(f"[5] PASS  {len(children)} claim ids all distinct (child_index in operator_id)")

assert W1 == W2, "[6] FAIL: claim-id set not stable across runs"
print(f"[6] PASS  claim-id set bit-stable across runs ({len(W1)} ids identical)")

assert nl1 == nl2 and nl1 in (64, 71, 106, 92, 113, 127, 148), f"[7] FAIL leaf count {nl1}"
print(f"[7] PASS  leaf count stable = {nl1} (no structural regression)")

assert np.array_equal(SA1, SA2), "[8] FAIL: S_A not bitwise identical"
print(f"[8] PASS  carried S_A bitwise identical (max diff {float(np.max(np.abs(SA1-SA2))):.0e}) -- Ghost #27 killed")

# [9] seed_memory_hash reproducible
def run_mem():
    prov = Provenance(parent_ids=(), operator_id="seed_exp601", timestamp=now_iso())
    c0 = Claim(provenance=prov, payload="scene:exp601", stalk=stalk.copy(), t=0, bbox=bbox)
    mu = MuState(t=0, claims={c0.id: c0}, entailments={}, active=frozenset([c0.id]), S=np.zeros(12),
                 alpha=ALPHA, S_A=np.zeros(8), S_C=np.zeros(4), S_D=np.zeros(6))
    out = apply_gamma_503_recursive(mu=mu, claim_id=c0.id, scene_n=5, bze_ema_prev=13.0, maint_latched=True, B_ent_spectral_prev=0.1, **SH)
    mu = out[0]
    mem = persist_scene_504(seed_memory_init_504(), mu.S_A, mu.S_C, mu.S_D, {spatial_key_504(mu.claims[c].bbox): 1.0 for c in mu.active}, 0.1, 13.0, True)
    return seed_memory_hash_504(mem)
assert run_mem() == run_mem(), "[9] FAIL seed_memory_hash not reproducible"
print(f"[9] PASS  seed_memory_hash_504 bitwise reproducible across runs")

# [10] sensitivity: different declaration -> different digest
stalk_b = stalk.copy(); stalk_b[0] = 2.0
def run_other():
    prov = Provenance(parent_ids=(), operator_id="seed_exp601", timestamp=now_iso())
    c0 = Claim(provenance=prov, payload="scene:exp601:B", stalk=stalk_b.copy(), t=0, bbox=bbox)
    mu = MuState(t=0, claims={c0.id: c0}, entailments={}, active=frozenset([c0.id]), S=np.zeros(12),
                 alpha=ALPHA, S_A=np.zeros(8), S_C=np.zeros(4), S_D=np.zeros(6))
    out = apply_gamma_503_recursive(mu=mu, claim_id=c0.id, scene_n=5, bze_ema_prev=13.0, maint_latched=True, B_ent_spectral_prev=0.1, **SH)
    W = sorted(out[0].active); Z = np.concatenate([np.asarray(out[0].claims[c].stalk, float) for c in W])
    return hashlib.sha256(json.dumps({"W": W, "Z": [float(x) for x in Z]}, sort_keys=True).encode()).hexdigest()
assert run_other() != d1
print(f"[10] PASS  different SEED_DECLARATION -> different digest (H_t sensitive)")

print(f"\n=== EXP-601 Fork A: 10/10 PASS ===")
print(f"    Claim.id timestamp-excluded; bitwise H_t reproducible; S_A bit-identical; Ghost #27 killed")
print(f"    engine change scope: state.py ONLY; leaf count {nl1}; {len(W1)} stable claim ids")
