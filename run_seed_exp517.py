"""
run_seed_exp517.py -- Fork A: EXP-517 Live MuState Injection (Fork rho)

Protocol exp517-v1. Declaration hash: 082b4a773bb23dfc2fe573d3c2d34010d5efd252e19707b0604b50d262338656
Injects a phase change into the running MuState (continuous H_t chain) and resolves Interference via
optimistic concurrency (stale basis_H rejected). Engine FROZEN. PYTHONHASHSEED=0.
"""
import sys, os, json, hashlib
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/agency"))
import numpy as np
from dentatus import core
from injection import (inject_phase_change_517, make_intent, apply_intent_517, rebase_intent, StaleStateError)

DH = "082b4a773bb23dfc2fe573d3c2d34010d5efd252e19707b0604b50d262338656"
with open(os.path.join(ROOT, "studies/exp517_live_injection/SEED_DECLARATION_exp517.json")) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DH
print(f"[1] PASS  declaration_hash = {DH[:16]}...")

def world(d_params, payload="mat"):
    s = np.zeros(18); s[0:4] = [1.0, 0.5, 0.5, 0.5]; s[12:18] = d_params
    cl = core.Claim(provenance=core.Provenance(parent_ids=(), operator_id="seed", timestamp=core.now_iso()),
                    payload=payload, stalk=s, t=0)
    mu = core.MuState(t=0, claims={cl.id: cl}, entailments={}, active=frozenset([cl.id]), S=np.zeros(18), alpha=0.5)
    mu.seal(); return mu, cl
DIA = [2.0, -1.0, -1.0, 0, 0, 0]; WAT = [0, 0, 0, 0, 0, 0]

mu0, dia = world(DIA); H0 = mu0.H
mu1, child, rec = inject_phase_change_517(mu0, dia, 40.0, 0.12, 148, 396, vorticity=0.40, expected_H=H0)

# [2] new state, chain advances
assert rec["injected"] and mu1.t == 1 and child.id in mu1.active and dia.id not in mu1.active and rec["H_engine_before"] != rec["H_engine_after"]
print(f"[2] PASS  injected: t 0->1, child active, parent inactive, H {rec['H_engine_before'][:10]}->{rec['H_engine_after'][:10]}")

# [3] H_t continuity / provenance
assert rec["H_engine_before"] == H0 and rec["H_engine_after"] == mu1.H and child.provenance.parent_ids == (dia.id,) and child.provenance.operator_id == "PhaseChange:minimal"
print(f"[3] PASS  continuous chain: H_before==H0, H_after==mu1.H; child provenance->parent op=PhaseChange:minimal")

# [4] CAS guard
try:
    inject_phase_change_517(mu1, child, 40.0, 0.16, 148, 396, vorticity=0.40, expected_H=H0); raise AssertionError("no raise")
except StaleStateError:
    pass
ok, _, _ = inject_phase_change_517(mu1, child, 40.0, 0.16, 148, 396, vorticity=0.40, expected_H=mu1.H)
print(f"[4] PASS  CAS: stale expected_H rejected; correct expected_H succeeds")

# [5] INTERFERENCE
intent_solid = make_intent(mu0, action="reinforce_lattice", assume="solid")
r = apply_intent_517(mu1, intent_solid)
assert not r["accepted"] and r["reason"] == "stale_basis"
print(f"[5] PASS  interference: solid intent (basis H0) on fluid world (H1) -> rejected stale_basis")

# [6] REBASE
r2 = apply_intent_517(mu1, rebase_intent(mu1, intent_solid))
assert r2["accepted"] and r2["live_H"] == mu1.H
print(f"[6] PASS  rebase: re-stamped intent accepted against live world")

# [7] world is now fluid
chi_after = core.material_compliance_chi_514(stalk=child.stalk)["chi"]
assert abs(chi_after - rec["chi_after"]) < 1e-9 and rec["dZ_norm"] > 0
print(f"[7] PASS  world fluidised: active material chi={chi_after:.3f} (was 0.05), dZ_norm={rec['dZ_norm']}")

# [8] purity
assert mu0.H == H0 and dia.id in mu0.active and child.id not in mu0.claims
print(f"[8] PASS  purity: input mu0 unchanged (H==H0, parent still active, child absent)")

# [9] stable/unsurvivable -> no injection
muw, wat = world(WAT)
m, c, rw = inject_phase_change_517(muw, wat, 40.0, 0.12, 148, 396, vorticity=0.40)
assert c is None and not rw["injected"] and m is muw and rw["status"] == "stable"
mu_d, dd = world(DIA)
m2, c2, ru = inject_phase_change_517(mu_d, dd, 6.0, 0.40, 148, 396, vorticity=0.30)
assert c2 is None and ru["status"] == "unsurvivable"
print(f"[9] PASS  no-op outcomes: water stable (no inject), diamond@high-shear unsurvivable (no inject)")

# [10] determinism
mu1b, childb, recb = inject_phase_change_517(world(DIA)[0], world(DIA)[1], 40.0, 0.12, 148, 396, vorticity=0.40)
assert recb["H_engine_after"] == rec["H_engine_after"] and childb.id == child.id
print(f"[10] PASS  determinism: H_engine_after + child id bit-stable")

print("\n=== EXP-517 Fork A: 10/10 PASS ===")
print("    Live injection: continuous H_t chain (lineage IS state); CAS + stale-intent rejection resolve")
print("    Interference (solid intent on fluid world); ghost-accumulated; engine frozen.")
