# crucible — the reverse-Collatz adversary (controlled chaos, no entropy)

`crucible` completes the triangle: **`syracuse` is the law, `tessera` is the witness, `crucible` is the
test.** It runs the compressed Syracuse map *backward* — starting from the terminus 1 and growing the tree
of pre-images upward — so every seed it emits has a forward stopping time equal to its reverse depth,
**known by construction rather than by guessing**. It is a deterministic fuzzer: structured hard cases, not
random garbage, with no RNG and therefore no entropy to drift the integer stack.

> Naming note: this is the `glitch_gen` spec from the design. It's filed as `crucible` to avoid colliding
> with the existing `glitch/` sibling (the forward state-space explorer); the two are distinct.

## Run it

```
PYTHONHASHSEED=0 python3 demo_crucible.py            # forest · ration boundary · tessera stress · manifest · gate
PYTHONHASHSEED=0 python3 tests/test_crucible.py      # 10 attack simulations
```

## How it generates difficulty

Pre-images of `m` under the compressed map `T(n) = n/2 | (3n+1)/2`:

```
even branch:  n = 2m            always valid (2m is even)
odd branch:   n = (2m-1)/3      valid iff 2m-1 ≡ 0 (mod 3), the result is odd, and > 1
```

The `n > 1` guard excludes re-entry into the trivial 1→2→1 cycle, so the reverse graph is a tree. A node at
reverse-depth `d` is a seed with forward stopping time exactly `d`. `verify_seed` cross-checks every emitted
seed against an **independent forward replay** through `syracuse` — the generator's own integrity gate.

Hardness is measured by **altitude = peak // n** (how far the orbit climbs above its seed). This matters:
raw `peak` trivially favours large powers of 2 (which have `peak == seed`, altitude 1, and are the
*easiest* cases — pure descent). `altitude` instead surfaces genuine climbers like `n=15279` (peak 77354,
altitude 5×).

## The Red Team Oracle (`oracle.py`)

It fires generated seeds at the rest of the stack and reports whether integer integrity holds:

- **`ration`** — `inject_ration(K)` finds a hard seed just within a step budget `K` (admitted) and a deeper
  one beyond it (refused) — the exact boundary, identical on any hardware.
- **`tessera`** — `inject_tessera(n)` mints a proof shard over a high-altitude climber's full orbit and
  replays it; the rolling 256-bit path-hash over arbitrary-precision integers cannot overflow or lose
  precision, and this confirms that end-to-end rather than asserting it.
- **`fuel`, `elenchus`** — later children; their hooks are declared TODO. The oracle does not pretend to
  test code that does not exist yet.

`build_manifest` / `write_manifest` emit a reproducible, **content-addressed** difficulty map
(`glitch_manifest.json`): the hardest seeds by altitude, each forward-verified, under a `manifest_hash`.

## Preflight integration

`tests/test_crucible.py` includes the **generator gate**: if `crucible` cannot forge a verifiable,
non-trivial hard seed, the suite fails — a broken generator breaks the build. The tests are written as
deterministic *attack simulations*, so a green run is a reproducible attack, not a lucky one.

## Honest bounds (do not oversell)

- It constructs seeds with a **known, targeted** stopping time and peak. It does **not** find the globally
  hardest seed — that is bound up with the open conjecture. It maps the difficulty landscape; it does not
  claim to maximize it.
- Surviving these seeds is **evidence** of integer integrity over a structured hard set, **not proof** of
  correctness for all integers. (integrity ≠ truth.)
- It does **not** solve Collatz. "Here is a seed that takes S steps — can your stack handle it?"

## Files

| File | Role |
|---|---|
| `forest.py` | reverse-Syracuse pre-image tree; `generate`, `verify_seed` (forward cross-check), `select` (altitude), `seed_just_under` |
| `oracle.py` | Red Team Oracle: `inject_ration`, `inject_tessera`, `build_manifest` / `write_manifest` (content-addressed) |
| `demo_crucible.py` | forest (A) · ration boundary (B) · tessera stress (C) · manifest (D) · generator gate (E) |
| `tests/test_crucible.py` | 10 attack simulations (also the preflight unit suite) |
