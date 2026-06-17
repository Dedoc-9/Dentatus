"""
run_p_invariance_exp511.py -- Fork B: EXP-511 P_yz invariance (reflection x -> -x).

strain, smoothed speeds, section mass (volume) and the gated halo are P_yz-invariant scalars/fields:
under x->-x velocity x-components flip but Frobenius strain norm, speed magnitudes and volumes are
unchanged. Requires PYTHONHASHSEED=0.
"""
import sys, os
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/observability"))
import numpy as np
from multivelocity import init_state, step, smooth_velocities, strain_field_for_halo, section_centroids
from sectioned_fiedler import stitched_fiedler

def scene(t, hv=+0.005, lv=-0.005):
    L = []
    for oy in (0, 1):
        for oz in (0, 1):
            cy, cz = 0.25 + 0.5 * oy, 0.25 + 0.5 * oz
            L.append({"center": (0.25 + hv * t, cy, cz), "size": (0.5, 0.5, 0.5)})
            L.append({"center": (0.55 + lv * t, cy, cz), "size": (0.1, 0.5, 0.5)})
    return L
def reflect(lv):
    return [{"center": (1.0 - l["center"][0], l["center"][1], l["center"][2]), "size": l["size"]} for l in lv]
def drive(frames):
    st = init_state()
    for lv in frames:
        st, _ = step(st, lv)
    return st

F = [scene(t) for t in range(3)]; Fr = [reflect(lv) for lv in F]
stA = drive(F); stB = drive(Fr)

sfA = strain_field_for_halo(stA, F[-1]); sfB = strain_field_for_halo(stB, Fr[-1])
assert np.allclose(sorted(sfA), sorted(sfB), atol=1e-9)
print(f"[1] PASS  P_yz: strain field invariant (max {sfA.max():.5f} == {sfB.max():.5f})")

gA = stitched_fiedler(F[-1], strain=sfA, gamma_strain=2.0)["halo_sigma"]
gB = stitched_fiedler(Fr[-1], strain=sfB, gamma_strain=2.0)["halo_sigma"]
assert np.allclose(sorted(gA), sorted(gB), atol=1e-9)
print(f"[2] PASS  gated halo_sigma invariant under reflection")

smA = smooth_velocities(stA, F[-1], mode="mass"); smB = smooth_velocities(stB, Fr[-1], mode="mass")
spA = sorted(round(float(np.linalg.norm(v)), 6) for v in smA.values())
spB = sorted(round(float(np.linalg.norm(v)), 6) for v in smB.values())
assert spA == spB
print(f"[3] PASS  smoothed speed multiset invariant")

mA = sorted(round(t["mass"], 6) for t in stA["tracks"].values())
mB = sorted(round(t["mass"], 6) for t in stB["tracks"].values())
assert mA == mB
print(f"[4] PASS  section mass (volume) invariant: {mA}")

assert np.array_equal(sfA, strain_field_for_halo(drive(F), F[-1]))
print(f"[5] PASS  cross-run bit-stability (PYTHONHASHSEED=0)")

print("\n=== EXP-511 Fork B: 5/5 PASS ===")
print("    Reflection-invariant: strain/speed/mass/halo are Frobenius-norm & volume scalars;")
print("    signed velocity x-components flip but observables are P_yz-invariant.")
