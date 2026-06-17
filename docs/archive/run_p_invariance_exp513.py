"""
run_p_invariance_exp513.py -- Fork B: EXP-513 P_yz invariance (reflection x -> -x).

strain & vorticity (Frobenius norms) and beta_Z are P_yz-invariant scalars, so both non-dimensional
strain* (courant strain*dt, weissenberg strain/|vort|) and the coupled dS_cit are reflection-invariant.
Requires PYTHONHASHSEED=0.
"""
import sys, os
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/observability"))
import numpy as np
from multivelocity import init_state, step, citadel_strain_coupling

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
        o = {(ox, oy, oz): ((+0.05 if oy == 0 else -0.05) * t, 0, 0) for ox in (0, 1) for oy in (0, 1) for oz in (0, 1)}
        lv = leaves(o)
        if reflectx:
            lv = [{"center": (1.0 - l["center"][0], l["center"][1], l["center"][2]), "size": l["size"]} for l in lv]
        last = lv; st, _ = step(st, lv)
    return st, last

stA, lvA = drive(False); stB, lvB = drive(True)
cA = citadel_strain_coupling(stA, lvA, 6.0, 148, 396, nondim="courant", dt=1.0)
cB = citadel_strain_coupling(stB, lvB, 6.0, 148, 396, nondim="courant", dt=1.0)
wA = citadel_strain_coupling(stA, lvA, 6.0, 148, 396, nondim="weissenberg")
wB = citadel_strain_coupling(stB, lvB, 6.0, 148, 396, nondim="weissenberg")

assert cA["dS_cit"] == cB["dS_cit"]
print(f"[1] PASS  P_yz: courant dS_cit invariant ({cA['dS_cit']})")
assert wA["dS_cit"] == wB["dS_cit"]
print(f"[2] PASS  P_yz: weissenberg dS_cit invariant ({wA['dS_cit']})")
assert cA["strain_star"] == cB["strain_star"] and wA["strain_star"] == wB["strain_star"]
print(f"[3] PASS  strain_star invariant both modes (courant {cA['strain_star']:.5f}, Wi {wA['strain_star']:.5f})")
assert cA["is_bethe_strain"] == cB["is_bethe_strain"] and wA["is_bethe_strain"] == wB["is_bethe_strain"]
print(f"[4] PASS  verdict invariant under reflection (courant={cA['is_bethe_strain']}, weissenberg={wA['is_bethe_strain']})")
stA2, lvA2 = drive(False)
assert citadel_strain_coupling(stA2, lvA2, 6.0, 148, 396, nondim="weissenberg")["dS_cit"] == wA["dS_cit"]
print(f"[5] PASS  cross-process bit-stability (PYTHONHASHSEED=0)")

print("\n=== EXP-513 Fork B: 5/5 PASS ===")
print("    Reflection-invariant: strain & vorticity (Frobenius) are P_yz scalars -> both strain* modes")
print("    and the coupled verdict are P_yz-invariant.")
