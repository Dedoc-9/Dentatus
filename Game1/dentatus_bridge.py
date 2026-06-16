"""
dentatus_bridge.py — live Mission-Control bridge for the Tactical Cockpit.

A dependency-free HTTP/SSE server that runs a REAL world through the Dentatus engine and streams its
true telemetry to tactical_cockpit.html. System Calls are executed server-side through the actual
firewall (EXP-509 Citadel / EXP-513 Weissenberg / EXP-515 melt / EXP-522 nucleation), returning a
verified H address. Self-pins PYTHONHASHSEED=0 for bit-perfect determinism.

    python3 dentatus_bridge.py            # then open  http://localhost:8770/

Endpoints:
    GET  /            -> serves tactical_cockpit.html
    GET  /stream      -> text/event-stream : a telemetry frame ~8 Hz
    POST /call        -> {call, synced} -> runs the system call through the engine -> verified result
"""
import os, sys, json, time, math, threading, random

# self-pin determinism (re-exec once with the seed fixed, like the EXP-605 service)
if os.environ.get("PYTHONHASHSEED") != "0":
    os.environ["PYTHONHASHSEED"] = "0"
    os.execv(sys.executable, [sys.executable] + sys.argv)

HERE = os.path.dirname(os.path.abspath(__file__))
# Locate the engine repo (the folder containing the `dentatus` package). On Windows Game1 sits INSIDE
# Reality_Engine (parent); in some layouts they are siblings. Try candidates + DENTATUS_REPO override.
def _find_repo():
    cands = []
    if os.environ.get("DENTATUS_REPO"): cands.append(os.environ["DENTATUS_REPO"])
    parent = os.path.dirname(HERE); grand = os.path.dirname(parent)
    cands += [parent, os.path.join(parent, "Reality_Engine"), os.path.join(grand, "Reality_Engine"), grand]
    for c in cands:
        if c and os.path.isdir(os.path.join(c, "dentatus")):
            return c
    return parent
REPO = _find_repo()
for _p in (REPO, os.path.join(REPO, "game/agency"), os.path.join(REPO, "game/observability")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import numpy as np
from dentatus import core
from phase_change import enact_phase_change_515
from recrystallize import enact_recrystallization_521
from nucleation import enact_oriented_nucleation_522
from sectioned_fiedler import global_fiedler
from composite_witness import composite_address, session_attest, verify_attest, game_sufficient_stats, NonceChain
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SEED = {"hash": "9671566edf7b1103", "bpm": 39, "T": 1.5385, "phase0": 0.873}
BETA, NF, NG, VORT, EPS_REF = 12.0, 148, 396, 0.40, 0.5
PORT = int(os.environ.get("BRIDGE_PORT", "8770"))
# SERVER SECRET — the real moat. NEVER ship this; set it in the deploy environment.
SERVER_SECRET = os.environ.get("DENTATUS_SERVER_SECRET", "DEV_INSECURE_KEY_set_DENTATUS_SERVER_SECRET").encode()
REQUIRE_ATTEST = os.environ.get("DENTATUS_REQUIRE_ATTEST", "0") == "1"   # gate: commits need a composite frame


def _glass_stalk():
    s = np.zeros(18); s[0:4] = [1.0, 0.55, 0.57, 0.62]; s[8:11] = [0, 0, 1]
    s[12:18] = [0.6, -0.1, -0.5, 0.3, 0.1, 0.2]               # moderate anisotropy ~ glass
    return s


def _leaf_world():
    L = []
    for x in range(12):
        for y in range(6):
            for z in range(2):
                L.append({"center": (float(x), float(y), float(z)), "size": (1.0, 1.0, 1.0)})
    return L


class World:
    def __init__(self):
        self.lock = threading.Lock()
        self.wi = 0.12
        self.stalk = _glass_stalk()
        self.frame = 0
        self.t0 = time.time()
        self.leaves = _leaf_world()
        self.fiedler = self._compute_fiedler(0.0)
        self.last_fied = 0.0
        self.last_event = "BRIDGE ONLINE · spectral split locked"
        self.last_event_bad = False
        self.cmdlog = []                                   # event-sourced: each commit's game sufficient-stats
        self.session = os.environ.get("DENTATUS_SESSION", "bridge-default")
        self.nonces = NonceChain(self.session)             # EXP-528 rolling nonce-chain (replay immunity)

    def chi(self):
        return core.material_compliance_chi_514(stalk=self.stalk)["chi"]

    def _compute_fiedler(self, shear):
        # shear displaces blob B in x -> the bisection can shift under stress (live deformation)
        L = []
        for lf in self.leaves:
            cx, cy, cz = lf["center"]
            if cx >= 6: cx += shear * 0.35
            L.append({"center": (cx, cy, cz), "size": lf["size"]})
        fied, edges, ctr, siz = global_fiedler(L)
        sign = np.sign(fied); sign[sign == 0] = 1
        red = int((sign > 0).sum()); blue = int((sign < 0).sum())
        cut = [[int(i), int(j)] for (i, j) in edges if sign[i] != sign[j]]
        nodes = [{"x": float(ctr[i][0]), "y": float(ctr[i][1]), "z": float(ctr[i][2]), "s": int(sign[i])}
                 for i in range(len(L))]
        return {"red": red, "blue": blue, "fault_edges": len(cut), "total_edges": len(edges),
                "nodes": nodes, "cut": cut}

    def pulse(self):
        t = time.time() - self.t0
        ph = ((t / SEED["T"]) + SEED["phase0"]) % 1.0
        return ph, math.cos(2 * math.pi * ph)

    def world_H(self, admissible):
        if not admissible:
            return None
        cl = core.Claim(provenance=core.Provenance(parent_ids=(), operator_id="bridge", timestamp=core.now_iso()),
                        payload="world", stalk=self.stalk, t=self.frame)
        mu = core.MuState(t=self.frame, claims={cl.id: cl}, entailments={}, active=frozenset([cl.id]),
                          S=np.zeros(18), alpha=0.5)
        mu.seal(); return mu.H[:16]

    def tick(self):
        with self.lock:
            self.frame += 1
            t = time.time() - self.t0
            # tectonic creep + noise; melted material relaxes shear, ordered material accrues it
            drift = 0.0011 + math.sin(t * 0.6) * 0.0016 + (random.random() - 0.5) * 0.0009
            self.wi = max(0.05, min(0.5, self.wi + drift))
            if t - self.last_fied > 1.6:                      # recompute the real Fiedler on a slow cadence
                self.fiedler = self._compute_fiedler(self.wi)
                self.last_fied = t

    def telem(self):
        with self.lock:
            ph, pv = self.pulse()
            chi = self.chi()
            bc = core.bethe_citadel_strain_512(BETA, self.wi * VORT, NF, NG, vorticity=VORT, chi=chi)
            melt = EPS_REF * chi
            admissible = bc["dS_cit"] >= 0.0
            return {"t": round(time.time() - self.t0, 3), "frame": self.frame,
                    "wi": round(self.wi, 4), "chi": round(chi, 4), "dS": round(bc["dS_cit"], 3),
                    "melt_thresh": round(melt, 4), "prox": round(self.wi / melt, 4),
                    "critical": bool(self.wi / melt >= 0.90),
                    "H_verified": self.world_H(admissible), "admissible": admissible,
                    "pulse_ph": round(ph, 4), "pulse_val": round(pv, 4),
                    "fiedler": {"red": self.fiedler["red"], "blue": self.fiedler["blue"],
                                "fault_edges": self.fiedler["fault_edges"]},
                    "event": self.last_event, "event_bad": self.last_event_bad,
                    "bpm": SEED["bpm"], "seed": SEED["hash"], "eps_ref": EPS_REF}

    def fiedler_full(self):
        with self.lock:
            return self.fiedler

    def do_call(self, name, synced, game_stats=None):
        with self.lock:
            # ATTESTATION GATE (L1 commit boundary): the game MUST contribute its sufficient-stats
            # into the verified frame; the server binds + signs it. The engine core is untouched.
            if REQUIRE_ATTEST and not game_stats:
                self.last_event = 'REJECTED · no composite frame (game sufficient-stats required)'
                self.last_event_bad = True
                return {'accepted': False, 'call': name, 'reason': 'no_composite_frame',
                        'H_verified': None, 'event': self.last_event}
            pv = 1.0 if synced else self.pulse()[1]
            order = 6 if name == "Geodesic_Melt_515" else 7
            E = BETA * (1 + 0.6 * pv); Hin = 2 * math.sqrt(2.7 * max(E, 0)) / math.log(2)
            tax = order - Hin                                  # bits levied on the Citadel budget
            chi0 = self.chi()
            if tax > chi0 * 0 and (order - Hin) > 0:           # tax positive -> Citadel breach path
                # (tax>0 means the order exceeds available H_in at this pulse -> rejected)
                self.last_event = "CITADEL BREACH · %s tax %.2f bits — REJECTED" % (name, tax)
                self.last_event_bad = True
                self.wi = min(0.5, self.wi + 0.05)
                return {"accepted": False, "call": name, "tax": round(tax, 3), "chi": round(chi0, 4),
                        "H_verified": None, "event": self.last_event}
            # admitted -> run the REAL engine operator
            if name == "Geodesic_Melt_515":
                ns, w = enact_phase_change_515(self.stalk, BETA, self.wi * VORT, NF, NG, vorticity=VORT, mode="total")
                if w["status"] == "melted":
                    self.stalk = np.asarray(ns, float)
                self.wi = max(0.05, self.wi - 0.04)
            else:  # Oriented_Nucleation_522
                if chi0 > 0.95:
                    ax = np.array([1.0, 0.4, 0.2]); ax /= np.linalg.norm(ax)
                    symL = 0.3 * np.outer(ax, ax) - 0.05 * np.eye(3)
                    ns, w = enact_oriented_nucleation_522(self.stalk, symL, BETA, self.wi * VORT, NF, NG, vorticity=VORT)
                else:
                    ns, w = enact_recrystallization_521(self.stalk, BETA, self.wi * VORT, NF, NG, vorticity=VORT)
                if w.get("status") in ("nucleated", "recrystallized"):
                    self.stalk = np.asarray(ns, float)
            chi1 = self.chi()
            Hv = self.world_H(True) or "%016x" % (self.frame)
            # bind the game frame into the verified identity (composite) and server-sign it (attestation)
            gstats = game_stats or {"call": name, "chi": round(chi1, 6), "wi": round(self.wi, 6), "frame": self.frame}
            seq, nonce = self.nonces.issue(Hv)                 # EXP-528: rolling head binds this commit
            comp = composite_address(Hv, gstats, nonce=nonce)
            attest = session_attest(Hv, gstats, SERVER_SECRET, nonce=nonce)
            self.cmdlog.append({"frame": self.frame, "call": name, "game": game_sufficient_stats(gstats),
                                "H": Hv, "composite": comp, "seq": seq, "nonce": nonce})   # logged -> replay reproduces nonce
            self.last_event = "%sCOMMIT %s · tax %.2f bits · χ %.2f→%.2f · ⊕%s" % (("SYNCED · " if synced else ""), name, tax, chi0, chi1, comp[:8])
            self.last_event_bad = False
            return {"accepted": True, "call": name, "tax": round(tax, 3), "chi": round(chi1, 4),
                    "H_verified": Hv, "composite": comp, "attestation": attest,
                    "seq": seq, "nonce": nonce, "event": self.last_event}


WORLD = World()
def _ticker():
    while True:
        WORLD.tick(); time.sleep(0.12)
threading.Thread(target=_ticker, daemon=True).start()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()
    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index"):
            try:
                with open(os.path.join(HERE, "tactical_cockpit.html"), "rb") as f:
                    body = f.read()
                self.send_response(200); self.send_header("Content-Type", "text/html"); self._cors()
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            except Exception as e:
                self.send_response(500); self.end_headers(); self.wfile.write(str(e).encode())
            return
        if self.path == "/fiedler":
            body = json.dumps(WORLD.fiedler_full()).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json"); self._cors()
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        if self.path == "/stream":
            self.send_response(200); self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache"); self.send_header("Connection", "keep-alive"); self._cors()
            self.end_headers()
            try:
                while True:
                    frame = json.dumps(WORLD.telem())
                    self.wfile.write(("data: " + frame + "\n\n").encode()); self.wfile.flush()
                    time.sleep(0.12)
            except Exception:
                return
        self.send_response(404); self.end_headers()
    def do_POST(self):
        if self.path == "/call":
            n = int(self.headers.get("Content-Length", "0"))
            req = json.loads(self.rfile.read(n) or b"{}")
            res = WORLD.do_call(req.get("call"), bool(req.get("synced")), req.get("game_stats"))
            body = json.dumps(res).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json"); self._cors()
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        self.send_response(404); self.end_headers()


if __name__ == "__main__":
    print("DENTATUS BRIDGE · live mission control")
    print("  engine repo : %s" % REPO)
    print("  open        : http://localhost:%d/" % PORT)
    print("  stream      : http://localhost:%d/stream   (SSE)" % PORT)
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
