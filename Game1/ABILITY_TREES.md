# FRACTAL NEURON PULSE — Ability Trees & First Bleed-Zone
### Companion to the Genesis Codex. Every ability is costed in exact engine quantities.

All costs are **bits of `ΔS_cit`** (the Entropic Tax) unless noted, modulated by the Neuron Pulse
(crest = cheap, trough = breach). An ability *resolves* only if it passes the firewall it targets; a
failed cast is a self-inflicted breach paid by the surroundings (Codex §4). Cooldowns are measured in
**beats** (1 beat = `T = 1.539 s` on this seed).

Notation: `O` = order (commits `2^O` complexity) · `B_ent` = manifold entanglement (delist at `>0.8`) ·
`Wi` = Weissenberg shear · `χ` = compliance · `‖S‖` = ghost residual · `λ₂` = local Fiedler value.

---

## I · CANTORID — *the spectral fault* (controls Face 1: continuity)

> Reads the `λ₂` fault. Wins by **delisting** (forcing a target's `B_ent` over `ε=0.8`) and by
> **stitching** allies back under the threshold. Glass-cannon: lives near its own fault.

### Tier 1 — Seam
- **Fault-Read** *(passive)* — see every entity's `B_ent` and the local `λ₂` fault line as a bright
  vein in the vine-wallpaper. Free.
- **Spectral Lance** `O5` — a thin shear that adds `+0.25 B_ent` to one target. Stacks. 1-beat cd.
- **Stitch** `O4` — applies a partition-of-unity halo (`σ_s ∝ 1/√λ₂`) to an ally: `−0.4 B_ent`,
  pulling them back from delist. 2-beat cd.

### Tier 2 — Shear
- **Cantor Split** `O7` — if target `B_ent > 0.55`, drive it instantly over `0.8` → **delist** (the
  body splits along `λ₂` and falls out of phase; a clean removal, no corpse). Off-beat this breaches and
  *you* take the shear. 4-beat cd.
- **Fiedler Step** `O6` — teleport along the local fault line (you move where the manifold is already
  torn — zero traversal cost because the seam is already open). 3-beat cd.

### Tier 3 — Discontinuity *(capstone)*
- **The Unwitnessing** `O9` — raise `B_ent` of *every* enemy in a cone by `+0.5` at once. A mass
  delist if they were already stressed. Enormous tax: only survivable **on the crest** (synced
  `ΔS_cit ≈ +3`; off-beat `≈ −1` → foreclosure). The signature "I tear the floor out from under a room."

**Identity cost:** Cantorid abilities raise the caster's *own* local `λ₂` instability — your Mandelsnap
runs nearer `∂M` while you wield the seam.

---

## II · LIENWARD — *the entropic ledger* (controls Face 2: budget)

> Moves `K_budget`. Wins by **leverage and timing**: afford the impossible now, make enemies'
> reality unaffordable. Does not deal damage — deals *insolvency*.

### Tier 1 — Ledger
- **Solvency Sight** *(passive)* — see every entity's `ΔS_cit` headroom and outstanding liens. Free.
- **Underwrite** `O3` — lend an ally `+4` effective `K_budget` for 3 beats (their casts get cheaper).
  1-beat cd.
- **Tithe** `O5` — reduce an enemy's `K_budget` by `−4` for 3 beats; their next manifestation's
  `ΔS_cit` likely goes negative → **their own spell overheats and recoils**. 2-beat cd.

### Tier 2 — Leverage
- **Overdraw** `O8+` — manifest *one order above your cap* immediately by booking a **lien** =
  `|ΔS_cit < 0|`. The structure is real now; the debt matures in 4 beats. Stack liens at your peril.
  No cd (the cd is the debt).
- **Call the Note** `O6` — transfer your accumulated lien onto an enemy. *Their* surroundings pay your
  foreclosure (their ground melts, their ghosts spawn). The Lienward's signature escape from a death
  spiral. 5-beat cd.

### Tier 3 — Foreclosure *(capstone)*
- **Margin Call** `O9` — instantly mature **every** lien in the zone (yours and enemies'). A
  synchronized Citadel foreclosure: everyone over-leveraged pays at once. The Lienward thrives in the
  chaos because they chose *when*. Cast on the crest or be buried by your own book.

**Identity cost:** a Lienward at `lien > K_budget` is **foreclosed** — their Mandelsnap re-crystallises
violently inward (Codex §4b) and they are stunned for 2 beats. Solvent or nothing.

---

## III · ANNEALITE — *the phase smith* (controls Face 4: mechanical / thermal)

> Drives `Wi → E*_eff → χ`. Wins by **editing matter**: overheat enemies' structure to fluid (strip
> armor, pin), harden allies and ground, melt walls and re-freeze them. The only State that reshapes
> terrain on purpose.

### Tier 1 — Forge
- **Heat-Read** *(passive)* — see every material's `χ` and the local `Wi` field as colour-temperature
  in the wallpaper. Free.
- **Shear Lash** `O5` — `+0.2 Wi` on a target; raises its overheat risk. 1-beat cd.
- **Temper** `O4` — anneal an ally or floor tile one step toward order (`χ ↓ 0.1`, det-preserving) —
  tougher footing, slower but solid. Respects the hysteresis band (`Δ_hys = 0.15`). 2-beat cd.

### Tier 2 — Phase
- **Overheat** `O7` — flood a target with `Wi` until `Wi > ε_ref·χ_target` → **forced melt**: `χ → 1`,
  armor and stiffness stripped, the target **pinned as fluid** for 2 beats. The Annealite's hard CC.
  4-beat cd.
- **Quench** `O6` — total-melt a wall/barrier to fluid (party pours through), then re-freeze it behind
  you (oriented nucleation along your exit axis). Terrain control. 3-beat cd.

### Tier 3 — Hysteresis *(capstone)*
- **Cold Snap** `O9` — drop the whole zone's shear below the freeze threshold and **re-crystallise
  everything at once** along *your* chosen stress axis (EXP-522): enemies caught mid-melt lock solid in
  awkward poses (rooted), the floor spikes jagged crystal toward your foes, allies harden. The world
  remembers it was fluid — it stays your shape until shear returns. Crest-only.

**Identity cost:** the Annealite carries the **amorphous lock** risk — overuse *Overheat* on yourself
to dodge (quench-dash) and you may total-melt with no residual order, unable to re-solidify without an
external strain axis (a teammate's *Temper*, or a wall to nucleate against).

---

## IV · CROSS-STATE — the shared currency

- **The Pulse** is universal: any ability synced to the crest costs ~10 bits less (Codex §3). Mastery
  is rhythm.
- **Ghosts** (`‖S‖`) are universal hazard *and* fuel: a high-`‖S‖` zone (lots of recent overdrafts)
  spawns echo-bodies that any State can **harvest** — collapse a ghost to refund `+2` budget, or let it
  haunt an enemy. Ghost-rich zones are high-risk, high-reward arenas.
- **Trinity synergy:** Cantorid stresses `B_ent` → Lienward `Tithe` drops the target's budget → its
  panicked counter-cast overheats → Annealite *Overheat* finishes the melt. The "shear → insolvency →
  phase-break" combo is the intended high-skill kill chain.

---

## V · VERTICAL SLICE — "The First Bleed-Zone"

A single arena to prove the loop end-to-end. One seed → one deterministic level.

**The arena.** A circular witnessed platform suspended in the Bleed, seeded from one `H_t`. The floor is
**real re-crystallisation terrain**: tiles carry a live `χ` and melt/freeze under the players' shear
(Annealite reshapes it; a melted tile is a fall hazard into the Bleed = instant delist).

**The clock.** The whole fight runs on the seed's **39-BPM pulse**; the platform's vine-border lights in
a surge on every beat (the HUD wallpaper *is* the arena's edge). Casting off-beat is punished by the
Citadel directly — no separate enemy needed for the tutorial of timing.

**The encounter — the Foreclosure.** The boss is not a monster; it is a **maturing lien** the zone took
out to exist. A `ΔS_cit` debt counter ticks down each beat. The party must keep the zone solvent:
- **Cantorid** delists the **Bleed-spawn** (Bent-drifting fragments that wander in from the void and, if
  they reach the core, add complexity `N_γ` → raise the debt).
- **Lienward** manages the master ledger — *Underwrite* the core, *Tithe* the spawn, and on the final
  beat *Margin Call* to dump residual debt back into the Bleed.
- **Annealite** keeps the **floor solid** (anneal melting tiles) and *Cold Snaps* the spawn-wave at the
  phase the Lienward calls.

**Win:** drive `ΔS_cit ≥ 0` at the foreclosure beat → the zone is permanently witnessed, stamped with a
new `H_verified`, and the seed forks a child zone (next level = a deeper hash). **Loss:** `ΔS_cit < 0` at
maturity → the platform forecloses (mass re-crystallisation), the floor melts out, the party falls into
the Bleed and delists — but the run is **replayable bit-for-bit** from the zone seed (EXP-520), so death
is a coordinate, not a wipe.

**Build order:** (1) HUD wallpaper [done] → (2) one playable State (Annealite, most tactile) with floor
`χ` tiles → (3) the pulse-locked debt clock → (4) Bleed-spawn AI (simple `B_ent`-drift) → (5) the other
two States → (6) the `dentatus.api` socket so the debt counter is a *real* server `ΔS_cit`, not a local
mock.

**Engine contract:** the client sends intents to `dentatus.api.observe`, receives `{H_verified,
ΔS_cit, B_ent, Wi, χ, ‖S‖}`, and renders the Mandelsnap from those. The server stays authoritative; the
fight is auditable; the rhythm is the hash. *Reality first, all the way down.*
