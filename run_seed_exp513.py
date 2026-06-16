"""
run_seed_exp513.py -- Fork A: EXP-513 Dimensionless Strain (Fork eta)

Protocol exp513-v1. Declaration hash: e283bd260e380617500f9e6a7412633dc422c42ebd71086c460718771417f447
courant strain*=strain*dt (CFL, per-step); weissenberg strain*=strain/|vort| (framerate-independent,
consolidates EXP-510 vorticity). STRAIN_STAR_REF universal. Dimensional path = EXP-512 (byte-stable).
Engine: additive validity extension. Requires PYTHONHASHSEED=0.
"""
import sys, os, json, hashlib
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/observability"))
import numpy as np
from engine.validity import (bethe_citadel_strain_512 as F, is_bethe_strain_512,
                             bethe_citadel_509, STRAIN_STAR_REF_512, STRAIN_EPS_REF_512)
from multivelocity import init_state, step, citadel_strain_coupling, strain_field_for_halo

DH = "e283bd260e380617500f9e6a7412633dc422c42ebd71086c460718771417f447"
with open(os.path.join(ROOT, "studies/exp513_dimensionless_strain/SEED_DECLARATION_exp513.json")) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DH
print(f"[1] PASS  declaration_hash = {DH[:16]}...")

# [2] backward compat: dimensional path byte-identical to EXP-512 (eps_ref default 0.5)
r_dim = F(10.0, 0.3, 148, 396)
assert r_dim["nd_mode"] == "dimensional" and r_dim["eps_ref"] == STRAIN_EPS_REF_512
assert abs(r_dim["E_strain_frac"] - (0.3 / 0.5) ** 2) < 1e-9
print(f"[2] PASS  dimensional path unchanged from EXP-512 (eps_ref={r_dim['eps_ref']}, mode={r_dim['nd_mode']})")

# [3] courant: strain*=strain*dt; finer dt -> smaller strain* -> dS increases (more permissive)
ds = []
for dt in [1.0, 0.5, 0.25]:
    r = F(6.0, 0.6, 148, 396, dt=dt)
    assert abs(r["strain_star"] - 0.6 * dt) < 1e-9 and r["nd_mode"] == "courant" and r["eps_ref"] == STRAIN_STAR_REF_512
    ds.append(r["dS_cit"])
assert ds[0] < ds[1] < ds[2]
print(f"[3] PASS  courant strain*=strain*dt; finer dt more permissive: dS {[round(x,2) for x in ds]} (universal eps_ref)")

# [4] courant universal: a per-step-unstable seam (strain*>eps_ref) rejected by THE SAME constant
unstable = F(6.0, 0.8, 148, 396, dt=1.0)        # strain*=0.8 > 0.5
assert unstable["strain_star"] > STRAIN_STAR_REF_512 and not is_bethe_strain_512(unstable["dS_cit"])
print(f"[4] PASS  courant universal: strain*={unstable['strain_star']} > {STRAIN_STAR_REF_512} -> reject (no per-world calibration)")

# [5] weissenberg: rotation-dominated admits, shear-dominated rejects
rot = F(6.0, 0.01, 148, 396, vorticity=0.20)
shear = F(6.0, 0.45, 148, 396, vorticity=0.10)
assert rot["nd_mode"] == "weissenberg" and is_bethe_strain_512(rot["dS_cit"]) and not is_bethe_strain_512(shear["dS_cit"])
print(f"[5] PASS  weissenberg: rotation-dom Wi={rot['strain_star']:.3f} ADMIT; shear-dom Wi={shear['strain_star']:.3f} REJECT")

# [6] FRAMERATE-INDEPENDENCE: common rate scaling of (strain, vort) -> identical Wi & verdict
v0 = F(6.0, 0.30, 148, 396, vorticity=0.20)
vk = [F(6.0, 0.30 * k, 148, 396, vorticity=0.20 * k) for k in [2.0, 0.5, 10.0]]
assert all(abs(r["strain_star"] - v0["strain_star"]) < 1e-9 and r["dS_cit"] == v0["dS_cit"] for r in vk)
print(f"[6] PASS  weissenberg framerate-INDEPENDENT: Wi={v0['strain_star']} invariant under rate-scaling x{{2,0.5,10}}")

# [7] ghost #47: vorticity=0 finite (regularised), high strain -> reject (no div-by-zero)
z = F(6.0, 0.5, 148, 396, vorticity=0.0)
assert np.isfinite(z["strain_star"]) and not is_bethe_strain_512(z["dS_cit"])
print(f"[7] PASS  ghost #47 regularised: vort=0 -> strain*={z['strain_star']:.1f} finite -> reject (no singularity)")

# [8] strain*=0 recovers EXP-509 in every mode
b509 = bethe_citadel_509(36.8, 148, 396)["dS_cit"]
assert F(36.8, 0.0, 148, 396, dt=1.0)["dS_cit"] == F(36.8, 0.0, 148, 396, vorticity=0.5)["dS_cit"] == b509
print(f"[8] PASS  strain*=0 recovers EXP-509 dS_cit in courant & weissenberg ({b509})")

# [9] end-to-end via game-layer coupling on a shear scene
def leaves(off):
    L = []; b = 0.25
    for ox in (0, 1):
        for oy in (0, 1):
            for oz in (0, 1):
                c = np.array([b + 0.5 * ox, b + 0.5 * oy, b + 0.5 * oz], float) + np.array(off.get((ox, oy, oz), (0, 0, 0)), float)
                L.append({"center": tuple(c), "size": (0.5, 0.5, 0.5)})
    return L
st = init_state(); last = None
for t in range(1, 5):
    o = {(ox, oy, oz): ((+0.05 if oy == 0 else -0.05) * t, 0, 0) for ox in (0, 1) for oy in (0, 1) for oz in (0, 1)}
    last = leaves(o); st, _ = step(st, last)
cc = citadel_strain_coupling(st, last, 6.0, 148, 396, nondim="courant", dt=1.0)
cw = citadel_strain_coupling(st, last, 6.0, 148, 396, nondim="weissenberg")
assert cc["nd_mode"] == "courant" and cw["nd_mode"] == "weissenberg"
print(f"[9] PASS  end-to-end: courant strain*={cc['strain_star']:.4f} admit={cc['is_bethe_strain']}; weissenberg Wi={cw['strain_star']:.3f} admit={cw['is_bethe_strain']}")

# [10] determinism
assert F(6.0, 0.6, 148, 396, dt=0.5)["dS_cit"] == F(6.0, 0.6, 148, 396, dt=0.5)["dS_cit"]
assert citadel_strain_coupling(st, last, 6.0, 148, 396, nondim="weissenberg")["dS_cit"] == cw["dS_cit"]
print(f"[10] PASS  determinism: strain*/dS_cit bit-stable")

print("\n=== EXP-513 Fork A: 10/10 PASS ===")
print("    Dimensionless strain: courant (strain*dt, per-step CFL) + weissenberg (strain/|vort|,")
print("    framerate-independent, EXP-510 consolidation); eps_ref universal; dimensional path EXP-512-exact.")
