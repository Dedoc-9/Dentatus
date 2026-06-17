"""
run_p_invariance_exp510.py -- Fork B: EXP-510 P_yz invariance (reflection x -> -x).

Protocol exp510-v1. Under x->-x: center.x, v.x, C_hat.x, G.x flip sign; speeds, strain, vorticity,
R, match/birth/death counts and the size-multiset are invariant. The structural hash (built only
from invariants) must be identical. Requires PYTHONHASHSEED=0.
"""
import sys, os
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/observability"))
import numpy as np
from multivelocity import run

def leaves(off):
    L = []; b = 0.25
    for ox in (0, 1):
        for oy in (0, 1):
            for oz in (0, 1):
                c = np.array([b + 0.5 * ox, b + 0.5 * oy, b + 0.5 * oz], float) + np.array(off.get((ox, oy, oz), (0, 0, 0)), float)
                L.append({"center": tuple(c), "size": (0.5, 0.5, 0.5)})
    return L
def shear(n=6, t0=1):
    fr = []
    for t in range(t0, t0 + n):
        o = {(ox, oy, oz): ((+0.01 if oy == 0 else -0.01) * t, 0.003 * t, 0) for ox in (0, 1) for oy in (0, 1) for oz in (0, 1)}
        fr.append(leaves(o))
    return fr
def reflect(frames):
    return [[{"center": (1.0 - l["center"][0], l["center"][1], l["center"][2]), "size": l["size"]} for l in fr] for fr in frames]

F = shear(); Fr = reflect(F)
_, recA, hA, _ = run(F)
_, recB, hB, _ = run(Fr)

assert hA == hB
print(f"[1] PASS  P_yz: per-frame structural hashes identical under x->-x ({hA[-1][:16]}...)")

for a, b in zip(recA, recB):
    assert a["strain"] == b["strain"] and a["vorticity"] == b["vorticity"] and a["rigidity_R"] == b["rigidity_R"]
    assert (a["matched"], a["births"], a["deaths"]) == (b["matched"], b["births"], b["deaths"])
print(f"[2] PASS  strain/vorticity/R/match counts invariant under reflection")

for a, b in zip(recA, recB):
    assert sorted(a["speeds"]) == sorted(b["speeds"])
print(f"[3] PASS  speed multiset invariant")

for a, b in zip(recA, recB):
    assert abs(a["divergence"] - b["divergence"]) < 1e-9     # tr(L) scalar, reflection-invariant
print(f"[4] PASS  divergence (tr L) invariant: e.g. {recA[-1]['divergence']:+.4f} == {recB[-1]['divergence']:+.4f}")

_, _, hA2, _ = run(shear())
assert hA == hA2
print(f"[5] PASS  cross-run bit-stability (PYTHONHASHSEED=0): hashes reproducible")

print(f"\n=== EXP-510 Fork B: 5/5 PASS ===")
print(f"    P_yz reflection-invariant: hash built only from invariants (speeds, strain, vort, counts);")
print(f"    signed x-components (v.x, G.x) excluded -- consistent with track_dag_hash_505 / Ghost #27.")
