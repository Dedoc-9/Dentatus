"""
guard_server/policy_server.py — a localhost Policy Enforcement Point (PEP).

The PEP holds the signing key and the pinned policy BEHIND a process boundary the agent calls but does not
control. The agent POSTs a request; the server evaluates it against its single pinned policy and returns a
verdict that is (a) bound to the SHA-256 of the request and (b) signed. Therefore:

    the agent cannot obtain a valid 'allow' for a request the policy would deny,
    and cannot forge any verdict without the server's key.

WHAT THIS IS / IS NOT (honest scope — no "diamond-hard / unbypassable" claims):
  * IS: out-of-process enforcement + server-pinned policy version + signed, request-bound verdicts. With
    Ed25519 a third party verifies a verdict using only the public key and cannot forge one.
  * IS NOT: OS/container/network isolation, authn of the caller, rate limiting, or TLS. This is a
    reference PEP on loopback. Real deployments add those layers; the cryptographic property above holds
    regardless of them.

Verdict (the signed core, deterministic — no clock):
    {request_hash, policy_version, policy_hash, decision, reasons}
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import policy as P
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "llm_toolkit"))
import agent_core as core
from agent_guard import make_guard_signer, Ed25519Verifier


def sign_verdict(policy, signer, request):
    """Pure verdict construction: evaluate, bind to the request hash, and sign the canonical core."""
    request_hash = core.state_hash(request)
    decision, reasons = policy.evaluate(request.get("stage"), request.get("payload", {}))
    vcore = {
        "request_hash": request_hash,
        "policy_version": policy.version,
        "policy_hash": policy.policy_hash,
        "decision": decision,
        "reasons": reasons,
    }
    signature = signer.sign(core.canonical_bytes(vcore))
    return {
        "verdict": vcore,
        "signature": signature,
        "algo": signer.algo,
        # only safe to publish for asymmetric backends; None for HMAC (verifier must hold the secret)
        "public_material": getattr(signer, "public_material", lambda: None)() if signer.algo == "ed25519" else None,
    }


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):            # quiet
        pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/policy":
            pol = self.server.policy
            return self._send(200, {"policy_version": pol.version, "policy_hash": pol.policy_hash,
                                    "algo": self.server.signer.algo,
                                    "public_material": getattr(self.server.signer, "public_material", lambda: None)()
                                    if self.server.signer.algo == "ed25519" else None})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/evaluate":
            return self._send(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            request = json.loads(self.rfile.read(n) or b"{}")
        except Exception as e:
            return self._send(400, {"error": "bad request: %s" % e})
        # The server enforces ITS pinned policy version; a client-supplied version is advisory only.
        return self._send(200, sign_verdict(self.server.policy, self.server.signer, request))


class PolicyServer:
    """Wraps a ThreadingHTTPServer bound to a free loopback port. Use as a context manager in demos/tests."""

    def __init__(self, policy=None, signer=None, secret=b"guard_server_pep_key_demo"):
        self.policy = policy or P.Policy()
        self.signer = signer or make_guard_signer(secret=secret, prefer_ed25519=True)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.httpd.policy = self.policy
        self.httpd.signer = self.signer
        self._t = None

    @property
    def base_url(self):
        host, port = self.httpd.server_address
        return "http://%s:%d" % (host, port)

    def public_verifier(self):
        """A verifier an auditor can use: Ed25519 public key, or the HMAC signer itself (key-holder only)."""
        if self.signer.algo == "ed25519":
            return Ed25519Verifier(self.signer.public_material())
        return self.signer

    def start(self):
        self._t = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._t.start()
        return self

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()
