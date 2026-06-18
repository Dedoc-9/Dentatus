"""
airlock/admissibility.py — the geometry of what ALMOST happened.

Most systems record only what happened. This membrane already records what *almost* happened — every
unrealized transition leaves a trace (rejection shards, proposal residuals R_p, shadow candidates). This
module makes those traces a FIRST-CLASS OBSERVABLE: it measures the *admissibility structure* a session
moved through.

Conceptual frame (a modeling lens, NOT a claim about nature):
    States  ⊂  Transitions  ⊂  Admissibility manifold
Reality is a trajectory through a continuously filtered space of candidate transitions. The filtering is
usually assumed invisible (nature instantiates lawful evolution directly, R_p≈0). In an agent-rich world —
humans, LLMs, planners — actors continuously propose trajectories only partially realized, so R_p ≠ 0 and
the filter itself becomes measurable. We call its magnitude PROPOSAL PRESSURE.

This is PURE TELEMETRY: it reads the ledger and computes; it never gates, never steers, never enters
identity (`telemetry ≠ control`). `integrity ≠ truth`: proposal pressure measures the filter's *shape*,
never whether the filter is *right*. Stdlib only.
"""


def geometry(ledger):
    """The admissibility geometry of a session's ledger. Exact-integer summaries (per-mille where a ratio).

    Returns:
      realized / unrealized / proposed  — committed vs rejected vs total proposals
      admissibility_permille            — realized·1000/proposed  (how much proposed history became real)
      proposal_pressure_permille        — unrealized·1000/proposed (how strongly the filter shaped history)
      gate_histogram                    — {gate: count} over rejections — the SHAPE of admissibility
      dominant_gate                     — where reality most filtered the proposals
      mean_Rp_commit                    — mean proposal residual of REALIZED transitions (the kept ghost)
    """
    nc = len(ledger.commits)
    nr = len(ledger.rejections)
    n = nc + nr
    hist = {}
    for s in ledger.rejections:
        g = s.get("gate", "?")
        hist[g] = hist.get(g, 0) + 1
    dominant = max(hist.items(), key=lambda kv: (kv[1], kv[0]))[0] if hist else None
    rps = [s["telemetry"].get("R_p") for s in ledger.commits
           if isinstance(s.get("telemetry"), dict) and isinstance(s["telemetry"].get("R_p"), int)]
    mean_rp = (sum(rps) // len(rps)) if rps else None
    return {
        "realized": nc, "unrealized": nr, "proposed": n,
        "admissibility_permille": (nc * 1000 // n) if n else None,
        "proposal_pressure_permille": (nr * 1000 // n) if n else None,
        "gate_histogram": hist,
        "dominant_gate": dominant,
        "mean_Rp_commit": mean_rp,
    }


def merge(*geometries):
    """Aggregate several session geometries (e.g. per region / per proposer) into one. Pure."""
    realized = sum(g["realized"] for g in geometries)
    unrealized = sum(g["unrealized"] for g in geometries)
    n = realized + unrealized
    hist = {}
    for g in geometries:
        for k, v in g["gate_histogram"].items():
            hist[k] = hist.get(k, 0) + v
    return {"realized": realized, "unrealized": unrealized, "proposed": n,
            "admissibility_permille": (realized * 1000 // n) if n else None,
            "proposal_pressure_permille": (unrealized * 1000 // n) if n else None,
            "gate_histogram": hist,
            "dominant_gate": max(hist.items(), key=lambda kv: (kv[1], kv[0]))[0] if hist else None,
            "mean_Rp_commit": None}
