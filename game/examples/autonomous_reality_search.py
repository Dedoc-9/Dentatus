"""
game/examples/autonomous_reality_search.py — EXP-603 first Autonomous Reality Search.

An agent "prompts" a docking-bay world, then autonomously searches resolution space for the
most-continuous (lowest tectonic-stress) admissible realization, reading Ghost Observables and
the Firewall from the L1 API and emitting a witnessed audit trail. It terminates only when the
manifold firewall issues a non-null H_verified — the permanent address of the stable reality.

Run deterministically:  PYTHONHASHSEED=0 python game/examples/autonomous_reality_search.py
"""
import os, sys
os.environ.setdefault("PYTHONHASHSEED", "0")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))  # game/
from agency.loop import run_reality_search   # game-layer only; reaches core via dentatus.api

BASE_INTENT = {
    "title": "imperial_docking_bay",
    "seed": {"density": 1.0, "material": [0.55, 0.57, 0.62], "normal": [0, 0, 1],
             "curvature": 2.0, "stress": {"axes": [3.0, 2.0, 0.4], "plane": "xy", "tilt_deg": 35}},
    "bbox": [[0, 0, 0], [1, 1, 1]], "zeeman": {"focus": [0.5, 0.5, 0.0]},
}

if __name__ == "__main__":
    r = run_reality_search(BASE_INTENT, budget_ladder=[1024, 2048, 512, 256, 128, 64],
                           k_stable=3, max_iter=12)
    print(f"Autonomous Reality Search — '{BASE_INTENT['title']}'")
    print(f"  probes: {r['iterations']}   witnessed artifacts: {len(r['audit_trail'])}   witness_core: {r['witness_core']}")
    print(f"  tectonic-stress (B_ent) trajectory: {r['stress_trajectory']}")
    if r["success"]:
        red = r["stress_trajectory"][0] - r["stress_trajectory"][-1]
        o = r["final_observables"]
        print(f"  CONVERGED & LATCHED. stress reduced {r['stress_trajectory'][0]:.4f} -> "
              f"{r['stress_trajectory'][-1]:.4f} ({red:.4f}); final leaves={o['n_leaves']} lambda_2={o['lambda_2']}")
        print(f"  VERIFIED reality address  H_verified = {r['H_verified']}")
    else:
        print("  search did not reach a latched, firewall-admitted state — no H_verified issued.")
