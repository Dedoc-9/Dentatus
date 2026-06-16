"""
run_seed_exp516.py -- Fork A: EXP-516 Transition Log -> Provenance DAG (Fork omicron)

Protocol exp516-v1. Declaration hash: e028deae2adcaeb6126e399577835413a735594ddd3569b82271912553cdf85f
Phase changes threaded into the Claim provenance DAG as first-class lineage nodes. Engine FROZEN
(game-layer; dentatus.core Claim/Provenance only). PYTHONHASHSEED=0.
"""
import sys, os, json, hashlib
os.environ.setdefault("PYTHONHASHSEED", "0")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "game/agency"))
import numpy as np
from dentatus import core
from transition_dag import TransitionDAG

DH = "e028deae2adcaeb6126e399577835413a735594ddd3569b82271912553cdf85f"
with open(os.path.join(ROOT, "studies/exp516_transition_provenance_dag/SEED_DECLARATION_exp516.json")) as f:
    decl = json.load(f)
stored = decl.pop("declaration_hash")
assert stored == hashlib.sha256(json.dumps(decl, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == DH
print(f"[1] PASS  declaration_hash = {DH[:16]}...")

def stalk(l11, l22, l33, l21=0.0, l31=0.0, l32=0.0):
    s = np.zeros(18); s[12:18] = [l11, l22, l33, l21, l31, l32]; return s
def root_claim(sk, pid="seed:diamond"):
    return core.Claim(provenance=core.Provenance(parent_ids=(), operator_id=pid, timestamp=core.now_iso()),
                      payload="diamond_seed", stalk=sk, t=0)

dag = TransitionDAG(); diamond = root_claim(stalk(2.0, -1.0, -1.0)); dag.add_root(diamond)
c1, w1 = dag.record(diamond, 40.0, 0.12, 148, 396, vorticity=0.40)   # Wi=0.30
c2, w2 = dag.record(c1, 40.0, 0.16, 148, 396, vorticity=0.40)        # Wi=0.40

# [2] melted -> child Claim w/ provenance
assert c1.provenance.parent_ids == (diamond.id,) and c1.provenance.operator_id == "PhaseChange:minimal"
print(f"[2] PASS  melted -> child Claim {c1.id} provenance.parent_ids=({diamond.id},) op={c1.provenance.operator_id}")

# [3] deterministic / content-addressed (timestamp excluded, EXP-601)
dag_r = TransitionDAG(); dia_r = root_claim(stalk(2.0, -1.0, -1.0)); dag_r.add_root(dia_r)
c1_r, _ = dag_r.record(dia_r, 40.0, 0.12, 148, 396, vorticity=0.40)
assert c1_r.id == c1.id and dia_r.id == diamond.id
print(f"[3] PASS  child id content-addressed & deterministic (re-record -> {c1_r.id}, timestamp excluded)")

# [4] edge witness
e = dag.edges[0]
assert e["parent"] == diamond.id and e["child"] == c1.id and set(e["witness"]) >= {"chi_before", "chi_after", "t_star", "H_before", "H_after"}
print(f"[4] PASS  edge witnessed: chi {e['witness']['chi_before']:.3f}->{e['witness']['chi_after']:.3f}, t*={e['witness']['t_star']:.3f}")

# [5] multi-step ancestry + lineage
anc = dag.ancestry(c2.id)
assert anc == [diamond.id, c1.id, c2.id]
lin = dag.lineage(c2.id)
assert len(lin) == 2 and lin[0]["chi_before"] < lin[0]["chi_after"] <= lin[1]["chi_after"]
print(f"[5] PASS  ancestry diamond->glass->softer = {[a[:8] for a in anc]}; lineage chi {[ (round(l['chi_before'],2),round(l['chi_after'],2)) for l in lin]}")

# [6] stable -> no growth
n_before = (len(dag.nodes), len(dag.edges))
water = root_claim(stalk(0, 0, 0), pid="seed:water"); dag.add_root(water)
cs, ws = dag.record(water, 40.0, 0.12, 148, 396, vorticity=0.40)
assert cs is None and ws["status"] == "stable" and len(dag.edges) == n_before[1]
print(f"[6] PASS  stable -> no edge growth (water admits; record returns None)")

# [7] unsurvivable -> no edge
cu, wu = dag.record(diamond, 6.0, 0.40, 148, 396, vorticity=0.30)
assert cu is None and wu["status"] == "unsurvivable" and len(dag.edges) == n_before[1]
print(f"[7] PASS  unsurvivable -> no edge (chi_required>1; record returns None)")

# [8] child stalk/payload/t
assert not np.allclose(c1.stalk[12:18], diamond.stalk[12:18]) and c1.payload == w1["H_after"] and c1.t == diamond.t + 1
print(f"[8] PASS  child: Sector D melted, payload=H_after, t={c1.t}=parent+1")

# [9] append-only + serializable
d = dag.to_dict()
assert d["edges"][0]["parent"] == diamond.id and json.dumps(d, sort_keys=True)
assert dag.edges[0]["child"] == c1.id  # first edge unmutated after later records
print(f"[9] PASS  append-only + serializable: {len(d['nodes'])} nodes, {len(d['edges'])} edges; prior edges intact")

# [10] determinism of full DAG
c2_r, _ = dag_r.record(c1_r, 40.0, 0.16, 148, 396, vorticity=0.40)
assert c2_r.id == c2.id and dag_r.ancestry(c2_r.id) == anc
print(f"[10] PASS  full DAG deterministic (child ids + ancestry bit-stable)")

print("\n=== EXP-516 Fork A: 10/10 PASS ===")
print("    Phase changes are first-class Claim lineage: PhaseChange operator_id, content-addressed ids,")
print("    ancestry/time-travel, witnessed edges, append-only; engine frozen (core facade only).")
