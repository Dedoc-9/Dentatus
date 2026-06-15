"""
dentatus — public package namespace (the Clean Room import contract).

Series 600 Interface & Agency layer. The engine core (`engine/`) is a frozen, AGPL-3.0
Physics Oracle and is NEVER imported directly by game code. Game layers reach the core
ONLY through this namespace:

    dentatus.core      — frozen oracle facade (read-only re-export of engine surface)
    dentatus.semantic  — L2 semantic compiler  (physical-property intent -> SEED_DECLARATION)
    dentatus.api       — L1 stateless reality API (intent/DAG -> verified observables + H_t)

Clean Room rule (enforced by game/tests/test_clean_room.py): no file under game/ may
`import engine` or `from engine ...`. All access flows through dentatus.*.
"""
__version__ = "0.6.0"          # Series 600
__engine_protocol__ = "exp505-v1"
__license__ = "AGPL-3.0-or-later (core); see DEV_NOTES_clean_room.md for dual-license boundary"
