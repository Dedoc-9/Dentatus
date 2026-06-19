# SPDX-License-Identifier: AGPL-3.0-only
"""
AetherManifold/conformance.py — trajectory conformance vectors (the cross-language / native-port oracle).

A vector binds (problem A,B; start X0; learning rate; steps) to the reference outputs: the final trajectory
hash + the Merkle root over per-step hashes. A native (C++/Rust int128) port is conformant iff it reproduces
both. Edge-case problems stress the retraction (near-singular starts, zero-gradient, aggressive step size).
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cores import merkle
import core as chcore
from signing import Ed25519Verifier
import riemann as R
import objective as O

fp = O.fp
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
_BODY = ("schema", "problem", "steps", "eta_num", "eta_den", "final_hash", "merkle_root", "final_defect")


def _problem(name):
    """Edge-case registry. Each returns (A, B, X0, eta=(num,den), steps)."""
    Xstar = [[fp(3, 5), 0], [fp(4, 5), 0], [0, fp(1)]]
    A = O.identity(3); B = R.F.matmul(A, Xstar)
    if name == "converge":
        return A, B, [[fp(1, 2), 0], [fp(1, 2), 0], [0, fp(1)]], (1, 5), 60
    if name == "near_singular":                              # two nearly-parallel start columns
        return A, B, [[fp(1), fp(99, 100)], [0, fp(1, 100)], [fp(1, 100), 0]], (1, 5), 60
    if name == "zero_gradient":                              # start AT the minimum -> trajectory stays
        return A, B, Xstar, (1, 5), 40
    if name == "aggressive_eta":                             # large step size; deterministic regardless
        return A, B, [[fp(1, 2), 0], [fp(1, 2), 0], [0, fp(1)]], (9, 10), 60
    raise ValueError(name)


def make_vector(name, signer=None):
    A, B, X0, (en, ed), steps = _problem(name)
    grad, energy = O.procrustes(A, B)
    res = R.optimize(X0, grad, fp(en, ed), steps, energy)
    body = {"schema": "aethermanifold-conformance/1", "problem": name, "steps": steps,
            "eta_num": en, "eta_den": ed, "final_hash": res["hashes"][-1],
            "merkle_root": merkle.merkle_root(res["hashes"]), "final_defect": res["final_defect"]}
    if signer is not None:
        body = {**body, "signature": signer.sign(chcore.canonical_bytes({k: body[k] for k in _BODY})),
                "algo": signer.algo, "public_material": signer.public_material() if signer.algo == "ed25519" else None}
    return body


def verify_vector(vec, verifier=None):
    A, B, X0, (en, ed), steps = _problem(vec["problem"])
    grad, energy = O.procrustes(A, B)
    res = R.optimize(X0, grad, fp(en, ed), steps, energy)
    if res["hashes"][-1] != vec["final_hash"]:
        return False, "FINAL mismatch (re-run diverged)"
    if merkle.merkle_root(res["hashes"]) != vec["merkle_root"]:
        return False, "MERKLE mismatch"
    if vec.get("signature") is not None:
        v = verifier
        if v is None and vec.get("algo") == "ed25519" and vec.get("public_material"):
            v = Ed25519Verifier(vec["public_material"])
        if v is None:
            return False, "SIGNATURE present, no verifier"
        if not v.verify(chcore.canonical_bytes({k: vec[k] for k in _BODY}), vec["signature"]):
            return False, "SIGNATURE invalid"
    return True, "CONFORMANT"


def export_fixtures():
    os.makedirs(FIXTURES, exist_ok=True)
    out = []
    for name in ("converge", "near_singular", "zero_gradient", "aggressive_eta"):
        vec = make_vector(name)
        with open(os.path.join(FIXTURES, name + ".json"), "w") as fh:
            json.dump(vec, fh, indent=2)
        out.append((name, verify_vector(vec)[0], vec["final_hash"][:16], vec["final_defect"]))
    return out
