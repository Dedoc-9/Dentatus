"""
VeriVerse/viewer/server.py — a minimal, stdlib-only "God Mode" viewer for the verifiable world.

It is NOT a GPU/WASM renderer (that is future work). It serves a top-down heightmap of a deterministic world
and lets you click a chunk to mint + verify its shard live — making "same seed -> same hashes, verifiable by
anyone" visible. Run:  PYTHONHASHSEED=0 python3 viewer/server.py [port]   then open http://127.0.0.1:8799/
"""
import os, sys, json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

_HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(_HERE)
sys.path.insert(0, APP)
sys.path.insert(0, os.path.join(os.path.dirname(APP), "chronicle"))
import world as W
import shards as S


def world_payload(seed, n):
    coords = [(cx, cz) for cz in range(n) for cx in range(n)]
    wshard, _ = S.world_shard(seed, coords)
    chunks = []
    for (cx, cz) in coords:
        ch = W.generate_chunk(seed, cx, cz)
        chunks.append({"coord": [cx, cz], "size": ch["size"], "heights": ch["heights"],
                       "surface": ch["surface"], "chunk_hash": W.chunk_hash(ch)[:16],
                       "feature": ch["feature"]})
    return {"seed": seed, "n": n, "world_root": wshard["root"], "chunks": chunks,
            "sea_level": W.SEA_LEVEL}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else body.encode()
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        if u.path == "/":
            return self._send(200, open(os.path.join(_HERE, "index.html"), encoding="utf-8").read(), "text/html; charset=utf-8")
        if u.path == "/api/world":
            seed = int(q.get("seed", ["98247"])[0]); n = max(1, min(6, int(q.get("n", ["3"])[0])))
            return self._send(200, json.dumps(world_payload(seed, n)))
        if u.path == "/api/verify":
            seed = int(q["seed"][0]); cx = int(q["cx"][0]); cz = int(q["cz"][0])
            shard = S.mint_chunk_shard(seed, cx, cz)
            ok, detail = S.verify_chunk_shard(shard)
            return self._send(200, json.dumps({"ok": ok, "detail": detail, "chunk_hash": shard["chunk_hash"],
                                               "feature": shard["feature"]}))
        return self._send(404, json.dumps({"error": "not found"}))


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8799
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print("VeriVerse viewer on http://127.0.0.1:%d/  (Ctrl-C to stop)" % port)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
