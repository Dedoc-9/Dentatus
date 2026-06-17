"""
quorum/tally.py — exact integer consensus over content-addressed state (the second half of the tautology).

The workbench's standing modesty is one clause: integrity(node) does NOT entail truth. A single replay-
verified ledger is honest and reproducible and can still be wrong, because its inputs/world-model were
never in scope. This module supplies the complementary clause, which DEFINES operational truth by
construction:

    Truth_op(round) := h*   such that   #{ w in Q : authentic(w) and H_w = h* } >= k

i.e. operational truth is the exact state hash on which a k-quorum of independently-keyed, integrity-
holding witnesses coincide. The two clauses only close the position together: integrity is necessary
per-witness; truth is the emergent fixed point across witnesses. Consensus-truth is analytic (the
agreement IS the truth), not correspondent (it is not checked against an external world).

INTEGER consensus: agreement is on exact 256-bit state hashes, so the relation is decidable and
tolerance-free -- h_i == h_j or it is not. There is no epsilon, hence no arbitrary coarse-graining
boundary. The ONE declared model construct is the quorum threshold k (the cut between consensus and
no-consensus); it is a chosen parameter, never an inherent limit.

EXACT GATE (folded into the certificate hash): witness id, round id, state_hash, k, n, the sorted vote
set. OBSERVABLE (recorded, never gated): agreement ratio, effective opinion-blocs (ESS), divergence.

HONEST BOUNDS: this is a quorum TALLY, not asynchronous Byzantine agreement -- no leader, no view-change,
no liveness guarantee under partition. Witness INDEPENDENCE is a trust input (pinned keys, out-of-band),
not a proven property; the tally cannot detect a Sybil operator behind several "witnesses". A colluding
>=k majority certifies a falsehood -- the certificate proves agreement among the named keys, nothing more.
Consensus is not truth either. (Integrity != truth, applied recursively.)

Stdlib + optional Ed25519 via the frozen chronicle core; imports chronicle read-only (Sibling Law).
"""
import os
import sys
import hashlib
from collections import Counter

_WB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_WB, "chronicle"))
import core                                                  # chronicle/core.py (canonical bytes, state_hash)
from signing import Ed25519Signer, Ed25519Verifier, HmacSigner, ed25519_available

PROTOCOL_VERSION = "quorum/1"


class QuorumError(Exception):
    pass


# ----------------------------------------------------------------- witnesses, keys, registry
def make_witness(seed_label):
    """Return a signer for a witness. Ed25519 (asymmetric: third parties verify, cannot forge) when the
    optional core is present; HMAC symmetric fallback otherwise (verifier can forge -- demo only)."""
    if ed25519_available():
        return Ed25519Signer()
    return HmacSigner(("quorum_witness_%s" % seed_label).encode())


def verifier_for(signer):
    if signer.algo == "ed25519":
        return Ed25519Verifier(signer.public_material())     # PUBLIC half only
    return signer                                            # HMAC: same key verifies (symmetric)


def build_registry(signers):
    """signers: {witness_id: signer}. Returns the PINNED registry {witness_id: verifier} a tally trusts.
    The registry is the trust anchor: a vote from a witness not in it is rejected, never counted."""
    return {wid: verifier_for(s) for wid, s in signers.items()}


# ----------------------------------------------------------------- votes
def _vote_message(witness_id, round_id, state_hash):
    return core.canonical_bytes({"protocol": PROTOCOL_VERSION, "round": round_id,
                                 "witness": witness_id, "state_hash": state_hash})


def witness_vote(witness_id, round_id, state, signer):
    """A witness's signed claim that, at `round_id`, the exact state content-addresses to state_hash.
    Whether state_hash actually equals H(state) is the witness's OWN integrity claim (chronicle's job per
    node); the tally only certifies that the pinned witnesses signed this exact hash for this round."""
    sh = core.state_hash({"round": round_id, "state": state})
    return {"witness": witness_id, "round": round_id, "state_hash": sh,
            "sig": signer.sign(_vote_message(witness_id, round_id, sh)), "algo": signer.algo}


def verify_vote(vote, registry):
    """(ok, reason): the voter is pinned AND the signature verifies over (protocol,round,witness,hash)."""
    v = registry.get(vote["witness"])
    if v is None:
        return False, "unknown witness %r (not in pinned registry)" % vote["witness"]
    try:
        if not v.verify(_vote_message(vote["witness"], vote["round"], vote["state_hash"]), vote["sig"]):
            return False, "signature invalid (forged / wrong key)"
    except Exception:
        return False, "signature invalid (malformed)"
    return True, "authentic"


# ----------------------------------------------------------------- the tally (integer, exact)
def observables(counted):
    """Pure numeric observables over the counted votes (one hash per non-equivocating witness)."""
    c = Counter(counted.values())
    n = len(counted)
    if n == 0:
        return {"agreement_ratio": 0.0, "ess_opinions": 0.0, "divergence": 0.0}
    m = max(c.values())
    sum_c = sum(c.values())
    sum_c2 = sum(x * x for x in c.values())
    return {"agreement_ratio": m / n,                        # in (0,1]; 1 == unanimous
            "ess_opinions": (sum_c * sum_c) / sum_c2,        # ESS = (Sum w)^2 / Sum w^2 in [1, n]
            "divergence": (n - m) / n}                       # ghost ratio


def certificate_hash(round_id, counted, quorum_hash, k, n):
    votes_canon = sorted([[w, h] for w, h in counted.items()])
    body = core.canonical_bytes({"protocol": PROTOCOL_VERSION, "round": round_id, "votes": votes_canon,
                                 "quorum_hash": quorum_hash, "k": k, "n": n})
    return hashlib.sha256(body).hexdigest()


def tally(votes, k, registry, round_id=None):
    """Tally a round of votes into a consensus certificate. EXACT integer counting, no float, no tolerance.

      1. authenticate every vote against the pinned registry (unauthenticated -> rejected, never counted);
      2. detect EQUIVOCATION: a witness that signed >=2 distinct hashes for this round is excluded from
         the count and named (the one Byzantine behaviour a tally can catch cheaply);
      3. count one hash per remaining witness; the modal hash h_mode with multiplicity m is the plurality;
      4. CERTIFY iff m >= k; else quorum_hash = None and the fork set is emitted for forensics.

    The GHOST is the dissent residual G = {witnesses whose hash != h_mode}: recorded, localizing the fork,
    and NEVER allowed to flip the certificate -- a lone honest dissenter may be the only correct one when
    the majority colludes, so dissent is preserved, not discarded."""
    if k < 1:
        raise QuorumError("k must be >= 1 (k is the declared quorum threshold, an explicit model cut)")
    authentic, rejected = [], []
    for vote in votes:
        ok, why = verify_vote(vote, registry)
        (authentic.append(vote) if ok else rejected.append({"witness": vote.get("witness"), "reason": why}))

    by_w = {}
    for vote in authentic:
        by_w.setdefault(vote["witness"], set()).add(vote["state_hash"])
    equivocators = sorted(w for w, hs in by_w.items() if len(hs) > 1)

    counted = {}                                             # witness -> single hash (non-equivocators)
    for vote in authentic:
        if vote["witness"] not in equivocators:
            counted[vote["witness"]] = vote["state_hash"]

    c = Counter(counted.values())
    h_mode, m = (c.most_common(1)[0] if c else (None, 0))
    n = len(counted)
    certified = (h_mode is not None and m >= k)
    quorum_hash = h_mode if certified else None
    ghost = {w: h for w, h in counted.items() if h != h_mode}

    return {"round": round_id, "protocol": PROTOCOL_VERSION,
            "certified": certified, "quorum_hash": quorum_hash, "modal_hash": h_mode,
            "agreed": m, "n": n, "k": k,
            "equivocators": equivocators,
            "rejected": rejected,
            "ghost": ghost,                                  # dissent residual {witness: hash}
            "observables": observables(counted),
            "cert_hash": certificate_hash(round_id, counted, quorum_hash, k, n)}
