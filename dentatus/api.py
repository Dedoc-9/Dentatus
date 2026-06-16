"""
dentatus.api — L1 Stateless Reality API.

Pure functions: JSON-serializable dict in -> dict out. No global/server state; all evolving
state (SeedMemory) is caller-tracked and passed in/out. The engine is a stateless oracle.

The FIREWALL IS THE HANDSHAKE CONTRACT: a verified state hash (`H_verified`) is stamped only
when is_manifold_501 passes. A torn world receives observables but no verified hash, so the
game layer cannot obtain a verified universe that violates manifold continuity.
"""
import json
import hashlib
import numpy as np

from dentatus import core, semantic


def _build_seed_mu(declaration):
    stalk = np.asarray(declaration["seed_stalk"], float)
    lo, hi = declaration["bbox"]
    bbox = (np.asarray(lo, float), np.asarray(hi, float))
    prov = core.Provenance(parent_ids=(), operator_id="dentatus_api_seed", timestamp=core.now_iso())
    claim = core.Claim(provenance=prov, payload=declaration.get("title", "scene"),
                       stalk=stalk.copy(), t=0, bbox=bbox)
    mu = core.MuState(t=0, claims={claim.id: claim}, entailments={},
                      active=frozenset([claim.id]),
                      S=np.zeros(12), alpha=core.ALPHA_DEFAULT,
                      S_A=np.zeros(8), S_C=np.zeros(4), S_D=np.zeros(6))
    return mu, claim.id, bbox



def state_hash(mu, ndigits=12):
    """EXP-602: deterministic content address of the REALIZED state (not the recipe).

    H_state = SHA256(W (sorted claim ids) # Z (stalks) # S_A # S_C # S_D # protocol).
    Bit-stable because EXP-601 made claim ids, Z, and the carried ghosts bitwise
    reproducible. Rounded to `ndigits` decimals to absorb cross-platform libm ULP while
    remaining a unique address. This is H_t in the engine sense: HASH(Z # S # W # protocol).
    """
    W = sorted(mu.active)
    def r(arr):
        return [round(float(x), ndigits) for x in np.asarray(arr).ravel()]
    payload = json.dumps({
        "W": W,
        "Z": {cid: r(mu.claims[cid].stalk) for cid in W},
        "S_A": r(mu.S_A), "S_C": r(mu.S_C), "S_D": r(mu.S_D),
        "protocol": "dentatus-state-v1",
        "engine_protocol": core.ENGINE_PROTOCOL,
    }, sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()


def observe(request):
    """L1 /observe. Compile (if intent), partition, observe the manifold, gate the firewall.

    request: {"intent": {...}}  OR  {"declaration": {...}};  optional "steps" (default 8).
    returns: observables + firewall gate + Fiedler stability + verified hash (iff admissible).
    """
    if "declaration" in request:
        decl = request["declaration"]
    elif "intent" in request:
        decl = semantic.compile_intent(request["intent"])
    else:
        return {"error": "request must contain 'intent' or 'declaration'"}

    steps = int(request.get("steps", 8))
    B = np.asarray(decl.get("B", [1.0, 0.5, 0.3]), float)
    K_budget = int(decl.get("K_budget", 2048))
    focus = (np.asarray(decl["bbox"][0], float) + np.asarray(decl["bbox"][1], float)) / 2.0

    SHARED = dict(partition_key="octree_split", beta=1.0, budget=1e9, spent=0.0,
                  K_budget=K_budget, depth=0, focal_point=focus, B=B, J_AC=np.eye(4), W_max=8,
                  beta_Z_base=core._BETA_Z_313, gamma_inf_A=core._GAMMA_INF_A_409,
                  gamma_inf_D=core._GAMMA_INF_D_409, tau_warmup=core._TAU_WARMUP_409,
                  alpha_disc=core._ALPHA_DISC_409, alpha_maint=core._ALPHA_MAINT_409,
                  beta_threshold=core._BETA_THRESHOLD_409, beta_Z_min=core._BETA_Z_MIN_409,
                  gamma_inf_ent=core._GAMMA_INF_ENT_503)

    mu, cid, bbox = _build_seed_mu(decl)
    bze = float(core._BETA_Z_313); maint = False
    for n in range(steps):
        if n > 0:
            prov = core.Provenance(parent_ids=(), operator_id="dentatus_api_seed", timestamp=core.now_iso())
            claim = core.Claim(provenance=prov, payload=decl.get("title", "scene"),
                               stalk=np.asarray(decl["seed_stalk"], float).copy(), t=0, bbox=bbox)
            mu = core.MuState(t=0, claims={claim.id: claim}, entailments={}, active=frozenset([claim.id]),
                              S=np.zeros(12), alpha=core.ALPHA_DEFAULT,
                              S_A=np.array(mu.S_A), S_C=np.array(mu.S_C), S_D=np.array(mu.S_D))
            cid = claim.id
        out = core.apply_gamma_503_recursive(mu=mu, claim_id=cid, scene_n=n, bze_ema_prev=bze,
                                             maint_latched=maint, B_ent_spectral_prev=0.0, **SHARED)
        mu, bze, B_A, B_D, maint = out[0], out[3], out[5], out[6], out[12]

    Zc = {c: np.asarray(mu.claims[c].stalk, float) for c in mu.active}
    bx = {c: mu.claims[c].bbox for c in mu.active}
    g, S_ent, B_ent, N_edges, lam2, edges = core.phi_ent_observe(Zc, bx, {c: 0.0 for c in mu.active},
                                                                 degree_normalize=True)
    Bsp, lam_modes, fied, gsp = core.spectral_ent_project(g, edges, list(mu.active), Z_claims=Zc,
                                                          k_modes=core._K_FIEDLER_503)
    Zn = float(np.linalg.norm([np.linalg.norm(Zc[c]) for c in sorted(Zc)]))
    ok, worst_cid, worst_ratio = core.is_manifold_501_perclaim(g, Zn)
    # EXP-508 Citadel entropy firewall (dual gate): the realized fragments (N_f) + delta_0
    # gamma emissions (N_gamma = edges) must fit the energy budget E* = K_budget.
    cit = core.citadel_entropy_508(K_budget, len(mu.active), int(N_edges))
    citadel_ok = core.is_citadel_508(cit["dS_cit"])
    # DUAL FIREWALL: manifold-continuous AND citadel-admissible.
    admissible = bool(core.is_manifold_501(B_ent) and ok and citadel_ok)

    resp = {
        "protocol": "dentatus-api-v1",
        "H_decl": decl["declaration_hash"],
        "observables": {
            "B_A": round(float(B_A), 9), "B_D": round(float(B_D), 9),
            "B_ent": round(float(B_ent), 9), "B_ent_spectral": round(float(Bsp), 9),
            "lambda_2": round(float(lam2), 9),
            "n_leaves": len(mu.active), "n_edges": int(N_edges),
            "beta_Z_eff": round(float(bze), 9),
        },
        "firewall": {
            "is_manifold_501": bool(core.is_manifold_501(B_ent) and ok),
            "epsilon": core.FIREWALL_EPSILON,
            "worst_ratio": round(float(worst_ratio), 9),
        },
        "citadel": {
            "H_in": cit["H_in"], "H_out": cit["H_out"], "dS_cit": cit["dS_cit"],
            "N_f": cit["N_f"], "N_gamma": cit["N_gamma"],
            "is_citadel": citadel_ok, "K_budget": int(K_budget),
        },
        "admissible": admissible,
        "fiedler": {"lambda_2": round(float(lam2), 9), "n_modes": int(len(lam_modes))},
    }
    # EXP-602: H_state is the bit-stable content address of the REALIZED world (W,Z,S).
    H_state = state_hash(mu)
    resp["H_state"] = H_state

    # EXP-604: optional telemetry block — per-leaf geometry + Fiedler eigenvector + g_ent for
    # the MCL dashboard. Content-addressed by H_state: identical worlds -> identical telemetry,
    # so the expensive Fiedler decomposition is computed once per unique reality and cacheable.
    if request.get("telemetry"):
        ids_sorted = sorted(mu.active)
        fv = list(fied) if len(fied) == len(ids_sorted) else [0.0] * len(ids_sorted)
        leaves = []
        for i, cid in enumerate(ids_sorted):
            lo, hi = mu.claims[cid].bbox
            leaves.append({
                "center": [round(float((lo[k] + hi[k]) / 2.0), 6) for k in range(3)],
                "size": [round(float(hi[k] - lo[k]), 6) for k in range(3)],
                "fiedler": round(float(fv[i]), 6),
                "g_ent": round(float(g[cid]), 6),
            })
        resp["telemetry"] = {"H_state": H_state, "leaves": leaves,
                             "fiedler_lambda": round(float(lam2), 9), "n_leaves": len(leaves)}
    # FIREWALL = HANDSHAKE: a VERIFIED reality address is issued only when the manifold is
    # admissible. The address is the realized-state hash (a permanent, unique reality id),
    # not merely the recipe hash H_decl.
    resp["H_verified"] = H_state if admissible else None
    return resp
