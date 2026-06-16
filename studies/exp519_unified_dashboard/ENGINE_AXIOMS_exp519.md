# EXP-519 — Unified Kinetic Dashboard (Capstone)

**Protocol** `exp519-v1` · **Scope** NO engine edits. `game/observability/kinetic_dashboard.html`
(WebGL/Three.js r128 + 2D canvas) replays `kinetic_telemetry.json`, captured by driving the real
engine through a Weissenberg shear ramp. Engine FROZEN.

## Reality First — the dashboard shows captured engine numbers, not animation

The telemetry is produced by a `CompactingWorld` (EXP-518) over a 4-plateau Weissenberg staircase:
each frame computes the real `bethe_citadel_strain_512` verdict (EXP-512/513), the material compliance
`χ` (EXP-514) of the live claim's Sector D, and — on a survivable breach — enacts a phase change
(EXP-515), injects it live (EXP-517), compacts (EXP-518), and records the provenance edge (EXP-516).
The `H_t` chain is **bit-identical on re-run** (deterministic capture, PYTHONHASHSEED=0), so the
visualization is a faithful replay of a reproducible reality, not a hand-animated mock.

## The four panels (one verdict, four faces)

1. **THE SEAM** — a manifold lattice shears by the real strain; cells tinted by the Weissenberg
   heat-map (blue→red as `Wi → Wi_crit`).
2. **THE YIELD** — the Citadel integrity arc dips toward the firewall (`ΔS=0`), flashes the
   `χ_required` target on the compliance bar, and pops on each melt; ends on `FIREWALL HOLDS · REJECT`
   when the shear is unsurvivable.
3. **THE LINEAGE** — the provenance tree grows one content-addressed node per transition
   (cyan diamond → amber glass → blue fluid), current node ringed, `H_after` shown.
4. **THE TRUTH** — the bit-perfect `H_t` advances every transition; the live working-set gauge stays
   flat (bounded) while the auditable-history gauge climbs (unbounded); the `‖ghost‖` (injection `dZ`)
   sparkline spikes at each melt; `η_CLT` reads the compaction-preserved observable.

## Captured arc

`diamond (χ=0.05) → glass → fluid (χ→1.0) → unsurvivable (firewall holds)` over 80 frames / 23
transitions; working set constant at 1; history → 23; 24 distinct `H_t`. The full Series 500 story —
the four-faced firewall and the kinetic lineage — in one view.

## Verification

Telemetry determinism: regenerating the capture yields a byte-identical `H_t` chain (proven). The
dashboard JSON parses, embeds no external data, and loads Three.js r128 from the approved CDN.
