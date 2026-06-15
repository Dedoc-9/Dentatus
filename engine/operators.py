"""
operators.py — Φ, Ψ, Ω for EXP-301.

Cost with gravitational backreaction:
    C(Op, t) = C₀(Op) · exp(β · ||S_t||)

    C₀(Φ) = 1.0
    C₀(Ψ) = k  (number of inputs)
    C₀(Ω) = 0.0

K-bound (Φ):
    Σᵢ K(payload_i) ≤ K(payload_v) + C_KBOUND · log(N)

Matroid independence (Ψ):
    r(M_{v_1} ∨ ... ∨ M_{v_k}) == Σᵢ r(M_{v_i})
    implemented as numpy matrix rank over stalk matrices

Restriction maps (E-301-003):
    Φ: F(parent → child_i) = outer(stalk_i, stalk_parent) / ||stalk_parent||²
       Satisfies: F(parent→child_i)(stalk_parent) = stalk_i  (by construction)
    Ψ: F(child_i → new) = alpha_i · I
       Satisfies: Σᵢ F(child_i→new)(stalk_i) = stalk_new  (weighted sum)

All operators return (new_MuState, cost) or raise an OperatorError.
On OperatorError the caller must revert to the last sealed state.
"""

from __future__ import annotations

import hashlib
import json
import math
import zlib
from dataclasses import replace
from typing import List, Tuple

import numpy as np

from engine.state import (
    C_KBOUND, EPSILON, PROTOCOL_VERSION, Claim, Entailment,
    EntailmentType, MuState, Provenance, now_iso,
)
from engine.validity import is_valid, lambda_min

# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------

class OperatorError(Exception):
    """Base. Caller must revert state to last valid H."""


class PartitionError(OperatorError):
    pass


class SynthesisError(OperatorError):
    pass


class ObservationError(OperatorError):
    pass


class BudgetExceeded(OperatorError):
    pass


# ---------------------------------------------------------------------------
# Backreaction cost
# ---------------------------------------------------------------------------

def _cost(C0: float, beta: float, S: np.ndarray) -> float:
    """C(Op, t) = C₀ · exp(β · ||S_t||)"""
    return C0 * math.exp(beta * float(np.linalg.norm(S)))


# ---------------------------------------------------------------------------
# Stalk helpers
# ---------------------------------------------------------------------------

def _orthogonal_decompose(stalk: np.ndarray, N: int, seed: int = 0) -> List[np.ndarray]:
    """
    Decompose stalk into N components such that:
      • Σᵢ stalk_i = stalk  (conservation)
      • ∀ i≠j: stalk_i · stalk_j ≈ 0  (orthogonality, best-effort in ℝ^d)

    Algorithm: QR decomposition of a random matrix gives N orthonormal basis
    vectors {q_1,...,q_N}. Project stalk onto each; add residual to component 0
    to guarantee conservation.

    Raises PartitionError if d < N (insufficient dimension for orthogonality).
    """
    d = stalk.shape[0]
    if d < N:
        raise PartitionError(
            f"DIM_INSUFFICIENT: stalk dim d={d} < N={N}. "
            "Re-declare Seed_0 with d >= N before partitioning."
        )
    rng  = np.random.default_rng(seed)
    A    = rng.standard_normal((d, d))
    Q, _ = np.linalg.qr(A)
    basis = Q[:, :N]                        # (d, N) orthonormal columns

    alphas     = basis.T @ stalk            # projections, shape (N,)
    components = [alphas[i] * basis[:, i] for i in range(N)]

    # Residual correction: guarantee Σᵢ stalk_i = stalk
    residual   = stalk - sum(components)
    components[0] = components[0] + residual

    return components


def _phi_restriction(stalk_child: np.ndarray, stalk_parent: np.ndarray) -> np.ndarray:
    """
    Restriction map F(parent → child) for Φ (E-301-003).

    F = outer(stalk_child, stalk_parent) / ||stalk_parent||²

    Satisfies: F(stalk_parent) = stalk_child  (exact by construction).
    Degenerate case (stalk_child ≈ 0 or stalk_parent ≈ 0): zero matrix.
    Shape: (d, d).
    """
    d = stalk_parent.shape[0]
    parent_norm_sq = float(np.dot(stalk_parent, stalk_parent))
    if parent_norm_sq < EPSILON or float(np.dot(stalk_child, stalk_child)) < EPSILON:
        return np.zeros((d, d))
    return np.outer(stalk_child, stalk_parent) / parent_norm_sq


def _matroid_rank(stalk_matrix: np.ndarray) -> int:
    """Rank of the vector matroid: numpy matrix rank of stalk column matrix."""
    if stalk_matrix.size == 0:
        return 0
    return int(np.linalg.matrix_rank(stalk_matrix, tol=1e-9))


def _check_matroid_independence(mu: MuState, claim_ids: List[str]) -> bool:
    """
    r(M_{v_1} ∨ ... ∨ M_{v_k}) == Σᵢ r(M_{v_i})

    Union matroid rank = rank of concatenated stalk matrices.
    Individual ranks = sum of ranks of individual subtree stalk matrices.
    Equality iff subtree stalk spaces are linearly independent.
    """
    matrices  = [mu.subtree_stalk_matrix(cid) for cid in claim_ids]
    ind_ranks = [_matroid_rank(m) for m in matrices]
    union_mat = np.hstack(matrices) if matrices else np.zeros((1, 1))
    union_rank = _matroid_rank(union_mat)
    return union_rank == sum(ind_ranks)


# ---------------------------------------------------------------------------
# Φ — Partition
# ---------------------------------------------------------------------------

def apply_phi(
    mu:            MuState,
    claim_id:      str,
    N:             int,
    partition_key: str,
    payloads:      List[str],
    beta:          float,
    budget:        float,
    spent:         float,
) -> Tuple[MuState, float]:
    """
    Φ(v, N, partition_key) → {v_1, ..., v_N}

    Preconditions:
      • claim_id ∈ W_t (active leaf)
      • N ≥ 2
      • len(payloads) == N
      • K-bound: Σᵢ K(payload_i) ≤ K(payload_v) + C_KBOUND·log(N)
      • stalk dim ≥ N

    Restriction maps: F(parent → child_i) = outer(stalk_i, stalk_parent) / ||stalk_parent||²
    is_valid(new_state) checked post-construction (E-301-003).

    Returns (new_MuState, cost). new_MuState is NOT sealed; caller seals after
    optional confluence check.
    """
    if claim_id not in mu.active:
        raise PartitionError(f"PRECONDITION: {claim_id} not in W_t (active leaves).")
    if N < 2:
        raise PartitionError(f"PRECONDITION: N={N} < 2.")
    if len(payloads) != N:
        raise PartitionError(f"PRECONDITION: len(payloads)={len(payloads)} != N={N}.")

    parent = mu.claims[claim_id]

    # K-bound check
    k_children = sum(
        len(zlib.compress(p.encode("utf-8"), level=9)) for p in payloads
    )
    k_limit = parent.K_bound + C_KBOUND * math.log(N)
    if k_children > k_limit:
        raise PartitionError(
            f"INFORMATION_OVERFLOW: Σ K(children)={k_children:.1f} > "
            f"K(parent)+c*log(N)={k_limit:.2f}"
        )

    # Backreaction cost
    cost = _cost(1.0, beta, mu.S)
    if spent + cost > budget:
        raise BudgetExceeded(
            f"Budget exceeded: spent={spent:.4f} + cost={cost:.4f} > B₀={budget}"
        )

    # Stalk decomposition
    stalks = _orthogonal_decompose(parent.stalk, N, seed=hash(partition_key) % (2**31))

    # Build child claims + entailments
    t_new      = mu.t + 1
    prov_hash  = hashlib.sha256(
        (partition_key + PROTOCOL_VERSION).encode()
    ).hexdigest()[:16]
    new_claims = dict(mu.claims)
    new_ents   = dict(mu.entailments)
    child_ids  = []

    for i, (payload, stalk_i) in enumerate(zip(payloads, stalks)):
        prov = Provenance(
            parent_ids=(claim_id,),
            operator_id=f"Phi:{partition_key}:{i}",
            timestamp=now_iso(),
        )
        child = Claim(provenance=prov, payload=payload, stalk=stalk_i, t=t_new)
        new_claims[child.id] = child
        child_ids.append(child.id)

        # Restriction map (E-301-003): F(parent→child_i)(stalk_parent) = stalk_i
        restriction = _phi_restriction(stalk_i, parent.stalk)
        ent = Entailment(
            source_id=claim_id,
            target_id=child.id,
            etype=EntailmentType.PARTITION,
            restriction=restriction,
            predicate_hash=prov_hash,
        )
        new_ents[(claim_id, child.id)] = ent

    # Update active set: remove parent, add children
    new_active = (mu.active - {claim_id}) | frozenset(child_ids)

    # Next S (EMA update)
    new_state = MuState(
        t=t_new,
        claims=new_claims,
        entailments=new_ents,
        active=new_active,
        S=mu.next_S(),
        alpha=mu.alpha,
    )

    # Consistency guard (E-301-003): forward entailment consistency
    if not is_valid(new_state):
        raise PartitionError(
            "CONSISTENCY_ERROR: is_valid(mu_1) failed after Φ — "
            "restriction maps are mis-calibrated. Reverting."
        )

    return new_state, cost


# ---------------------------------------------------------------------------
# Ψ — Synthesis
# ---------------------------------------------------------------------------

def apply_psi(
    mu:            MuState,
    claim_ids:     List[str],
    synthesis_key: str,
    payload:       str,
    weights:       List[float],
    beta:          float,
    budget:        float,
    spent:         float,
) -> Tuple[MuState, float]:
    """
    Ψ(v_1, ..., v_k, synthesis_key) → v_new

    Preconditions:
      • ∀ i: claim_ids[i] ∈ W_t
      • len(weights) == len(claim_ids); weights normalised internally
      • Matroid independence: r(M_{v_1} ∨ ... ∨ M_{v_k}) == Σᵢ r(M_{v_i})

    stalk(v_new) = Σᵢ αᵢ · stalk(v_i)
    Restriction maps (E-301-003): F(child_i → new) = alpha_i · I
    Multi-source consistency: Σᵢ F(child_i→new)(stalk_i) = stalk_new  (by construction)
    """
    k = len(claim_ids)
    for cid in claim_ids:
        if cid not in mu.active:
            raise SynthesisError(f"PRECONDITION: {cid} not in W_t.")
    if len(weights) != k:
        raise SynthesisError(f"PRECONDITION: len(weights)={len(weights)} != k={k}.")

    # Matroid independence check
    if not _check_matroid_independence(mu, claim_ids):
        raise SynthesisError(
            "MATROID_VIOLATION: r(union) < Σ r(individual). "
            "Sub-claim stalk spaces are not linearly independent."
        )

    # Backreaction cost: C₀ = k
    cost = _cost(float(k), beta, mu.S)
    if spent + cost > budget:
        raise BudgetExceeded(
            f"Budget exceeded: spent={spent:.4f} + cost={cost:.4f} > B₀={budget}"
        )

    # Normalise weights
    w = np.array(weights, dtype=float)
    w = w / w.sum()

    # Synthesised stalk: weighted sum
    d = mu.claims[claim_ids[0]].stalk.shape[0]
    new_stalk = np.zeros(d)
    for alpha_i, cid in zip(w, claim_ids):
        new_stalk += alpha_i * mu.claims[cid].stalk

    t_new     = mu.t + 1
    prov_hash = hashlib.sha256(
        (synthesis_key + PROTOCOL_VERSION).encode()
    ).hexdigest()[:16]
    prov = Provenance(
        parent_ids=tuple(claim_ids),
        operator_id=f"Psi:{synthesis_key}",
        timestamp=now_iso(),
    )
    new_claim = Claim(provenance=prov, payload=payload, stalk=new_stalk, t=t_new)

    new_claims = dict(mu.claims)
    new_claims[new_claim.id] = new_claim

    new_ents = dict(mu.entailments)
    for alpha_i, cid in zip(w, claim_ids):
        # Restriction map (E-301-003): F(child_i → new) = alpha_i · I
        # Multi-source check: Σᵢ (alpha_i · I)(stalk_i) = stalk_new  ✓
        src_d = mu.claims[cid].stalk.shape[0]
        ent   = Entailment(
            source_id=cid,
            target_id=new_claim.id,
            etype=EntailmentType.SYNTHESIS,
            restriction=alpha_i * np.eye(src_d),
            predicate_hash=prov_hash,
        )
        new_ents[(cid, new_claim.id)] = ent

    new_active = (mu.active - frozenset(claim_ids)) | frozenset([new_claim.id])

    new_state = MuState(
        t=t_new,
        claims=new_claims,
        entailments=new_ents,
        active=new_active,
        S=mu.next_S(),
        alpha=mu.alpha,
    )

    # Consistency guard (E-301-003): forward entailment consistency (multi-source)
    if not is_valid(new_state):
        raise SynthesisError(
            "CONSISTENCY_ERROR: is_valid(mu_1) failed after Ψ — "
            "weighted sum inconsistency. Reverting."
        )

    return new_state, cost


# ---------------------------------------------------------------------------
# Ω — Observation
# ---------------------------------------------------------------------------

def apply_omega(
    mu:             MuState,
    claim_id:       str,
    confluence_cert: str,
) -> dict:
    """
    Ω(v) → Artifact

    Preconditions:
      • claim_id ∈ W_t
      • is_valid(μ_t) — forward entailment consistency (E-301-003)
      • confluence_cert is non-empty (issued by confluence.py)

    Cost C₀ = 0.0 (observation is free — no budget charge).

    Returns Artifact dict. Does NOT modify MuState (caller marks claim OBSERVED
    by removing from active and sealing).
    """
    if claim_id not in mu.active:
        raise ObservationError(f"PRECONDITION: {claim_id} not in W_t.")
    if not is_valid(mu):
        raise ObservationError(
            "VALIDITY_FAIL: forward entailment consistency violated. "
            "State is inconsistent; Ω blocked."
        )
    if not confluence_cert:
        raise ObservationError("CONFLUENCE_CERT_MISSING: obtain cert from confluence.py first.")

    # Build Merkle path: sequence of H values from t=0 to t=current
    # (Caller passes mu with sealed H_t; path is embedded in state chain)
    merkle_path = [mu.H]   # full chain requires archive; minimally the current hash

    artifact = {
        "claim_id":        claim_id,
        "payload":         mu.claims[claim_id].payload,
        "stalk":           mu.claims[claim_id].stalk.tolist(),
        "K_bound":         mu.claims[claim_id].K_bound,
        "merkle_path":     merkle_path,
        "confluence_cert": confluence_cert,
        "state_hash":      mu.H,
        "t":               mu.t,
        "protocol_version": PROTOCOL_VERSION,
    }
    return artifact


# ---------------------------------------------------------------------------
# R3 — Tensor product artifact and joint observation (ENGINE_AXIOMS §5.5)
# ---------------------------------------------------------------------------

def tensor_product_artifact(
    art1:    dict,
    art2:    dict,
    weights: List[float] = None,
) -> dict:
    """
    Monoidal product: Art_A ⊗ Art_B → Art_tensor

    Defined on Artifact dicts produced by apply_omega.
    stalk(A⊗B) = w_A·stalk(A) + w_B·stalk(B)   (same weighted sum as Ψ)

    R3 invariant: stalk(Ω(Ψ(A,B))) == stalk(Ω(A) ⊗ Ω(B))
    Proof: stalk(v_AB) = Σᵢ αᵢ·stalk(vᵢ) by Ψ construction;
           tensor uses same αᵢ weights; equality is exact.

    K-bound factorization: K(A⊗B) = K(A) + K(B) (not claimed to be tight;
    the synthesised payload may be shorter — that is the information gain of Ψ).
    """
    if weights is None:
        weights = [0.5, 0.5]
    w = np.array(weights, dtype=float)
    w = w / w.sum()
    s1 = np.array(art1["stalk"], dtype=float)
    s2 = np.array(art2["stalk"], dtype=float)
    stalk_product = w[0] * s1 + w[1] * s2
    return {
        "type":             "TENSOR_PRODUCT",
        "claim_ids":        [art1["claim_id"], art2["claim_id"]],
        "payloads":         [art1["payload"],   art2["payload"]],
        "stalk":            stalk_product.tolist(),
        "K_bound_sum":      art1["K_bound"] + art2["K_bound"],
        "K_synthesis_gain": (art1["K_bound"] + art2["K_bound"]) - art1.get("K_bound", 0),
        "weights":          w.tolist(),
        "confluence_certs": [art1["confluence_cert"], art2["confluence_cert"]],
        "state_hashes":     [art1["state_hash"],      art2["state_hash"]],
        "t":                max(art1["t"], art2["t"]),
        "protocol_version": PROTOCOL_VERSION,
    }


def check_r3(
    art_psi:    dict,
    art_tensor: dict,
    tol:        float = 1e-10,
) -> Tuple[bool, float]:
    """
    R3 stalk invariant: ||stalk(Ω(Ψ(A,B))) − stalk(Ω(A)⊗Ω(B))|| < tol

    Returns (passes: bool, err: float).
    """
    s_psi    = np.array(art_psi["stalk"],    dtype=float)
    s_tensor = np.array(art_tensor["stalk"], dtype=float)
    err = float(np.linalg.norm(s_psi - s_tensor))
    return err < tol, err


def apply_omega_tensor(
    mu:             MuState,
    claim_ids:      List[str],
    certs:          List[str],
    weights:        List[float] = None,
) -> dict:
    """
    Ω⊗(v_1, ..., v_k) → TensorArtifact

    Joint observation of k matroid-independent claims.
    Preconditions:
      • ∀ i: claim_ids[i] ∈ W_t
      • is_valid(μ_t)
      • Matroid independence: r(M_{v_1} ∨ ... ∨ M_{v_k}) = Σᵢ r(M_{v_i})
      • ∀ i: certs[i] non-empty (issued by ConfluenceRegistry)

    Returns TensorArtifact dict (type="TENSOR_PRODUCT") over the k claims.
    Cost C₀ = 0.0 (observation is free).

    Raises ObservationError if preconditions fail.
    """
    k = len(claim_ids)
    if len(certs) != k:
        raise ObservationError(f"PRECONDITION: len(certs)={len(certs)} != k={k}.")
    for cid in claim_ids:
        if cid not in mu.active:
            raise ObservationError(f"PRECONDITION: {cid} not in W_t.")
    if not is_valid(mu):
        raise ObservationError("VALIDITY_FAIL: forward entailment consistency violated.")
    if not _check_matroid_independence(mu, claim_ids):
        raise ObservationError(
            "MATROID_VIOLATION: claims are not matroid-independent. "
            "R3 requires r(M_{v_1}∨...∨M_{v_k}) = Σᵢ r(M_{v_i})."
        )
    for cert in certs:
        if not cert:
            raise ObservationError("CONFLUENCE_CERT_MISSING: all certs must be non-empty.")

    # Observe each component
    arts = [apply_omega(mu, cid, cert) for cid, cert in zip(claim_ids, certs)]

    # Build tensor product iteratively
    if weights is None:
        weights = [1.0 / k] * k
    w = np.array(weights, dtype=float); w = w / w.sum()

    result = arts[0].copy()
    result = {
        "type":             "TENSOR_PRODUCT",
        "claim_ids":        [a["claim_id"] for a in arts],
        "payloads":         [a["payload"]  for a in arts],
        "stalk":            sum(w[i] * np.array(arts[i]["stalk"]) for i in range(k)).tolist(),
        "K_bound_sum":      sum(a["K_bound"] for a in arts),
        "weights":          w.tolist(),
        "confluence_certs": [a["confluence_cert"] for a in arts],
        "state_hashes":     [a["state_hash"]      for a in arts],
        "t":                mu.t,
        "protocol_version": PROTOCOL_VERSION,
    }
    return result


# ---------------------------------------------------------------------------
# Γ — Spatial Subdivision Operator (EXP-303)
# ---------------------------------------------------------------------------

# Spatial partition keys and their N values
SPATIAL_KEYS = {
    "axis_bisect_x": 2,
    "axis_bisect_y": 2,
    "axis_bisect_z": 2,
    "octree_split":  8,
}


def _compute_child_bboxes(
    parent_bbox: Tuple[np.ndarray, np.ndarray],
    key: str,
) -> List[Tuple[np.ndarray, np.ndarray]]:
    """
    Compute child bounding boxes for a given spatial partition key.
    Returns list of (lo, hi) tuples, one per child.

    axis_bisect_x/y/z: N=2, bisect along the named axis.
    octree_split:      N=8, bisect all three axes simultaneously.
      Children ordered by 3-bit index (bit2=x, bit1=y, bit0=z):
        i=0: (lo_x, lo_y, lo_z)  i=1: (lo_x, lo_y, hi_z)
        i=2: (lo_x, hi_y, lo_z)  i=3: (lo_x, hi_y, hi_z)
        i=4: (hi_x, lo_y, lo_z)  i=5: (hi_x, lo_y, hi_z)
        i=6: (hi_x, hi_y, lo_z)  i=7: (hi_x, hi_y, hi_z)
    """
    lo, hi = np.array(parent_bbox[0], dtype=float), np.array(parent_bbox[1], dtype=float)
    mid = (lo + hi) / 2.0

    if key == "axis_bisect_x":
        return [
            (lo.copy(),              np.array([mid[0], hi[1], hi[2]])),
            (np.array([mid[0], lo[1], lo[2]]), hi.copy()),
        ]
    elif key == "axis_bisect_y":
        return [
            (lo.copy(),              np.array([hi[0], mid[1], hi[2]])),
            (np.array([lo[0], mid[1], lo[2]]), hi.copy()),
        ]
    elif key == "axis_bisect_z":
        return [
            (lo.copy(),              np.array([hi[0], hi[1], mid[2]])),
            (np.array([lo[0], lo[1], mid[2]]), hi.copy()),
        ]
    elif key == "octree_split":
        corners = [lo, mid]   # corners[0]=lo half, corners[1]=hi half
        bboxes = []
        for ix in range(2):
            for iy in range(2):
                for iz in range(2):
                    c_lo = np.array([corners[ix][0], corners[iy][1], corners[iz][2]])
                    c_hi = np.array([corners[1-ix if ix==0 else ix][0],
                                     corners[1-iy if iy==0 else iy][1],
                                     corners[1-iz if iz==0 else iz][2]])
                    # Simpler: lo = [mid[d] if bit set else lo[d]], hi = [hi[d] if bit set else mid[d]]
                    c_lo2 = np.array([mid[0] if ix else lo[0],
                                      mid[1] if iy else lo[1],
                                      mid[2] if iz else lo[2]])
                    c_hi2 = np.array([hi[0] if ix else mid[0],
                                      hi[1] if iy else mid[1],
                                      hi[2] if iz else mid[2]])
                    bboxes.append((c_lo2, c_hi2))
        return bboxes
    else:
        raise PartitionError(f"UNKNOWN_SPATIAL_KEY: '{key}' not in SPATIAL_KEYS.")


def apply_gamma(
    mu:            MuState,
    claim_id:      str,
    partition_key: str,
    payloads:      List[str],
    beta:          float,
    budget:        float,
    spent:         float,
) -> Tuple[MuState, float]:
    """
    Γ(v, partition_key) → {v_1, ..., v_N}

    Spatial subdivision operator (EXP-303).

    Two independent channels:
      Algebraic: uses _orthogonal_decompose (sum conservation, same as Φ)
        Σᵢ stalk(child_i) = stalk(parent)  — unchanged
      Geometric: assigns bbox to each child via _compute_child_bboxes
        bbox(child_i) ⊂ bbox(parent)  — spatial containment invariant

    Preconditions:
      • claim_id ∈ W_t
      • partition_key ∈ SPATIAL_KEYS
      • mu.claims[claim_id].bbox is not None  (parent must have bbox declared)
      • K-bound (same as Φ, C_KBOUND·log(N))
      • dim check: d ≥ N (from _orthogonal_decompose)

    Post-conditions:
      • is_valid(new_state)   [forward entailment consistency on algebraic stalks]
      • is_spatially_valid(new_state)  [bbox containment on SPATIAL edges]

    Entailment type: EntailmentType.SPATIAL (distinct from PARTITION).
    Cost: C₀ = 1.0 (same as Φ), with backreaction.
    """
    from engine.validity import is_spatially_valid
    from engine.state import EntailmentType

    if claim_id not in mu.active:
        raise PartitionError(f"PRECONDITION: {claim_id} not in W_t.")
    if partition_key not in SPATIAL_KEYS:
        raise PartitionError(
            f"UNKNOWN_SPATIAL_KEY: '{partition_key}'. "
            f"Valid keys: {list(SPATIAL_KEYS.keys())}"
        )
    N = SPATIAL_KEYS[partition_key]
    if len(payloads) != N:
        raise PartitionError(f"PRECONDITION: len(payloads)={len(payloads)} != N={N}.")

    parent = mu.claims[claim_id]
    if parent.bbox is None:
        raise PartitionError(
            f"PRECONDITION: claim {claim_id} has no bbox. "
            "Spatial subdivision requires a declared bounding box on the parent claim."
        )

    # K-bound (same as Φ)
    k_children = sum(len(zlib.compress(p.encode("utf-8"), level=9)) for p in payloads)
    k_limit = parent.K_bound + C_KBOUND * math.log(N)
    if k_children > k_limit:
        raise PartitionError(
            f"INFORMATION_OVERFLOW: Σ K(children)={k_children:.1f} > "
            f"K(parent)+c*log(N)={k_limit:.2f}"
        )

    # Backreaction cost
    cost = _cost(1.0, beta, mu.S)
    if spent + cost > budget:
        raise BudgetExceeded(
            f"Budget exceeded: spent={spent:.4f} + cost={cost:.4f} > B₀={budget}"
        )

    # Algebraic channel: orthogonal stalk decomposition
    stalks = _orthogonal_decompose(
        parent.stalk, N, seed=hash(partition_key) % (2**31)
    )

    # Geometric channel: compute child bboxes
    child_bboxes = _compute_child_bboxes(parent.bbox, partition_key)

    # Build child claims + SPATIAL entailments
    t_new     = mu.t + 1
    prov_hash = hashlib.sha256(
        (partition_key + PROTOCOL_VERSION).encode()
    ).hexdigest()[:16]
    new_claims = dict(mu.claims)
    new_ents   = dict(mu.entailments)
    child_ids  = []

    for i, (payload, stalk_i, bbox_i) in enumerate(zip(payloads, stalks, child_bboxes)):
        prov = Provenance(
            parent_ids=(claim_id,),
            operator_id=f"Gamma:{partition_key}:{i}",
            timestamp=now_iso(),
        )
        child = Claim(
            provenance=prov,
            payload=payload,
            stalk=stalk_i,
            t=t_new,
            bbox=bbox_i,   # geometric metadata
        )
        new_claims[child.id] = child
        child_ids.append(child.id)

        # Algebraic restriction map (same as Φ)
        restriction = _phi_restriction(stalk_i, parent.stalk)
        ent = Entailment(
            source_id=claim_id,
            target_id=child.id,
            etype=EntailmentType.SPATIAL,
            restriction=restriction,
            predicate_hash=prov_hash,
        )
        new_ents[(claim_id, child.id)] = ent

    new_active = (mu.active - {claim_id}) | frozenset(child_ids)
    new_state  = MuState(
        t=t_new,
        claims=new_claims,
        entailments=new_ents,
        active=new_active,
        S=mu.next_S(),
        alpha=mu.alpha,
    )

    # Algebraic validity
    if not is_valid(new_state):
        raise PartitionError(
            "CONSISTENCY_ERROR: is_valid failed after Γ — "
            "algebraic restriction maps mis-calibrated. Reverting."
        )

    # Spatial validity
    if not is_spatially_valid(new_state):
        raise PartitionError(
            "SPATIAL_CONTAINMENT_ERROR: bbox(child) ⊄ bbox(parent) after Γ. "
            "Geometric channel invariant violated. Reverting."
        )

    return new_state, cost


# ===========================================================================
# EXP-304 — Φ_B (Sector B barycentric partition) + Γ_304 (dual-sector Gamma)
# ===========================================================================

SECTOR_A_DIMS = (0, 1, 2, 3)   # [mass, r, g, b]  sum-conserved
SECTOR_B_DIMS = (4, 5, 6, 7)   # [x, y, z, w]     barycentric, w=1


def apply_phi_b(
    mu,
    claim_id:   str,
    N:          int,
    payloads:   list,
    beta:       float,
    budget:     float,
    spent:      float,
    weights:    list = None,
) -> tuple:
    """
    Φ_B — Sector B barycentric partition (EXP-304).

    Algebraic:
      stalk_B(child_i) = [centroid_x(bbox_i), centroid_y(bbox_i), centroid_z(bbox_i), 1.0]
      Σᵢ ωᵢ · stalk_B(child_i) = stalk_B(parent)  iff ωᵢ = vol(bbox_i)/vol(parent)
      or uniformly ωᵢ = 1/N when all bboxes are equal.

    Preconditions:
      - claim is in mu.active (not retired)
      - claim.bbox is not None (bbox required for centroid assignment)
      - N >= 2
      - K-bound: Σᵢ K(payload_i) ≤ K(parent) + C_KBOUND·log(N)

    Sector A (dims 0–3) is NOT touched by Φ_B; it remains on the parent.
    Φ_B is called from apply_gamma_304 after Sector A is decomposed by Φ_A.

    Returns: (new_mu, cost)
    """
    from engine.validity import is_valid_b, is_spatially_valid, is_valid
    import math

    if claim_id not in mu.active:
        raise PartitionError(f"PHI_B_ERROR: claim {claim_id} not in active set.")

    parent = mu.claims[claim_id]
    if parent.bbox is None:
        raise PartitionError(f"PHI_B_ERROR: claim {claim_id} has no bbox; Sector B centroid undefined.")

    d = parent.stalk.shape[0]
    if d <= SECTOR_B_DIMS[-1]:
        raise PartitionError(f"PHI_B_ERROR: stalk dim={d} < {SECTOR_B_DIMS[-1]+1}; Sector B inaccessible.")

    if len(payloads) != N:
        raise PartitionError(f"PHI_B_ERROR: expected {N} payloads, got {len(payloads)}.")

    # K-bound
    k_children = sum(len(zlib.compress(p.encode("utf-8"), level=9)) for p in payloads)
    k_limit = parent.K_bound + C_KBOUND * math.log(N)
    if k_children > k_limit:
        raise PartitionError(
            f"PHI_B_INFORMATION_OVERFLOW: Σ K(children)={k_children:.1f} > "
            f"K(parent)+c*log(N)={k_limit:.2f}"
        )

    # Normalise weights
    if weights is None:
        omegas = [1.0 / N] * N
    else:
        total = sum(weights)
        omegas = [w / total for w in weights]
    assert all(o > 0 for o in omegas), "PHI_B_ERROR: all weights must be positive."

    # Backreaction cost
    cost = _cost(C0=1.0, beta=beta, S=mu.S)
    if spent + cost > budget:
        raise PartitionError(
            f"PHI_B_BUDGET: spent={spent:.4f} + cost={cost:.4f} > B0={budget}"
        )

    # Build child claims — Sector B centroid from bbox
    t_new = mu.t + 1
    lo, hi = parent.bbox
    mid = (lo + hi) / 2.0

    # Child bboxes: axis_bisect_x used if N=2, else uniform bbox (caller must
    # have already run _compute_child_bboxes via apply_gamma_304)
    # For standalone Φ_B (no spatial key), assign parent bbox to all children.
    child_bboxes = [parent.bbox] * N  # default: inherit parent bbox

    new_claims = dict(mu.claims)
    new_entailments = dict(mu.entailments)
    child_ids = []

    b0, b1 = SECTOR_B_DIMS[0], SECTOR_B_DIMS[-1] + 1  # slice [4:8]

    for i, (payload, omega) in enumerate(zip(payloads, omegas)):
        # Sector B stalk: centroid of child bbox + w=1
        c_lo, c_hi = child_bboxes[i]
        centroid = (c_lo + c_hi) / 2.0  # ℝ^3

        child_stalk = parent.stalk.copy()
        child_stalk[b0:b0+3] = centroid
        child_stalk[SECTOR_B_DIMS[-1]] = 1.0   # w = 1.0

        prov = Provenance(
            parent_ids=(claim_id,),
            operator_id=f"PhiB:{i}",
            timestamp=now_iso(),
        )
        child = Claim(provenance=prov, payload=payload, stalk=child_stalk,
                      t=t_new, bbox=child_bboxes[i])
        child_ids.append(child.id)
        new_claims[child.id] = child

        # Restriction map: project parent Sector B → child Sector B
        F = np.zeros((d, d))
        # Sector A: pass-through (identity block dims 0–3)
        for j in SECTOR_A_DIMS:
            F[j, j] = 1.0
        # Sector B: omega · I on [x,y,z]; 1.0 on w
        for j in SECTOR_B_DIMS[:3]:
            F[j, j] = omega
        F[SECTOR_B_DIMS[-1], SECTOR_B_DIMS[-1]] = 1.0

        # Sector B restriction: outer(stalk_B_child, stalk_B_parent) / ||stalk_B_parent||^2
        stalk_B_parent = parent.stalk[b0:b1]
        stalk_B_norm_sq = float(np.dot(stalk_B_parent, stalk_B_parent))
        if stalk_B_norm_sq > 1e-30:
            F[b0:b1, b0:b1] = np.outer(child_stalk[b0:b1], stalk_B_parent) / stalk_B_norm_sq

        det_sign_val = float(np.linalg.det(F[b0:b1, b0:b1]))
        det_sign = int(np.sign(det_sign_val)) if abs(det_sign_val) > 1e-30 else 1

        ent = Entailment(
            source_id=claim_id,
            target_id=child.id,
            etype=EntailmentType.PARTITION,
            restriction=F,
            predicate_hash=hashlib.sha256(F.tobytes()).hexdigest()[:16],
            omega=omega,
            det_sign=det_sign,
        )
        new_entailments[(claim_id, child.id)] = ent

    new_active = (mu.active - {claim_id}) | frozenset(child_ids)

    new_state = MuState(
        t=t_new,
        claims=new_claims,
        entailments=new_entailments,
        active=new_active,
        S=mu.next_S(),
        alpha=mu.alpha,
    )
    new_state.seal()

    if not is_valid_b(new_state):
        raise PartitionError(
            "PHI_B_CONSISTENCY_ERROR: is_valid_b failed — "
            "barycentric constraint or w=1 invariant violated."
        )

    return new_state, cost


def apply_gamma_304(
    mu,
    claim_id:      str,
    partition_key: str,
    payloads:      list,
    beta:          float,
    budget:        float,
    spent:         float,
    weights:       list = None,
) -> tuple:
    """
    Γ_304 — Dual-sector spatial partition (EXP-304).

    Two independent channels applied in sequence:

      Channel 1 — Geometric: _compute_child_bboxes(bbox_parent, key) → child bboxes
      Channel 2A — Algebraic Sector A: _orthogonal_decompose on stalk[0:4] (sum conservation)
      Channel 2B — Algebraic Sector B: centroid(child_bbox) → stalk[4:7], w=1.0

    Barycentric weights ωᵢ = vol(child_bbox_i) / vol(parent_bbox)
    (= 1/N for uniform subdivision, e.g. axis_bisect and octree_split).

    Validity: is_valid_A ∧ is_valid_B ∧ is_spatially_valid.

    Returns: (new_mu, cost)
    """
    from engine.validity import is_valid, is_valid_b, is_spatially_valid
    import math

    if claim_id not in mu.active:
        raise PartitionError(f"GAMMA304_ERROR: claim {claim_id} not in active set.")

    parent = mu.claims[claim_id]
    if parent.bbox is None:
        raise PartitionError(f"GAMMA304_ERROR: claim {claim_id} has no bbox.")

    d = parent.stalk.shape[0]
    if d != 8:
        raise PartitionError(f"GAMMA304_ERROR: EXP-304 requires d=8, got d={d}.")

    if partition_key not in SPATIAL_KEYS:
        raise PartitionError(
            f"GAMMA304_UNKNOWN_KEY: '{partition_key}' not in {list(SPATIAL_KEYS.keys())}."
        )
    N = SPATIAL_KEYS[partition_key]

    if len(payloads) != N:
        raise PartitionError(f"GAMMA304_ERROR: expected {N} payloads, got {len(payloads)}.")

    # K-bound
    k_children = sum(len(zlib.compress(p.encode("utf-8"), level=9)) for p in payloads)
    k_limit = parent.K_bound + C_KBOUND * math.log(N)
    if k_children > k_limit:
        raise PartitionError(
            f"GAMMA304_INFORMATION_OVERFLOW: Σ K(children)={k_children:.1f} > "
            f"K(parent)+c*log(N)={k_limit:.2f}"
        )

    # Backreaction cost
    cost = _cost(C0=1.0, beta=beta, S=mu.S)
    if spent + cost > budget:
        raise PartitionError(
            f"GAMMA304_BUDGET: spent={spent:.4f} + cost={cost:.4f} > B0={budget}"
        )

    # --- Geometric channel: child bboxes ---
    child_bboxes = _compute_child_bboxes(parent.bbox, partition_key)

    # --- Barycentric weights from bbox volumes ---
    p_lo, p_hi = parent.bbox
    parent_vol = float(np.prod(p_hi - p_lo))
    if parent_vol < 1e-30:
        omegas = [1.0 / N] * N   # degenerate bbox: uniform
    else:
        vols = [float(np.prod(cb[1] - cb[0])) for cb in child_bboxes]
        total_vol = sum(vols)
        omegas = [v / total_vol for v in vols]

    if weights is not None:
        total = sum(weights)
        omegas = [w / total for w in weights]

    # --- Sector A: orthogonal decompose ---
    # If N <= d_A (4), decompose Sector A slice only.
    # If N > d_A (e.g. octree N=8), decompose full d=8 stalk so d >= N,
    # then Sector A conservation holds from the sum property: Σ child[0:4] = parent[0:4].
    stalk_A = parent.stalk[SECTOR_A_DIMS[0]:SECTOR_A_DIMS[-1]+1]   # ℝ^4
    d_A = len(SECTOR_A_DIMS)
    if N <= d_A:
        stalk_A_children = _orthogonal_decompose(stalk_A, N)        # list of ℝ^4
    else:
        # Decompose full stalk; take Sector A slice of each child
        full_children = _orthogonal_decompose(parent.stalk, N)      # list of ℝ^8
        stalk_A_children = [c[SECTOR_A_DIMS[0]:SECTOR_A_DIMS[-1]+1] for c in full_children]

    # --- Build child claims ---
    t_new = mu.t + 1
    new_claims = dict(mu.claims)
    new_entailments = dict(mu.entailments)
    child_ids = []

    b0A, b1A = SECTOR_A_DIMS[0], SECTOR_A_DIMS[-1] + 1   # [0:4]
    b0B, b1B = SECTOR_B_DIMS[0], SECTOR_B_DIMS[-1] + 1   # [4:8]

    for i, (payload, omega, stalk_A_i, (c_lo, c_hi)) in enumerate(
            zip(payloads, omegas, stalk_A_children, child_bboxes)):

        centroid_B = (c_lo + c_hi) / 2.0  # ℝ^3 centroid of child bbox

        child_stalk = np.empty(d)
        child_stalk[b0A:b1A] = stalk_A_i          # Sector A: orthogonal split
        child_stalk[b0B:b0B+3] = centroid_B        # Sector B xyz: bbox centroid
        child_stalk[SECTOR_B_DIMS[-1]] = 1.0       # Sector B w: homogeneous = 1

        prov = Provenance(
            parent_ids=(claim_id,),
            operator_id=f"Gamma304:{partition_key}:{i}",
            timestamp=now_iso(),
        )
        child = Claim(provenance=prov, payload=payload, stalk=child_stalk,
                      t=t_new, bbox=(c_lo, c_hi))
        child_ids.append(child.id)
        new_claims[child.id] = child

        # Restriction map (full d=8):
        #   Sector A: outer(stalk_A_i, stalk_A_parent) / ||stalk_A_parent||²
        #   Sector B: omega·I on [x,y,z]; 1.0 on w
        F = np.zeros((d, d))
        stalk_A_norm_sq = float(np.dot(stalk_A, stalk_A))
        if stalk_A_norm_sq > 1e-30:
            F[b0A:b1A, b0A:b1A] = np.outer(stalk_A_i, stalk_A) / stalk_A_norm_sq
        else:
            F[b0A:b1A, b0A:b1A] = np.zeros((4, 4))
        for j in range(3):
            F[b0B+j, b0B+j] = omega
        F[SECTOR_B_DIMS[-1], SECTOR_B_DIMS[-1]] = 1.0

        # Sector B restriction: outer(stalk_B_child, stalk_B_parent) / ||stalk_B_parent||^2
        # Satisfies: F_B @ stalk_B_parent = stalk_B_child  (exact, by construction)
        stalk_B_parent = parent.stalk[b0B:b1B]
        stalk_B_norm_sq = float(np.dot(stalk_B_parent, stalk_B_parent))
        if stalk_B_norm_sq > 1e-30:
            F[b0B:b1B, b0B:b1B] = np.outer(child_stalk[b0B:b1B], stalk_B_parent) / stalk_B_norm_sq
        # else: zero block (degenerate)

        det_B = float(np.linalg.det(F[b0B:b1B, b0B:b1B]))
        det_sign = int(np.sign(det_B)) if abs(det_B) > 1e-30 else 1

        ent_spatial = Entailment(
            source_id=claim_id,
            target_id=child.id,
            etype=EntailmentType.SPATIAL,
            restriction=F,
            predicate_hash=hashlib.sha256(F.tobytes()).hexdigest()[:16],
            omega=omega,
            det_sign=det_sign,
        )
        new_entailments[(claim_id, child.id)] = ent_spatial

    new_active = (mu.active - {claim_id}) | frozenset(child_ids)

    new_state = MuState(
        t=t_new,
        claims=new_claims,
        entailments=new_entailments,
        active=new_active,
        S=mu.next_S(),
        alpha=mu.alpha,
    )
    new_state.seal()

    if not is_valid(new_state):
        raise PartitionError(
            "GAMMA304_CONSISTENCY_ERROR: is_valid (Sector A) failed. Reverting."
        )
    if not is_valid_b(new_state):
        raise PartitionError(
            "GAMMA304_CONSISTENCY_ERROR: is_valid_b (Sector B) failed. Reverting."
        )
    if not is_spatially_valid(new_state):
        raise PartitionError(
            "GAMMA304_SPATIAL_ERROR: bbox containment violated. Reverting."
        )

    return new_state, cost


# ===========================================================================
# EXP-305 -- Gamma_305 (triple-sector: Sector A + B + C with unit-norm Phi_C)
# ===========================================================================

SECTOR_C_DIMS = (8, 9, 10)   # [nx, ny, nz]  axial pseudo-vector, unit-norm


def apply_gamma_305(
    mu,
    claim_id,
    partition_key,
    payloads,
    beta,
    budget,
    spent,
    weights=None,
):
    """
    Gamma_305 -- Triple-sector spatial partition (EXP-305).
    Channels:
      1  Geometric:   _compute_child_bboxes(bbox_parent, key)
      2A Sector A:    Phi_A (sum conservation, dims 0-3)
      2B Sector B:    Phi_B (bbox centroid, w=1.0, dims 4-7)
      2C Sector C:    Phi_C (L2-normalize child normals, dims 8-10)
    Restriction map: block-diagonal 11x11 (F_A, F_B, F_C on-diagonal only).
    Returns: (new_mu, cost)
    """
    from engine.validity import (
        is_valid, is_valid_b, is_spatially_valid,
        is_unit_norm, is_valid_block_diagonal,
    )

    if claim_id not in mu.active:
        raise PartitionError(f"GAMMA305_ERROR: claim {claim_id} not in active set.")
    parent = mu.claims[claim_id]
    if parent.bbox is None:
        raise PartitionError(f"GAMMA305_ERROR: claim {claim_id} has no bbox.")
    d = parent.stalk.shape[0]
    if d != 11:
        raise PartitionError(f"GAMMA305_ERROR: EXP-305 requires d=11, got d={d}.")
    if partition_key not in SPATIAL_KEYS:
        raise PartitionError(
            f"GAMMA305_UNKNOWN_KEY: '{partition_key}' not in {list(SPATIAL_KEYS.keys())}."
        )
    N = SPATIAL_KEYS[partition_key]
    if len(payloads) != N:
        raise PartitionError(f"GAMMA305_ERROR: expected {N} payloads, got {len(payloads)}.")

    k_children = sum(len(zlib.compress(p.encode("utf-8"), level=9)) for p in payloads)
    k_limit = parent.K_bound + C_KBOUND * math.log(N)
    if k_children > k_limit:
        raise PartitionError(
            f"GAMMA305_INFORMATION_OVERFLOW: sum K(children)={k_children:.1f} > "
            f"K(parent)+c*log(N)={k_limit:.2f}"
        )

    cost = _cost(C0=1.0, beta=beta, S=mu.S)
    if spent + cost > budget:
        raise PartitionError(
            f"GAMMA305_BUDGET: spent={spent:.4f} + cost={cost:.4f} > B0={budget}"
        )

    child_bboxes = _compute_child_bboxes(parent.bbox, partition_key)

    p_lo, p_hi = parent.bbox
    parent_vol = float(np.prod(p_hi - p_lo))
    if parent_vol < 1e-30:
        omegas = [1.0 / N] * N
    else:
        vols = [float(np.prod(cb[1] - cb[0])) for cb in child_bboxes]
        total_vol = sum(vols)
        omegas = [v / total_vol for v in vols]
    if weights is not None:
        total = sum(weights)
        omegas = [w / total for w in weights]

    b0A, b1A = SECTOR_A_DIMS[0], SECTOR_A_DIMS[-1] + 1
    b0B, b1B = SECTOR_B_DIMS[0], SECTOR_B_DIMS[-1] + 1
    b0C, b1C = SECTOR_C_DIMS[0], SECTOR_C_DIMS[-1] + 1

    stalk_A = parent.stalk[b0A:b1A]
    d_A = len(SECTOR_A_DIMS)
    d_C = len(SECTOR_C_DIMS)
    full_children_cache = None

    if N <= d_A:
        stalk_A_children = _orthogonal_decompose(stalk_A, N)
    else:
        full_children_cache = _orthogonal_decompose(parent.stalk, N)
        stalk_A_children = [c[b0A:b1A] for c in full_children_cache]

    stalk_C_parent = parent.stalk[b0C:b1C]
    stalk_C_norm = float(np.linalg.norm(stalk_C_parent))
    stalk_C_unit = stalk_C_parent / stalk_C_norm if stalk_C_norm >= 1e-12 else np.array([0.0, 0.0, 1.0])

    if N <= d_C:
        raw_C_children = _orthogonal_decompose(stalk_C_parent, N)
    else:
        if full_children_cache is None:
            full_children_cache = _orthogonal_decompose(parent.stalk, N)
        raw_C_children = [c[b0C:b1C] for c in full_children_cache]

    stalk_C_children = []
    for raw_c in raw_C_children:
        r_norm = float(np.linalg.norm(raw_c))
        stalk_C_children.append(raw_c / r_norm if r_norm >= 1e-12 else stalk_C_unit.copy())

    t_new = mu.t + 1
    new_claims = dict(mu.claims)
    new_entailments = dict(mu.entailments)
    child_ids = []

    stalk_A_parent = parent.stalk[b0A:b1A]
    stalk_B_parent = parent.stalk[b0B:b1B]

    stalk_A_nsq = float(np.dot(stalk_A_parent, stalk_A_parent))
    stalk_B_nsq = float(np.dot(stalk_B_parent, stalk_B_parent))
    stalk_C_nsq = float(np.dot(stalk_C_parent, stalk_C_parent))

    for i, (payload, omega, stalk_A_i, (c_lo, c_hi), n_child) in enumerate(
            zip(payloads, omegas, stalk_A_children, child_bboxes, stalk_C_children)):

        centroid_B = (c_lo + c_hi) / 2.0

        child_stalk = np.empty(d)
        child_stalk[b0A:b1A] = stalk_A_i
        child_stalk[b0B:b0B+3] = centroid_B
        child_stalk[SECTOR_B_DIMS[-1]] = 1.0
        child_stalk[b0C:b1C] = n_child

        prov = Provenance(
            parent_ids=(claim_id,),
            operator_id=f"Gamma305:{partition_key}:{i}",
            timestamp=now_iso(),
        )
        child = Claim(provenance=prov, payload=payload, stalk=child_stalk,
                      t=t_new, bbox=(c_lo, c_hi))
        child_ids.append(child.id)
        new_claims[child.id] = child

        F = np.zeros((d, d))
        if stalk_A_nsq > 1e-30:
            F[b0A:b1A, b0A:b1A] = np.outer(stalk_A_i, stalk_A_parent) / stalk_A_nsq
        if stalk_B_nsq > 1e-30:
            F[b0B:b1B, b0B:b1B] = np.outer(child_stalk[b0B:b1B], stalk_B_parent) / stalk_B_nsq
        if stalk_C_nsq > 1e-30:
            F[b0C:b1C, b0C:b1C] = np.outer(n_child, stalk_C_parent) / stalk_C_nsq

        det_B = float(np.linalg.det(F[b0B:b1B, b0B:b1B]))
        det_sign = int(np.sign(det_B)) if abs(det_B) > 1e-30 else 1

        ent_spatial = Entailment(
            source_id=claim_id,
            target_id=child.id,
            etype=EntailmentType.SPATIAL,
            restriction=F,
            predicate_hash=hashlib.sha256(F.tobytes()).hexdigest()[:16],
            omega=omega,
            det_sign=det_sign,
        )
        new_entailments[(claim_id, child.id)] = ent_spatial

    new_active = (mu.active - {claim_id}) | frozenset(child_ids)
    new_state = MuState(
        t=t_new,
        claims=new_claims,
        entailments=new_entailments,
        active=new_active,
        S=mu.next_S(),
        alpha=mu.alpha,
    )
    new_state.seal()

    if not is_valid(new_state):
        raise PartitionError("GAMMA305_CONSISTENCY_ERROR: is_valid (Sector A) failed.")
    if not is_valid_b(new_state):
        raise PartitionError("GAMMA305_CONSISTENCY_ERROR: is_valid_b (Sector B) failed.")
    if not is_unit_norm(new_state):
        raise PartitionError("GAMMA305_UNIT_NORM_ERROR: is_unit_norm (Sector C) failed.")
    if not is_spatially_valid(new_state):
        raise PartitionError("GAMMA305_SPATIAL_ERROR: bbox containment violated.")
    if not is_valid_block_diagonal(new_state):
        raise PartitionError("GAMMA305_BLOCK_DIAGONAL_ERROR: off-diagonal sector coupling detected.")

    return new_state, cost


# ===========================================================================
# EXP-306 -- Gamma_306 (d=12: centroid-outward normals, kappa additive,
#            dual ghost S_A/S_C, recursive K-budget decay)
# ===========================================================================

SECTOR_C_KAPPA_DIM = 11  # kappa scalar, dims [8,9,10,11] = Sector C in EXP-306
K_MIN_PARTITION = 16     # atomic floor for recursive K-budget
LAMBDA_DECAY = 0.6931471805599453  # ln(2); halves K_budget per depth


def _centroid_outward_normal(centroid_child, centroid_parent):
    """
    n = normalize(centroid_child - centroid_parent).
    Degenerate (same centroid): return [0,0,1].
    """
    d = centroid_child - centroid_parent
    norm = float(np.linalg.norm(d))
    if norm < 1e-12:
        return np.array([0.0, 0.0, 1.0])
    return d / norm


def apply_gamma_306(
    mu,
    claim_id,
    partition_key,
    payloads,
    beta,
    budget,
    spent,
    weights=None,
):
    """
    Gamma_306 -- d=12 spatial partition with centroid-outward normals,
    kappa additive split, and dual ghost (S_A, S_C).

    Sector C (dims 8-11):
      [8:11] normal: n_child = normalize(centroid_child - centroid_parent)
      [11]   kappa:  kappa_child_i = kappa_parent * omega_i

    Restriction map (12x12 block-diagonal):
      F[0:4,   0:4 ] = F_A (outer product, Sector A)
      F[4:8,   4:8 ] = F_B (outer product, Sector B)
      F[8:11,  8:11] = F_C (outer product, centroid-outward n_child)
      F[11,    11  ] = omega_i (kappa scalar block)
      All off-diagonal sector cross blocks = 0.

    Dual ghost update:
      S_A_{t+1} = alpha * S_A_t + (1-alpha) * G_A_t  (dims 0-7)
      S_C_{t+1} = alpha * S_C_t + (1-alpha) * G_C_t  (dims 8-11)

    Returns: (new_mu, cost)
    """
    from engine.validity import (
        is_valid, is_valid_b, is_spatially_valid,
        is_unit_norm, is_valid_block_diagonal_306,
    )
    import math

    if claim_id not in mu.active:
        raise PartitionError(f"GAMMA306_ERROR: claim {claim_id} not in active set.")
    parent = mu.claims[claim_id]
    if parent.bbox is None:
        raise PartitionError(f"GAMMA306_ERROR: claim {claim_id} has no bbox.")

    d = parent.stalk.shape[0]
    if d != 12:
        raise PartitionError(f"GAMMA306_ERROR: EXP-306 requires d=12, got d={d}.")
    if partition_key not in SPATIAL_KEYS:
        raise PartitionError(
            f"GAMMA306_UNKNOWN_KEY: '{partition_key}' not in {list(SPATIAL_KEYS.keys())}."
        )
    N = SPATIAL_KEYS[partition_key]
    if len(payloads) != N:
        raise PartitionError(f"GAMMA306_ERROR: expected {N} payloads, got {len(payloads)}.")

    k_children = sum(len(zlib.compress(p.encode("utf-8"), level=9)) for p in payloads)
    k_limit = parent.K_bound + C_KBOUND * math.log(N)
    if k_children > k_limit:
        raise PartitionError(
            f"GAMMA306_INFORMATION_OVERFLOW: sum K={k_children:.1f} > limit={k_limit:.2f}"
        )

    cost = _cost(C0=1.0, beta=beta, S=mu.S)
    if spent + cost > budget:
        raise PartitionError(
            f"GAMMA306_BUDGET: spent={spent:.4f} + cost={cost:.4f} > B0={budget}"
        )

    child_bboxes = _compute_child_bboxes(parent.bbox, partition_key)

    p_lo, p_hi = parent.bbox
    parent_vol = float(np.prod(p_hi - p_lo))
    if parent_vol < 1e-30:
        omegas = [1.0 / N] * N
    else:
        vols = [float(np.prod(cb[1] - cb[0])) for cb in child_bboxes]
        total_vol = sum(vols)
        omegas = [v / total_vol for v in vols]
    if weights is not None:
        total = sum(weights)
        omegas = [w / total for w in weights]

    b0A, b1A = SECTOR_A_DIMS[0], SECTOR_A_DIMS[-1] + 1   # [0:4]
    b0B, b1B = SECTOR_B_DIMS[0], SECTOR_B_DIMS[-1] + 1   # [4:8]
    b0N = SECTOR_C_DIMS[0]                                 # 8 (normal start)
    b1N = SECTOR_C_DIMS[-1] + 1                            # 11 (normal end)
    b_k = SECTOR_C_KAPPA_DIM                               # 11 (kappa scalar)

    stalk_A = parent.stalk[b0A:b1A]
    d_A = len(SECTOR_A_DIMS)
    full_children_cache = None

    if N <= d_A:
        stalk_A_children = _orthogonal_decompose(stalk_A, N)
    else:
        full_children_cache = _orthogonal_decompose(parent.stalk, N)
        stalk_A_children = [c[b0A:b1A] for c in full_children_cache]

    # Sector C normals: centroid-outward convention
    p_centroid = (p_lo + p_hi) / 2.0  # parent centroid
    n_children = [
        _centroid_outward_normal((cb[0] + cb[1]) / 2.0, p_centroid)
        for cb in child_bboxes
    ]

    kappa_parent = float(parent.stalk[b_k])

    t_new = mu.t + 1
    new_claims = dict(mu.claims)
    new_entailments = dict(mu.entailments)
    child_ids = []

    stalk_A_parent = parent.stalk[b0A:b1A]
    stalk_B_parent = parent.stalk[b0B:b1B]
    stalk_N_parent = parent.stalk[b0N:b1N]

    stalk_A_nsq = float(np.dot(stalk_A_parent, stalk_A_parent))
    stalk_B_nsq = float(np.dot(stalk_B_parent, stalk_B_parent))
    stalk_N_nsq = float(np.dot(stalk_N_parent, stalk_N_parent))

    for i, (payload, omega, stalk_A_i, (c_lo, c_hi), n_child) in enumerate(
            zip(payloads, omegas, stalk_A_children, child_bboxes, n_children)):

        centroid_B = (c_lo + c_hi) / 2.0  # R^3 centroid for Sector B

        child_stalk = np.empty(d)
        child_stalk[b0A:b1A] = stalk_A_i          # Sector A
        child_stalk[b0B:b0B+3] = centroid_B        # Sector B xyz
        child_stalk[SECTOR_B_DIMS[-1]] = 1.0       # Sector B w = 1
        child_stalk[b0N:b1N] = n_child             # Sector C normal (centroid-outward)
        child_stalk[b_k] = kappa_parent * omega     # kappa additive split

        prov = Provenance(
            parent_ids=(claim_id,),
            operator_id=f"Gamma306:{partition_key}:{i}",
            timestamp=now_iso(),
        )
        child = Claim(provenance=prov, payload=payload, stalk=child_stalk,
                      t=t_new, bbox=(c_lo, c_hi))
        child_ids.append(child.id)
        new_claims[child.id] = child

        # Block-diagonal restriction map (12x12)
        F = np.zeros((d, d))

        if stalk_A_nsq > 1e-30:
            F[b0A:b1A, b0A:b1A] = np.outer(stalk_A_i, stalk_A_parent) / stalk_A_nsq
        if stalk_B_nsq > 1e-30:
            F[b0B:b1B, b0B:b1B] = (
                np.outer(child_stalk[b0B:b1B], stalk_B_parent) / stalk_B_nsq
            )
        if stalk_N_nsq > 1e-30:
            F[b0N:b1N, b0N:b1N] = np.outer(n_child, stalk_N_parent) / stalk_N_nsq
        # kappa scalar block
        F[b_k, b_k] = omega

        det_B = float(np.linalg.det(F[b0B:b1B, b0B:b1B]))
        det_sign = int(np.sign(det_B)) if abs(det_B) > 1e-30 else 1

        ent_spatial = Entailment(
            source_id=claim_id,
            target_id=child.id,
            etype=EntailmentType.SPATIAL,
            restriction=F,
            predicate_hash=hashlib.sha256(F.tobytes()).hexdigest()[:16],
            omega=omega,
            det_sign=det_sign,
        )
        new_entailments[(claim_id, child.id)] = ent_spatial

    new_active = (mu.active - {claim_id}) | frozenset(child_ids)

    # Dual ghost update
    new_S_A = mu.next_S_A()
    new_S_C = mu.next_S_C()
    new_S   = np.concatenate([new_S_A, new_S_C])  # for backward-compat S field

    new_state = MuState(
        t=t_new,
        claims=new_claims,
        entailments=new_entailments,
        active=new_active,
        S=new_S,
        alpha=mu.alpha,
        S_A=new_S_A,
        S_C=new_S_C,
    )
    new_state.seal()

    if not is_valid(new_state):
        raise PartitionError("GAMMA306_CONSISTENCY_ERROR: is_valid failed.")
    if not is_valid_b(new_state):
        raise PartitionError("GAMMA306_CONSISTENCY_ERROR: is_valid_b failed.")
    if not is_unit_norm(new_state):
        raise PartitionError("GAMMA306_UNIT_NORM_ERROR: is_unit_norm failed.")
    if not is_spatially_valid(new_state):
        raise PartitionError("GAMMA306_SPATIAL_ERROR: bbox containment violated.")
    if not is_valid_block_diagonal_306(new_state):
        raise PartitionError("GAMMA306_BLOCK_DIAGONAL_ERROR: off-diagonal coupling.")

    return new_state, cost


def apply_gamma_306_recursive(
    mu,
    claim_id,
    partition_key,
    payload_fn,
    beta,
    budget,
    spent,
    K_budget,
    depth=0,
):
    """
    Recursive Gamma_306 with soft-decay K-budget.

    Applies apply_gamma_306 to claim_id, then recursively to all
    resulting active leaves, decaying K_budget each level:
      K_budget_child = K_budget * exp(-LAMBDA_DECAY * 1) = K_budget / 2

    Termination: K_budget < K_MIN_PARTITION -> return mu unchanged.

    payload_fn: callable(depth, index) -> payload string for child i at depth d.
      Example: lambda d, i: f"node_d{d}_i{i}"

    Returns: (final_mu, total_cost)
    """
    import math
    if K_budget < K_MIN_PARTITION:
        return mu, 0.0

    N = SPATIAL_KEYS[partition_key]
    payloads = [payload_fn(depth, i) for i in range(N)]

    try:
        mu_next, cost = apply_gamma_306(
            mu=mu, claim_id=claim_id, partition_key=partition_key,
            payloads=payloads, beta=beta, budget=budget, spent=spent,
        )
    except PartitionError:
        return mu, 0.0

    total_cost = cost
    spent_now = spent + cost

    K_child = K_budget * math.exp(-LAMBDA_DECAY)  # halved

    # Identify new leaf children (active nodes that came from claim_id)
    new_child_ids = [
        cid for cid in mu_next.active
        if cid not in mu.active
    ]

    for cid in new_child_ids:
        mu_next, rc = apply_gamma_306_recursive(
            mu=mu_next,
            claim_id=cid,
            partition_key=partition_key,
            payload_fn=payload_fn,
            beta=beta,
            budget=budget,
            spent=spent_now,
            K_budget=K_child,
            depth=depth + 1,
        )
        total_cost += rc
        spent_now += rc

    return mu_next, total_cost


# ===========================================================================
# EXP-307 -- Gamma_307 (d=12: kappa = tr(H_bbox), auto-payload)
# ===========================================================================

def _kappa_from_bbox(bbox, kappa_max=1e9):
    """kappa = tr(H_bbox) = sum_i (2 / extent_i).  Mirrors validity.kappa_from_bbox."""
    lo, hi = bbox
    total = 0.0
    for i in range(len(lo)):
        e = float(hi[i] - lo[i])
        total += (kappa_max if e < 1e-12 else 2.0 / e)
    return total


def _auto_payload(parent_id: str, partition_key: str, depth: int, index: int) -> str:
    """
    Deterministic payload for recursive Gamma_307.
    payload = SHA256(parent_id:partition_key:depth:index)[:16]
    """
    raw = f"{parent_id}:{partition_key}:{depth}:{index}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def apply_gamma_307(
    mu,
    claim_id,
    partition_key,
    payloads,
    beta,
    budget,
    spent,
    weights=None,
):
    """
    Gamma_307 -- d=12 spatial partition with kappa = tr(H_bbox).

    Identical to apply_gamma_306 except:
      kappa_child_i = kappa_from_bbox(child_bbox_i)   [geometric, not additive]
      F[11,11] = kappa_child_i / kappa_parent          [ratio, not omega]

    Post-validates: is_valid, is_valid_b, is_unit_norm, is_spatially_valid,
                    is_valid_block_diagonal_306, is_valid_kappa  (6 predicates)
    """
    from engine.validity import (
        is_valid, is_valid_b, is_spatially_valid,
        is_unit_norm, is_valid_block_diagonal_306, is_valid_kappa,
    )

    if claim_id not in mu.active:
        raise PartitionError(f"GAMMA307_ERROR: claim {claim_id} not in active set.")
    parent = mu.claims[claim_id]
    if parent.bbox is None:
        raise PartitionError(f"GAMMA307_ERROR: claim {claim_id} has no bbox.")

    d = parent.stalk.shape[0]
    if d != 12:
        raise PartitionError(f"GAMMA307_ERROR: EXP-307 requires d=12, got d={d}.")
    if partition_key not in SPATIAL_KEYS:
        raise PartitionError(
            f"GAMMA307_UNKNOWN_KEY: '{partition_key}' not in {list(SPATIAL_KEYS.keys())}."
        )
    N = SPATIAL_KEYS[partition_key]
    if len(payloads) != N:
        raise PartitionError(f"GAMMA307_ERROR: expected {N} payloads, got {len(payloads)}.")

    k_children = sum(len(zlib.compress(p.encode("utf-8"), level=9)) for p in payloads)
    k_limit = parent.K_bound + C_KBOUND * math.log(N)
    if k_children > k_limit:
        raise PartitionError(
            f"GAMMA307_INFORMATION_OVERFLOW: sum K={k_children:.1f} > limit={k_limit:.2f}"
        )

    cost = _cost(C0=1.0, beta=beta, S=mu.S)
    if spent + cost > budget:
        raise PartitionError(
            f"GAMMA307_BUDGET: spent={spent:.4f} + cost={cost:.4f} > B0={budget}"
        )

    child_bboxes = _compute_child_bboxes(parent.bbox, partition_key)

    p_lo, p_hi = parent.bbox
    parent_vol = float(np.prod(p_hi - p_lo))
    if parent_vol < 1e-30:
        omegas = [1.0 / N] * N
    else:
        vols = [float(np.prod(cb[1] - cb[0])) for cb in child_bboxes]
        total_vol = sum(vols)
        omegas = [v / total_vol for v in vols]
    if weights is not None:
        total = sum(weights)
        omegas = [w / total for w in weights]

    b0A, b1A = SECTOR_A_DIMS[0], SECTOR_A_DIMS[-1] + 1
    b0B, b1B = SECTOR_B_DIMS[0], SECTOR_B_DIMS[-1] + 1
    b0N = SECTOR_C_DIMS[0]; b1N = SECTOR_C_DIMS[-1] + 1
    b_k = SECTOR_C_KAPPA_DIM  # 11

    stalk_A = parent.stalk[b0A:b1A]
    d_A = len(SECTOR_A_DIMS)

    d_A = len(SECTOR_A_DIMS)
    if N <= d_A:
        stalk_A_children = _orthogonal_decompose(stalk_A, N)
    else:
        full_children = _orthogonal_decompose(parent.stalk, N)
        stalk_A_children = [c[b0A:b1A] for c in full_children]

    p_centroid = (p_lo + p_hi) / 2.0
    n_children = [
        _centroid_outward_normal((cb[0] + cb[1]) / 2.0, p_centroid)
        for cb in child_bboxes
    ]

    kappa_parent = float(parent.stalk[b_k])

    t_new = mu.t + 1
    new_claims = dict(mu.claims)
    new_entailments = dict(mu.entailments)
    child_ids = []

    stalk_A_parent = parent.stalk[b0A:b1A]
    stalk_B_parent = parent.stalk[b0B:b1B]
    stalk_N_parent = parent.stalk[b0N:b1N]

    stalk_A_nsq = float(np.dot(stalk_A_parent, stalk_A_parent))
    stalk_B_nsq = float(np.dot(stalk_B_parent, stalk_B_parent))
    stalk_N_nsq = float(np.dot(stalk_N_parent, stalk_N_parent))

    for i, (payload, omega, stalk_A_i, (c_lo, c_hi), n_child) in enumerate(
            zip(payloads, omegas, stalk_A_children, child_bboxes, n_children)):

        centroid_B = (c_lo + c_hi) / 2.0
        kappa_child = _kappa_from_bbox((c_lo, c_hi))  # geometric

        child_stalk = np.empty(d)
        child_stalk[b0A:b1A] = stalk_A_i
        child_stalk[b0B:b0B+3] = centroid_B
        child_stalk[SECTOR_B_DIMS[-1]] = 1.0
        child_stalk[b0N:b1N] = n_child
        child_stalk[b_k] = kappa_child

        prov = Provenance(
            parent_ids=(claim_id,),
            operator_id=f"Gamma307:{partition_key}:{i}",
            timestamp=now_iso(),
        )
        child = Claim(provenance=prov, payload=payload, stalk=child_stalk,
                      t=t_new, bbox=(c_lo, c_hi))
        child_ids.append(child.id)
        new_claims[child.id] = child

        F = np.zeros((d, d))
        if stalk_A_nsq > 1e-30:
            F[b0A:b1A, b0A:b1A] = np.outer(stalk_A_i, stalk_A_parent) / stalk_A_nsq
        if stalk_B_nsq > 1e-30:
            F[b0B:b1B, b0B:b1B] = (
                np.outer(child_stalk[b0B:b1B], stalk_B_parent) / stalk_B_nsq
            )
        if stalk_N_nsq > 1e-30:
            F[b0N:b1N, b0N:b1N] = np.outer(n_child, stalk_N_parent) / stalk_N_nsq
        # kappa geometric ratio (not omega)
        if abs(kappa_parent) > 1e-30:
            F[b_k, b_k] = kappa_child / kappa_parent
        else:
            F[b_k, b_k] = 0.0

        det_B = float(np.linalg.det(F[b0B:b1B, b0B:b1B]))
        det_sign = int(np.sign(det_B)) if abs(det_B) > 1e-30 else 1

        ent_spatial = Entailment(
            source_id=claim_id,
            target_id=child.id,
            etype=EntailmentType.SPATIAL,
            restriction=F,
            predicate_hash=hashlib.sha256(F.tobytes()).hexdigest()[:16],
            omega=omega,
            det_sign=det_sign,
        )
        new_entailments[(claim_id, child.id)] = ent_spatial

    new_active = (mu.active - {claim_id}) | frozenset(child_ids)

    new_S_A = mu.next_S_A()
    new_S_C = mu.next_S_C()
    new_S   = np.concatenate([new_S_A, new_S_C])

    new_state = MuState(
        t=t_new,
        claims=new_claims,
        entailments=new_entailments,
        active=new_active,
        S=new_S,
        alpha=mu.alpha,
        S_A=new_S_A,
        S_C=new_S_C,
    )
    new_state.seal()

    if not is_valid(new_state):
        raise PartitionError("GAMMA307_CONSISTENCY_ERROR: is_valid failed.")
    if not is_valid_b(new_state):
        raise PartitionError("GAMMA307_CONSISTENCY_ERROR: is_valid_b failed.")
    if not is_unit_norm(new_state):
        raise PartitionError("GAMMA307_UNIT_NORM_ERROR: is_unit_norm failed.")
    if not is_spatially_valid(new_state):
        raise PartitionError("GAMMA307_SPATIAL_ERROR: bbox containment violated.")
    if not is_valid_block_diagonal_306(new_state):
        raise PartitionError("GAMMA307_BLOCK_DIAGONAL_ERROR: off-diagonal coupling.")
    if not is_valid_kappa(new_state):
        raise PartitionError("GAMMA307_KAPPA_ERROR: kappa != tr(H_bbox).")

    return new_state, cost


def apply_gamma_307_recursive(
    mu,
    claim_id,
    partition_key,
    beta,
    budget,
    spent,
    K_budget,
    depth=0,
):
    """
    Recursive Gamma_307 with auto-generated payloads.

    payload_i = SHA256(parent_id:partition_key:depth:i)[:16]  (deterministic)
    K_budget decays by exp(-LAMBDA_DECAY) per level (halved).
    Terminates when K_budget < K_MIN_PARTITION.

    Returns: (final_mu, total_cost)
    """
    if K_budget < K_MIN_PARTITION:
        return mu, 0.0

    N = SPATIAL_KEYS[partition_key]
    payloads = [_auto_payload(claim_id, partition_key, depth, i) for i in range(N)]

    try:
        mu_next, cost = apply_gamma_307(
            mu=mu, claim_id=claim_id, partition_key=partition_key,
            payloads=payloads, beta=beta, budget=budget, spent=spent,
        )
    except PartitionError:
        return mu, 0.0

    total_cost = cost
    spent_now = spent + cost
    K_child = K_budget * math.exp(-LAMBDA_DECAY)

    new_child_ids = [cid for cid in mu_next.active if cid not in mu.active]

    for cid in new_child_ids:
        mu_next, rc = apply_gamma_307_recursive(
            mu=mu_next,
            claim_id=cid,
            partition_key=partition_key,
            beta=beta,
            budget=budget,
            spent=spent_now,
            K_budget=K_child,
            depth=depth + 1,
        )
        total_cost += rc
        spent_now += rc

    return mu_next, total_cost


# ===========================================================================
# EXP-308 -- Gamma_308 (d=12: kappa=kappa_integral, bbox-hash payload)
# ===========================================================================

def _kappa_integral(bbox, eps_rel=1e-9):
    """
    kappa = 2*(ly*lz/lx + lx*lz/ly + lx*ly/lz) / (lx*ly + ly*lz + lx*lz)
    Regularized: eps = max(lx,ly,lz) * eps_rel; li = max(li, eps).
    Mirrors validity.kappa_integral (relative floor, EXP-308 rev).
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


def _bbox_hash_payload(bbox, depth: int, index: int) -> str:
    """
    payload = SHA256(bbox_lo_bytes + bbox_hi_bytes + depth_bytes + index_bytes)[:16]
    bbox bytes: IEEE 754 big-endian doubles (struct '>ddd').
    Deterministic function of geometry + recursion position.
    """
    import struct
    lo, hi = bbox
    raw = (struct.pack('>ddd', float(lo[0]), float(lo[1]), float(lo[2])) +
           struct.pack('>ddd', float(hi[0]), float(hi[1]), float(hi[2])) +
           struct.pack('>I', depth) +
           struct.pack('>I', index))
    return hashlib.sha256(raw).hexdigest()[:16]


def apply_gamma_308(
    mu,
    claim_id,
    partition_key,
    payloads,
    beta,
    budget,
    spent,
    weights=None,
):
    """
    Gamma_308 -- d=12 with kappa = kappa_integral(bbox).

    Identical to apply_gamma_307 except:
      kappa_child_i = _kappa_integral(child_bbox_i)
      F[11,11] = kappa_child_i / kappa_parent
      Post-validates with is_valid_kappa_308 (not is_valid_kappa).
    """
    from engine.validity import (
        is_valid, is_valid_b, is_spatially_valid,
        is_unit_norm, is_valid_block_diagonal_306, is_valid_kappa_308,
    )

    if claim_id not in mu.active:
        raise PartitionError(f"GAMMA308_ERROR: claim {claim_id} not in active set.")
    parent = mu.claims[claim_id]
    if parent.bbox is None:
        raise PartitionError(f"GAMMA308_ERROR: claim {claim_id} has no bbox.")

    d = parent.stalk.shape[0]
    if d != 12:
        raise PartitionError(f"GAMMA308_ERROR: EXP-308 requires d=12, got d={d}.")
    if partition_key not in SPATIAL_KEYS:
        raise PartitionError(
            f"GAMMA308_UNKNOWN_KEY: '{partition_key}' not in {list(SPATIAL_KEYS.keys())}."
        )
    N = SPATIAL_KEYS[partition_key]
    if len(payloads) != N:
        raise PartitionError(f"GAMMA308_ERROR: expected {N} payloads, got {len(payloads)}.")

    k_children = sum(len(zlib.compress(p.encode("utf-8"), level=9)) for p in payloads)
    k_limit = parent.K_bound + C_KBOUND * math.log(N)
    if k_children > k_limit:
        raise PartitionError(
            f"GAMMA308_INFORMATION_OVERFLOW: sum K={k_children:.1f} > limit={k_limit:.2f}"
        )

    cost = _cost(C0=1.0, beta=beta, S=mu.S)
    if spent + cost > budget:
        raise PartitionError(
            f"GAMMA308_BUDGET: spent={spent:.4f} + cost={cost:.4f} > B0={budget}"
        )

    child_bboxes = _compute_child_bboxes(parent.bbox, partition_key)

    p_lo, p_hi = parent.bbox
    parent_vol = float(np.prod(p_hi - p_lo))
    if parent_vol < 1e-30:
        omegas = [1.0 / N] * N
    else:
        vols = [float(np.prod(cb[1] - cb[0])) for cb in child_bboxes]
        total_vol = sum(vols)
        omegas = [v / total_vol for v in vols]
    if weights is not None:
        total_w = sum(weights)
        omegas = [w / total_w for w in weights]

    b0A, b1A = SECTOR_A_DIMS[0], SECTOR_A_DIMS[-1] + 1
    b0B, b1B = SECTOR_B_DIMS[0], SECTOR_B_DIMS[-1] + 1
    b0N = SECTOR_C_DIMS[0]; b1N = SECTOR_C_DIMS[-1] + 1
    b_k = SECTOR_C_KAPPA_DIM

    stalk_A = parent.stalk[b0A:b1A]
    d_A = len(SECTOR_A_DIMS)
    if N <= d_A:
        stalk_A_children = _orthogonal_decompose(stalk_A, N)
    else:
        full_children = _orthogonal_decompose(parent.stalk, N)
        stalk_A_children = [c[b0A:b1A] for c in full_children]

    p_centroid = (p_lo + p_hi) / 2.0
    n_children = [
        _centroid_outward_normal((cb[0] + cb[1]) / 2.0, p_centroid)
        for cb in child_bboxes
    ]

    kappa_parent = float(parent.stalk[b_k])

    t_new = mu.t + 1
    new_claims = dict(mu.claims)
    new_entailments = dict(mu.entailments)
    child_ids = []

    stalk_A_parent = parent.stalk[b0A:b1A]
    stalk_B_parent = parent.stalk[b0B:b1B]
    stalk_N_parent = parent.stalk[b0N:b1N]
    stalk_A_nsq = float(np.dot(stalk_A_parent, stalk_A_parent))
    stalk_B_nsq = float(np.dot(stalk_B_parent, stalk_B_parent))
    stalk_N_nsq = float(np.dot(stalk_N_parent, stalk_N_parent))

    for i, (payload, omega, stalk_A_i, (c_lo, c_hi), n_child) in enumerate(
            zip(payloads, omegas, stalk_A_children, child_bboxes, n_children)):

        centroid_B = (c_lo + c_hi) / 2.0
        kappa_child = _kappa_integral((c_lo, c_hi))

        child_stalk = np.empty(d)
        child_stalk[b0A:b1A] = stalk_A_i
        child_stalk[b0B:b0B+3] = centroid_B
        child_stalk[SECTOR_B_DIMS[-1]] = 1.0
        child_stalk[b0N:b1N] = n_child
        child_stalk[b_k] = kappa_child

        prov = Provenance(
            parent_ids=(claim_id,),
            operator_id=f"Gamma308:{partition_key}:{i}",
            timestamp=now_iso(),
        )
        child = Claim(provenance=prov, payload=payload, stalk=child_stalk,
                      t=t_new, bbox=(c_lo, c_hi))
        child_ids.append(child.id)
        new_claims[child.id] = child

        F = np.zeros((d, d))
        if stalk_A_nsq > 1e-30:
            F[b0A:b1A, b0A:b1A] = np.outer(stalk_A_i, stalk_A_parent) / stalk_A_nsq
        if stalk_B_nsq > 1e-30:
            F[b0B:b1B, b0B:b1B] = (
                np.outer(child_stalk[b0B:b1B], stalk_B_parent) / stalk_B_nsq
            )
        if stalk_N_nsq > 1e-30:
            F[b0N:b1N, b0N:b1N] = np.outer(n_child, stalk_N_parent) / stalk_N_nsq
        if abs(kappa_parent) > 1e-30:
            F[b_k, b_k] = kappa_child / kappa_parent
        else:
            F[b_k, b_k] = 0.0

        det_B = float(np.linalg.det(F[b0B:b1B, b0B:b1B]))
        det_sign = int(np.sign(det_B)) if abs(det_B) > 1e-30 else 1

        ent = Entailment(
            source_id=claim_id,
            target_id=child.id,
            etype=EntailmentType.SPATIAL,
            restriction=F,
            predicate_hash=hashlib.sha256(F.tobytes()).hexdigest()[:16],
            omega=omega,
            det_sign=det_sign,
        )
        new_entailments[(claim_id, child.id)] = ent

    new_active = (mu.active - {claim_id}) | frozenset(child_ids)
    new_S_A = mu.next_S_A()
    new_S_C = mu.next_S_C()
    new_S   = np.concatenate([new_S_A, new_S_C])

    new_state = MuState(
        t=t_new, claims=new_claims, entailments=new_entailments,
        active=new_active, S=new_S, alpha=mu.alpha, S_A=new_S_A, S_C=new_S_C,
    )
    new_state.seal()

    if not is_valid(new_state):
        raise PartitionError("GAMMA308_CONSISTENCY_ERROR: is_valid failed.")
    if not is_valid_b(new_state):
        raise PartitionError("GAMMA308_CONSISTENCY_ERROR: is_valid_b failed.")
    if not is_unit_norm(new_state):
        raise PartitionError("GAMMA308_UNIT_NORM_ERROR: is_unit_norm failed.")
    if not is_spatially_valid(new_state):
        raise PartitionError("GAMMA308_SPATIAL_ERROR: bbox containment violated.")
    if not is_valid_block_diagonal_306(new_state):
        raise PartitionError("GAMMA308_BLOCK_DIAGONAL_ERROR: off-diagonal coupling.")
    if not is_valid_kappa_308(new_state):
        raise PartitionError("GAMMA308_KAPPA_ERROR: kappa != kappa_integral(bbox).")

    return new_state, cost


def apply_gamma_308_recursive(
    mu,
    claim_id,
    partition_key,
    beta,
    budget,
    spent,
    K_budget,
    depth=0,
):
    """
    Recursive Gamma_308 with bbox-hash payloads.

    payload_i = SHA256(bbox_lo_bytes + bbox_hi_bytes + depth_bytes + index_bytes)[:16]
    (deterministic function of child bbox geometry + recursion position)

    K_budget decays by exp(-LAMBDA_DECAY) per level. Terminates when K_budget < K_MIN_PARTITION.
    """
    if K_budget < K_MIN_PARTITION:
        return mu, 0.0

    N = SPATIAL_KEYS[partition_key]
    # Payloads derived from CHILD bboxes (computed before partition for determinism)
    child_bboxes_preview = _compute_child_bboxes(mu.claims[claim_id].bbox, partition_key)
    payloads = [
        _bbox_hash_payload(child_bboxes_preview[i], depth, i)
        for i in range(N)
    ]

    try:
        mu_next, cost = apply_gamma_308(
            mu=mu, claim_id=claim_id, partition_key=partition_key,
            payloads=payloads, beta=beta, budget=budget, spent=spent,
        )
    except PartitionError:
        return mu, 0.0

    total_cost = cost
    spent_now = spent + cost
    K_child = K_budget * math.exp(-LAMBDA_DECAY)
    new_child_ids = [cid for cid in mu_next.active if cid not in mu.active]

    for cid in new_child_ids:
        mu_next, rc = apply_gamma_308_recursive(
            mu=mu_next, claim_id=cid, partition_key=partition_key,
            beta=beta, budget=budget, spent=spent_now,
            K_budget=K_child, depth=depth + 1,
        )
        total_cost += rc
        spent_now += rc

    return mu_next, total_cost


# ===========================================================================
# EXP-309 -- Gamma_309 (SPRT LOD observer, focal point, ghost quarantine)
# ===========================================================================

from engine.validity import (
    lod_value as _lod_value,
    lod_bypass_set as _lod_bypass_set,
    is_lod_valid_309 as _is_lod_valid_309,
    bypass_registry_309 as _bypass_registry_309,
    LOD_THRESHOLDS_309 as _LOD_THRESHOLDS_309,
    NON_BYPASSABLE_309 as _NON_BYPASSABLE_309,
)


def apply_gamma_309(
    mu,
    claim_id,
    partition_key,
    payloads,
    beta,
    budget,
    spent,
    focal_point=None,
    thresholds=None,
):
    """
    Gamma_309: SPRT LOD-gated single-step partition.

    Operator pipeline: mu -> Ltau -> Btau -> Rtau -> Z -> S -> W -> OBS
    Validity class (SPRT):
      FULL_VALID  : all 6 predicates pass, no bypasses active.
      LOD_RELAXED : non-bypassed predicates pass; >=1 bypassable predicate bypassed.
      INVALID     : any NON_BYPASSABLE predicate fails -> PartitionError.

    LOD_RELAXED claims: not revert targets, not partition sources.
    Ghost quarantine applied via mu.next_S_C_309(bypass_registry).
    focal_point defaults to mu.focal_point_value() (mass-weighted centroid).
    """
    if thresholds is None:
        thresholds = _LOD_THRESHOLDS_309
    if focal_point is None:
        focal_point = mu.focal_point_value()

    # Step 1: run the base 308 partition
    mu_next, cost = apply_gamma_308(
        mu=mu, claim_id=claim_id, partition_key=partition_key,
        payloads=payloads, beta=beta, budget=budget, spent=spent,
    )

    # Step 2: LOD validity check
    valid, validity_class = _is_lod_valid_309(mu_next, focal_point, thresholds)
    if not valid:
        raise PartitionError(
            f'apply_gamma_309: INVALID after partition. '
            f'claim_id={claim_id}, partition_key={partition_key}'
        )

    # Step 3: ghost quarantine for LOD_RELAXED
    bypass_reg = _bypass_registry_309(mu_next, focal_point, thresholds)
    if validity_class == 'LOD_RELAXED':
        s_c_new = mu_next.next_S_C_309(bypass_reg)
        mu_next = mu_next._replace_S_C(s_c_new)

    # Step 4: update focal point
    fp_new = mu_next.next_focal_point()
    mu_next = mu_next._replace_focal_point(fp_new)

    # Step 5: tag validity class
    mu_next = mu_next._replace_validity_class(validity_class)

    return mu_next, cost, validity_class


def apply_gamma_309_recursive(
    mu,
    claim_id,
    partition_key,
    beta,
    budget,
    spent,
    K_budget,
    depth=0,
    focal_point=None,
    thresholds=None,
):
    """
    Recursive Gamma_309 with SPRT LOD gating.

    LOD_RELAXED claims are NOT expanded (partition_source=False).
    FULL_VALID claims recurse normally with decaying K_budget.
    Ghost quarantine applied after each LOD_RELAXED step.
    Focal point updated after each step.

    Returns: (final_mu, total_cost)
    """
    if thresholds is None:
        thresholds = _LOD_THRESHOLDS_309
    if focal_point is None:
        focal_point = mu.focal_point_value()

    if K_budget < K_MIN_PARTITION:
        return mu, 0.0

    # LOD_RELAXED guard: do not expand a state produced by a LOD_RELAXED partition.
    # validity_class is set on MuState by _replace_validity_class, not on Claim.
    if getattr(mu, 'validity_class', 'FULL_VALID') == 'LOD_RELAXED':
        return mu, 0.0

    N = SPATIAL_KEYS[partition_key]
    child_bboxes_preview = _compute_child_bboxes(mu.claims[claim_id].bbox, partition_key)
    payloads = [
        _bbox_hash_payload(child_bboxes_preview[i], depth, i)
        for i in range(N)
    ]

    try:
        mu_next, cost, validity_class = apply_gamma_309(
            mu=mu, claim_id=claim_id, partition_key=partition_key,
            payloads=payloads, beta=beta, budget=budget, spent=spent,
            focal_point=focal_point, thresholds=thresholds,
        )
    except PartitionError:
        return mu, 0.0

    total_cost = cost
    spent_now = spent + cost
    K_child = K_budget * math.exp(-LAMBDA_DECAY)
    fp_next = mu_next.focal_point_value()

    # Only recurse into FULL_VALID children
    if validity_class == 'FULL_VALID':
        new_child_ids = [cid for cid in mu_next.active if cid not in mu.active]
        for cid in new_child_ids:
            mu_next, rc = apply_gamma_309_recursive(
                mu=mu_next, claim_id=cid, partition_key=partition_key,
                beta=beta, budget=budget, spent=spent_now,
                K_budget=K_child, depth=depth + 1,
                focal_point=fp_next, thresholds=thresholds,
            )
            total_cost += rc
            spent_now += rc

    return mu_next, total_cost


# ============================================================
# EXP-311: The Asymmetric Injection
# G_inject auxiliary residual; A->C directed ghost activation
# Declaration hash: 10659ed4d37c027aed4144fd847c3e35986e49e45be596c9cc77b6806d040f35
# ============================================================

_ALPHA_EMA_311 = 0.85
_ALPHA_LEAK_311 = 0.1
_BETA_CA_311 = 0.3
_MASS_REF_311 = 2.0     # ||[1,1,1,1]||; unit seed Sector A norm
_KAPPA_REF_311 = 2.0    # kappa_integral([0,1]^3); unit cube kappa


def apply_gamma_311(
    mu,
    claim_id,
    partition_key,
    payloads,
    beta,
    budget,
    spent,
    focal_point=None,
    thresholds=None,
    alpha_leak=_ALPHA_LEAK_311,
    beta_CA=_BETA_CA_311,
    mass_ref=_MASS_REF_311,
    kappa_ref=_KAPPA_REF_311,
):
    """
    EXP-311 non-lossless Gamma operator.

    Wraps apply_gamma_309 with G_inject auxiliary residual injection:
      G_inject_C[3] = alpha_leak * (||Z_before[0:4]|| / mass_ref)   [A->C]
      G_inject_A[7] = alpha_leak * beta_CA * (Z_before[11] / kappa_ref)  [C->A, weaker]

    S_C and S_A updated via EMA from G_inject after apply_gamma_309 returns.
    G_t = Z_t - Pi_W(Z_t) = 0 identity unchanged (structural result).
    G_inject is orthogonal auxiliary channel; NOT G_t.

    G_inject values appended to mu_next.G_inject_log (non-hashed trace field).

    Returns: (mu_next, cost, validity_class)
    """
    # Step 1: record Z_before (stalk aggregate before expansion)
    Z_before = mu.Z()

    # Step 2: run apply_gamma_309
    mu_309, cost, validity_class = apply_gamma_309(
        mu=mu,
        claim_id=claim_id,
        partition_key=partition_key,
        payloads=payloads,
        beta=beta,
        budget=budget,
        spent=spent,
        focal_point=focal_point,
        thresholds=thresholds,
    )

    # Step 3: compute G_inject from Z_before (stateless: only declared inputs)
    import numpy as _np
    mass_norm = float(_np.linalg.norm(Z_before[0:4]))
    kappa_val = float(Z_before[11])

    G_inject_C = _np.zeros(4)
    G_inject_C[3] = alpha_leak * (mass_norm / (mass_ref + 1e-15))

    G_inject_A = _np.zeros(8)
    G_inject_A[7] = alpha_leak * beta_CA * (kappa_val / (kappa_ref + 1e-15))

    # Step 4: EMA update S_C
    s_c = mu_309.S_C if mu_309.S_C is not None else _np.zeros(4)
    s_c_new = _ALPHA_EMA_311 * s_c + (1.0 - _ALPHA_EMA_311) * G_inject_C
    mu_next = mu_309._replace_S_C(s_c_new)

    # Step 5: EMA update S_A
    s_a = mu_next.S_A if mu_next.S_A is not None else _np.zeros(8)
    s_a_new = _ALPHA_EMA_311 * s_a + (1.0 - _ALPHA_EMA_311) * G_inject_A
    mu_next = mu_next._replace_S_A(s_a_new)

    # Step 6: append G_inject trace (non-hashed)
    # Read from INPUT mu (not mu_next): apply_gamma_309 constructs fresh MuState
    # internally, dropping dynamic attributes. Propagate from the input state.
    log = getattr(mu, 'G_inject_log', None)
    if log is None:
        log = []
    log = log + [(float(G_inject_C[3]), float(G_inject_A[7]))]
    mu_next.G_inject_log = log

    # Step 7: update ghost history for TE
    # Same issue: read ghost_history from INPUT mu, copy, append current norms.
    import _collections_abc as _abc
    from collections import deque as _deque
    _hist_src = getattr(mu, 'ghost_history', None)
    if _hist_src is None:
        _hist = _deque(maxlen=32)
    else:
        _hist = _deque(_hist_src, maxlen=32)
    _hist.append((float(_np.linalg.norm(s_a_new)), float(_np.linalg.norm(s_c_new))))
    mu_next.ghost_history = _hist

    return mu_next, cost, validity_class


def apply_gamma_311_recursive(
    mu,
    claim_id,
    partition_key,
    beta,
    budget,
    spent,
    K_budget,
    depth=0,
    focal_point=None,
    thresholds=None,
    alpha_leak=_ALPHA_LEAK_311,
    beta_CA=_BETA_CA_311,
    mass_ref=_MASS_REF_311,
    kappa_ref=_KAPPA_REF_311,
):
    """
    Recursive Gamma_311 with SPRT LOD gating and G_inject ghost activation.

    Inherits LOD_RELAXED guard, focal point update, and ghost quarantine from
    apply_gamma_309. Adds G_inject EMA update at every partition step.

    Returns: (final_mu, total_cost)
    """
    if thresholds is None:
        thresholds = _LOD_THRESHOLDS_309
    if focal_point is None:
        focal_point = mu.focal_point_value()

    if K_budget < K_MIN_PARTITION:
        return mu, 0.0

    # LOD_RELAXED guard (MuState attribute, not Claim)
    if getattr(mu, 'validity_class', 'FULL_VALID') == 'LOD_RELAXED':
        return mu, 0.0

    N = SPATIAL_KEYS[partition_key]
    child_bboxes_preview = _compute_child_bboxes(mu.claims[claim_id].bbox, partition_key)
    payloads = [
        _bbox_hash_payload(child_bboxes_preview[i], depth, i)
        for i in range(N)
    ]

    try:
        mu_next, cost, validity_class = apply_gamma_311(
            mu=mu,
            claim_id=claim_id,
            partition_key=partition_key,
            payloads=payloads,
            beta=beta,
            budget=budget,
            spent=spent,
            focal_point=focal_point,
            thresholds=thresholds,
            alpha_leak=alpha_leak,
            beta_CA=beta_CA,
            mass_ref=mass_ref,
            kappa_ref=kappa_ref,
        )
    except PartitionError:
        return mu, 0.0

    total_cost = cost
    spent_now = spent + cost
    K_child = K_budget * math.exp(-LAMBDA_DECAY)
    fp_next = mu_next.focal_point_value()

    # Only recurse into FULL_VALID children
    if validity_class == 'FULL_VALID':
        new_child_ids = [cid for cid in mu_next.active if cid not in mu.active]
        for cid in new_child_ids:
            mu_next, rc = apply_gamma_311_recursive(
                mu=mu_next,
                claim_id=cid,
                partition_key=partition_key,
                beta=beta,
                budget=budget,
                spent=spent_now,
                K_budget=K_child,
                depth=depth + 1,
                focal_point=fp_next,
                thresholds=thresholds,
                alpha_leak=alpha_leak,
                beta_CA=beta_CA,
                mass_ref=mass_ref,
                kappa_ref=kappa_ref,
            )
            total_cost += rc
            spent_now += rc

    return mu_next, total_cost


# ===========================================================================
# EXP-312 -- The Symmetric Budget
# Two P_yz symmetry fixes:
#   Fix 1: _bbox_hash_payload_312 -- extents-based payload (coordinate-free)
#   Fix 2: _stalk_A_decompose_312 -- Sector A isolation for N > d_A
# Declaration hash: e6c4ee25d9f0dca47f2ee0704c007f5772c381a9242d5014c6b00970cdf0e112
# ===========================================================================

def _bbox_hash_payload_312(bbox, depth: int, index: int) -> str:
    """
    EXP-312 Fix 1: P_yz-invariant bbox payload.

    payload = SHA256(pack(>ddd, ex, ey, ez) + pack(>I, depth) + pack(>I, index))[:16]
    ex = abs(hi[0]-lo[0]),  ey = abs(hi[1]-lo[1]),  ez = abs(hi[2]-lo[2])

    Extents are unsigned differences -- invariant under any coordinate reflection.
    Replaces _bbox_hash_payload which used absolute lo,hi coords.
    """
    import struct
    lo, hi = bbox
    ex = abs(float(hi[0]) - float(lo[0]))
    ey = abs(float(hi[1]) - float(lo[1]))
    ez = abs(float(hi[2]) - float(lo[2]))
    raw = (struct.pack(">ddd", ex, ey, ez) +
           struct.pack(">I", depth) +
           struct.pack(">I", index))
    return hashlib.sha256(raw).hexdigest()[:16]


def _stalk_A_decompose_312(stalk_A: np.ndarray, N: int, seed: int = 0):
    """
    EXP-312 Fix 2: P_yz-invariant Sector A decomposition.

    For N <= d_A: standard _orthogonal_decompose on stalk_A only.
    For N > d_A: zero-pad stalk_A to dim=N, decompose, take first d_A dims.

    Guarantees:
      - Input to _orthogonal_decompose depends only on stalk_A (not Sector B/C) -> P_yz-invariant
      - Sum conservation: sum(result_i) == stalk_A (exact, from zero-padding)
    """
    d_A = stalk_A.shape[0]
    if N <= d_A:
        return _orthogonal_decompose(stalk_A, N, seed=seed)
    padded = np.zeros(N)
    padded[:d_A] = stalk_A
    full_children = _orthogonal_decompose(padded, N, seed=seed)
    return [c[:d_A] for c in full_children]


def apply_gamma_312(
    mu,
    claim_id,
    partition_key,
    payloads,
    beta,
    budget,
    spent,
    focal_point=None,
    thresholds=None,
    alpha_leak=_ALPHA_LEAK_311,
    beta_CA=_BETA_CA_311,
    mass_ref=_MASS_REF_311,
    kappa_ref=_KAPPA_REF_311,
    g_inject_fn=None,
):
    """
    EXP-312 non-lossless Gamma operator.

    Reimplements the partition kernel with two P_yz fixes:
      Fix 1: payloads must be generated by _bbox_hash_payload_312 (caller responsibility)
      Fix 2: _stalk_A_decompose_312 for Sector A children (N > d_A case)

    Then applies EXP-311 G_inject EMA (default) or a caller-supplied g_inject_fn:
      default: G_inject_C[3] = alpha_leak * (||Z_before[0:4]|| / mass_ref)
               G_inject_A[7] = alpha_leak * beta_CA * (Z_before[11] / kappa_ref)
      override (EXP-315+): g_inject_fn(mass_norm, kappa_val, alpha_leak, beta_CA, mass_ref,
                            kappa_ref) -> (G_inject_C: ndarray(4), G_inject_A: ndarray(8))

    g_inject_fn=None preserves all EXP-311/312/313/314 behavior exactly (backward-compatible).

    Returns: (mu_next, cost, validity_class)
    """
    import numpy as _np
    from collections import deque as _deque

    if thresholds is None:
        thresholds = _LOD_THRESHOLDS_309
    if focal_point is None:
        focal_point = mu.focal_point_value()

    # Step 1: record Z_before
    Z_before = mu.Z()

    if claim_id not in mu.active:
        raise PartitionError(f"GAMMA312_ERROR: claim {claim_id} not in active set.")

    parent = mu.claims[claim_id]
    if parent.bbox is None:
        raise PartitionError(f"GAMMA312_ERROR: claim {claim_id} has no bbox.")

    if partition_key not in SPATIAL_KEYS:
        raise PartitionError(f"GAMMA312_UNKNOWN_KEY: '{partition_key}' not in {list(SPATIAL_KEYS.keys())}.")

    N = SPATIAL_KEYS[partition_key]
    if len(payloads) != N:
        raise PartitionError(f"GAMMA312_ERROR: expected {N} payloads, got {len(payloads)}.")

    # Step 2a: K-bound check
    k_children = sum(len(zlib.compress(p.encode("utf-8"), level=9)) for p in payloads)
    k_limit = parent.K_bound + C_KBOUND * math.log(N)
    if k_children > k_limit:
        raise PartitionError(
            f"GAMMA312_INFORMATION_OVERFLOW: sum K={k_children:.1f} > limit={k_limit:.2f}"
        )

    # Step 2b: backreaction cost
    from engine.state import EntailmentType
    cost = _cost(C0=1.0, beta=beta, S=mu.S)
    if spent + cost > budget:
        raise PartitionError(
            f"GAMMA312_BUDGET: spent={spent:.4f} + cost={cost:.4f} > B0={budget}"
        )

    # Step 2c: child bboxes
    child_bboxes = _compute_child_bboxes(parent.bbox, partition_key)

    # Step 2d: Sector A children (Fix 2: Sector A isolation)
    b0A, b1A = SECTOR_A_DIMS[0], SECTOR_A_DIMS[-1] + 1
    b0B, b1B = SECTOR_B_DIMS[0], SECTOR_B_DIMS[-1] + 1
    b0C = SECTOR_C_DIMS[0]; b1C = SECTOR_C_DIMS[-1] + 1
    b_k = SECTOR_C_KAPPA_DIM

    stalk_A = parent.stalk[b0A:b1A]
    d = len(parent.stalk)
    # Fix 2 (uniform): stalk_A_i = stalk_A / N for all i.
    # Proof: sum = N*(stalk_A/N) = stalk_A (conservation). All masses equal ->
    # mass-weighted centroid = geometric centroid -> P_yz-covariant focal evolution.
    # The index-based orthogonal decompose assigns mass by algebraic index, not
    # spatial octant. Under P_yz, octant i <-> octant (i XOR 4) permute, so
    # non-uniform mass breaks focal covariance. Uniform split is P_yz-invariant.
    stalk_A_children = [stalk_A / N for _ in range(N)]

    # Pre-compute parent sector norms for block-diagonal F
    stalk_A_parent = parent.stalk[b0A:b1A]
    stalk_B_parent = parent.stalk[b0B:b1B]
    stalk_N_parent = parent.stalk[b0C:b1C]
    kappa_parent = float(parent.stalk[b_k])
    stalk_A_nsq = float(_np.dot(stalk_A_parent, stalk_A_parent))
    stalk_B_nsq = float(_np.dot(stalk_B_parent, stalk_B_parent))
    stalk_N_nsq = float(_np.dot(stalk_N_parent, stalk_N_parent))

    # Step 2e: build child claims
    p_lo, p_hi = parent.bbox
    p_centroid = (p_lo + p_hi) / 2.0
    n_children = [
        _centroid_outward_normal((cb[0] + cb[1]) / 2.0, p_centroid)
        for cb in child_bboxes
    ]

    t_new = mu.t + 1
    new_claims = dict(mu.claims)
    new_ents = dict(mu.entailments)
    child_ids = []

    for i, (payload, stalk_A_i, (c_lo, c_hi), n_child) in enumerate(
            zip(payloads, stalk_A_children, child_bboxes, n_children)):
        centroid_B = (c_lo + c_hi) / 2.0
        kappa_child = _kappa_integral((c_lo, c_hi))

        child_stalk = _np.zeros(d)  # zero-init: Sector D (d>12) starts at 0; S_D tracks via EMA
        child_stalk[b0A:b1A] = stalk_A_i
        child_stalk[b0B:b0B + 3] = centroid_B
        child_stalk[SECTOR_B_DIMS[-1]] = 1.0
        child_stalk[b0C:b1C] = n_child
        child_stalk[b_k] = kappa_child

        prov = Provenance(
            parent_ids=(claim_id,),
            operator_id=f"Gamma312:{partition_key}:{i}",
            timestamp=now_iso(),
        )
        child = Claim(
            provenance=prov,
            payload=payload,
            stalk=child_stalk,
            t=t_new,
            bbox=(c_lo, c_hi),
        )

        # Block-diagonal restriction map (same structure as apply_gamma_308)
        F = _np.zeros((d, d))
        if stalk_A_nsq > 1e-30:
            F[b0A:b1A, b0A:b1A] = _np.outer(stalk_A_i, stalk_A_parent) / stalk_A_nsq
        if stalk_B_nsq > 1e-30:
            F[b0B:b1B, b0B:b1B] = _np.outer(child_stalk[b0B:b1B], stalk_B_parent) / stalk_B_nsq
        if stalk_N_nsq > 1e-30:
            F[b0C:b1C, b0C:b1C] = _np.outer(n_child, stalk_N_parent) / stalk_N_nsq
        if abs(kappa_parent) > 1e-30:
            F[b_k, b_k] = kappa_child / kappa_parent
        det_B = float(_np.linalg.det(F[b0B:b1B, b0B:b1B]))
        det_sign = int(_np.sign(det_B)) if abs(det_B) > 1e-30 else 1

        ent = Entailment(
            source_id=claim_id,
            target_id=child.id,
            etype=EntailmentType.SPATIAL,
            restriction=F,
            predicate_hash=hashlib.sha256(F.tobytes()).hexdigest()[:16],
            omega=1.0 / N,
            det_sign=det_sign,
        )
        new_claims[child.id] = child
        new_ents[(claim_id, child.id)] = ent
        child_ids.append(child.id)

    new_active = (mu.active - {claim_id}) | frozenset(child_ids)

    # S update: match apply_gamma_308 pattern (S_A/S_C decay separately)
    new_S_A = mu.next_S_A() if hasattr(mu, 'next_S_A') and callable(mu.next_S_A) else mu.S_A
    new_S_C = mu.next_S_C() if hasattr(mu, 'next_S_C') and callable(mu.next_S_C) else mu.S_C
    new_S = _np.concatenate([new_S_A, new_S_C]) if new_S_A is not None and new_S_C is not None else mu.next_S()

    mu_308 = MuState(
        t=t_new,
        claims=new_claims,
        entailments=new_ents,
        active=new_active,
        S=new_S,
        alpha=mu.alpha,
        S_A=new_S_A,
        S_C=new_S_C,
    )
    mu_308.seal()

    # Step 2f: LOD validity check
    valid, validity_class = _is_lod_valid_309(mu_308, focal_point, thresholds)
    if not valid:
        raise PartitionError(
            f"GAMMA312_INVALID after partition. claim_id={claim_id}"
        )

    # Step 2g: ghost quarantine for LOD_RELAXED
    bypass_reg = _bypass_registry_309(mu_308, focal_point, thresholds)
    if validity_class == "LOD_RELAXED":
        s_c_q = mu_308.next_S_C_309(bypass_reg)
        mu_308 = mu_308._replace_S_C(s_c_q)

    # Step 2h: update focal_point
    fp_new = mu_308.next_focal_point()
    mu_308 = mu_308._replace_focal_point(fp_new)
    mu_308 = mu_308._replace_validity_class(validity_class)

    # Step 3: compute G_inject from Z_before
    mass_norm = float(_np.linalg.norm(Z_before[0:4]))
    kappa_val = float(Z_before[11])

    if g_inject_fn is not None:
        G_inject_C, G_inject_A = g_inject_fn(
            mass_norm, kappa_val, alpha_leak, beta_CA, mass_ref, kappa_ref,
            Z_before=Z_before,
        )
        G_inject_C = _np.asarray(G_inject_C, dtype=float)
        G_inject_A = _np.asarray(G_inject_A, dtype=float)
    else:
        G_inject_C = _np.zeros(4)
        G_inject_C[3] = alpha_leak * (mass_norm / (mass_ref + 1e-15))
        G_inject_A = _np.zeros(8)
        G_inject_A[7] = alpha_leak * beta_CA * (kappa_val / (kappa_ref + 1e-15))

    # Step 4: EMA update S_C
    s_c = mu_308.S_C if mu_308.S_C is not None else _np.zeros(4)
    s_c_new = _ALPHA_EMA_311 * s_c + (1.0 - _ALPHA_EMA_311) * G_inject_C
    mu_next = mu_308._replace_S_C(s_c_new)

    # Step 5: EMA update S_A
    s_a = mu_next.S_A if mu_next.S_A is not None else _np.zeros(8)
    s_a_new = _ALPHA_EMA_311 * s_a + (1.0 - _ALPHA_EMA_311) * G_inject_A
    mu_next = mu_next._replace_S_A(s_a_new)

    # Step 6: propagate G_inject_log from INPUT mu
    log = getattr(mu, "G_inject_log", None)
    if log is None:
        log = []
    log = log + [(float(G_inject_C[3]), float(G_inject_A[7]))]
    mu_next.G_inject_log = log

    # Step 7: propagate ghost_history from INPUT mu
    _hist_src = getattr(mu, "ghost_history", None)
    if _hist_src is None:
        _hist = _deque(maxlen=32)
    else:
        _hist = _deque(_hist_src, maxlen=32)
    _hist.append((float(_np.linalg.norm(s_a_new)), float(_np.linalg.norm(s_c_new))))
    mu_next.ghost_history = _hist

    return mu_next, cost, validity_class


def apply_gamma_312_recursive(
    mu,
    claim_id,
    partition_key,
    beta,
    budget,
    spent,
    K_budget,
    depth=0,
    focal_point=None,
    thresholds=None,
    alpha_leak=_ALPHA_LEAK_311,
    beta_CA=_BETA_CA_311,
    mass_ref=_MASS_REF_311,
    kappa_ref=_KAPPA_REF_311,
):
    """
    Recursive EXP-312 operator.

    Uses _bbox_hash_payload_312 (extents-based) for P_yz-invariant payload generation.
    Uses _stalk_A_decompose_312 via apply_gamma_312 for P_yz-invariant Sector A children.

    Multi-step leaf counts and norm(S_C), norm(S_A) are P_yz-invariant
    when focal_point is derived from mu.focal_point_value() (not externally fixed).

    Returns: (final_mu, total_cost)
    """
    if thresholds is None:
        thresholds = _LOD_THRESHOLDS_309
    if focal_point is None:
        focal_point = mu.focal_point_value()

    if K_budget < K_MIN_PARTITION:
        return mu, 0.0

    if getattr(mu, "validity_class", "FULL_VALID") == "LOD_RELAXED":
        return mu, 0.0

    N = SPATIAL_KEYS[partition_key]
    child_bboxes_preview = _compute_child_bboxes(mu.claims[claim_id].bbox, partition_key)
    # Fix 1: extents-based payloads
    payloads = [
        _bbox_hash_payload_312(child_bboxes_preview[i], depth, i)
        for i in range(N)
    ]

    try:
        mu_next, cost, validity_class = apply_gamma_312(
            mu=mu,
            claim_id=claim_id,
            partition_key=partition_key,
            payloads=payloads,
            beta=beta,
            budget=budget,
            spent=spent,
            focal_point=focal_point,
            thresholds=thresholds,
            alpha_leak=alpha_leak,
            beta_CA=beta_CA,
            mass_ref=mass_ref,
            kappa_ref=kappa_ref,
        )
    except PartitionError:
        return mu, 0.0

    total_cost = cost
    spent_now = spent + cost
    K_child = K_budget * math.exp(-LAMBDA_DECAY)
    fp_next = mu_next.focal_point_value()

    if validity_class == "FULL_VALID":
        new_child_ids = [cid for cid in mu_next.active if cid not in mu.active]
        for cid in new_child_ids:
            mu_next, rc = apply_gamma_312_recursive(
                mu=mu_next,
                claim_id=cid,
                partition_key=partition_key,
                beta=beta,
                budget=budget,
                spent=spent_now,
                K_budget=K_child,
                depth=depth + 1,
                focal_point=fp_next,
                thresholds=thresholds,
                alpha_leak=alpha_leak,
                beta_CA=beta_CA,
                mass_ref=mass_ref,
                kappa_ref=kappa_ref,
            )
            total_cost += rc
            spent_now += rc

    return mu_next, total_cost


# ===========================================================================
# EXP-313 -- The Zeeman K_bound
# Field-weighted K_budget allocation via Zeeman energy level splitting.
# Declaration hash: 708e7b75be7bbd907568fcbd16a32fa128ceea0e0112dcdc64de38e8480273b4
# ===========================================================================

_B_DEFAULT_313 = np.array([1.0, 0.5, 0.3])
_BETA_Z_313 = 2.0


def _zeeman_weights(child_bboxes, B: np.ndarray, beta_Z: float) -> np.ndarray:
    """
    EXP-313: softmax Zeeman weights for child octant budget allocation.

    w_i = softmax(beta_Z * (centroid_i . B_hat))
    P_yz covariance: w_fwd[i] == w_mir[i XOR 4] when B_mir = P_yz(B_fwd).
    """
    B_hat = B / (np.linalg.norm(B) + 1e-30)
    centroids = np.array([(np.array(cb[0]) + np.array(cb[1])) / 2.0
                          for cb in child_bboxes])
    projections = centroids @ B_hat          # shape (N,)
    logits = beta_Z * projections
    logits -= logits.max()                   # numerical stability
    weights = np.exp(logits)
    weights /= weights.sum()
    return weights                           # shape (N,), sums to 1.0


def apply_gamma_313(
    mu,
    claim_id,
    partition_key,
    payloads,
    beta,
    budget,
    spent,
    focal_point=None,
    B=None,
    beta_Z=_BETA_Z_313,
    thresholds=None,
    alpha_leak=_ALPHA_LEAK_311,
    beta_CA=_BETA_CA_311,
    mass_ref=_MASS_REF_311,
    kappa_ref=_KAPPA_REF_311,
    g_inject_fn=None,
):
    """
    EXP-313: Zeeman K_bound operator.

    Delegates partition kernel to apply_gamma_312 (Fix1 + Fix2 inherited).
    K_budget weighting is handled in apply_gamma_313_recursive.
    This single-step function is identical to apply_gamma_312 — the Zeeman
    splitting affects only the per-child K_budget passed in recursive calls.
    g_inject_fn passes through to apply_gamma_312 for EXP-315+ overrides.

    Returns: (mu_next, cost, validity_class)
    """
    if B is None:
        B = _B_DEFAULT_313
    return apply_gamma_312(
        mu=mu,
        claim_id=claim_id,
        partition_key=partition_key,
        payloads=payloads,
        beta=beta,
        budget=budget,
        spent=spent,
        focal_point=focal_point,
        thresholds=thresholds,
        alpha_leak=alpha_leak,
        beta_CA=beta_CA,
        mass_ref=mass_ref,
        kappa_ref=kappa_ref,
        g_inject_fn=g_inject_fn,
    )


def apply_gamma_313_recursive(
    mu,
    claim_id,
    partition_key,
    beta,
    budget,
    spent,
    K_budget,
    depth=0,
    focal_point=None,
    B=None,
    beta_Z=_BETA_Z_313,
    thresholds=None,
    alpha_leak=_ALPHA_LEAK_311,
    beta_CA=_BETA_CA_311,
    mass_ref=_MASS_REF_311,
    kappa_ref=_KAPPA_REF_311,
):
    """
    Recursive EXP-313 operator with Zeeman K_budget splitting.

    Each child octant i receives:
        K_child_i = K_budget * N * w_i * exp(-LAMBDA_DECAY)
    where w_i = softmax(beta_Z * (centroid_i . B_hat)).

    P_yz covariance: K_fwd[i] == K_mir[i XOR 4] when B_mir = P_yz(B_fwd).
    Multi-step invariance: fwd_leaves == mir_leaves (by induction, see ENGINE_AXIOMS).

    Returns: (final_mu, total_cost, K_weights_step0)
      K_weights_step0: np.ndarray(N,) of Zeeman weights at depth=0, for Fork A/B diagnostics.
    """
    if B is None:
        B = _B_DEFAULT_313
    if thresholds is None:
        thresholds = _LOD_THRESHOLDS_309
    if focal_point is None:
        focal_point = mu.focal_point_value()

    if K_budget < K_MIN_PARTITION:
        return mu, 0.0, None

    if getattr(mu, "validity_class", "FULL_VALID") == "LOD_RELAXED":
        return mu, 0.0, None

    N = SPATIAL_KEYS[partition_key]
    child_bboxes_preview = _compute_child_bboxes(mu.claims[claim_id].bbox, partition_key)

    # Fix 1 (inherited): extents-based payloads
    payloads = [
        _bbox_hash_payload_312(child_bboxes_preview[i], depth, i)
        for i in range(N)
    ]

    # Zeeman weights for this node
    w = _zeeman_weights(child_bboxes_preview, B, beta_Z)  # shape (N,)

    try:
        mu_next, cost, validity_class = apply_gamma_313(
            mu=mu,
            claim_id=claim_id,
            partition_key=partition_key,
            payloads=payloads,
            beta=beta,
            budget=budget,
            spent=spent,
            focal_point=focal_point,
            B=B,
            beta_Z=beta_Z,
            thresholds=thresholds,
            alpha_leak=alpha_leak,
            beta_CA=beta_CA,
            mass_ref=mass_ref,
            kappa_ref=kappa_ref,
        )
    except PartitionError:
        return mu, 0.0, w

    total_cost = cost
    spent_now = spent + cost
    # fp_next = bbox centroid of the CURRENT node (not accumulated focal_point_value).
    # Rationale: focal_point_value() accumulates expansions of previously processed
    # siblings, making LOD gating order-dependent and P_yz-variant under non-uniform
    # Zeeman budgets. bbox centroid is deterministic and P_yz-covariant at every depth:
    #   centroid(bbox_mir[i^4]) = P_yz(centroid(bbox_fwd[i]))  (isometry)
    # For EXP-312 uniform masses: bbox centroid == focal_point_value() (identical result).
    _cur_lo, _cur_hi = np.array(mu.claims[claim_id].bbox[0]), np.array(mu.claims[claim_id].bbox[1])
    fp_next = (_cur_lo + _cur_hi) / 2.0

    if validity_class == "FULL_VALID":
        new_child_ids = [cid for cid in mu_next.active if cid not in mu.active]
        # Match each new child to its bbox index in child_bboxes_preview by bbox comparison.
        # frozenset iteration order is non-deterministic -- cannot use enumerate directly.
        def _bbox_match_index(cid):
            cb = mu_next.claims[cid].bbox
            cb_lo = np.array(cb[0]); cb_hi = np.array(cb[1])
            for idx, (pb_lo, pb_hi) in enumerate(child_bboxes_preview):
                if (np.allclose(cb_lo, np.array(pb_lo), atol=1e-12) and
                        np.allclose(cb_hi, np.array(pb_hi), atol=1e-12)):
                    return idx
            return 0  # fallback (should not occur)
        # Sort by DESCENDING Zeeman weight for deterministic P_yz-covariant order.
        # Paired children (i <-> i XOR 4) process at the same step in fwd/mir:
        # => Z_before[11] (kappa aggregate) identical at every corresponding step
        # => G_inject_A[7] = f(Z_before[11]) equal => S_A identical => cost invariant.
        child_idx_pairs = sorted(
            [(_bbox_match_index(cid), cid) for cid in new_child_ids],
            key=lambda x: -float(w[x[0]])
        )
        for i, cid in child_idx_pairs:
            # Formula: K_child_i = K_budget * w_i * exp(-LAMBDA_DECAY)
            # No N factor -- budget strictly decreases (w_i<=1, exp<1).
            K_child_i = K_budget * float(w[i]) * math.exp(-LAMBDA_DECAY)
            mu_next, rc, _ = apply_gamma_313_recursive(
                mu=mu_next,
                claim_id=cid,
                partition_key=partition_key,
                beta=beta,
                budget=budget,
                spent=spent_now,
                K_budget=K_child_i,
                depth=depth + 1,
                focal_point=fp_next,
                B=B,
                beta_Z=beta_Z,
                thresholds=thresholds,
                alpha_leak=alpha_leak,
                beta_CA=beta_CA,
                mass_ref=mass_ref,
                kappa_ref=kappa_ref,
            )
            total_cost += rc
            spent_now += rc

    return mu_next, total_cost, w


# ===========================================================================
# EXP-314 -- The Hyperfine Ghost
# J_AC coupling: inter-channel precession angle Omega_AC + lag tau_opt.
# Declaration hash: 5ca52bef5d2a508073ab8585a1e84aa8393e64ddd7672c2c48ab4dd4a0a5006c
# ===========================================================================

_J_AC_DEFAULT_314 = np.eye(4)   # 4x4 identity (direct S_A[0:4] <-> S_C coupling)
_W_MAX_314 = 8


def _compute_omega_ac(S_A: np.ndarray, S_C: np.ndarray,
                      J_AC: np.ndarray, eps: float = 1e-15) -> float:
    """
    EXP-314: precession angle between ghost channels S_A and S_C.

    Primary formula (dot-product path):
      v_A = J_AC @ S_A[0:4]
      Omega_AC = arccos(clip(v_A . S_C / (||v_A|| * ||S_C|| + eps), -1, 1))

    Fallback (norm-ratio path) triggered when ||v_A|| < NUMERIC_FLOOR:
      The G_inject architecture injects into S_A[7] and S_C[3] exclusively.
      Under lossless partition G_A = 0 => S_A[0:4] = 0 in exact arithmetic.
      ||v_A|| < NUMERIC_FLOOR means the arccos numerator/denominator are both
      floating-point noise (O(1e-15)) -- result is non-deterministic under P_yz.
      Fallback: Omega_AC = 2 * arctan2(||S_C||, ||S_A||) in (0, pi).
      This is P_yz-invariant (||S_A|| and ||S_C|| proven invariant by EXP-313 [5][6]).
      tau_opt formula unchanged: max(1, round(Omega_AC / pi * W_max)).

    Dev note (ghost #6 fix -- EXP-314 implementation): The arccos formula is
    forward-compatible; once G_inject_A targets dims in S_A[0:4] the primary
    path activates automatically. The fallback is only a numerical guard.
    """
    NUMERIC_FLOOR = 1e-6   # below this, v_A is entirely floating-point noise
    v_A = J_AC @ S_A[:4]
    norm_vA = float(np.linalg.norm(v_A))
    norm_C = float(np.linalg.norm(S_C))
    if norm_vA >= NUMERIC_FLOOR and norm_C >= NUMERIC_FLOOR:
        # Primary: arccos of cosine between coupled projections
        cos_val = float(np.dot(v_A, S_C)) / (norm_vA * norm_C + eps)
        cos_val = float(np.clip(cos_val, -1.0, 1.0))
        return float(np.arccos(cos_val))
    # Fallback: norm-ratio precession angle in (0, pi)
    norm_A = float(np.linalg.norm(S_A))
    norm_C2 = float(np.linalg.norm(S_C))
    return float(2.0 * np.arctan2(norm_C2 + eps, norm_A + eps))


def _tau_opt(omega_ac: float, W_max: int = _W_MAX_314) -> int:
    """Deterministic lag from precession angle: tau_opt = max(1, round(Omega/pi * W_max))."""
    return max(1, round(omega_ac / math.pi * W_max))


def apply_gamma_314(
    mu,
    claim_id,
    partition_key,
    payloads,
    beta,
    budget,
    spent,
    focal_point=None,
    B=None,
    beta_Z=_BETA_Z_313,
    J_AC=None,
    W_max=_W_MAX_314,
    thresholds=None,
    alpha_leak=_ALPHA_LEAK_311,
    beta_CA=_BETA_CA_311,
    mass_ref=_MASS_REF_311,
    kappa_ref=_KAPPA_REF_311,
    g_inject_fn=None,
):
    """
    EXP-314: Hyperfine ghost coupling operator.

    Wraps apply_gamma_313. After partition, computes:
      v_A = J_AC @ S_A[0:4]
      Omega_AC = arccos(clip(v_A . S_C / (|v_A||S_C| + eps), -1, 1))
      tau_opt  = max(1, round(Omega_AC / pi * W_max))

    Appends (|S_A|, |S_C|, Omega_AC, tau_opt) to ghost_history.
    Dual-space only: Z_t and stalk values not modified.
    g_inject_fn passes through to apply_gamma_312 for EXP-315+ overrides.

    Returns: (mu_next, cost, validity_class)
    """
    if J_AC is None:
        J_AC = _J_AC_DEFAULT_314
    J_AC = np.array(J_AC)

    mu_313, cost, validity_class = apply_gamma_313(
        mu=mu,
        claim_id=claim_id,
        partition_key=partition_key,
        payloads=payloads,
        beta=beta,
        budget=budget,
        spent=spent,
        focal_point=focal_point,
        B=B,
        beta_Z=beta_Z,
        thresholds=thresholds,
        alpha_leak=alpha_leak,
        beta_CA=beta_CA,
        mass_ref=mass_ref,
        kappa_ref=kappa_ref,
        g_inject_fn=g_inject_fn,
    )

    S_A = mu_313.S_A if mu_313.S_A is not None else np.zeros(8)
    S_C = mu_313.S_C if mu_313.S_C is not None else np.zeros(4)

    omega = _compute_omega_ac(S_A, S_C, J_AC)
    tau = _tau_opt(omega, W_max)

    # Append to ghost_history: (S_A_norm, S_C_norm, Omega_AC, tau_opt)
    prev_gh = list(getattr(mu_313, "ghost_history", []) or [])
    prev_gh.append((float(np.linalg.norm(S_A)), float(np.linalg.norm(S_C)),
                    float(omega), int(tau)))

    try:
        mu_next = mu_313._replace(ghost_history=prev_gh)
    except Exception:
        object.__setattr__(mu_313, "ghost_history", prev_gh)
        mu_next = mu_313

    return mu_next, cost, validity_class


def apply_gamma_314_recursive(
    mu,
    claim_id,
    partition_key,
    beta,
    budget,
    spent,
    K_budget,
    depth=0,
    focal_point=None,
    B=None,
    beta_Z=_BETA_Z_313,
    J_AC=None,
    W_max=_W_MAX_314,
    thresholds=None,
    alpha_leak=_ALPHA_LEAK_311,
    beta_CA=_BETA_CA_311,
    mass_ref=_MASS_REF_311,
    kappa_ref=_KAPPA_REF_311,
    g_inject_fn=None,
):
    """
    Recursive EXP-314 operator with Zeeman K_budget + hyperfine Omega_AC logging.

    Inherits all EXP-313 structural properties (P_yz invariance, Zeeman splitting,
    bbox-centroid fp, weight-sorted child ordering). Adds Omega_AC and tau_opt
    to ghost_history at each partition step.
    g_inject_fn passes through to apply_gamma_312 for EXP-315+ overrides.

    Returns: (final_mu, total_cost, K_weights_step0)
    """
    if B is None:
        B = _B_DEFAULT_313
    if J_AC is None:
        J_AC = _J_AC_DEFAULT_314
    J_AC = np.array(J_AC)
    if thresholds is None:
        thresholds = _LOD_THRESHOLDS_309
    if focal_point is None:
        focal_point = mu.focal_point_value()

    if K_budget < K_MIN_PARTITION:
        return mu, 0.0, None

    if getattr(mu, "validity_class", "FULL_VALID") == "LOD_RELAXED":
        return mu, 0.0, None

    N = SPATIAL_KEYS[partition_key]
    child_bboxes_preview = _compute_child_bboxes(mu.claims[claim_id].bbox, partition_key)

    payloads = [
        _bbox_hash_payload_312(child_bboxes_preview[i], depth, i)
        for i in range(N)
    ]

    w = _zeeman_weights(child_bboxes_preview, B, beta_Z)

    try:
        mu_next, cost, validity_class = apply_gamma_314(
            mu=mu,
            claim_id=claim_id,
            partition_key=partition_key,
            payloads=payloads,
            beta=beta,
            budget=budget,
            spent=spent,
            focal_point=focal_point,
            B=B,
            beta_Z=beta_Z,
            J_AC=J_AC,
            W_max=W_max,
            thresholds=thresholds,
            alpha_leak=alpha_leak,
            beta_CA=beta_CA,
            mass_ref=mass_ref,
            kappa_ref=kappa_ref,
            g_inject_fn=g_inject_fn,
        )
    except PartitionError:
        return mu, 0.0, w

    total_cost = cost
    spent_now = spent + cost

    _cur_lo = np.array(mu.claims[claim_id].bbox[0])
    _cur_hi = np.array(mu.claims[claim_id].bbox[1])
    fp_next = (_cur_lo + _cur_hi) / 2.0

    if validity_class == "FULL_VALID":
        new_child_ids = [cid for cid in mu_next.active if cid not in mu.active]

        def _bbox_match_idx(cid):
            cb = mu_next.claims[cid].bbox
            cb_lo = np.array(cb[0]); cb_hi = np.array(cb[1])
            for idx, (pb_lo, pb_hi) in enumerate(child_bboxes_preview):
                if (np.allclose(cb_lo, np.array(pb_lo), atol=1e-12) and
                        np.allclose(cb_hi, np.array(pb_hi), atol=1e-12)):
                    return idx
            return 0

        child_idx_pairs = sorted(
            [(_bbox_match_idx(cid), cid) for cid in new_child_ids],
            key=lambda x: -float(w[x[0]])
        )
        for i, cid in child_idx_pairs:
            K_child_i = K_budget * float(w[i]) * math.exp(-LAMBDA_DECAY)
            mu_next, rc, _ = apply_gamma_314_recursive(
                mu=mu_next,
                claim_id=cid,
                partition_key=partition_key,
                beta=beta,
                budget=budget,
                spent=spent_now,
                K_budget=K_child_i,
                depth=depth + 1,
                focal_point=fp_next,
                B=B,
                beta_Z=beta_Z,
                J_AC=J_AC,
                W_max=W_max,
                thresholds=thresholds,
                alpha_leak=alpha_leak,
                beta_CA=beta_CA,
                mass_ref=mass_ref,
                kappa_ref=kappa_ref,
                g_inject_fn=g_inject_fn,
            )
            total_cost += rc
            spent_now += rc

    return mu_next, total_cost, w


# ===========================================================================
# EXP-315 -- Dual G_inject_A Activation
# Routes mass-norm coupling into S_A[0] and kappa coupling into S_A[3].
# Activates primary Omega_AC arccos path. tau_opt varies with mass/kappa ratio.
# Declaration hash: e16dd1a01735bc1d6a97100daf2bfb3dfd172e2853b5875a875ccc54ea5933b0
# ===========================================================================

def _g_inject_315(mass_norm, kappa_val, alpha_leak, beta_CA, mass_ref, kappa_ref, Z_before=None):
    """
    EXP-315 dual G_inject_A function.

    G_inject_A[0] = alpha_leak * (mass_norm / mass_ref)           [mass-norm coupling]
    G_inject_A[3] = alpha_leak * beta_CA * (kappa_val / kappa_ref) [kappa coupling]
    G_inject_C[3] = alpha_leak * (mass_norm / mass_ref)            [unchanged]

    P_yz-invariant:
      mass_norm = ||Z_before[0:4]|| = ||sum(Sector A stalks)|| -- Sector A unchanged under P_yz
      kappa_val = Z_before[11] -- extents-based, P_yz-invariant (EXP-312)

    Returns: (G_inject_C: ndarray(4), G_inject_A: ndarray(8))
    """
    eps = 1e-15
    G_C = np.zeros(4)
    G_C[3] = alpha_leak * (mass_norm / (mass_ref + eps))

    G_A = np.zeros(8)
    G_A[0] = alpha_leak * (mass_norm / (mass_ref + eps))
    G_A[3] = alpha_leak * beta_CA * (kappa_val / (kappa_ref + eps))

    return G_C, G_A


def apply_gamma_315(
    mu,
    claim_id,
    partition_key,
    payloads,
    beta,
    budget,
    spent,
    focal_point=None,
    B=None,
    beta_Z=_BETA_Z_313,
    J_AC=None,
    W_max=_W_MAX_314,
    thresholds=None,
    alpha_leak=_ALPHA_LEAK_311,
    beta_CA=_BETA_CA_311,
    mass_ref=_MASS_REF_311,
    kappa_ref=_KAPPA_REF_311,
):
    """
    EXP-315: Dual G_inject_A operator.

    Calls apply_gamma_314 with g_inject_fn=_g_inject_315.
    Injects G_inject_A[0] = f(mass_norm) and G_inject_A[3] = f(kappa).
    This activates the primary Omega_AC arccos path:
      v_A = J_AC @ S_A[0:4] = [S_A0, 0, 0, S_A3]  (both non-zero)
      Omega_AC = arctan(S_A0 / S_A3) = arctan(mass_norm / (beta_CA * kappa))
      tau_opt varies with mass/kappa ratio across tree depth.

    P_yz-invariant: both injection sources are P_yz-invariant.
    Fallback path in _compute_omega_ac not activated.

    Returns: (mu_next, cost, validity_class)
    """
    if J_AC is None:
        J_AC = _J_AC_DEFAULT_314
    J_AC = np.array(J_AC)

    return apply_gamma_314(
        mu=mu,
        claim_id=claim_id,
        partition_key=partition_key,
        payloads=payloads,
        beta=beta,
        budget=budget,
        spent=spent,
        focal_point=focal_point,
        B=B,
        beta_Z=beta_Z,
        J_AC=J_AC,
        W_max=W_max,
        thresholds=thresholds,
        alpha_leak=alpha_leak,
        beta_CA=beta_CA,
        mass_ref=mass_ref,
        kappa_ref=kappa_ref,
        g_inject_fn=_g_inject_315,
    )


def apply_gamma_315_recursive(
    mu,
    claim_id,
    partition_key,
    beta,
    budget,
    spent,
    K_budget,
    depth=0,
    focal_point=None,
    B=None,
    beta_Z=_BETA_Z_313,
    J_AC=None,
    W_max=_W_MAX_314,
    thresholds=None,
    alpha_leak=_ALPHA_LEAK_311,
    beta_CA=_BETA_CA_311,
    mass_ref=_MASS_REF_311,
    kappa_ref=_KAPPA_REF_311,
):
    """
    Recursive EXP-315 operator.

    Inherits Zeeman K_budget, bbox-centroid fp, weight-sorted child ordering (EXP-313).
    Inherits Omega_AC ghost_history logging (EXP-314).
    Uses dual G_inject_A (EXP-315): S_A[0] = mass-norm, S_A[3] = kappa.
    Primary Omega_AC arccos path active; tau_opt varies with mass/kappa balance.

    Returns: (final_mu, total_cost, K_weights_step0)
    """
    return apply_gamma_314_recursive(
        mu=mu,
        claim_id=claim_id,
        partition_key=partition_key,
        beta=beta,
        budget=budget,
        spent=spent,
        K_budget=K_budget,
        depth=depth,
        focal_point=focal_point,
        B=B,
        beta_Z=beta_Z,
        J_AC=J_AC,
        W_max=W_max,
        thresholds=thresholds,
        alpha_leak=alpha_leak,
        beta_CA=beta_CA,
        mass_ref=mass_ref,
        kappa_ref=kappa_ref,
        g_inject_fn=_g_inject_315,
    )


# ===========================================================================
# EXP-316 -- 3-Component G_inject_A: y-aggregate coupling into S_A[1]
# Extends EXP-315 dual injection with a third channel from |Z_before[5]|.
# v_A = [S_A0, S_A1, 0, S_A3] -- 3-component non-degenerate precession vector.
# Full 4D angular resolution of ghost precession beyond the planar EXP-315 angle.
# Series 300 hardening (final).
# ===========================================================================

_Y_REF_316 = 1.0  # y-coordinate reference scale


def _g_inject_316(
    mass_norm, kappa_val, alpha_leak, beta_CA, mass_ref, kappa_ref,
    Z_before=None, y_ref=_Y_REF_316,
):
    """
    EXP-316 three-component G_inject_A function.

    G_inject_A[0] = alpha_leak * (mass_norm / mass_ref)               [mass-norm, EXP-315]
    G_inject_A[1] = alpha_leak * (|Z_before[5]| / y_ref)              [y-agg coupling, NEW]
    G_inject_A[3] = alpha_leak * beta_CA * (kappa_val / kappa_ref)    [kappa, EXP-315]
    G_inject_C[3] = alpha_leak * (mass_norm / mass_ref)               [unchanged]

    P_yz-invariance:
      Z_before[5] = aggregate y-coordinate (Sector B dim 1).
      p_yz_stalk negates stalk[4] (x) and stalk[8] (nx); stalk[5] (y) unchanged.
      => |Z_before[5]| P_yz-invariant => G_inject_A[1] P_yz-invariant.

    Returns: (G_inject_C: ndarray(4), G_inject_A: ndarray(8))
    """
    eps = 1e-15
    G_C = np.zeros(4)
    G_C[3] = alpha_leak * (mass_norm / (mass_ref + eps))

    G_A = np.zeros(8)
    G_A[0] = alpha_leak * (mass_norm / (mass_ref + eps))
    if Z_before is not None:
        y_val = abs(float(Z_before[5]))
    else:
        y_val = 0.0
    G_A[1] = alpha_leak * (y_val / (y_ref + eps))
    G_A[3] = alpha_leak * beta_CA * (kappa_val / (kappa_ref + eps))

    return G_C, G_A


def apply_gamma_316(
    mu,
    claim_id,
    partition_key,
    payloads,
    beta,
    budget,
    spent,
    focal_point=None,
    B=None,
    beta_Z=_BETA_Z_313,
    J_AC=None,
    W_max=_W_MAX_314,
    thresholds=None,
    alpha_leak=_ALPHA_LEAK_311,
    beta_CA=_BETA_CA_311,
    mass_ref=_MASS_REF_311,
    kappa_ref=_KAPPA_REF_311,
    y_ref=_Y_REF_316,
):
    """
    EXP-316: Three-component G_inject_A operator.

    Calls apply_gamma_314 with g_inject_fn=_g_inject_316.
    Injects G_inject_A[0]=f(mass_norm), G_inject_A[1]=f(|y_agg|), G_inject_A[3]=f(kappa).
    v_A = J_AC @ S_A[0:4] = [S_A0, S_A1, 0, S_A3]  (three non-zero dims)
    Omega_AC = arccos(S_A3 / sqrt(S_A0^2 + S_A1^2 + S_A3^2))
    tau_opt varies with three-way mass/y/kappa balance.
    P_yz-invariant: all three injection sources P_yz-invariant.

    Returns: (mu_next, cost, validity_class)
    """
    import functools
    if J_AC is None:
        J_AC = _J_AC_DEFAULT_314
    J_AC = np.array(J_AC)
    fn = functools.partial(_g_inject_316, y_ref=y_ref)

    return apply_gamma_314(
        mu=mu,
        claim_id=claim_id,
        partition_key=partition_key,
        payloads=payloads,
        beta=beta,
        budget=budget,
        spent=spent,
        focal_point=focal_point,
        B=B,
        beta_Z=beta_Z,
        J_AC=J_AC,
        W_max=W_max,
        thresholds=thresholds,
        alpha_leak=alpha_leak,
        beta_CA=beta_CA,
        mass_ref=mass_ref,
        kappa_ref=kappa_ref,
        g_inject_fn=fn,
    )


def apply_gamma_316_recursive(
    mu,
    claim_id,
    partition_key,
    beta,
    budget,
    spent,
    K_budget,
    depth=0,
    focal_point=None,
    B=None,
    beta_Z=_BETA_Z_313,
    J_AC=None,
    W_max=_W_MAX_314,
    thresholds=None,
    alpha_leak=_ALPHA_LEAK_311,
    beta_CA=_BETA_CA_311,
    mass_ref=_MASS_REF_311,
    kappa_ref=_KAPPA_REF_311,
    y_ref=_Y_REF_316,
):
    """
    Recursive EXP-316 operator.

    Inherits Zeeman K_budget, bbox-centroid fp, weight-sorted child ordering (EXP-313).
    Inherits Omega_AC ghost_history logging (EXP-314).
    Inherits dual G_inject_A channels 0+3 (EXP-315).
    Adds y-aggregate channel G_inject_A[1] (EXP-316): 3-component v_A.
    Full 4D angular resolution of ghost precession.

    Returns: (final_mu, total_cost, K_weights_step0)
    """
    import functools
    fn = functools.partial(_g_inject_316, y_ref=y_ref)

    return apply_gamma_314_recursive(
        mu=mu,
        claim_id=claim_id,
        partition_key=partition_key,
        beta=beta,
        budget=budget,
        spent=spent,
        K_budget=K_budget,
        depth=depth,
        focal_point=focal_point,
        B=B,
        beta_Z=beta_Z,
        J_AC=J_AC,
        W_max=W_max,
        thresholds=thresholds,
        alpha_leak=alpha_leak,
        beta_CA=beta_CA,
        mass_ref=mass_ref,
        kappa_ref=kappa_ref,
        g_inject_fn=fn,
    )


# ===========================================================================
# EXP-401 -- Anisotropic Gaussian Covariance
# Extends EXP-316 with Sector D: 6-dim log-Cholesky covariance.
# G_inject_D[3:6] aligned to B_hat outer-product, modulated by tau_opt.
# Covariance tensor test (Fork B): Sigma_mir = R * Sigma_fwd * R^T, R=diag(-1,1,1).
# ===========================================================================

_ALPHA_D_401  = 0.05   # injection rate for Sector D
_Y_REF_316_   = 1.0    # re-export for EXP-401 use

def p_yz_stalk_401(stalk):
    """P_yz reflection for d=18 stalk. Extends EXP-316 with Sector D terms.
    Negates: stalk[4]=x, stalk[8]=nx, stalk[15]=l21 (xy), stalk[16]=l31 (xz).
    stalk[17]=l32 (yz) unchanged: no x component.
    """
    s = stalk.copy()
    s[4]  = -s[4]
    s[8]  = -s[8]
    s[15] = -s[15]
    s[16] = -s[16]
    return s


def _g_inject_401(
    mass_norm, kappa_val, alpha_leak, beta_CA, mass_ref, kappa_ref,
    Z_before=None, y_ref=_Y_REF_316_,
    B=None, tau_opt=1, W_max=8, alpha_D=_ALPHA_D_401,
):
    """
    EXP-401 injection function.

    Inherits EXP-316 channels:
      G_inject_A[0] = alpha_leak * (mass_norm / mass_ref)
      G_inject_A[1] = alpha_leak * (|Z_before[5]| / y_ref)
      G_inject_A[3] = alpha_leak * beta_CA * (kappa / kappa_ref)
      G_inject_C[3] = alpha_leak * (mass_norm / mass_ref)

    New Sector D channel:
      tau_norm = tau_opt / W_max  in [1/8, 1]
      B_hat    = B / ||B||
      G_inject_D[3] = alpha_D * tau_norm * B_hat[0] * B_hat[1]   (l21: xy)
      G_inject_D[4] = alpha_D * tau_norm * B_hat[0] * B_hat[2]   (l31: xz)
      G_inject_D[5] = alpha_D * tau_norm * B_hat[1] * B_hat[2]   (l32: yz)
      G_inject_D[0:3] = 0  (diagonal log-scales: identity in EXP-401)

    P_yz covariance proof:
      B_hat[0] -> -B_hat[0] under P_yz
      => G_D[3] -> -G_D[3]  =>  S_D[3] -> -S_D[3]  (l21 negates)  checkmark
      => G_D[4] -> -G_D[4]  =>  S_D[4] -> -S_D[4]  (l31 negates)  checkmark
      => G_D[5] unchanged   =>  S_D[5] unchanged    (l32 invariant) checkmark
      => Sigma_mir = R * Sigma_fwd * R^T  QED

    Returns: (G_inject_C: ndarray(4), G_inject_A: ndarray(8), G_inject_D: ndarray(6))
    """
    eps = 1e-15

    G_C = np.zeros(4)
    G_C[3] = alpha_leak * (mass_norm / (mass_ref + eps))

    G_A = np.zeros(8)
    G_A[0] = alpha_leak * (mass_norm / (mass_ref + eps))
    y_val = abs(float(Z_before[5])) if Z_before is not None else 0.0
    G_A[1] = alpha_leak * (y_val / (y_ref + eps))
    G_A[3] = alpha_leak * beta_CA * (kappa_val / (kappa_ref + eps))

    G_D = np.zeros(6)
    if B is not None and W_max > 0:
        B_arr = np.asarray(B, dtype=float)
        B_norm = float(np.linalg.norm(B_arr))
        if B_norm > eps:
            B_hat = B_arr / B_norm
            tau_norm = float(tau_opt) / float(W_max)
            G_D[3] = alpha_D * tau_norm * B_hat[0] * B_hat[1]
            G_D[4] = alpha_D * tau_norm * B_hat[0] * B_hat[2]
            G_D[5] = alpha_D * tau_norm * B_hat[1] * B_hat[2]

    return G_C, G_A, G_D


def apply_gamma_401_recursive(
    mu,
    claim_id,
    partition_key,
    beta,
    budget,
    spent,
    K_budget,
    depth=0,
    focal_point=None,
    B=None,
    beta_Z=_BETA_Z_313,
    J_AC=None,
    W_max=_W_MAX_314,
    thresholds=None,
    alpha_leak=_ALPHA_LEAK_311,
    beta_CA=_BETA_CA_311,
    mass_ref=_MASS_REF_311,
    kappa_ref=_KAPPA_REF_311,
    y_ref=_Y_REF_316_,
    alpha_D=_ALPHA_D_401,
):
    """
    Recursive EXP-401 operator.

    Inherits all EXP-316 properties (3-component v_A, Zeeman K_budget, Omega_AC,
    tau_opt in {1,2,3}). Adds Sector D covariance update:
      S_D tracks log-Cholesky off-diagonals aligned to B_hat,
      modulated by retarded tau_opt from previous ghost_history entry.

    Fork B invariant: Sigma_mir = R * Sigma_fwd * R^T  where R = diag(-1,1,1).

    Returns: (final_mu, total_cost, K_weights_step0)
    """
    if B is None:
        B = np.array([1.0, 0.0, 0.0])

    # Retarded tau_opt: use last recorded tau from prior ghost_history
    gh_prev = getattr(mu, 'ghost_history', None) or []
    gh4_prev = [h for h in gh_prev if len(h) == 4]
    tau_opt_prev = int(gh4_prev[-1][3]) if gh4_prev else 1

    # Run EXP-316 recursive (gets S_A, S_C, ghost_history with tau_opt)
    mu_next, total_cost, K_weights = apply_gamma_316_recursive(
        mu=mu,
        claim_id=claim_id,
        partition_key=partition_key,
        beta=beta,
        budget=budget,
        spent=spent,
        K_budget=K_budget,
        depth=depth,
        focal_point=focal_point,
        B=B,
        beta_Z=beta_Z,
        J_AC=J_AC,
        W_max=W_max,
        thresholds=thresholds,
        alpha_leak=alpha_leak,
        beta_CA=beta_CA,
        mass_ref=mass_ref,
        kappa_ref=kappa_ref,
        y_ref=y_ref,
    )

    # Final tau_opt from completed run
    gh_final = getattr(mu_next, 'ghost_history', None) or []
    gh4_final = [h for h in gh_final if len(h) == 4]
    tau_opt_final = int(gh4_final[-1][3]) if gh4_final else 1

    # Compute G_inject_D using root stalk and final tau_opt
    Z_root = mu.claims[claim_id].stalk if claim_id in mu.claims else mu_next.Z()
    mass_norm_root = float(np.linalg.norm(Z_root[0:4]))
    kappa_root_val = float(Z_root[11]) if len(Z_root) > 11 else 0.0

    _G_C, _G_A, G_D = _g_inject_401(
        mass_norm=mass_norm_root,
        kappa_val=kappa_root_val,
        alpha_leak=alpha_leak,
        beta_CA=beta_CA,
        mass_ref=mass_ref,
        kappa_ref=kappa_ref,
        Z_before=Z_root,
        y_ref=y_ref,
        B=B,
        tau_opt=tau_opt_final,
        W_max=W_max,
        alpha_D=alpha_D,
    )

    # EMA update for S_D
    s_d_init = mu.S_D if (hasattr(mu, 'S_D') and mu.S_D is not None) else np.zeros(6)
    alpha_ema = float(mu_next.alpha)
    s_d_new = alpha_ema * s_d_init + (1.0 - alpha_ema) * G_D
    if hasattr(mu_next, '_replace_S_D'):
        mu_next = mu_next._replace_S_D(s_d_new)
    else:
        mu_next.S_D = s_d_new

    return mu_next, total_cost, K_weights


# ===========================================================================
# EXP-402 -- Ghost-Zeeman Homeostasis (Dual Pullback Feedback)
# Operator Phi_fb: (S_A_prev, Z_A_prev, S_D_prev) -> beta_Z_eff
# Inserted between Z-computation and B_tau (Zeeman weight step).
# B_A = norm(S_A) / (norm(Z_A) + eps)    [precession ghost ratio]
# B_D = norm(S_D) / (norm(Z_A) + eps)    [covariance ghost ratio, Z_A denominator]
# beta_Z_eff = max(beta_Z_min, beta_Z_base * (1 + gamma_fb_A*B_A - gamma_fb_D*B_D))
# Equilibrium: B_A* = B_D* when gamma_fb_A == gamma_fb_D
# Ghost #10 prevention: Z_D=0 in all children => B_D uses norm(Z_A) not norm(Z_D)
# Declaration hash: d933ad3ba860b601137cf7159b2485b2e86e1fc12b8939bce9bc1a08c3678407
# ===========================================================================

_GAMMA_FB_A_402 = 0.5
_GAMMA_FB_D_402 = 0.5
_BETA_Z_MIN_402 = 0.5
_EPS_FB_402     = 1e-15


def phi_fb(S_A, Z_A, S_D,
           beta_Z_base=_BETA_Z_313,
           gamma_fb_A=_GAMMA_FB_A_402,
           gamma_fb_D=_GAMMA_FB_D_402,
           beta_Z_min=_BETA_Z_MIN_402,
           eps=_EPS_FB_402):
    """
    Phi_fb: Ghost-Zeeman homeostasis operator.

    Declared I/O: (S_A_prev, Z_A_prev, S_D_prev, params) -> beta_Z_eff (scalar).
    Stateless. Does not write to Z_t, stalk, or S_A/S_D.

    B_A = norm(S_A) / (norm(Z_A) + eps)
    B_D = norm(S_D) / (norm(Z_A) + eps)   [Z_A denominator: Ghost #10 prevention]
    beta_Z_eff = max(beta_Z_min, beta_Z_base * (1 + gamma_fb_A*B_A - gamma_fb_D*B_D))

    P_yz invariance: B_A and B_D are norms => P_yz-invariant => beta_Z_eff P_yz-invariant.
    Stability: gamma_fb_A in (0, 2.0) with beta_Z_base=2.0 (inherited EXP-317 gate spec).
    Equilibrium: B_A* = B_D* when gamma_fb_A == gamma_fb_D.
    """
    S_A_arr = np.asarray(S_A, dtype=float)
    Z_A_arr = np.asarray(Z_A, dtype=float)
    S_D_arr = np.asarray(S_D, dtype=float) if S_D is not None else np.zeros(6)

    norm_Z_A = float(np.linalg.norm(Z_A_arr))
    B_A = float(np.linalg.norm(S_A_arr)) / (norm_Z_A + eps)
    B_D = float(np.linalg.norm(S_D_arr)) / (norm_Z_A + eps)

    beta_raw = float(beta_Z_base) * (1.0 + float(gamma_fb_A) * B_A - float(gamma_fb_D) * B_D)
    return float(max(float(beta_Z_min), beta_raw)), B_A, B_D


def apply_gamma_402_recursive(
    mu,
    claim_id,
    partition_key,
    beta,
    budget,
    spent,
    K_budget,
    depth=0,
    focal_point=None,
    B=None,
    beta_Z_base=_BETA_Z_313,
    J_AC=None,
    W_max=_W_MAX_314,
    thresholds=None,
    alpha_leak=_ALPHA_LEAK_311,
    beta_CA=_BETA_CA_311,
    mass_ref=_MASS_REF_311,
    kappa_ref=_KAPPA_REF_311,
    y_ref=_Y_REF_316_,
    alpha_D=_ALPHA_D_401,
    gamma_fb_A=_GAMMA_FB_A_402,
    gamma_fb_D=_GAMMA_FB_D_402,
    beta_Z_min=_BETA_Z_MIN_402,
):
    """
    EXP-402 recursive operator.

    Inherits all EXP-401 properties (d=18, S_D, log-Cholesky, Sigma_mir=R*Sigma*R^T).
    Prepends Phi_fb: computes beta_Z_eff from prior mu's S_A, Z_A, S_D before
    passing to apply_gamma_401_recursive.

    Pipeline position: Phi_fb between Z-read and B_tau (Zeeman weights).
    Declared I/O: (S_A_prev, Z_A_prev, S_D_prev) -> beta_Z_eff (scalar).

    Returns: (final_mu, total_cost, K_weights_step0, beta_Z_eff, B_A, B_D)
    """
    if B is None:
        B = np.array([1.0, 0.0, 0.0])

    # Phi_fb: read prior state BEFORE any partition
    S_A_prev = mu.S_A if (hasattr(mu, 'S_A') and mu.S_A is not None) else np.zeros(8)
    S_D_prev = mu.S_D if (hasattr(mu, 'S_D') and mu.S_D is not None) else np.zeros(6)
    Z_prev   = mu.Z()
    Z_A_prev = Z_prev[0:4] if len(Z_prev) >= 4 else np.zeros(4)

    beta_Z_eff, B_A, B_D = phi_fb(
        S_A=S_A_prev,
        Z_A=Z_A_prev,
        S_D=S_D_prev,
        beta_Z_base=beta_Z_base,
        gamma_fb_A=gamma_fb_A,
        gamma_fb_D=gamma_fb_D,
        beta_Z_min=beta_Z_min,
    )

    # Delegate to apply_gamma_401_recursive with effective beta_Z
    mu_next, total_cost, K_weights = apply_gamma_401_recursive(
        mu=mu,
        claim_id=claim_id,
        partition_key=partition_key,
        beta=beta,
        budget=budget,
        spent=spent,
        K_budget=K_budget,
        depth=depth,
        focal_point=focal_point,
        B=B,
        beta_Z=beta_Z_eff,
        J_AC=J_AC,
        W_max=W_max,
        thresholds=thresholds,
        alpha_leak=alpha_leak,
        beta_CA=beta_CA,
        mass_ref=mass_ref,
        kappa_ref=kappa_ref,
        y_ref=y_ref,
        alpha_D=alpha_D,
    )

    # Store beta_Z_eff and B_A/B_D in ghost_history as 7-tuple for observability
    # Format: (norm_S_A, norm_S_C, Omega_AC, tau_opt, beta_Z_eff, B_A, B_D)
    gh = list(getattr(mu_next, 'ghost_history', None) or [])
    if gh and len(gh[-1]) == 4:
        last = gh[-1]
        gh[-1] = (last[0], last[1], last[2], last[3], beta_Z_eff, B_A, B_D)
        try:
            mu_next.ghost_history = gh
        except AttributeError:
            pass

    return mu_next, total_cost, K_weights, beta_Z_eff, B_A, B_D


# =============================================================================
# EXP-404 — Exponential Phi_fb (Saturation Resolution)
# Gate trigger: saturation_ratio > 0.5 (EXP-403 Fork A [10])
# beta_Z_eff_exp = max(beta_Z_min_exp, beta_Z_base * exp(gamma_A*B_A - gamma_D*B_D))
# Properties: always positive; fixed point at beta_Z_base; linearises to EXP-402 for |x|<<1
# Ghost #14: exp amplification with B_A>>B_D gives ~22x beta_Z vs base; monitor leaf_count.
# declaration_hash: e7447ec6a65022a25d426a8f0b796ef18292d6cf3f85047c2239b004d225e67c
# =============================================================================

_GAMMA_FB_A_404  = 0.5
_GAMMA_FB_D_404  = 0.5
_BETA_Z_MIN_404  = 0.1    # lower floor: exp always positive; 2x more headroom than linear
_EPS_FB_404      = 1e-15


def phi_fb_exp(S_A, Z_A, S_D,
               beta_Z_base=_BETA_Z_313,
               gamma_fb_A=_GAMMA_FB_A_404,
               gamma_fb_D=_GAMMA_FB_D_404,
               beta_Z_min=_BETA_Z_MIN_404,
               eps=_EPS_FB_404):
    """Exponential Ghost-Zeeman feedback operator (EXP-404).

    beta_Z_eff = max(beta_Z_min, beta_Z_base * exp(gamma_A * B_A - gamma_D * B_D))

    B_A = norm(S_A) / (norm(Z_A) + eps)   [precession ghost ratio]
    B_D = norm(S_D) / (norm(Z_A) + eps)   [covariance ghost ratio; Z_A denom]

    Fixed point: gamma_A * B_A == gamma_D * B_D -> beta_Z_eff == beta_Z_base.
    Linearisation: exp(x) ~ 1+x for |x|<<1 -> reduces to EXP-402 phi_fb.
    Saturation floor raised: exp floor at ln(beta_Z_base/beta_Z_min)=ln(20)~3.0
      vs linear floor at (1 - beta_Z_min/beta_Z_base)/gamma_D = 1.5/gamma_D.

    Ghost #14: with B_A>>B_D (scene-structural), exp(gamma_A*B_A) amplifies
    exponentially. B_A*=4.81 -> exp(0.5*4.81)=11.07 -> beta_Z_eff*~22.
    """
    import numpy as _np404
    import math as _math404
    S_A_arr = _np404.asarray(S_A, dtype=float)
    Z_A_arr = _np404.asarray(Z_A, dtype=float)
    S_D_arr = _np404.asarray(S_D, dtype=float) if S_D is not None else _np404.zeros(6)
    norm_Z_A = float(_np404.linalg.norm(Z_A_arr))
    B_A = float(_np404.linalg.norm(S_A_arr)) / (norm_Z_A + eps)
    B_D = float(_np404.linalg.norm(S_D_arr)) / (norm_Z_A + eps)
    exponent = float(gamma_fb_A) * B_A - float(gamma_fb_D) * B_D
    beta_raw  = float(beta_Z_base) * _math404.exp(exponent)
    return float(max(float(beta_Z_min), beta_raw)), B_A, B_D


def apply_gamma_404_recursive(mu, claim_id, partition_key, beta, budget, spent, K_budget,
        depth=0, focal_point=None, B=None, beta_Z_base=_BETA_Z_313, J_AC=None,
        W_max=_W_MAX_314, thresholds=None, alpha_leak=_ALPHA_LEAK_311, beta_CA=_BETA_CA_311,
        mass_ref=_MASS_REF_311, kappa_ref=_KAPPA_REF_311, y_ref=_Y_REF_316_,
        alpha_D=_ALPHA_D_401,
        gamma_fb_A=_GAMMA_FB_A_404, gamma_fb_D=_GAMMA_FB_D_404,
        beta_Z_min=_BETA_Z_MIN_404):
    """EXP-404: wrap apply_gamma_401_recursive with exponential Phi_fb.

    Operator pipeline position: Phi_fb_exp inserted between Z-read and Bτ.
    Reads (S_A_prev, Z_A_prev, S_D_prev) from mu BEFORE partition.
    Passes beta_Z_eff_exp to apply_gamma_401_recursive as beta_Z parameter.

    Returns: (mu_next, total_cost, K_weights, beta_Z_eff, B_A, B_D)
    """
    import numpy as _np404r
    # Phi_fb_exp: read prior state BEFORE partition
    S_A_prev = mu.S_A if (hasattr(mu, 'S_A') and mu.S_A is not None) else _np404r.zeros(8)
    S_D_prev = mu.S_D if (hasattr(mu, 'S_D') and mu.S_D is not None) else _np404r.zeros(6)
    Z_prev   = mu.Z()
    Z_A_prev = Z_prev[0:4] if len(Z_prev) >= 4 else _np404r.zeros(4)

    beta_Z_eff, B_A, B_D = phi_fb_exp(
        S_A=S_A_prev, Z_A=Z_A_prev, S_D=S_D_prev,
        beta_Z_base=beta_Z_base,
        gamma_fb_A=gamma_fb_A,
        gamma_fb_D=gamma_fb_D,
        beta_Z_min=beta_Z_min,
    )

    mu_next, total_cost, K_weights = apply_gamma_401_recursive(
        mu=mu, claim_id=claim_id,
        partition_key=partition_key, beta=beta,
        budget=budget, spent=spent, K_budget=K_budget,
        depth=depth, focal_point=focal_point, B=B,
        beta_Z=beta_Z_eff, J_AC=J_AC, W_max=W_max,
        thresholds=thresholds, alpha_leak=alpha_leak, beta_CA=beta_CA,
        mass_ref=mass_ref, kappa_ref=kappa_ref, y_ref=y_ref, alpha_D=alpha_D,
    )

    # Annotate ghost_history 4-tuple -> 7-tuple with (beta_Z_eff, B_A, B_D)
    gh = list(getattr(mu_next, 'ghost_history', None) or [])
    if gh and len(gh[-1]) == 4:
        last = gh[-1]
        gh[-1] = (last[0], last[1], last[2], last[3], beta_Z_eff, B_A, B_D)
        try:
            mu_next.ghost_history = gh
        except AttributeError:
            pass

    return mu_next, total_cost, K_weights, beta_Z_eff, B_A, B_D
