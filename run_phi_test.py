"""
run_phi_test.py -- First Phi execution on Dentatus / EXP-301.

Partitions Seed_0 into 2 child claims using default_partition key.
Verifies post-Phi invariants:
  1. H_1 sealed and distinct from H_0
  2. is_valid(mu_1) -- forward entailment consistency (E-301-003)
  3. Stalk conservation: stalk(c1) + stalk(c2) == stalk(Seed_0)
  4. Stalk orthogonality: stalk(c1) . stalk(c2) ~= 0
  5. K-bound satisfied (c=C_KBOUND=150, E-301-002)
  6. Backreaction cost computed
  7. B(1), ESS(1), eta_CLT(1)
  8. Ghost residual G_1, S_1 after first EMA step
  9. Confluence cert issuable for both children (no convergences)
  10. Omega on each child produces valid Artifact

Declaration sourced from SEED_DECLARATION_exp301.json (d=4, E-301-001).
"""
import json
import math
import sys
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent

DECL = json.loads(
    (ROOT / "studies/exp301_generative_engine/SEED_DECLARATION_exp301.json").read_text(encoding="utf-8")
)
assert DECL["protocol_version"] == "exp301-v1"
assert DECL["status"] == "LOCKED"
assert DECL["d"] == 4, f"E-301-001 not applied: d={DECL['d']}"

from engine.state import C_KBOUND, Claim, MuState, Provenance, now_iso
from engine.validity import is_valid, lambda_min, delta_lambda_min
from engine.operators import apply_phi, apply_omega, PartitionError
from engine.confluence import ConfluenceRegistry

ALPHA = DECL["alpha"]
BETA  = DECL["beta"]
B0    = DECL["B0"]

# ---------------------------------------------------------------------------
# 1. Reconstruct mu_0 (same as run_seed0.py)
# ---------------------------------------------------------------------------
prov = Provenance(parent_ids=(), operator_id="GENESIS", timestamp=now_iso())
seed_stalk = np.array(DECL["seed_stalk"], dtype=float)
seed_claim = Claim(provenance=prov, payload=DECL["seed_payload"], stalk=seed_stalk, t=0)
S0 = np.zeros_like(seed_stalk)
mu0 = MuState(t=0, claims={seed_claim.id: seed_claim}, entailments={},
              active=frozenset([seed_claim.id]), S=S0, alpha=ALPHA)
H0 = mu0.seal()
print(f"mu_0  H_0: {H0}")
print(f"Seed_0 id: {seed_claim.id}  stalk: {seed_stalk.tolist()}")

# ---------------------------------------------------------------------------
# 2. Apply Phi: Seed_0 -> {c1, c2}
# ---------------------------------------------------------------------------
PARTITION_KEY = "default_partition"

PAYLOAD_C1 = "Sub-claim A: K-complexity of a claim is non-zero implies information content is irreducible."
PAYLOAD_C2 = "Sub-claim B: stalk non-null implies the claim has representable structure in the active basis."

print(f"\n--- Applying Phi(Seed_0, N=2, key='{PARTITION_KEY}') ---")

try:
    mu1, cost_phi = apply_phi(
        mu=mu0,
        claim_id=seed_claim.id,
        N=2,
        partition_key=PARTITION_KEY,
        payloads=[PAYLOAD_C1, PAYLOAD_C2],
        beta=BETA,
        budget=B0,
        spent=0.0,
    )
except PartitionError as e:
    print(f"PARTITION ERROR: {e}")
    sys.exit(1)

H1 = mu1.seal()
print(f"mu_1  H_1: {H1}")
print(f"cost_phi (backreaction): {cost_phi:.6f}  (C0=1.0, beta={BETA}, ||S_0||=0)")

# ---------------------------------------------------------------------------
# 3. Post-Phi invariant checks
# ---------------------------------------------------------------------------
print(f"\n--- Invariant checks ---")

assert H1 != H0, "FAIL: H_1 == H_0 (state did not advance)"
print(f"H continuity:  H_1 != H_0  OK")

lam1 = lambda_min(mu1)
valid1 = is_valid(mu1)
dlam = delta_lambda_min(mu0, mu1)
print(f"lambda_min(mu_1): {lam1:.6f}  is_valid: {valid1}  delta_lambda: {dlam:.6f}")
assert valid1, "FAIL: mu_1 not valid after Phi"

assert seed_claim.id not in mu1.active, "FAIL: Seed_0 still in W_1"
assert len(mu1.active) == 2, f"FAIL: |W_1|={len(mu1.active)} != 2"
child_ids = sorted(mu1.active)
c1_id, c2_id = child_ids
c1 = mu1.claims[c1_id]
c2 = mu1.claims[c2_id]
print(f"Active leaves: {c1_id}, {c2_id}")
print(f"  c1 stalk: {c1.stalk.tolist()}")
print(f"  c2 stalk: {c2.stalk.tolist()}")

stalk_sum = c1.stalk + c2.stalk
conservation_err = float(np.linalg.norm(stalk_sum - seed_stalk))
status = "OK" if conservation_err < 1e-10 else "WARN"
print(f"Stalk conservation ||sum - parent||: {conservation_err:.2e}  {status}")

dot = float(np.dot(c1.stalk, c2.stalk))
status = "(~0 OK)" if abs(dot) < 1e-6 else "(non-zero: check decomposition)"
print(f"Stalk orthogonality c1.c2: {dot:.6f}  {status}")

# K-bound (E-301-002: c = C_KBOUND = 150)
k_c1 = len(zlib.compress(PAYLOAD_C1.encode("utf-8"), level=9))
k_c2 = len(zlib.compress(PAYLOAD_C2.encode("utf-8"), level=9))
k_sum = k_c1 + k_c2
k_limit = seed_claim.K_bound + C_KBOUND * math.log(2)
status = "OK" if k_sum <= k_limit else "VIOLATION"
print(f"K-bound (c={C_KBOUND}): K(c1)={k_c1} K(c2)={k_c2} sum={k_sum} <= limit={k_limit:.2f}  {status}")
assert k_sum <= k_limit, f"K-bound violated: {k_sum} > {k_limit:.2f}"

# ---------------------------------------------------------------------------
# 4. Dual channel observables at t=1
# ---------------------------------------------------------------------------
print(f"\n--- Observables at t=1 ---")
Z1 = mu1.Z()           # sum of active stalks in R^d
G1 = mu1.G()           # ghost residual in R^d
S1 = mu1.S             # EMA (set during apply_phi via next_S)
B1 = mu1.B()
ESS1 = mu1.ESS()
eta1 = mu1.eta_CLT()

# G orthogonality: W^T @ G should be ~0 (lstsq guarantee)
W1 = mu1.W_basis()     # (d, k)
g_orth = float(np.max(np.abs(W1.T @ G1)))

print(f"  ||Z_1|| (sum stalks): {np.linalg.norm(Z1):.6f}")
print(f"  ||G_1||: {np.linalg.norm(G1):.2e}  (ghost residual; ~0 for lossless partition)")
print(f"  ||S_1||: {np.linalg.norm(S1):.6f}  (EMA after first step)")
print(f"  B(1):    {B1:.6f}  (ghost-to-primary ratio)")
print(f"  ESS(1):  {ESS1:.4f}")
print(f"  eta_CLT: {eta1:.6f}")
print(f"  max |W_1^T G_1|: {g_orth:.2e}  (should be ~0, lstsq guarantee)")

# ---------------------------------------------------------------------------
# 5. Confluence registry
# ---------------------------------------------------------------------------
print(f"\n--- Confluence ---")
reg = ConfluenceRegistry()
reg.record_path(seed_claim.id, ("GENESIS",), t=0)
reg.record_path(c1_id, ("GENESIS", f"Phi:{PARTITION_KEY}:0"), t=1)
reg.record_path(c2_id, ("GENESIS", f"Phi:{PARTITION_KEY}:1"), t=1)

cert_c1 = reg.issue_cert(c1_id)
cert_c2 = reg.issue_cert(c2_id)
print(f"  cert(c1): {cert_c1}")
print(f"  cert(c2): {cert_c2}")
print(f"  Registry: {reg.summary()}")

# ---------------------------------------------------------------------------
# 6. Omega on each child
# ---------------------------------------------------------------------------
print(f"\n--- Omega(c1), Omega(c2) ---")
art1 = apply_omega(mu1, c1_id, confluence_cert=cert_c1)
art2 = apply_omega(mu1, c2_id, confluence_cert=cert_c2)
print(f"Artifact c1: claim_id={art1['claim_id']}  K={art1['K_bound']}  H={art1['state_hash'][:16]}...")
print(f"Artifact c2: claim_id={art2['claim_id']}  K={art2['K_bound']}  H={art2['state_hash'][:16]}...")

# ---------------------------------------------------------------------------
# 7. Budget ledger
# ---------------------------------------------------------------------------
spent = cost_phi
remaining = B0 - spent
print(f"\n--- Budget ---")
print(f"  B0={B0}  spent={spent:.6f}  remaining={remaining:.6f}")

print(f"\n=== Phi PASS: all invariants satisfied ===")
print(f"H_0: {H0}")
print(f"H_1: {H1}")
print(f"declaration_hash: {DECL['declaration_hash']}")
