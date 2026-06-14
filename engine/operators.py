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
            f"K(parent)+c·log(N)={k_limit:.2f}"
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
