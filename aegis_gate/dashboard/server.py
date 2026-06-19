# SPDX-License-Identifier: AGPL-3.0-only
"""
aegis_gate/dashboard/server.py — a stdlib-only audit dashboard (no third-party packages).

Two panels, both backed by the workbench primitives (not by mock data):

  Panel A — Replay Court (forensic view). Lists every recorded transfer. /api/verify re-runs
            chronicle.court.verify_chain over ledger.jsonl on this process and reports the exact result.
            If a stored digit is altered, the court names the precise fault (REPLAY drift / CHAIN broken /
            signature mismatch) and the seq it occurred at — this is the live tamper test.

  Panel B — Drift Monitor (self-audit view). /api/drift re-hashes the frozen chronicle cores aegis_gate
            depends on and compares them to selfaudit's PINNED baseline. Any change to a core file forks
            the hash and the panel reports drift. This is honest about scope: it detects core-file change,
            not arbitrary "workspace correctness".

Run:  PYTHONHASHSEED=0 python3 dashboard/server.py [port]   (default 8755)
Open: http://127.0.0.1:8755/
"""
import os, sys, json, hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

_HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(_HERE)
sys.path.insert(0, APP)

from _workbench import verify_chain, frozen_core_files, SELFAUDIT_BASELINE
from app import policy, bank_engine as be
import run_pipeline as R

LEDGER_PATH = os.path.join(APP, "ledger.jsonl")
TEMPLATE = os.path.join(_HERE, "templates", "audit.html")


def _read_ledger():
    if not os.path.exists(LEDGER_PATH):
        return []
    return [json.loads(l) for l in open(LEDGER_PATH) if l.strip()]


def _ledger_rows(ledger):
    rows = []
    for r in ledger:
        f = r["frame"]; inp = f["inputs"]; out = f["outputs"]
        rows.append({
            "seq": f["seq"], "decision_id": f["decision_id"], "approved": bool(out["approved"]),
            "amount": be.dollars(inp["amount_cents"]), "amount_cents": inp["amount_cents"],
            "src": inp["src"], "dst": inp["dst"],
            "reason": (out["reasons"][0] if out["reasons"] else ""),
            "world_H": out["world_H"][:16], "committed_hash": r["committed_hash"][:16],
            "confidence": inp.get("_captured", {}).get("parse_confidence"),
        })
    return rows


def _verify(upto=None):
    ledger = _read_ledger()
    sub = ledger if upto is None else ledger[:upto + 1]
    if not sub:
        return {"ok": False, "reason": "ledger is empty — run run_pipeline.py first", "at": None, "n": 0}
    v = verify_chain(sub, R.INSTITUTION_SECRET, policy.decide, policy.aml_invariant)
    world_H = sub[-1]["frame"]["outputs"]["world_H"] if v.ok else None
    return {"ok": bool(v.ok), "reason": (None if v.ok else v.reason), "at": v.at,
            "n": len(sub), "world_H": world_H}


def _drift():
    baseline = json.load(open(SELFAUDIT_BASELINE))
    drift = []
    current = {}
    for key, path in frozen_core_files():
        h = hashlib.sha256(open(path, "rb").read()).hexdigest()
        current[key] = h
        if key not in baseline:
            drift.append("UNPINNED %s" % key)
        elif baseline[key] != h:
            drift.append("DRIFT %s: baseline %s != current %s" % (key, baseline[key][:12], h[:12]))
    composite = hashlib.sha256(json.dumps(current, sort_keys=True).encode()).hexdigest()
    base_composite = hashlib.sha256(json.dumps({k: baseline[k] for k in current if k in baseline},
                                               sort_keys=True).encode()).hexdigest()
    return {"ok": not drift, "drift": drift, "baseline_H": base_composite[:24], "current_H": composite[:24]}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/":
            try:
                html = open(TEMPLATE, encoding="utf-8").read()
            except FileNotFoundError:
                return self._send(500, "audit.html template missing", "text/plain")
            return self._send(200, html, "text/html; charset=utf-8")
        if u.path == "/api/ledger":
            return self._send(200, json.dumps(_ledger_rows(_read_ledger())))
        if u.path == "/api/verify":
            upto = int(q["seq"][0]) if "seq" in q else None
            return self._send(200, json.dumps(_verify(upto)))
        if u.path == "/api/drift":
            return self._send(200, json.dumps(_drift()))
        return self._send(404, json.dumps({"error": "not found"}))


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8755
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print("AegisGate dashboard on http://127.0.0.1:%d/  (Ctrl-C to stop)" % port)
    print("  ledger: %s  (%d decisions)" % (LEDGER_PATH, len(_read_ledger())))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
