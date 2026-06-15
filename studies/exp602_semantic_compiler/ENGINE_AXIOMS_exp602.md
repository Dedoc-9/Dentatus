# ENGINE_AXIOMS_exp602 — Bit-Stable Semantic Compiler (realized-state H_verified)

**Protocol:** exp602-v1 · **Series:** 600 · **Inherits:** exp601-v1
**Primary architect:** Daniel J. Dillberg — bigdilly95@gmail.com
**Declaration hash:** `7753731c596ef389d92449092d15f94f38a1ba3f66cba237ba980a32190b6abd`
**Status:** open · **Gate source:** EXP-601 bitwise H_t → content-addressed reality store

---

## Axiom 1 — H_verified is the realized-state address

Before EXP-602 the API stamped `H_verified = declaration_hash` (the recipe). EXP-601 made the
engine bit-reproducible, so `H_verified` now hashes the REALIZED world:

```
H_state = SHA256(W (sorted ids) ⊕ Z (stalks) ⊕ S_A ⊕ S_C ⊕ S_D ⊕ protocol)   [12-decimal rounded]
H_verified = H_state   iff is_manifold_501(ε=0.8) passes   else None
```

Three distinct addresses: `H_decl` (recipe), `H_state` (realized world), `H_verified` (the
firewall-gated permanent reality id). Verified bit-stable across 3 runs; idempotent (same intent
→ same id, a content-store/dedup key); intent-sensitive; geometry-dependent (budget 2048→256
changed leaves 148→36 → different `H_state`).

## Axiom 2 — Firewall = handshake (your agreement, made literal)

A verified reality address is issued only when the manifold firewall admits the world. A torn
manifold returns observables but `H_verified = None`. The contract `(H_verified is None) ⇔
¬is_manifold_501` holds by construction.

## Axiom 3 — P_yz of the verification

The realized address hashes signed Z. Under the seed Sector-B x-stalk flip, leaf stalks are
geometry-derived (the seed x-stalk does not propagate), so the realized world — and `H_verified`
— is P_yz-INVARIANT (verified Fork B: `H_verified_fwd == H_verified_mir`). The firewall decision
and observables are P_yz-invariant at machine precision (`dB_ent = dλ₂ = 0.0`).

## Axiom 4 — Observable purity (executable-epistemics witness test)

EXP-602 output is cross-checked against the `executable-epistemics` witness instrument
(`witness_core`, same author). The L1 observables (`B_ent`, `λ₂`, `B_ent_spectral`, `worst_ratio`,
`H_state`, …) are pure numerics / structural indices and pass the witness **interpretive
firewall** (no verdict-shaped field in `data`). The firewall boolean `is_manifold_501` is an
interpretation, NOT an observable, and is therefore kept OUT of witness `data`; admissibility is
carried as the numeric bound `worst_ratio ≤ epsilon_manifold`. See
`studies/exp602_semantic_compiler/witness_bridge_exp602.py`. This is a cross-project test, not a
merge: neither project imports the other internally (Clean Room preserved).

## Ghost Notes

**Ghost #32 — Cross-process hash-seed nondeterminism (resolved by pin):** EXP-601 removed the
timestamp source, but `PYTHONHASHSEED` randomizes string set/dict iteration order, perturbing the
gamma-recursion `S_A` summation -> within-process `H_verified` is stable, but it varies ACROSS
processes. A content-addressed store therefore requires `PYTHONHASHSEED=0` (the same reproducible-
runtime discipline the witness toolkit uses with `SOURCE_DATE_EPOCH`). `dentatus_service.py`
self-pins it (re-exec); `determinism_crossproc.py` proves cross-process stability. Eliminating the
pin entirely would require sorting set/dict iterations in the recursion (deferred core change).

**Ghost #31 — Verdict leakage (guarded):** emitting the firewall boolean as an observable would
make the API output an interpretation. Resolution: `data` carries only numerics + structural
addresses; the verdict lives in `validity_scope.certifies` / the reader's threshold test. The
witness bridge demonstrates the firewall catches a naive `valid: True` leak.

## Scope

`dentatus/api.py` (`state_hash` + `H_verified` redefinition) and a witness bridge test. No engine
change. All Series 400/500/EXP-601 assertions remain valid.
