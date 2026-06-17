"""
run_trajectory_test.py -- Multi-step trajectory: Phi->Phi->Psi->Omega

Pipeline:
  t=0: Seed_0
  t=1: Phi(Seed_0, N=2)        -> {c1, c2}
  t=2: Phi(c1, N=2)            -> {c1a, c1b, c2}   (c2 remains active)
  t=3: Psi({c1a, c1b})         -> {v_AB, c2}        (re-synthesise c1's subtree)
  t=4: Omega(v_AB), Omega(c2)  -> 2 artifacts

Observes:
  - DAG depth (3 levels): subtree matroid at t=3 spans {c1a, c1b}
  - Ghost accumulation: S_t grows as G_t != 0 after second Phi
    (Z = sum(active stalks) changes structure; W basis shifts)
  - Backreaction: C(Psi, t=3) = k * exp(beta * ||S_2||)
    At t=2 S is still near zero (Phi is lossless), so effect is small here.
    But the trajectory structure is in place to test high-S regimes.
  - Budget ledger through 3 operators.
"""
import json, math, sys
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
spent = 0.0

def banner(label, mu, cost=None):
    H = mu._H if mu._sealed else "(unsealed)"
    Z = mu.Z(); G = mu.G(); S = mu.S
    extra = f"  cost={cost:.6f}" if cost is not None else ""
    print(f"\n[{label}] H={H[:16]}...{extra}")
    print(f"  |W|={len(mu.active)}  ||Z||={np.linalg.norm(Z):.4f}"
          f"  ||G||={np.linalg.norm(G):.2e}  ||S||={np.linalg.norm(S):.4f}"
          f"  B={mu.B():.4f}  ESS={mu.ESS():.3f}")
    for cid in sorted(mu.active):
        print(f"    {cid}: stalk={np.round(mu.claims[cid].stalk,4).tolist()}")

# ---------------------------------------------------------------------------
# t=0  Seed_0
# ---------------------------------------------------------------------------
prov = Provenance(parent_ids=(), operator_id="GENESIS", timestamp=now_iso())
seed_stalk = np.array(DECL["seed_stalk"], dtype=float)
seed = Claim(provenance=prov, payload=DECL["seed_payload"], stalk=seed_stalk, t=0)
mu0  = MuState(t=0, claims={seed.id: seed}, entailments={},
               active=frozenset([seed.id]), S=np.zeros_like(seed_stalk), alpha=ALPHA)
mu0.seal()
banner("t=0 Seed_0", mu0)
assert is_valid(mu0)

# ---------------------------------------------------------------------------
# t=1  Phi(Seed_0, N=2) -> {c1, c2}
# ---------------------------------------------------------------------------
P1_KEY = "default_partition"
P1_C1  = "Sub-claim A: K-complexity of a claim is non-zero implies information content is irreducible."
P1_C2  = "Sub-claim B: stalk non-null implies the claim has representable structure in the active basis."

mu1, c1_phi = apply_phi(mu=mu0, claim_id=seed.id, N=2, partition_key=P1_KEY,
                         payloads=[P1_C1, P1_C2], beta=BETA, budget=B0, spent=spent)
mu1.seal(); spent += c1_phi
banner("t=1 Phi(Seed_0)", mu1, c1_phi)
assert is_valid(mu1)

c1_id, c2_id = sorted(mu1.active)  # sorted by hash for determinism

# ---------------------------------------------------------------------------
# t=2  Phi(c1, N=2) -> {c1a, c1b}  (c2 unchanged)
# ---------------------------------------------------------------------------
P2_KEY = "partition_c1"
P2_C1A = "Sub-claim A.1: irreducibility of K-complexity holds at every recursive decomposition level."
P2_C1B = "Sub-claim A.2: the lower bound on K-complexity is determined by the minimal description length."

mu2, c2_phi = apply_phi(mu=mu1, claim_id=c1_id, N=2, partition_key=P2_KEY,
                         payloads=[P2_C1A, P2_C1B], beta=BETA, budget=B0, spent=spent)
mu2.seal(); spent += c2_phi
banner("t=2 Phi(c1)", mu2, c2_phi)
assert is_valid(mu2)

# c2 is still active; two new leaves are c1a, c1b
new_leaves = mu2.active - {c2_id}
assert len(new_leaves) == 2, f"Expected 2 new leaves, got {len(new_leaves)}"
c1a_id, c1b_id = sorted(new_leaves)

print(f"\n  S norm after 2nd Phi: ||S_2||={np.linalg.norm(mu2.S):.6f}")
print(f"  Backreaction at t=3 (Psi, k=2): C0=2 * exp({BETA}*||S_2||) = "
      f"{2.0 * math.exp(BETA * float(np.linalg.norm(mu2.S))):.6f}")

# ---------------------------------------------------------------------------
# t=3  Psi({c1a, c1b}) -> v_AB   (re-synthesise c1's partition)
# ---------------------------------------------------------------------------
SYN_KEY  = "resynthesis_c1"
SYN_PAY  = ("Synthesis A: K-complexity irreducibility holds at all decomposition levels "
            "with the minimal description length as the floor.")
WEIGHTS  = [0.5, 0.5]

try:
    mu3, c3_psi = apply_psi(mu=mu2, claim_ids=[c1a_id, c1b_id],
                             synthesis_key=SYN_KEY, payload=SYN_PAY,
                             weights=WEIGHTS, beta=BETA, budget=B0, spent=spent)
except SynthesisError as e:
    print(f"SYNTHESIS ERROR: {e}"); sys.exit(1)

mu3.seal(); spent += c3_psi
banner("t=3 Psi(c1a,c1b)", mu3, c3_psi)
assert is_valid(mu3)

v_AB_id = next(iter(mu3.active - {c2_id}))
v_AB    = mu3.claims[v_AB_id]

# Verify stalk: Psi(0.5*c1a + 0.5*c1b)
c1a_s = mu2.claims[c1a_id].stalk
c1b_s = mu2.claims[c1b_id].stalk
expected_vAB = 0.5*c1a_s + 0.5*c1b_s
err = float(np.linalg.norm(v_AB.stalk - expected_vAB))
print(f"\n  Psi stalk reconstruction err: {err:.2e}  {'OK' if err < 1e-12 else 'WARN'}")

# ---------------------------------------------------------------------------
# t=4  Omega on both active leaves
# ---------------------------------------------------------------------------
print(f"\n--- Confluence + Omega ---")
reg = ConfluenceRegistry()
reg.record_path(seed.id,  ("GENESIS",), t=0)
reg.record_path(c1_id,    ("GENESIS", f"Phi:{P1_KEY}:0"), t=1)
reg.record_path(c2_id,    ("GENESIS", f"Phi:{P1_KEY}:1"), t=1)
reg.record_path(c1a_id,   ("GENESIS", f"Phi:{P1_KEY}:0", f"Phi:{P2_KEY}:0"), t=2)
reg.record_path(c1b_id,   ("GENESIS", f"Phi:{P1_KEY}:0", f"Phi:{P2_KEY}:1"), t=2)
reg.record_path(v_AB_id,  ("GENESIS", f"Phi:{P1_KEY}:0", f"Phi:{P2_KEY}:0", f"Psi:{SYN_KEY}"), t=3)
reg.record_path(v_AB_id,  ("GENESIS", f"Phi:{P1_KEY}:0", f"Phi:{P2_KEY}:1", f"Psi:{SYN_KEY}"), t=3)
reg.register_morphism(
    path1=("GENESIS", f"Phi:{P1_KEY}:0", f"Phi:{P2_KEY}:0", f"Psi:{SYN_KEY}"),
    path2=("GENESIS", f"Phi:{P1_KEY}:0", f"Phi:{P2_KEY}:1", f"Psi:{SYN_KEY}"),
    claim_id=v_AB_id, rule_id="R2", t=3,
)

cert_AB = reg.issue_cert(v_AB_id)
cert_c2 = reg.issue_cert(c2_id)
print(f"  cert(v_AB): {cert_AB}")
print(f"  cert(c2):   {cert_c2}")
print(f"  Registry:   {reg.summary()}")

art_AB = apply_omega(mu3, v_AB_id, cert_AB)
art_c2 = apply_omega(mu3, c2_id,   cert_c2)
print(f"\n  Artifact v_AB: K={art_AB['K_bound']}  H={art_AB['state_hash'][:16]}...")
print(f"  Artifact c2:   K={art_c2['K_bound']}  H={art_c2['state_hash'][:16]}...")

# ---------------------------------------------------------------------------
# Budget summary
# ---------------------------------------------------------------------------
print(f"\n--- Budget ledger ---")
print(f"  Phi(Seed_0): {c1_phi:.4f}")
print(f"  Phi(c1):     {c2_phi:.4f}")
print(f"  Psi(c1a,c1b):{c3_psi:.4f}")
print(f"  Total spent: {spent:.4f} / B0={B0}  remaining={B0-spent:.4f}")

# ---------------------------------------------------------------------------
# Trajectory summary
# ---------------------------------------------------------------------------
print(f"\n=== Trajectory PASS ===")
print(f"  H_0={mu0._H[:16]}...")
print(f"  H_1={mu1._H[:16]}...")
print(f"  H_2={mu2._H[:16]}...")
print(f"  H_3={mu3._H[:16]}...")
print(f"  DAG: 1 -> 2 -> 3 -> 2 active  (depth=3, operators=3)")
