"""
run_seed_exp520.py -- Fork A: EXP-520 Replay / Time-Travel Debugger (Fork tau)

Protocol exp520-v1. Declaration hash: 2e489550a816e08ee5d6ace0f4ac293fa059977c9109f15ee87e79604cbb2eb2
Event-sourced history: command log + sparse checkpoints reconstruct any historical mu, verified by H_t
match. Cold-restore beyond the EXP-518 skeleton window. Engine FROZEN. PYTHONHASHSEED=0.
"""
import sys, os, json, hashlib
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/agency"))
import numpy as np
from dentatus import core
from replay import TimeMachine, cold_restore, ReplayMismatch
from compaction import CompactingWorld, BeyondWindowError

DH = "2e489550a816e08ee5d6ace0f4ac293fa059977c9109f15ee87e79604cbb2eb2"
with open(os.path.join(ROOT, "studies/exp520_replay_debugger/SEED_DECLARATION_exp520.json")) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DH
print(f"[1] PASS  declaration_hash = {DH[:16]}...")

def diamond():
    s = np.zeros(18); s[0:4] = [1.0, 0.55, 0.57, 0.62]; s[12:18] = [2.0, -1.0, -1.0, 0, 0, 0]
    cl = core.Claim(provenance=core.Provenance(parent_ids=(), operator_id="seed", timestamp=core.now_iso()),
                    payload="dia", stalk=s, t=0)
    mu = core.MuState(t=0, claims={cl.id: cl}, entailments={}, active=frozenset([cl.id]), S=np.zeros(18), alpha=0.5)
    mu.seal(); return mu
DRIVE = [(40.0, 0.12 + 0.012 * i, 0.40) for i in range(16)]

def build_tm(ce=4):
    tm = TimeMachine(diamond(), checkpoint_every=ce); chain = [tm.live.H]
    for (b, st, vo) in DRIVE:
        if tm.step(b, st, 148, 396, vorticity=vo).get("injected"): chain.append(tm.live.H)
    return tm, chain
tm, chain = build_tm()

# [2] capture
assert len(tm.commands) >= 4 and 0 in tm.checkpoints and 4 in tm.checkpoints
print(f"[2] PASS  capture: {len(tm.commands)} commands, checkpoints at {sorted(tm.checkpoints)}")

# [3] exact reconstruction of a mid-history state
target = chain[5]
mu, info = tm.reconstruct(target)
assert mu.H == target
print(f"[3] PASS  reconstruct seq{info['target_seq']}: mu.H == target ({target[:12]})")

# [4] verified replay end-to-end
n = tm.verify_history()
assert n == len(tm.commands)
print(f"[4] PASS  verify_history: all {n} recorded H reproduced (end-to-end determinism)")

# [5] checkpoint efficiency
assert info["from_checkpoint"] == 4 and info["steps_replayed"] < info["target_seq"]
print(f"[5] PASS  checkpoint efficiency: replayed {info['steps_replayed']} from seq {info['from_checkpoint']} (< target {info['target_seq']})")

# [6] genesis + latest
g, _ = tm.reconstruct(0); l, _ = tm.reconstruct(tm.live.H)
assert g.H == chain[0] and l.H == tm.live.H
print(f"[6] PASS  reconstruct genesis -> root; latest -> live")

# [7] tamper detection
tm_t, _ = build_tm(); tm_t.commands[3]["result_H"] = "deadbeef" * 8
try:
    tm_t.verify_history(); raise AssertionError("no raise")
except ReplayMismatch:
    pass
print(f"[7] PASS  tamper detection: corrupted recorded H -> ReplayMismatch")

# [8] COLD RESTORE beyond the skeleton window
cw = CompactingWorld(diamond(), skeleton_n=2); cwH = [cw.H]
for (b, st, vo) in DRIVE:
    p = cw.live.claims[next(iter(cw.live.active))]
    rec = cw.inject(p, b, st, 148, 396, vorticity=vo)
    if rec.get("injected"): cwH.append(cw.H)
cw.undo(); cw.undo()                       # exhaust skeleton_n=2
try:
    cw.undo(); raise AssertionError("window not exhausted")
except BeyondWindowError:
    pass
old_H = cwH[1]                              # an early state the skeleton can no longer reach
restored, info2 = cold_restore(tm, old_H)  # tm journaled the identical drive (H-inert: same chain)
assert restored.H == old_H and info2["cold_restore"]
print(f"[8] PASS  cold restore: BeyondWindowError state {old_H[:12]} reconstructed from DAG+checkpoint")

# [9] seq vs H agree
by_seq, _ = tm.reconstruct(5); by_H, _ = tm.reconstruct(chain[5])
assert by_seq.H == by_H.H
print(f"[9] PASS  reconstruct by seq == by H string")

# [10] determinism
a, _ = tm.reconstruct(target); b, _ = tm.reconstruct(target)
assert a.H == b.H
print(f"[10] PASS  reconstruct deterministic")

print("\n=== EXP-520 Fork A: 10/10 PASS ===")
print("    Time machine: event-sourced command log + sparse checkpoints reconstruct any historical mu,")
print("    VERIFIED by H_t match (tamper-evident); BeyondWindowError -> cold restore; engine frozen.")
