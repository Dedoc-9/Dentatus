"""
validity.py -- Validity predicates for EXP-301 through EXP-304.

E-301-003 (corrected):
  Original predicate lambda_min(L_F) > 0 is incorrect for directed DAGs.
  For a connected consistent sheaf, lambda_min(L_F) = 0 always (zero mode =
  constant global section = the valid case). Strict positivity rejects every
  valid connected state.

CORRECTED PREDICATE -- Forward Entailment Consistency (is_valid):
  is_valid(mu_t) iff for every edge (u->v) in E_t:
    - Single-source (PARTITION): F(u->v)(stalk_u) ~= stalk_v
    - Multi-source  (SYNTHESIS): sum_i F(u_i->v)(stalk_{u_i}) ~= stalk_v

EXP-303: is_spatially_valid -- bbox containment on SPATIAL edges.

EXP-304: is_valid_b -- Sector B barycentric constraint and w=1 invariant.
"""
from __future__ import annotations
from collections import defaultdict
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from engine.state import MuState

CONSISTENCY_TOL = 1e-8
LAMBDA_MIN_THRESHOLD = 0.0  # retained for observability only


def build_coboundary(mu):
    """delta: prod F(v) -> prod F(e),  (delta x)_e = F(u->v)(x_u) - x_v"""
    claims = mu.claims
    entailments = mu.entailments
    if not entailments or not claims:
        return np.zeros((1, 1))
    node_ids = sorted(claims.keys())
    node_off = {}
    offset = 0
    for cid in node_ids:
        node_off[cid] = offset
        offset += claims[cid].stalk.shape[0]
    total_node_dim = offset
    edge_keys = list(entailments.keys())
    edge_off = {}
    offset = 0
    for e in edge_keys:
        edge_off[e] = offset
        offset += entailments[e].restriction.shape[0]
    total_edge_dim = offset
    if total_node_dim == 0 or total_edge_dim == 0:
        return np.zeros((1, 1))
    delta = np.zeros((total_edge_dim, total_node_dim))
    for (src, tgt), ent in entailments.items():
        e_o   = edge_off[(src, tgt)]
        e_d   = ent.restriction.shape[0]
        src_o = node_off[src]
        src_d = claims[src].stalk.shape[0]
        tgt_o = node_off[tgt]
        tgt_d = claims[tgt].stalk.shape[0]
        delta[e_o:e_o+e_d, src_o:src_o+src_d] += ent.restriction
        size = min(e_d, tgt_d)
        delta[e_o:e_o+size, tgt_o:tgt_o+size] -= np.eye(size)
    return delta


def sheaf_laplacian(mu):
    """L_F = delta^T delta  (PSD by construction; observable only, not the validity gate)."""
    d = build_coboundary(mu)
    return d.T @ d


def lambda_min(mu):
    """
    Minimum eigenvalue of L_F. Observable metric only (not is_valid gate after E-301-003).
    Clamped to 0.0 since L_F is PSD by construction; negative values are numerical noise.
    """
    if not mu.entailments:
        return 0.0
    L = sheaf_laplacian(mu)
    if L.shape == (1, 1):
        return max(float(L[0, 0]), 0.0)
    try:
        return max(float(np.min(np.linalg.eigvalsh(L))), 0.0)
    except np.linalg.LinAlgError:
        return -1.0


def is_valid(mu):
    """
    Forward entailment consistency check (E-301-003).

    For each target node v in E_t:
      PARTITION edge (single source u):
        ||F(u->v)(stalk_u) - stalk_v|| < CONSISTENCY_TOL
      SYNTHESIS edge (multiple sources u_i):
        ||sum_i F(u_i->v)(stalk_{u_i}) - stalk_v|| < CONSISTENCY_TOL

    Empty graph: trivially valid.
    """
    if not mu.entailments:
        return True

    incoming = defaultdict(list)
    for (src, tgt), ent in mu.entailments.items():
        incoming[tgt].append((src, ent))

    for tgt_id, edges in incoming.items():
        stalk_tgt = mu.claims[tgt_id].stalk
        predicted = sum(
            ent.restriction @ mu.claims[src_id].stalk
            for src_id, ent in edges
        )
        if np.linalg.norm(predicted - stalk_tgt) > CONSISTENCY_TOL:
            return False

    return True


def delta_lambda_min(mu_prev, mu_next):
    """Observable: change in lambda_min across a state transition."""
    return lambda_min(mu_next) - lambda_min(mu_prev)


# ---------------------------------------------------------------------------
# Sector B validity -- EXP-304
# ---------------------------------------------------------------------------

def is_valid_b(mu, sector_B_dims=(4, 5, 6, 7), tol=1e-8) -> bool:
    """
    Sector B validity predicate (EXP-304).

    For every claim with stalk dimension >= 8:
      1. Homogeneous invariant: stalk[7] == 1.0  (w = 1, tol=1e-10)

    For every PARTITION entailment with omega != None (Phi_B edges):
      2. Barycentric check (per parent):
           sum_i omega_i * stalk_B(child_i) == stalk_B(parent)  (tol)

    Empty graph or no Phi_B edges: trivially valid.
    """
    from engine.state import EntailmentType
    W_TOL = 1e-10
    b0 = sector_B_dims[0]
    b1 = sector_B_dims[-1] + 1    # slice [4:8]
    w_dim = sector_B_dims[-1]     # dim index of homogeneous coordinate

    if not mu.entailments:
        # Still check w=1 on all claims
        for cid, claim in mu.claims.items():
            if claim.stalk.shape[0] > w_dim:
                if abs(float(claim.stalk[w_dim]) - 1.0) > W_TOL:
                    return False
        return True

    # 1. Homogeneous invariant on every claim with Sector B slice
    for cid, claim in mu.claims.items():
        if claim.stalk.shape[0] > w_dim:
            w = float(claim.stalk[w_dim])
            if abs(w - 1.0) > W_TOL:
                return False

    # 2. Barycentric: group Phi_B children by parent
    phi_b_children = defaultdict(list)  # parent_id -> [(child_stalk_B, omega)]
    for (src_id, tgt_id), ent in mu.entailments.items():
        if ent.etype != EntailmentType.PARTITION or ent.omega is None:
            continue
        child_stalk_B = mu.claims[tgt_id].stalk[b0:b1]
        phi_b_children[src_id].append((child_stalk_B, ent.omega))

    for parent_id, children in phi_b_children.items():
        parent_stalk_B = mu.claims[parent_id].stalk[b0:b1]
        weighted_sum = sum(omega * stalk_B for stalk_B, omega in children)
        if np.linalg.norm(weighted_sum - parent_stalk_B) > tol:
            return False

    return True


# ---------------------------------------------------------------------------
# Spatial validity -- EXP-303
# ---------------------------------------------------------------------------

def is_spatially_valid(mu) -> bool:
    """
    Spatial bounding-box containment check (EXP-303).
    For every SPATIAL entailment (src -> tgt):
      bbox(tgt) subset bbox(src): lo_src <= lo_tgt and hi_tgt <= hi_src
      (component-wise, tolerance 1e-10)
    Returns True if no SPATIAL entailments exist or all satisfy containment.
    Skips edges where either endpoint has bbox=None.
    """
    from engine.state import EntailmentType
    TOL = 1e-10
    for (src_id, tgt_id), ent in mu.entailments.items():
        if ent.etype != EntailmentType.SPATIAL:
            continue
        parent = mu.claims[src_id]
        child  = mu.claims[tgt_id]
        if parent.bbox is None or child.bbox is None:
            continue
        p_lo, p_hi = parent.bbox
        c_lo, c_hi = child.bbox
        if not (np.all(c_lo >= p_lo - TOL) and np.all(c_hi <= p_hi + TOL)):
            return False
    return True


# ---------------------------------------------------------------------------
# Sector C validity -- EXP-305
# ---------------------------------------------------------------------------

def is_unit_norm(mu, sector_C_dims=(8, 9, 10), tol=1e-8) -> bool:
    """
    Sector C unit-norm predicate (EXP-305).
    For every claim with stalk dimension >= 11:
      | ||stalk[8:11]||_2 - 1.0 | < tol
    Trivially true for claims with d < 11.
    """
    c0 = sector_C_dims[0]
    c1 = sector_C_dims[-1] + 1
    for cid, claim in mu.claims.items():
        if claim.stalk.shape[0] >= c1:
            n = float(np.linalg.norm(claim.stalk[c0:c1]))
            if abs(n - 1.0) > tol:
                return False
    return True


def is_valid_block_diagonal(mu, tol=1e-7) -> bool:
    """
    Block-diagonal restriction map predicate (EXP-305).
    For each PARTITION or SPATIAL entailment with F shape (11, 11):
      Sector A (0:4), B (4:8), C (8:11) off-diagonal cross blocks near-zero.
    Skips entailments with restriction shape != (11, 11).
    Returns True if no qualifying entailments exist.
    """
    from engine.state import EntailmentType
    for (src_id, tgt_id), ent in mu.entailments.items():
        if ent.etype not in (EntailmentType.PARTITION, EntailmentType.SPATIAL):
            continue
        F = ent.restriction
        if F.shape != (11, 11):
            continue
        if np.linalg.norm(F[0:4, 4:11]) > tol:
            return False
        if np.linalg.norm(F[4:8, 0:4]) > tol:
            return False
        if np.linalg.norm(F[4:8, 8:11]) > tol:
            return False
        if np.linalg.norm(F[8:11, 0:8]) > tol:
            return False
    return True


def is_valid_block_diagonal_306(mu, tol=1e-7) -> bool:
    """
    Block-diagonal restriction map predicate for EXP-306 (d=12) / EXP-401 (d=18).
    Sector boundaries: A=[0:4], B=[4:8], C=[8:12], D=[12:18] (EXP-401 only)
    Off-diagonal cross blocks must be near-zero.
    Also handles d=11 (delegates to is_valid_block_diagonal).
    Skips F with shape other than (11,11), (12,12), or (18,18).
    EXP-401: Sector D (log-Cholesky) is tracked via S_D EMA, not partition-inherited.
      Child claims have stalk[12:18]=0, so F[12:18,:] must be zero (satisfied by
      np.zeros construction in apply_gamma_312). Block D cross-terms checked here.
    """
    from engine.state import EntailmentType
    for (src_id, tgt_id), ent in mu.entailments.items():
        if ent.etype not in (EntailmentType.PARTITION, EntailmentType.SPATIAL):
            continue
        F = ent.restriction
        if F.shape == (11, 11):
            # delegate to EXP-305 check
            if np.linalg.norm(F[0:4, 4:11]) > tol:
                return False
            if np.linalg.norm(F[4:8, 0:4]) > tol:
                return False
            if np.linalg.norm(F[4:8, 8:11]) > tol:
                return False
            if np.linalg.norm(F[8:11, 0:8]) > tol:
                return False
        elif F.shape == (12, 12):
            if np.linalg.norm(F[0:4, 4:12]) > tol:
                return False
            if np.linalg.norm(F[4:8, 0:4]) > tol:
                return False
            if np.linalg.norm(F[4:8, 8:12]) > tol:
                return False
            if np.linalg.norm(F[8:12, 0:8]) > tol:
                return False
        elif F.shape == (18, 18):
            # EXP-401: check ABC block off-diagonals; Sector D rows/cols must be zero
            if np.linalg.norm(F[0:4, 4:12]) > tol:
                return False
            if np.linalg.norm(F[4:8, 0:4]) > tol:
                return False
            if np.linalg.norm(F[4:8, 8:12]) > tol:
                return False
            if np.linalg.norm(F[8:12, 0:8]) > tol:
                return False
            # Sector D cross-terms (rows 12:18 touching ABC columns, and vice versa)
            if np.linalg.norm(F[12:18, 0:12]) > tol:
                return False
            if np.linalg.norm(F[0:12, 12:18]) > tol:
                return False
        # else: skip non-matching shapes
    return True


# ---------------------------------------------------------------------------
# kappa geometric validity -- EXP-307
# ---------------------------------------------------------------------------

KAPPA_MAX = 1e9   # clamp for degenerate (zero-extent) bbox dims

def kappa_from_bbox(bbox, kappa_max=KAPPA_MAX):
    """
    kappa = tr(H_bbox) = sum_i (2 / extent_i)
    extent_i = hi[i] - lo[i]
    Degenerate: extent < 1e-12 -> contribute kappa_max to sum.
    """
    lo, hi = bbox
    total = 0.0
    for i in range(len(lo)):
        e = float(hi[i] - lo[i])
        if e < 1e-12:
            total += kappa_max
        else:
            total += 2.0 / e
    return total


def is_valid_kappa(mu, kappa_dim=11, tol=1e-8) -> bool:
    """
    Shape operator trace predicate (EXP-307).

    For every claim with stalk.shape[0] > kappa_dim AND bbox not None:
      kappa_geom = kappa_from_bbox(claim.bbox)
      | stalk[kappa_dim] - kappa_geom | < tol

    Claims without bbox or with stalk dim <= kappa_dim: skipped.
    Empty graph: trivially valid.
    """
    for cid, claim in mu.claims.items():
        if claim.stalk.shape[0] <= kappa_dim:
            continue
        if claim.bbox is None:
            continue
        kappa_geom = kappa_from_bbox(claim.bbox)
        kappa_stalk = float(claim.stalk[kappa_dim])
        if abs(kappa_stalk - kappa_geom) > tol:
            return False
    return True


# ---------------------------------------------------------------------------
# Integral curvature validity -- EXP-308
# ---------------------------------------------------------------------------

EPS_REL = 1e-9   # relative regularization floor for bbox extents (EXP-308 rev)
# floor = max(lx_raw, ly_raw, lz_raw) * EPS_REL applied per-axis independently.
# Rationale: abs floor 1e-6 and relative floor give identical results for all
# normal extents >= 1e-3; relative floor is strictly correct for degenerate
# extents < 1e-7 where abs floor would over-clamp relative to bbox scale.


def kappa_integral(bbox, eps_rel=EPS_REL):
    """
    kappa = 2*(ly*lz/lx + lx*lz/ly + lx*ly/lz) / (lx*ly + ly*lz + lx*lz)

    Area-weighted mean curvature integral over rectangular bbox surface.
    Each face pair contributes face_area * (2/extent_perpendicular).
    Regularized: eps = max(lx,ly,lz) * eps_rel; each li = max(li, eps).

    For unit cube: kappa = 2.0
    For uniform octant [0,0.5]^3: kappa = 4.0
    """
    lo, hi = bbox
    lx_raw = float(hi[0] - lo[0])
    ly_raw = float(hi[1] - lo[1])
    lz_raw = float(hi[2] - lo[2])
    eps = max(lx_raw, ly_raw, lz_raw) * eps_rel
    lx = max(lx_raw, eps)
    ly = max(ly_raw, eps)
    lz = max(lz_raw, eps)
    num = 2.0 * (ly * lz / lx + lx * lz / ly + lx * ly / lz)
    den = lx * ly + ly * lz + lx * lz
    return num / den


def is_valid_kappa_308(mu, kappa_dim=11, tol=1e-8) -> bool:
    """
    Integral curvature predicate (EXP-308).

    For every claim with stalk.shape[0] > kappa_dim AND bbox not None:
      kappa_geom = kappa_integral(claim.bbox)
      | stalk[kappa_dim] - kappa_geom | < tol

    Claims without bbox are skipped.
    Returns True if no qualifying claims exist.
    """
    for cid, claim in mu.claims.items():
        if claim.stalk.shape[0] > kappa_dim and claim.bbox is not None:
            kappa_geom = kappa_integral(claim.bbox)
            if abs(float(claim.stalk[kappa_dim]) - kappa_geom) > tol:
                return False
    return True


# ---------------------------------------------------------------------------
# LOD Observer validity -- EXP-309
# ---------------------------------------------------------------------------

LOD_EPS       = 1e-12   # distance floor for LOD computation
LOD_THRESHOLDS_309 = {
    "is_valid_kappa_308": 0.05,   # bypass when bbox > 20x its size from focal
    "is_unit_norm":       0.10,   # bypass when bbox > 10x its size from focal
    "is_spatially_valid": 0.01,   # bypass at extreme distance (100x)
}
NON_BYPASSABLE_309 = frozenset([
    "is_valid",
    "is_valid_b",
    "is_valid_block_diagonal_306",
])
BYPASSABLE_309 = frozenset(LOD_THRESHOLDS_309.keys())


def lod_value(bbox, focal_point, eps=LOD_EPS) -> float:
    """
    LOD(bbox, f) = max(lx,ly,lz) / (||centroid(bbox) - f||_2 + eps)

    Returns float >= 0. Approaches inf as bbox centroid -> focal_point.
    P_yz invariant: LOD(mirror_bbox, mirror_f) = LOD(fwd_bbox, fwd_f) exactly.
    """
    lo, hi = bbox
    lx = float(hi[0] - lo[0]); ly = float(hi[1] - lo[1]); lz = float(hi[2] - lo[2])
    l = max(lx, ly, lz)
    c = (np.array(lo, dtype=float) + np.array(hi, dtype=float)) / 2.0
    dist = float(np.linalg.norm(c - np.asarray(focal_point, dtype=float)))
    return l / (dist + eps)


def lod_bypass_set(bbox, focal_point,
                   thresholds=None) -> frozenset:
    """
    Return frozenset of predicate names to bypass for this claim given focal_point.
    A predicate is bypassed when LOD(bbox, focal_point) < threshold[predicate].
    """
    if thresholds is None:
        thresholds = LOD_THRESHOLDS_309
    lod = lod_value(bbox, focal_point)
    return frozenset(p for p, tau in thresholds.items() if lod < tau)


def is_lod_valid_309(mu, focal_point, thresholds=None):
    """
    Synchronous Predicate Relaxation Tier (SPRT) validity check.

    Returns (bool, validity_class) where validity_class in
    {'FULL_VALID', 'LOD_RELAXED', 'INVALID'}.

    FULL_VALID:   all 6 predicates pass; no bypasses active.
    LOD_RELAXED:  non-bypassed predicates pass; >=1 predicate bypassed.
    INVALID:      any NON_BYPASSABLE predicate fails.

    NON_BYPASSABLE are checked globally (whole mu):
        is_valid, is_valid_b, is_valid_block_diagonal_306

    Per-claim checks (bypassable):
        is_valid_kappa_308, is_unit_norm, is_spatially_valid
    """
    import numpy as _np
    if thresholds is None:
        thresholds = LOD_THRESHOLDS_309

    # --- Non-bypassable global checks ---
    if not is_valid(mu):
        return False, 'INVALID'
    if not is_valid_b(mu):
        return False, 'INVALID'
    if not is_valid_block_diagonal_306(mu):
        return False, 'INVALID'

    any_bypass = False

    for cid, claim in mu.claims.items():
        if claim.bbox is None:
            continue
        bypass = lod_bypass_set(claim.bbox, focal_point, thresholds)
        if bypass:
            any_bypass = True

        # is_unit_norm per claim
        if "is_unit_norm" not in bypass:
            if claim.stalk.shape[0] >= 11:
                n = claim.stalk[8:11]
                if abs(float(_np.linalg.norm(n)) - 1.0) > 1e-6:
                    return False, 'INVALID'

        # is_valid_kappa_308 per claim
        if "is_valid_kappa_308" not in bypass:
            if claim.stalk.shape[0] > 11:
                kappa_geom = kappa_integral(claim.bbox)
                if abs(float(claim.stalk[11]) - kappa_geom) > 1e-8:
                    return False, 'INVALID'

    # is_spatially_valid: global; bypass only if ALL active claims have it bypassed
    all_spatial_bypassed = all(
        "is_spatially_valid" in lod_bypass_set(
            mu.claims[c].bbox, focal_point, thresholds)
        for c in mu.active
        if mu.claims[c].bbox is not None
    )
    if not all_spatial_bypassed:
        if not is_spatially_valid(mu):
            return False, 'INVALID'

    return True, ('LOD_RELAXED' if any_bypass else 'FULL_VALID')


def bypass_registry_309(mu, focal_point, thresholds=None) -> dict:
    """
    Compute per-claim bypass sets for all claims with bboxes.
    Returns Dict[claim_id -> frozenset[predicate_name]].
    """
    if thresholds is None:
        thresholds = LOD_THRESHOLDS_309
    return {
        cid: lod_bypass_set(claim.bbox, focal_point, thresholds)
        for cid, claim in mu.claims.items()
        if claim.bbox is not None
    }


# ===========================================================================
# EXP-401 -- Anisotropic Gaussian Covariance validity predicate
# Sector D: stalk[12:18] = [log_l11, log_l22, log_l33, l21, l31, l32]
# Cholesky factor L: lower-triangular, positive diagonal via exp(log_lii).
# Positive-definiteness guaranteed by log-Cholesky construction.
# ===========================================================================

import numpy as _np401


def cholesky_from_stalk_401(stalk):
    """
    Reconstruct lower-triangular Cholesky factor L from Sector D stalk[12:18].

    stalk[12] = log_l11  => L[0,0] = exp(stalk[12])  (l11 > 0 always)
    stalk[13] = log_l22  => L[1,1] = exp(stalk[13])  (l22 > 0 always)
    stalk[14] = log_l33  => L[2,2] = exp(stalk[14])  (l33 > 0 always)
    stalk[15] = l21      => L[1,0] = stalk[15]        (unconstrained)
    stalk[16] = l31      => L[2,0] = stalk[16]        (unconstrained)
    stalk[17] = l32      => L[2,1] = stalk[17]        (unconstrained)

    Returns (L, Sigma) where Sigma = L @ L.T (guaranteed positive-definite).
    """
    s = stalk
    L = _np401.zeros((3, 3))
    L[0, 0] = _np401.exp(float(s[12]))
    L[1, 1] = _np401.exp(float(s[13]))
    L[2, 2] = _np401.exp(float(s[14]))
    L[1, 0] = float(s[15])
    L[2, 0] = float(s[16])
    L[2, 1] = float(s[17])
    Sigma = L @ L.T
    return L, Sigma


def is_valid_covariance_401(stalk):
    """
    EXP-401 validity predicate for Sector D (log-Cholesky covariance).

    Checks:
      1. stalk has at least 18 elements.
      2. stalk[12:18] are all finite.
      3. Sigma = L @ L.T is positive-definite (all eigenvalues > 0).
         (Guaranteed by log-Cholesky unless diagonal entries are -inf.)

    Returns bool.
    """
    if len(stalk) < 18:
        return False
    if not _np401.all(_np401.isfinite(stalk[12:18])):
        return False
    L, Sigma = cholesky_from_stalk_401(stalk)
    eigvals = _np401.linalg.eigvalsh(Sigma)
    return bool(_np401.all(eigvals > 0))


# ---------------------------------------------------------------------------
# Manifold Firewall -- EXP-502 (is_manifold_501)
# ---------------------------------------------------------------------------
#
# Elastic-limit gate on the inter-claim (manifold) entanglement ghost.
# Reads the DEGREE-NORMALIZED global entanglement ratio B_ent produced by
# phi_ent_observe(..., degree_normalize=True) (EXP-502, Ghost #22 fix).
#
# eps_manifold is the "unbreakable skin": the maximum admissible inter-claim
# deformation. A state whose normalized residual exceeds eps_manifold is
# structurally torn and is rejected; per protocol the engine reverts to the
# last valid hashed state.
#
# Calibration (EXP-502 preregistration):
#   * Un-normalized B_ent baseline (EXP-501, measured): median ~ 0.678.
#   * Degree normalization shifts the baseline DOWN by ~1/sqrt(mean_deg);
#     mean_deg = 2*N_edges/N_leaves ~ 2*198/71 ~ 5.58, sqrt ~ 2.36.
#   * Preregistered limit eps_manifold = 0.8 (declared constant).
#     NOTE: against the *normalized* baseline this is a PERMISSIVE skin
#     (limit / normalized_baseline ~ 2.5-3x). The measured normalized median
#     from EXP-502 Fork A is the lower bound for a tighter elastic limit;
#     retune here, not in the operator (Ghost #21 Zusammenhang Stiffness).
EPS_MANIFOLD_502 = 0.8


def is_manifold_501(B_ent, eps_manifold=EPS_MANIFOLD_502):
    """EXP-502 Manifold Firewall (global gate).

    Returns True (state admissible) iff the degree-normalized global entanglement
    ratio B_ent does not exceed the elastic limit eps_manifold.

        is_manifold_501 := (B_ent <= eps_manifold)

    Pure scalar predicate; no MuState mutation. Observable purity preserved.
    """
    return bool(float(B_ent) <= float(eps_manifold))


def is_manifold_501_perclaim(G_ent_per_claim, Z_active_norm,
                             eps_manifold=EPS_MANIFOLD_502, eps=1e-15):
    """EXP-502 Manifold Firewall (per-claim gate, strict variant).

    Returns (ok, worst_cid, worst_ratio). ok is True iff EVERY claim's normalized
    residual ratio g_i / (||Z_active|| + eps) is within eps_manifold. Catches a
    single torn claim that a global average would mask (localized tears).
    """
    worst_cid = None
    worst_ratio = 0.0
    denom = float(Z_active_norm) + eps
    for cid, g in G_ent_per_claim.items():
        r = float(g) / denom
        if r > worst_ratio:
            worst_ratio = r
            worst_cid = cid
    return bool(worst_ratio <= float(eps_manifold)), worst_cid, worst_ratio

# ---------------------------------------------------------------------------
# Citadel Entropy Firewall -- EXP-508 (is_citadel_508)
# ---------------------------------------------------------------------------
#
# Information-admissibility law (NOT the thermodynamic Second Law). E* = K_budget
# is the energy/resolution budget; it licenses Omega(E*) = K_budget microstates, so
#   H_in  = log2(K_budget)
#   H_out = log2(N_f + N_gamma)        distributed entropy across N_f fragments (leaves)
#                                      and N_gamma gamma/photon emissions (the delta_0
#                                      coboundary residuals exchanged between fragments)
#   dS_cit = H_in - H_out = log2( K_budget / (N_f + N_gamma) )
#
# Law of the Citadel:  dS_cit >= 0  <=>  N_f + N_gamma <= K_budget
#   "no structure is fabricated beyond what the energy budget E* licenses."
# Dual firewall: a reality is verified only if it is BOTH manifold-continuous
# (is_manifold_501, eps=0.8) AND citadel-admissible (is_citadel_508, dS_cit >= 0).

CITADEL_FLOOR_508 = 0.0     # entropy-neutral-or-positive admission threshold (bits)


def citadel_entropy_508(K_budget, n_fragments, n_gamma):
    """EXP-508 Citadel entropy accounting. Returns dict(H_in, H_out, dS_cit, N_f, N_gamma, quanta).

    H_in   = log2(K_budget)                 (E* = K_budget licensing)
    H_out  = log2(N_f + N_gamma)            (fragments + gamma/delta_0 emissions)
    dS_cit = H_in - H_out                   (the citadel score, in bits)

    Pure numeric; counts are P_yz-invariant -> dS_cit is P_yz-invariant.
    """
    Nf = max(int(n_fragments), 0)
    Ng = max(int(n_gamma), 0)
    quanta = max(Nf + Ng, 1)
    H_in = float(np.log2(max(float(K_budget), 1.0)))
    H_out = float(np.log2(float(quanta)))
    return {"H_in": round(H_in, 9), "H_out": round(H_out, 9),
            "dS_cit": round(H_in - H_out, 9), "N_f": Nf, "N_gamma": Ng, "quanta": quanta}


def is_citadel_508(dS_cit, floor=CITADEL_FLOOR_508):
    """Law of the Citadel: admit iff dS_cit >= floor (entropy-neutral or positive)."""
    return bool(float(dS_cit) >= float(floor))

# ---------------------------------------------------------------------------
# Zeeman/Bethe Citadel -- EXP-509 (is_bethe_citadel_509)
# ---------------------------------------------------------------------------
#
# Dynamic thermodynamic refinement of the Citadel law (EXP-508). The static law used
# E* = K_budget with a counting level density. EXP-509 couples E* to the ZEEMAN ENERGY
# (beta_Z, the homeostatic excitation / "temperature") and a BETHE level density:
#
#   rho(E*)  = exp( 2*sqrt(a * E*) )                   Bethe nuclear level density
#   H_in     = log2 rho(E*) = 2*sqrt(a*E*) / ln2       available phase space (bits)
#   H_out    = log2(N_f + N_gamma)                      realized microstates
#   dS_cit_bethe = H_in - H_out
#
# Law of the (thermodynamic) Citadel: dS_cit_bethe >= 0
#   -- a world whose realized complexity exceeds the phase space its excitation E* licenses
#      "overheats" and is rejected. Excitation gates structure (friction).
#
# LEVEL-DENSITY PARAMETER a:  a = a0 * d_stalk  (the stalk-schema mass, d=18 = the substrate's
#   intrinsic degrees of freedom). a is a SUBSTRATE property, FIXED per realization. It does NOT
#   scale with leaf-count: leaf-count is the realized complexity already in H_out; coupling a to
#   it would double-count N and dissolve the friction. (a0 calibrated so valid realizations pass.)

BETHE_A0_509 = 0.15          # level-density per stalk dimension (calibrated)
import math as _math509


def bethe_citadel_509(beta_Z, n_fragments, n_gamma, a0=BETHE_A0_509, d_stalk=18):
    """EXP-509 Zeeman/Bethe Citadel score. E* = beta_Z (Zeeman excitation); Bethe level density.
    Returns dict(a, E_star, H_in, H_out, dS_cit, N_f, N_gamma, quanta).  P_yz: counts + beta_Z
    (a norm-derived scalar) are P_yz-invariant -> dS_cit P_yz-invariant."""
    a = float(a0) * int(d_stalk)
    E = max(float(beta_Z), 0.0)
    Nf = max(int(n_fragments), 0); Ng = max(int(n_gamma), 0)
    quanta = max(Nf + Ng, 1)
    H_in = float(2.0 * _math509.sqrt(a * E) / _math509.log(2.0))     # log2 of Bethe rho(E*)
    H_out = float(_math509.log2(float(quanta)))
    return {"a": round(a, 9), "E_star": round(E, 9), "H_in": round(H_in, 9),
            "H_out": round(H_out, 9), "dS_cit": round(H_in - H_out, 9),
            "N_f": Nf, "N_gamma": Ng, "quanta": quanta}


def is_bethe_citadel_509(dS_cit, floor=0.0):
    """Thermodynamic Law of the Citadel: admit iff dS_cit_bethe >= floor (not overheated)."""
    return bool(float(dS_cit) >= float(floor))
