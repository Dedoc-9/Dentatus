# constitution/ — the canonical law of the Dentatus Reality Engine

This folder is the authoritative, consolidated specification. Read in order:

1. **[CONSTITUTIONAL_CHARTER.md](CONSTITUTIONAL_CHARTER.md)** — the Theory of the Manifold. State,
   operator pipeline, hash index, the ghost, the Four-Faced Firewall (with the unified
   stress→temperature→entropy law), Epistemic Materialism, the Kinetic Lineage, invariances, the clean
   room, observability. **Start here.**
2. **[EXPERIMENT_LEDGER.md](EXPERIMENT_LEDGER.md)** — the proof index: each article backed by a
   preregistered, hash-locked study (Fork A determinism + Fork B P_yz).
3. **[GHOST_REGISTRY.md](GHOST_REGISTRY.md)** — the catalogue of numeric residuals (#1–#54).
4. **[CAPSTONE.md](CAPSTONE.md)** — the Genesis Block: full-system walkthrough, file index, LLM handoff. Run `walkthrough_genesis.py` beside it.

**Authority.** The charter governs the *law*; the studies govern the *proof*. The engine core
(`engine/state.py`, `operators.py`, `confluence.py`) is frozen; behaviour is added only as additive
`engine/validity.py` predicates or in the decoupled game layer. Every law is verified by a runner
(`run_seed_exp*.py` + `run_p_invariance_exp*.py`) under `PYTHONHASHSEED=0`.

**For an LLM/developer handoff:** the charter is the single source of truth for *what the engine
guarantees*. To extend it, declare a new study (seed + axioms), implement behind the clean-room
boundary, and prove Fork A/B before amending the relevant article.
