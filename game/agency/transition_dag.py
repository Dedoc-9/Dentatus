"""
game/agency/transition_dag.py — EXP-516 Transition Log -> Provenance DAG (Fork omicron).

Phase changes (EXP-515) become FIRST-CLASS nodes in the world's provenance DAG: a melted manifold is
a genuine child Claim whose provenance points to the pre-melt Claim with operator_id
"PhaseChange:<mode>". Because Claim.id is content-addressed and timestamp-excluded (EXP-601), the
lineage is deterministic and cryptographically traceable -> historical auditing & time-travel.

Clean room: builds Claim/Provenance via dentatus.core ONLY (no engine.* import). Child payloads are the
P_yz-invariant material eigenvalue hash (EXP-515 witness), so the whole chain is reflection-invariant.
Engine stays FROZEN.
"""
import os, sys
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_REALITY = os.path.dirname(os.path.dirname(_HERE))
if _REALITY not in sys.path:
    sys.path.insert(0, _REALITY)
from dentatus import core as _core
from phase_change import enact_phase_change_515

PROTOCOL = "exp516-v1"


class TransitionDAG:
    """Append-only DAG of material phase transitions over the engine's Claim lineage.
    nodes: claim_id -> {t, chi, det, status, material_H, operator_id}
    edges: list of {parent, child, operator_id, witness}
    """

    def __init__(self):
        self.nodes = {}
        self.edges = []

    def add_root(self, claim):
        """Register an existing Claim as a lineage root (no incoming edge)."""
        self.nodes[claim.id] = {"t": int(claim.t), "operator_id": claim.provenance.operator_id,
                                "material_H": None, "chi": None, "det": None, "status": "root"}
        return claim.id

    def record(self, parent_claim, beta_Z, strain, n_fragments, n_gamma, *, mode="minimal", **kw):
        """Run a phase change on parent_claim.stalk; if it MELTS, append a child Claim + witnessed edge.
        Returns (child_claim_or_None, witness). Pure w.r.t. the engine; parent is never mutated."""
        new_stalk, w = enact_phase_change_515(parent_claim.stalk, beta_Z, strain,
                                              n_fragments, n_gamma, mode=mode, **kw)
        if parent_claim.id not in self.nodes:
            self.add_root(parent_claim)
        if w["status"] != "melted":
            return None, w                       # stable / unsurvivable -> no lineage growth
        op = "PhaseChange:%s" % mode
        prov = _core.Provenance(parent_ids=(parent_claim.id,), operator_id=op, timestamp=_core.now_iso())
        child = _core.Claim(provenance=prov, payload=w["H_after"], stalk=new_stalk, t=int(parent_claim.t) + 1)
        self.nodes[child.id] = {"t": int(child.t), "operator_id": op, "material_H": w["H_after"],
                                "chi": w["chi_after"], "det": w["det_after"], "status": "melted"}
        self.edges.append({"parent": parent_claim.id, "child": child.id, "operator_id": op, "witness": w})
        return child, w

    def parents_of(self, claim_id):
        return [e["parent"] for e in self.edges if e["child"] == claim_id]

    def ancestry(self, claim_id):
        """Walk the lineage back to a root. Returns [oldest ... claim_id] (deterministic, single-parent)."""
        chain = [claim_id]
        cur = claim_id
        while True:
            ps = self.parents_of(cur)
            if not ps:
                break
            cur = ps[0]
            chain.append(cur)
        return list(reversed(chain))

    def lineage(self, claim_id):
        """Witnessed transitions along the ancestry path (the 'how did this become this' record)."""
        anc = self.ancestry(claim_id)
        out = []
        for a, b in zip(anc, anc[1:]):
            e = next(e for e in self.edges if e["parent"] == a and e["child"] == b)
            out.append({"parent": a, "child": b, "operator_id": e["operator_id"],
                        "chi_before": e["witness"]["chi_before"], "chi_after": e["witness"]["chi_after"],
                        "t_star": e["witness"]["t_star"], "H_before": e["witness"]["H_before"],
                        "H_after": e["witness"]["H_after"]})
        return out

    def to_dict(self):
        return {"protocol": PROTOCOL, "nodes": self.nodes,
                "edges": [{"parent": e["parent"], "child": e["child"], "operator_id": e["operator_id"],
                           "chi_before": e["witness"]["chi_before"], "chi_after": e["witness"]["chi_after"],
                           "t_star": e["witness"]["t_star"]} for e in self.edges]}
