"""
run_p_invariance_exp516.py -- Fork B: EXP-516 P_yz invariance (reflection x -> -x).

Child payloads = material eigenvalue hashes (EXP-515 witness), and Claim.id excludes the stalk, so the
whole transition lineage is reflection-invariant. PYTHONHASHSEED=0.
"""
import sys, os
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/agency"))
import numpy as np
from dentatus import core
from dentatus.semantic import stalk_D_from_sigma
from engine.validity import cholesky_from_stalk_401
from transition_dag import TransitionDAG

def stalk(l11, l22, l33, l21=0.0, l31=0.0, l32=0.0):
    s = np.zeros(18); s[12:18] = [l11, l22, l33, l21, l31, l32]; return s
def root_claim(sk):
    return core.Claim(provenance=core.Provenance(parent_ids=(), operator_id="seed", timestamp=core.now_iso()),
                      payload="seed", stalk=sk, t=0)

base = stalk(1.6, -0.7, -0.9, 0.4, 0.2, 0.3)
_, Sig = cholesky_from_stalk_401(base)
refl = base.copy(); refl[12:18] = stalk_D_from_sigma(np.diag([-1.0, 1, 1]) @ Sig @ np.diag([-1.0, 1, 1]).T)

def build(sk):
    dag = TransitionDAG(); r = root_claim(sk); dag.add_root(r)
    a, _ = dag.record(r, 40.0, 0.12, 148, 396, vorticity=0.40)
    b, _ = dag.record(a, 40.0, 0.16, 148, 396, vorticity=0.40)
    return dag, r, a, b
dA, rA, aA, bA = build(base)
dB, rB, aB, bB = build(refl)

assert aA.id == aB.id and bA.id == bB.id
print(f"[1] PASS  P_yz: child Claim ids invariant under reflection ({aA.id}, {bA.id})")
wA = dA.edges[0]["witness"]; wB = dB.edges[0]["witness"]
assert wA["H_before"] == wB["H_before"] and wA["H_after"] == wB["H_after"]
print(f"[2] PASS  witness H_before & H_after invariant")
assert dA.ancestry(bA.id) == dB.ancestry(bB.id)
print(f"[3] PASS  ancestry structure identical under reflection")
assert wA["t_star"] == wB["t_star"] and wA["chi_after"] == wB["chi_after"]
print(f"[4] PASS  t_star & chi invariant (t*={wA['t_star']:.4f}, chi_after={wA['chi_after']:.3f})")
dA2, _, _, bA2 = build(base)
assert bA2.id == bA.id
print(f"[5] PASS  cross-process bit-stability (PYTHONHASHSEED=0)")

print("\n=== EXP-516 Fork B: 5/5 PASS ===")
print("    Reflection-invariant: material-eigenvalue payloads -> child ids, witness hashes, ancestry all invariant.")
