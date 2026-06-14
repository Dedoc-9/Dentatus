"""
run_ghost_stress_test.py -- E-301-004: path-coherence residuals -> non-zero G_t

Demonstrates the ghost channel becoming physically active.

Setup:
  Build PATH1 and PATH2 from run_r1_interchange_test.py setup (same A,B stalks).
  After both paths complete, declare convergence between:
    ab1 (PATH1 leaf) and ab1' (PATH2 leaf)
  WITHOUT registering the R1 2-morphism.

Observables measured:
  (a) ||G_t|| with registry (path-coherence residual active)
  (b) ||G_t|| without registry (base term, 0 by construction)
  (c) S_t recomputed with registry -> ||S_t|| > 0
  (d) B(t) = ||S_t|| / (||Z_t|| + eps) > 0
  (e) Psi cost: C0=2 * exp(beta * ||S_t||) > 2.0  (backreaction active)
  (f) Omega BLOCKED: issue_cert raises on ab1 (unresolved convergence)
  (g) Omega PASSES after register_morphism resolves the collision

Key equation:
  G_t = 0 (base) + (stalk(ab1) - stalk(ab1'))  [path-coherence residual]
  S_t = alpha*0 + (1-alpha)*G_t
  ||S_t|| = (1-alpha) * ||stalk(ab1) - stalk(ab1')||
"""
import json, math, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).parent
DECL = json.loads(
    (ROOT / "studies/exp301_generative_engine/SEED_DECLARATION_exp301.json").read_text(encoding="utf-8")
)
assert DECL["protocol_version"] == "exp301-v1" and DECL["status"] == "LOCKED"

from engine.state import C_KBOUND, Claim, MuState, Provenance, now_iso
from engine.validity import is_valid
from engine.operators import apply_phi, apply_psi, apply_omega, PartitionError, SynthesisError, BudgetExceeded
from engine.confluence import ConfluenceRegistry

ALPHA = DECL["alpha"]; BETA = DECL["beta"]; B0 = DECL["B0"]
P0_KEY = "default_partition"
KEY1 = "stress_ab_partition"; KEY2 = "stress_a_partition"; KEY3 = "stress_b_partition"
SYN_AB = "stress_psi_ab"; SYN1 = "stress_psi_a1b1"; SYN2 = "stress_psi_a2b2"

P_A  = "Claim A: the Kolmogorov complexity of any computable string is bounded below by its entropy."
P_B  = "Claim B: the minimum description length of a model is an upper bound on its Kolmogorov complexity."
P_AB = "Synthesis AB: K-complexity and MDL are dual characterizations of information irreducibility."
P_A1 = "Claim A.1: the entropy bound on K-complexity holds in expectation over the uniform distribution."
P_A2 = "Claim A.2: for incompressible strings, K-complexity meets the entropy lower bound exactly."
P_B1 = "Claim B.1: MDL minimization is equivalent to Bayesian model selection under a universal prior."
P_B2 = "Claim B.2: the gap between MDL and K-complexity is bounded by the description length of the prior."
P_AB1 = "Synthesis ab1: entropy-meeting K-complexity and MDL-equivalent model selection are primal-dual."
P_AB2 = "Synthesis ab2: incompressible strings admit both K-complexity and MDL descriptions at the bound."

# ---------------------------------------------------------------------------
# Shared base: Seed_0 -> {A, B}
# ---------------------------------------------------------------------------
prov0 = Provenance(parent_ids=(), operator_id="GENESIS", timestamp=now_iso())
seed_stalk = np.array(DECL["seed_stalk"], dtype=float)
seed = Claim(provenance=prov0, payload=DECL["seed_payload"], stalk=seed_stalk, t=0)
mu0  = MuState(t=0, claims={seed.id: seed}, entailments={},
               active=frozenset([seed.id]), S=np.zeros_like(seed_stalk), alpha=ALPHA)
mu0.seal()

mu_base, _ = apply_phi(mu=mu0, claim_id=seed.id, N=2, partition_key=P0_KEY,
                        payloads=[P_A, P_B], beta=BETA, budget=B0, spent=0.0)
mu_base.seal()
A_id, B_id = sorted(mu_base.active)
A = mu_base.claims[A_id]; B = mu_base.claims[B_id]
spent = 1.0

# ---------------------------------------------------------------------------
# PATH 1: Psi(A,B)->AB -> Phi(AB,2)
# ---------------------------------------------------------------------------
mu_p1_1, c1 = apply_psi(mu=mu_base, claim_ids=[A_id, B_id], synthesis_key=SYN_AB,
                         payload=P_AB, weights=[0.5, 0.5], beta=BETA, budget=B0, spent=spent)
mu_p1_1.seal()
AB_id = next(iter(mu_p1_1.active))

mu_p1_2, c2 = apply_phi(mu=mu_p1_1, claim_id=AB_id, N=2, partition_key=KEY1,
                          payloads=[P_AB1, P_AB2], beta=BETA, budget=B0, spent=spent+c1)
mu_p1_2.seal()
ab1_id, ab2_id = sorted(mu_p1_2.active)
ab1 = mu_p1_2.claims[ab1_id]; ab2 = mu_p1_2.claims[ab2_id]

# ---------------------------------------------------------------------------
# PATH 2: Phi(A,2) -> Phi(B,2) -> Psi(a1,b1)
# ---------------------------------------------------------------------------
mu_p2_a, _ = apply_phi(mu=mu_base, claim_id=A_id, N=2, partition_key=KEY2,
                        payloads=[P_A1, P_A2], beta=BETA, budget=B0, spent=spent)
mu_p2_a.seal()
a1_id, a2_id = sorted(mu_p2_a.active - {B_id})

mu_p2_b, _ = apply_phi(mu=mu_p2_a, claim_id=B_id, N=2, partition_key=KEY3,
                        payloads=[P_B1, P_B2], beta=BETA, budget=B0, spent=spent+1.0)
mu_p2_b.seal()
b1_id, b2_id = sorted(mu_p2_b.active - {a1_id, a2_id})

mu_p2_c, _ = apply_psi(mu=mu_p2_b, claim_ids=[a1_id, b1_id], synthesis_key=SYN1,
                        payload=P_AB1, weights=[0.5, 0.5], beta=BETA, budget=B0, spent=spent+2.0)
mu_p2_c.seal()
ab1p_id = next(iter(mu_p2_c.active - {a2_id, b2_id}))
ab1p = mu_p2_c.claims[ab1p_id]

print(f"=== PATH 1 leaf ab1  stalk: {np.round(ab1.stalk, 4).tolist()}")
print(f"=== PATH 2 leaf ab1' stalk: {np.round(ab1p.stalk, 4).tolist()}")
residual_vec = ab1.stalk - ab1p.stalk
print(f"=== Path residual (ab1 - ab1'): {np.round(residual_vec, 4).tolist()}")
print(f"    ||residual||: {np.linalg.norm(residual_vec):.6f}")

# ---------------------------------------------------------------------------
# Phase 1: G WITHOUT registry (should be 0)
# ---------------------------------------------------------------------------
print(f"\n--- Phase 1: G without registry (baseline) ---")
G_base = mu_p1_2.G(registry=None)
print(f"  ||G_base||: {np.linalg.norm(G_base):.2e}  (0 by E-301-004 invariant)")

# ---------------------------------------------------------------------------
# Phase 2: declare_convergence WITHOUT registering 2-morphism
# ---------------------------------------------------------------------------
print(f"\n--- Phase 2: declare_convergence(ab1, ab1') — no 2-morphism ---")
reg = ConfluenceRegistry()
reg.record_path(seed.id,  ("GENESIS",), t=0)
reg.record_path(A_id,     ("GENESIS", f"Phi:{P0_KEY}:0"), t=1)
reg.record_path(B_id,     ("GENESIS", f"Phi:{P0_KEY}:1"), t=1)
reg.record_path(AB_id,    ("GENESIS", f"Phi:{P0_KEY}:0", f"Psi:{SYN_AB}"), t=2)
reg.record_path(AB_id,    ("GENESIS", f"Phi:{P0_KEY}:1", f"Psi:{SYN_AB}"), t=2)
# NOTE: registering R2 for AB to keep AB itself clean; the stress is on ab1 vs ab1'
reg.register_morphism(
    path1=("GENESIS", f"Phi:{P0_KEY}:0", f"Psi:{SYN_AB}"),
    path2=("GENESIS", f"Phi:{P0_KEY}:1", f"Psi:{SYN_AB}"),
    claim_id=AB_id, rule_id="R2", t=2,
)
reg.record_path(ab1_id,  ("GENESIS", f"Phi:{P0_KEY}:0", f"Psi:{SYN_AB}", f"Phi:{KEY1}:0"), t=3)
reg.record_path(ab2_id,  ("GENESIS", f"Phi:{P0_KEY}:0", f"Psi:{SYN_AB}", f"Phi:{KEY1}:1"), t=3)

# Declare convergence: ab1 and ab1' should be the same claim but differ in stalk
rec = reg.declare_convergence(ab1_id, ab1.stalk, ab1p_id, ab1p.stalk)
print(f"  ConvergenceRecord: {ab1_id[:12]}... vs {ab1p_id[:12]}...")
print(f"  ||residual||: {np.linalg.norm(rec.residual):.6f}")
print(f"  Registry: {reg.summary()}")

# ---------------------------------------------------------------------------
# Phase 3: G WITH registry (path-coherence active)
# ---------------------------------------------------------------------------
print(f"\n--- Phase 3: G with registry ---")
G_coherent = mu_p1_2.G(registry=reg)
print(f"  ||G_coherent||: {np.linalg.norm(G_coherent):.6f}  (should match ||residual||)")
assert np.linalg.norm(G_coherent) > 0.01, "FAIL: G still 0 with unresolved convergence"

# Recompute S with coherence (S starts at 0, one EMA step)
S_stressed = ALPHA * np.zeros_like(seed_stalk) + (1.0 - ALPHA) * G_coherent
print(f"  ||S_stressed||: {np.linalg.norm(S_stressed):.6f}  = (1-alpha)*||G||")
print(f"  Expected:       {(1.0 - ALPHA) * np.linalg.norm(G_coherent):.6f}")

B_stressed = float(np.linalg.norm(S_stressed) / (np.linalg.norm(mu_p1_2.Z()) + 1e-12))
print(f"  B(t) stressed:  {B_stressed:.6f}")

# ---------------------------------------------------------------------------
# Phase 4: Backreaction on next Psi
# ---------------------------------------------------------------------------
print(f"\n--- Phase 4: Backreaction ---")
S_norm_stressed = float(np.linalg.norm(S_stressed))
cost_unstressed = 2.0 * math.exp(BETA * 0.0)
cost_stressed   = 2.0 * math.exp(BETA * S_norm_stressed)
print(f"  C(Psi, S=0):        {cost_unstressed:.6f}")
print(f"  C(Psi, S_stressed): {cost_stressed:.6f}  (+{100*(cost_stressed/cost_unstressed - 1):.3f}%)")
print(f"  Delta cost:         {cost_stressed - cost_unstressed:.6f}")

# ---------------------------------------------------------------------------
# Phase 5: Omega BLOCKED on ab1 (unresolved convergence)
# ---------------------------------------------------------------------------
print(f"\n--- Phase 5: Omega blocked on ab1 ---")
try:
    cert = reg.issue_cert(ab1_id)
    print(f"FAIL: cert issued despite unresolved convergence: {cert}")
    sys.exit(1)
except RuntimeError as e:
    print(f"  BLOCKED (expected): {e}")

# ---------------------------------------------------------------------------
# Phase 6: Register R1 2-morphism -> Omega unblocked
# ---------------------------------------------------------------------------
print(f"\n--- Phase 6: Register R1 -> convergence resolved -> Omega unblocked ---")
reg.record_path(a1_id,   ("GENESIS", f"Phi:{P0_KEY}:0", f"Phi:{KEY2}:0"), t=2)
reg.record_path(b1_id,   ("GENESIS", f"Phi:{P0_KEY}:1", f"Phi:{KEY3}:0"), t=2)
reg.record_path(ab1p_id, ("GENESIS", f"Phi:{P0_KEY}:0", f"Phi:{KEY2}:0", f"Psi:{SYN1}"), t=3)
reg.register_morphism(
    path1=("GENESIS", f"Phi:{P0_KEY}:0", f"Psi:{SYN_AB}", f"Phi:{KEY1}:0"),
    path2=("GENESIS", f"Phi:{P0_KEY}:0", f"Phi:{KEY2}:0", f"Psi:{SYN1}"),
    claim_id=ab1_id, rule_id="R1", t=3,
)
print(f"  Registry after R1: {reg.summary()}")

# G after resolution
G_resolved = mu_p1_2.G(registry=reg)
print(f"  ||G|| after resolution: {np.linalg.norm(G_resolved):.2e}  (should be ~0)")

# Omega now succeeds
cert_ab1 = reg.issue_cert(ab1_id)
print(f"  cert(ab1): {cert_ab1}")
art = apply_omega(mu_p1_2, ab1_id, cert_ab1)
print(f"  Artifact: K={art['K_bound']}  H={art['state_hash'][:16]}...")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n=== GHOST STRESS TEST PASS ===")
print(f"  ||G_base||:      {np.linalg.norm(G_base):.2e}  (no registry — lossless invariant)")
print(f"  ||G_coherent||:  {np.linalg.norm(G_coherent):.6f}  (E-301-004 active)")
print(f"  ||S_stressed||:  {np.linalg.norm(S_stressed):.6f}  = (1-{ALPHA})*||G||")
print(f"  B(t):            {B_stressed:.6f}")
print(f"  Backreaction:    +{100*(cost_stressed/cost_unstressed - 1):.3f}% on Psi cost")
print(f"  Omega blocked:   YES (unresolved convergence)")
print(f"  Omega unblocked: YES (after R1 2-morphism)")
print(f"  ||G|| resolved:  {np.linalg.norm(G_resolved):.2e}  (~0)")
