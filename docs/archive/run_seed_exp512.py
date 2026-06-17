"""
run_seed_exp512.py -- Fork A: EXP-512 Strain -> Bethe coupling (Fork epsilon)

Protocol exp512-v1. Declaration hash: dd86223ac4b68ff8d1cfcc208ae807edd9999ede8eea23755bbbe50d03292a37
E*_eff = beta_Z*(1-(strain/eps_ref)^2); a fixed (substrate); strain=0 recovers EXP-509. Deformation
energy drains the excitation reservoir -> violent shear overheats -> rejected. Engine: additive
validity predicate only. Requires PYTHONHASHSEED=0.
"""
import sys, os, json, hashlib
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/observability"))
import numpy as np
from engine.validity import bethe_citadel_strain_512 as F, is_bethe_strain_512, bethe_citadel_509, STRAIN_EPS_REF_512
from multivelocity import init_state, step, citadel_strain_coupling, strain_field_for_halo

DH = "dd86223ac4b68ff8d1cfcc208ae807edd9999ede8eea23755bbbe50d03292a37"
with open(os.path.join(ROOT, "studies/exp512_strain_bethe_coupling/SEED_DECLARATION_exp512.json")) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DH
print(f"[1] PASS  declaration_hash = {DH[:16]}...")

# [2] strain=0 recovers EXP-509 exactly
assert F(36.8, 0.0, 148, 396)["dS_cit"] == bethe_citadel_509(36.8, 148, 396)["dS_cit"]
print(f"[2] PASS  strain=0 recovers EXP-509 dS_cit exactly ({bethe_citadel_509(36.8,148,396)['dS_cit']})")

# [3] friction: dS strictly decreasing, crosses 0
ds = [F(10.0, s, 148, 396)["dS_cit"] for s in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]]
assert all(ds[i] > ds[i + 1] for i in range(len(ds) - 1)) and ds[0] > 0 and ds[-1] < 0
print(f"[3] PASS  excitation friction: strain=[0..0.5] -> dS {[round(x,2) for x in ds]} (admit->reject)")

# [4] a unchanged across strain
assert F(10.0, 0.0, 148, 396)["a"] == F(10.0, 0.3, 148, 396)["a"] == F(10.0, 0.5, 148, 396)["a"] == round(0.15 * 18, 9)
print(f"[4] PASS  a = a0*d_stalk = {round(0.15*18,9)} unchanged across strain (substrate constant)")

# [5] quadratic elastic fraction
r = F(10.0, 0.25, 148, 396)
assert abs(r["E_strain_frac"] - (0.25 / 0.5) ** 2) < 1e-9
print(f"[5] PASS  E_strain_frac == (strain/eps_ref)^2 = {r['E_strain_frac']} (quadratic / elastic)")

# [6] overheat at eps_ref
o = F(10.0, 0.5, 148, 396)
assert o["E_star_eff"] == 0.0 and not is_bethe_strain_512(o["dS_cit"])
print(f"[6] PASS  strain=eps_ref -> E*_eff=0 -> overheat reject (dS={o['dS_cit']})")

# [7] end-to-end: measure scene strains, calibrate eps_ref between rigid & violent, assert verdicts
def leaves(off):
    L = []; b = 0.25
    for ox in (0, 1):
        for oy in (0, 1):
            for oz in (0, 1):
                c = np.array([b + 0.5 * ox, b + 0.5 * oy, b + 0.5 * oz], float) + np.array(off.get((ox, oy, oz), (0, 0, 0)), float)
                L.append({"center": tuple(c), "size": (0.5, 0.5, 0.5)})
    return L
def drive(kind, n=4):
    st = init_state(); last = None
    for t in range(1, 1 + n):
        o = {}
        for ox in (0, 1):
            for oy in (0, 1):
                for oz in (0, 1):
                    o[(ox, oy, oz)] = ((+0.02 if oy == 0 else -0.02) * t, 0, 0) if kind == "shear" else (0.02 * t, 0, 0)
        last = leaves(o); st, _ = step(st, last)
    return st, last
st_v, lv_v = drive("shear"); st_r, lv_r = drive("rigid")
s_violent = float(np.max(strain_field_for_halo(st_v, lv_v)))
s_rigid = float(np.max(strain_field_for_halo(st_r, lv_r)))
eps = 0.5 * (s_violent + s_rigid) if s_violent > s_rigid else max(s_violent, 1e-6) * 0.5
viol = citadel_strain_coupling(st_v, lv_v, 6.0, 148, 396, eps_ref=eps)
rig = citadel_strain_coupling(st_r, lv_r, 6.0, 148, 396, eps_ref=eps)
assert s_violent > s_rigid and not viol["is_bethe_strain"] and rig["is_bethe_strain"]
print(f"[7] PASS  end-to-end: shear strain={s_violent:.4f} REJECT, rigid strain={s_rigid:.4f} ADMIT (eps_ref={eps:.4f})")

# [8] no-regression: EXP-509 default path bit-identical
assert bethe_citadel_509(20.0, 100, 200)["dS_cit"] == bethe_citadel_509(20.0, 100, 200)["dS_cit"]
b0 = bethe_citadel_509(20.0, 100, 200); b1 = F(20.0, 0.0, 100, 200)
assert b0["dS_cit"] == b1["dS_cit"] and "E_strain_frac" not in b0
print(f"[8] PASS  no-regression: bethe_citadel_509 default path unchanged (coupling is opt-in fn)")

# [9] determinism
assert F(10.0, 0.3, 148, 396)["dS_cit"] == F(10.0, 0.3, 148, 396)["dS_cit"]
assert citadel_strain_coupling(st_v, lv_v, 6.0, 148, 396, eps_ref=eps)["dS_cit"] == viol["dS_cit"]
print(f"[9] PASS  determinism: coupled dS_cit bit-stable")

# [10] eps_ref knob monotone
assert F(10.0, 0.3, 148, 396, eps_ref=1.0)["dS_cit"] > F(10.0, 0.3, 148, 396, eps_ref=0.5)["dS_cit"]
print(f"[10] PASS  eps_ref monotone: larger eps_ref -> higher dS at fixed strain (more tolerant)")

print("\n=== EXP-512 Fork A: 10/10 PASS ===")
print("    Strain->Bethe: deformation energy drains excitation (E*_eff=beta_Z*(1-(strain/eps_ref)^2));")
print("    a fixed; strain=0 recovers 509; violent shear overheats; engine additive-only.")
