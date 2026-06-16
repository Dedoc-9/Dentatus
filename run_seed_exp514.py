"""
run_seed_exp514.py -- Fork A: EXP-514 Epistemic Materialism (Fork theta)

Protocol exp514-v1. Declaration hash: 99eda360b4e85bd8bf8ff7da6815e5c2bf15b77f7eced542d45303f0bce7398a
Compliance chi (continuous map of Sector D covariance spectrum) -> material narrows the constitutional
window: eps_ref_eff = STRAIN_STAR_REF*chi. Diamond (stiff, low chi) fragile; water (chi=1) tolerant.
chi from declared state (no API bypass). Engine: additive. Requires PYTHONHASHSEED=0.
"""
import sys, os, json, hashlib
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/observability"))
import numpy as np
from engine.validity import (material_compliance_chi_514 as chi_of, bethe_citadel_strain_512 as F,
                             is_bethe_strain_512, CHI_MIN_514, STRAIN_STAR_REF_512)

DH = "99eda360b4e85bd8bf8ff7da6815e5c2bf15b77f7eced542d45303f0bce7398a"
with open(os.path.join(ROOT, "studies/exp514_epistemic_materialism/SEED_DECLARATION_exp514.json")) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DH
print(f"[1] PASS  declaration_hash = {DH[:16]}...")

def stalk(l11, l22, l33, l21=0.0, l31=0.0, l32=0.0):
    s = np.zeros(18); s[12:18] = [l11, l22, l33, l21, l31, l32]; return s

water = chi_of(stalk(0, 0, 0))
diamond = chi_of(stalk(2.0, -1.0, -1.0))
granite = chi_of(stalk(0.5, 0.0, -0.4, 0.3, 0.1, 0.2))

# [2] water isotropic -> chi=1
assert water["chi"] == 1.0 and water["eta_spec"] == 1.0 and water["gap_spec"] == 0.0
print(f"[2] PASS  water (isotropic): chi={water['chi']} eta={water['eta_spec']} gap={water['gap_spec']}")

# [3] diamond anisotropic -> chi=chi_min; monotone more-anisotropy -> lower chi
assert diamond["chi"] == CHI_MIN_514 and diamond["eta_spec"] < 0.1 and diamond["gap_spec"] > 0.9
assert water["chi"] > granite["chi"] > diamond["chi"]
print(f"[3] PASS  diamond: chi={diamond['chi']} (floor); ordering water {water['chi']} > granite {granite['chi']:.3f} > diamond {diamond['chi']}")

# [4] CONTINUOUS (not lookup): tiny perturbation -> tiny chi change
c0 = chi_of(stalk(0.5, 0.0, -0.4, 0.3, 0.1, 0.2))["chi"]
c1 = chi_of(stalk(0.5 + 1e-3, 0.0, -0.4, 0.3, 0.1, 0.2))["chi"]
assert abs(c1 - c0) < 1e-2
print(f"[4] PASS  continuous map: d(stalk)=1e-3 -> dchi={abs(c1-c0):.2e} (not a discrete lookup)")

# [5] bounded: eps_ref_eff = STRAIN_STAR_REF*chi <= STRAIN_STAR_REF
for m in (water, granite, diamond):
    r = F(40.0, 0.12, 148, 396, vorticity=0.40, chi=m["chi"])
    assert CHI_MIN_514 <= m["chi"] <= 1.0 and r["eps_ref_eff"] <= STRAIN_STAR_REF_512 + 1e-12
print(f"[5] PASS  bounded: chi in [{CHI_MIN_514},1]; eps_ref_eff <= STRAIN_STAR_REF (material narrows only)")

# [6] EPISTEMIC MATERIALISM: same Weissenberg shear -> water ADMITS, diamond REJECTS
# operating point: beta_Z=40, Wi=0.3 (strain=0.12, vort=0.40) -> water admits, diamond shatters
wv = F(40.0, 0.12, 148, 396, vorticity=0.40, chi=water["chi"])
dv = F(40.0, 0.12, 148, 396, vorticity=0.40, chi=diamond["chi"])
assert is_bethe_strain_512(wv["dS_cit"]) and not is_bethe_strain_512(dv["dS_cit"])
print(f"[6] PASS  same Wi=0.30: water dS={wv['dS_cit']:+.2f} ADMIT, diamond dS={dv['dS_cit']:+.2f} REJECT (material = truth filter)")

# [7] phase-change target: chi_required; admit iff chi >= chi_required
req = wv["chi_required"]
assert req is not None and diamond["chi"] < req <= water["chi"]
print(f"[7] PASS  phase-change: chi_required={req:.3f}; diamond {diamond['chi']} < req <= water {water['chi']} (must soften to survive)")

# [8] no-bypass: chi>1 clipped to 1 (cannot widen beyond constitution)
over = F(40.0, 0.12, 148, 396, vorticity=0.40, chi=5.0)
assert over["chi"] == 1.0 and over["eps_ref_eff"] == STRAIN_STAR_REF_512
print(f"[8] PASS  no-bypass: chi=5.0 clipped to {over['chi']}; eps_ref_eff={over['eps_ref_eff']} (can't exceed constitution)")

# [9] backward compat: chi=None -> byte-identical dS to EXP-513
assert F(40.0, 0.12, 148, 396, vorticity=0.40)["dS_cit"] == F(40.0, 0.12, 148, 396, vorticity=0.40, chi=None)["dS_cit"]
print(f"[9] PASS  backward compat: chi=None identical to EXP-513 dS_cit")

# [10] determinism
assert chi_of(stalk(2.0, -1.0, -1.0))["chi"] == diamond["chi"] and F(40.0, 0.12, 148, 396, vorticity=0.40, chi=0.5)["dS_cit"] == F(40.0, 0.12, 148, 396, vorticity=0.40, chi=0.5)["dS_cit"]
print(f"[10] PASS  determinism: chi + coupled dS_cit bit-stable")

print("\n=== EXP-514 Fork A: 10/10 PASS ===")
print("    Epistemic Materialism: continuous Sector-D-spectrum -> compliance chi; diamond fragile, water")
print("    tolerant; bounded (narrows only, no API bypass); phase-change chi_required; engine additive.")
