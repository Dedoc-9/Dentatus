# ENGINE_AXIOMS_exp603 — Agency Loop & Autonomous Reality Search

**Protocol:** exp603-v1 · **Series:** 600 · **Inherits:** exp602-v1
**Primary architect:** Daniel J. Dillberg — bigdilly95@gmail.com
**Declaration hash:** `fdb106028f99333e4673e4a134d841ddca3261be234094925e62483ca5489da2`
**Status:** open · **Gate source:** EXP-602 bit-stable verified addresses → iterate-to-stable agency
**Location:** `game/agency/loop.py` (decoupled game layer — never `engine/`)

---

## Axiom 1 — Iterate-to-Stable

An agent proposes Semantic Intent (L2), reads Ghost Observables (`B_ent` = manifold tension /
tectonic stress, `B_ent_spectral`, `λ₂`) and the Firewall (ε=0.8) from the L1 API, and searches
resolution space for the most-continuous admissible realization. The loop reaches the core ONLY
through `dentatus.api`; it never imports `engine.*` (clean-room guard enforced).

## Axiom 2 — Agency Hysteresis Latch (Ghost #33, lifts EXP-409)

```
discovery:    greedy-accept only stress-reducing proposals  ->  monotone-non-increasing trajectory
maintenance:  IRREVERSIBLE latch on convergence (k_stable non-improving probes) OR ladder exhaustion,
              gated by  monotone(B_ent) AND monotone(B_ent_spectral) AND firewall-admitted
commit:       H_verified issued ONLY in the latched, admitted state   ("the teeth of truth")
```

This bounds the outer-loop backreaction: stress never increases on the committed path (no
oscillation), iterations are capped, and the verified address is withheld until stress settles.

## Axiom 3 — Witnessed Audit Trail

Every iteration — including rejected probes — is emitted as an executable-epistemics Witness
Artifact (`witness_core`, cross-project bridge). `data` carries pure numerics + structural
addresses only; the firewall verdict and the latch decision are NOT in `data` (observable
purity). `H_verified` appears only in the single terminal commit artifact. The trail is a
verifiable record of the agency's traversal of the manifold.

## Axiom 4 — Results (first Autonomous Reality Search)

Docking-bay prompt, budget ladder `[1024,2048,512,256,128,64]`, k_stable=3:

```
tectonic-stress (B_ent) trajectory:  0.1700 -> 0.1394 -> 0.0574   (67% reduction)
probes: 6 (4 witnessed rejects + 2 accepts) + 1 commit artifact = 7
committed:  budget 128, 8 leaves, λ₂=2.0, firewall-admitted
H_verified: bit-perfect across 3 separate processes (PYTHONHASHSEED=0)
```

Fork A 10/10, Fork B 5/5 (agency outcome P_yz-invariant: trajectory, address, latch all match).

## Ghost Notes

**Ghost #33 — Outer-loop backreaction (resolved):** the Agency Latch (Axiom 2).

**Ghost #34 — Sector D stress is realization-inert:** Sector D (shear/stress) is dual-only (not
partition-inherited), so semantic stress intent does not shape realized geometry; `B_ent_spectral`
≈ 0 for symmetric single worlds. The operative, realizable tectonic-stress signal is `B_ent`; the
realizable search variable is resolution budget. (A future study could make Sector D shape the
partition so "high shear" realizes as geometry — a genuine engine extension.)

**Ghost #35 — Agency Attraktorwahl:** greedy descent + early latch can commit a LOCAL stress
minimum (EXP-409 Ghost #19 at the agency layer). Mitigation: full-ladder exploration + exhaustion
latch commits the global best found; `k_stable` tunes explore-vs-commit.

## Scope

`game/agency/` + `game/examples/autonomous_reality_search.py` + Fork A/B. No engine change; no
dentatus.* change. Requires `PYTHONHASHSEED=0` for bit-perfect committed `H_verified`.
