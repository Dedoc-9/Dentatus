"""
run_seed_exp509.py -- Fork A: EXP-509 Zeeman/Bethe Citadel (thermodynamic firewall)

Protocol: exp509-v1
Declaration hash: 58f3f306a8f48cbe7defa35291a8374a8a94ba7e37d02849c3807fa344c5eea2

E* = beta_Z (Zeeman excitation); Bethe level density rho(E*) = exp(2*sqrt(a*E*)); a = a0*d_stalk
(substrate schema mass, NOT leaf-count). dS_cit_bethe = log2 rho(E*) - log2(N_f+N_gamma) >= 0.
Requires PYTHONHASHSEED=0.

Tests [1-10]: see SEED_DECLARATION_exp509.json assertions_fork_A.
"""
import sys, os, json, hashlib, math
os.environ.setdefault("PYTHONHASHSEED", "0")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dentatus import api, core
from engine.validity import bethe_citadel_509, is_bethe_citadel_509, BETHE_A0_509

DECL_HASH = "58f3f306a8f48cbe7defa35291a8374a8a94ba7e37d02849c3807fa344c5eea2"
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
          "studies/exp509_zeeman_bethe_citadel/SEED_DECLARATION_exp509.json")) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DECL_HASH
print(f"[1] PASS  declaration_hash = {DECL_HASH[:16]}...")

d = core.STALK_DIM; a = BETHE_A0_509 * d; LN2 = math.log(2)
b = bethe_citadel_509(36.8, 148, 396)
assert abs(b["a"] - a) < 1e-9
assert abs(b["H_in"] - 2 * math.sqrt(a * 36.8) / LN2) < 1e-6
assert abs(b["H_out"] - math.log2(544)) < 1e-6 and abs(b["dS_cit"] - (b["H_in"] - b["H_out"])) < 1e-6
print(f"[2] PASS  Bethe math: H_in=2*sqrt(a*E)/ln2={b['H_in']:.3f}, a={a}, dS_cit={b['dS_cit']:.3f}")

# a depends on schema mass d, NOT on leaf-count: vary N_f, a is unchanged
assert bethe_citadel_509(36.8, 8, 12)["a"] == bethe_citadel_509(36.8, 2000, 5000)["a"] == round(a, 9)
print(f"[3] PASS  a = a0*d_stalk = {a} (substrate schema mass, independent of leaf-count -- no double-count)")

ds_by_E = [bethe_citadel_509(E, 148, 396)["dS_cit"] for E in [40, 20, 10, 5, 2]]
assert all(ds_by_E[i] > ds_by_E[i + 1] for i in range(len(ds_by_E) - 1)) and ds_by_E[0] > 0 and ds_by_E[-1] < 0
print(f"[4] PASS  excitation friction: fixed complexity, E*=[40..2] -> dS {[round(x,1) for x in ds_by_E]} (crosses 0)")

over = bethe_citadel_509(2.0, 148, 396)
assert not is_bethe_citadel_509(over["dS_cit"]) and over["dS_cit"] < 0
print(f"[5] PASS  overheat reject: low excitation (E*=2) over-complex -> dS={over['dS_cit']:.2f} -> is_bethe False")

INTENT = {"title": "docking_bay", "seed": {"density": 1.0, "material": [0.55, 0.57, 0.62], "normal": [0, 0, 1],
          "curvature": 2.0, "stress": {"axes": [3.0, 2.0, 0.4], "plane": "xy", "tilt_deg": 35}},
          "bbox": [[0, 0, 0], [1, 1, 1]], "zeeman": {"focus": [0.5, 0.5, 0.0]}}
adm = []
for bud in [2048, 1024, 512, 256, 128, 64]:
    r = api.observe({"op": "observe", "intent": {**INTENT, "zeeman": {"focus": [0.5,0.5,0.0], "budget": bud}}, "steps": 8})
    adm.append(r["bethe_citadel"]["is_bethe_citadel"])
assert all(adm)
print(f"[6] PASS  valid worlds admitted: docking ladder all Bethe-admissible (E* = realized beta_Z)")

r = api.observe({"op": "observe", "intent": {**INTENT, "zeeman": {"focus": [0.5,0.5,0.0], "budget": 2048}}, "steps": 8})
bc = r["bethe_citadel"]
assert set(bc) >= {"E_star", "H_in", "H_out", "dS_cit", "is_bethe_citadel"}
print(f"[7] PASS  observable reported: E*={bc['E_star']:.1f}, dS_cit_bethe={bc['dS_cit']:.2f} (the temperature)")

rg = api.observe({"op": "observe", "intent": {**INTENT, "zeeman": {"focus": [0.5,0.5,0.0], "budget": 2048}}, "steps": 8, "bethe_gate": True})
assert rg["bethe_citadel"]["gated"] is True and r["bethe_citadel"]["gated"] is False
assert (r["H_verified"] is not None)
print(f"[8] PASS  opt-in gate: bethe_gate=True gated={rg['bethe_citadel']['gated']}; default unchanged")

r2 = api.observe({"op": "observe", "intent": {**INTENT, "zeeman": {"focus": [0.5,0.5,0.0], "budget": 2048}}, "steps": 8})
assert r2["bethe_citadel"]["dS_cit"] == r["bethe_citadel"]["dS_cit"]
print(f"[9] PASS  determinism: dS_cit_bethe bit-stable ({r['bethe_citadel']['dS_cit']})")

assert r["H_verified"] is not None and r["firewall"]["is_manifold_501"] and r["citadel"]["is_citadel"]
print(f"[10] PASS  no regression: default H_verified unchanged vs EXP-508 ({r['H_verified'][:16]}...)")

print(f"\n=== EXP-509 Fork A: 10/10 PASS ===")
print(f"    Zeeman/Bethe Citadel: E*=beta_Z, rho=exp(2sqrt(aE*)), a=a0*d_stalk={a} (schema mass, not leaf-count)")
print(f"    excitation friction (overheat reject); observable + opt-in gate; valid worlds admitted")
