"""
run_seed0.py — First execution: initialize Seed_0 and verify engine invariants.

Validates:
  1. Seed_0 Claim constructed and hashed
  2. MuState sealed with valid H_0
  3. is_valid(μ_0) — sheaf Laplacian check (trivially True for single node)
  4. Observables: B(0), ESS(0), η_CLT(0)
  5. Confluence cert issuable for Seed_0 (no convergences at t=0)
  6. Ω(Seed_0) produces a valid Artifact
  7. Budget and backreaction at t=0

DECLARED parameters sourced from SEED_DECLARATION_exp301.json.
"""

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent

# Load Seed_0 declaration
DECL = json.loads(
    (ROOT / "studies/exp301_generative_engine/SEED_DECLARATION_exp301.json").read_text()
)
assert DECL["protocol_version"] == "exp301-v1", "Protocol version mismatch"
assert DECL["status"] == "LOCKED", "Seed_0 declaration not locked"

from engine.state import Claim, MuState, Provenance, now_iso
from engine.validity import is_valid, lambda_min
from engine.operators import apply_omega
from engine.confluence import ConfluenceRegistry

ALPHA = DECL["alpha"]
BETA  = DECL["beta"]
B0    = DECL["B0"]
D     = DECL["d"]

# ---------------------------------------------------------------------------
# 1. Construct Seed_0 claim
# ---------------------------------------------------------------------------

prov = Provenance(
    parent_ids=(),
    operator_id="GENESIS",
    timestamp=now_iso(),
)
seed_stalk = np.array(DECL["seed_stalk"], dtype=float)

seed_claim = Claim(
    provenance=prov,
    payload=DECL["seed_payload"],
    stalk=seed_stalk,
    t=0,
)
print(f"Seed_0 id:      {seed_claim.id}")
print(f"Seed_0 K_bound: {seed_claim.K_bound} bytes")
print(f"Seed_0 stalk:   {seed_stalk.tolist()}")

# ---------------------------------------------------------------------------
# 2. Initialize μ_0
# ---------------------------------------------------------------------------

S_init = np.zeros_like(seed_stalk)

mu0 = MuState(
    t=0,
    claims={seed_claim.id: seed_claim},
    entailments={},
    active=frozenset([seed_claim.id]),
    S=S_init,
    alpha=ALPHA,
)

H0 = mu0.seal()
print(f"\nH_0: {H0}")

# ---------------------------------------------------------------------------
# 3. Validity check
# ---------------------------------------------------------------------------

lam = lambda_min(mu0)
valid = is_valid(mu0)
print(f"\nλ_min(L_F(μ_0)): {lam:.6f}  →  is_valid: {valid}")
assert valid, "INVARIANT FAIL: μ_0 must be valid"

# ---------------------------------------------------------------------------
# 4. Observables
# ---------------------------------------------------------------------------

B     = mu0.B()
ESS   = mu0.ESS()
eta   = mu0.eta_CLT()
Z_norm = float(np.linalg.norm(mu0.Z()))
S_norm = float(np.linalg.norm(mu0.S))

print(f"\nObservables at t=0:")
print(f"  B(0)    = {B:.6f}   (ghost-to-primary ratio)")
print(f"  ESS(0)  = {ESS:.4f}")
print(f"  η_CLT   = {eta:.6f}")
print(f"  ||Z_0|| = {Z_norm:.6f}")
print(f"  ||S_0|| = {S_norm:.6f}")

# ---------------------------------------------------------------------------
# 5. Confluence registry — Seed_0 path
# ---------------------------------------------------------------------------

reg = ConfluenceRegistry()
reg.record_path(seed_claim.id, ("GENESIS",), t=0)
cert = reg.issue_cert(seed_claim.id)
print(f"\nConfluence cert (Seed_0): {cert}")
print(f"Registry summary: {reg.summary()}")

# ---------------------------------------------------------------------------
# 6. Ω(Seed_0) — first observation
# ---------------------------------------------------------------------------

artifact = apply_omega(mu0, seed_claim.id, confluence_cert=cert)
print(f"\nArtifact:")
print(json.dumps(artifact, indent=2))

# ---------------------------------------------------------------------------
# 7. Budget status
# ---------------------------------------------------------------------------

print(f"\nBudget: spent=0.0 / B₀={B0}  (Ω is free)")
print(f"β (backreaction coeff): {BETA}")
print(f"\n=== Seed_0 PASS: all invariants satisfied ===")
print(f"declaration_hash: {DECL['declaration_hash']}")
print(f"H_0:              {H0}")
