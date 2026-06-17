"""
game/observability/composite_witness.py — EXP-525 Composite Attestation (integrity / anti-cheat)
                                          + EXP-528 Rolling nonce-chaining (replay immunity).

Binds the engine identity H_t to the game layer's own deterministic state, WITHOUT touching the frozen
engine (Charter II.3 / EXP-523 witness pattern).

  composite_address(H_t, game_stats)        -> PUBLIC tamper-evidence. A hash of deterministic, fully
                                               disclosed inputs. Anyone (incl. a replay) can recompute
                                               it; that is the point. NOT a lock.

  session_attest(H_t, game_stats, secret)   -> the REAL moat. An HMAC under a SERVER-HELD secret. A
  verify_attest(...)                           client cannot forge a valid attestation.

  NonceChain (EXP-528)                       -> a deterministic hash-ratchet over the sealed-H sequence.
                                               The chain is PUBLIC and replay-reproducible (EXP-520), so
                                               re-running history reproduces every nonce bit-for-bit. The
                                               secret never enters the nonce; replay IMMUNITY comes from
                                               binding the rolling head into session_attest and tracking
                                               a strictly-monotone accepted sequence.

Replay (EXP-520) is preserved: game_sufficient_stats are appended to the command log, so reconstruct()
reproduces the exact composite_address bit-for-bit. The engine `_compute_H` is unchanged.

Clean room: stdlib only; no engine.* import. Engine FROZEN.
"""
import hashlib, hmac, json

PROTOCOL = "exp525-v1"
NDIGITS = 6


def game_sufficient_stats(state, ndigits=NDIGITS):
    """Canonical, deterministic projection of arbitrary game-layer state to loggable sufficient
    statistics. Floats rounded, keys sorted -> reproducible across runs/processes (for replay)."""
    out = {}
    for k in sorted(state.keys()):
        v = state[k]
        if isinstance(v, float):
            out[k] = round(v, ndigits)
        elif isinstance(v, (list, tuple)):
            out[k] = [round(x, ndigits) if isinstance(x, float) else x for x in v]
        else:
            out[k] = v
    return out


def _canon(H_t, game_stats, protocol, nonce=None):
    # EXP-528: `nonce` is included ONLY when present, so nonce=None reproduces the pre-528 bytes exactly
    # -> existing composite/attest values are unchanged and old receipts still verify.
    payload = {"H_t": H_t, "game": game_sufficient_stats(game_stats), "pv": protocol}
    if nonce is not None:
        payload["nonce"] = nonce
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def composite_address(H_t, game_stats, protocol=PROTOCOL, nonce=None):
    """Public composite identity: binds engine H_t to game sufficient-stats. Tamper-evident, NOT secret.
    Changing any bound game statistic changes the address -> proves client state matches the engine step."""
    return hashlib.sha256(_canon(H_t, game_stats, protocol, nonce)).hexdigest()[:16]


def session_attest(H_t, game_stats, server_secret, protocol=PROTOCOL, nonce=None):
    """Server-signed attestation (HMAC-SHA256 under a secret the client never holds). Only an authority
    that knows `server_secret` can mint a valid attestation -> the real, forgery-resistant gate.
    EXP-528: when `nonce` is the current rolling head, the signature is bound to the exact sequential
    session position, so a captured-and-replayed frame fails once the head has advanced."""
    if isinstance(server_secret, str):
        server_secret = server_secret.encode()
    return hmac.new(server_secret, _canon(H_t, game_stats, protocol, nonce), hashlib.sha256).hexdigest()


def verify_attest(H_t, game_stats, server_secret, sig, protocol=PROTOCOL, nonce=None):
    """Constant-time verification of a server attestation (nonce-aware; nonce=None is the legacy path)."""
    expect = session_attest(H_t, game_stats, server_secret, protocol, nonce)
    try:
        return hmac.compare_digest(expect, sig)
    except Exception:
        return False


# == EXP-528 - Rolling nonce-chaining =================================================================
# Deterministic hash-ratchet over the sealed-H sequence. Public + replay-reproducible (a pure function
# of session_id and the H prefix). Nonce value public + HMAC binding = anti-replay.
NONCE_PV = "exp528-v1"


def nonce_genesis(session_id, protocol=NONCE_PV):
    """Deterministic genesis head for a session (public)."""
    return hashlib.sha256(("genesis\x1f%s\x1f%s" % (session_id, protocol)).encode()).hexdigest()[:16]


def advance_nonce(prev_nonce, H_t, seq, protocol=NONCE_PV):
    """One ratchet step: fold the just-sealed H_t (and its sequence index) into the head. Pure."""
    return hashlib.sha256(("\x1f".join([prev_nonce, str(H_t), str(int(seq)), protocol])).encode()).hexdigest()[:16]


class NonceChain:
    """Authority-side rolling nonce. `issue(H_t)` returns the nonce that binds THIS commit, then advances
    the head. The whole sequence is reconstructible from the command log via `expected_nonce`, so a
    replay re-derives identical nonces (EXP-520). Strictly ordered: `accept` rejects stale/replayed seq."""

    def __init__(self, session_id, protocol=NONCE_PV):
        self.session_id = str(session_id); self.pv = protocol
        self.seq = 0; self.head = nonce_genesis(self.session_id, protocol)
        self._last_accepted = -1

    def issue(self, H_t):
        """Return (seq, nonce) binding this commit; advance the head. Deterministic."""
        seq = self.seq; nonce = self.head
        self.head = advance_nonce(self.head, H_t, seq, self.pv); self.seq = seq + 1
        return seq, nonce

    def expected_nonce(self, H_seq, seq):
        """Pure replay oracle: the nonce commit `seq` MUST carry given the sealed-H prefix H_seq[:seq]."""
        n = nonce_genesis(self.session_id, self.pv)
        for i in range(seq):
            n = advance_nonce(n, H_seq[i], i, self.pv)
        return n

    def accept(self, seq, H_seq, presented_nonce):
        """Verifier guard: fresh iff the nonce matches the deterministic chain AND seq strictly advances
        (replay of an earlier, validly-signed frame is rejected because its seq is not newer)."""
        if seq <= self._last_accepted:
            return False
        if presented_nonce != self.expected_nonce(H_seq, seq):
            return False
        self._last_accepted = seq
        return True
