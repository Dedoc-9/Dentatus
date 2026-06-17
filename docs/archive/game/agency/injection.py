"""
game/agency/injection.py — EXP-517 Live MuState Injection (Fork rho).

Closes the audit-vs-live gap (Ghost #50): a phase change is injected into the RUNNING world, advancing
the engine H_t chain continuously (H_before -> H_after) so the Lineage IS the State.

Concurrency / "Interference" (the solid-intent-on-fluid-world hazard) is resolved by OPTIMISTIC
CONCURRENCY CONTROL on the content-addressed hash: every actor stamps the H it read; an injection is a
compare-and-swap on H, and an intent pulse whose basis_H != current H is STALE and rejected -> the
Agency must rebase (re-read the fluid world) and retry. No locks; the hash is the truth.

Clean room: core (MuState/Claim/Provenance) + game.phase_change only; no engine.* import. Engine FROZEN.
"""
import os, sys
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_REALITY = os.path.dirname(os.path.dirname(_HERE))
if _REALITY not in sys.path:
    sys.path.insert(0, _REALITY)
from dentatus import core as _core
from phase_change import enact_phase_change_515

PROTOCOL = "exp517-v1"


class StaleStateError(Exception):
    """Raised when an actor's basis hash no longer matches the live world (Interference)."""


def _seal(t, claims, entailments, active, S, alpha, S_A, S_C, S_D):
    mu = _core.MuState(t=t, claims=claims, entailments=entailments, active=active,
                       S=S, alpha=alpha, S_A=S_A, S_C=S_C, S_D=S_D)
    mu.seal()
    return mu


def inject_phase_change_517(mu, parent_claim, beta_Z, strain, n_fragments, n_gamma, *,
                            vorticity=None, dt=None, mode="minimal", expected_H=None):
    """CAS-guarded live injection. Returns (new_mu, child_claim, record).
    On 'stable'/'unsurvivable' -> (mu, None, record) (no state change).
    expected_H: if given and != mu.H -> StaleStateError (a concurrent writer advanced the world)."""
    if not mu._sealed:
        mu.seal()
    if expected_H is not None and mu.H != expected_H:
        raise StaleStateError("inject CAS failed: expected %s, live %s" % (expected_H[:12], mu.H[:12]))
    if parent_claim.id not in mu.active:
        raise ValueError("parent_claim is not an active leaf of the live world")

    new_stalk, w = enact_phase_change_515(parent_claim.stalk, beta_Z, strain, n_fragments, n_gamma,
                                          vorticity=vorticity, dt=dt, mode=mode)
    rec = {"protocol": PROTOCOL, "status": w["status"], "H_engine_before": mu.H,
           "material_H_before": w["H_before"], "material_H_after": w["H_after"],
           "chi_before": w["chi_before"], "chi_after": w["chi_after"], "t_star": w["t_star"]}
    if w["status"] != "melted":
        rec.update({"H_engine_after": mu.H, "child_id": None, "injected": False})
        return mu, None, rec

    op = "PhaseChange:%s" % mode
    prov = _core.Provenance(parent_ids=(parent_claim.id,), operator_id=op, timestamp=_core.now_iso())
    child = _core.Claim(provenance=prov, payload=w["H_after"], stalk=new_stalk, t=int(mu.t) + 1)
    new_claims = {**mu.claims, child.id: child}
    new_active = (set(mu.active) - {parent_claim.id}) | {child.id}
    new_active = frozenset(new_active)

    # accumulate the INJECTION GHOST (Ghost #51): re-declaration changes Z; S accumulates its residual
    tmp = _core.MuState(t=int(mu.t) + 1, claims=new_claims, entailments=mu.entailments,
                        active=new_active, S=mu.S, alpha=mu.alpha,
                        S_A=mu.S_A, S_C=mu.S_C, S_D=mu.S_D)
    S_new = tmp.next_S()
    new_mu = _seal(int(mu.t) + 1, new_claims, mu.entailments, new_active, S_new, mu.alpha,
                   mu.S_A, mu.S_C, mu.S_D)

    dZ = float(np.linalg.norm(new_mu.Z() - mu.Z()))
    rec.update({"H_engine_after": new_mu.H, "child_id": child.id, "parent_id": parent_claim.id,
                "operator_id": op, "dZ_norm": round(dZ, 9), "injected": True})
    return new_mu, child, rec


# --------------------------------------------------------------------------- #
# Optimistic-concurrency intent reconciliation (Interference resolution)
# --------------------------------------------------------------------------- #

def make_intent(mu, **payload):
    """Stamp an intent pulse with the H it was computed against (its basis)."""
    if not mu._sealed:
        mu.seal()
    return {"basis_H": mu.H, **payload}


def apply_intent_517(mu, intent, *, raise_on_stale=False):
    """Apply an intent pulse under optimistic concurrency. If intent.basis_H != mu.H the pulse was
    computed against a SUPERSEDED world (e.g. a solid that has since melted) -> rejected as stale.
    Returns a record; raises StaleStateError if raise_on_stale and stale."""
    if not mu._sealed:
        mu.seal()
    basis = intent.get("basis_H")
    if basis != mu.H:
        if raise_on_stale:
            raise StaleStateError("stale intent: basis %s != live %s" % (str(basis)[:12], mu.H[:12]))
        return {"accepted": False, "reason": "stale_basis", "basis_H": basis, "live_H": mu.H}
    return {"accepted": True, "live_H": mu.H, "intent": {k: v for k, v in intent.items() if k != "basis_H"}}


def rebase_intent(mu, stale_intent):
    """Re-stamp a stale intent against the current live world (the Agency's required response to a
    rejected pulse). The PAYLOAD is unchanged; only the basis is refreshed -> caller must recompute
    any state-dependent fields against the new material before resubmitting."""
    payload = {k: v for k, v in stale_intent.items() if k != "basis_H"}
    return make_intent(mu, **payload)
