# Dentatus Game Layer (decoupled)

This is a **separate project** that sits *above* the Dentatus engine core. It is the home for
all game-specific mechanics — Star Wars combat, RuneScape-style economies, the nested "Call of
Duty" PC, turnip-farming sims. None of that lives in the engine.

## The Clean Room Protocol

| Tier | What it is | Rule |
|------|------------|------|
| **Immutable Core** | `engine/`, `engine/validity.py`, `studies/` | Black-box Physics Oracle. Frozen. AGPL-3.0. |
| **Public Contract** | `dentatus.core` / `dentatus.semantic` / `dentatus.api` | The only import path. Stable. |
| **Game Layer** | `game/` (this project) | Talks to the core **only** through the handshake. |

**The Handshake.** The game sends **Intent JSON** (physical properties) and receives **Verified
State Hashes** (`H_verified`) plus observables. It never touches the stalk schema, operators, or
log-Cholesky internals. A verified hash is issued **only when the manifold firewall
(`is_manifold_501`, ε=0.8) passes** — the game cannot obtain a verified world that is torn.

```python
from dentatus import api            # L1 handshake — the ONLY engine access game code uses
resp = api.observe({"op": "observe", "intent": {...}})
if resp["H_verified"]:
    ...                             # mathematically stable, verified world
```

## Decoupling is enforced, not just documented

`game/tests/test_clean_room.py` fails CI if any file under `game/` does `import engine` or
`from engine ...`. Game code reaches the core exclusively through `dentatus.*`.

For maximum license separation, run the core out-of-process via `dentatus_service.py` (stdio
JSON): the game becomes an independent program exchanging JSON across a process boundary.

## Running the example

```bash
# from the repo root (or with dentatus-core installed)
python game/examples/docking_bay.py
python game/tests/test_clean_room.py
```
