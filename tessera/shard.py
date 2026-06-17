"""
tessera/shard.py — a portable, self-verifying shard of a deterministic computation's process history.

A `tessera` is the Roman token two parties broke and later rematched to prove a prior agreement. Here it
is a tiny record that lets ANYONE replay a declared deterministic-integer computation offline and confirm
it took exactly the claimed path -- trusting no producer, no central validator, no log file.

WHAT IT PROVES (and the exact line it does not cross):
  * REPLAY-CORRECTNESS is trustless. Given the same pinned rule + the seed, a verifier re-runs the integer
    trajectory and recomputes a rolling path-hash; if it matches, the claimed step count, terminus, and
    bit-flip history are exactly real. No trust in the producer is required for this half.
  * AUTHORSHIP is NOT trustless. The optional signature attributes the shard to a key; verifying *who*
    minted it still needs that signer's pinned public key (Ed25519) -- the same bound as `pact`/`chronicle`.

HONEST BOUNDS (do not oversell):
  * This is NOT cryptography in the secrecy sense: there is no preimage resistance, anyone can mint a valid
    tessera for their OWN computation. Its value is that forging the *process history of a declared
    computation* is detectable -- not that results are secret or that a result cannot be recomputed.
  * A tessera proves the path of the DECLARED rule from the seed. It is a proof of THAT computation, never
    a proxy for unrelated heavy work: replaying a cheap orbit says nothing about a separate expensive job
    unless the job *is* the declared deterministic computation. (Reject the proxy fallacy.)
  * integrity != truth: it certifies the steps were taken, never that the computation's result is correct,
    wise, or meaningful.

Stdlib + optional Ed25519 via the frozen chronicle core; imports chronicle read-only (Sibling Law).
"""
import os
import sys
import hashlib

_WB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_WB, "chronicle"))
import core                                                  # chronicle/core.py
from signing import Ed25519Verifier                          # for authorship checks

PROTOCOL_VERSION = "tessera/1"
GENESIS = "0" * 64


class TesseraError(Exception):
    pass


# ----------------------------------------------------------------- the rolling path-hash (bit-flip history)
def roll(rule_step, done, seed, max_steps):
    """Walk the deterministic trajectory from `seed`, chaining a rolling hash of every intermediate state.
    Returns (path_hash, terminus, steps). Raises if `done` is not reached within max_steps."""
    h = hashlib.sha256(core.canonical_bytes({"v": PROTOCOL_VERSION, "seed": seed})).hexdigest()
    state = seed
    steps = 0
    while not done(state):
        if steps >= max_steps:
            raise TesseraError("terminus not reached within %d steps" % max_steps)
        state = rule_step(state)
        steps += 1
        h = hashlib.sha256(("%s|%s" % (h, core.state_hash(state))).encode()).hexdigest()
    return h, state, steps


def _body(ruleset_hash, seed, steps, terminus, path_hash, prev, meta):
    return {"protocol": PROTOCOL_VERSION, "ruleset_hash": ruleset_hash, "prev": prev,
            "seed": core._canon(seed), "steps": steps, "terminus": core._canon(terminus),
            "path_hash": path_hash, "meta": meta or {}}


# ----------------------------------------------------------------- mint
def mint(rule_step, done, seed, max_steps=1_000_000, signer=None, prev=None, meta=None):
    """Forge a tessera for the trajectory of (rule_step, done) from `seed`. The rule is source-bound via
    `ruleset_hash`, so a verifier proves it ran the SAME rule. Optionally signed for authorship."""
    rh = core.ruleset_hash(rule_step, done)
    path_hash, terminus, steps = roll(rule_step, done, seed, max_steps)
    body = _body(rh, seed, steps, terminus, path_hash, prev or GENESIS, meta)
    sig = signer.sign(core.canonical_bytes(body)) if signer is not None else None
    return {**body, "signature": sig, "algo": getattr(signer, "algo", None),
            "public_material": (signer.public_material() if signer is not None and signer.algo == "ed25519" else None)}


# ----------------------------------------------------------------- verify (trustless replay)
def verify(tessera, rule_step, done, verifier=None):
    """Re-run the pinned rule from the shard's seed and confirm the claimed path. Returns (ok, detail).
    Names the precise failure: RULESET / STEPS / TERMINUS / PATH / SIGNATURE."""
    if core.ruleset_hash(rule_step, done) != tessera["ruleset_hash"]:
        return False, "RULESET mismatch (verifier ran a different rule than the shard declares)"
    try:
        path_hash, terminus, steps = roll(rule_step, done, tessera["seed"], tessera["steps"])
    except TesseraError:
        return False, "STEPS mismatch (terminus not reached in the claimed %d steps)" % tessera["steps"]
    if steps != tessera["steps"]:
        return False, "STEPS mismatch (claimed %d, replayed %d)" % (tessera["steps"], steps)
    if core.canonical_bytes(terminus) != core.canonical_bytes(tessera["terminus"]):
        return False, "TERMINUS mismatch (replayed end-state differs)"
    if path_hash != tessera["path_hash"]:
        return False, "PATH mismatch (bit-flip history differs from the claim)"
    if tessera.get("signature") is not None:
        v = verifier
        if v is None and tessera.get("algo") == "ed25519" and tessera.get("public_material"):
            v = Ed25519Verifier(tessera["public_material"])
        if v is None:
            return False, "SIGNATURE present but no verifier key supplied (authorship unconfirmed)"
        body = _body(tessera["ruleset_hash"], tessera["seed"], tessera["steps"], tessera["terminus"],
                     tessera["path_hash"], tessera["prev"], tessera.get("meta"))
        if not v.verify(core.canonical_bytes(body), tessera["signature"]):
            return False, "SIGNATURE invalid (forged / wrong key)"
    return True, "VERIFIED"


# ----------------------------------------------------------------- forensic divergence (names the lie's step)
def locate_divergence(tessera, rule_step, claimed_path):
    """Given a producer's FULL claimed sequence, recompute step-by-step from the seed and return the index
    of the first state that does not match (or None if the claimed path is exactly reproducible). This is
    the 'name the exact step' forensic: the compact shard says match/no-match; a claimed scroll says where."""
    if not claimed_path or core.canonical_bytes(claimed_path[0]) != core.canonical_bytes(tessera["seed"]):
        return 0
    state = tessera["seed"]
    for i in range(1, len(claimed_path)):
        state = rule_step(state)
        if core.canonical_bytes(state) != core.canonical_bytes(claimed_path[i]):
            return i
    return None


# ----------------------------------------------------------------- immutable lineage (pact-for-computation)
def link(prev_tessera, rule_step, done, max_steps=1_000_000, signer=None, seed_from=None, meta=None):
    """Mint a new shard whose seed continues from `prev_tessera`'s terminus and whose `prev` binds to the
    prior shard's path_hash -- an immutable lineage of replayable computations."""
    seed = prev_tessera["terminus"] if seed_from is None else seed_from(prev_tessera["terminus"])
    return mint(rule_step, done, seed, max_steps, signer=signer, prev=prev_tessera["path_hash"], meta=meta)


def verify_lineage(chain, rule_step, done, verifier=None):
    """Verify each shard AND that each binds to its predecessor's path_hash. Returns (ok, fault) where
    fault names the exact link index and reason, or None."""
    prev_ph = GENESIS
    for i, t in enumerate(chain):
        ok, detail = verify(t, rule_step, done, verifier)
        if not ok:
            return False, {"link": i, "reason": detail}
        if t["prev"] != prev_ph:
            return False, {"link": i, "reason": "LINEAGE broken (prev != prior path_hash)"}
        prev_ph = t["path_hash"]
    return True, None
