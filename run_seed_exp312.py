"""
run_seed_exp312.py - Fork A: EXP-312 Seed Validation

Protocol: exp312-v1
declaration_hash: 2e6ccdc20da7aefb2a6bb3b024d8a3102c87e706d610ba454122afaf66329cc5

Asserts:
  1. Declaration hash matches SEED_DECLARATION_exp312.json
  2. norm(S_C) > 0.01 after recursive 312 run
  3. norm(S_A) > 0.001 after recursive 312 run
  4. G_inject_C[3] != 0 at every partition step
  5. S_C[3] > 0 (EMA accumulation confirmed)
  6. Ghost history populated
  7. H_t chain continuous
  8. fwd_leaves > 0 (tree expands)

Dev notes:
  - Uniform Sector A split: stalk_A_i = stalk_A / N
  - Extents-based bbox payload: f(|hi-lo|) not f(lo,hi)
  - Both fixes together yield full multi-step P_yz invariance (see Fork B)
"""

import sys, os, json, hashlib
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import apply_gamma_312_recursive
from engine.validity import kappa_integral

# === Declaration hash check ===
DECL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "studies/exp312_symmetric_budget/SEED_DECLARATION_exp312.json",
)
EXPECTED_HASH = "2e6ccdc20da7aefb2a6bb3b024d8a3102c87e706d610ba454122afaf66329cc5"

with open(DECL_PATH) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
canon = json.dumps(decl, sort_keys=True, separators=(",", ":"))
computed = hashlib.sha256(canon.encode()).hexdigest()
assert stored == EXPECTED_HASH, f"Hash stored/expected mismatch: {stored}"
assert computed == EXPECTED_HASH, f"Hash computed/expected mismatch: {computed}"
print(f"[1] PASS  declaration_hash = {EXPECTED_HASH[:16]}...")

# === Build seed state ===
ALPHA_EMA = 0.85
D = 12

root_bbox = (np.zeros(3), np.ones(3))
kappa_root = kappa_integral(root_bbox)   # 2.0 for unit cube

prov = Provenance(parent_ids=(), operator_id="seed_exp312", timestamp=now_iso())
seed_stalk = np.array([1.0, 1.0, 1.0, 1.0,
                        0.5, 0.5, 0.5, 1.0,
                        0.0, 0.0, 1.0,
                        kappa_root])

root_claim = Claim(
    provenance=prov,
    payload="root: d=12 EXP-312",
    stalk=seed_stalk.copy(),
    t=0,
    bbox=root_bbox,
)

mu0 = MuState(
    t=0,
    claims={root_claim.id: root_claim},
    entailments={},
    active=frozenset([root_claim.id]),
    S=np.zeros(D),
    alpha=ALPHA,
    S_A=np.zeros(8),
    S_C=np.zeros(4),
)
mu0.seal()

S_C_initial_norm = float(np.linalg.norm(mu0.S_C))
S_A_initial_norm = float(np.linalg.norm(mu0.S_A))
root_id = root_claim.id

# === Run recursive 312 ===
mu_final, total_cost = apply_gamma_312_recursive(
    mu=mu0,
    claim_id=root_id,
    partition_key="octree_split",
    beta=1.0,
    budget=1e9,
    spent=0.0,
    K_budget=256,
    depth=0,
    focal_point=np.array([0.5, 0.5, 0.5]),
    alpha_leak=0.1,
    beta_CA=0.3,
    mass_ref=2.0,
    kappa_ref=2.0,
)

n_leaves = len(mu_final.active)
S_C_final = mu_final.S_C if mu_final.S_C is not None else np.zeros(4)
S_A_final = mu_final.S_A if mu_final.S_A is not None else np.zeros(8)
S_C_norm = float(np.linalg.norm(S_C_final))
S_A_norm = float(np.linalg.norm(S_A_final))
G_inject_log = getattr(mu_final, "G_inject_log", [])

print(f"    Recursive 312: {n_leaves} leaves, total_cost={total_cost:.4f}")
print(f"    norm(S_C) = {S_C_norm:.6f}  (initial: {S_C_initial_norm:.6f})")
print(f"    norm(S_A) = {S_A_norm:.6f}  (initial: {S_A_initial_norm:.6f})")
print(f"    G_inject_log entries: {len(G_inject_log)}")
if G_inject_log:
    gc_vals = [e[0] for e in G_inject_log]
    ga_vals = [e[1] for e in G_inject_log]
    print(f"    G_inject_C[3] range: [{min(gc_vals):.6f}, {max(gc_vals):.6f}]")
    print(f"    G_inject_A[7] range: [{min(ga_vals):.6f}, {max(ga_vals):.6f}]")

# === Assertions ===

# [2] S_C activated
assert S_C_norm > 0.01, f"norm(S_C) too small: {S_C_norm:.8f} (need > 0.01)"
print(f"[2] PASS  norm(S_C) = {S_C_norm:.6f} > 0.01")

# [3] S_A activated
assert S_A_norm > 0.001, f"norm(S_A) too small: {S_A_norm:.8f} (need > 0.001)"
print(f"[3] PASS  norm(S_A) = {S_A_norm:.6f} > 0.001")

# [4] G_inject log non-empty, all C entries non-zero
assert len(G_inject_log) > 0, "G_inject_log is empty -- no partition steps recorded"
gc_vals = [e[0] for e in G_inject_log]
ga_vals = [e[1] for e in G_inject_log]
all_nonzero = all(abs(v) > 1e-12 for v in gc_vals)
assert all_nonzero, "Some G_inject_C[3] entries are zero"
print(f"[4] PASS  G_inject_log has {len(G_inject_log)} entries; all G_inject_C[3] non-zero")

# [5] S_C[3] accumulated
assert float(S_C_final[3]) > 1e-6, (
    f"S_C[3]={S_C_final[3]:.8f} not positive (EMA did not accumulate)"
)
print(f"[5] PASS  S_C[3] = {S_C_final[3]:.6f} > 0 (EMA accumulated)")

# [6] Ghost history populated
gh = getattr(mu_final, "ghost_history", None)
assert gh is not None and len(gh) > 0, "ghost_history empty"
a_series = [h[0] for h in gh]
c_series = [h[1] for h in gh]
assert max(c_series) > 1e-6, f"c_series all zero: max={max(c_series)}"
print(f"[6] PASS  ghost_history len={len(gh)}; c_max={max(c_series):.6f}, a_max={max(a_series):.6f}")

# [7] H_t chain continuous
assert mu_final._H is not None, "H_t is None after run -- hash chain broken"
print(f"[7] PASS  H_t = {mu_final._H[:16]}...")

# [8] Tree expanded
assert n_leaves > 0, "Zero leaves -- tree did not expand"
print(f"[8] PASS  n_leaves = {n_leaves} > 0")

# === Observables ===
Z_final = mu_final.Z()
norm_ZA = float(np.linalg.norm(Z_final[0:8]))
norm_ZC = float(np.linalg.norm(Z_final[8:12]))
B_A = S_A_norm / (norm_ZA + 1e-15)
B_C = S_C_norm / (norm_ZC + 1e-15)
print(f"  OBS: B_A(t) = {B_A:.6f}  |  B_C(t) = {B_C:.6f}")
print(f"  OBS: norm(Z_A) = {norm_ZA:.6f}  |  norm(Z_C) = {norm_ZC:.6f}")

coupling_ratio = sum(gc_vals) / (sum(ga_vals) + 1e-15)
print(f"  OBS: sum(G_inject_C)/sum(G_inject_A) = {coupling_ratio:.4f}")

print(f"\nFork A: ALL TESTS PASSED ({n_leaves} leaves)")
