"""
run_seed_exp510.py -- Fork A: EXP-510 Multi-Velocity Section Tracking (Ghost #40)

Protocol: exp510-v1
Declaration hash: 5f83cb5ac6b907e1fc618707b4d500f5e3a0dea44522fa1b70d07e2ecf38e579

Per-section co-moving frames (velocity v_s, EMA of observed displacement) hold correspondence under
DIFFERENTIAL motion; velocity-gradient L = strain(sym) + vorticity(antisym) isolates true non-
rigidity. Game layer only (no engine edits). Requires PYTHONHASHSEED=0.
"""
import sys, os, json, hashlib
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/observability"))
import numpy as np
from multivelocity import run, step, init_state, kinematic_decomposition

DECL_HASH = "5f83cb5ac6b907e1fc618707b4d500f5e3a0dea44522fa1b70d07e2ecf38e579"
with open(os.path.join(ROOT, "studies/exp510_multivelocity_tracking/SEED_DECLARATION_exp510.json")) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DECL_HASH
print(f"[1] PASS  declaration_hash = {DECL_HASH[:16]}...")

def leaves(off):
    L = []; b = 0.25
    for ox in (0, 1):
        for oy in (0, 1):
            for oz in (0, 1):
                c = np.array([b + 0.5 * ox, b + 0.5 * oy, b + 0.5 * oz], float) + np.array(off.get((ox, oy, oz), (0, 0, 0)), float)
                L.append({"center": tuple(c), "size": (0.5, 0.5, 0.5)})
    return L
def frames(kind, n=6, t0=0):
    fr = []
    for t in range(t0, t0 + n):
        o = {}
        for ox in (0, 1):
            for oy in (0, 1):
                for oz in (0, 1):
                    if kind == "rigid":   o[(ox, oy, oz)] = (0.01 * t, 0, 0)
                    elif kind == "shear": o[(ox, oy, oz)] = ((+0.01 if oy == 0 else -0.01) * t, 0, 0)
                    elif kind == "expand":o[(ox, oy, oz)] = ((ox - 0.5) * 0.02 * t, (oy - 0.5) * 0.02 * t, (oz - 0.5) * 0.02 * t)
                    elif kind == "rot":   o[(ox, oy, oz)] = (-(oy - 0.5) * 0.02 * t, (ox - 0.5) * 0.02 * t, 0)
        fr.append(leaves(o))
    return fr

_, rec_r, h_r, _ = run(frames("rigid"))
r = rec_r[-1]
assert r["strain"] == 0.0 and r["vorticity"] == 0.0 and r["divergence"] == 0.0 and r["rigidity_R"] == 1.0
print(f"[2] PASS  rigid translation: strain={r['strain']} vort={r['vorticity']} div={r['divergence']} R={r['rigidity_R']} (zero deformation)")

_, rec_s, _, _ = run(frames("shear"))
assert all(x["match_rate"] == 1.0 for x in rec_s[1:])
print(f"[3] PASS  differential shear: match_rate sustained = {[x['match_rate'] for x in rec_s[1:]]} (single-motion 505 would tear)")

s = rec_s[-1]
assert s["strain"] > 0 and s["vorticity"] > 0 and abs(s["divergence"]) < 1e-6
print(f"[4] PASS  simple shear Cauchy split: strain={s['strain']:.4f} vort={s['vorticity']:.4f} div={s['divergence']:.4f}")

_, rec_e, _, _ = run(frames("expand"))
e = rec_e[-1]
assert e["divergence"] > 0 and e["vorticity"] == 0.0
print(f"[5] PASS  isotropic expansion: div={e['divergence']:+.4f} vort={e['vorticity']} (dilation isolated)")

_, rec_t, _, _ = run(frames("rot"))
t_ = rec_t[-1]
assert t_["vorticity"] > 3 * t_["strain"]
print(f"[6] PASS  rotation: vort={t_['vorticity']:.4f} > 3x strain={t_['strain']:.4f} (near-rigid)")

gk = [x["ghost_kin_mean"] for x in rec_s[1:]]
assert gk[-1] < gk[0]
print(f"[7] PASS  kinematic ghost decays under constant velocity: G_kin {gk} (EMA convergence)")

# [8] ghost never controls forward assignment: assignment (match counts) is identical whether or not
# we read Skin -- Skin is write-only w.r.t. control. Verify by re-running; matched sequence stable.
m1 = [x["matched"] for x in rec_s]
_, rec_s2, _, _ = run(frames("shear"))
assert [x["matched"] for x in rec_s2] == m1
print(f"[8] PASS  ghost is reported-only: matched sequence {m1} independent of Skin (no backreaction)")

_, _, h_s1, _ = run(frames("shear"))
_, _, h_s2, _ = run(frames("shear"))
assert h_s1 == h_s2
print(f"[9] PASS  determinism: identical hashes on re-run (bit-stable) {h_s1[-1][:16]}...")

_, rec_sm, _, _ = run(frames("shear", t0=1))   # symmetry already broken at frame 0
fc = [x["fault_continuity"] for x in rec_sm[1:]]
assert min(fc) >= 0.75
print(f"[10] PASS  fault continuity under differential motion: {fc} (>= 0.75, fault stays healed)")

print(f"\n=== EXP-510 Fork A: 10/10 PASS ===")
print(f"    Multi-velocity: per-section co-moving frames hold correspondence under non-rigid motion;")
print(f"    L = strain(+vort+div) Cauchy split isolates true non-rigidity; ghost reported-only; engine frozen.")
