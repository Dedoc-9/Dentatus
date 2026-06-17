# ENGINE AXIOMS — EXP-301 Generative Reality Engine (Series 300)

**Preregistration status**: GATE LOCKED — commit this file before Seed_0 declaration.
**Protocol version**: exp301-v1
**Workspace**: Reality_Engine/
**Commitment chain**: EXP-102 REJECTED (Series 200 terminus) → EXP-301 (Series 300 genesis)

---

## 0. Hardening notes (deviations from submitted specification)

Three components of the submitted specification required formal hardening.
One structural addition is proposed as the pioneering extension.
All deviations recorded here before lock.

| component | submitted | hardened | reason |
|-----------|-----------|----------|--------|
| Validity predicate | r(Matroid(μ_t)) == 1 | forward entailment consistency (E-301-003) | §3 |
| Φ conservation | "preserves information density" | K-bound §2.1 | underspecified |
| Ψ compatibility | "Galois closures non-intersecting" | r(M_A ∨ M_B) = r(M_A) + r(M_B) | §2.2 |
| [NEW] Path structure | single-path DAG | 2-categorical confluence | §5 |

---

## 1. Primary State Variable μ_t

μ_t is a cellular sheaf (G_t, F_t):

**Graph structure**: G_t = (V_t, E_t) directed acyclic graph.

**Node structure** — each v ∈ V_t:

    Claim(v) = {
        id:         HASH(provenance_v ⊕ payload_v ⊕ t ⊕ protocol_version),
        provenance: {parent_ids, operator_id, timestamp},
        payload:    symbolic content (string | structure | artifact ref),
        K_bound:    upper bound on Kolmogorov complexity K(payload_v),
        stalk:      F(v) ∈ ℝ^{d_v}
    }

**Edge structure** — each e = (u → v) ∈ E_t:

    Entailment(e) = {
        type:           PARTITION | SYNTHESIS | DEPENDENCY,
        restriction:    F(u → v): F(u) → F(v),
        predicate_hash: HASH(predicate licensing the entailment)
    }

**State identity**:

    H_t = HASH(V_t_sorted ⊕ E_t_sorted ⊕ Z_t ⊕ S_t ⊕ W_t ⊕ protocol_version)

H_t is immutable once written. Transition H_{t-1} → H_t requires explicit operator invocation.
No hidden state mutation outside declared pipeline.

**Active claim set** W_t ⊆ V_t: nodes with out-degree 0 (unspent leaves).
G_t is append-only; spent nodes are archived, not removed.

---

## 2. Construction Operators

Pipeline:

    μ_t → [Φ | Ψ] → Z_{t+1} → S_{t+1} → W_{t+1} → [Ω?] → OBS

Each operator is stateless, depends only on declared inputs, produces declared outputs.
No cross-stage mutation.

### 2.1 Φ (Partition)

**Signature**: `Φ(v, N, partition_key) → {v_1, ..., v_N} | PartitionError`

**Preconditions**:
- v ∈ W_t
- N ≥ 2
- partition_key preregistered or hash-committed before invocation

**Conservation law**:

    Orthogonality:  ∀ i ≠ j: F(v_i) · F(v_j) = 0  (stalk space)
    K-bound:        Σᵢ K(payload_{v_i}) ≤ K(payload_v) + c·log(N)
                    c = 150 (zlib-adjusted; E-301-002)
                    K ≈ len(zlib.compress(payload, level=9))
    Note: c=2 is correct for theoretical Kolmogorov complexity. zlib
    incurs ~12 bytes per-stream overhead absent from theory. c=150
    accounts for overhead, sub-string compression loss, and elaborative
    expansion. Empirical floor: c >= 100 for typical English payloads.

Violation → PartitionError(INFORMATION_OVERFLOW).

**Post-condition**: Σᵢ stalk(v_i) = stalk(v)

### 2.2 Ψ (Synthesis)

**Signature**: `Ψ(v_1, ..., v_k, synthesis_key) → v_new | SynthesisError`

**Preconditions**:
- ∀ i: v_i ∈ W_t
- synthesis_key preregistered
- Matroid independence (hardened):

      r(M_{v_1} ∨ ... ∨ M_{v_k}) = Σᵢ r(M_{v_i})

  M_{v_i} = claim matroid induced by v_i's subtree; ∨ = matroid union.
  This is the exact algebraic form of "Galois closures non-intersecting" — precise and computable.

**Stalk update**: stalk(v_new) = Σᵢ α_i · F(v_i → v_new)(stalk(v_i))
where α_i are declared synthesis weights (default: 1/k).

### 2.3 Ω (Observation — terminal)

**Signature**: `Ω(v) → Artifact | ObservationError`

**Preconditions**:
- v ∈ W_t
- is_valid(μ_t) == True (§3)
- Confluence certificate issued (§5)

**Artifact**:

    {
        claim_id:        v.id,
        payload:         v.payload,
        merkle_path:     [H_0, H_1, ..., H_t],
        confluence_cert: cert_hash,
        state_hash:      H_t
    }

v marked OBSERVED, removed from W_t.

---

## 3. Validity Predicate — Forward Entailment Consistency (E-301-003 corrected)

**Submitted**: `r(Matroid(μ_t)) == 1`

**First hardening (superseded by E-301-003)**: `λ_min(L_F(μ_t)) > 0`

**Failure mode of λ_min > 0**: For any connected consistent sheaf on a DAG, the
sheaf Laplacian L_F = δᵀδ has λ_min = 0 by construction. The zero mode corresponds
to the constant global section (all nodes have the same value under restriction maps) —
precisely the valid case. Strict positivity would block every valid connected state.
λ_min > 0 is the correct predicate for detecting inconsistency in UNDIRECTED sheaves
where all paths must close; for a directed acyclic graph it is never achievable.

**Corrected (E-301-003)**:

    is_valid(μ_t)  iff  for each target v ∈ V_t:
      ||Σᵢ F(uᵢ → v)(stalk_{uᵢ}) - stalk_v|| < ε

where the sum is over all edges (uᵢ → v) entering v.
- Single-source edge (PARTITION): F(parent → child)(stalk_parent) ≈ stalk_child
- Multi-source edges (SYNTHESIS): Σᵢ F(childᵢ → new)(stalk_i) ≈ stalk_new

**Interpretation**: each claim's stalk must be exactly derivable from its construction
history under the declared restriction maps. Violation = stalk corrupted externally,
restriction maps mis-calibrated, or state rolled back incorrectly.

**Restriction maps (corrected simultaneously)**:
- Φ: `F(parent → child_i) = outer(stalk_i, stalk_parent) / ||stalk_parent||²`
  Satisfies `F(stalk_parent) = stalk_i` exactly by construction.
- Ψ: `F(child_i → new) = αᵢ · I`
  Satisfies `Σᵢ αᵢ · stalk_i = stalk_new` by construction.
- Both: degenerate case (zero stalk) → zero matrix restriction.

**Invariant enforcement**: after each operator, check is_valid(new_state).
If False, operator returns ConsistencyError; state reverts to H_{t-1}.

**λ_min retained as observable**: λ_min(L_F) is computed and logged as a numeric
metric. It is PSD-clamped (max(λ, 0)) and reported alongside B(t), ESS, η_CLT.
It does NOT gate operator execution.

**Connection to EXP-102 M3**: The validity correction does not affect M3 linkage.
Forward consistency is a per-edge predicate; M3 aggregates claim closure density.
High M3 → dense restriction map matrix → forward consistency violations are
detectable before the state space collapses (earlier warning signal than M3).

---

## 4. Dual Arithmetic — Ghost Channel and Backreaction

### 4.1 State vectors

**Primary space** Z_t ∈ ℝ^D: concatenation of active claim stalks
    Z_t = [stalk(v_1), ..., stalk(v_k)],    v_i ∈ W_t

**Active claim basis** W_t ⊆ ℝ^D: column space of active stalk matrix

**Ghost residual**:
    G_t = Z_t − Π_{W_t}(Z_t)

G_t = component of primary state not representable in current active basis.

**EMA accumulation**:
    S_{t+1} = α·S_t + (1−α)·G_t        α ∈ (0,1), default α = 0.85

G_t has no direct control pathway (protocol constraint).

### 4.2 Observables (pure numeric — no interpretation attached)

    B(t)  = ||S_t|| / (||Z_t|| + ε)
    ESS   = (Σ wᵢ)² / Σ wᵢ²
    η_CLT = √|W_t| · (μ̂_stalk − μ_stalk)

### 4.3 Gravitational Backreaction

**Operator cost**:
    C(Op, t) = C₀(Op) · exp(β · ||S_t||)

    C₀(Φ) = 1.0
    C₀(Ψ) = k    (k = number of inputs to Ψ)
    C₀(Ω) = 0.0  (observation is free)
    β = backreaction coefficient (preregistered in Seed_0)

**Budget constraint** (preregistered):
    Σ_{t=0}^{T} C(Op_t, t) ≤ B₀

Trajectory exceeding B₀ → PRUNED.

**Mechanical effect**: high ||S_t|| makes Ψ exponentially expensive, preventing
runaway abstraction. System forced to observe (Ω, cost=0) or re-partition (Φ expands
|W_t|, increasing Π_{W_t} coverage, reducing G_{t+1}).

**Equations of motion**:
    Z_{t+1} = F_Op(Z_t)
    G_{t+1} = Z_{t+1} − Π_{W_{t+1}}(Z_{t+1})
    S_{t+1} = α·S_t + (1−α)·G_{t+1}
    H_{t+1} = HASH(Z_{t+1} ⊕ S_{t+1} ⊕ W_{t+1} ⊕ protocol_version)

Dual space (S, G) and primary space (Z) never algebraically collapsed.
Orthogonality enforced: ∀t, S_t ⊥ W_t by construction.

---

## 5. Pioneering Extension — 2-Categorical Confluence

### 5.1 Motivation

The submitted spec defines a DAG where each claim is reached by a single construction
path from Seed_0. In a generative system, multiple valid paths may produce the same claim:

    Φ(Ψ(A,B), 2, key₁)  ≅  Ψ(Φ(A, 2, key₂), Φ(B, 2, key₃))

Without tracking path equivalences, Ω cannot certify that an artifact is
construction-path-independent — a necessary condition for a claim to constitute
"reality" rather than "one construction history."

### 5.2 2-Category structure

C is a 2-category where:
- **Objects** (0-cells): claim states μ_t
- **1-morphisms**: construction paths P: μ_s →* μ_t (operator sequences)
- **2-morphisms**: certified equalities α: P₁ ⇒ P₂

### 5.3 Confluence predicate

    is_confluent(μ_t) iff ∀ P₁, P₂ from Seed_0 to μ_t: ∃ α: P₁ ⇒ P₂

Global confluence by Newman's lemma: local confluence + termination → global confluence.
Termination guaranteed by budget constraint B₀ (§4.3).

### 5.4 Coherence defect in dual channel

Each unresolved convergence (two paths reaching same node without registered 2-morphism)
contributes to G_t:

    G_t^(path) = stalk(P₁(v)) − stalk(P₂(v))    for unresolved convergences

Accumulates in S_t. ||S_t|| spike at a junction = "phantom duplicate" — hidden
ambiguity in the claim network. S_t encodes both structural entropy (§4.1) and
path coherence defect. Both are additive in the EMA.

**Confluence certificate** (required by Ω):
    cert = HASH("confluent" ⊕ v.id)    if no unresolved convergences in v's subtree

Ω returns ObservationError if cert cannot be issued.

### 5.5 Preregistered interchange laws (2-morphisms)

    [R1]  Φ(Ψ(A, B), 2, key₁) ≅ Ψ(Φ(A, 2, key₂), Φ(B, 2, key₃))
          iff key₁ compatible with (key₂, key₃) under declared partition schema

    [R2]  Ψ(Φ(A, N, key), N, key') ≅ A
          iff key' is the declared inverse synthesis for key

    [R3]  Ω(Ψ(A, B)) ≅ Ω(A) ⊗ Ω(B)
          iff A and B satisfy matroid independence (§2.2)

Post-execution rule addition is forbidden.

---

## 6. Protocol Pipeline (full)

    μ_t → [Φ | Ψ] → Z_{t+1} → G_{t+1} → S_{t+1} → W_{t+1} → [confluence_check] → [Ω?] → OBS

Stages:
1. Operator application (Φ or Ψ): updates V_t, E_t, W_t
2. Z update: recompute from new W_t stalks
3. Ghost: G_{t+1} = Z_{t+1} − Π_{W_{t+1}}(Z_{t+1})
4. EMA: S_{t+1} = α·S_t + (1−α)·G_{t+1}
5. Basis: W_{t+1} = column space of active stalk matrix
6. Confluence check: verify no unresolved 2-morphism residuals in W_{t+1}
7. Hash commit: H_{t+1} = HASH(Z_{t+1} ⊕ S_{t+1} ⊕ W_{t+1} ⊕ protocol_version)
8. Ω (if terminal): Artifact with Merkle path + confluence cert

Stateless stages. No hidden coupling. No cross-stage mutation outside declared mappings.

---

## 7. Seed_0 Declaration Requirements

SEED_DECLARATION_exp301.json must specify before first execution:

| parameter | description |
|-----------|-------------|
| seed_payload | initial claim payload / axiom set |
| seed_stalk | F(Seed_0) ∈ ℝ^d |
| d | stalk dimension |
| α | EMA coefficient |
| β | backreaction coefficient |
| B₀ | operator cost budget |
| partition_schema | declared keys for Φ |
| synthesis_schema | declared keys for Ψ |
| rewrite_rules | preregistered interchange laws |
| protocol_version | exp301-v1 |
| declaration_hash | SHA-256(json(above fields, sorted)) |

declaration_hash committed before any operator invocation.

---

## 8. Forbidden Procedures

- post_hoc_rewrite_rule_addition: interchange laws added after any operator has run
- ghost_direct_control: using G_t to select next operator
- stalk_collapse: merging Z and S into single representation
- retroactive_confluence_cert: certifying after Ω called
- budget_retroactive_adjustment: changing B₀ after Seed_0 committed
- validity_predicate_shift: changing the forward consistency tolerance ε post-first-operator

---

## 9. Commitment Chain

EXP-001 VALIDATED → EXP-002 REJECTED → EXP-003 REJECTED_CONDITIONAL →
EXP-004 INCONCLUSIVE → EXP-005 NOT_CONFIRMED → EXP-101 INCONCLUSIVE →
EXP-102 REJECTED (Series 200 terminus) →
**EXP-301 Generative Reality Engine (Series 300 genesis)**
