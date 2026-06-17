"""
run_seed_exp511.py -- Fork A: EXP-511 Strain-Gated Halo + Boundary Velocity Smoothing

Protocol exp511-v1. Declaration hash: 943feae7c1f52a4e99564a692f7e01197f1168cde87e2ad752ae060bfa301268
Mass-momentum boundary smoothing (volume mass, EMA, NOT leaf-count) stabilizes Cauchy strain that
gates the EXP-506 halo (sigma *= 1+gamma*strain). gamma=0 -> EXP-506 exact. Game layer only.
Requires PYTHONHASHSEED=0.
"""
import sys, os, json, hashlib
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/observability"))
import numpy as np
from multivelocity import (init_state, step, smooth_velocities, local_strain,
                           strain_field_for_halo, section_centroids)
from sectioned_fiedler import stitched_fiedler

DH = "943feae7c1f52a4e99564a692f7e01197f1168cde87e2ad752ae060bfa301268"
with open(os.path.join(ROOT, "studies/exp511_strain_gated_halo/SEED_DECLARATION_exp511.json")) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DH
print(f"[1] PASS  declaration_hash = {DH[:16]}...")

def scene(t, hv=+0.005, lv=-0.005, subdivide=False):
    L = []
    for oy in (0, 1):
        for oz in (0, 1):
            cy, cz = 0.25 + 0.5 * oy, 0.25 + 0.5 * oz
            hc = (0.25 + hv * t, cy, cz)
            if subdivide:                       # 8 sub-leaves filling the same 0.5 cube (same VOLUME)
                for sx in (-1, 1):
                    for sy in (-1, 1):
                        for sz in (-1, 1):
                            L.append({"center": (hc[0] + sx * 0.125, cy + sy * 0.125, cz + sz * 0.125), "size": (0.25, 0.25, 0.25)})
            else:
                L.append({"center": hc, "size": (0.5, 0.5, 0.5)})
            L.append({"center": (0.55 + lv * t, cy, cz), "size": (0.1, 0.5, 0.5)})
    return L

def drive(frames):
    st = init_state()
    for lv in frames:
        st, _ = step(st, lv)
    return st

shear = [scene(t) for t in range(3)]
st = drive(shear)

# [2] SAFETY: gamma=0 reproduces EXP-506 byte-identically
sf = strain_field_for_halo(st, shear[-1])
base = stitched_fiedler(shear[-1])
g0 = stitched_fiedler(shear[-1], strain=sf, gamma_strain=0.0)
assert np.array_equal(base["field"], g0["field"]) and np.array_equal(base["halo_sigma"], g0["halo_sigma"])
print("[2] PASS  gamma_strain=0 -> stitched_fiedler byte-identical to EXP-506 (field+sigma)")

# [3] mass-weighting pulls the light sliver toward the heavy bulk MORE than distance
cur, _ = section_centroids(shear[-1]); lk = [k for k in cur if k[0] == 1]
mm = smooth_velocities(st, shear[-1], mode="mass"); dd = smooth_velocities(st, shear[-1], mode="distance")
vx_m = np.mean([mm[k][0] for k in lk]); vx_d = np.mean([dd[k][0] for k in lk])
assert vx_m > vx_d   # heavy drifts +x; mass pulls light's (-) velocity further toward + than distance
print(f"[3] PASS  mass-momentum pulls sliver toward bulk: v_x mass={vx_m:.5f} > distance={vx_d:.5f} (raw=-0.00375)")

# [4] LOD-INVARIANCE: subdivide heavy (same volume, 8x leaves) -> mass-smoothing identical
sub = [scene(t, subdivide=True) for t in range(3)]
st_sub = drive(sub)
mm_sub = smooth_velocities(st_sub, sub[-1], mode="mass")
cur_s, _ = section_centroids(sub[-1]); lk_s = [k for k in cur_s if k[0] == 1]
assert np.allclose(sorted(mm[k][0] for k in lk), sorted(mm_sub[k][0] for k in lk_s), atol=1e-6)
print("[4] PASS  LOD-invariance: subdividing heavy (same volume, 8x leaves) -> identical smoothing (volume != count)")

# [5] strain-gated halo widens under shear
gat = stitched_fiedler(shear[-1], strain=sf, gamma_strain=2.0)
assert float(np.mean(gat["halo_sigma"])) > float(np.mean(base["halo_sigma"]))
print(f"[5] PASS  halo widens under shear: mean sigma {np.mean(base['halo_sigma']):.5f} -> {np.mean(gat['halo_sigma']):.5f}")

# [6] rigid translation -> strain ~0 -> halo unchanged
rigid = [scene(t, hv=+0.005, lv=+0.005) for t in range(3)]
st_r = drive(rigid)
sf_r = strain_field_for_halo(st_r, rigid[-1])
base_r = stitched_fiedler(rigid[-1]); gat_r = stitched_fiedler(rigid[-1], strain=sf_r, gamma_strain=2.0)
assert abs(float(np.mean(gat_r["halo_sigma"])) - float(np.mean(base_r["halo_sigma"]))) < 1e-6
print(f"[6] PASS  rigid translation -> strain~0 -> halo unchanged (delta {abs(np.mean(gat_r['halo_sigma'])-np.mean(base_r['halo_sigma'])):.2e})")

# [7] smoothing reduces shimmer: alternating jitter on light side -> mass-smoothed strain steadier than raw
def raw_vel_dict(state, leaves):
    cur, _ = section_centroids(leaves)
    out = {}
    for k in cur:
        c = cur[k]; best = None; bd = None
        for t in state["tracks"].values():
            d = sum((c[i] - t["centroid"][i]) ** 2 for i in range(3))
            if bd is None or d < bd:
                bd = d; best = t
        out[k] = tuple(best["v"]) if best else (0.0, 0.0, 0.0)
    return out
raw_series, sm_series = [], []
st_j = init_state()
for t in range(8):
    jit = 0.01 * (1 if t % 2 == 0 else -1)              # deterministic alternating jitter
    lv = scene(t, lv=-0.005 + jit)
    st_j, _ = step(st_j, lv)
    raw_series.append(float(np.max(list(local_strain(raw_vel_dict(st_j, lv), lv).values()))))
    sm_series.append(float(np.max(list(local_strain(smooth_velocities(st_j, lv, mode="mass"), lv).values()))))
ptp_raw = max(raw_series[2:]) - min(raw_series[2:]); ptp_sm = max(sm_series[2:]) - min(sm_series[2:])
assert ptp_sm < ptp_raw
print(f"[7] PASS  smoothing reduces shimmer: strain peak-to-peak raw={ptp_raw:.5f} -> mass-smoothed={ptp_sm:.5f}")

# [8] mass EMA damping: a sudden volume doubling moves EMA mass only halfway (alpha=0.5)
sA = init_state(); sA, _ = step(sA, [{"center": (0.25, 0.25, 0.25), "size": (0.5, 0.5, 0.5)}])
m0 = sA["tracks"][0]["mass"]
sB, _ = step(sA, [{"center": (0.25, 0.25, 0.25), "size": (0.5, 0.5, 0.5)}, {"center": (0.30, 0.30, 0.30), "size": (0.5, 0.5, 0.5)}])
# section now has raw volume 0.25 (two leaves); EMA mass < raw, > m0 -> damped
m1 = next(iter(sB["tracks"].values()))["mass"]
assert m0 < m1 < 0.25
print(f"[8] PASS  mass EMA damps churn: raw doubling 0.125->0.25 damped to {m1} (no shimmer jump)")

# [9] determinism
assert np.array_equal(sf, strain_field_for_halo(drive(shear), shear[-1]))
print("[9] PASS  determinism: strain field bit-identical on re-run")

# [10] dual-only: step() trajectory independent of smoothing/halo calls (no backreaction)
a = init_state(); seqA = []
for lv in shear:
    a, r = step(a, lv); _ = strain_field_for_halo(a, lv); seqA.append(r["matched"])
b = init_state(); seqB = []
for lv in shear:
    b, r = step(b, lv); seqB.append(r["matched"])
assert seqA == seqB
print(f"[10] PASS  dual-only: step matched seq {seqA} unaffected by smoothing/halo (no backreaction)")

print("\n=== EXP-511 Fork A: 10/10 PASS ===")
print("    Mass-momentum boundary smoothing (volume, EMA, not count); strain-gated halo widens only at")
print("    deforming seams; gamma=0 EXP-506-exact; LOD-invariant; shimmer reduced; engine frozen.")
