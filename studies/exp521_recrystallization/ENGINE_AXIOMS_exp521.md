# EXP-521 — Re-crystallization / Annealing (Fork ξ)

**Protocol** `exp521-v1` · **Declaration hash** `8f9fcf2b21b0ce974e0069b279e66ace9175fdc27acffde7aa3e7975bb449418`
**Scope** NO engine edits. `game/agency/recrystallize.py` uses `dentatus.core` (χ, bethe, cholesky) +
`dentatus.semantic`. Engine FROZEN. **Closes Ghost #49.**

---

## A1 — Closing the one-way ratchet

The EXP-515 melt raised compliance `χ` to survive shear but never lowered it again — a one-way entropy
ratchet. Re-crystallization adds the reverse leg: when stress subsides far enough, matter regains order
(`χ ↓`). The two legs use **distinct thresholds**, which is what makes the cycle a true thermodynamic
loop rather than a reversible line.

## A2 — Schmitt-trigger on the material state (the hysteresis)

```
melt   boundary : χ_required(Wi)                      (stress exceeds what the material bears  → melt, χ↑)
freeze boundary : χ_required(Wi) + hysteresis         (re-order only with this much headroom    → freeze, χ↓)
dead-zone       : χ_required < χ_cur < χ_required + hysteresis   → HOLD   (the material remembers)
```

Re-crystallization fires only when `χ_cur − χ_required ≥ hysteresis` (stress is a full margin below the
melt point), and cools only **down to** `χ_required + hysteresis` — staying a margin above the melt
boundary, so the freshly-frozen material cannot immediately re-melt. The dead-zone between the two
boundaries is the memory: inside it nothing changes (Fork A [2]). This is the same latch pattern as
EXP-409 (`β_threshold`) and the EXP-603 Agency Latch, applied to the material's order parameter.

**Chatter-free (the explicit Ghost #49 requirement).** Because freeze stops a margin above the melt
boundary, a material at fixed low stress converges and holds — verified: `χ` settles and the last steps
are bit-identical, no oscillation (Fork A [6]).

## A3 — Geometry: the reverse geodesic (dual math ↔ code)

Re-crystallization is the **reverse** of the melt geodesic on the SPD manifold — same eigenbasis,
det-preserving:

```
ℓ_i = ln λ_i(Σ);  ℓ̄ = mean(ℓ_i);   ℓ_i(g) = ℓ̄ + g·(ℓ_i − ℓ̄)
   g < 1 : melt   (shrink spread → isotropic → χ↑)        [EXP-515]
   g > 1 : freeze (widen  spread → ordered  → χ↓)         [EXP-521]
```

```python
ll = log(eigvals(Sigma)); lbar = ll.mean()
Sigma_g = (V * exp(lbar + g*(ll - lbar))) @ V.T        # g>1 amplifies residual anisotropy; det preserved
g* = bisect(g in [1, G_MAX] : chi(Sigma_g) ≤ chi_target)
```

The melt and freeze legs are one line in spectrum-space parameterised by `g ≥ 0` (`g=0` isotropic,
`g=1` current, `g>1` ordered); `χ(g)` is monotone decreasing. Verified: shear up → melt → `χ` tracks
`χ_required`; shear down → freeze → `χ` lags by exactly `hysteresis`; **loop area = 1.005** (Fork A [5]),
volume preserved (Fork A [9]), anneal-rate limited (Fork A [7]).

## A4 — P_yz & determinism

Re-crystallization acts on the covariance eigenvalue spectrum (P_yz-invariant), so `χ_after`, the
widening factor `g`, `det`, and the status are reflection-invariant (Fork B). Bit-stable (Fork A [10]).

## A5 — Composition with the lineage

A re-crystallization is a witnessed transition like a melt: its `new_stalk` injects via EXP-517
(`operator_id = "Recrystallize"`), appends a provenance edge (EXP-516), and is replayable (EXP-520).
The thermal cycle therefore writes both legs into the same auditable lineage — a world's material state
records its full thermal history, not merely its last melt.

---

## DEV NOTE — Ghost #54: the amorphous lock

Re-crystallization *amplifies the residual ordering* already present in the spectrum (`g > 1` widens the
existing spread). A **fully isotropic** state (`Σ ∝ I`, `χ = 1`, reached only by a *total* melt) has no
residual direction to amplify — every eigenvalue is equal, so the geodesic rescale is the identity. Such
a state is **amorphous-locked**: it cannot spontaneously re-crystallise and returns `amorphous_hold`
(Fork A [8]). Physically correct — a perfectly quenched glass has no nucleus.

The residual is the missing **orienting field**: to crystallise an amorphous state one must impose a
direction (e.g. the principal strain axis, dendrites aligning to the flow). Closing it is Fork ψ: seed
re-crystallisation along `Sym(L)`'s principal axis when the spectrum is degenerate. Until then, *minimal*
melts (which stop at `χ_required < 1` and always retain residual anisotropy) are always re-crystallisable;
only the *total*-melt limit locks.

## Suggested improvements / forks

- **Fork ψ (oriented nucleation).** Re-crystallise an amorphous state along the strain principal axis,
  closing Ghost #54 — gives the engine a "directional solidification" operator.
- **Fork ϡ (temperature-rate annealing).** Make the anneal rate a function of the cooling *rate*
  (fast quench → less order regained, more residual `χ`), reproducing quench-vs-anneal microstructure.
- **Fork Ϟ (hysteresis-loop observable).** Emit the enclosed `χ`–`Wi` loop area as a pure observable —
  the material's dissipated energy per cycle (mechanical hysteresis loss).

## Foreign-language note (rhetoric → code)

The reverse leg is *Rekristallisation* (re-crystallisation) / *Glühen* (annealing): *Ordnung*
(order) is regained by *Verbreiterung* (widening) of the *Eigenwertspektrum*, the reverse of the
melt's *Verschmälerung* (narrowing). The distinct *Abkühlschwelle* (cooling threshold) below the
*Schmelzschwelle* (melting threshold) is *Hysterese*; between them the material *erinnert sich*
(remembers). A fully *amorph* (amorphous) state is *eingefroren* (frozen-in) without a *Keim*
(nucleus) — the *amorphe Sperre* (amorphous lock) of Ghost #54.
