"""
game/agency/compaction.py — EXP-518 History Compaction (Fork upsilon).

"Garbage collection of reality": bounded live working set, unbounded auditable history.

After EXP-517 injections, inactive (former-material) claims accumulate in MuState.claims (Ghost #51).
Compaction EVICTS them from the live working set. Two correctness properties make this safe:
  (1) H-INERT: H_t = HASH(Z + S + W + t) depends only on ACTIVE claims, so evicting inactive claims
      leaves H_t bit-identical (the world's identity is unchanged by GC).
  (2) OBSERVATIONALLY INERT: the only observable that reads ALL claims is eta_CLT (grand mean). It is
      preserved EXACTLY by retaining sufficient statistics (sum/sumsq/count of evicted norms) instead
      of the claim objects -> bounded memory, exact observable.

Tiered memory (EXP-606 hot/cold):
  - SKELETON LINEAGE: a bounded deque of the last N (live mu, evict-stats) snapshots -> O(1) instant undo.
  - PROVENANCE DAG (EXP-516): hashes/witnesses of every transition -> unbounded cold history.
  - Look-back beyond the skeleton window requires DAG replay (Fork tau).

Clean room: core (MuState) + game.injection/transition_dag only; no engine.* import. Engine FROZEN.
"""
import os, sys
from collections import deque
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_REALITY = os.path.dirname(os.path.dirname(_HERE))
if _REALITY not in sys.path:
    sys.path.insert(0, _REALITY)
from dentatus import core as _core
from injection import inject_phase_change_517
from transition_dag import TransitionDAG

PROTOCOL = "exp518-v1"


class BeyondWindowError(Exception):
    """Undo requested past the skeleton window -> requires DAG replay (cold path)."""


def _compact(mu):
    """Return a MuState holding ONLY active claims. H_t is preserved (depends only on active)."""
    trimmed = {cid: mu.claims[cid] for cid in mu.active}
    out = _core.MuState(t=mu.t, claims=trimmed, entailments=mu.entailments, active=mu.active,
                        S=mu.S, alpha=mu.alpha, S_A=mu.S_A, S_C=mu.S_C, S_D=mu.S_D)
    out.seal()
    return out


class CompactingWorld:
    """Bounded-memory live world with unbounded auditable history."""

    def __init__(self, mu, skeleton_n=8, dag=None):
        if not mu._sealed:
            mu.seal()
        # seed evicted-claim sufficient stats from any non-active claims already present
        self._ev_sum = 0.0; self._ev_sumsq = 0.0; self._ev_n = 0
        for cid, cl in mu.claims.items():
            if cid not in mu.active:
                n = float(np.linalg.norm(cl.stalk)); self._ev_sum += n; self._ev_sumsq += n * n; self._ev_n += 1
        self.live = _compact(mu)
        self.skeleton = deque(maxlen=int(skeleton_n))
        self.dag = dag if dag is not None else TransitionDAG()
        self.skeleton_n = int(skeleton_n)

    # ---- sufficient-statistics observables (observationally inert) --------
    def eta_CLT(self):
        """eta_CLT over the FULL population (live active + evicted), via sufficient stats. Equals the
        value an un-compacted world would report (Fork A [5])."""
        act = [self.live.claims[c].stalk_norm() for c in self.live.active]
        if not act:
            return 0.0
        n_act = len(act); sum_act = float(np.sum(act))
        mu_hat = sum_act / n_act
        grand_n = n_act + self._ev_n
        mu_grand = (sum_act + self._ev_sum) / grand_n if grand_n else 0.0
        return float(np.sqrt(n_act) * (mu_hat - mu_grand))

    def working_set_size(self):
        return len(self.live.claims)            # == |active|, bounded

    def history_size(self):
        return len(self.dag.edges)              # transitions preserved (hashes) — unbounded

    @property
    def H(self):
        return self.live.H

    # ---- kinetic step: inject + compact + record -------------------------
    def inject(self, parent_claim, beta_Z, strain, n_fragments, n_gamma, **kw):
        """Inject a phase change, compact the result, snapshot for undo, record to the DAG.
        Returns the witness record. On stable/unsurvivable -> no state change."""
        new_mu, child, rec = inject_phase_change_517(self.live, parent_claim, beta_Z, strain,
                                                     n_fragments, n_gamma, **kw)
        if not rec.get("injected"):
            return rec
        # snapshot CURRENT live + stats for O(1) undo BEFORE mutating
        self.skeleton.append((self.live, (self._ev_sum, self._ev_sumsq, self._ev_n)))
        # evicted = claims in new_mu that are not active (the former parent)
        for cid, cl in new_mu.claims.items():
            if cid not in new_mu.active:
                nrm = float(np.linalg.norm(cl.stalk)); self._ev_sum += nrm; self._ev_sumsq += nrm * nrm; self._ev_n += 1
        self.live = _compact(new_mu)
        if parent_claim.id not in self.dag.nodes:
            self.dag.add_root(parent_claim)
        op = rec["operator_id"]
        prov = _core.Provenance(parent_ids=(parent_claim.id,), operator_id=op, timestamp=_core.now_iso())
        self.dag.nodes[child.id] = {"t": int(child.t), "operator_id": op, "material_H": rec["material_H_after"],
                                    "chi": rec["chi_after"], "det": None, "status": "melted"}
        self.dag.edges.append({"parent": parent_claim.id, "child": child.id, "operator_id": op,
                               "witness": {"chi_before": rec["chi_before"], "chi_after": rec["chi_after"],
                                           "t_star": rec["t_star"], "H_before": rec["material_H_before"],
                                           "H_after": rec["material_H_after"]}})
        return rec

    def undo(self):
        """O(1) restore of the previous live state from the Skeleton Lineage. Raises BeyondWindowError
        if the window is exhausted (cold look-back must replay from the DAG -- Fork tau)."""
        if not self.skeleton:
            raise BeyondWindowError("undo past skeleton window of %d; replay from provenance DAG required" % self.skeleton_n)
        mu_prev, (s, ss, n) = self.skeleton.pop()
        self.live = mu_prev
        self._ev_sum, self._ev_sumsq, self._ev_n = s, ss, n
        return self.live.H
