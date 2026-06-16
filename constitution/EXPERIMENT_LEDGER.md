# DENTATUS EXPERIMENT LEDGER
## The proof index — each law backed by a preregistered, hash-locked study

Every experiment is gate-locked before implementation by a `SEED_DECLARATION_*.json` whose
`declaration_hash` is verified at the top of its Fork-A runner. Each study ships **Fork A** (a
seed/determinism proof, 10 assertions) and **Fork B** (P_yz reflection invariance, 5 assertions).
Engine core frozen since EXP-509 (behaviour added only via additive `validity.py` predicates or the
game layer). `PYTHONHASHSEED=0` required for cross-process bit-stability.

## Series 500 — Manifold Integration

| EXP | Charter article | Result | Declaration hash | Greek fork |
|---|---|---|---|---|
| 502 | IV.F1 | Manifold Firewall `is_manifold_501` (ε=0.8); degree-normalized G_ent (Ghost #22) | `0979f7f520421a28` | — |
| 503 | VIII | Spectral manifold feedback `phi_fb_manifold`; bounded Ω_ent_sp (Ghost #25) | `16f3e47232a3a84e` | — |
| 504 | VI(memory) | Stateful Seed; temporal manifold smoothing; healing curve (Ghost #26/#27) | `93201baeac72aac9` | — |
| 505 | VI.4 | Moving claims; motion-compensated world frame; track-correspondence DAG (Ghost #28) | `6885720d383ca775` | — |
| 506 | VIII.2 | Stitched local Fiedler; Galerkin coarse + partition-of-unity; spectral-diameter halo | `d69b59b3ad635e16` | — |
| 507 | VIII.2 | Streaming world-sections; bounded resident set; content-addressed eviction | `2889884aa163e496` | — |
| 508 | IV.F2 | Citadel entropy firewall; Law of the Citadel ΔS_cit ≥ 0; dual-gate | `8a511d4360b4c040` | — |
| 509 | IV.F3 | Zeeman/Bethe Citadel; E*=β_Z, ρ=exp(2√(aE*)), a=a₀·d_stalk; opt-in gate (Ghost #43) | `58f3f306a8f48cbe` | — |
| 510 | VIII.3, IV | Multi-velocity section tracking; Cauchy split L=strain⊕vorticity (Ghost #40/#44) | `5f83cb5ac6b907e1` | — |
| 511 | VIII.3 | Strain-gated halo + mass-momentum smoothing (volume not count); shimmer −2.3× (Ghost #45) | `943feae7c1f52a4e` | δ-prep |
| 512 | IV.F4 | Strain→Bethe coupling; E*_eff=β_Z(1−(strain/ε_ref)²); a fixed (Ghost #46) | `dd86223ac4b68ff8` | ε |
| 513 | IV.F4 | Dimensionless strain; shear-Courant + Weissenberg (framerate-independent); ε_ref universal (Ghost #47) | `e283bd260e380617` | η |
| 514 | V | Epistemic Materialism; χ = continuous map of Sector D spectrum; stiff=fragile (Ghost #48) | `99eda360b4e85bd8` | θ |
| 515 | VI.2 | Enacted Phase Change; volume-preserving anisotropy-melt geodesic; minimal t* (Ghost #49) | `c238e89e21e18bb5` | λ |
| 516 | VI.4 | Transition Log → Provenance DAG; first-class Claim lineage; time-travel (Ghost #50) | `e028deae2adcaeb6` | ο |
| 517 | VI.3 | Live MuState Injection; continuous H_t; optimistic-concurrency Interference (Ghost #51) | `082b4a773bb23dfc` | ρ |
| 518 | VI.5 | History Compaction; H-inert + observationally-inert eviction; bounded memory (Ghost #52) | `32c1314a87fbd523` | υ |
| 519 | X | Unified Kinetic Dashboard; WebGL replay of bit-perfect telemetry; diamond→glass→fluid→firewall-holds | capture (deterministic) | — |
| 520 | VI.5, II.2 | Replay / Time-Travel Debugger; event-sourced command log + checkpoints; VERIFIED reconstruction (tamper-evident); cold restore (Ghost #53) | `2e489550a816e08e` | τ |
| 521 | VI.2, V | Re-crystallization / Annealing; distinct cooling threshold → true thermal hysteresis (χ–Wi loop, chatter-free); reverse anisotropy geodesic; closes Ghost #49 (opens #54) | `8f9fcf2b21b0ce97` | ξ |
| 522 | VI.2, V | Oriented Nucleation; amorphous state re-crystallises along the strain principal axis (det-preserving, aligned to flow); closes Ghost #54 | `851a4f654a262c2a` | ψ |
| 523 | II.3, VII | Validity Witness; binds the SPRT integrity class (FULL_VALID/LOD_RELAXED/INVALID) to the verified address; closes Ghost #5 (integrity laundering across LOD); backward-compatible | `1fc9721cf4e667cb` | ω |
| 524 | ALL | The Genesis Block — full-system walkthrough; one world through the entire constitution, self-verifying & deterministic (capstone / proof-of-life) | walkthrough | — |

## Series 600 — Developer Interface

| EXP | Charter article | Result | Declaration hash |
|---|---|---|---|
| 601 | II.2 | Deterministic seeding; `Claim.id` timestamp-excluded; bitwise `H_t` (Ghost #27 killed) | `f352e458d1e252f4` |
| 602 | II.2 | Bit-stable semantic compiler; `H_verified` = firewall-gated address; HASHSEED pin (Ghost #32) | `7753731c596ef389` |
| 603 | IX | Agency loop & autonomous reality search; Agency Hysteresis Latch (Ghost #33/#35) | `fdb106028f99333e` |
| 604 | X | MCL Observability dashboard; content-addressed telemetry; WebGL | `f1f9c1a4438c3c23` |
| 605 | X | Live SSE reality stream; keyframe+delta codec; bitrate ∝ change | `7e682b51a229f7e6` |
| 606 | VI.5(precedent) | LRU coarse cache; session H_coarse anchors; zero-cost returns (Ghost #41/#42) | `1bbbccefaec5ec17` |

## Open fork backlog (declared, not yet built)

`δ` anisotropic halo · `ι` per-section local Citadel · `μ` anisotropic χ tensor · `ν` cross-sector
entropic tax · `ξ` re-crysta
---

### EXP-528 · Rolling Nonce-Chaining (Fork ι)
- **Axiom:** Replay is a transport-layer exploit; it requires a transport-layer cryptographic fence *outside* the frozen core. The fence must not perturb engine determinism or the EXP-520 replay debugger.
- **Mechanism:** deterministic hash-ratchet `N_{t+1} = SHA256(N_t ∥ H_t ∥ seq ∥ pv)`, head bound into `session_attest` as an **optional** parameter via backward-compatible canonicalization (`nonce=None` ⇒ pre-528 bytes byte-identical). The nonce is PUBLIC and secret-free; the secret enters only the HMAC.
- **Replay immunity = two mechanisms, not one:** (a) the rolling head is bound into the signature, so a signature cannot be moved to another sequence position; (b) the verifier enforces a strictly-monotone accepted `seq`, so a re-sent *validly-signed* old frame is rejected as stale. (A stale frame's HMAC is still internally valid — it is rejected by ordering, not by signature failure.)
- **Verification:** `forge/nonce_proof.py` — 0 violations across 5 properties: (1) backward-compat; (2) replay-reproducibility (EXP-520 recovers every nonce bit-for-bit from the command log); (3) replay immunity; (4) forge resistance (wrong secret hard-rejects; substituted nonce rejects); (5) fork sensitivity (one divergent H forks all subsequent nonces, no reconvergence).
- **Wiring:** `Game1/dentatus_bridge.py` issues a nonce per commit, binds it into composite + attestation, logs `{seq,nonce}`. Collider/shear-rifle servers (no-nonce path) unaffected.
- **Status:** Sealed · Engine Core Frozen (37/83/13/29) · Verification 5/5.

---

### EXP-529 · Network Chaos-Injection Harness (Fork κ)
- **Axiom:** Robustness is proven by an adversary, not asserted. The committed timeline must be invariant to transport hostility.
- **Mechanism:** `forge/chaos_harness.py` — deterministic L1 reducer (tick-batched NET superposition → seal → EXP-528 nonce) under a seeded chaos transport: drop-cascade 30%, jitter-reorder, latency-spike past the rebase window.
- **Proven invariant:** the committed `H_verified` timeline is a pure function of the *accepted set* + server seq, independent of arrival order. Within a tick, resolution is net-superposition (order-free); across ticks, commit is by server seq; beyond the window, frames reject as `stale_basis` (never spliced).
- **Verification:** 5/5 — arrival-order invariance (jitter == canonical, bit-for-bit), chaos determinism, bounded-rebase rejection (stale deterministic), drop resilience, liveness (no lock). 0 violations.
- **Honest scope:** bounded-window order-invariance + deterministic stale-rejection — NOT zero-latency re-proof of deep history.
- **Status:** Sealed · Engine Core Frozen (37/83/13/29).

### EXP-530 · Automated Invariant Synthesis (Fork λ′)
- **Axiom:** A system that licenses its own constraints manufactures its own confirmations (Layer-0 violation). Mining may PROPOSE; only a human-licensed registry may enforce.
- **Separation of powers:** the forge mines candidates tagged by basis — **constitutional** (derivable: χ∈[0.05,1], Bethe frac∈[0,1], E*_eff≥0) vs **empirical** (sample-observed: dS_cit envelope). The registry `constitution/INVARIANT_REGISTRY.json` is a precommitment ledger; a candidate is enforced only when a human licenses its exact SHA-256 fingerprint with a declared `failure_condition`.
- **Hard safety rule:** empirical (finite-sample) bounds may be licensed ONLY as `monitor` (log/alert), NEVER as `hard` reverts — a sampled range is not a law.
- **L1 gate:** `active_clamps()` compiles a guard only if the entry's recomputed fingerprint matches the license (no silent drift) AND the engine code hash still matches (license voids on operator change).
- **Verification:** `forge/invariant_synthesis.py` — 7/7: mining-alone-inert, licensing-activates, empirical-can't-be-hard, no-failure-condition-refused, crypto-drift-void, engine-drift-void, deterministic fingerprints. 0 violations.
- **Status:** Sealed · registry seeded (3 hard constitutional + 1 empirical monitor) · Engine Core Frozen (37/83/13/29).

### EXP-530.L · Live L1 Gate (Active Server Defense)
- **Integration:** `active_clamps()` is loaded once at `World.__init__` and evaluated inside `do_call` (`POST /call`) AFTER the real operator runs and `chi1` is computed, but BEFORE the step is sealed or an `H_verified`/nonce is issued. Frozen `engine/` untouched; all gating lives in `Game1/dentatus_bridge.py`.
- **Fail-closed:** a HARD-clamp breach reverts `(stalk, wi)` to the pre-call snapshot, holds `last_valid_H`, logs a deterministic rejection, returns `REJECTED · property clamp violation`. Only the offending call is rejected — liveness preserved for the rest of the world. MONITOR breaches are logged, never reverted.
- **Replay continuity:** clamp validations are written to the command log; identical synced drives reproduce the cmdlog (H/composite/seq/nonce/clamps) bit-for-bit (EXP-520).
- **Verification:** `forge/bridge_gate_proof.py` 4/4; full forge suite (oracle_fuzz, nonce_proof, chaos_harness, invariant_synthesis, bridge_gate_proof) 0 violations. Engine Frozen (37/83/13/29); 0 engine imports.

### EXP-531 · Cryptographic Registry Signing (Boot Airlock)
- **Axiom:** Fingerprint self-consistency (EXP-530) proves a registry entry is INTERNALLY consistent, not that it was AUTHORIZED. A wholesale replacement with recomputed fingerprints would self-verify — authorization requires asymmetric attestation, not a hash the attacker can also compute.
- **Mechanism:** detached **Ed25519** (RFC 8032, deterministic) signature over the exact bytes of `INVARIANT_REGISTRY.json`, stored in `INVARIANT_REGISTRY.sig`. The server holds only PUBLIC keys (`AUTHORIZED_KEYS.json`); at boot it verifies the signature against that allowlist BEFORE compiling a clamp. Failure → `RegistryCryptographicBreach`, server refuses to start (fail-closed boot). Strict mode (`DENTATUS_REQUIRE_SIGNED_REGISTRY=1`) mandates a signature; otherwise a present-but-bad signature still fails closed, only an absent one is tolerated (dev).
- **Verification:** `forge/signature_proof.py` 7/7 — authorized boots; one-byte registry tamper, signature tamper, unauthorized signer, **wholesale-replace-and-re-sign**, missing-sig-strict, and present-but-bad-in-dev all fail closed. Live bridge boots through the airlock with the signed registry and REFUSES to boot on a tampered one.
- **Honest trust-root note (recorded, not buried):** signing relocates the trust root from "any writer of the registry file" to "a holder of a listed private key OR a writer of the public-key allowlist." Real narrowing, not absolute — the allowlist itself must be protected out-of-band (committed, read-only deploy, signed release). Private key is gitignored, never committed; the server needs only the public key.
- **Status:** Sealed · Engine Core Frozen (37/83/13/29) · full forge sweep (6 suites) 0 violations · requires `cryptography`.

### EXP-532 · Autonomous Simulation Lab & Profiler
- **Axiom:** Optimization without telemetry is a structural assumption; a next-gen kernel rewrite is prohibited until an empirical performance budget is breached.
- **Mechanism:** server-authoritative B policy (FSM: rebuild / advance / drill / assault) + a runtime tick profiler, both inside `collider_duel.py`. The bot enqueues like a human combatant (replay-safe).
- **Verification:** 300-tick continuous automated-combat benchmark — mean 2.9 ms · p50 2.8 ms · p95 4.9 ms · max 13.7 ms against the 100 ms (10 Hz) budget; sustainable ~73 Hz.
- **Strategic Verdict:** greenfield `engine_v2/` remains UN-LICENSED — ~7× safety margin at 48-tile scale. The profiler ships in every `/stream` frame (`tick_ms`) so the budget-breach moment is observable in play.
- **Balance finding:** at current tuning two equally-aggressive combatants stalemate (no breach in 300 ticks); the bot beats a passive opponent. Pacing/threshold tuning is a future pass, not a bug.

### EXP-533 · Hardware-Invariant Pulse (Determinism Seal)
- **Axiom:** No wall-clock value may enter a committed state transition; `H_verified` must re-derive bit-for-bit on any machine from the command log alone (EXP-520).
- **Vulnerability:** off-beat (non-synced) commits computed `beta_eff` from `self.pulse()` = `time.time()`, so the melt verdict carried a trace of host timing — replay on different hardware would drift and throw an illegitimate `ReplayMismatch`.
- **Correction:** committed pulse is now `_tick_pulse()` — a pure function of the integer frame (`frame/TICK_HZ`), never the clock. `synced` is server-confirmed against that deterministic pulse (also closes the always-claim-synced exploit). Each committed log entry records `tick_pulse` + `beta_eff`, so the replayer reads the value, not the clock. Display metronome stays wall-clock (cosmetic only).
- **Verification:** `forge/duel_determinism_proof.py` — identical scripted runs produce identical H-chains; the SAME run with random wall-clock sleeps injected produces a BIT-IDENTICAL H-chain (hardware-invariance); every commit logs its pulse/beta.
- **Status:** Sealed · Engine Core Frozen (37/83/13/29).

### Scaling Backlog · Hilbert spatial-spiral linearization (MEASURED · UN-LICENSED)
- **Status:** candidate EXP-507 scaling primitive. NOT sealed, NOT wired to the live game. Profiler (EXP-532) shows ~7x headroom at 48 tiles, so adopting this now would be premature optimization.
- **Measurement (`forge/hilbert_compress_proof.py`, 64x64 = 4096 leaves, representative coherent frame):**
  - **Block locality: 13x tighter** — avg 1-D index span of a 4x4 spatial block 195 (row-major) → 15 (Hilbert). This is the real, robust benefit: contiguous LRU eviction / cold-storage blocks (EXP-606/518) instead of fragmented leaves.
  - Compression: +5.2% gzip reduction, **data-dependent** — it can go negative on adversarial fields (e.g. column-alternating sign), so it is a minor perk, not a guarantee.
- **Correction of record:** an earlier draft claimed a 30.92% compression gain and a "cache discontinuity" metric. Both were wrong — the 30.92% does not reproduce (real ≈ +5% on a representative frame, ≈ −5% on the adversarial one the draft actually used), and the discontinuity metric measured row-scan locality (which row-major wins by construction), not the block locality Hilbert provides. Hardened script verifies the Hilbert order is a bijection with a correct inverse and measures block-span instead.
- **Adopt when:** the world scales to thousands of streamed leaves and the profiler bends — then linearize leaves by Hilbert index for section assignment, eviction order, and persistent command-log layout. Conceptual fit: the space-axis analogue of the EXP-528 nonce ratchet (the time-axis spiral).
