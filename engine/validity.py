"""
validity.py -- Sheaf Laplacian validity predicate for EXP-301.

is_valid(mu_t) iff lambda_min(L_F(mu_t)) > 0
L_F = delta^T delta
(delta x)_e = F(u->v)(x_u) - x_v  for e=(u->v)

Single-node DAG (no edges): trivially valid.
lambda_min = 0 with no edges; the predicate becomes non-trivial only
when entailments exist. This matches the sheaf theory: an empty graph
has no constraints, so every section is vacuously harmonic.

Dev note: lambda_min < 0 signals a non-trivial harmonic section --
a global inconsistency invisible to local checks.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    from engine.state import MuState

LAMBDA_MIN_THRESHOLD = 0.0


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
    """L_F = delta^T delta  (PSD by construction)."""
    d = build_coboundary(mu)
    return d.T @ d


def lambda_min(mu):
    """Minimum eigenvalue of L_F. Returns 0.0 for empty graph."""
    if not mu.entailments:
        return 0.0
    L = sheaf_laplacian(mu)
    if L.shape == (1, 1):
        return float(L[0, 0])
    try:
        return float(np.min(np.linalg.eigvalsh(L)))
    except np.linalg.LinAlgError:
        return -1.0


def is_valid(mu):
    """
    is_valid(mu_t) iff lambda_min(L_F(mu_t)) > 0
    Trivially True when no entailments exist.
    """
    if not mu.entailments:
        return True
    return lambda_min(mu) > LAMBDA_MIN_THRESHOLD


def delta_lambda_min(mu_prev, mu_next):
    """
    delta_lambda_min = lambda_min(mu_{t+1}) - lambda_min(mu_t).
    Negative -> ConsistencyError; revert to H_{t-1}.
    """
    return lambda_min(mu_next) - lambda_min(mu_prev)
