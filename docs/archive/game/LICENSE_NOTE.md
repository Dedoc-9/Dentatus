# Licensing boundary (game layer)

**Not legal advice** — confirm specifics with counsel before distribution.

- **Engine core (`engine/`, `dentatus/`, `studies/`)**: GNU AGPL-3.0-or-later. Copyright held
  solely by Daniel J. Dillberg, which permits **dual licensing**.
- **This game layer (`game/`)**: licensed independently. It may be proprietary, experimental,
  or open — its license is declared in `game/pyproject.toml`, separate from the core.

## How proprietary game development stays clean

AGPL copyleft generally extends across **in-process linking**. Two boundaries keep a proprietary
game lawful above an AGPL core:

1. **Process boundary (recommended for proprietary).** Run the core via `dentatus_service.py`
   (stdio/socket JSON). The game is then a **separate program** exchanging Intent JSON ⇄ Verified
   Hashes — not a linked derivative. (AGPL's network clause still obliges the *engine service* to
   offer its own source to its users; it does not reach into the separate game program.)
2. **Dual license (recommended for shipping a linked binary).** As sole copyright holder, the
   author may offer the engine under AGPL-3.0 **or** a commercial license. Open games take AGPL;
   proprietary games take the commercial grant.

In-process `import dentatus.core` is intended for **engine development** and **AGPL-licensed
games**. Proprietary games should use boundary (1) or (2).
