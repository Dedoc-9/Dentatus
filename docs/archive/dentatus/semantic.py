"""
dentatus.semantic — L2 Semantic Compiler.

Deterministic map: physical-property intent (the LLM/game vocabulary) -> SEED_DECLARATION
(the engine's stalk schema). The game speaks physics; the compiler speaks stalk. No game
semantics leak into the engine: this layer only TARGETS the frozen schema in dentatus.core.

Sector D (anisotropic stress / shear) uses the exact inverse of cholesky_from_stalk_401,
verified to round-trip at machine precision (max|Sigma_engine - Sigma_target| ~ 1e-15).
"""
import json
import hashlib
import numpy as np

from dentatus import core   # oracle facade only — never engine.* directly


def _rot_in_plane(plane, deg):
    """Rotation matrix for an in-plane shear tilt (deg) in the named coordinate plane."""
    t = np.deg2rad(float(deg))
    c, s = np.cos(t), np.sin(t)
    if plane == "xy":
        return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    if plane == "xz":
        return np.array([[c, 0.0, -s], [0.0, 1.0, 0.0], [s, 0.0, c]])
    if plane == "yz":
        return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])
    raise ValueError(f"unknown plane {plane!r} (use xy|xz|yz)")


def sigma_from_semantics(axes, plane="xy", tilt_deg=0.0):
    """Physical stress intent -> target covariance Sigma* = R diag(axes^2) R^T (PD)."""
    R = _rot_in_plane(plane, tilt_deg)
    D = np.diag(np.asarray(axes, float) ** 2)
    return R @ D @ R.T


def stalk_D_from_sigma(Sigma):
    """INVERSE of core.cholesky_from_stalk_401: target Sigma -> Sector D [12:18] (log-Cholesky)."""
    L = np.linalg.cholesky(np.asarray(Sigma, float))   # lower-triangular, positive diagonal
    return np.array([np.log(L[0, 0]), np.log(L[1, 1]), np.log(L[2, 2]),
                     L[1, 0], L[2, 0], L[2, 1]])


def compile_stalk(props):
    """Compile one claim's physical properties -> a d=18 stalk (np.ndarray).

    props keys (all optional; sensible defaults):
        density:   float          -> A[0]
        material:  [r,g,b]         -> A[1:4]
        position:  [x,y,z]         -> B[4:7]   (w=B[7]=1 homogeneous)
        normal:    [nx,ny,nz]      -> C[8:11]  (unit-normalized)
        curvature: float           -> C[11]
        stress:    {axes:[s1,s2,s3], plane:"xy", tilt_deg:deg}  -> D[12:18]
    """
    s = np.zeros(core.STALK_DIM)
    s[0] = float(props.get("density", 1.0))
    mat = props.get("material", [1.0, 1.0, 1.0]); s[1:4] = np.asarray(mat, float)[:3]
    pos = props.get("position", [0.5, 0.5, 0.5]); s[4:7] = np.asarray(pos, float)[:3]
    s[7] = 1.0  # homogeneous coordinate w=1 (is_valid_b invariant)
    nrm = np.asarray(props.get("normal", [0.0, 0.0, 1.0]), float)[:3]
    n = np.linalg.norm(nrm); s[8:11] = nrm / n if n > 0 else np.array([0.0, 0.0, 1.0])
    s[11] = float(props.get("curvature", 0.0))
    st = props.get("stress")
    if st:
        Sigma = sigma_from_semantics(st.get("axes", [1.0, 1.0, 1.0]),
                                     st.get("plane", "xy"), st.get("tilt_deg", 0.0))
        s[12:18] = stalk_D_from_sigma(Sigma)
    # escape hatch: explicit raw sector override (logged power-user path)
    if "raw_stalk_override" in props:
        ov = props["raw_stalk_override"]
        for idx, val in ov.items():
            s[int(idx)] = float(val)
    return s


def compile_intent(intent):
    """Physical-property intent (dict) -> SEED_DECLARATION (dict) with deterministic hash.

    intent schema:
        {
          "title": str,
          "seed": { <claim props, see compile_stalk> },
          "bbox": [[lo_x,lo_y,lo_z],[hi_x,hi_y,hi_z]],     (default unit cube)
          "zeeman": {"focus":[x,y,z], "budget":int}        (attention field + budget)
        }

    Returns a JSON-serializable declaration with a content-addressed declaration_hash.
    Deterministic: identical intent -> identical declaration_hash (no wall-clock).
    """
    seed_props = intent.get("seed", {})
    stalk = compile_stalk(seed_props)
    bbox = intent.get("bbox", [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]])
    zeeman = intent.get("zeeman", {})
    focus = zeeman.get("focus", [0.5, 0.5, 0.5])
    budget = int(zeeman.get("budget", 2048))
    # B (Zeeman field) = unit vector from bbox center toward focus (attention direction)
    center = (np.asarray(bbox[0], float) + np.asarray(bbox[1], float)) / 2.0
    bvec = np.asarray(focus, float) - center
    bn = np.linalg.norm(bvec)
    B = (bvec / bn) if bn > 1e-12 else np.array([1.0, 0.5, 0.3]) / np.linalg.norm([1.0, 0.5, 0.3])

    decl = {
        "protocol": "dentatus-intent-v1",
        "engine_protocol": core.ENGINE_PROTOCOL,
        "title": intent.get("title", "untitled"),
        "seed_stalk": [round(float(x), 12) for x in stalk],
        "bbox": [[float(x) for x in bbox[0]], [float(x) for x in bbox[1]]],
        "B": [round(float(x), 12) for x in B],
        "K_budget": budget,
    }
    canon = json.dumps(decl, sort_keys=True, separators=(",", ":"))
    decl["declaration_hash"] = hashlib.sha256(canon.encode()).hexdigest()
    return decl
