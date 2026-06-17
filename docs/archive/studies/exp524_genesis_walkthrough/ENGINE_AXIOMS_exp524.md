# EXP-524 — The Genesis Block (Full System Walkthrough)

**Scope** NO engine edits. `walkthrough_genesis.py` (root) drives one world through the entire
constitution using only public operators. Engine FROZEN. The full capstone — file index, LLM handoff,
the seven acts, and axioms — is **`constitution/CAPSTONE.md`**.

## What it is

A single, asserting, deterministic script (the integration capstone) that composes every law:
creation → stress → metamorphosis (melt) → continuity (inject + interference) → audit (compact + replay
resurrection) → recovery (oriented nucleation) → final integrity witness. It is both the project's
proof-of-life and its end-to-end integration test — each ACT asserts the constitutional invariant it
demonstrates, so a non-zero exit means a law was violated.

## Verification

`PYTHONHASHSEED=0 python3 walkthrough_genesis.py` → **ALL ACTS PASS**, deterministic. Real captured
output and the act-by-act mapping to Charter articles are in `constitution/CAPSTONE.md §2`.

## Axioms

- **A1 Composability is the proof** — the seven acts use the same public operators any developer would;
  that they interlock into one unbroken asserting chain evidences the constitution's internal consistency.
- **A2 The cycle is closed and reversible** — thermal (melt 515 ↔ re-crystallise 521 / nucleate 522) and
  memory (inject 517 ↔ undo 518 ↔ replay 520) both run both ways; the world returns to FULL_VALID.
- **A3 The past is a coordinate** — ACT V resurrects genesis from `H_0` via command log + checkpoint,
  re-proving the hash (tamper-evident).
- **A4 Truth is invariant under symmetry and scale** — P_yz-invariant witnesses; resolution-relative
  integrity address.
- **A5 The engine never moved** — every law since EXP-509 lives outside the frozen core.

See `constitution/CAPSTONE.md` for the complete document.
