"""
forge/bridge_gate_proof.py — EXP-530 live L1 gate integration proof (Game1/dentatus_bridge.py).
Proves: clean commits pass the licensed clamps; a HARD violation triggers a fail-closed revert to the
last valid H (state restored, liveness preserved); replay-continuity (deterministic cmdlog). 0 violations.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
for p in (REPO, os.path.join(REPO, "Game1"), os.path.join(REPO, "forge"),
          os.path.join(REPO, "game/agency"), os.path.join(REPO, "game/observability")):
    if p not in sys.path: sys.path.insert(0, p)
import numpy as np, dentatus_bridge as B
fails = []

# (1) CLEAN COMMIT passes the gate; every licensed hard clamp is satisfied by real engine output
W = B.World()
r1 = W.do_call("Geodesic_Melt_515", True, {"x": 1})
if not r1.get("accepted"): fails.append("clean commit rejected: %r" % r1.get("event"))
if not all(c["ok"] for c in r1.get("clamps", [])): fails.append("a licensed clamp failed on real output")
if not any(c["enf"] == "hard" for c in r1.get("clamps", [])): fails.append("no hard clamp was actually evaluated")

# (2) FAIL-CLOSED: inject a tripwire HARD clamp that rejects the real chi -> revert + hold last valid H
stalk_snap = W.stalk.copy(); H_anchor = W.last_valid_H
W.clamps["tripwire_chi"] = ("chi", lambda v: (False, "tripwire"), "hard")
r2 = W.do_call("Geodesic_Melt_515", True, {"x": 2})
if r2.get("accepted"): fails.append("tripwire commit was accepted (no fail-closed)")
if r2.get("reason") != "property_clamp_violation": fails.append("wrong rejection reason: %r" % r2.get("reason"))
if not np.array_equal(W.stalk, stalk_snap): fails.append("state NOT reverted after hard violation")
if r2.get("H_verified") != H_anchor: fails.append("H advanced on a rejected transaction")
if W.cmdlog[-1].get("rejected") != "property_clamp": fails.append("rejection not logged deterministically")

# (3) LIVENESS: remove tripwire -> the very next call commits normally (world un-locked)
del W.clamps["tripwire_chi"]
r3 = W.do_call("Oriented_Nucleation_522", True, {"x": 3})
if not r3.get("accepted"): fails.append("world stayed locked after a fail-closed revert (liveness lost)")
if r3.get("H_verified") == H_anchor: fails.append("H failed to advance on the recovery commit")

# (4) REPLAY CONTINUITY: two fresh worlds, identical synced drive -> identical committed log (bit-for-bit)
def drive():
    w = B.World(); seq = ["Geodesic_Melt_515", "Oriented_Nucleation_522"] * 4
    for i, nm in enumerate(seq):
        w.do_call(nm, True, {"i": i})
    return [(e.get("H"), e.get("composite"), e.get("seq"), e.get("nonce"), e.get("clamps"), e.get("rejected"))
            for e in w.cmdlog]
if drive() != drive(): fails.append("cmdlog not deterministic across identical drives (replay drift)")

print("EXP-530 · live L1 gate integration proof")
print("  1 clean commit passes licensed clamps .........", "PASS" if not any('clean' in f or 'licensed clamp' in f or 'hard clamp' in f for f in fails) else "FAIL")
print("  2 fail-closed revert on hard violation ........", "PASS" if not any('tripwire' in f or 'revert' in f or 'advanced' in f or 'logged' in f or 'reason' in f for f in fails) else "FAIL")
print("  3 liveness preserved after revert .............", "PASS" if not any('locked' in f or 'recovery' in f for f in fails) else "FAIL")
print("  4 replay continuity (deterministic cmdlog) ....", "PASS" if not any('deterministic' in f for f in fails) else "FAIL")
print("  VIOLATIONS:", len(fails))
for f in fails: print("   !", f)
sys.exit(1 if fails else 0)
