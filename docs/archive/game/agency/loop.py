"""
game/agency/loop.py — EXP-603 Agency Loop & Autonomous Reality Search.

An agent proposes Semantic Intent (L2), reads Ghost Observables (B_ent = manifold tension /
tectonic stress, B_ent_spectral, lambda_2) and the Firewall status (eps=0.8) from the L1 API,
and iterates toward a stable, admissible realization. An Agency Hysteresis Latch (lifted from
EXP-409) prevents outer-loop backreaction: H_verified is committed only when the accepted
tectonic-stress trajectory is monotone non-increasing AND the search has converged AND the
firewall admits the world (non-null H_verified) — "the teeth of truth".

Decoupled: imports dentatus.api only (never engine.*). Determinism requires PYTHONHASHSEED=0
(EXP-602 Ghost #32) for a bit-identical committed H_verified across runs.

Note (Ghost #34): Sector D stress is dual-only (not partition-inherited), so semantic stress
intent does not shape the realized geometry; B_ent_spectral ~ 0 for symmetric single worlds.
The operative, realizable tectonic-stress signal is B_ent (degree-normalized inter-claim
deformation), driven via the resolution budget. B_ent_spectral monotonicity is also enforced.
"""
import os
import sys

# --- L1 handshake (the ONLY engine access) ---
_HERE = os.path.dirname(os.path.abspath(__file__))
_REALITY = os.path.dirname(os.path.dirname(_HERE))
if _REALITY not in sys.path:
    sys.path.insert(0, _REALITY)
from dentatus import api, core   # dentatus.* contract only — no engine.* import

# --- optional witness emission (cross-project bridge; graceful if absent) ---
_MCL = os.path.join(os.path.dirname(_REALITY), "MCL_OBS2")
if _MCL not in sys.path:
    sys.path.insert(0, _MCL)
try:
    from witness_core import Artifact, WitnessViolation  # type: ignore
    _WITNESS = True
except Exception:
    _WITNESS = False


def _witness(data, certifies, claim_class="agency_iteration"):
    """Emit an executable-epistemics Witness Artifact (observable purity). data carries pure
    numerics + structural addresses only — no verdict-shaped fields. Falls back to a plain dict
    record if witness_core is unavailable."""
    forbidden = [
        "B_ent / B_ent_spectral are structural deformation ratios, not quality/health/correctness scores",
        "H_verified is a content address, not a semantic label or endorsement",
        "lower tectonic stress is not a value judgement that the world is 'better'",
        "the agency latch is a convergence control, not a truth claim about the world",
    ]
    prov = {"engine_protocol": core.ENGINE_PROTOCOL, "operator": "game.agency.loop (EXP-603)",
            "source_date_epoch": os.environ.get("SOURCE_DATE_EPOCH", "0"),
            "pythonhashseed": os.environ.get("PYTHONHASHSEED")}
    scope = {"certifies": certifies, "domain": "single-seed octree realization", "epsilon_manifold": 0.8}
    if _WITNESS:
        return Artifact(data=data, provenance=prov, claim_class=claim_class,
                        validity_scope=scope, forbidden_interpretations=forbidden)
    return {"data": data, "provenance": prov, "claim_class": claim_class,
            "validity_scope": scope, "forbidden_interpretations": forbidden, "witness_core": False}


class AgencyLatch:
    """Hysteresis latch for the agency outer loop (lifts EXP-409).

    Discovery: the agent explores, accepting only tectonic-stress-reducing proposals, so the
    accepted-stress trajectory is monotone non-increasing by construction.

    Maintenance latch engages IRREVERSIBLY when, for `k_stable` consecutive non-improving
    proposals (convergence), the accepted B_ent trajectory is monotone non-increasing AND
    B_ent_spectral is non-increasing AND the current world is firewall-admissible. Once latched
    the search commits; H_verified is issued only in the latched state.
    """

    def __init__(self, k_stable=2, eps_tol=1e-9):
        self.k_stable = int(k_stable)
        self.eps_tol = float(eps_tol)
        self.maint_latched = False
        self.no_improve_streak = 0
        self.accepted_stress = []      # B_ent of accepted states (monotone non-increasing)
        self.spectral_hist = []        # B_ent_spectral of accepted states

    def _monotone(self, seq):
        return all(seq[i + 1] <= seq[i] + self.eps_tol for i in range(len(seq) - 1))

    def on_accept(self, b_ent, b_ent_spectral):
        self.accepted_stress.append(float(b_ent))
        self.spectral_hist.append(float(b_ent_spectral))
        self.no_improve_streak = 0

    def on_reject(self):
        self.no_improve_streak += 1

    def update(self, firewall_ok):
        """Engage the irreversible maintenance latch on convergence + monotonicity + admissibility."""
        if self.maint_latched:
            return True
        converged = self.no_improve_streak >= self.k_stable
        mono = (len(self.accepted_stress) >= 1 and self._monotone(self.accepted_stress)
                and self._monotone(self.spectral_hist))
        if converged and mono and firewall_ok:
            self.maint_latched = True
        return self.maint_latched


def run_reality_search(base_intent, budget_ladder, k_stable=2, max_iter=12, steps=8, witness=True):
    """Autonomous Reality Search: descend the resolution budget to minimize tectonic stress
    (B_ent), committing H_verified only when the Agency Latch engages (monotone-settled +
    firewall-admitted). Returns a result dict with the committed reality address and the full
    witnessed audit trail (including rejected proposals).
    """
    latch = AgencyLatch(k_stable=k_stable)
    artifacts = []
    best_b_ent = float("inf")
    committed = None     # (intent, resp) of the accepted minimum
    it = 0
    for budget in budget_ladder:
        if it >= max_iter:
            break
        it += 1
        intent = {**base_intent, "zeeman": {**base_intent.get("zeeman", {}), "budget": int(budget)}}
        resp = api.observe({"op": "observe", "intent": intent, "steps": steps})
        o = resp["observables"]
        b_ent = float(o["B_ent"]); b_sp = float(o["B_ent_spectral"])
        fw_ok = bool(resp["firewall"]["is_manifold_501"]) and resp["H_verified"] is not None
        delta = b_ent - best_b_ent
        improved = fw_ok and (b_ent < best_b_ent - latch.eps_tol)
        if improved:
            best_b_ent = b_ent
            committed = (intent, resp)
            latch.on_accept(b_ent, b_sp)
        else:
            latch.on_reject()
        # Early convergence latch (EXP-409 style): k_stable consecutive non-improving probes.
        early = latch.update(firewall_ok=(committed is not None))
        data = {
            "iteration": it, "proposed_K_budget": int(budget),
            "B_ent": round(b_ent, 9), "B_ent_spectral": round(b_sp, 9),
            "lambda_2": round(float(o["lambda_2"]), 9),
            "worst_ratio": resp["firewall"]["worst_ratio"], "epsilon_manifold": resp["firewall"]["epsilon"],
            "n_leaves": o["n_leaves"], "n_edges": o["n_edges"],
            "delta_B_ent_vs_best": round(float(delta), 9),
            "stress_trajectory": [round(x, 9) for x in latch.accepted_stress],
            "stable_count": latch.no_improve_streak,
            "latch_maintenance_phase": 1 if latch.maint_latched else 0,
            "H_state": resp["H_state"], "H_verified": None,   # search phase: not yet committed
        }
        certifies = ("one manifold realization at proposed_K_budget; admissibility = "
                     "worst_ratio <= epsilon_manifold; H_verified committed only after the agency latch")
        artifacts.append(_witness(data, certifies) if witness else data)
        if early:
            break

    # Exhaustion latch: if exploration ended without early convergence, commit the global best
    # found provided the accepted tectonic-stress trajectory is monotone and the world is admitted.
    if (not latch.maint_latched) and committed is not None \
            and latch._monotone(latch.accepted_stress) and latch._monotone(latch.spectral_hist):
        latch.maint_latched = True

    success = bool(latch.maint_latched and committed is not None)
    if success:
        # final COMMIT artifact bearing the verified reality address (the teeth of truth)
        cr = committed[1]; co = cr["observables"]
        commit_data = {
            "iteration": it + 1, "committed_K_budget": int(committed[0]["zeeman"]["budget"]),
            "B_ent": round(float(co["B_ent"]), 9), "B_ent_spectral": round(float(co["B_ent_spectral"]), 9),
            "lambda_2": round(float(co["lambda_2"]), 9), "n_leaves": co["n_leaves"], "n_edges": co["n_edges"],
            "worst_ratio": cr["firewall"]["worst_ratio"], "epsilon_manifold": cr["firewall"]["epsilon"],
            "stress_trajectory": [round(x, 9) for x in latch.accepted_stress],
            "stress_reduction": round(latch.accepted_stress[0] - latch.accepted_stress[-1], 9) if latch.accepted_stress else 0.0,
            "H_state": cr["H_state"], "H_verified": cr["H_verified"],
        }
        artifacts.append(_witness(commit_data,
                          "committed bit-stable verified reality address; agency latch engaged on "
                          "monotone-settled tectonic stress; admitted by the manifold firewall",
                          claim_class="agency_commit") if witness else commit_data)
    return {
        "success": success,
        "H_verified": committed[1]["H_verified"] if (success and committed) else None,
        "final_B_ent": round(best_b_ent, 9) if committed else None,
        "final_observables": committed[1]["observables"] if committed else None,
        "stress_trajectory": [round(x, 9) for x in latch.accepted_stress],
        "iterations": it,
        "latched": latch.maint_latched,
        "audit_trail": artifacts,
        "witness_core": _WITNESS,
    }
