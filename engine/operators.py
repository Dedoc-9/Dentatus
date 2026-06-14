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
):
    """
    EXP-312 non-lossless Gamma operator.

    Reimplements the partition kernel with two P_yz fixes:
      Fix 1: payloads must be generated by _bbox_hash_payload_312 (caller responsibility)
      Fix 2: _stalk_A_decompose_312 for Sector A children (N > d_A case)

    Then applies EXP-311 G_inject EMA (identical to apply_gamma_311):
      G_inject_C[3] = alpha_leak * (||Z_before[0:4]|| / mass_ref)   [A->C]
      G_inject_A[7] = alpha_leak * beta_CA * (Z_before[11] / kappa_ref)  [C->A, weaker]

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

        child_stalk = _np.empty(d)
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
