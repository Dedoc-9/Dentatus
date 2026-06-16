"""
forge/clamps.py — L1 commit-boundary property clamps (additive, non-normative).

Fail-closed runtime guards for the live L1 commit boundary. Each clamp is a pure predicate over an
operator's declared outputs; a violation raises ClampViolation so the boundary can revert to the last
valid hashed state (the engine's existing discipline). These clamps DO NOT edit the frozen core; they
are an external guard layer whose thresholds are the constitutional constants plus fuzz-mined bounds.

Discipline (Annex I): a clamp certifies INTEGRITY of a well-formed transition, never truth. It guarantees
the operator's outputs stay inside their declared envelope; it makes no claim about the world.
"""
CHI_MIN = 0.05          # CHI_MIN_514 — stiffest admissible material floor
CHI_MAX = 1.0
_FIN = float("inf")


class ClampViolation(Exception):
    """Raised at the L1 boundary when a well-formed transition leaves its declared envelope."""
    def __init__(self, clamp, detail):
        super().__init__("%s: %s" % (clamp, detail)); self.clamp = clamp; self.detail = detail


def _finite(x):
    return isinstance(x, (int, float)) and x == x and abs(x) != _FIN   # not NaN, not +/-inf


def clamp_chi(chi):
    """Material compliance must sit in [CHI_MIN, 1] (EXP-514)."""
    if not _finite(chi) or not (CHI_MIN - 1e-9 <= chi <= CHI_MAX + 1e-9):
        return False, "chi=%r outside [%g,%g]" % (chi, CHI_MIN, CHI_MAX)
    return True, "ok"


def clamp_bethe(bc):
    """Bethe-Citadel output envelope (EXP-509/512/514)."""
    f = bc.get("E_strain_frac")
    if not _finite(f) or not (-1e-9 <= f <= 1.0 + 1e-9):
        return False, "E_strain_frac=%r outside [0,1]" % (f,)
    if not _finite(bc.get("E_star_eff")) or bc["E_star_eff"] < -1e-9:
        return False, "E_star_eff=%r negative/non-finite" % (bc.get("E_star_eff"),)
    if bc.get("E_star_eff") > bc.get("E_star", _FIN) + 1e-6:
        return False, "E_star_eff>E_star (strain widened the window)"   # EXP-514: strain may only narrow
    if not _finite(bc.get("dS_cit")):
        return False, "dS_cit non-finite"
    if bc.get("H_out") is not None and bc["H_out"] < -1e-9:
        return False, "H_out negative"
    if not isinstance(bc.get("survivable_by_material"), bool):
        return False, "survivable_by_material not bool"
    c = bc.get("chi")
    if c is not None and not (CHI_MIN - 1e-9 <= c <= CHI_MAX + 1e-9):
        return False, "bethe.chi=%r outside [%g,1]" % (c, CHI_MIN)
    return True, "ok"


def clamp_hash_continuity(prev_H, new_H, advanced=True):
    """L1 commit must produce a well-formed hash and (when advancing) change it."""
    for nm, h in (("prev_H", prev_H), ("new_H", new_H)):
        if not isinstance(h, str) or len(h) < 8:
            return False, "%s malformed (%r)" % (nm, h)
    if advanced and new_H == prev_H:
        return False, "H did not advance on a committing transition"
    return True, "ok"


_CLAMPS = {"chi": clamp_chi, "bethe": clamp_bethe}


def assert_l1(name, value):
    """Fail-closed gate for the live boundary. Raises ClampViolation on breach; returns value on pass."""
    fn = _CLAMPS.get(name)
    if fn is None:
        raise ClampViolation(name, "no such clamp")
    ok, why = fn(value)
    if not ok:
        raise ClampViolation(name, why)
    return value
