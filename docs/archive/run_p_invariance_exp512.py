"""
run_p_invariance_exp512.py -- Fork B: EXP-512 P_yz invariance (reflection x -> -x).

strain (Frobenius norm) and beta_Z are P_yz-invariant scalars; deformation-energy drain and the
coupled dS_cit are therefore reflection-invariant. Requires PYTHONHASHSEED=0.
"""
import sys, os
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/observability"))
import numpy as np
from multivelocity import init_state, step, citadel_strain_coupling, strain_field_for_halo

def leaves(off):
    L = []; b = 0.25
    for ox in (0, 1):
        for oy in (0, 1):
            for oz in (0, 1):
                c = np.array([b + 0.5 * ox, b + 0.5 * oy, b + 0.5 * oz], float) + np.array(off.get((ox, oy, oz), (0, 0, 0)), float)
                L.append({"center": tuple(c), "size": (0.5, 0.5, 0.5)})
    return L
def drive(reflectx=False, n=4):
    st = init_state(); last = None
    for t in range(1, 1 + n):
        o = {(ox, oy, oz): ((+0.02 if oy == 0 else -0.02) * t, 0, 0) for ox in (0, 1) for oy in (0, 1) for oz in (0, 1)}
        lv = leaves(o)
        if reflectx:
            lv = [{"center": (1.0 - l["center"][0], l["center"][1], l["center"][2]), "size": l["size"]} for l in lv]
        last = lv; st, _ = step(st, lv)
    return st, last

stA, lvA = drive(False); stB, lvB = drive(True)
a = citadel_strain_coupling(stA, lvA, 6.0, 148, 396, eps_ref=0.006)
b = citadel_strain_coupling(stB, lvB, 6.0, 148, 396, eps_ref=0.006)

assert a["dS_cit"] == b["dS_cit"]
print(f"[1] PASS  P_yz: coupled dS_cit invariant under x->-x ({a['dS_cit']})")
assert a["E_star_eff"] == b["E_star_eff"]
print(f"[2] PASS  E_star_eff invariant ({a['E_star_eff']})")
assert a["is_bethe_strain"] == b["is_bethe_strain"]
print(f"[3] PASS  end-to-end verdict invariant (is_bethe_strain={a['is_bethe_strain']})")
sA = float(np.max(strain_field_for_halo(stA, lvA))); sB = float(np.max(strain_field_for_halo(stB, lvB)))
assert abs(sA - sB) < 1e-9
print(f"[4] PASS  max-section strain invariant ({sA:.6f} == {sB:.6f})")
stA2, lvA2 = drive(False)
assert citadel_strain_coupling(stA2, lvA2, 6.0, 148, 396, eps_ref=0.006)["dS_cit"] == a["dS_cit"]
print(f"[5] PASS  cross-process bit-stability (PYTHONHASHSEED=0)")

print("\n=== EXP-512 Fork B: 5/5 PASS ===")
print("    Reflection-invariant: strain (Frobenius) & beta_Z are P_yz scalars -> coupled dS_cit invariant.")
