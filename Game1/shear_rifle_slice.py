"""
shear_rifle_slice.py — First Playable Combat Core (the "Shear-Rifle") over Dentatus.

Two-clock tactical FPS slice. The SERVER is the authoritative Truth Tick (~12 Hz): it owns a grid of
material tiles, resolves every shot as a real engine phase-transition, advances a verified world hash,
HMAC-signs it, and logs it. The CLIENT (shear_rifle_viewport.html) renders at display rate with local
prediction and reconciles to this stream.

A SHOT is not a raycast. POST /call/shear_fire injects Weissenberg shear `Wi` into a target tile;
the server runs the Bethe-Citadel firewall (EXP-509/512); on a survivable breach it drives the
volume-preserving anisotropy melt (EXP-515), the tile's compliance `χ` rises (solid→glass→fluid), the
Fiedler structural fault (weighted by stiffness) re-routes through the weakened material, and H_t
advances. Cheat-proof: only the server (holding SERVER_SECRET) mints the attested receipt.

    python3 shear_rifle_slice.py          # then open  http://localhost:8780/

Endpoints:  GET /  (viewport) · GET /arena (geometry) · GET /stream (SSE 12 Hz) · POST /call/shear_fire
"""
import os, sys, json, time, math, threading, random, hashlib
if os.environ.get("PYTHONHASHSEED") != "0":
    os.environ["PYTHONHASHSEED"] = "0"; os.execv(sys.executable, [sys.executable] + sys.argv)
HERE = os.path.dirname(os.path.abspath(__file__))
def _find_repo():
    p = os.path.dirname(HERE); g = os.path.dirname(p)
    for c in (os.environ.get("DENTATUS_REPO"), p, os.path.join(p, "Reality_Engine"), os.path.join(g, "Reality_Engine"), g):
        if c and os.path.isdir(os.path.join(c, "dentatus")): return c
    return p
REPO = _find_repo()
for _p in (REPO, os.path.join(REPO, "game/agency"), os.path.join(REPO, "game/observability")):
    if _p not in sys.path: sys.path.insert(0, _p)
import numpy as np
from dentatus import core
from phase_change import enact_phase_change_515
from recrystallize import enact_recrystallization_521
from nucleation import enact_oriented_nucleation_522
from composite_witness import composite_address, session_attest, game_sufficient_stats
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SEED = {"hash": "9671566edf7b1103", "bpm": 39, "T": 1.5385, "phase0": 0.873}
BETA, NF, NG, VORT, EPS_REF = 12.0, 64, 96, 0.40, 0.5
GX, GY = 8, 6                                       # arena = 48 tiles
TICK_HZ = 10.0                                      # Truth Tick (directive: 10 Hz)
FOCUS_R = 2.2                                       # tiles within this radius of focus = FULL_VALID; beyond = LOD_RELAXED
PORT = int(os.environ.get("SHEAR_PORT", "8780"))
SERVER_SECRET = os.environ.get("DENTATUS_SERVER_SECRET", "DEV_INSECURE_KEY").encode()


def _solid_stalk():
    s = np.zeros(18); s[0:4] = [1.0, 0.55, 0.57, 0.62]; s[8:11] = [0, 0, 1]
    s[12:18] = [0.9, -0.3, -0.6, 0.0, 0.0, 0.0]     # moderate solid (χ~0.25): resists 1 shot, breaks under sustained fire
    return s


class Arena:
    def __init__(self):
        self.lock = threading.Lock()
        self.t0 = time.time(); self.frame = 0
        self.tiles = [{"id": y * GX + x, "gx": x, "gy": y, "stalk": _solid_stalk(), "wi": 0.06,
                       "hit": 0.0} for y in range(GY) for x in range(GX)]
        self.signs = self._fiedler()
        self.log = []
        self.last = "ARENA ONLINE · 48 tiles solid"
        self.focus = (GX / 2.0 - 0.5, GY - 0.5)         # player vantage (near edge) -> drives the Integrity Axis

    def chi(self, t):
        return float(core.material_compliance_chi_514(stalk=t["stalk"])["chi"])

    def _tileH(self, t):
        return hashlib.sha256(np.round(t["stalk"], 6).tobytes()).hexdigest()[:16]

    def vclass(self, t):
        d = math.hypot(t["gx"] - self.focus[0], t["gy"] - self.focus[1])
        return "FULL_VALID" if d <= FOCUS_R else "LOD_RELAXED"

    def vaddr(self, t):
        # INTEGRITY AXIS (EXP-523): FULL_VALID -> tileH ; LOD_RELAXED -> distinct address (no resolution laundering)
        h = self._tileH(t); vc = self.vclass(t)
        if vc == "FULL_VALID":
            return h
        return hashlib.sha256(("\x1f".join([h, vc, "exp523-v1"])).encode()).hexdigest()[:16]

    def _fiedler(self):
        # weighted grid Laplacian: edge weight = min stiffness (1-χ). Melted tiles = weak links,
        # so the structural fault re-routes THROUGH the damage. 48 nodes -> sub-ms.
        n = len(self.tiles); Lap = np.zeros((n, n)); stiff = [max(1e-3, 1.0 - self.chi(t)) for t in self.tiles]
        def idx(x, y): return y * GX + x
        for y in range(GY):
            for x in range(GX):
                i = idx(x, y)
                for dx, dy in ((1, 0), (0, 1)):
                    nx, ny = x + dx, y + dy
                    if nx < GX and ny < GY:
                        j = idx(nx, ny); w = min(stiff[i], stiff[j])
                        Lap[i, i] += w; Lap[j, j] += w; Lap[i, j] -= w; Lap[j, i] -= w
        w, v = np.linalg.eigh(Lap); order = np.argsort(w)
        f = v[:, order[1]] if n > 1 else np.zeros(n)
        sg = np.sign(f); sg[sg == 0] = 1
        return [int(x) for x in sg]

    def pulse(self):
        t = time.time() - self.t0; ph = ((t / SEED["T"]) + SEED["phase0"]) % 1.0
        return ph, math.cos(2 * math.pi * ph)

    def world_H(self):
        claims = {}
        for t in self.tiles:
            cl = core.Claim(provenance=core.Provenance(parent_ids=(), operator_id="tile%d" % t["id"], timestamp=core.now_iso()),
                            payload="t%d" % t["id"], stalk=t["stalk"], t=self.frame)
            claims[cl.id] = cl
        mu = core.MuState(t=self.frame, claims=claims, entailments={}, active=frozenset(claims.keys()),
                          S=np.zeros(18), alpha=0.5)
        mu.seal(); return mu.H[:16]

    def phase_of(self, chi):
        return "solid" if chi < 0.3 else ("glass" if chi < 0.7 else "fluid")

    def tick(self):
        with self.lock:
            self.frame += 1
            for t in self.tiles:
                t["wi"] = max(0.06, t["wi"] * 0.94)         # shear relaxes (the manifold heals toward rest)
                t["hit"] *= 0.82                            # hit-flash decay
            if self.frame % 8 == 0:                          # recolor the fault a few Hz (cheap)
                self.signs = self._fiedler()

    def shear_fire(self, section, wi_inj, synced, game_stats=None, focus=None):
        with self.lock:
            if focus is not None and focus[0] is not None and focus[1] is not None:
                self.focus = (float(focus[0]), float(focus[1]))
            if section is None or section < 0 or section >= len(self.tiles):
                return {"accepted": False, "reason": "no_target"}
            t = self.tiles[section]
            chi0 = self.chi(t)
            t["wi"] = min(1.2, t["wi"] + float(wi_inj)); t["hit"] = 1.0
            pv = 1.0 if synced else self.pulse()[1]
            beta_eff = BETA * (1 + 0.6 * pv)
            bc = core.bethe_citadel_strain_512(beta_eff, t["wi"] * VORT, NF, NG, vorticity=VORT, chi=chi0)
            melt_thresh = EPS_REF * chi0; prox = t["wi"] / melt_thresh
            melted = False
            if bc["dS_cit"] < 0 and bc["survivable_by_material"]:
                ns, w = enact_phase_change_515(t["stalk"], beta_eff, t["wi"] * VORT, NF, NG,
                                               vorticity=VORT, mode="minimal")
                if w["status"] == "melted":
                    t["stalk"] = np.asarray(ns, float); melted = True
            chi1 = self.chi(t)
            self.signs = self._fiedler()                    # fault re-routes immediately on a melt
            Hv = self.world_H()
            gs = game_stats or {"section": section, "chi": round(chi1, 6), "wi": round(t["wi"], 6), "frame": self.frame}
            comp = composite_address(Hv, gs); attest = session_attest(Hv, gs, SERVER_SECRET)
            self.log.append({"frame": self.frame, "section": section, "wi": round(t["wi"], 4),
                             "melted": melted, "H": Hv, "composite": comp})
            verb = "MELT" if melted else ("BREACH" if bc["dS_cit"] < 0 else "HIT")
            self.last = "SHEAR %s tile %d · Wi %.2f · χ %.2f→%.2f · ⊕%s" % (verb, section, t["wi"], chi0, chi1, comp[:6])
            return {"accepted": True, "section": section, "verdict": verb, "melted": melted,
                    "dS_cit": round(bc["dS_cit"], 3), "wi": round(t["wi"], 4), "prox": round(prox, 3),
                    "chi": round(chi1, 4), "phase": self.phase_of(chi1),
                    "H_verified": Hv, "composite": comp, "attestation": attest, "event": self.last}

    def anneal(self, section, synced, game_stats=None, focus=None):
        with self.lock:
            if focus is not None and focus[0] is not None and focus[1] is not None:
                self.focus = (float(focus[0]), float(focus[1]))
            if section is None or section < 0 or section >= len(self.tiles):
                return {"accepted": False, "reason": "no_target"}
            t = self.tiles[section]; chi0 = self.chi(t)
            if chi0 <= 0.30:
                return {"accepted": True, "section": section, "verdict": "SOLID", "chi": round(chi0, 4),
                        "phase": self.phase_of(chi0), "event": "tile %d already solid cover" % section}
            beta_eff = BETA * (1 + 0.6 * (1.0 if synced else self.pulse()[1]))
            t["wi"] = max(0.06, t["wi"] * 0.5)                # annealing relaxes shear
            if chi0 >= 0.999:                                 # fully amorphous (total melt) -> ORIENTED NUCLEATION (EXP-522)
                ax = np.array([1.0, 0.4, 0.2]); ax /= np.linalg.norm(ax)
                symL = 0.3 * np.outer(ax, ax) - 0.05 * np.eye(3)
                ns, w = enact_oriented_nucleation_522(t["stalk"], symL, beta_eff, t["wi"] * VORT, NF, NG, vorticity=VORT)
                op = "Oriented_Nucleation_522"
            else:                                             # residual order -> RE-CRYSTALLISE (EXP-521)
                ns, w = enact_recrystallization_521(t["stalk"], beta_eff, t["wi"] * VORT, NF, NG, vorticity=VORT)
                op = "Re_crystallization_521"
            re = w.get("status") in ("nucleated", "recrystallized")
            if re:
                t["stalk"] = np.asarray(ns, float)
            chi1 = self.chi(t); self.signs = self._fiedler(); Hv = self.world_H()
            gs = game_stats or {"section": section, "chi": round(chi1, 6), "op": op}
            comp = composite_address(Hv, gs); attest = session_attest(Hv, gs, SERVER_SECRET)
            verb = "ANNEAL" if re else ("HOLD" if w.get("status") in ("hold", "amorphous_hold", "no_orienting_field") else "HOLD")
            self.log.append({"frame": self.frame, "section": section, "op": op, "anneal": re, "H": Hv})
            self.last = "%s tile %d · %s · χ %.2f→%.2f · ⊕%s" % (verb, section, op, chi0, chi1, comp[:6])
            return {"accepted": True, "section": section, "verdict": verb, "op": op, "annealed": re,
                    "chi": round(chi1, 4), "phase": self.phase_of(chi1), "H_verified": Hv,
                    "composite": comp, "attestation": attest, "event": self.last}

    def arena(self):
        with self.lock:
            return {"GX": GX, "GY": GY, "tiles": [{"id": t["id"], "gx": t["gx"], "gy": t["gy"]} for t in self.tiles]}

    def telem(self):
        with self.lock:
            ph, pv = self.pulse(); out = []
            red = blue = 0
            for i, t in enumerate(self.tiles):
                chi = self.chi(t); sg = self.signs[i]
                red += sg > 0; blue += sg < 0
                mt = EPS_REF * chi; prox = t["wi"] / mt
                vc = self.vclass(t)
                out.append({"id": t["id"], "chi": round(chi, 3), "wi": round(t["wi"], 3),
                            "phase": self.phase_of(chi), "prox": round(prox, 3),
                            "critical": bool(prox >= 0.9), "sign": sg, "hit": round(t["hit"], 3),
                            "vclass": vc, "vaddr": self.vaddr(t)})
            full = sum(1 for t in self.tiles if self.vclass(t) == "FULL_VALID")
            return {"frame": self.frame, "t": round(time.time() - self.t0, 2), "tiles": out,
                    "full_valid": int(full), "lod_relaxed": int(len(self.tiles) - full),
                    "focus": [round(self.focus[0], 2), round(self.focus[1], 2)],
                    "H_verified": self.world_H(), "pulse_ph": round(ph, 4), "pulse_val": round(pv, 4),
                    "red": int(red), "blue": int(blue), "event": self.last, "bpm": SEED["bpm"], "seed": SEED["hash"]}


WORLD = Arena()
def _ticker():
    dt = 1.0 / TICK_HZ
    while True:
        WORLD.tick(); time.sleep(dt)
threading.Thread(target=_ticker, daemon=True).start()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*"); self.send_header("Access-Control-Allow-Headers", "Content-Type")
    def _json(self, obj, code=200):
        b = json.dumps(obj).encode(); self.send_response(code)
        self.send_header("Content-Type", "application/json"); self._cors()
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_OPTIONS(self): self.send_response(204); self._cors(); self.end_headers()
    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index"):
            try:
                with open(os.path.join(HERE, "shear_rifle_viewport.html"), "rb") as f: body = f.read()
                self.send_response(200); self.send_header("Content-Type", "text/html"); self._cors()
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            except Exception as e:
                self.send_response(500); self.end_headers(); self.wfile.write(str(e).encode())
            return
        if self.path == "/arena": return self._json(WORLD.arena())
        if self.path == "/stream":
            self.send_response(200); self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache"); self.send_header("Connection", "keep-alive"); self._cors(); self.end_headers()
            try:
                while True:
                    self.wfile.write(("data: " + json.dumps(WORLD.telem()) + "\n\n").encode()); self.wfile.flush()
                    time.sleep(1.0 / TICK_HZ)
            except Exception:
                return
        self.send_response(404); self.end_headers()
    def do_POST(self):
        if self.path == "/call/shear_fire":
            n = int(self.headers.get("Content-Length", "0")); req = json.loads(self.rfile.read(n) or b"{}")
            return self._json(WORLD.shear_fire(req.get("section"), req.get("wi", 0.05), bool(req.get("synced")), req.get("game_stats"), req.get("focus")))
        if self.path == "/call/anneal":
            n = int(self.headers.get("Content-Length", "0")); req = json.loads(self.rfile.read(n) or b"{}")
            return self._json(WORLD.anneal(req.get("section"), bool(req.get("synced")), req.get("game_stats"), req.get("focus")))
        self.send_response(404); self.end_headers()


if __name__ == "__main__":
    print("DENTATUS · SHEAR-RIFLE SLICE  (two-clock: %g Hz truth tick)" % TICK_HZ)
    print("  arena %dx%d=%d tiles · open http://localhost:%d/" % (GX, GY, GX * GY, PORT))
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
