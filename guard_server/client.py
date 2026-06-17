"""
guard_server/client.py — agent-side stub for the Policy Enforcement Point.

The agent uses this to ask the server for authorization. It NEVER holds the signing key, so it cannot
fabricate an 'allow'. `verify_verdict` lets the agent (or a downstream auditor) confirm a verdict really
came from the server and is bound to the exact request it submitted.
"""
import json
import urllib.request

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "llm_toolkit"))
import agent_core as core


def make_request(stage, payload, policy_version):
    return {"stage": stage, "payload": payload, "policy_version": policy_version}


def request_verdict(base_url, request, timeout=5.0):
    """POST a request to the PEP; return the server's signed verdict response dict."""
    body = json.dumps(request).encode()
    req = urllib.request.Request(base_url + "/evaluate", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def get_policy(base_url, timeout=5.0):
    with urllib.request.urlopen(base_url + "/policy", timeout=timeout) as r:
        return json.loads(r.read())


def is_allowed(response):
    return response.get("verdict", {}).get("decision") == "allow"


def verify_verdict(response, verifier, expected_request):
    """Independent check: (1) the signature attests the verdict core under the server key, and
    (2) the verdict is bound to the hash of exactly the request we submitted. Both must hold."""
    vcore = response.get("verdict")
    sig = response.get("signature")
    if not vcore or sig is None:
        return False, "no verdict/signature"
    if vcore.get("request_hash") != core.state_hash(expected_request):
        return False, "verdict not bound to this request (request_hash mismatch)"
    if not verifier.verify(core.canonical_bytes(vcore), sig):
        return False, "signature invalid (not from the server key / tampered)"
    return True, "verdict authentic and request-bound"
