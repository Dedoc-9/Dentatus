# EXP-515 — Enacted Phase Change (Fork λ)

**Protocol** `exp515-v1` · **Declaration hash** `c238e89e21e18bb50ad97626309f923e1efb93f8bb50c92d62ce872204415bfa`
**Scope** NO engine edits. `game/agency/phase_change.py` consumes `dentatus.core`
(`material_compliance_chi_514`, `bethe_citadel_strain_512`, `cholesky_from_stalk_401`) +
`dentatus.semantic` (`stalk_D_from_sigma`). `state`/`operators`/`confluence`/`validity` FROZEN.

---

## A1 — Reported → enacted

EXP-514 *reports* `χ_required` but never mutates the world (A6 firewall). Fork λ is the game-layer
policy that *enacts* the transition: on a survivable breach (`χ_world < χ_required ≤ 1`) it re-declares
the world's Sector D so the manifold survives the present shear, and emits a **witnessed** transition
`H_before → H_after`. The engine stays a pure oracle; the choice to transition (and its audit trail)
lives in the game layer. This is the kinetic step — overheat rejection becomes a *state change*, not an
error.

## A2 — Melt geometry: volume-preserving anisotropy reduction (dual math ↔ code)

The least-dissipation path reduces only the *anisotropy* of `Σ`, preserving its volume `det Σ`:

    ℓ_i = ln λ_i(Σ);   ℓ̄ = mean(ℓ_i)
    λ_i(t) = exp( ℓ̄ + (1−t)·(ℓ_i − ℓ̄) )        # shrink log-eigenvalue spread; Σℓ_i preserved ⇒ det preserved
    t=0 → original;   t=1 → isotropic at constant volume (λ_i = geometric mean)

```python
lam, V = eigh(Sigma); ll = log(lam); lbar = ll.mean()
Sigma_t = (V * exp(lbar + (1-t)*(ll-lbar))) @ V.T          # det(Sigma_t) == det(Sigma) for all t
```

`χ(t)` is monotone increasing (entropy rises as the spectrum equalises). Verified: diamond
`[54.6, .14, .14]` melts through `χ = 0.05 → 0.08 → 0.29 → 1.0` with `det ≡ 1.0` throughout.

## A3 — Two modes

| Mode | Rule | Meaning |
|---|---|---|
| **minimal** | `t* = min t : χ(melt(Σ,t)) ≥ χ_required + margin` (bisection, 50 iters) | least entropy injection — **graceful yield** (diamond → stressed glass). Pays the *exact* Entropic Tax. |
| **total** | `t = 1` | full isotropic melt (diamond → fluid). `χ → 1`. |

Verified (Fork A): minimal lands `χ = 0.631` against `χ_required = 0.630` (overshoot `0.001`, i.e. the
margin) and admits; it does **not** run to `χ = 1`. Total melts to `χ = 1`. Both preserve volume.

## A4 — Three outcomes (firewall-exhaustive)

    χ_world ≥ χ_required          → status=stable        (no transition; H unchanged)
    χ_world < χ_required ≤ 1      → status=melted        (minimal/total re-declaration; H_before≠H_after)
    χ_required > 1 (unsurvivable) → status=unsurvivable  (no melt saves it; world must shed shear/complexity)

The `unsurvivable` branch is the honest limit: when even the isotropic limit (`χ = 1`) cannot admit the
shear at this excitation/complexity, the firewall is telling you the problem is not the material — it is
the shear or the budget. No re-declaration is attempted (Fork A [7]).

## A5 — Witness & purity (backreaction firewall)

The function returns a **new** stalk and a witness; it never mutates the input or any engine state
(Fork A [9]). The witness hash is built from the **eigenvalue spectrum** (P_yz-invariant) + `χ` +
protocol — the off-diagonal Sector D bits (signed under x→−x) are excluded, consistent with Ghost #27
and the EXP-505 track hash. `H_before ≠ H_after` records the transition as an auditable event; under
reflection both hashes are invariant (Fork B).

---

## DEV NOTE — Ghost #49: melt is one-way, and the level set is under-determined

1. **Irreversibility / hysteresis.** This policy only *melts* (raises `χ` toward isotropy); it never
   re-crystallises. A manifold that survived a shear spike by melting stays melted even if the shear
   subsides. That is physically reasonable for a single yield event, but a full material model needs a
   *reverse* path (cool/anneal) with its own threshold — otherwise the world monotonically loses order
   (entropy ratchet). The residual is the missing re-crystallisation operator (Fork ξ): it must have a
   *different* threshold than the melt (true hysteresis), or melting and freezing would chatter at the
   boundary.

2. **The level set is a manifold; the geodesic picks one point on it.** The constraint `χ(Σ') =
   χ_required` defines a whole surface in Sector-D space (e.g. one could melt a single axis, or all
   axes unevenly). The volume-preserving **uniform** spread-reduction geodesic is a *canonical* choice
   — minimal, isotropic-direction, deterministic — but it is a choice, not the only solution. Naming it:
   the melt direction is the gradient of spectral entropy under the det-constraint; uniform reduction is
   its symmetric representative. A future fork (Fork μ, anisotropic χ) could melt preferentially along
   the shear axis, a *less* symmetric but more physical yield.

3. **Reported ≠ enacted stays a game-layer line.** The engine deliberately does not call this policy;
   admissibility and the transition decision are separated so the engine remains a stateless oracle and
   `H_verified` content-addressing is never polluted by a policy choice.

## Suggested improvements / forks

- **Fork ξ (re-crystallisation / annealing).** The reverse operator with a distinct (lower) threshold,
  giving true thermal hysteresis instead of a one-way entropy ratchet.
- **Fork ο (witnessed transition log → DAG).** Thread `H_before → H_after` into the EXP-505/602
  provenance DAG so phase changes are first-class nodes in the world history.
- **Fork π (directional melt).** Melt preferentially along the principal shear axis (pairs with EXP-511
  Fork δ / EXP-514 Fork μ) — anisotropic yield rather than uniform spread reduction.

## Foreign-language note (rhetoric → code)

The graceful-yield mode is *Fließen* (plastic flow / yielding), not *Schmelzen* (melting): the manifold
*nachgibt* (yields) just enough — *minimale Entropie-Einspritzung* (minimal entropy injection) — rather
than fully *schmilzt* (melts). The geodesic preserves *Volumen* (`det Σ`) and reduces only the
*Anisotropie*; the transition is *bezeugt* (witnessed) by the *Eigenwertspektrum*-hash. The one-way
nature is the *Entropie-Ratsche* (entropy ratchet) of Ghost #49, awaiting its *Rekristallisation*.
