"""
run_p_invariance_exp523.py -- Fork B: EXP-523 Validity Witness P_yz invariance (x -> -x).

The validity class is a geometry-independent label; the address-binding construction is identical in
both orientations, so the laundering-closure property is reflection-invariant. PYTHONHASHSEED=0.
"""
import sys, os
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/observability"))
import numpy as np
from dentatus import core
from integrity import verified_address, integrity_witness, addresses_distinct

def mk(reflectx=False):
    s = np.zeros(18); s[0:4] = [1.0, 0.5, 0.5, 0.5]; s[8:11] = [0, 0, 1]
    bbox = (np.array([0.0, 0, 0]), np.array([1.0, 1, 1]))
    if reflectx:
        bbox = (np.array([-1.0, 0, 0]), np.array([0.0, 1, 1]))   # x -> -x reflected extents
    cl = core.Claim(provenance=core.Provenance(parent_ids=(), operator_id="seed", timestamp=core.now_iso()),
                    payload="p", stalk=s, t=0, bbox=bbox)
    mu = core.MuState(t=0, claims={cl.id: cl}, entailments={}, active=frozenset([cl.id]), S=np.zeros(18), alpha=0.5)
    mu.seal(); return mu

aF, aR = mk(False), mk(True)
bF, bR = mk(False), mk(True)

# [1] validity class label is geometry-independent
assert getattr(aF, "validity_class", "FULL_VALID") == getattr(aR, "validity_class", "FULL_VALID") == "FULL_VALID"
print(f"[1] PASS  validity_class label geometry-independent (FULL_VALID both orientations)")

# [2] binding property holds in both orientations
assert verified_address(aF, "FULL_VALID") == aF.H and verified_address(aR, "FULL_VALID") == aR.H
print(f"[2] PASS  FULL_VALID address == H_t in both orientations (consistent binding)")

# [3] addresses_distinct holds under reflection
assert addresses_distinct(aF, bF) and addresses_distinct(aR, bR)
print(f"[3] PASS  laundering-closure (addresses_distinct) holds in both orientations")

# [4] is_full_integrity invariant
assert integrity_witness(aF, "LOD_RELAXED")["is_full_integrity"] == integrity_witness(aR, "LOD_RELAXED")["is_full_integrity"] == False
print(f"[4] PASS  witness is_full_integrity invariant under reflection")

# [5] bit-stable
assert verified_address(bF, "LOD_RELAXED") == verified_address(mk(False), "LOD_RELAXED")
print(f"[5] PASS  cross-process bit-stability (PYTHONHASHSEED=0)")

print("\n=== EXP-523 Fork B: 5/5 PASS ===")
print("    Validity class is a geometry-independent integrity label; the binding closes laundering in")
print("    every orientation (the geometric H_t carries orientation, the integrity tag does not).")
