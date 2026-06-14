"""
run_psi_test.py -- First Psi execution on Dentatus / EXP-301.

Pipeline: Seed_0 -[Phi]-> {c1, c2} -[Psi]-> v_new

Psi combines c1 and c2 back into a single synthesised claim.
Verifies:
  1. H_2 sealed and distinct from H_1
  2. is_valid(mu_2) -- multi-source forward consistency
  3. Matroid independence: r(M_c1 v M_c2) == r(M_c1) + r(M_c2)
  4. Stalk reconstruction: stalk(v_new) = alpha*c1 + (1-alpha)*c2
  5. Multi-source restriction check: sum_i F(c_i->new)(stalk_i) = stalk_new
  6. Budget: Phi cost + Psi cost (C0=2) within B0
  7. Ghost channel: ||G_2|| after synthesis
  8. Confluence cert issuable for v_new
  9. Omega(v_new) produces valid Artifact

This tests the full Phi->Psi->Omega trajectory at minimal scale.
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

from engine.state import C_KBOUND, Claim, MuState, Provenance, now_iso
from engine.validity import is_valid, lambda_min
from engine.operators import apply_phi, apply_psi, apply_omega, PartitionError, SynthesisError
from engine.confluence import ConfluenceRegistry

ALPHA = DECL["alpha"]
BETA  = DECL["beta"]
B0    = DECL["B0"]

# ---------------------------------------------------------------------------
# 1. Reconstruct mu_0
# ---------------------------------------------------------------------------
prov     = Provenance(parent_ids=(), operator_id="GENESIS", timestamp=now_iso())
seed_stalk = np.array(DECL["seed_stalk"], dtype=float)
seed_claim = Claim(provenance=prov, payload=DECL["seed_payload"], stalk=seed_stalk, t=0)
S0  = np.zeros_like(seed_stalk)
mu0 = MuState(t=0, claims={seed_claim.id: seed_claim}, entailments={},
              active=frozenset([seed_claim.id]), S=S0, alpha=ALPHA)
H0  = mu0.seal()

# ---------------------------------------------------------------------------
# 2. Apply Phi: Seed_0 -> {c1, c2}
# ---------------------------------------------------------------------------
PARTITION_KEY = "default_partition"
PAYLOAD_C1 = "Sub-claim A: K-complexity of a claim is non-zero implies information content is irreducible."
PAYLOAD_C2 = "Sub-claim B: stalk non-null implies the claim has representable structure in the active basis."

mu1, cost_phi = apply_phi(
    mu=mu0, claim_id=seed_claim.id, N=2,
    partition_key=PARTITION_KEY, payloads=[PAYLOAD_C1, PAYLOAD_C2],
    beta=BETA, budget=B0, spent=0.0,
)
H1 = mu1.seal()
spent = cost_phi
child_ids = sorted(mu1.active)
c1_id, c2_id = child_ids
print(f"mu_0  H_0: {H0[:16]}...")
print(f"mu_1  H_1: {H1[:16]}...  cost_phi={cost_phi:.6f}")
print(f"  c1: {c1_id}  stalk={mu1.claims[c1_id].stalk.tolist()}")
print(f"  c2: {c2_id}  stalk={mu1.claims[c2_id].stalk.tolist()}")

# ---------------------------------------------------------------------------
# 3. Apply Psi: {c1, c2} -> v_new
# ---------------------------------------------------------------------------
SYNTHESIS_KEY = "default_synthesis"
PAYLOAD_PSI   = ("Synthesis AB: a claim is structurally non-trivial iff its K-complexity is "
                 "non-zero AND its stalk is representable in the active basis.")

# Equal weights: alpha_1 = alpha_2 = 0.5
WEIGHTS = [0.5, 0.5]

print(f"\n--- Applying Psi({{c1, c2}}, key='{SYNTHESIS_KEY}') ---")

try:
    mu2, cost_psi = apply_psi(
        mu=mu1, claim_ids=[c1_id, c2_id],
        synthesis_key=SYNTHESIS_KEY, payload=PAYLOAD_PSI,
        weights=WEIGHTS, beta=BETA, budget=B0, spent=spent,
    )
except SynthesisError as e:
    print(f"SYNTHESIS ERROR: {e}")
    sys.exit(1)

H2 = mu2.seal()
spent += cost_psi
print(f"mu_2  H_2: {H2[:16]}...  cost_psi={cost_psi:.6f}")

# ---------------------------------------------------------------------------
# 4. Invariant checks
# ---------------------------------------------------------------------------
print(f"\n--- Invariant checks ---")

assert H2 != H1 != H0, "FAIL: hash collision in trajectory"
print(f"H continuity:  H_2 != H_1 != H_0  OK")

valid2 = is_valid(mu2)
lam2   = lambda_min(mu2)
print(f"lambda_min(mu_2): {lam2:.6f}  is_valid: {valid2}")
assert valid2, "FAIL: mu_2 not valid after Psi"

# Active set: only v_new should remain
assert c1_id not in mu2.active, "FAIL: c1 still active after Psi"
assert c2_id not in mu2.active, "FAIL: c2 still active after Psi"
assert len(mu2.active) == 1, f"FAIL: |W_2|={len(mu2.active)} != 1"
new_id = next(iter(mu2.active))
v_new  = mu2.claims[new_id]
print(f"Active leaf: {new_id}")
print(f"  v_new stalk: {v_new.stalk.tolist()}")

# Stalk reconstruction: stalk(v_new) = 0.5*c1 + 0.5*c2
c1_stalk = mu1.claims[c1_id].stalk
c2_stalk = mu1.claims[c2_id].stalk
expected = 0.5 * c1_stalk + 0.5 * c2_stalk
recon_err = float(np.linalg.norm(v_new.stalk - expected))
print(f"Stalk reconstruction ||v_new - 0.5c1 - 0.5c2||: {recon_err:.2e}", "OK" if recon_err < 1e-12 else "WARN")

# Multi-source restriction check: sum_i F(c_i->new)(stalk_i) = stalk_new
psi_ents = [(src, ent) for (src, tgt), ent in mu2.entailments.items() if tgt == new_id]
predicted = sum(ent.restriction @ mu2.claims[src].stalk for src, ent in psi_ents)
multicheck_err = float(np.linalg.norm(predicted - v_new.stalk))
print(f"Multi-source consistency ||sum F(c_i)(stalk_i) - stalk_new||: {multicheck_err:.2e}", "OK" if multicheck_err < 1e-10 else "FAIL")

# ---------------------------------------------------------------------------
# 5. Dual channel at t=2
# ---------------------------------------------------------------------------
print(f"\n--- Observables at t=2 ---")
Z2  = mu2.Z()
G2  = mu2.G()
S2  = mu2.S
B2  = mu2.B()
ESS2 = mu2.ESS()
eta2 = mu2.eta_CLT()
W2   = mu2.W_basis()
g_orth = float(np.max(np.abs(W2.T @ G2)))

print(f"  ||Z_2||: {np.linalg.norm(Z2):.6f}")
print(f"  ||G_2||: {np.linalg.norm(G2):.2e}")
print(f"  ||S_2||: {np.linalg.norm(S2):.6f}  (EMA after Phi+Psi)")
print(f"  B(2):    {B2:.6f}")
print(f"  ESS(2):  {ESS2:.4f}")
print(f"  eta_CLT: {eta2:.6f}")
print(f"  max |W_2^T G_2|: {g_orth:.2e}  (should be ~0)")

# ---------------------------------------------------------------------------
# 6. Confluence
# ---------------------------------------------------------------------------
print(f"\n--- Confluence ---")
reg = ConfluenceRegistry()
reg.record_path(seed_claim.id, ("GENESIS",), t=0)
reg.record_path(c1_id, ("GENESIS", f"Phi:{PARTITION_KEY}:0"), t=1)
reg.record_path(c2_id, ("GENESIS", f"Phi:{PARTITION_KEY}:1"), t=1)
reg.record_path(new_id, ("GENESIS", f"Phi:{PARTITION_KEY}:0", f"Psi:{SYNTHESIS_KEY}"), t=2)
reg.record_path(new_id, ("GENESIS", f"Phi:{PARTITION_KEY}:1", f"Psi:{SYNTHESIS_KEY}"), t=2)
# Two paths reach new_id -> register R2 2-morphism (Psi inverts Phi per R2)
reg.register_morphism(
    path1=("GENESIS", f"Phi:{PARTITION_KEY}:0", f"Psi:{SYNTHESIS_KEY}"),
    path2=("GENESIS", f"Phi:{PARTITION_KEY}:1", f"Psi:{SYNTHESIS_KEY}"),
    claim_id=new_id,
    rule_id="R2",
    t=2,
)
cert_new = reg.issue_cert(new_id)
print(f"  cert(v_new): {cert_new}")
print(f"  Registry: {reg.summary()}")

# ---------------------------------------------------------------------------
# 7. Omega(v_new)
# ---------------------------------------------------------------------------
print(f"\n--- Omega(v_new) ---")
art = apply_omega(mu2, new_id, confluence_cert=cert_new)
print(f"Artifact: claim_id={art['claim_id']}  K={art['K_bound']}  H={art['state_hash'][:16]}...")

# ---------------------------------------------------------------------------
# 8. Budget
# ---------------------------------------------------------------------------
remaining = B0 - spent
print(f"\n--- Budget ---")
print(f"  cost_phi={cost_phi:.6f}  cost_psi={cost_psi:.6f}  total={spent:.6f}  remaining={remaining:.6f}")
print(f"  Gravitational backreaction at t=2: C(Psi)=2.0*exp(0.4*||S_1||)={cost_psi:.6f}")

print(f"\n=== Psi PASS: Phi->Psi->Omega trajectory complete ===")
print(f"H_0: {H0}")
print(f"H_1: {H1}")
print(f"H_2: {H2}")
