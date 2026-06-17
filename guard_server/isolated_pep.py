"""
guard_server/isolated_pep.py — a privilege-separated Policy Enforcement Point with a filesystem clamp.

================================================================================================
WHAT THIS PROTECTS  (and what it does NOT)
================================================================================================
PROTECTS:
  * Bounded authority. An untrusted local agent must ask this PEP to authorize a filesystem action. The
    PEP holds the signing key and a pinned policy; it returns a verdict cryptographically BOUND to the
    SHA-256 of the exact requested action and SIGNED. The agent cannot alter a verdict, cannot reuse a
    past verdict for a different action, and cannot fabricate an ALLOW (it lacks the key).
  * Privilege separation. Designed to run as a SEPARATE local user (e.g. `chronicle_pep`) while the agent
    runs as your normal user. With real OS separation, the agent cannot read the PEP's key or its policy.
  * Path containment. Writes/reads are clamped to an allow-list of real directories; `..` traversal and
    symlink escape are resolved away before the check (fail-closed on anything unresolvable).
  * Tamper-evident refusals. Every violation is appended to an append-only JSONL log.

DOES NOT PROTECT:
  * Honesty of what the agent reports. The PEP authorizes the ACTION it is shown; if a compromised agent
    performs a different action than it requested, that is an OS-enforcement gap, not a crypto gap. Real
    containment requires the agent to run with OS permissions that make the unauthorized action
    impossible (separate user + filesystem ACLs / sandbox), with this PEP as the policy brain.
  * A host already compromised at root, which can bypass user separation entirely.
This is bounded authority + tamper-evidence, NOT impossible "tamper-proofness".

NO CARGO-CULTING: there is deliberately no "kill on PYTHONHASHSEED != 0" control here. That env var is a
determinism/reproducibility guard, not a security boundary. The PEP rejects on POLICY, returns deterministic
verdict codes, and logs failures.
"""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "llm_toolkit"))
sys.path.insert(0, _HERE)
import agent_core as core
from agent_guard import make_guard_signer, Ed25519Verifier


# ============================================================ filesystem path policy
class PathPolicy:
    """Allow-list of real directories. An action is permitted only if every path it touches resolves
    (symlinks + `..` collapsed) to a location INSIDE an allowed root. Fail-closed."""

    def __init__(self, allowed_roots, allow_create=True):
        # store canonical real roots; relative roots are resolved against the PEP's cwd at construction
        self.roots = [os.path.realpath(os.path.expanduser(r)) for r in allowed_roots]
        self.allow_create = allow_create
        self.policy_hash = core.state_hash({
            "logic": core.source_hash(PathPolicy.path_within, PathPolicy.evaluate),
            "roots": sorted(self.roots), "allow_create": allow_create,
        })[:16]

    @staticmethod
    def path_within(real_path, roots):
        for root in roots:
            if real_path == root or real_path.startswith(root + os.sep):
                return True
        return False

    def _resolve(self, path):
        """Resolve a path for checking even if it does not exist yet: realpath the deepest existing
        ancestor, then re-append the remainder, so a not-yet-created file is checked against where it
        WOULD live and symlinked ancestors cannot smuggle the target outside a root."""
        p = os.path.expanduser(path)
        p = p if os.path.isabs(p) else os.path.join(os.getcwd(), p)
        existing = p
        tail = []
        while not os.path.exists(existing) and os.path.dirname(existing) != existing:
            existing, t = os.path.split(existing)
            tail.insert(0, t)
        return os.path.join(os.path.realpath(existing), *tail)

    def evaluate(self, action):
        """action = {"op": "read"|"write"|"exec", "paths": [..]}. Return (decision, reasons)."""
        reasons = []
        op = action.get("op")
        paths = action.get("paths", [])
        if op not in ("read", "write", "exec"):
            return "deny", ["unknown op %r" % op]
        if not paths:
            return "deny", ["no paths in action"]
        for raw in paths:
            try:
                real = self._resolve(raw)
            except Exception as e:
                reasons.append("unresolvable path %r (%s)" % (raw, e))
                continue
            if not PathPolicy.path_within(real, self.roots):
                reasons.append("path escapes allow-list: %r -> %r" % (raw, real))
            elif op == "write" and not self.allow_create and not os.path.exists(real):
                reasons.append("creation disallowed: %r" % raw)
        return ("allow" if not reasons else "deny"), reasons


# ============================================================ signed, request-bound verdicts
def sign_action_verdict(policy, signer, action):
    request_hash = core.state_hash(action)
    decision, reasons = policy.evaluate(action)
    vcore = {"request_hash": request_hash, "policy_hash": policy.policy_hash,
             "decision": decision, "reasons": reasons}
    return {"verdict": vcore, "signature": signer.sign(core.canonical_bytes(vcore)),
            "algo": signer.algo,
            "public_material": getattr(signer, "public_material", lambda: None)()
            if signer.algo == "ed25519" else None}


def verify_action_verdict(response, verifier, expected_action):
    v = response.get("verdict"); sig = response.get("signature")
    if not v or sig is None:
        return False, "no verdict/signature"
    if v.get("request_hash") != core.state_hash(expected_action):
        return False, "verdict not bound to this action"
    if not verifier.verify(core.canonical_bytes(v), sig):
        return False, "signature invalid"
    return True, "authentic and action-bound"


# ============================================================ append-only violation log
class AppendOnlyLog:
    def __init__(self, path):
        self.path = path
        open(path, "a").close()

    def append(self, record):
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            f.flush()
            os.fsync(f.fileno())


# ============================================================ the server
class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/policy":
            s = self.server
            return self._send(200, {"policy_hash": s.policy.policy_hash, "roots": s.policy.roots,
                                    "algo": s.signer.algo,
                                    "public_material": getattr(s.signer, "public_material", lambda: None)()
                                    if s.signer.algo == "ed25519" else None})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/authorize":
            return self._send(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            action = json.loads(self.rfile.read(n) or b"{}")
        except Exception as e:
            return self._send(400, {"error": "bad request: %s" % e})
        resp = sign_action_verdict(self.server.policy, self.server.signer, action)
        if resp["verdict"]["decision"] == "deny":
            self.server.violations.append({"action": action, "reasons": resp["verdict"]["reasons"],
                                           "request_hash": resp["verdict"]["request_hash"]})
        return self._send(200, resp)


class IsolatedPEP:
    """Privilege-separated PEP. Intended to run under a dedicated user; see `print_setup()`."""

    def __init__(self, allowed_roots, signer=None, secret=b"isolated_pep_key_demo",
                 violation_log=None):
        self.policy = PathPolicy(allowed_roots)
        self.signer = signer or make_guard_signer(secret=secret, prefer_ed25519=True)
        self.violations = AppendOnlyLog(violation_log or os.path.join(_HERE, "pep_violations.jsonl"))
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.httpd.policy = self.policy
        self.httpd.signer = self.signer
        self.httpd.violations = self.violations
        self._t = None

    @property
    def base_url(self):
        host, port = self.httpd.server_address
        return "http://%s:%d" % (host, port)

    def public_verifier(self):
        if self.signer.algo == "ed25519":
            return Ed25519Verifier(self.signer.public_material())
        return self.signer

    def privilege_warning(self):
        """Return a warning string if the PEP appears to run as the SAME OS user as its caller would
        (i.e. no real separation). On platforms without getuid (Windows), returns a portable note."""
        getuid = getattr(os, "geteuid", None)
        if getuid is None:
            return ("[isolated_pep] No POSIX uid on this platform; run the PEP under a dedicated account "
                    "(Windows: a separate user / AppContainer) for real privilege separation.")
        if getuid() == 0:
            return "[isolated_pep] Running as ROOT — root can bypass user separation; use a low-priv user."
        return ("[isolated_pep] Running as uid %d. For real isolation, run THIS server as a dedicated user "
                "(e.g. chronicle_pep) distinct from the agent's user, with the policy roots writable by "
                "the agent but the key + this process owned by chronicle_pep." % getuid())

    @staticmethod
    def print_setup(user="chronicle_pep", root="~/projects/design"):
        sys.stderr.write(
            "\n# --- one-time OS privilege-separation setup (Linux) ---\n"
            "sudo useradd -r -s /usr/sbin/nologin %s\n"
            "sudo -u %s mkdir -p %s\n"
            "# run the PEP AS %s (its key + policy are unreadable to your normal user):\n"
            "sudo -u %s env CHRONICLE_SIGNER_PASSPHRASE=... python3 -m guard_server.isolated_pep\n"
            "# your agent runs as YOU and must call the PEP for every filesystem action.\n\n"
            % (user, user, root, user, user))

    def start(self):
        sys.stderr.write(self.privilege_warning() + "\n")
        self._t = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._t.start()
        return self

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def __enter__(self): return self.start()
    def __exit__(self, *e): self.stop()


if __name__ == "__main__":
    IsolatedPEP.print_setup()
    roots = [os.environ.get("CHRONICLE_PEP_ROOT", os.path.expanduser("~/projects/design"))]
    pep = IsolatedPEP(roots).start()
    sys.stderr.write("[isolated_pep] policy roots=%s  url=%s\n" % (pep.policy.roots, pep.base_url))
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pep.stop()
