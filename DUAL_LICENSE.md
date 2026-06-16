# DENTATUS — Dual Licensing

> **Not legal advice.** This document explains the *intended* licensing model and is a starting template.
> Before you offer commercial terms or rely on copyleft scope, have an IP attorney review it and draft
> the actual commercial agreement. License-scope questions (what counts as a derivative work, how AGPL
> applies across an API or network boundary) are genuine legal questions that this file cannot settle.

Dentatus is offered under **two tracks**. You (Daniel J. Dillberg) are the sole copyright holder, so you
may license the same code both ways.

---

## Track A — Open Source (AGPL-3.0)

The engine core and all published modules are licensed under the **GNU Affero General Public License,
version 3.0** (see `AGPL-3.0`). Under this track you may run, study, modify, and redistribute Dentatus
freely, **provided that**:

- if you distribute Dentatus or a derivative, **or make it available to users over a network**, you must
  offer the *complete corresponding source* of the covered work under AGPL-3.0;
- you preserve copyright and license notices.

This track is for the open community, research, and anyone willing to keep their derivative open.

**The clean-room boundary (what AGPL covers).** Dentatus is architected so the engine core
(`engine/`, exposed via `dentatus.core`/`dentatus.api`) is a self-contained covered work. Code that
merely *uses* the published `dentatus.api` contract across a process/network boundary may, depending on
the facts and the law, be a separate work — but **do not rely on that to keep a derivative closed.**
Whether your game is "based on" Dentatus is fact-specific. If you want certainty that your closed-source
project is not subject to AGPL, take Track B.

---

## Track B — Commercial License (closed source)

If you cannot or do not wish to comply with AGPL-3.0 — typically because you want to ship a
**closed-source** product, or distribute without disclosing your own source — you may obtain a
**commercial license** that grants Dentatus under non-copyleft terms.

The commercial license is the path for studios and vendors who want to:

- keep their game/application source proprietary;
- distribute binaries without the AGPL network/disclosure obligation;
- receive support, indemnification, or warranty terms (as negotiated).

Contact: **bigdilly95@gmail.com** · Subject: `Dentatus Commercial License`.

> The commercial agreement (price, scope, support, indemnity) is negotiated and lawyer-drafted per deal;
> this document only establishes that the option exists.

---

## What the license does *not* do (and why the moat is elsewhere)

The license is your **legal** protection. It is deliberately **not** propped up by crippling the open
core. Two technical layers do the protecting, and they sit *outside* the frozen engine:

1. **Composite attestation (integrity / anti-cheat) — `game/observability/composite_witness.py`.**
   The game's deterministic sufficient-statistics are bound into a verified address
   `composite = HASH(H_t ⊕ game_stats)`. This is **public tamper-evidence**: it proves a client's state
   matches the authoritative engine step. It is *not* a secret and is *not* a lock — anyone (including a
   deterministic replay) can recompute it. That is by design.

2. **Server-signed sessions (the actual moat) — `session_attest` (HMAC-SHA256 under `SERVER_SECRET`).**
   Only an authority holding the server secret can mint a valid attestation. A third party may run the
   AGPL engine and their own private world — that is their right and costs you nothing — but they
   **cannot** forge a session your official servers accept, **cannot** join your authoritative
   content-addressed ecosystem, and **cannot** ship your proprietary content and seeds. The moat is the
   **service and content**, secured by a secret they do not have — not a sabotaged open core, which
   would give no real protection and would forfeit the goodwill (and arguably the AGPL grant) you depend
   on.

**The engine stays frozen and fully runnable.** `engine/state.py`, `operators.py`, `confluence.py`, and
`validity.py` are unchanged by any commercial mechanism. Determinism and replay (EXP-520) are preserved
because game sufficient-statistics are appended to the command log. The Constitution (`constitution/`)
governs the engine regardless of license track.

---

## Summary

| | Track A — AGPL-3.0 | Track B — Commercial |
|---|---|---|
| Cost | free | negotiated |
| Your source | must be open (AGPL) | may stay closed |
| Network/distribution disclosure | required | waived |
| Support / indemnity | none | as negotiated |
| Access to official ecosystem | run your own | per agreement |

The fork is yours, openly. The *official, attested, content-addressed universe* is the product.
