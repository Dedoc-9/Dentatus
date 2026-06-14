"""
confluence.py — 2-morphism registry and confluence certificate issuance.

2-Category structure (ENGINE_AXIOMS §5):
  Objects:      claim states μ_t
  1-morphisms:  construction paths P: μ_s →* μ_t  (operator sequences)
  2-morphisms:  α: P₁ ⇒ P₂  (certified path equivalences)

is_confluent(μ_t) iff all paths from Seed_0 to μ_t have registered 2-morphisms.
Confluence cert = HASH("confluent" ⊕ claim_id) if no unresolved convergences exist.

Preregistered interchange laws (ENGINE_AXIOMS §5.5):
  R1: Φ(Ψ(A,B), 2, key₁) ≅ Ψ(Φ(A, 2, key₂), Φ(B, 2, key₃))
  R2: Ψ(Φ(A, N, key), N, key') ≅ A  (round-trip identity)
  R3: Ω(Ψ(A, B)) ≅ Ω(A) ⊗ Ω(B)

E-301-004 extension: stalk-valued path-coherence residuals.
  declare_convergence(id1, s1, id2, s2): asserts id1 and id2 should be
    semantically equivalent but were constructed with different stalks.
    Unresolved → contributes to G_t via path_residual_sum().
    Resolved by register_morphism() for either id.
  path_residual_sum(): Σ_{unresolved pairs} (stalk1 − stalk2) ∈ ℝ^d.
    Added to base G_t in state.py so S_t accumulates even for lossless operators.

Post-execution addition of rewrite rules is forbidden.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

import numpy as np

PROTOCOL_VERSION = "exp301-v1"

# ---------------------------------------------------------------------------
# Rewrite rules (preregistered at protocol level)
# ---------------------------------------------------------------------------

REWRITE_RULES = {
    "R1": "Phi(Psi(A,B), 2, key1) ~= Psi(Phi(A, 2, key2), Phi(B, 2, key3)) "
          "iff key1 compatible with (key2, key3) under partition schema",
    "R2": "Psi(Phi(A, N, key), N, key_inv) ~= A "
          "iff key_inv is declared inverse synthesis for key",
    "R3": "Omega(Psi(A, B)) ~= Omega(A) x Omega(B) "
          "iff A and B satisfy matroid independence",
}


# ---------------------------------------------------------------------------
# 2-morphism record
# ---------------------------------------------------------------------------

@dataclass
class TwoMorphism:
    """
    alpha: P1 => P2
    Certifies that two construction paths reaching target_claim_id are equivalent.
    """
    id:               str
    source_path:      Tuple[str, ...]
    target_path:      Tuple[str, ...]
    target_claim_id:  str
    rule_id:          str          # R1 | R2 | R3
    registered_at_t:  int


def _morphism_id(path1: Tuple[str, ...], path2: Tuple[str, ...], rule: str) -> str:
    raw = json.dumps({
        "p1": list(path1), "p2": list(path2), "rule": rule,
        "protocol_version": PROTOCOL_VERSION,
    }, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Convergence record (E-301-004)
# ---------------------------------------------------------------------------

@dataclass
class ConvergenceRecord:
    """
    Stalk-valued path-coherence residual.
    Declares that id1 and id2 are semantically equivalent but have different stalks.
    residual = stalk1 − stalk2 ∈ ℝ^d.
    Enters G_t until a 2-morphism for id1 or id2 resolves this record.
    """
    id1:      str
    stalk1:   np.ndarray
    id2:      str
    stalk2:   np.ndarray
    resolved: bool = False

    @property
    def residual(self) -> np.ndarray:
        return self.stalk1 - self.stalk2

    @property
    def key(self) -> Tuple[str, str]:
        return tuple(sorted([self.id1, self.id2]))


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

@dataclass
class ConfluenceRegistry:
    """
    Tracks construction paths, registered 2-morphisms, and stalk-valued
    path-coherence residuals (E-301-004).

    path_log:          claim_id → list of paths that reached it
    morphisms:         morphism_id → TwoMorphism
    unresolved:        set of claim_ids with same-id convergences but no 2-morphism
    convergences:      key → ConvergenceRecord  (cross-id semantic equivalences)
    frozen_at:         timestep after which no new rewrite rules may be added
    """
    path_log:     Dict[str, List[Tuple[str, ...]]] = field(default_factory=dict)
    morphisms:    Dict[str, TwoMorphism]            = field(default_factory=dict)
    unresolved:   Set[str]                          = field(default_factory=set)
    convergences: Dict[Tuple[str,str], ConvergenceRecord] = field(default_factory=dict)
    frozen_at:    Optional[int]                     = None

    # ---- path recording --------------------------------------------------

    def record_path(self, claim_id: str, path: Tuple[str, ...], t: int) -> Optional[str]:
        """
        Record a construction path reaching claim_id.
        If a prior path exists and no 2-morphism covers it, mark as unresolved.
        Returns unresolved claim_id if new convergence created, else None.
        """
        if self.frozen_at is None:
            self.frozen_at = t
        existing = self.path_log.get(claim_id, [])
        self.path_log.setdefault(claim_id, []).append(path)
        if existing:
            if not self._is_covered(claim_id):
                self.unresolved.add(claim_id)
                return claim_id
        return None

    def _is_covered(self, claim_id: str) -> bool:
        paths = self.path_log.get(claim_id, [])
        if len(paths) <= 1:
            return True
        for m in self.morphisms.values():
            if m.target_claim_id == claim_id:
                return True
        return False

    # ---- 2-morphism registration -----------------------------------------

    def register_morphism(
        self,
        path1:    Tuple[str, ...],
        path2:    Tuple[str, ...],
        claim_id: str,
        rule_id:  str,
        t:        int,
    ) -> TwoMorphism:
        """
        Register alpha: P1 => P2.
        Raises if rule_id not in REWRITE_RULES (post-hoc addition forbidden).
        Auto-resolves any ConvergenceRecord involving claim_id.
        """
        if rule_id not in REWRITE_RULES:
            raise ValueError(
                f"FORBIDDEN: rule_id '{rule_id}' not in preregistered REWRITE_RULES. "
                "post_hoc_rewrite_rule_addition is a forbidden procedure."
            )
        mid = _morphism_id(path1, path2, rule_id)
        m   = TwoMorphism(
            id=mid, source_path=path1, target_path=path2,
            target_claim_id=claim_id, rule_id=rule_id, registered_at_t=t,
        )
        self.morphisms[mid] = m
        if self._is_covered(claim_id):
            self.unresolved.discard(claim_id)
        # E-301-004: resolve any convergence involving this claim_id
        for rec in self.convergences.values():
            if not rec.resolved and claim_id in (rec.id1, rec.id2):
                rec.resolved = True
        return m

    # ---- E-301-004: stalk-valued convergence declarations ----------------

    def declare_convergence(
        self,
        id1: str, stalk1: np.ndarray,
        id2: str, stalk2: np.ndarray,
    ) -> ConvergenceRecord:
        """
        Assert id1 and id2 should be semantically equivalent but were constructed
        via different paths with different stalks.

        Residual = stalk1 − stalk2 enters G_t via path_residual_sum() until resolved.
        Resolved by register_morphism() for either id.

        Raises if id1 == id2 (same claim cannot have a stalk-valued self-residual).
        """
        if id1 == id2:
            raise ValueError("declare_convergence: id1 == id2 (trivial convergence, no residual)")
        key = tuple(sorted([id1, id2]))
        rec = ConvergenceRecord(id1=id1, stalk1=np.array(stalk1, dtype=float),
                                id2=id2, stalk2=np.array(stalk2, dtype=float))
        self.convergences[key] = rec
        return rec

    def path_residual_sum(self, d: int = None) -> np.ndarray:
        """
        Σ_{unresolved ConvergenceRecords} (stalk1 − stalk2) ∈ ℝ^d.
        Returns zero vector (shape (d,) or (1,)) if no unresolved records exist.
        Used by G() in state.py.
        """
        result = None
        for rec in self.convergences.values():
            if not rec.resolved:
                diff = rec.residual
                result = diff.copy() if result is None else result + diff
        if result is None:
            return np.zeros(d if d is not None else 1)
        return result

    def unresolved_convergence_norm(self) -> float:
        """||path_residual_sum|| — scalar observable for convergence pressure."""
        total = None
        for rec in self.convergences.values():
            if not rec.resolved:
                diff = rec.residual
                total = diff.copy() if total is None else total + diff
        return float(np.linalg.norm(total)) if total is not None else 0.0

    def has_unresolved_convergence(self, claim_id: str) -> bool:
        """True iff claim_id is party to any unresolved ConvergenceRecord."""
        for rec in self.convergences.values():
            if not rec.resolved and claim_id in (rec.id1, rec.id2):
                return True
        return False

    # ---- certificate issuance -------------------------------------------

    def issue_cert(self, claim_id: str) -> str:
        """
        Returns confluence certificate for claim_id.
        Raises if:
          (a) claim_id has same-id unresolved path convergences, OR
          (b) claim_id is party to an unresolved stalk-valued ConvergenceRecord (E-301-004).
        """
        if claim_id in self.unresolved:
            raise RuntimeError(
                f"CONFLUENCE_FAIL: {claim_id} has unresolved same-id path convergences. "
                "Register a 2-morphism (R1/R2/R3) before observing."
            )
        if self.has_unresolved_convergence(claim_id):
            norm = self.unresolved_convergence_norm()
            raise RuntimeError(
                f"CONFLUENCE_FAIL: {claim_id} is party to an unresolved stalk-valued "
                f"convergence (E-301-004). ||residual||={norm:.4f}. "
                "Register a 2-morphism to resolve the path collision before observing."
            )
        if claim_id not in self.path_log:
            raise RuntimeError(
                f"CONFLUENCE_FAIL: no path recorded for {claim_id}. "
                "Call record_path() after each operator step."
            )
        raw = ("confluent" + claim_id + PROTOCOL_VERSION).encode()
        return hashlib.sha256(raw).hexdigest()[:16]

    # ---- observables -------------------------------------------------------

    def coherence_defect_count(self) -> int:
        """Number of claims with unresolved path convergences."""
        return len(self.unresolved) + sum(
            1 for rec in self.convergences.values() if not rec.resolved
        )

    def summary(self) -> dict:
        unresolved_conv = [
            f"{rec.id1[:8]}..{rec.id2[:8]}  ||res||={np.linalg.norm(rec.residual):.4f}"
            for rec in self.convergences.values() if not rec.resolved
        ]
        return {
            "paths_tracked":          len(self.path_log),
            "morphisms_registered":   len(self.morphisms),
            "unresolved_count":       len(self.unresolved),
            "unresolved_ids":         sorted(self.unresolved),
            "convergence_records":    len(self.convergences),
            "unresolved_convergences": unresolved_conv,
            "frozen_at_t":            self.frozen_at,
        }
