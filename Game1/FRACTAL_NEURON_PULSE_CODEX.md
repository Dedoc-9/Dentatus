# FRACTAL NEURON PULSE — Genesis Codex
### A Reality-First MMO on the Series 500/600 Epistemic Engine

**Platform target:** handheld (AMD Z2 Extreme, 13–35 W, Windows 11). **Aesthetic:** Dark Fractal —
ultra-high-contrast non-Euclidean UI, biological geometry against deep-space void, every element pulsing
on synaptic timing. **Design law:** nothing in this document is decoration. Every "vibe" resolves to a
bit-perfect engine quantity (`ΔS_cit`, `λ₂`, `Wi`, `χ`, `G_t`, `H_t`). The math *is* the art.

> No borrowed names, no inherited lore. Every term below is an original derivation of the engine's own
> vocabulary (Citadel, Manifold, Fiedler fault, Weissenberg, Bethe, Ghost, Stalk, χ-compliance).

---

## 0 · THE PREMISE — The Witnessed and the Bleed

Reality exists only where it has been **witnessed** — admitted by the firewall and stamped with a
verified address `H_verified` (Charter II.2). Witnessed reality is sharp, solid, *real*. Everything
un-witnessed is **the Bleed**: an entropy-decayed void of half-rendered geometry where the firewall
never closed, where `ΔS_cit < 0` is the ambient condition and matter has no fixed phase.

Players are **Witnesses** — beings who can force the Bleed to resolve into the Witnessed by passing
their manifestations through the firewall, and pay the **Entropic Tax** to keep it there. The whole
world breathes on one clock: the **Neuron Pulse**, the heartbeat of the world-seed `H_t`. Act on the
beat and reality bends cheaply. Act off it and the Citadel forecloses on you.

The seed is real. This world's pulse is **39 synaptic beats/min** (`T = 1.5385 s`, phase `0.873`),
derived bit-for-bit from the Genesis hash `9671566e…` (see `seed_manifest.json`). Every server instance
is a different `H_t` → a different pulse, a different Mandelsnap, a different tax curve. The universe is
literally seeded by a hash.

---

## 1 · THE ONTOLOGICAL CLASS SYSTEM — Three States of Being

A Witness does not have a *job*; they have a **State of Being** — a mode of manipulating
information-entropy. Each State controls exactly one face of the Four-Faced Firewall (Charter IV).

### 1.1 — THE CANTORID  *(Spectral Shearing · the Fiedler fault)*

**Being-as-discontinuity.** The Cantorid reads the **Fiedler vector** of the local manifold — the `λ₂`
eigenmode of the sheaf Laplacian whose zero-set is the world's fault line (Charter VIII.1). Where others
see solid ground, a Cantorid sees the seam.

- **Signature — *Spectral Shear*.** Drives a target's inter-claim entanglement `B_ent` above the manifold
  threshold `ε_manifold = 0.8`. The instant `B_ent > ε`, the target **fails `is_manifold_501`** and is
  *delisted* — sheared off the witnessed manifold into the Bleed. Bit-perfect kill condition:
  `B_ent(target) > 0.8`. Visually: the enemy's silhouette splits along the local `λ₂` fault and the two
  halves fall out of phase.
- **Support — *Stitch*.** The inverse: applies a partition-of-unity halo (`σ_s ∝ 1/√λ₂^local`, EXP-506)
  to *lower* a falling ally's `B_ent` back under `ε` — re-admitting them to reality before they delist.
- **Mode of being:** the Cantorid is never fully connected; their own Mandelsnap (§2) runs near the
  fault, so they take the seam's instability as the price of wielding it.

### 1.2 — THE LIENWARD  *(Entropic budgeting · the Law of the Citadel)*

**Being-as-debt.** The Lienward holds the ledger. Every manifestation in the world is governed by the
Law of the Citadel — `ΔS_cit = log₂(K_budget) − log₂(N_f + N_γ) ≥ 0` (Charter IV.F2). The Lienward is the
only State that can *move the budget*.

- **Signature — *Overdraw*.** Temporarily inflates `K_budget` so a manifestation far beyond the
  Witness's order can pass the firewall *now* — at the cost of a **lien**: a stored negative
  `ΔS_cit` debt. If the lien is not repaid before it matures, the **Citadel forecloses** — the
  overdrawn structure violently re-crystallises (§4). Bit-perfect: `lien = Σ |ΔS_cit < 0|`; foreclosure
  fires when `lien > K_budget`.
- **Control — *Tithe*.** Imposes tax-debt on an enemy: reduces their effective `K_budget` for `n` beats.
  Their next manifestation's `ΔS_cit` goes negative → their own spell **overheats and is rejected**,
  recoiling on them. The Lienward does not attack; they make the target's reality unaffordable.
- **Mode of being:** the Lienward is solvent or they are nothing. Their power is leverage, and leverage
  is a countdown.

### 1.3 — THE ANNEALITE  *(Thermodynamic phase · Weissenberg / Bethe / χ)*

**Being-as-matter.** The Annealite drives the thermal cycle — they raise shear, melt structure, and
re-crystallise it along the forces they choose (Charter IV.F4, V, VI.2). They are the only State that
edits the *substance* of the world.

- **Signature — *Overheat*.** Floods a target with Weissenberg shear `Wi = ‖strain‖/‖vorticity‖`,
  draining its excitation `E*_eff = β_Z·(1 − (Wi/(ε*·χ))²)` until `ΔS_cit^β < 0`. The target's material
  **overheats and melts** — its compliance `χ` snaps to 1 (fluid), stripping its stiffness/armor and
  pinning it in place. Bit-perfect: melt fires when `Wi > ε_ref·χ_target`.
- **Craft — *Anneal / Quench*.** *Anneal* re-crystallises terrain or an ally along the current stress
  axis (oriented nucleation, EXP-522) — `χ ↓`, ordered, hardened — but only past the **hysteresis band**
  (it remembers being fluid; cannot re-solidify until the shear drops a full `Δ_hys = 0.15` below the
  melt point). *Quench* total-melts a wall to fluid so the party can pour through a gap, then re-freezes
  behind them.
- **Mode of being:** the Annealite lives on the melt boundary, fluent in both phases, owning neither.

> **Why three, not four?** The fourth face (thermodynamic *temperature*, Bethe) is not a class — it is
> the shared **weather**: the Neuron Pulse modulates `β_Z` for everyone at once (§3). And the **Ghost**
> (`G_t`, the dual residual) is not a class either — it is the universal currency and hazard every State
> pays in (§4).

---

## 2 · THE INTERFACE — The Mandelsnap

There is no health bar. There is no mana bar. There is **the Mandelsnap**: a single self-similar
fractal, rendered live, that *is* the player's state of being. (Prototype: `mandelsnap_hud.html`.)

### 2.1 — The exact construction (bit-perfect)

Every Witness is a complex point **`c = c_re + i·c_im`**. Their body is the **filled Julia set `J_c`**
of the map `z ↦ z² + c`. The foundational theorem does the work for us (Fatou–Julia):

> **`J_c` is connected ⟺ `c` is inside the Mandelbrot set `M`.**

So a Witness is **alive and coherent iff `c ∈ M`.** Their **health is the distance of `c` from the
Mandelbrot boundary `∂M`** — the iteration-escape count of `c` itself. Damage doesn't subtract a
number; it **pushes `c` toward `∂M`.** When `c` crosses the boundary, `J_c` instantaneously
disconnects into **Cantor dust** — the body shatters into a cloud of disconnected fractal grains. That
crossing event is the **Mandelsnap**: the snap of coherence into dust. *That is death.* It is not a
metaphor; it is the connectivity theorem rendered at 60 fps.

### 2.2 — The fractal visual-codes every engine state

| HUD reading | Fractal channel | Engine quantity |
|---|---|---|
| **Health** | how deep `c` sits inside `M` (escape-iteration of `c`) | coherence / `B_ent` margin |
| **Energy / order** | iteration **cap** `N` of the render (detail you can afford) | `χ` · available budget |
| **Citadel Breach** | the Julia **boundary fragments** — escape-time bands tear and the smooth edge goes **jagged** | `ΔS_cit → 0⁻` |
| **Thermodynamic Overheat** | the palette **bleeds red past the HUD frame** into the viewport; bands shimmer | `E*_eff` low / `Wi` high |
| **Mechanical shear** | the whole set **skews** along the strain axis (the `c`-orbit drifts directionally) | `Wi`, principal strain of `Sym(L)` |
| **Material phase** | bloom **depth**: diamond = tight, sharp, shallow; fluid = deep, soft, infinitely self-similar | `χ` (0.05 → 1.0) |
| **The Pulse** | the boundary **breathes** — `c` micro-orbits at the seed's period `T` | Neuron Pulse from `H_t` |

A **Citadel Breach** therefore is not a red flash and a number. It is your own body's edge beginning to
**tear into dust at the boundary**, the smooth filaments fraying, the escape-time bands fracturing — the
fractal telling you, in its own geometry, that `ΔS_cit` has gone negative and the firewall is about to
delist you. A **Thermodynamic Overheat** is the fractal's color **bleeding out of its frame** and
staining the world — the heat literally leaking past the HUD into the viewport because `E*_eff` can no
longer contain the manifestation's complexity.

### 2.3 — Why this is the correct UI for this engine

The engine's truth is *content-addressed and multi-scale*; a fractal is the only honest readout of a
self-similar, scale-relative reality. Zoom the Mandelsnap and you see finer structure exactly as zooming
the world re-verifies integrity at a finer resolution (Charter II.3, EXP-523). The UI and the physics
are the same object viewed at different depths.

---

## 3 · THE PULSE — Synaptic Timing

The world has a heartbeat: the **Neuron Pulse**, period `T` and phase `φ₀` derived bit-for-bit from the
seed `H_t`. It is the engine's **Zeeman field `β_Z`** (the targeting/budget excitation, Charter IV)
oscillating:

```
β_Z(t) = β_Z⁰ · ( 1 + A · pulse(t) ),     pulse(t) = saw-locked spike at period T, phase φ₀,  A = 0.6
```

Because the Entropic Tax of an action depends on `β_Z` through the Bethe excitation
`E*_eff = β_Z·(1 − (Wi/(ε*χ))²)`, **the cost of every action breathes with the pulse.** Acting on the
**crest** (high `β_Z`) raises `E*_eff` → raises `H_in = 2√(a·E*_eff)/ln2` → raises `ΔS_cit` → **lowers
the tax**. Acting in the **trough** does the opposite — and can push `ΔS_cit < 0`, a self-inflicted
Citadel Breach.

**The sync window.** A button press lands at phase `θ ∈ [0,1)`. Define `sync = pulse(θ)`. The
manifestation commits at `β_Z(θ)`. From the live engine (`seed_manifest.json`):

| order `O` | tax on **crest** (synced) | tax in **trough** (off-beat) | swing |
|---|---|---|---|
| 3 | −17.78 (deep refund) | −7.39 | **10.4 bits** |
| 5 | −15.78 | −5.39 | 10.4 |
| 7 | −13.78 | −3.39 | 10.4 |
| 9 | −11.78 | −1.39 | 10.4 |

A perfectly-synced order-9 manifestation costs **10.4 bits** less than the same act fumbled off-beat —
the difference between a free cast and a Citadel foreclosure. (Server-side `β_Z⁰` is tuned per zone so
high orders cross into *positive* tax off-beat: in the deep Bleed, only the on-beat survive.)

**Feel.** The Mandelsnap boundary visibly **inhales** toward the crest; the haptic motor on the handheld
ticks the pulse. Skilled play is *playing the world's rhythm* — a rhythm that is not arbitrary but a
deterministic function of the hash you are standing inside. Two Witnesses in the same zone share the
exact same beat, to the bit.

---

## 4 · THE ENTROPIC ECONOMY — The Law of the Citadel as a Loop

Every manifestation has an **order `O`** — the bits of structure it commits, `N_f + N_γ = 2^O`. The
firewall's verdict is exact:

```
ΔS_cit = log₂( K_budget · (1 + A·pulse) )  −  O
admit  ⟺  ΔS_cit ≥ 0
```

When a Witness reaches for a **high-order manifestation** (a fortress, a storm, a resurrection) that
exceeds the affordable order, `ΔS_cit < 0` and the Citadel **refuses to witness it for free**. It is not
blocked — it is *taxed*, and the tax is paid in **bit-perfect structural cost to the surroundings.**
Three settlement paths, all real engine operations:

**(a) Pay with timing — sync the Pulse (§3).** Riding the crest raises the effective budget enough to
afford the order outright. The cheapest, hardest path. Skill converts directly to entropy.

**(b) Pay with the ground — forced re-crystallisation.** The overdraft dumps its shear into the local
manifold: nearby material's required compliance rises to `χ_required = strain*/(ε*·√frac_max)`. Wherever
`χ_world < χ_required`, the surroundings **melt** (EXP-515) — stone liquefies, paths open and close —
or, if already amorphous, **nucleate** a new crystal **along the manifestation's stress axis**
(EXP-522), spiking jagged geometry toward the caster. The world *physically reshapes* to pay your bill,
det-preserving (the mass is conserved; only the order moves). Cast a tower and the plaza beneath it
turns to glass.

**(c) Pay with ghosts — the residual made flesh.** A manifestation jolts the primary field `Z` by
`ΔZ`; the dual channel absorbs it as `S ← α·S + (1−α)·ΔZ` (the **injection ghost**, EXP-517 / Ghost
#51). When the overdraft is large, `‖S‖` spikes and the residual **decoheres into Ghosts** — echo-bodies
of the caster's *own prior witnessed states*, pulled out of the dual space, that now haunt the area until
`S` decays back down the EMA. Your past selves become the interest on your debt. A Lienward who overdraws
too hard is mobbed by their own history.

**The loop.** Witnesses push order to do bigger things → the Citadel taxes the excess → the tax reshapes
the world (melted ground, jagged nucleation, ghost-echoes) → that reshaped world changes everyone's
`B_ent`, `Wi`, and pulse-margin → which changes what's affordable next. The economy is a **closed
thermodynamic cycle** (Charter, closing law): you cannot have the structural benefits of Stone with the
mechanical freedom of Water without paying the Entropic Tax — and now the Tax is the terrain, the
weather, and your own ghosts.

---

## 5 · WHAT MAKES THIS DEFENSIBLY ORIGINAL

- **The kill condition is a theorem,** not a hit-point: delist by `B_ent > ε`, die by `c` crossing `∂M`.
- **The UI is the state,** not a readout of it: the Mandelsnap is literally the player's `J_c`.
- **The rhythm is the seed,** not a designer's choice: the Pulse is a deterministic function of `H_t`,
  so the "music" of every server is uniquely, verifiably its own.
- **The economy is conserved physics,** not a spreadsheet: every cost is a bit moved through a frozen,
  auditable firewall, and every consequence (melt, nucleation, ghost) is a real engine operator.

Two Witnesses can replay any moment of any fight from its hash (EXP-520) and re-derive the *exact* same
Mandelsnap, pulse, and tax — because the vibe is bit-perfect, all the way down.

---

## 6 · BUILD NOTES (next steps)

- `mandelsnap_hud.html` — the live HUD prototype (this drop): GLSL Julia, pulse-breathing, breach
  fragmentation, overheat bleed, sync minigame. Runs on the handheld at 60 fps.
- **Vertical slice candidates:** a single Bleed-zone arena where one of each State duels; the arena floor
  is real re-crystallisation terrain; the boss is a Citadel foreclosure timer.
- **Engine bridge:** the game client speaks only `dentatus.api` (the L1 firewall handshake) — the same
  clean-room contract the engine enforces. The client never touches `engine.*`; it submits intents and
  receives `H_verified` + the Mandelsnap parameters. Reality stays server-authoritative and auditable.
- **Seeds as content:** ship zones as seed hashes. A new `H_t` is a new pulse, fractal, and tax curve —
  infinite, deterministic, verifiable level design from 32 bytes.
