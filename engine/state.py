"""
state.py — Core state structures for EXP-301.

H_t = HASH(Z_t ⊕ S_t ⊕ W_t ⊕ t ⊕ protocol_version)
G_t = Z_t − Π_{W_t}(Z_t)
S_{t+1} = α·S_t + (1−α)·G_t

Dual space (S, G) and primary space (Z) never collapsed into a single representation.
Orthogonality enforced: S_t ⊥ W_t by construction.
"""

from __future__ import annotations

import hashlib
import json
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, FrozenSet, Optional, Tuple

import numpy as np

PROTOCOL_VERSION = "exp301-v1"
ALPHA_DEFAULT    = 0.85
EPSILON          = 1e-12
C_KBOUND         = 150          # K-bound slack constant (ENGINE_AXIOMS §2.1)


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

class EntailmentType(Enum):
    PARTITION   = "PARTITION"
    SYNTHESIS   = "SYNTHESIS"
    DEPENDENCY  = "DEPENDENCY"
    SPATIAL     = "SPATIAL"     # geometric subdivision edge (EXP-303)


@dataclass(frozen=True)
class Provenance:
    parent_ids:  Tuple[str, ...]
    operator_id: str
    timestamp:   str            # ISO 8601

    def to_dict(self) -> dict:
        return {
            "parent_ids":  list(self.parent_ids),
            "operator_id": self.operator_id,
            "timestamp":   self.timestamp,
        }


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Claim (node)
# ---------------------------------------------------------------------------

@dataclass
class Claim:
    """
    Node in the claim DAG.
    id   = SHA-256(provenance ⊕ payload ⊕ t ⊕ protocol_version)[:16]
    K    ≈ len(zlib.compress(payload, level=9))
    """
    provenance: Provenance
    payload:    str
    stalk:      np.ndarray      # F(v) ∈ ℝ^d
    t:          int
    bbox:       Optional[Tuple[np.ndarray, np.ndarray]] = None
                                # geometric bounding box (lo,hi) in ℝ^3 — EXP-303
                                # spatial metadata; NOT included in id hash

    # computed at init
    id:      str = field(init=False)
    K_bound: int = field(init=False)

    def __post_init__(self):
        raw = json.dumps({
            "provenance":       self.provenance.to_dict(),
            "payload":          self.payload,
            "t":                self.t,
            "protocol_version": PROTOCOL_VERSION,
        }, sort_keys=True).encode()
        self.id      = hashlib.sha256(raw).hexdigest()[:16]
        self.K_bound = len(zlib.compress(self.payload.encode("utf-8"), level=9))

    def stalk_norm(self) -> float:
        return float(np.linalg.norm(self.stalk))


# ---------------------------------------------------------------------------
# Entailment (edge)
# ---------------------------------------------------------------------------

@dataclass
class Entailment:
    """
    Directed edge (source → target).
    restriction: linear map F(source) → F(target), shape (d_tgt, d_src)

    EXP-304 fields (optional metadata — NOT included in H_t hash):
      omega:    barycentric weight ωᵢ for Sector B (Φ_B edges); default None
      det_sign: sign(det(F_B)) ∈ {-1, +1}; +1 for non-reflective affine maps; default None
    """
    source_id:      str
    target_id:      str
    etype:          EntailmentType
    restriction:    np.ndarray      # (d_tgt, d_src)
    predicate_hash: str
    omega:          Optional[float] = None   # barycentric weight (EXP-304 Φ_B)
    det_sign:       Optional[int]   = None   # chirality flag (EXP-304 Φ_B)


# ---------------------------------------------------------------------------
# State hash
# ---------------------------------------------------------------------------

def _compute_H(
    Z: np.ndarray,
    S: np.ndarray,
    W: FrozenSet[str],
    t: int,
) -> str:
    """H_t = HASH(Z_t ⊕ S_t ⊕ W_t ⊕ t ⊕ protocol_version)"""
    payload = json.dumps({
        "Z":                Z.tolist(),
        "S":                S.tolist(),
        "W":                sorted(W),
        "t":                t,
        "protocol_version": PROTOCOL_VERSION,
    }, sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# MuState
# ---------------------------------------------------------------------------

@dataclass
class MuState:
    """
    Full engine state μ_t = cellular sheaf (G_t, F_t).

    claims:      V_t — id → Claim
    entailments: E_t — (src_id, tgt_id) → Entailment
    active:      W_t — frozenset of leaf claim ids (out-degree 0)
    S:           EMA ghost accumulation ∈ ℝ^D
    alpha:       EMA coefficient
    t:           current timestep
    """
    t:           int
    claims:      Dict[str, Claim]
    entailments: Dict[Tuple[str, str], Entailment]
    active:      FrozenSet[str]
    S:           np.ndarray
    alpha:       float = ALPHA_DEFAULT
    S_A:         Optional[np.ndarray] = field(default=None)  # dual ghost Sector A+B dims 0-7 (EXP-306)
    S_C:         Optional[np.ndarray] = field(default=None)  # dual ghost Sector C dims 8-11 (EXP-306)
    _H:          Optional[str]  = field(default=None, repr=False)
    _sealed:     bool           = field(default=False, repr=False)

    # ---- primary space ----------------------------------------------------

    def Z(self) -> np.ndarray:
        """Z_t: sum of active claim stalks in R^d.
        Sum (not concatenation) so Z lives in the same R^d space as S and G,
        enabling G_t = Z_t - Pi_{W_t}(Z_t) via lstsq in R^d.
        Lossless partition: sum(children) = parent -> G = 0 by construction.
        """
        if not self.active:
            d = next(iter(self.claims.values())).stalk.shape[0] if self.claims else 1
            return np.zeros(d)
        stalks = [self.claims[cid].stalk for cid in self.active]
        return sum(stalks[1:], stalks[0].copy())

    def W_basis(self) -> np.ndarray:
        """Column matrix of active stalks, shape (d, |W_t|)."""
        stalks = [self.claims[cid].stalk for cid in sorted(self.active)]
        if not stalks:
            return np.zeros((1, 1))
        return np.column_stack(stalks)

    # ---- dual space -------------------------------------------------------

    def G(self, registry=None) -> np.ndarray:
        """
        G_t = (Z_t − Π_{W_t}(Z_t)) + path_coherence_residual  (E-301-004)

        base term: projection residual (0 for lossless operators by construction)
        coherence term: Σ_{unresolved ConvergenceRecords} (stalk1 − stalk2)
          Non-zero iff declare_convergence() called on registry without a
          registered 2-morphism resolving the pair.

        registry: ConfluenceRegistry | None.
          If None, returns base term only (backward compatible).
        """
        Z = self.Z()
        W = self.W_basis()
        try:
            coeff, _, _, _ = np.linalg.lstsq(W, Z, rcond=None)
            proj = W @ coeff
        except np.linalg.LinAlgError:
            proj = np.zeros_like(Z)
        base_G = Z - proj

        if registry is not None:
            d = Z.shape[0]
            residual = registry.path_residual_sum(d=d)
            if residual.shape == base_G.shape:
                return base_G + residual
        return base_G

    def next_S(self, registry=None) -> np.ndarray:
        """S_{t+1} = α·S_t + (1−α)·G_t(registry)"""
        G = self.G(registry=registry)
        s = self.S
        # broadcast to matching dim if needed
        if s.shape != G.shape:
            s = np.zeros_like(G)
        return self.alpha * s + (1.0 - self.alpha) * G

    # ---- observables (pure numeric) --------------------------------------

    def B(self) -> float:
        """B(t) = ||S_t|| / (||Z_t|| + ε)"""
        return float(np.linalg.norm(self.S) / (np.linalg.norm(self.Z()) + EPSILON))

    def ESS(self) -> float:
        """ESS = (Σ wᵢ)² / Σ wᵢ²  over active claim stalk norms."""
        if not self.active:
            return 0.0
        w = np.array([self.claims[cid].stalk_norm() for cid in self.active])
        denom = float((w ** 2).sum())
        return float(w.sum() ** 2 / denom) if denom > 0 else 0.0

    def eta_CLT(self) -> float:
        """η_CLT = √|W_t| · (μ̂_stalk − μ_stalk)  (uses grand mean across all claims)."""
        if not self.active:
            return 0.0
        active_norms  = np.array([self.claims[cid].stalk_norm() for cid in self.active])
        all_norms     = np.array([c.stalk_norm() for c in self.claims.values()])
        mu_hat = active_norms.mean()
        mu     = all_norms.mean() if len(all_norms) > 0 else 0.0
        return float(np.sqrt(len(self.active)) * (mu_hat - mu))

    # ---- hash / seal -----------------------------------------------------

    def seal(self) -> str:
        """Compute and lock H_t. Raises if already sealed.
        When dual ghost (S_A, S_C) active: S_hash = concat(S_A, S_C).
        Backward compat: S_A/S_C None -> use S directly.
        """
        if self._sealed:
            raise RuntimeError(f"State t={self.t} already sealed; H={self._H}")
        if self.S_A is not None and self.S_C is not None:
            S_hash = np.concatenate([self.S_A, self.S_C])
        else:
            S_hash = self.S
        self._H      = _compute_H(self.Z(), S_hash, self.active, self.t)
        self._sealed = True
        return self._H

    @property
    def H(self) -> str:
        if not self._sealed:
            raise RuntimeError(f"State t={self.t} not sealed; call seal() first.")
        return self._H

    # ---- graph helpers ---------------------------------------------------

    def subtree_ids(self, cid: str) -> FrozenSet[str]:
        """All descendant ids reachable by walking target edges (includes cid).
        Traverses DOWNSTREAM (src->tgt direction) to collect claim's own content
        and all claims it produced. Used for matroid independence check in Psi:
        M_v = vector matroid of v and its descendants (not ancestors).
        Ancestors are shared across siblings and would collapse union rank.
        """
        visited: set = set()
        stack = [cid]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            for (src, tgt) in self.entailments:
                if src == node:
                    stack.append(tgt)
        return frozenset(visited)

    # ---- dual ghost (EXP-306) ------------------------------------------------

    def G_A(self) -> np.ndarray:
        """G_A = Z_A - Pi_{W_A}(Z_A) over dims 0:8 (Sectors A+B).
        Projects Z_A onto column space of W_basis[0:8, :].
        Returns zero vector if stalk dim < 8.
        """
        Z = self.Z()
        d = Z.shape[0]
        if d < 8:
            return np.zeros(d)
        Z_A = Z[0:8]
        W = self.W_basis()
        W_A = W[0:8, :]
        try:
            coeff, _, _, _ = np.linalg.lstsq(W_A, Z_A, rcond=None)
            proj = W_A @ coeff
        except np.linalg.LinAlgError:
            proj = np.zeros_like(Z_A)
        return Z_A - proj

    def G_C(self) -> np.ndarray:
        """G_C = Z_C - Pi_{W_C}(Z_C) over dims 8:12 (Sector C incl. kappa).
        Projects Z_C onto column space of W_basis[8:12, :].
        Returns zero vector of shape (4,) if stalk dim < 12.
        """
        Z = self.Z()
        d = Z.shape[0]
        if d < 12:
            return np.zeros(4)
        Z_C = Z[8:12]
        W = self.W_basis()
        W_C = W[8:12, :]
        try:
            coeff, _, _, _ = np.linalg.lstsq(W_C, Z_C, rcond=None)
            proj = W_C @ coeff
        except np.linalg.LinAlgError:
            proj = np.zeros_like(Z_C)
        return Z_C - proj

    def next_S_A(self) -> np.ndarray:
        """S_A_{t+1} = alpha * S_A + (1-alpha) * G_A_t  (EXP-306 dual ghost)."""
        G = self.G_A()
        s = self.S_A if self.S_A is not None else np.zeros(8)
        if s.shape != G.shape:
            s = np.zeros_like(G)
        return self.alpha * s + (1.0 - self.alpha) * G

    def next_S_C(self) -> np.ndarray:
        """S_C_{t+1} = alpha * S_C + (1-alpha) * G_C_t  (EXP-306 dual ghost)."""
        G = self.G_C()
        s = self.S_C if self.S_C is not None else np.zeros(4)
        if s.shape != G.shape:
            s = np.zeros_like(G)
        return self.alpha * s + (1.0 - self.alpha) * G

    def B_A(self) -> float:
        """B_A(t) = ||S_A|| / (||Z[0:8]|| + eps)  (EXP-306 photometric ghost ratio)."""
        S_A = self.S_A if self.S_A is not None else np.zeros(8)
        Z_A = self.Z()[0:8] if self.Z().shape[0] >= 8 else self.Z()
        return float(np.linalg.norm(S_A) / (np.linalg.norm(Z_A) + EPSILON))

    def B_C(self) -> float:
        """B_C(t) = ||S_C|| / (||Z[8:12]|| + eps)  (EXP-306 geometric ghost ratio)."""
        S_C = self.S_C if self.S_C is not None else np.zeros(4)
        Z = self.Z()
        Z_C = Z[8:12] if Z.shape[0] >= 12 else np.zeros(4)
        return float(np.linalg.norm(S_C) / (np.linalg.norm(Z_C) + EPSILON))
