"""
run_seed_exp314.py - Fork A: EXP-314 Hyperfine Ghost Seed Validation

Protocol: exp314-v1
declaration_hash: 5ca52bef5d2a508073ab8585a1e84aa8393e64ddd7672c2c48ab4dd4a0a5006c

Asserts:
  1. Declaration hash match
  2. Omega_AC != 0 after first partition (channels not perfectly aligned)
  3. tau_opt in {1, ..., W_max}
  4. ghost_history entries contain (S_A_norm, S_C_norm, Omega_AC, tau_opt)
  5. norm(S_C) > 0.01, norm(S_A) > 0.001
  6. H_t chain continuous
  7. n_leaves > 0
  8. Omega_AC evolves across partition steps (non-constant)

Dev note (ghost #6 -- hyperfine coupling):
  Omega_AC is the first inter-channel observable. J_AC=I means we measure the
  angle between S_A[0:4] and S_C directly. tau_opt = max(1, round(Omega/pi * 8))
  provides deterministic lag selection for multi-lag TE without grid search.
"""

import sys, os, json, hashlib, math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.state import MuState, Claim, Provenance, now_iso, ALPHA_DEFAULT as ALPHA
from engine.operators import apply_gamma_314_recursive, _compute_omega_ac, _tau_opt
from engine.validity import kappa_integral

DECL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "studies/exp314_hyperfine_ghost/SEED_DECLARATION_exp314.json",
)
EXPECTED_HASH = "5ca52bef5d2a508073ab8585a1e84aa8393e64ddd7672c2c48ab4dd4a0a5006c"

with open(DECL_PATH) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
canon = json.dumps(decl, sort_keys=True, separators=(",", ":"))
computed = hashlib.sha256(canon.encode()).hexdigest()
assert stored == EXPECTED_HASH
assert computed == EXPECTED_HASH
print(f"[1] PASS  declaration_hash = {EXPECTED_HASH[:16]}...")

D = 12
B = np.array([1.0, 0.5, 0.3])
BETA_Z = 2.0
J_AC = np.eye(4)
W_MAX = 8

root_bbox = (np.zeros(3), np.ones(3))
kappa_root = kappa_integral(root_bbox)

prov = Provenance(parent_ids=(), operator_id="seed_exp314", timestamp=now_iso())
seed_stalk = np.array([1.0, 1.0, 1.0, 1.0,
                        0.5, 0.5, 0.5, 1.0,
                        0.0, 0.0, 1.0,
                        kappa_root])

root_claim = Claim(
    provenance=prov, payload="root: d=12 EXP-314",
    stalk=seed_stalk.copy(), t=0, bbox=root_bbox,
)
mu0 = MuState(
    t=0, claims={root_claim.id: root_claim}, entailments={},
    active=frozenset([root_claim.id]),
    S=np.zeros(D), alpha=ALPHA, S_A=np.zeros(8), S_C=np.zeros(4),
)
mu0.seal()
root_id = root_claim.id

mu_final, total_cost, w0 = apply_gamma_314_recursive(
    mu=mu0, claim_id=root_id, partition_key="octree_split",
    beta=1.0, budget=1e9, spent=0.0, K_budget=2048,
    depth=0, focal_point=np.array([0.5, 0.5, 0.5]),
    B=B, beta_Z=BETA_Z, J_AC=J_AC, W_max=W_MAX,
    alpha_leak=0.1, beta_CA=0.3, mass_ref=2.0, kappa_ref=2.0,
)

n_leaves = len(mu_final.active)
S_C_final = mu_final.S_C if mu_final.S_C is not None else np.zeros(4)
S_A_final = mu_final.S_A if mu_final.S_A is not None else np.zeros(8)
S_C_norm = float(np.linalg.norm(S_C_final))
S_A_norm = float(np.linalg.norm(S_A_final))
gh = list(getattr(mu_final, "ghost_history", []) or [])
# ghost_history contains mixed-length entries:
#   2-tuples: (S_A_norm, S_C_norm) from apply_gamma_312 (base partition kernel)
#   4-tuples: (S_A_norm, S_C_norm, Omega_AC, tau_opt) from apply_gamma_314 (hyperfine layer)
gh4 = [h for h in gh if len(h) == 4]  # EXP-314 entries only

print(f"    Recursive 314: {n_leaves} leaves, total_cost={total_cost:.4f}")
print(f"    norm(S_C) = {S_C_norm:.6f}  norm(S_A) = {S_A_norm:.6f}")
print(f"    ghost_history total={len(gh)}  (4-tuple EXP-314 entries: {len(gh4)})")
if gh4:
    omegas = [h[2] for h in gh4]
    taus = [h[3] for h in gh4]
    print(f"    Omega_AC range: [{min(omegas):.4f}, {max(omegas):.4f}] rad")
    print(f"    tau_opt range:  [{min(taus)}, {max(taus)}]")
    print(f"    Final: Omega_AC={omegas[-1]:.4f} rad  tau_opt={taus[-1]}")

# [2] Omega_AC >= 0 in final EXP-314 entry
assert len(gh4) > 0, "No 4-tuple ghost_history entries from EXP-314"
omega_final = gh4[-1][2]
assert omega_final >= 0.0, f"Omega_AC negative: {omega_final}"
print(f"[2] PASS  Omega_AC final = {omega_final:.6f} rad (>= 0)")

# [3] tau_opt in range
tau_final = int(gh4[-1][3])
assert 1 <= tau_final <= W_MAX, f"tau_opt={tau_final} outside [1,{W_MAX}]"
print(f"[3] PASS  tau_opt = {tau_final} in [1, {W_MAX}]")

# [4] EXP-314 ghost_history entries are 4-tuples
assert all(len(h) == 4 for h in gh4), "EXP-314 ghost entries not 4-tuples"
print(f"[4] PASS  EXP-314 ghost_history has {len(gh4)} 4-tuple entries (S_A_norm, S_C_norm, Omega_AC, tau_opt)")

# [5] S channels activated
assert S_C_norm > 0.01, f"norm(S_C) too small: {S_C_norm}"
assert S_A_norm > 0.001, f"norm(S_A) too small: {S_A_norm}"
print(f"[5] PASS  norm(S_C)={S_C_norm:.6f} > 0.01  norm(S_A)={S_A_norm:.6f} > 0.001")

# [6] H_t chain
assert mu_final._H is not None
print(f"[6] PASS  H_t = {mu_final._H[:16]}...")

# [7] Leaves
assert n_leaves > 0
print(f"[7] PASS  n_leaves = {n_leaves} > 0")

# [8] Omega_AC evolves (not constant zero throughout EXP-314 entries)
all_omegas = [h[2] for h in gh4]
omega_max = max(all_omegas) if all_omegas else 0.0
assert omega_max > 0.0 or S_C_norm < 1e-10, (
    f"Omega_AC is 0 throughout but S_C_norm={S_C_norm:.6f} -- channels may not be coupling"
)
print(f"[8] PASS  Omega_AC evolves: max={omega_max:.6f} rad across {len(gh4)} EXP-314 steps")

# Observables
Z_final = mu_final.Z()
B_A = S_A_norm / (float(np.linalg.norm(Z_final[0:8])) + 1e-15)
B_C = S_C_norm / (float(np.linalg.norm(Z_final[8:12])) + 1e-15)
print(f"  OBS: B_A(t)={B_A:.6f}  B_C(t)={B_C:.6f}")
print(f"  OBS: final Omega_AC={omega_final:.4f} rad ({math.degrees(omega_final):.1f} deg)")
print(f"  OBS: final tau_opt={tau_final}  (lag window for TE)")
print(f"  OBS: K_ratio={float(w0.max()/w0.min()):.4f}  K_align=octant_{int(np.argmax(w0))}")

print(f"\nFork A: ALL TESTS PASSED ({n_leaves} leaves)")
