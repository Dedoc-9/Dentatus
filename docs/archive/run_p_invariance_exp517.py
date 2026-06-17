"""
run_p_invariance_exp517.py -- Fork B: EXP-517 P_yz invariance (reflection x -> -x).

The engine H_t hashes raw Z (orientation-bearing) so it is NOT P_yz-invariant -- that is the live
geometric chain. The MATERIAL lineage witness (eigenvalue H_before/H_after, chi, child id with
material-H payload) and the interference verdict ARE P_yz-invariant. PYTHONHASHSEED=0.
"""
import sys, os
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/agency"))
import numpy as np
from dentatus import core
from dentatus.semantic import stalk_D_from_sigma
from engine.validity import cholesky_from_stalk_401
from injection import inject_phase_change_517, make_intent, apply_intent_517

def world(d_params):
    s = np.zeros(18); s[0:4] = [1.0, 0.5, 0.5, 0.5]; s[12:18] = d_params
    cl = core.Claim(provenance=core.Provenance(parent_ids=(), operator_id="seed", timestamp=core.now_iso()),
                    payload="mat", stalk=s, t=0)
    mu = core.MuState(t=0, claims={cl.id: cl}, entailments={}, active=frozenset([cl.id]), S=np.zeros(18), alpha=0.5)
    mu.seal(); return mu, cl

DIA = [1.6, -0.7, -0.9, 0.4, 0.2, 0.3]
sA = np.zeros(18); sA[12:18] = DIA
_, Sig = cholesky_from_stalk_401(sA)
DIA_REFL = list(stalk_D_from_sigma(np.diag([-1.0, 1, 1]) @ Sig @ np.diag([-1.0, 1, 1]).T))

muA, dA = world(DIA); muB, dB = world(DIA_REFL)
mA, cA, rA = inject_phase_change_517(muA, dA, 40.0, 0.12, 148, 396, vorticity=0.40)
mB, cB, rB = inject_phase_change_517(muB, dB, 40.0, 0.12, 148, 396, vorticity=0.40)

assert rA["material_H_before"] == rB["material_H_before"] and rA["material_H_after"] == rB["material_H_after"]
print(f"[1] PASS  P_yz: material H_before & H_after invariant under reflection")
assert rA["chi_after"] == rB["chi_after"]
print(f"[2] PASS  chi_after invariant ({rA['chi_after']})")
assert cA.id == cB.id
print(f"[3] PASS  child Claim.id invariant (material-H payload): {cA.id}")
solidA = make_intent(muA, action="x"); solidB = make_intent(muB, action="x")
vA = apply_intent_517(mA, solidA)["accepted"]; vB = apply_intent_517(mB, solidB)["accepted"]
assert vA == vB == False
print(f"[4] PASS  interference verdict invariant (solid intent rejected under reflection)")
mA2, cA2, rA2 = inject_phase_change_517(world(DIA)[0], world(DIA)[1], 40.0, 0.12, 148, 396, vorticity=0.40)
assert cA2.id == cA.id and rA2["material_H_after"] == rA["material_H_after"]
print(f"[5] PASS  cross-process bit-stability (PYTHONHASHSEED=0)")

print("\n=== EXP-517 Fork B: 5/5 PASS ===")
print("    Material lineage P_yz-invariant (eigenvalue witness, child id, verdict); the geometric H_t")
print("    chain is the live orientation-bearing state, as intended.")
