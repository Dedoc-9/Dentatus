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

    def eta_AC(self) -> float:
        """
        eta_AC(t) = |lambda_A . lambda_C| / (||lambda_A|| * ||lambda_C|| + eps)

        Cosine similarity between per-sector projection coefficient vectors.
        lambda_A: lstsq(W_basis[0:8,:], Z[0:8])  -- sector A+B weighting
        lambda_C: lstsq(W_basis[8:12,:], Z[8:12]) -- sector C weighting

        Returns 0.0 if |W_t| < 2 or either lambda is zero.
        Range: [0, 1]. 0 = fully decoupled; 1 = identical stalk weighting.
        """
        if len(self.active) < 2:
            return 0.0
        Z = self.Z()
        if Z.shape[0] < 12:
            return 0.0
        W = self.W_basis()
        W_A = W[0:8, :];  Z_A = Z[0:8]
        W_C = W[8:12, :]; Z_C = Z[8:12]
        try:
            lam_A, _, _, _ = np.linalg.lstsq(W_A, Z_A, rcond=None)
            lam_C, _, _, _ = np.linalg.lstsq(W_C, Z_C, rcond=None)
        except np.linalg.LinAlgError:
            return 0.0
        norm_A = float(np.linalg.norm(lam_A))
        norm_C = float(np.linalg.norm(lam_C))
        if norm_A < EPSILON or norm_C < EPSILON:
            return 0.0
        return float(abs(np.dot(lam_A, lam_C)) / (norm_A * norm_C + EPSILON))

    # ---- EXP-309: focal point + LOD observer --------------------------------

    # focal_point: Optional[np.ndarray] stored as instance attribute (not field)
    # Set after construction: mu.focal_point = np.array([...])
    # NOT included in H_t hash computation.

    def next_focal_point(self, eps: float = 1e-12) -> np.ndarray:
        """
        f_{t+1} = mass-weighted centroid of active leaves.

        pos_cid  = stalk_B[cid][0:3]   (dims 4,5,6)
        mass_cid = ||stalk_A[cid]||_2  (dims 0:4)

        Fallback: if total mass < eps -> geometric centroid of active bbox centroids.
        """
        if not self.active:
            return np.zeros(3)
        positions = np.array([self.claims[c].stalk[4:7] for c in self.active])
        masses    = np.array([float(np.linalg.norm(self.claims[c].stalk[0:4]))
                              for c in self.active])
        total = float(masses.sum())
        if total < eps:
            bboxes = [self.claims[c].bbox for c in self.active
                      if self.claims[c].bbox is not None]
            if bboxes:
                return np.mean([(lo + hi) / 2.0 for lo, hi in bboxes], axis=0)
            return np.zeros(3)
        return float(1.0 / total) * (positions * masses[:, None]).sum(axis=0)

    def next_S_C_309(self, bypass_registry: dict) -> np.ndarray:
        """
        Ghost quarantine for EXP-309 (EMA with selective freeze).

        bypass_registry: Dict[claim_id -> frozenset of bypassed predicate names]

        CASE 1 (any active claim has is_valid_kappa_308 bypassed):
            freeze S_C entirely -- spurious kappa residual must not accumulate.
        CASE 2 (any active claim has is_unit_norm bypassed, kappa not bypassed):
            freeze dims 0:3 (normal); update dim 3 (kappa) via standard EMA.
        CASE 3 (no bypass active):
            full EMA update (standard EXP-308 next_S_C).
        """
        bypassed_kappa = any("is_valid_kappa_308" in bypass_registry.get(c, frozenset())
                             for c in self.active)
        bypassed_norm  = any("is_unit_norm" in bypass_registry.get(c, frozenset())
                             for c in self.active)

        if bypassed_kappa:
            # full freeze
            s = self.S_C if self.S_C is not None else np.zeros(4)
            return s.copy()
        elif bypassed_norm:
            # partial freeze: update kappa dim only
            G_C = self.G_C()
            s = (self.S_C if self.S_C is not None else np.zeros(4)).copy()
            if s.shape[0] >= 4 and G_C.shape[0] >= 4:
                s[3] = self.alpha * s[3] + (1.0 - self.alpha) * G_C[3]
            return s
        else:
            return self.next_S_C()

    def focal_point_value(self) -> np.ndarray:
        """Return stored focal_point or default [0.5,0.5,0.5]."""
        fp = getattr(self, 'focal_point', None)
        return fp if fp is not None else np.array([0.5, 0.5, 0.5])

    def _replace_S_C(self, s_c_new: np.ndarray) -> 'MuState':
        """Return copy of self with S_C replaced; reseals (S_C affects H_t)."""
        import copy as _copy
        mu = _copy.copy(self)
        mu.S_C     = s_c_new
        mu._H      = None
        mu._sealed = False
        mu.seal()
        return mu

    def _replace_focal_point(self, fp: np.ndarray) -> 'MuState':
        """Return copy of self with focal_point updated. Does not affect H_t."""
        import copy as _copy
        mu = _copy.copy(self)
        mu.focal_point = fp
        return mu

    def _replace_validity_class(self, vc: str) -> 'MuState':
        """Return copy of self with validity_class set. Does not affect H_t."""
        import copy as _copy
        mu = _copy.copy(self)
        mu.validity_class = vc
        return mu

    # ---- EXP-310: causal ghost / transfer entropy ----------------------------

    def _update_ghost_history(self, maxlen: int = 32) -> None:
        """Append (||S_A||, ||S_C||) to ghost_history circular buffer.
        Not included in H_t. Called after seal() in apply_gamma_310 wrapper."""
        from collections import deque
        hist = getattr(self, 'ghost_history', None)
        if hist is None:
            hist = deque(maxlen=maxlen)
        a = float(np.linalg.norm(self.S_A if self.S_A is not None else np.zeros(8)))
        c = float(np.linalg.norm(self.S_C if self.S_C is not None else np.zeros(4)))
        hist.append((a, c))
        self.ghost_history = hist

    def te_observables(self, k: int = 5):
        """Compute (T_A_to_C, T_C_to_A, delta_T_AC, T_norm).
        Returns (nan,nan,nan,nan) if ghost_history has fewer than k+2 entries.
        Primary estimator: KSG scalar TE on (||S_A||, ||S_C||) sequences.
        """
        hist = getattr(self, 'ghost_history', None)
        if hist is None or len(hist) < max(k + 2, 4):
            nan = float('nan')
            return nan, nan, nan, nan

        import math as _math
        arr = np.array(list(hist), dtype=float)
        a_seq = arr[:, 0]
        c_seq = arr[:, 1]

        def _digamma(x):
            r = 0.0
            while x < 15.0:
                r -= 1.0 / x
                x += 1.0
            r += _math.log(x) - 0.5 / x
            x2 = x * x
            r -= 1.0 / (12.0 * x2)
            r += 1.0 / (120.0 * x2 * x2)
            r -= 1.0 / (252.0 * x2 * x2 * x2)
            return r

        def _ksg_te(a, c):
            """T_{a->c} = I(c_now ; [a_prev, c_prev]) - I(c_now ; c_prev). KSG Alg 1.
            Returns 0.0 for degenerate (zero-variance) marginals: KSG undefined."""
            a_prev = a[:-1]; c_prev = c[:-1]; c_now = c[1:]
            N = len(c_now)
            if N < k + 2:
                return float('nan')
            # Degeneracy guard: KSG undefined when any marginal has zero variance.
            # Frozen S_C -> c constant -> std=0 -> return 0.0 by convention.
            if float(np.std(c_now)) < 1e-15 or float(np.std(c_prev)) < 1e-15:
                return 0.0
            if float(np.std(a_prev)) < 1e-15:
                return 0.0

            def _kth_eps_joint(data):
                eps = np.zeros(N)
                for i in range(N):
                    d = np.max(np.abs(data - data[i]), axis=1)
                    d[i] = np.inf
                    eps[i] = np.partition(d, k - 1)[k - 1]
                return eps

            # I(c_now ; [a_prev, c_prev]) in R^3
            j3 = np.column_stack([c_now, a_prev, c_prev])
            e3 = _kth_eps_joint(j3)
            nx3 = np.array([np.sum(np.abs(c_now - c_now[i]) <= e3[i] + 1e-15) - 1
                            for i in range(N)])
            ap_cp = np.column_stack([a_prev, c_prev])
            ny3 = np.array([np.sum(np.max(np.abs(ap_cp - ap_cp[i]), axis=1) <= e3[i] + 1e-15) - 1
                            for i in range(N)])
            I_joint = (_digamma(k)
                       - float(np.mean([_digamma(nx3[i]+1)+_digamma(ny3[i]+1) for i in range(N)]))
                       + _digamma(N))

            # I(c_now ; c_prev) in R^2
            j2 = np.column_stack([c_now, c_prev])
            e2 = _kth_eps_joint(j2)
            nx2 = np.array([np.sum(np.abs(c_now - c_now[i]) <= e2[i] + 1e-15) - 1
                            for i in range(N)])
            ny2 = np.array([np.sum(np.abs(c_prev - c_prev[i]) <= e2[i] + 1e-15) - 1
                            for i in range(N)])
            I_cond = (_digamma(k)
                      - float(np.mean([_digamma(nx2[i]+1)+_digamma(ny2[i]+1) for i in range(N)]))
                      + _digamma(N))

            return max(0.0, I_joint - I_cond)

        T_ac = _ksg_te(a_seq, c_seq)
        T_ca = _ksg_te(c_seq, a_seq)
        if _math.isnan(T_ac) or _math.isnan(T_ca):
            nan = float('nan')
            return nan, nan, nan, nan
        delta = T_ac - T_ca

        # Normalization: T_norm = T_ac / H(c|c_prev)  via KSG entropy estimate
        # H(c_now | c_prev) = H(c_now, c_prev) - H(c_prev)
        # H_KSG(X) = -< log(n_X / (N-1)) > + log(vol_k)  [marginal KSG entropy]
        # Approximate: use I_cond = H(c_now) - H(c_now|c_prev) -> H(c|c_prev) = H(c_now) - I_cond
        # For normalization, use I_cond as proxy for H(c|c_prev); T_norm = T_ac / I_cond
        T_norm = float('nan')
        if T_ac > 1e-15:
            # simple normalization: T_ac / (T_ac + T_ca + 1e-15)
            T_norm = T_ac / (T_ac + T_ca + 1e-15)

        return T_ac, T_ca, delta, T_norm
