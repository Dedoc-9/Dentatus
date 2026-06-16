"""
game/observability/telemetry.py — content-addressed telemetry for the MCL dashboard (EXP-604).

Runs an Autonomous Reality Search (EXP-603) and exports a replay bundle: one telemetry frame per
probe (per-leaf geometry + Fiedler eigenvector + ghost observables + firewall), the stress
trajectory, and the committed verified address. Every frame is keyed by H_state, so identical
worlds share telemetry (the O(N^3) Fiedler decomposition is computed once per unique reality).
"""
import os, sys
os.environ.setdefault("PYTHONHASHSEED", "0")
_HERE = os.path.dirname(os.path.abspath(__file__))
_REALITY = os.path.dirname(os.path.dirname(_HERE))
for _p in (_REALITY, os.path.join(_REALITY, "game")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from dentatus import api, core   # dentatus.* contract only


def export_bundle(base_intent, budget_ladder, steps=8):
    """Return a content-addressed telemetry bundle (JSON-serializable) for the dashboard."""
    frames = []
    cache = {}                    # H_state -> telemetry  (content-addressed dedup)
    best = float("inf")
    accepted = []
    committed = None
    cache_hits = 0
    for budget in budget_ladder:
        intent = {**base_intent, "zeeman": {**base_intent.get("zeeman", {}), "budget": int(budget)}}
        r = api.observe({"op": "observe", "intent": intent, "steps": steps, "telemetry": True})
        o = r["observables"]; H = r["H_state"]
        if H in cache:
            tele = cache[H]; cache_hits += 1     # Fiedler decomposition reused (content address hit)
        else:
            tele = r["telemetry"]; cache[H] = tele
        b_ent = float(o["B_ent"])
        improved = (r["H_verified"] is not None) and (b_ent < best - 1e-9)
        if improved:
            best = b_ent; accepted.append(round(b_ent, 9)); committed = (budget, r, tele)
        frames.append({
            "K_budget": int(budget),
            "B_ent": round(b_ent, 9), "B_ent_spectral": round(float(o["B_ent_spectral"]), 9),
            "lambda_2": round(float(o["lambda_2"]), 9), "worst_ratio": r["firewall"]["worst_ratio"],
            "epsilon": r["firewall"]["epsilon"], "n_leaves": o["n_leaves"], "n_edges": o["n_edges"],
            "beta_Z_eff": round(float(o["beta_Z_eff"]), 6),
            "accepted": 1 if improved else 0,
            "dS_cit": r["citadel"]["dS_cit"], "H_in": r["citadel"]["H_in"],
            "H_out": r["citadel"]["H_out"], "K_budget": r["citadel"]["K_budget"],
            "H_state": H, "telemetry": tele,
        })
    return {
        "protocol": "mcl-telemetry-v1", "engine_protocol": core.ENGINE_PROTOCOL,
        "title": base_intent.get("title", "untitled"),
        "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
        "firewall_epsilon": 0.8,
        "stress_trajectory": accepted,
        "stress_reduction": round(accepted[0] - accepted[-1], 9) if len(accepted) >= 2 else 0.0,
        "committed_H_verified": committed[1]["H_verified"] if committed else None,
        "committed_K_budget": committed[0] if committed else None,
        "unique_states": len(cache), "frames_total": len(frames), "cache_hits": cache_hits,
        "frames": frames,
    }
