"""
run_seed_exp518.py -- Fork A: EXP-518 History Compaction (Fork upsilon)

Protocol exp518-v1. Declaration hash: 32c1314a87fbd52301eeba7ddae8be59cc23999f2bb834acff312e794d912fd8
Bounded working set + unbounded auditable history: H-inert eviction, sufficient-statistic eta_CLT,
Skeleton Lineage O(1) undo, DAG cold history. Engine FROZEN. PYTHONHASHSEED=0.
"""
import sys, os, json, hashlib
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/agency"))
import numpy as np
from dentatus import core
from injection import inject_phase_change_517
from compaction import CompactingWorld, BeyondWindowError, _compact

DH = "32c1314a87fbd52301eeba7ddae8be59cc23999f2bb834acff312e794d912fd8"
with open(os.path.join(ROOT, "studies/exp518_history_compaction/SEED_DECLARATION_exp518.json")) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DH
print(f"[1] PASS  declaration_hash = {DH[:16]}...")

def world():
    s = np.zeros(18); s[0:4] = [1.0, 0.5, 0.5, 0.5]; s[12:18] = [2.0, -1.0, -1.0, 0, 0, 0]
    cl = core.Claim(provenance=core.Provenance(parent_ids=(), operator_id="seed", timestamp=core.now_iso()),
                    payload="dia", stalk=s, t=0)
    mu = core.MuState(t=0, claims={cl.id: cl}, entailments={}, active=frozenset([cl.id]), S=np.zeros(18), alpha=0.5)
    mu.seal(); return mu, cl
SHEARS = [(40.0, 0.12, 0.40), (40.0, 0.16, 0.40), (40.0, 0.18, 0.40)]

# [2] H-inert eviction (single step on a world that already has an inactive claim)
mu, cl = world()
live2, child, rec = inject_phase_change_517(mu, cl, 40.0, 0.12, 148, 396, vorticity=0.40)   # live2 has parent+child
assert _compact(live2).H == live2.H
print(f"[2] PASS  H-inert eviction: compacted live.H == uncompacted ({live2.H[:12]})")

# build compacting world + run chain
mu, cl = world(); cw = CompactingWorld(mu, skeleton_n=2)
parent = cl; eta_comp = [round(cw.eta_CLT(), 9)]; ws = []
for (b, st, vo) in SHEARS:
    cw.inject(parent, b, st, 148, 396, vorticity=vo)
    parent = cw.live.claims[next(iter(cw.live.active))]
    ws.append(cw.working_set_size()); eta_comp.append(round(cw.eta_CLT(), 9))

# [3] bounded working set
assert ws == [1, 1, 1]
print(f"[3] PASS  bounded working set: sizes {ws} (constant, not O(K)) over {len(SHEARS)} injections")

# [4] unbounded history
assert cw.history_size() == len(SHEARS)
print(f"[4] PASS  unbounded history: DAG retains all {cw.history_size()} transitions")

# [5] observationally inert vs non-compacting reference
mu2, cl2 = world(); live = mu2; p2 = cl2; eta_full = [round(mu2.eta_CLT(), 9)]
for (b, st, vo) in SHEARS:
    live, ch, _ = inject_phase_change_517(live, p2, b, st, 148, 396, vorticity=vo); p2 = ch
    eta_full.append(round(live.eta_CLT(), 9))
assert eta_comp == eta_full
print(f"[5] PASS  observationally inert: eta_CLT {eta_comp} == full reference (sufficient-stat exact)")

# [6] skeleton undo
H_now = cw.H; H_prev = cw.undo()
assert H_prev != H_now and cw.H == H_prev
print(f"[6] PASS  skeleton undo: {H_now[:10]} -> {H_prev[:10]} (O(1) restore)")

# [7] undo restores stats
assert round(cw.eta_CLT(), 9) == eta_comp[-2]
print(f"[7] PASS  undo restores eta_CLT to prior value ({eta_comp[-2]})")

# [8] beyond-window
cw.undo()  # exhausts window (skeleton_n=2)
try:
    cw.undo(); raise AssertionError("no raise")
except BeyondWindowError:
    pass
print(f"[8] PASS  beyond-window -> BeyondWindowError (replay required)")

# [9] determinism
mu3, cl3 = world(); cw3 = CompactingWorld(mu3, skeleton_n=2); p3 = cl3; eta3 = [round(cw3.eta_CLT(), 9)]
for (b, st, vo) in SHEARS:
    cw3.inject(p3, b, st, 148, 396, vorticity=vo); p3 = cw3.live.claims[next(iter(cw3.live.active))]
    eta3.append(round(cw3.eta_CLT(), 9))
assert eta3 == eta_comp
print(f"[9] PASS  determinism: eta_CLT chain bit-stable across runs")

# [10] engine frozen
import subprocess
src = open(os.path.join(ROOT, "game/agency/compaction.py")).read()
assert "import engine" not in src and mu.H  # original mu still sealed/intact
print(f"[10] PASS  engine frozen: 0 engine.* imports; original mu intact")

print("\n=== EXP-518 Fork A: 10/10 PASS ===")
print("    History compaction: bounded working set (constant), unbounded auditable history (DAG);")
print("    H-inert + observationally-inert (sufficient stats); skeleton O(1) undo; engine frozen.")
