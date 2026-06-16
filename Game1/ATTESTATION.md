# Dentatus Attestation — Deployment & Secret Protocol

The live mission-control bridge (`dentatus_bridge.py`) gates verified commits behind a server-signed
attestation (`game/observability/composite_witness.py`, EXP-525). This document is the operational
protocol for the one thing that makes the moat real: **the `DENTATUS_SERVER_SECRET`.**

> **Threat model.** The composite address (`HASH(H_t ⊕ game_stats)`) is *public* tamper-evidence — anyone
> can recompute it. The **only** secret in the system is the HMAC key. If it leaks, an attacker can forge
> sessions your official servers accept. Protecting this one value protects the entire commercial layer.

---

## 1 · Secret isolation (never in the repo, the client, or logs)

**The secret is read from the environment only** — `dentatus_bridge.py` line:
```python
SERVER_SECRET = os.environ.get("DENTATUS_SERVER_SECRET", "DEV_INSECURE_KEY_set_DENTATUS_SERVER_SECRET").encode()
```
The default is a deliberately useless placeholder; a real deployment **must** override it.

Hard rules:
- **NEVER** commit the secret. `.gitignore` blocks `.env*`, `*.secret`, `*.key`, `*credentials*`,
  `DENTATUS_SERVER_SECRET*`, etc. Verify with `git check-ignore -v .env`.
- **NEVER** ship the secret to the client. The cockpit (`tactical_cockpit.html`) never sees it — it only
  sends game sufficient-stats and receives the signed receipt. HMAC verification is server-side only.
- **NEVER** log the secret. Log the *attestation* and *composite* (safe, public-ish) — never the key.
- Prefer a managed secret store (cloud secrets manager / vault) injected as an env var at boot, over a
  `.env` file on disk. If you use a file, keep it `chmod 600` and outside the repo tree.

**Generate a strong key** (256-bit, base64):
```bash
# Linux/macOS
openssl rand -base64 32
```
```powershell
# Windows PowerShell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Max 256 }))
```

**Run the gated server** (strict mode rejects any commit lacking a composite frame):
```bash
DENTATUS_SERVER_SECRET="<your-32-byte-base64-key>" DENTATUS_REQUIRE_ATTEST=1 python dentatus_bridge.py
```
```powershell
$env:DENTATUS_SERVER_SECRET="<your-key>"; $env:DENTATUS_REQUIRE_ATTEST="1"; python dentatus_bridge.py
```

---

## 2 · Key rotation governance

Rotate **on a schedule** (e.g. every 90 days) and **immediately on any suspected leak**. Because
attestation is stateless HMAC, rotation needs a brief **dual-key overlap** so live sessions don't break.

**Rotation procedure (zero-downtime, dual-key window):**
1. **Generate** the new key `K_new` (Section 1). Do not delete `K_old` yet.
2. **Stage both.** Deploy a verifier that accepts a signature valid under **either** `K_old` *or* `K_new`,
   while **signing only with `K_new`** going forward. (Add a `DENTATUS_SERVER_SECRET_PREV` env var the
   bridge also checks in `verify_attest`; sign with the primary, accept either — a ~10-line change.)
3. **Drain.** Keep the overlap window open longer than your max session lifetime (e.g. 24 h) so every
   `K_old`-signed session has expired or re-attested under `K_new`.
4. **Retire.** Remove `K_old` (`DENTATUS_SERVER_SECRET_PREV`) and confirm only `K_new` verifies.
5. **Record.** Log the rotation event (timestamp, key id/fingerprint — **never the key**) to your audit
   trail. Use a non-secret key *fingerprint* `SHA256(key)[:8]` to identify which key signed a session.

**Key identification without exposure:** stamp each attestation context with a public `kid`
(`SHA256(secret)[:8]`) so you can tell which key signed a session during overlap — the fingerprint
reveals nothing about the key itself.

---

## 3 · Incident response (suspected leak)

1. **Rotate now.** Treat the leaked key as `K_old`; generate `K_new`; run the dual-key window but
   **shorten the drain** (force re-attestation) and **revoke** `K_old` as fast as session lifetimes allow.
2. **Invalidate sessions.** Any session whose attestation verifies only under the leaked key is suspect —
   require re-attestation under `K_new`.
3. **Scrub history.** If the key ever touched the repo, a `.gitignore` is **not** enough — the secret is
   in git history. Rotate (the old key is now worthless anyway) and, if the repo is private/internal,
   purge with `git filter-repo` (or BFG) and force-push; if it was ever public, **assume permanently
   compromised** and rely on rotation, not deletion.
4. **Audit.** Review the bridge command log and access logs for sessions signed under the leaked key
   during the exposure window.

---

## 4 · Pre-commit checklist (run before every push)

```bash
git check-ignore -v .env                       # -> must print a .gitignore match
git grep -nE "DENTATUS_SERVER_SECRET\s*=\s*[\"']" -- '*.py' || echo "OK: no literal secret assignment"
git grep -niE "openssl rand|topsecret|BEGIN .*PRIVATE KEY"  || echo "OK: no obvious key material"
```
The bridge must contain **only** `os.environ.get("DENTATUS_SERVER_SECRET", ...)` — never a literal key.

---

## 5 · What is safe to commit

| Safe in repo | Never in repo |
|---|---|
| `dentatus_bridge.py` (reads secret from env) | the secret value |
| `composite_witness.py` (the algorithm) | any `.env` / `*.key` / `*.secret` file |
| `composite_address` outputs (public) | the HMAC key or its base64 |
| attestation *signatures* in logs (useless without the key) | server private keys / TLS keys |

The algorithm is open (AGPL). The **key** is the moat. Guard the key; publish everything else.
