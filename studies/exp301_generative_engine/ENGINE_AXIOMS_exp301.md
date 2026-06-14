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
| Validity predicate | r(Matroid(μ_t)) == 1 | λ_min(L_F(μ_t)) > 0 | §3 |
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

## 3. Validity Predicate — Sheaf Laplacian (hardened)

**Submitted**: `r(Matroid(μ_t)) == 1`

**Failure mode of submitted form**: rank-1 matroid over V_t forces every pair of nodes
into the same circuit — all claims co-dependent. This rejects any DAG with independent
claim lineages. More fundamentally, matroid rank captures independence structure only;
it does not detect semantic inconsistency between claim contents.

**Hardened**:

    is_valid(μ_t)  iff  λ_min(L_F(μ_t)) > 0

where L_F = δᵀδ is the cellular sheaf Laplacian and δ is the coboundary operator:

    (δx)_e = F(u → v)(x_u) - x_v    for e = (u → v)

**Interpretation**:
- λ_min > 0 iff no non-trivial harmonic sections exist — no global inconsistency that
  appears locally consistent
- λ_min = 0 signals Pseudo-T contamination precisely: a claim satisfying all local
  predicates while globally underdetermined
- L_F is positive semi-definite by construction; λ_min < 0 is impossible

**Computation**: L_F is block-structured; λ_min via power iteration with deflation.
O(|E|·d²) per step for sparse DAGs.

**Invariant enforcement**: at each operator invocation, compute Δλ_min.
If Δλ_min < 0, operator returns ConsistencyError; state reverts to H_{t-1}.

**Connection to EXP-102 M3**: M3 ≈ mean closure size / N is a coarse bound on
entailment graph density. High M3 predicts large off-diagonal mass in L_F, predicting
small λ_min. The EXP-102 null finding (M3 does not predict detection rate) is consistent
with L_F being a more sensitive instrument — M3 aggregates what L_F resolves per-edge.

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
- validity_predicate_shift: changing sheaf Laplacian threshold post-first-operator

---

## 9. Commitment Chain

EXP-001 VALIDATED → EXP-002 REJECTED → EXP-003 REJECTED_CONDITIONAL →
EXP-004 INCONCLUSIVE → EXP-005 NOT_CONFIRMED → EXP-101 INCONCLUSIVE →
EXP-102 REJECTED (Series 200 terminus) →
**EXP-301 Generative Reality Engine (Series 300 genesis)**
