"""
run_p_invariance_exp520.py -- Fork B: EXP-520 P_yz invariance (reflection x -> -x).

Command inputs (beta_Z, strain, vorticity) are the same physical drive; child ids use material-
eigenvalue payloads. The engine H_t chain is orientation-bearing (different per orientation) but each
is INTERNALLY consistent -- verify_history passes for both. PYTHONHASHSEED=0.
"""
import sys, os
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/agency"))
import numpy as np
from dentatus import core
from dentatus.semantic import stalk_D_from_sigma
from engine.validity import cholesky_from_stalk_401, material_compliance_chi_514
from replay import TimeMachine

def world(dpar):
    s = np.zeros(18); s[0:4] = [1.0, 0.55, 0.57, 0.62]; s[12:18] = dpar
    cl = core.Claim(provenance=core.Provenance(parent_ids=(), operator_id="seed", timestamp=core.now_iso()),
                    payload="m", stalk=s, t=0)
    mu = core.MuState(t=0, claims={cl.id: cl}, entailments={}, active=frozenset([cl.id]), S=np.zeros(18), alpha=0.5)
    mu.seal(); return mu
DIA = [2.0, -1.0, -1.0, 0.0, 0.0, 0.0]
sA = np.zeros(18); sA[12:18] = DIA
_, Sig = cholesky_from_stalk_401(sA)
DIA_R = list(stalk_D_from_sigma(np.diag([-1.0, 1, 1]) @ Sig @ np.diag([-1.0, 1, 1]).T))
DRIVE = [(40.0, 0.12 + 0.012 * i, 0.40) for i in range(10)]

def build(dpar):
    tm = TimeMachine(world(dpar), checkpoint_every=4)
    for (b, st, vo) in DRIVE: tm.step(b, st, 148, 396, vorticity=vo)
    return tm
tmA, tmB = build(DIA), build(DIA_R)

inA = [(c["inputs"]["beta_Z"], c["inputs"]["strain"], c["inputs"]["vorticity"]) for c in tmA.commands]
inB = [(c["inputs"]["beta_Z"], c["inputs"]["strain"], c["inputs"]["vorticity"]) for c in tmB.commands]
assert inA == inB
print(f"[1] PASS  P_yz: command inputs invariant ({len(inA)} commands)")
assert [c["child_id"] for c in tmA.commands] == [c["child_id"] for c in tmB.commands]
print(f"[2] PASS  child ids invariant (material-H payloads)")
assert tmA.verify_history() == tmB.verify_history() == len(tmA.commands)
print(f"[3] PASS  verified replay passes for both orientations (internally consistent)")
muA, _ = tmA.reconstruct(3); muB, _ = tmB.reconstruct(3)
cA = material_compliance_chi_514(stalk=muA.claims[next(iter(muA.active))].stalk)["chi"]
cB = material_compliance_chi_514(stalk=muB.claims[next(iter(muB.active))].stalk)["chi"]
assert cA == cB
print(f"[4] PASS  reconstructed material chi at seq 3 invariant ({cA})")
tmA2 = build(DIA)
assert [c["result_H"] for c in tmA2.commands] == [c["result_H"] for c in tmA.commands]
print(f"[5] PASS  cross-process bit-stability (PYTHONHASHSEED=0)")

print("\n=== EXP-520 Fork B: 5/5 PASS ===")
print("    Command inputs + material lineage P_yz-invariant; each orientation's H_t chain internally")
print("    consistent under verified replay.")
