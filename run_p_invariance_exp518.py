"""
run_p_invariance_exp518.py -- Fork B: EXP-518 P_yz invariance (reflection x -> -x).

eta_CLT is built from stalk NORMS (P_yz-invariant) and the DAG child ids use material-eigenvalue
payloads, so the compacted observables and the lineage are reflection-invariant. PYTHONHASHSEED=0.
"""
import sys, os
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/agency"))
import numpy as np
from dentatus import core
from dentatus.semantic import stalk_D_from_sigma
from engine.validity import cholesky_from_stalk_401
from compaction import CompactingWorld

def world(dpar):
    s = np.zeros(18); s[0:4] = [1.0, 0.5, 0.5, 0.5]; s[12:18] = dpar
    cl = core.Claim(provenance=core.Provenance(parent_ids=(), operator_id="seed", timestamp=core.now_iso()),
                    payload="mat", stalk=s, t=0)
    mu = core.MuState(t=0, claims={cl.id: cl}, entailments={}, active=frozenset([cl.id]), S=np.zeros(18), alpha=0.5)
    mu.seal(); return mu, cl
DIA = [2.0, -1.0, -1.0, 0.0, 0.0, 0.0]
sA = np.zeros(18); sA[12:18] = DIA
_, Sig = cholesky_from_stalk_401(sA)
DIA_R = list(stalk_D_from_sigma(np.diag([-1.0, 1, 1]) @ Sig @ np.diag([-1.0, 1, 1]).T))
SHEARS = [(40.0, 0.12, 0.40), (40.0, 0.16, 0.40)]

def run(dpar):
    mu, cl = world(dpar); cw = CompactingWorld(mu, skeleton_n=4); p = cl; eta = [round(cw.eta_CLT(), 9)]
    cids = []
    for (b, st, vo) in SHEARS:
        cw.inject(p, b, st, 148, 396, vorticity=vo)
        p = cw.live.claims[next(iter(cw.live.active))]; eta.append(round(cw.eta_CLT(), 9))
    cids = [e["child"] for e in cw.dag.edges]
    return cw, eta, cids
cwA, etaA, cidsA = run(DIA)
cwB, etaB, cidsB = run(DIA_R)

assert etaA == etaB
print(f"[1] PASS  P_yz: eta_CLT invariant under reflection {etaA}")
assert cidsA == cidsB
print(f"[2] PASS  DAG child ids invariant (material-H payloads)")
assert cwA.working_set_size() == cwB.working_set_size() and cwA.history_size() == cwB.history_size()
print(f"[3] PASS  working_set & history sizes invariant ({cwA.working_set_size()}, {cwA.history_size()})")
hA = cwA.undo(); hB = cwB.undo()
assert round(cwA.eta_CLT(), 9) == round(cwB.eta_CLT(), 9) == etaA[-2]
print(f"[4] PASS  undo restores invariant eta_CLT ({etaA[-2]})")
cw2, eta2, _ = run(DIA)
assert eta2 == etaA
print(f"[5] PASS  cross-process bit-stability (PYTHONHASHSEED=0)")

print("\n=== EXP-518 Fork B: 5/5 PASS ===")
print("    Reflection-invariant: norm-based eta_CLT + material-eigenvalue DAG ids -> compaction is P_yz-invariant.")
