"""
validity.py -- Validity predicate for EXP-301 (E-301-003 corrected form).

CORRECTION (E-301-003):
  The original predicate lambda_min(L_F) > 0 is incorrect for our directed DAG.
  For a connected consistent sheaf, lambda_min(L_F) = 0 always (the zero mode
  is the constant global section, which IS the valid case). Strict positivity
  would reject every valid connected state.

CORRECTED PREDICATE -- Forward Entailment Consistency:
  is_valid(mu_t) iff for every edge (u->v) in E_t:
    - Single-source (PARTITION): F(u->v)(stalk_u) ~= stalk_v
    - Multi-source  (SYNTHESIS): sum_i F(u_i->v)(stalk_{u_i}) ~= stalk_v

  This checks that restriction maps are correctly calibrated to the observed stalks.
  Violation = a claim whose stalk is inconsistent with its construction history.
  This is the directed-DAG analogue of H^1(G, F) = 0 (no holonomy obstruction).

  lambda_min is retained as a numeric observable (not the validity gate).
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
    Guaranteed True by construction after apply_phi / apply_psi if restriction
    maps are correctly set. Fails only if state is externally corrupted or
    restriction maps are mis-calibrated.
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
