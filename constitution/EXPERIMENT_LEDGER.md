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
entropic tax · `ξ` re-crystallisation (melt hysteresis) · `ρ`→`σ` merge-aware lineage · `τ` replay /
time-travel debugger · `υ`→`ψ` delta snapshots · `ω` checkpoint cadence · `φ` multi-leaf partial melt ·
`χ` self-healing intent queue.
