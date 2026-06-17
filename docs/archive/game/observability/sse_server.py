#!/usr/bin/env python3
"""
game/observability/sse_server.py — EXP-605 live SSE reality-stream server (stdlib only).

Serves the MCL dashboard at  /  and a live keyframe+delta reality stream at  /stream .
The game layer talks to the core only via dentatus.api; never imports engine.*.

Run:   PYTHONHASHSEED=0 python game/observability/sse_server.py [port]
Then open http://localhost:<port>/ and click LIVE.
"""
import os, sys, json, time, http.server, socketserver

if os.environ.get("PYTHONHASHSEED") != "0":            # bit-stable addresses require the pin
    os.environ["PYTHONHASHSEED"] = "0"
    os.execv(sys.executable, [sys.executable] + sys.argv)

_HERE = os.path.dirname(os.path.abspath(__file__))
_REALITY = os.path.dirname(os.path.dirname(_HERE))
for _p in (_REALITY, os.path.join(_REALITY, "game")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from dentatus import api                                   # noqa: E402
from observability.stream import encode_reality_stream, sse_format  # noqa: E402

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8642
INTENT = {"title": "imperial_docking_bay",
          "seed": {"density": 1.0, "material": [0.55, 0.57, 0.62], "normal": [0, 0, 1],
                   "curvature": 2.0, "stress": {"axes": [3.0, 2.0, 0.4], "plane": "xy", "tilt_deg": 35}},
          "bbox": [[0, 0, 0], [1, 1, 1]], "zeeman": {"focus": [0.5, 0.5, 0.0]}}


def generate_states(n_equilibrium=6):
    """A live reality: the agency budget ladder (worlds change -> sections pulse) followed by
    equilibrium (same world held -> the stream goes near-silent / heartbeats)."""
    states = []
    for b in [1024, 2048, 512, 256, 128, 64]:
        r = api.observe({"op": "observe", "intent": {**INTENT, "zeeman": {"focus": [0.5, 0.5, 0.0], "budget": b}},
                         "steps": 8, "telemetry": True})
        states.append({"H_state": r["H_state"], "leaves": r["telemetry"]["leaves"]})
    states += [states[-1]] * n_equilibrium                  # equilibrium tail
    return states


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._serve_file("mcl_dashboard.html", "text/html")
        elif self.path == "/stream":
            self._serve_stream()
        else:
            fn = os.path.basename(self.path)
            if os.path.isfile(os.path.join(_HERE, fn)):
                self._serve_file(fn, "application/octet-stream")
            else:
                self.send_error(404)

    def _serve_file(self, name, ctype):
        path = os.path.join(_HERE, name)
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _serve_stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        events = encode_reality_stream(generate_states())
        try:
            for ev, d in events:
                self.wfile.write(sse_format(ev, d).encode())
                self.wfile.flush()
                if ev == "world":
                    time.sleep(0.4)                          # pulse one world per beat
            self.wfile.write(sse_format("end", {}).encode()); self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return


class Threaded(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


if __name__ == "__main__":
    print(f"Dentatus MCL live stream → http://localhost:{PORT}/  (SSE at /stream)")
    Threaded(("", PORT), Handler).serve_forever()
