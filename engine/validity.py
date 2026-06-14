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
    Block-diagonal restriction map predicate for EXP-306 (d=12).
    Sector boundaries: A=[0:4], B=[4:8], C=[8:12]
    Off-diagonal cross blocks must be near-zero.
    Also handles d=11 (delegates to is_valid_block_diagonal).
    Skips F with shape other than (11,11) or (12,12).
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
        # else: skip non-matching shapes
    return True
