"""
run_seed_exp515.py -- Fork A: EXP-515 Enacted Phase Change (Fork lambda)

Protocol exp515-v1. Declaration hash: c238e89e21e18bb50ad97626309f923e1efb93f8bb50c92d62ce872204415bfa
Witnessed material re-declaration: volume-preserving anisotropy-melt geodesic, minimal t* (least
entropy injection) vs total isotropic melt. Engine FROZEN (game-layer policy). PYTHONHASHSEED=0.
"""
import sys, os, json, hashlib
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/agency"))
import numpy as np
from phase_change import enact_phase_change_515

DH = "c238e89e21e18bb50ad97626309f923e1efb93f8bb50c92d62ce872204415bfa"
with open(os.path.join(ROOT, "studies/exp515_enacted_phase_change/SEED_DECLARATION_exp515.json")) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DH
print(f"[1] PASS  declaration_hash = {DH[:16]}...")

def stalk(l11, l22, l33, l21=0.0, l31=0.0, l32=0.0):
    s = np.zeros(18); s[12:18] = [l11, l22, l33, l21, l31, l32]; return s
diamond = stalk(2.0, -1.0, -1.0); water = stalk(0, 0, 0)

# [2] stable
ns, w = enact_phase_change_515(water, 40.0, 0.12, 148, 396, vorticity=0.40)
assert w["status"] == "stable" and np.allclose(ns, water) and w["H_before"] == w["H_after"] and w["t_star"] == 0.0
print(f"[2] PASS  stable: water admits -> no transition (stalk unchanged, H stable)")

# [3] melted minimal
ns, w = enact_phase_change_515(diamond, 40.0, 0.12, 148, 396, vorticity=0.40, mode="minimal")
assert w["status"] == "melted" and w["chi_after"] >= w["chi_required"] and w["admit_after"] and not w["admit_before"]
print(f"[3] PASS  melted (minimal): chi {w['chi_before']:.3f}->{w['chi_after']:.3f} (req {w['chi_required']:.3f}), admit False->True")

# [4] volume preserved
assert abs(w["det_after"] - w["det_before"]) < 1e-6
print(f"[4] PASS  volume preserved: det {w['det_before']:.4f} == {w['det_after']:.4f} (anisotropy-only melt)")

# [5] minimality: chi_after just above required, far below total melt (chi<1)
assert (w["chi_after"] - w["chi_required"]) < 0.05 and w["chi_after"] < 0.95
print(f"[5] PASS  minimality: chi_after-chi_required={w['chi_after']-w['chi_required']:.4f} (<0.05), chi_after={w['chi_after']:.3f}<1 (not total melt)")

# [6] total mode
ns_t, wt = enact_phase_change_515(diamond, 40.0, 0.12, 148, 396, vorticity=0.40, mode="total")
assert wt["chi_after"] == 1.0 and wt["admit_after"] and abs(wt["det_after"] - wt["det_before"]) < 1e-6
print(f"[6] PASS  total melt: chi_after={wt['chi_after']} (isotropic), admit_after={wt['admit_after']}, det preserved")

# [7] unsurvivable
ns_u, wu = enact_phase_change_515(diamond, 6.0, 0.40, 148, 396, vorticity=0.30)
assert wu["status"] == "unsurvivable" and np.allclose(ns_u, diamond) and (wu["chi_required"] is None or wu["chi_required"] > 1.0)
print(f"[7] PASS  unsurvivable: chi_required>1 (no melt saves) -> stalk unchanged, status={wu['status']}")

# [8] witnessed
assert w["H_before"] != w["H_after"] and set(w) >= {"chi_before", "chi_after", "chi_required", "t_star"}
print(f"[8] PASS  witnessed: H_before != H_after ({w['H_before'][:10]}..->{w['H_after'][:10]}..); witness complete")

# [9] purity: input unchanged
d0 = stalk(2.0, -1.0, -1.0)
enact_phase_change_515(d0, 40.0, 0.12, 148, 396, vorticity=0.40)
assert np.allclose(d0, stalk(2.0, -1.0, -1.0))
print(f"[9] PASS  purity: input stalk unchanged after call (engine state untouched)")

# [10] determinism
ns2, w2 = enact_phase_change_515(diamond, 40.0, 0.12, 148, 396, vorticity=0.40, mode="minimal")
assert np.allclose(ns2[12:18], ns[12:18]) and w2["H_after"] == w["H_after"] and w2["t_star"] == w["t_star"]
print(f"[10] PASS  determinism: new Sector D + witness H_after bit-stable")

print("\n=== EXP-515 Fork A: 10/10 PASS ===")
print("    Enacted phase change: volume-preserving anisotropy-melt; minimal t* (least entropy injection)")
print("    diamond chi 0.05->0.63 graceful yield; total mode -> 1.0; witnessed; engine frozen.")
