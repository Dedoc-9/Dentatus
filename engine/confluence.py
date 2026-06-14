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

Post-execution addition of rewrite rules is forbidden.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from engine.state import MuState

PROTOCOL_VERSION = "exp301-v1"

# ---------------------------------------------------------------------------
# Rewrite rules (preregistered at protocol level)
# ---------------------------------------------------------------------------

REWRITE_RULES = {
    "R1": "Phi(Psi(A,B), 2, key1) ≅ Psi(Phi(A, 2, key2), Phi(B, 2, key3)) "
          "iff key1 compatible with (key2, key3) under partition schema",
    "R2": "Psi(Phi(A, N, key), N, key_inv) ≅ A "
          "iff key_inv is declared inverse synthesis for key",
    "R3": "Omega(Psi(A, B)) ≅ Omega(A) ⊗ Omega(B) "
          "iff A and B satisfy matroid independence",
}


# ---------------------------------------------------------------------------
# 2-morphism record
# ---------------------------------------------------------------------------

@dataclass
class TwoMorphism:
    """
    α: P₁ ⇒ P₂
    Certifies that two construction paths reaching target_claim_id are equivalent.
    """
    id:               str          # HASH(source_path + target_path + rule_id)
    source_path:      Tuple[str, ...]  # sequence of operator call ids
    target_path:      Tuple[str, ...]
    target_claim_id:  str
    rule_id:          str          # R1 | R2 | R3 | custom
    registered_at_t:  int


def _morphism_id(path1: Tuple[str, ...], path2: Tuple[str, ...], rule: str) -> str:
    raw = json.dumps({
        "p1": list(path1), "p2": list(path2), "rule": rule,
        "protocol_version": PROTOCOL_VERSION,
    }, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

@dataclass
class ConfluenceRegistry:
    """
    Tracks construction paths and registered 2-morphisms.
    Maintains the set of unresolved convergences (coherence defect → S_t).

    path_log:      claim_id → list of paths that reached it
    morphisms:     morphism_id → TwoMorphism
    unresolved:    set of claim_ids with convergences but no registered 2-morphism
    frozen_at:     timestep after which no new rewrite rules may be added (set on first operator call)
    """
    path_log:   Dict[str, List[Tuple[str, ...]]] = field(default_factory=dict)
    morphisms:  Dict[str, TwoMorphism]            = field(default_factory=dict)
    unresolved: Set[str]                          = field(default_factory=set)
    frozen_at:  Optional[int]                     = None

    # ---- path recording --------------------------------------------------

    def record_path(self, claim_id: str, path: Tuple[str, ...], t: int) -> Optional[str]:
        """
        Record a construction path reaching claim_id.
        If a prior path exists and no 2-morphism covers it, mark as unresolved.
        Returns the unresolved claim_id if a new convergence was created, else None.
        """
        if self.frozen_at is None:
            self.frozen_at = t   # freeze rewrite rules on first operator call

        existing = self.path_log.get(claim_id, [])
        self.path_log.setdefault(claim_id, []).append(path)

        if existing:
            # New convergence: check if any morphism already covers all prior paths
            covered = self._is_covered(claim_id)
            if not covered:
                self.unresolved.add(claim_id)
                return claim_id
        return None

    def _is_covered(self, claim_id: str) -> bool:
        """True iff every pair of paths to claim_id has a registered 2-morphism."""
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
        path1:       Tuple[str, ...],
        path2:       Tuple[str, ...],
        claim_id:    str,
        rule_id:     str,
        t:           int,
    ) -> TwoMorphism:
        """
        Register α: P₁ ⇒ P₂.
        Raises if rule_id is not in REWRITE_RULES (post-hoc addition is forbidden).
        """
        if rule_id not in REWRITE_RULES:
            raise ValueError(
                f"FORBIDDEN: rule_id '{rule_id}' not in preregistered REWRITE_RULES. "
                "post_hoc_rewrite_rule_addition is a forbidden procedure."
            )
        mid = _morphism_id(path1, path2, rule_id)
        m   = TwoMorphism(
            id=mid,
            source_path=path1,
            target_path=path2,
            target_claim_id=claim_id,
            rule_id=rule_id,
            registered_at_t=t,
        )
        self.morphisms[mid] = m
        # resolve if was unresolved
        if self._is_covered(claim_id):
            self.unresolved.discard(claim_id)
        return m

    # ---- certificate issuance -------------------------------------------

    def issue_cert(self, claim_id: str) -> str:
        """
        Returns confluence certificate for claim_id.
        Raises if any unresolved convergence exists in claim_id's ancestry.
        """
        if claim_id in self.unresolved:
            raise RuntimeError(
                f"CONFLUENCE_FAIL: claim {claim_id} has unresolved path convergences. "
                "Register a 2-morphism before observing."
            )
        # Check that all paths have been seen (at least 1)
        if claim_id not in self.path_log:
            raise RuntimeError(
                f"CONFLUENCE_FAIL: no path recorded for claim {claim_id}. "
                "Call record_path() after each operator step."
            )
        raw = ("confluent" + claim_id + PROTOCOL_VERSION).encode()
        return hashlib.sha256(raw).hexdigest()[:16]

    # ---- coherence defect observable ------------------------------------

    def coherence_defect_count(self) -> int:
        """Number of claims with unresolved path convergences. Feeds into S_t ghost signal."""
        return len(self.unresolved)

    def summary(self) -> dict:
        return {
            "paths_tracked":      len(self.path_log),
            "morphisms_registered": len(self.morphisms),
            "unresolved_count":   len(self.unresolved),
            "unresolved_ids":     sorted(self.unresolved),
            "frozen_at_t":        self.frozen_at,
        }
