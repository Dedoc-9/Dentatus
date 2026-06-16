"""
run_seed_exp521.py -- Fork A: EXP-521 Re-crystallization / Annealing (Fork xi)

Protocol exp521-v1. Declaration hash: 8f9fcf2b21b0ce974e0069b279e66ace9175fdc27acffde7aa3e7975bb449418
True thermal hysteresis: distinct cooling threshold, reverse anisotropy geodesic, chatter-free; closes
Ghost #49. Engine FROZEN. PYTHONHASHSEED=0.
"""
import sys, os, json, hashlib
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/agency"))
import numpy as np
from dentatus import core
from phase_change import enact_phase_change_515
from recrystallize import enact_recrystallization_521, HYSTERESIS_521, ANNEAL_521

DH = "8f9fcf2b21b0ce974e0069b279e66ace9175fdc27acffde7aa3e7975bb449418"
with open(os.path.join(ROOT, "studies/exp521_recrystallization/SEED_DECLARATION_exp521.json")) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DH
print(f"[1] PASS  declaration_hash = {DH[:16]}...")

BETA, NF, NG, VORT = 40.0, 148, 396, 0.40
def diamond():
    s = np.zeros(18); s[0:4] = [1.0, 0.55, 0.57, 0.62]; s[12:18] = [2.0, -1.0, -1.0, 0, 0, 0]; return s
def chi(st): return core.material_compliance_chi_514(stalk=st)["chi"]
def melt_to(st, target_chi):
    for strain in [0.10, 0.13, 0.15, 0.165, 0.175]:   # rising SURVIVABLE melts (Wi < ~0.47)
        if chi(st) >= target_chi - 0.02: break
        st2, w = enact_phase_change_515(st, BETA, strain, NF, NG, vorticity=VORT)
        if w["status"] == "melted": st = st2
    return st

# a fluid (melted) material at low stress -> should re-crystallize
fluid = melt_to(diamond(), 0.9)

# [2] hold in dead-zone: stress whose chi_required is ~0.08 below chi_cur (headroom < hysteresis)
c0 = chi(fluid)
assert c0 > 0.7, f"melt helper failed: fluid chi={c0}"
strain_dead = max(0.0, c0 - 0.08) * 0.1906   # chi_required = strain*/(0.5*sqrt(frac)) -> strain ~ chi_req*0.19
hold = enact_recrystallization_521(fluid, BETA, strain_dead, NF, NG, vorticity=VORT)[1]
assert hold["headroom"] < HYSTERESIS_521 and hold["status"] == "hold"
print(f"[2] PASS  dead-zone hold: headroom {hold['headroom']:.3f} < hysteresis {HYSTERESIS_521} -> hold (memory)")

# [3] recrystallize at low stress (large headroom)
ns, w = enact_recrystallization_521(fluid, BETA, 0.05 * VORT, NF, NG, vorticity=VORT)
assert w["status"] == "recrystallized" and w["chi_after"] < w["chi_before"]
print(f"[3] PASS  recrystallize: chi {w['chi_before']:.3f} -> {w['chi_after']:.3f} (regains order, headroom {w['headroom']:.2f})")

# [4] stays admissible (no immediate re-melt)
assert w["chi_after"] > w["chi_required"]
print(f"[4] PASS  no re-melt: chi_after {w['chi_after']:.3f} > chi_required {w['chi_required']:.3f}")

# [5] HYSTERESIS LOOP
def thermal_step(st, strain):
    c = chi(st); bc = core.bethe_citadel_strain_512(BETA, strain, NF, NG, vorticity=VORT, chi=c)
    if bc["dS_cit"] < 0 and bc["survivable_by_material"]:
        ns, ww = enact_phase_change_515(st, BETA, strain, NF, NG, vorticity=VORT); return ns
    ns, ww = enact_recrystallization_521(st, BETA, strain, NF, NG, vorticity=VORT); return ns
st = diamond(); up = [round(0.10 + 0.05 * i, 3) for i in range(8)]; down = up[::-1]
um, dm = {}, {}
for wi in up: st = thermal_step(st, wi * VORT); um[wi] = chi(st)
for wi in down: st = thermal_step(st, wi * VORT); dm.setdefault(wi, chi(st))
area = sum(abs(dm[wi] - um[wi]) for wi in up)
assert all(dm[wi] >= um[wi] - 1e-6 for wi in up) and area > 0.3
print(f"[5] PASS  hysteresis loop: down-path chi >= up-path at every Wi; loop area {area:.3f} (>0 = true hysteresis)")

# [6] chatter-free
st = diamond()
for _ in range(6): st = thermal_step(st, 0.30 * VORT)
seq = [round(chi(thermal_step(st, 0.05 * VORT) if False else st), 4)]
cs = []
for _ in range(8):
    st = thermal_step(st, 0.05 * VORT); cs.append(round(chi(st), 4))
assert len(set(cs[-3:])) == 1
print(f"[6] PASS  chatter-free: fixed low stress settles to {cs[-1]} (last 3 identical, no oscillation)")

# [7] anneal-rate limited
ns, w = enact_recrystallization_521(fluid, BETA, 0.0, NF, NG, vorticity=VORT)
assert (w["chi_before"] - w["chi_after"]) <= ANNEAL_521 + 1e-2
print(f"[7] PASS  anneal-rate limited: Δchi {w['chi_before']-w['chi_after']:.3f} <= {ANNEAL_521} (slow cooling)")

# [8] amorphous guard
iso = np.zeros(18); iso[0:4] = [1, 0.5, 0.5, 0.5]; iso[12:18] = [0, 0, 0, 0, 0, 0]  # Sigma = I (isotropic)
ns, w = enact_recrystallization_521(iso, BETA, 0.0, NF, NG, vorticity=VORT)
assert w["status"] == "amorphous_hold"
print(f"[8] PASS  amorphous guard: isotropic Sigma (zero spread) -> {w['status']} (no residual order)")

# [9] volume preserved
ns, w = enact_recrystallization_521(fluid, BETA, 0.05 * VORT, NF, NG, vorticity=VORT)
assert abs(w["det_after"] - w["det_before"]) < 1e-6
print(f"[9] PASS  volume preserved: det {w['det_before']:.4f} == {w['det_after']:.4f}")

# [10] determinism
a = enact_recrystallization_521(fluid, BETA, 0.05 * VORT, NF, NG, vorticity=VORT)[1]
b = enact_recrystallization_521(fluid, BETA, 0.05 * VORT, NF, NG, vorticity=VORT)[1]
assert a["chi_after"] == b["chi_after"] and a["g"] == b["g"]
print(f"[10] PASS  determinism: chi_after + g bit-stable")

print("\n=== EXP-521 Fork A: 10/10 PASS ===")
print("    Re-crystallization: distinct cooling threshold (Schmitt hysteresis), reverse anisotropy")
print("    geodesic, chatter-free, volume-preserving -> true thermal hysteresis. Ghost #49 CLOSED.")
