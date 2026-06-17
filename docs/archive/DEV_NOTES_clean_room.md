# DEV NOTES — Clean Room Protocol (Core ⇄ Game linkage)

**Design philosophy.** Every game — starship dogfight or turnip-farming sim — lives in a
separate Game Layer that treats the Engine Core as an immutable, black-box oracle of truth.
The engine roasts the "turnips" of axiomatic truth; games consume verified hashes.

## Project topology

```
Reality_Engine/                    (repo root)
├── engine/                  FROZEN core internals (operators, validity, state)  — AGPL-3.0
│   └── validity.py          firewall is_manifold_501, covariance, predicates
├── studies/                 axioms + seed declarations (EXP-301…505, Series 600 roadmap)
├── dentatus/                PUBLIC CONTRACT (import path) — the only door into the core
│   ├── core.py              frozen oracle facade (re-export of engine surface)
│   ├── semantic.py          L2: physical-property intent -> SEED_DECLARATION
│   └── api.py               L1: stateless observe/step -> observables + verified hash
├── dentatus_service.py      process-boundary handshake (stdio JSON) — license firewall
├── pyproject.toml           packages `dentatus-core` (AGPL-3.0)
└── game/                    DECOUPLED game layer — SEPARATE project, own license
    ├── pyproject.toml       depends on dentatus-core; license independent of core
    ├── examples/            game programs (handshake only)
    └── tests/test_clean_room.py   CI guard: forbids `import engine` under game/
```

## The three rules

1. **Immutable Core.** `engine/`, `engine/validity.py`, `studies/` are a black box. Series 600
   adds nothing to them — `dentatus/` and `game/` were created without editing a single engine
   file. Engine evolves only under its own AGPL studies pipeline (EXP-NNN + Fork A/B).
2. **Deterministic import path.** Game and API code import `dentatus.core` (stable), never
   `engine.*` (internal). The facade decouples callers from internal refactors.
3. **The Handshake.** Game ⇄ Core crosses only via L1 `dentatus.api` and L2 `dentatus.semantic`:
   Intent JSON in, Verified State Hash (`H_verified`) out. No stalk/operator/log-Cholesky detail
   leaks upward; no game mechanic leaks downward.

## Firewall = handshake contract

`dentatus.api.observe` stamps `H_verified` **only when `is_manifold_501` (ε=0.8) passes**. A torn
manifold returns observables but `H_verified = None`. The game literally cannot obtain a verified
universe that violates manifold continuity — validity is enforced at the boundary, not trusted.

## Cross-project linkage (how `import dentatus.core` works without merging codebases)

- Core is installable: `pip install -e .` exposes `dentatus` and `engine` as `dentatus-core`.
- Game is a separate project: `game/pyproject.toml` declares `dependencies = ["dentatus-core"]`.
  The game repo can live anywhere; it pulls the core as a versioned dependency, never vendoring it.
- In-repo dev: run with the repo root on `PYTHONPATH` (examples include a one-line bootstrap).

## Licensing (NOT legal advice)

- Core: **AGPL-3.0-or-later**, sole copyright Daniel J. Dillberg ⇒ **dual-licensing is available**.
- Proprietary games stay lawful via either:
  - **Process boundary** — run `dentatus_service.py`; the game is a separate program exchanging
    JSON, not an in-process linked derivative; or
  - **Commercial dual license** — the author grants a non-AGPL license for linked distribution.
- In-process `import dentatus.core` is for **engine development** and **AGPL-licensed games**.

## Solo / independent development

The engine is a self-contained AGPL project (`dentatus-core`) with its own test suite
(`run_seed_exp*.py` / `run_p_invariance_exp*.py`, all Fork A/B green). An independent developer
can fork, extend the studies pipeline, and ship under AGPL-3.0 — or, as copyright holder, grant
commercial licenses — without ever touching a game layer.

## Determinism requirement (content-addressed store)

`H_verified` (the realized-state reality address) is bit-stable only with **`PYTHONHASHSEED=0`**
(EXP-602 Ghost #32). `dentatus_service.py` self-pins it; set it in any process that needs stable
addresses. EXP-601 fixed claim-id determinism; the hash-seed pin fixes set/dict iteration order.

## Guardrails (wire into CI)

```bash
python game/tests/test_clean_room.py     # fails if game/ imports engine.* directly
python run_seed_exp505.py                # core forks must stay green (no contamination)
PYTHONHASHSEED=0 python game/examples/docking_bay.py   # handshake smoke -> bit-stable H_verified
python studies/exp602_semantic_compiler/determinism_crossproc.py  # cross-process address stability
```
