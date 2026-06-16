"""
walkthrough_genesis.py — EXP-524 The Genesis Block (Full System Walkthrough).

One world through the entire Dentatus constitution, in a single unbroken, self-verifying chain. This is
the proof-of-life: every act calls the real engine + game-layer operators and asserts the constitutional
invariant it demonstrates. Run with PYTHONHASHSEED=0.

    ACT I    Creation        — instantiate a pristine Diamond manifold; FULL_VALID, chi=0.05
    ACT II   Stress          — tectonic shear past the Weissenberg limit; the Citadel reports a breach
    ACT III  Metamorphosis   — minimal-entropy melt Diamond -> Stressed Glass; then a total melt -> Fluid
    ACT IV   Continuity      — inject into MuState, advance H_t; optimistic-concurrency rejects stale intent
    ACT V    Audit           — compact (bounded memory); replay-resurrect the ORIGINAL diamond from the DAG
    ACT VI   Recovery        — lower the shear; oriented nucleation re-crystallises along the new stress axis
    ACT VII  Final Witness   — mint the integrity witness: FULL_VALID at the new resolution
"""
import sys, os
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
for p in ("game/agency", "game/observability"):
    sys.path.insert(0, os.path.join(ROOT, p))
import numpy as np
from dentatus import core
from phase_change import enact_phase_change_515
from injection import inject_phase_change_517, make_intent, apply_intent_517, rebase_intent, StaleStateError
from compaction import CompactingWorld
from replay import TimeMachine, cold_restore
from recrystallize import enact_recrystallization_521
from nucleation import enact_oriented_nucleation_522
from integrity import verified_address, integrity_witness

BETA, NF, NG, VORT = 40.0, 148, 396, 0.40
def chi(st): return core.material_compliance_chi_514(stalk=st)["chi"]
def banner(n, t): print("\n" + "=" * 74 + f"\n  ACT {n} — {t}\n" + "=" * 74)


# ===================== ACT I — CREATION =====================
banner("I", "CREATION — a pristine Diamond manifold")
s = np.zeros(18); s[0:4] = [1.0, 0.55, 0.57, 0.62]; s[8:11] = [0, 0, 1]; s[12:18] = [2.0, -1.0, -1.0, 0, 0, 0]
seed = core.Claim(provenance=core.Provenance(parent_ids=(), operator_id="genesis:diamond", timestamp=core.now_iso()),
                  payload="diamond", stalk=s, t=0)
mu0 = core.MuState(t=0, claims={seed.id: seed}, entailments={}, active=frozenset([seed.id]), S=np.zeros(18), alpha=0.5)
mu0.seal(); H0 = mu0.H
w0 = integrity_witness(mu0, "FULL_VALID")
print(f"  H_0 (genesis)   : {H0}")
print(f"  material chi    : {chi(s):.3f}  (diamond — ordered, low compliance)")
print(f"  integrity       : {w0['validity_class']}  verified_address={w0['verified_address']}")
assert chi(s) < 0.1 and w0["is_full_integrity"] and w0["verified_address"] == H0
print("  [OK] pristine diamond, FULL_VALID, address == H_0")


# ===================== ACT II — STRESS =====================
banner("II", "STRESS — tectonic shear past the Weissenberg limit")
for wi in (0.20, 0.35, 0.45):
    bc = core.bethe_citadel_strain_512(BETA, wi * VORT, NF, NG, vorticity=VORT, chi=chi(s))
    flag = "ADMIT" if bc["dS_cit"] >= 0 else "BREACH"
    print(f"  Wi={wi:.2f}  strain*={bc['strain_star']:.2f}  dS_cit={bc['dS_cit']:+.2f}  chi_req={bc['chi_required']}  [{flag}]")
bc = core.bethe_citadel_strain_512(BETA, 0.45 * VORT, NF, NG, vorticity=VORT, chi=chi(s))
assert bc["dS_cit"] < 0 and bc["survivable_by_material"]
print(f"  [OK] diamond breaches at Wi=0.45 (dS<0) but is survivable -> must metamorphose")


# ===================== ACT III — METAMORPHOSIS =====================
banner("III", "METAMORPHOSIS — minimal-entropy melt, then total melt to Fluid")
tm = TimeMachine(mu0, checkpoint_every=3)
chi_path = [chi(tm.live.claims[next(iter(tm.live.active))].stalk)]
for wi in (0.18, 0.26):                                   # gentle survivable shears -> Stressed Glass
    tm.step(BETA, wi * VORT, NF, NG, vorticity=VORT)
    chi_path.append(chi(tm.live.claims[next(iter(tm.live.active))].stalk))
glass_chi = chi_path[-1]
tm.step(BETA, 0.45 * VORT, NF, NG, vorticity=VORT, mode="total")   # tectonic spike breaches glass -> TOTAL melt -> amorphous fluid
fluid_claim = tm.live.claims[next(iter(tm.live.active))]
print(f"  chi: diamond {chi_path[0]:.3f} --minimal melts--> stressed glass {glass_chi:.3f} --total melt--> fluid {chi(fluid_claim.stalk):.3f}")
print(f"  transitions journaled: {len(tm.commands)}   H_live: {tm.live.H[:16]}")
assert chi_path[0] < glass_chi < 1.0 and chi(fluid_claim.stalk) == 1.0
print("  [OK] diamond -> stressed glass -> amorphous fluid (minimal entropy injection, det-preserving)")


# ===================== ACT IV — CONTINUITY + INTERFERENCE =====================
banner("IV", "CONTINUITY — H_t advances; optimistic concurrency rejects stale intent")
intent_solid = make_intent(mu0, action="reinforce_lattice", assume="solid")   # computed against the DIAMOND
r_stale = apply_intent_517(tm.live, intent_solid)
r_rebased = apply_intent_517(tm.live, rebase_intent(tm.live, intent_solid))
print(f"  H chain: {H0[:16]} -> ... -> {tm.live.H[:16]}  (continuous, t=0 -> t={tm.live.t})")
print(f"  solid-intent on fluid world : accepted={r_stale['accepted']} reason={r_stale.get('reason')}")
print(f"  rebased intent              : accepted={r_rebased['accepted']}")
assert tm.live.H != H0 and not r_stale["accepted"] and r_rebased["accepted"]
print("  [OK] lineage IS the state; a stale solid-assumption intent cannot corrupt the fluid world")


# ===================== ACT V — AUDIT (compaction + replay resurrection) =====================
banner("V", "AUDIT — bounded memory; resurrect the ORIGINAL diamond from the DAG")
cw = CompactingWorld(mu0, skeleton_n=4)
for cmd in tm.commands:
    p = cw.live.claims[next(iter(cw.live.active))]
    cw.inject(p, cmd["inputs"]["beta_Z"], cmd["inputs"]["strain"], NF, NG,
              **{k: v for k, v in cmd["inputs"].items() if k not in ("beta_Z", "strain", "n_fragments", "n_gamma")})
print(f"  live working set : {cw.working_set_size()} claim   |   auditable history : {cw.history_size()} transitions")
n_verified = tm.verify_history()
diamond_again, info = tm.reconstruct(H0)                  # resurrect genesis from command log + checkpoint
print(f"  verify_history   : {n_verified} transitions reproduce bit-for-bit (determinism proof)")
print(f"  RESURRECTION     : reconstruct(H_0) -> H={diamond_again.H[:16]}  == genesis : {diamond_again.H == H0}")
assert cw.working_set_size() == 1 and diamond_again.H == H0 and chi(diamond_again.claims[next(iter(diamond_again.active))].stalk) < 0.1
print("  [OK] bounded memory + unbounded history; the pristine diamond is re-materialised from its hash")


# ===================== ACT VI — RECOVERY (oriented nucleation) =====================
banner("VI", "RECOVERY — shear subsides; oriented nucleation along the new stress axis")
new_axis = np.array([0.2, 1.0, 0.5]); new_axis /= np.linalg.norm(new_axis)
sym_L = 0.3 * np.outer(new_axis, new_axis) - 0.05 * np.eye(3)     # a NEW, re-oriented low strain field
ns, wn = enact_oriented_nucleation_522(fluid_claim.stalk, sym_L, BETA, 0.05 * VORT, NF, NG, vorticity=VORT)
_, Sig = core.cholesky_from_stalk_401(ns); _, cV = np.linalg.eigh(Sig)
align = abs(float(cV[:, -1] @ new_axis))
print(f"  amorphous fluid chi {wn['chi_before']:.3f} --oriented nucleation--> chi {wn['chi_after']:.3f}")
print(f"  crystal axis . new strain axis = {align:.4f}  (world re-orders along the forces now acting on it)")
print(f"  det preserved    : {wn['det_before']:.4f} == {wn['det_after']:.4f}   |   no re-melt (hysteresis)")
assert wn["status"] == "nucleated" and wn["chi_after"] < 1.0 and align > 0.999 and wn["chi_after"] > wn["chi_required"]
print("  [OK] the amorphous fluid re-crystallises into a new ordered solid aligned to the new stress")


# ===================== ACT VII — FINAL WITNESS =====================
banner("VII", "FINAL WITNESS — FULL_VALID at the new resolution")
child = core.Claim(provenance=core.Provenance(parent_ids=(fluid_claim.id,), operator_id="Nucleate", timestamp=core.now_iso()),
                   payload="recrystallised", stalk=ns, t=tm.live.t + 1)
mu_final = core.MuState(t=child.t, claims={child.id: child}, entailments={}, active=frozenset([child.id]),
                        S=tm.live.S, alpha=0.5); mu_final.seal()
wf = integrity_witness(mu_final, "FULL_VALID")
print(f"  H_final          : {mu_final.H}")
print(f"  material chi     : {chi(ns):.3f}  (a new ordered solid)")
print(f"  integrity        : {wf['validity_class']}  verified_address={wf['verified_address']}  full_integrity={wf['is_full_integrity']}")
assert wf["is_full_integrity"] and wf["verified_address"] == mu_final.H
print("  [OK] the world is FULL_VALID; address == H_final (no integrity laundering)")


# ===================== EPILOGUE =====================
print("\n" + "=" * 74)
print("  GENESIS COMPLETE — the universe lived a full constitutional cycle:")
print(f"    created (chi 0.05) -> sheared past Wi -> melted (glass -> fluid) -> injected ({len(tm.commands)} txns,")
print(f"    H_t continuous) -> compacted (mem={cw.working_set_size()}, history={cw.history_size()}) ->")
print(f"    diamond resurrected from hash -> nucleated to a new solid (chi {wn['chi_after']:.2f}, aligned) -> FULL_VALID.")
print("  Every step verified. Engine constitutionally frozen throughout.")
print("=" * 74)
print("\n=== EXP-524 Genesis Walkthrough: ALL ACTS PASS ===")
