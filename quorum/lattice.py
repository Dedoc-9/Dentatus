"""
quorum/lattice.py — the 2D attestation lattice: quorum (lateral) composed with pact (temporal).

Two orthogonal axes, deliberately NOT collapsed into one number:

  LATERAL  (this sibling): at each round t, k-of-n independently-keyed witnesses must agree on the exact
           state hash. tally() certifies the round and yields its canonical quorum_hash. Residual = the
           dissent ghost (witnesses outvoted at that round).

  TEMPORAL (pact): the sequence of certified quorum_hashes must form an unbroken covenant -- each round's
           certified state cross-attested to the prior round's certified state under a pinned notary key,
           satisfying a precommitted temporal invariant. Residual = a broken covenant link.

A cell (t, w) carries witness w's state hash at round t. A ROW is valid iff it reaches quorum; a COLUMN
(the spine of certified rounds) is valid iff its covenant holds. The lattice is valid iff every row
certifies AND the temporal spine audits clean. The two failure residuals are independent: a round can
reach quorum yet break the temporal rule (lateral OK / temporal fault), or hold the temporal rule on a
round that never reached quorum (which is refused -- you cannot bind an uncertified round).

HONEST BOUND: the notary that signs the temporal spine is a trust input, like every pinned key here. The
lattice proves "a quorum agreed at each round AND the certified rounds form an unbroken covenant" -- not
global truth. A colluding quorum, or a colluding notary, is out of scope by construction. Integrity is
not truth; consensus is not truth; a bound lattice of both is still not truth -- it is a strictly stronger,
fully attributable agreement.

Imports chronicle + pact read-only (Sibling Law). pact/covenant.py self-bootstraps its own path.
"""
import os
import sys
import hashlib

_HERE = os.path.dirname(os.path.abspath(__file__))
_WB = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)                                    # tally.py (this sibling)
sys.path.insert(0, os.path.join(_WB, "chronicle"))
sys.path.insert(0, os.path.join(_WB, "pact"))
import core                                                  # chronicle/core.py
import tally as Q                                            # quorum/tally.py
import covenant as P                                         # pact/covenant.py (cross-attestation)

PROTOCOL_VERSION = "quorum-lattice/1"


class LatticeBreach(Exception):
    pass


def lateral_pass(rounds, k, registry):
    """rounds: ordered list of (round_id, [votes]). Returns the per-round quorum certificates."""
    return [Q.tally(votes, k, registry, round_id=rid) for rid, votes in rounds]


def _round_state(cert):
    """The exact, content-addressable state a certified round contributes to the temporal spine."""
    return {"round": cert["round"], "quorum_hash": cert["quorum_hash"], "agreed": cert["agreed"], "n": cert["n"]}


def temporal_spine(certs, notary_id, notary_signer, pact_registry, temporal_invariant):
    """Bind certified rounds into a pact covenant chain under a pinned notary key. Fail-closed: refuses to
    bind a round that did not certify (you cannot attest agreement that does not exist)."""
    chain = []
    prior = None
    for cert in certs:
        if not cert["certified"]:
            raise LatticeBreach("round %r did not reach quorum (agreed %d < k); cannot bind to spine"
                                % (cert["round"], cert["agreed"]))
        state = _round_state(cert)
        if prior is None:
            r = P.state_receipt(notary_id, state, notary_signer)
            chain.append({"receipt": r})
            prior = r
        else:
            link = P.cross_attest(prior, notary_id, state, notary_signer, temporal_invariant, pact_registry)
            chain.append(link)
            prior = link["receipt"]
    return chain


def lattice_hash(certs, spine):
    """Content address of the whole lattice: every round cert_hash + the temporal spine receipt hashes."""
    body = core.canonical_bytes({
        "protocol": PROTOCOL_VERSION,
        "lateral": [c["cert_hash"] for c in certs],
        "temporal": [l["receipt"]["state_hash"] for l in spine],
    })
    return hashlib.sha256(body).hexdigest()


def evaluate(rounds, k, registry, notary_id, notary_signer, pact_registry, temporal_invariant):
    """Full lattice evaluation. Returns a verdict dict with both axes and the exact fault, if any:

        {ok, certs, spine, lattice_hash, fault}
      fault is None, or {"axis": "lateral", "round": rid, "agreed": m, "k": k}, or
                        {"axis": "temporal", ...pact fault...}.
    """
    certs = lateral_pass(rounds, k, registry)

    # lateral axis: every row must certify
    for c in certs:
        if not c["certified"]:
            return {"ok": False, "certs": certs, "spine": None, "lattice_hash": None,
                    "fault": {"axis": "lateral", "round": c["round"], "agreed": c["agreed"], "k": k,
                              "ghost": list(c["ghost"].keys()), "equivocators": c["equivocators"]}}

    # temporal axis: the certified spine must form an unbroken covenant
    try:
        spine = temporal_spine(certs, notary_id, notary_signer, pact_registry, temporal_invariant)
    except (P.CovenantBreach, LatticeBreach) as e:
        return {"ok": False, "certs": certs, "spine": None, "lattice_hash": None,
                "fault": {"axis": "temporal", "reason": str(e)}}

    inv_map = {notary_id: temporal_invariant}
    ok, fault = P.audit_covenant(spine, pact_registry, inv_map)
    if not ok:
        return {"ok": False, "certs": certs, "spine": spine, "lattice_hash": None,
                "fault": {"axis": "temporal", **fault}}

    return {"ok": True, "certs": certs, "spine": spine,
            "lattice_hash": lattice_hash(certs, spine), "fault": None}
