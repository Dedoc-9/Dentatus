"""
run_seed_exp522.py -- Fork A: EXP-522 Oriented Nucleation (Fork psi)

Protocol exp522-v1. Declaration hash: 851a4f654a262c2ac4e5ad73c9d67558337315b6714cb399963a67e5c601d3b8
An amorphous (total-melt) state re-crystallises along the strain principal axis. Closes Ghost #54.
Engine FROZEN. PYTHONHASHSEED=0.
"""
import sys, os, json, hashlib
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/agency"))
import numpy as np
from dentatus import core
from phase_change import enact_phase_change_515
from nucleation import enact_oriented_nucleation_522, HYSTERESIS_522

DH = "851a4f654a262c2ac4e5ad73c9d67558337315b6714cb399963a67e5c601d3b8"
with open(os.path.join(ROOT, "studies/exp522_oriented_nucleation/SEED_DECLARATION_exp522.json")) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DH
print(f"[1] PASS  declaration_hash = {DH[:16]}...")

BETA, NF, NG, VORT = 40.0, 148, 396, 0.40
def diamond():
    s = np.zeros(18); s[0:4] = [1.0, 0.55, 0.57, 0.62]; s[12:18] = [2.0, -1.0, -1.0, 0, 0, 0]; return s
def chi(st): return core.material_compliance_chi_514(stalk=st)["chi"]
amorph, _ = enact_phase_change_515(diamond(), 40.0, 0.12, NF, NG, vorticity=VORT, mode="total")
ax = np.array([1.0, 0.6, 0.2]); ax /= np.linalg.norm(ax)
SYM_L = 0.3 * np.outer(ax, ax) - 0.05 * np.eye(3)

# [2] amorphous re-crystallises
assert chi(amorph) > 0.99
ns, w = enact_oriented_nucleation_522(amorph, SYM_L, BETA, 0.05 * VORT, NF, NG, vorticity=VORT)
assert w["status"] == "nucleated" and w["chi_after"] < 0.99
print(f"[2] PASS  amorphous {w['chi_before']:.3f} -> nucleated {w['chi_after']:.3f} (regained order)")

# [3] ALIGNMENT
_, Sig = core.cholesky_from_stalk_401(ns); _, cV = np.linalg.eigh(Sig)
align = abs(float(cV[:, -1] @ ax))
assert w["alignment_cos"] > 0.999 and align > 0.999
print(f"[3] PASS  alignment: covariance major axis . strain axis = {align:.4f} (~1, crystal aligned to flow)")

# [4] no orienting field (isotropic stress)
_, wi = enact_oriented_nucleation_522(amorph, 0.1 * np.eye(3), BETA, 0.05 * VORT, NF, NG, vorticity=VORT)
assert wi["status"] == "no_orienting_field"
print(f"[4] PASS  isotropic stress -> no_orienting_field (stays amorphous, no preferred axis)")

# [5] not_amorphous defers
_, wd = enact_oriented_nucleation_522(diamond(), SYM_L, BETA, 0.05 * VORT, NF, NG, vorticity=VORT)
assert wd["status"] == "not_amorphous"
print(f"[5] PASS  residual-order material -> not_amorphous (defers to EXP-521)")

# [6] volume preserved
assert abs(w["det_after"] - w["det_before"]) < 1e-6
print(f"[6] PASS  volume preserved: det {w['det_before']:.4f} == {w['det_after']:.4f}")

# [7] hysteresis dead-zone -> hold
c0 = chi(amorph)
strain_dead = max(0.0, c0 - 0.08) * 0.1906
_, wh = enact_oriented_nucleation_522(amorph, SYM_L, BETA, strain_dead, NF, NG, vorticity=VORT)
assert wh["status"] == "hold"
print(f"[7] PASS  hysteresis dead-zone -> hold (no nucleation when headroom < {HYSTERESIS_522})")

# [8] stays admissible
assert w["chi_after"] > w["chi_required"]
print(f"[8] PASS  stays admissible: chi_after {w['chi_after']:.3f} > chi_required {w['chi_required']:.3f}")

# [9] Ghost #54 end-to-end closure: total-melt then oriented-nucleate
d = diamond()
melted, mw = enact_phase_change_515(d, 40.0, 0.12, NF, NG, vorticity=VORT, mode="total")
nucleated, nw = enact_oriented_nucleation_522(melted, SYM_L, BETA, 0.05 * VORT, NF, NG, vorticity=VORT)
assert mw["chi_after"] == 1.0 and nw["status"] == "nucleated" and chi(nucleated) < 1.0
print(f"[9] PASS  Ghost #54 closed: diamond -total-melt-> chi=1.0 -nucleate-> chi={chi(nucleated):.3f} (amorphous re-ordered)")

# [10] determinism
a = enact_oriented_nucleation_522(amorph, SYM_L, BETA, 0.05 * VORT, NF, NG, vorticity=VORT)[1]
b = enact_oriented_nucleation_522(amorph, SYM_L, BETA, 0.05 * VORT, NF, NG, vorticity=VORT)[1]
assert a["chi_after"] == b["chi_after"] and a["beta"] == b["beta"] and a["alignment_cos"] == b["alignment_cos"]
print(f"[10] PASS  determinism: chi_after + beta + alignment bit-stable")

print("\n=== EXP-522 Fork A: 10/10 PASS ===")
print("    Oriented nucleation: amorphous state re-crystallises along the strain principal axis")
print("    (det-preserving, hysteresis-gated, aligned to the flow). Ghost #54 CLOSED.")
