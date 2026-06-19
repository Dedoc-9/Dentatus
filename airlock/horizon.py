"""
airlock/horizon.py — the geometry of the field of unrealized admissible alternatives.

`admissibility.py` counts `possible \\ admissible`; `possibility.py` counts `admissible \\ realized`. Counting
is not geometry. This module measures the SHAPE of the admissible-but-unrealized field SURROUNDING a realized
state: how far the lawful alternatives reach, how dispersed they are, and the total magnitude of the
could-have-been packed around what-was.

The deepest idea of the project, made measurable:
    reality is not only a trajectory through state space — it is a trajectory through a field of unrealized
    admissible alternatives, and the geometry of that field can itself be measured.

For physics: a rigorous observability framework over alternative lawful evolutions (`why this realization
instead of another admissible one?`). For games: the engine knows not just what happened but what could have
— a state's POSSIBILITY PRESSURE is the felt weight of the unrealized possibilities around it.

PURE telemetry: every alternative is computed in SHADOW (no commit; the world never advances). Distances use
the adapter's exact-integer `delta_norm`. Honest bound: this measures the geometry of the admissible field
*under the declared structure* (airlock + adapter + constraints + severity) — never that the structure is the
right one, and "pressure"/"aliveness" are magnitude metaphors, not claims about nature. `integrity ≠ truth`.
Stdlib only.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import possibility as PS


def neighborhood(world, realized_index, candidates, adapter, severity="game"):
    """Geometry of the admissible-but-unrealized field around the realized choice.

    Returns:
      alternatives          — number of admissible-but-unrealized lawful continuations
      distances             — {index: ‖outcome_alt − outcome_realized‖} (exact integer, per alternative)
      reach                 — max distance: how far the surrounding possibility extends
      mean_distance         — mean distance of the alternatives from what became real
      dispersion            — mean absolute deviation of the distances (how spread the field is)
      possibility_pressure  — Σ distances: total magnitude of the surrounding unrealized field
    """
    aset = PS.admissible_set(world, candidates, adapter, severity)
    if realized_index not in aset["admissible"]:
        raise ValueError("realized_index %r is not admissible at this state" % realized_index)
    realized_world = adapter.apply(world, candidates[realized_index]["transition"])
    dists = {}
    for i in aset["admissible"]:
        if i == realized_index:
            continue
        alt_world = adapter.apply(world, candidates[i]["transition"])
        dists[i] = adapter.delta_norm(realized_world, alt_world)
    ds = list(dists.values())
    n = len(ds)
    mean = sum(ds) // n if n else 0
    mad = (sum(abs(d - mean) for d in ds) // n) if n else 0
    return {
        "alternatives": n,
        "distances": dists,
        "reach": max(ds) if ds else 0,
        "mean_distance": mean,
        "dispersion": mad,
        "possibility_pressure": sum(ds),
        "admissible_total": len(aset["admissible"]),
    }
