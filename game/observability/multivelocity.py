"""
game/observability/multivelocity.py — EXP-510 Multi-Velocity Section Tracking (Ghost #40).

PROBLEM (Ghost #40). engine.operators.track_correspondence_505 keys every claim in ONE world
frame offset by a single cumulative_motion vector. That presumes the world translates as a rigid
body. When sections move at DIFFERENT velocities (a fleet dispersing, a galaxy shearing, a non-
rigid actor), one global offset cannot hold every section's keys stable: matched-track counts
collapse and the stitched Fiedler fault tears at the moving seams.

MODEL (formal). State variables, operators, transformations only.
  Forward (geometry, OBSERVED — never mutated by the dual channel):
    leaves_t            : list[ {center:(3,), size:(3,)} ]              (engine telemetry)
    so_t, C_t[s]        : section_of_leaf, section centroid             (assign_sections, observed)
    field_t             : stitched Fiedler per leaf                     (sectioned_fiedler)
  Dual (kinematics, RESIDUAL — reported, never fed back as control):
    v_s                 : per-section velocity                          EMA of observed displacement
    Ĉ_s = C_s^prev + v_s·dt   : predicted section centroid               (correspondence only)
    G_s = C_s^match − Ĉ_s     : kinematic ghost (Ghost #44 residual)
    Skin_s              : EMA(G_s)                                       (observable only)

OPERATOR ORDER (stateless, declared I/O):  μ(leaves) → SEC(assign) → PRED(Ĉ) → ASSOC(greedy gate)
  → VEL(EMA v) → GHOST(G,Skin) → OBS(R, match, Φ_fault, ||Skin||) .  No stage mutates forward
  geometry from the dual channel (backreaction firewall: prediction informs CORRESPONDENCE, never
  leaf positions). Section assignment runs on OBSERVED centers each frame, so the Fiedler operator
  never sees a velocity-displaced world — forward/dual orthogonality (dual arithmetic separation).

P_yz. Under x→−x: center.x, v.x, Ĉ.x, G.x all flip sign; speeds ||v||, ||Skin||, the rigidity
ratio R, match/birth/death counts and the size-multiset are invariant. The structural hash is
built only from these invariants (consistent with track_dag_hash_505 / Ghost #27).

Decoupled (Clean Room): imports sectioned_fiedler + dentatus.core only; never engine.*.
"""
import os, sys, hashlib
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from sectioned_fiedler import build_adjacency, assign_sections, stitched_fiedler

# --- engine constants (fixed; not leaf-count-scaled, consistent with EXP-509 substrate-mass rule)
VEL_EMA_ALPHA = 0.5     # velocity smoothing  v <- a*v + (1-a)*observed
GHOST_EMA_ALPHA = 0.5   # Skin <- a*Skin + (1-a)*G    (Ghost #44 accumulation; reported only)
GATE_K = 1.5            # association gate = GATE_K * section spacing
NDIGITS = 6             # bit-stability rounding
PROTOCOL = "exp510-v1"
EPS = 1e-12


def _r(x):
    return round(float(x), NDIGITS)


def _rt(v):
    return tuple(_r(x) for x in v)


def section_centroids(leaves, grid=(2, 2, 2)):
    """μ → SEC. OBSERVED section centroids (no prediction). Returns dict[sid_tuple -> centroid]."""
    ctr = np.array([l["center"] for l in leaves], float)
    # use the RAW octant key (not the compacted index) so identity is position-addressed
    sid = [tuple(min(grid[d] - 1, int(ctr[i, d] * grid[d])) for d in range(3))
           for i in range(len(leaves))]
    out = {}
    for s in sorted(set(sid)):
        m = np.array([ctr[i] for i in range(len(leaves)) if sid[i] == s])
        out[s] = _rt(m.mean(axis=0))
    return out, sid


def _spacing(centroids):
    """Median nearest-neighbour centroid distance -> association gate scale (deterministic)."""
    pts = np.array(list(centroids.values()), float)
    if len(pts) < 2:
        return 1.0
    d = np.sqrt(((pts[:, None, :] - pts[None, :, :]) ** 2).sum(-1))
    np.fill_diagonal(d, np.inf)
    return float(np.median(d.min(axis=1)))


def init_state():
    return {"tracks": {}, "next_id": 0, "frame": 0}


def step(state, leaves, grid=(2, 2, 2), dt=1.0,
         alpha_v=VEL_EMA_ALPHA, alpha_g=GHOST_EMA_ALPHA, gate_k=GATE_K):
    """One forward+dual frame. PRED → ASSOC → VEL → GHOST. Pure: returns (new_state, record).

    new_state.tracks[id] = {centroid, v, Skin, age, last_seen}
    record = deterministic per-frame kinematic observables (see observables()).
    """
    tracks = {int(k): {kk: (tuple(vv) if isinstance(vv, (list, tuple)) else vv)
                       for kk, vv in t.items()} for k, t in state["tracks"].items()}
    next_id = int(state["next_id"])
    cur, _sid = section_centroids(leaves, grid)
    cur_keys = sorted(cur.keys())                      # deterministic order
    gate = gate_k * _spacing(cur) if cur else 1.0

    # PRED: predicted centroid per existing track  Ĉ = C_prev + v*dt
    pred = {tid: tuple(_r(t["centroid"][d] + t["v"][d] * dt) for d in range(3))
            for tid, t in tracks.items()}

    # ASSOC: greedy nearest within gate. Deterministic: iterate sections by octant key, candidate
    # tracks ranked by (rounded distance, track id). One-to-one.
    used = set()
    assign = {}        # section_key -> track_id
    for sk in cur_keys:
        c = cur[sk]
        best = None
        cand = []
        for tid, p in pred.items():
            if tid in used:
                continue
            dist = _r(np.sqrt(sum((c[d] - p[d]) ** 2 for d in range(3))))
            if dist <= gate:
                cand.append((dist, tid))
        if cand:
            cand.sort()
            best = cand[0][1]
            used.add(best)
            assign[sk] = best

    # VEL + GHOST: update matched tracks; birth unmatched sections; mark deaths.
    new_tracks = {}
    matched = 0
    births = 0
    G_norms = []
    speeds = []
    vels = []
    for sk in cur_keys:
        c = cur[sk]
        if sk in assign:
            tid = assign[sk]
            t = tracks[tid]
            obs_v = tuple(_r((c[d] - t["centroid"][d]) / dt) for d in range(3))   # observed displ.
            v = tuple(_r(alpha_v * t["v"][d] + (1 - alpha_v) * obs_v[d]) for d in range(3))
            g = tuple(_r(c[d] - pred[tid][d]) for d in range(3))                  # Ghost #44 resid.
            skin = tuple(_r(alpha_g * t["Skin"][d] + (1 - alpha_g) * g[d]) for d in range(3))
            new_tracks[tid] = {"centroid": c, "v": v, "Skin": skin,
                               "age": int(t["age"]) + 1, "last_seen": int(state["frame"]) + 1}
            matched += 1
            G_norms.append(_r(np.sqrt(sum(x * x for x in g))))
        else:
            tid = next_id
            next_id += 1
            new_tracks[tid] = {"centroid": c, "v": (0.0, 0.0, 0.0), "Skin": (0.0, 0.0, 0.0),
                               "age": 1, "last_seen": int(state["frame"]) + 1}
            births += 1
            G_norms.append(0.0)
        vels.append(new_tracks[tid]["v"])
        speeds.append(_r(np.sqrt(sum(x * x for x in new_tracks[tid]["v"]))))

    deaths = sum(1 for tid in tracks if tid not in used)
    new_state = {"tracks": new_tracks, "next_id": int(next_id), "frame": int(state["frame"]) + 1}

    V = np.array(vels, float) if vels else np.zeros((0, 3))
    mean_v = V.mean(axis=0) if len(V) else np.zeros(3)
    mean_speed = float(np.mean(speeds)) if speeds else 0.0
    R = _r(np.linalg.norm(mean_v) / (mean_speed + EPS)) if mean_speed > 0 else 1.0
    rec = {
        "frame": new_state["frame"],
        "n_sections": len(cur_keys),
        "matched": matched, "births": births, "deaths": deaths,
        "match_rate": _r(matched / max(len(cur_keys), 1)),
        "rigidity_R": R,                       # 1 = rigid, ->0 = differential / non-rigid
        "nonrigidity": _r(1.0 - R),
        "mean_speed": _r(mean_speed),
        "ghost_kin_mean": _r(np.mean(G_norms)) if G_norms else 0.0,
        "skin_norm_total": _r(np.sqrt(sum(sum(x * x for x in t["Skin"]) for t in new_tracks.values()))),
        "speeds": [float(s) for s in speeds],
        "section_keys": [list(k) for k in cur_keys],
    }
    kd = kinematic_decomposition(new_state)
    rec["strain"] = kd["strain"]      # TRUE non-rigidity (deformation)
    rec["vorticity"] = kd["vort"]     # rotation (rigid)
    rec["divergence"] = kd["div"]     # expansion/contraction
    rec["translation"] = kd["trans"]  # bulk drift
    return new_state, rec


def fault_continuity(prev_field, prev_sid, curr_field, curr_sid):
    """Φ_fault: fraction of OCTANT-stable leaf positions whose stitched Fiedler SIGN persists
    frame-to-frame. Pure observable; uses sign(field) at matched octant cells. No interpretation.
    """
    # group leaf field by octant key -> mean sign per cell
    def cellsign(field, sid):
        cells = {}
        for i, k in enumerate(sid):
            cells.setdefault(k, []).append(field[i])
        return {k: (1 if np.mean(v) >= 0 else -1) for k, v in cells.items()}
    a = cellsign(prev_field, prev_sid)
    b = cellsign(curr_field, curr_sid)
    common = sorted(set(a) & set(b))
    if not common:
        return 1.0
    # global sign gauge is arbitrary; align by majority then measure persistence
    agree = sum(1 for k in common if a[k] == b[k])
    agree = max(agree, len(common) - agree)         # sign-flip-invariant alignment
    return _r(agree / len(common))


def kinematic_decomposition(state):
    """Helmholtz/Cauchy split of the section velocity field. Fit v(x) ~ v0 + L(x-xbar) by least
    squares over section centroids; L = STRAIN (sym) + VORTICITY (antisym).
        rigid motion (translation+rotation) => ||strain|| = 0
        true non-rigid deformation          => ||strain|| > 0   (this is what tears the fault)
    Observables (pure scalars, P_yz-invariant Frobenius norms):
        trans  = ||v0||         (bulk translation)
        vort   = ||Omega||_F    (rotation rate; rigid)
        strain = ||Sym||_F      (deformation rate; TRUE non-rigidity)
        div    = tr(L)          (expansion/contraction rate)
    NOTE (mindfulness on coarse-graining): L is a property of the section centroids — a coarse
    sampling of the continuum field. Its boundaries are model constructs; refine the grid and L
    converges to the local velocity gradient. div is reported separately because a uniform
    expansion is non-rigid yet structurally benign (isotropic), unlike anisotropic shear.
    """
    ts = state["tracks"]
    if len(ts) < 4:
        return {"trans": 0.0, "vort": 0.0, "strain": 0.0, "div": 0.0}
    X = np.array([t["centroid"] for t in ts.values()], float)
    Vv = np.array([t["v"] for t in ts.values()], float)
    xbar = X.mean(axis=0)
    A = np.hstack([np.ones((len(X), 1)), X - xbar])          # [1 | (x-xbar)]
    coef, *_ = np.linalg.lstsq(A, Vv, rcond=None)            # rows: v0 ; columns map to each v-comp
    v0 = coef[0]
    L = coef[1:].T                                           # 3x3 velocity gradient  dv_i/dx_j
    Sym = 0.5 * (L + L.T)
    Omega = 0.5 * (L - L.T)
    return {"trans": _r(np.linalg.norm(v0)),
            "vort": _r(np.linalg.norm(Omega)),
            "strain": _r(np.linalg.norm(Sym)),
            "div": _r(np.trace(L))}


def multivelocity_hash(record, protocol=PROTOCOL):
    """P_yz-invariant structural index. Built only from invariants: counts + SORTED speed multiset
    + scalar observables. Velocity DIRECTIONS (signed x) are excluded (consistent w/ Ghost #27)."""
    speeds = sorted(f"{s:.{NDIGITS}f}" for s in record["speeds"])
    parts = [
        f"frame={record['frame']}", f"sections={record['n_sections']}",
        f"matched={record['matched']}", f"births={record['births']}", f"deaths={record['deaths']}",
        f"R={record['rigidity_R']:.{NDIGITS}f}", f"ms={record['mean_speed']:.{NDIGITS}f}",
        f"skin={record['skin_norm_total']:.{NDIGITS}f}",
        f"strain={record.get('strain',0.0):.{NDIGITS}f}", f"vort={record.get('vorticity',0.0):.{NDIGITS}f}",
        "speeds=" + ";".join(speeds), f"pv={protocol}",
    ]
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


def run(frames, grid=(2, 2, 2), dt=1.0):
    """Drive a sequence of leaf-frames. Returns (final_state, [records], [hashes], [fields,sids])."""
    st = init_state()
    recs, hashes, fields = [], [], []
    prev_field = prev_sid = None
    for leaves in frames:
        st, rec = step(st, leaves, grid, dt)
        sf = stitched_fiedler(leaves, grid)
        _, sid = section_centroids(leaves, grid)
        if prev_field is not None:
            rec["fault_continuity"] = fault_continuity(prev_field, prev_sid, sf["field"], sid)
        else:
            rec["fault_continuity"] = 1.0
        prev_field, prev_sid = sf["field"], sid
        recs.append(rec)
        hashes.append(multivelocity_hash(rec))
        fields.append((sf["field"], sid))
    return st, recs, hashes, fields
