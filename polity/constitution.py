"""
polity/constitution.py — deterministic governance: let the pinned rulesets EVOLVE without breaking custody.

Today the rulesets that `elenchus`, `fuel`, and the policy layers enforce are FROZEN — pinned by content
hash, with no path to change them except editing code. That is safe but brittle: the system rots the moment
a rule is wrong. `polity` adds the missing primitive — a deterministic way to ratify a new ruleset version —
without giving up the chain of custody.

A ruleset is governed only by its CONTENT HASH; `polity` never needs to know the rule semantics. Governors
(a pinned key registry) vote on a proposal; the vote is tallied by `quorum` (exact integer count, no float);
if a k-quorum ratifies, a new **constitution version** is minted that binds to the prior one (a `pact`-style
content-addressed lineage). The active ruleset is whatever the latest ratified version names.

HONEST BOUNDS:
  * It proves the VOTE happened and the tally is exact under the pinned governor keys. It does NOT prove the
    new ruleset is better, correct, or wise. (integrity != truth.)
  * Governor INDEPENDENCE is a trust input (the same Sybil bound as `quorum`): a colluding >= k governing
    majority ratifies a bad rule just as cleanly as a good one. The certificate proves agreement among the
    named keys, nothing more.
  * It governs WHICH content-addressed ruleset is active; it does not execute or validate the rules (that is
    `elenchus`/`fuel`'s job against the hash `polity` ratifies).

Imports quorum + chronicle read-only (Sibling Law).
"""
import os
import sys

_WB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_WB, "chronicle"))
sys.path.insert(0, os.path.join(_WB, "quorum"))
import core                                                  # chronicle/core.py
import tally as Q                                            # quorum/tally.py

PROTOCOL_VERSION = "polity/1"
GENESIS = "0" * 64


# ----------------------------------------------------------------- governors + proposals
def governor_registry(signers):
    """signers: {governor_id: signer}. Returns the PINNED registry {id: verifier} the tally trusts."""
    return Q.build_registry(signers)


def genesis_constitution(ruleset_hash, meta=None):
    """Version 0: the founding ruleset, ratified by fiat (no prior vote). Everything chains from here."""
    rec = {"protocol": PROTOCOL_VERSION, "version": 0, "prev": GENESIS,
           "ruleset_hash": ruleset_hash, "proposal_hash": None, "vote": None, "meta": meta or {}}
    rec["constitution_hash"] = core.state_hash(rec)
    return rec


def propose(prev_constitution, new_ruleset_hash, proposer_id, meta=None):
    """A proposed amendment binding the NEW ruleset hash to the CURRENT constitution."""
    return {"protocol": PROTOCOL_VERSION, "prev": prev_constitution["constitution_hash"],
            "ruleset_hash": new_ruleset_hash, "proposer": proposer_id, "meta": meta or {}}


def proposal_hash(proposal):
    return core.state_hash(proposal)


def _yea_state(ph):
    return {"vote": "ratify", "proposal": ph}


def _nay_state(ph):
    return {"vote": "reject", "proposal": ph}


def _yea_hash(ph):
    # must equal quorum.witness_vote's internal state_hash for a yea ballot
    return core.state_hash({"round": ph, "state": _yea_state(ph)})


def cast(governor_id, signer, proposal, decision="yea"):
    """A governor's signed ballot. 'yea' agrees on the proposal; 'nay' signs a distinct reject hash, so it
    is authenticated and counted as present, but does NOT add to the ratify tally."""
    ph = proposal_hash(proposal)
    state = _yea_state(ph) if decision == "yea" else _nay_state(ph)
    return Q.witness_vote(governor_id, ph, state, signer)


# ----------------------------------------------------------------- ratify (exact quorum) + lineage
def ratify(prev_constitution, proposal, ballots, k, registry):
    """Tally the ballots; if >= k governors agree on RATIFY, mint the next constitution version bound to the
    prior. Returns {ratified, constitution?, certificate, reason?}. Fail-closed: no quorum -> no new version."""
    ph = proposal_hash(proposal)
    cert = Q.tally(ballots, k, registry, round_id=ph)
    if not (cert["certified"] and cert["quorum_hash"] == _yea_hash(ph)):
        return {"ratified": False, "certificate": cert,
                "reason": "ratify quorum not reached (agreed %d of %d, k=%d)" % (cert["agreed"], cert["n"], k)}
    rec = {"protocol": PROTOCOL_VERSION, "version": prev_constitution["version"] + 1,
           "prev": prev_constitution["constitution_hash"], "ruleset_hash": proposal["ruleset_hash"],
           "proposal_hash": ph, "meta": proposal.get("meta", {}),
           "vote": {"agreed": cert["agreed"], "n": cert["n"], "k": k, "cert_hash": cert["cert_hash"]}}
    rec["constitution_hash"] = core.state_hash(rec)
    return {"ratified": True, "constitution": rec, "certificate": cert}


def verify_lineage(chain):
    """Replay a constitution lineage: each version content-addresses correctly, binds to its predecessor,
    and the version index is contiguous. Returns (ok, fault) naming the exact version, or None."""
    prev_hash = GENESIS
    for i, rec in enumerate(chain):
        body = {key: rec[key] for key in rec if key != "constitution_hash"}
        if core.state_hash(body) != rec["constitution_hash"]:
            return False, {"version": rec.get("version"), "reason": "tampered (constitution_hash mismatch)"}
        if rec["prev"] != prev_hash:
            return False, {"version": rec.get("version"), "reason": "lineage broken (prev != prior constitution_hash)"}
        if rec["version"] != i:
            return False, {"version": rec.get("version"), "reason": "version index not contiguous"}
        prev_hash = rec["constitution_hash"]
    return True, None


def active_ruleset(chain):
    """The ruleset hash named by the latest ratified constitution version."""
    return chain[-1]["ruleset_hash"]
