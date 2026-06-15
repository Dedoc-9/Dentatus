"""
game/examples/docking_bay.py — a GAME-LAYER program (decoupled from the engine).

Clean Room rule: this file reaches the Physics Oracle ONLY through dentatus.api /
dentatus.semantic. It does NOT import engine.* and knows nothing of stalks, log-Cholesky,
or operators. It speaks physics (density, shear stress, curvature) and receives a verified
state hash. Game-specific mechanics (combat, economy, AI) live here, never in engine/.
"""
import os, sys
# In-repo bootstrap: production game code pip-installs `dentatus-core` and drops this block.
# This only puts the repo root (the dentatus package) on the path; it does NOT import engine.*.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dentatus import api   # L1 handshake only


def build_docking_bay():
    # Star-Wars-style docking bay: flat landing pad under high in-plane shear, sharp rim.
    intent = {
        "title": "imperial_docking_bay",
        "seed": {
            "density": 1.0,
            "material": [0.55, 0.57, 0.62],          # durasteel grey
            "normal": [0, 0, 1],                     # pad faces up
            "curvature": 2.0,                        # sharp rim
            "stress": {"axes": [3.0, 2.0, 0.4],      # long, wide, thin (flat pad)
                       "plane": "xy", "tilt_deg": 35},  # shear tilt on the pad
        },
        "bbox": [[0, 0, 0], [1, 1, 1]],
        "zeeman": {"focus": [0.5, 0.5, 0.0], "budget": 2048},  # attention on the pad
    }
    resp = api.observe({"op": "observe", "intent": intent, "steps": 8})
    return resp


if __name__ == "__main__":
    import json
    r = build_docking_bay()
    print(json.dumps(r, indent=2))
    if r.get("H_verified"):
        print(f"\nVERIFIED world H_t = {r['H_verified'][:16]}...  "
              f"(firewall passed: B_ent={r['observables']['B_ent']} < eps={r['firewall']['epsilon']})")
    else:
        print("\nREJECTED by manifold firewall — no verified hash issued (world is torn).")
