"""
collider_arena.py — Two-Player Contested Arena over Dentatus (fork of shear_rifle_slice).

The single-player slice resolves each shot synchronously. The collider proves CONTESTED TRUTH:
two authoritative combatants whose intents are RESOLVED TOGETHER at the 10 Hz Truth Tick.

Core architectural change (the only one that matters): intents are not resolved on arrival. POST
/call/{shear_fire,anneal} ENQUEUES an intent; tick() drains the queue, groups by tile, and resolves
each contested tile EXACTLY ONCE per tick by netting the stacked stress. There is no lock contention,
no first-come-first-served queue, no rollback — concurrency is race-free by construction because the
commit boundary is the tick, not the socket.

Two faithful mechanics ride on that:
  1. Dual vantage (EXP-523). A tile's validity class is computed per player from each player's own
     focus. Tile 30 can be FULL_VALID for A (close) and LOD_RELAXED for B (far) at the same instant.
  2. LOD tax. Firing/annealing a tile you have NOT verified at fine resolution delivers less precise
     energy: effective stress is scaled by RELAX_EFF<1 when your vantage of the target is LOD_RELAXED.
     This is the "uncertainty" cost of acting on a coarse address — not black fog, a resolution barrier.

Honest bounds (see the response): the "optimistic rebase" is BOUNDED (REBASE_WINDOW ticks); intents
older than the window are rejected, not re-proved into deep history. Net resolution is scalar stress
superposition, not quantum superposition.

    python3 collider_arena.py        # open  http://localhost:8781/?player=A   and  /?player=B
"""
import os, sys, json, time, math, threading, hashlib
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
from composite_witness import composite_address, session_attest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SEED = {"hash": "9671566edf7b1103", "bpm": 39, "T": 1.5385, "phase0": 0.873}
BETA, NF, NG, VORT, EPS_REF = 12.0, 64, 96, 0.40, 0.5
GX, GY = 8, 6
TICK_HZ = 10.0
FOCUS_R = 2.2
RELAX_EFF = 0.45            # LOD tax: stress delivered to an un-verified (LOD_RELAXED) tile is attenuated
ANNEAL_BASE = 0.06         # ordering stress contributed by one anneal intent (matches one default shear)
ANNEAL_GAIN = 1.0          # how strongly anneal ordering subtracts from the shear (wi) channel
REBASE_WINDOW = 3          # bounded optimistic rebase: intents older than this many ticks are rejected
PORT = int(os.environ.get("COLLIDER_PORT", "8781"))
SERVER_SECRET = os.environ.get("DENTATUS_SERVER_SECRET", "DEV_INSECURE_KEY").encode()


def _solid_stalk():
    s = np.zeros(18); s[0:4] = [1.0, 0.55, 0.57, 0.62]; s[8:11] = [0, 0, 1]
    s[12:18] = [0.9, -0.3, -0.6, 0.0, 0.0, 0.0]
    return s


class Collider:
    def __init__(self):
        self.lock = threading.Lock()
        self.t0 = time.time(); self.frame = 0
        self.tiles = [{"id": y * GX + x, "gx": x, "gy": y, "stalk": _solid_stalk(), "wi": 0.06, "hit": 0.0}
                      for y in range(GY) for x in range(GX)]
        self.foc = {"A": (1.5, GY - 0.5), "B": (GX - 1.5, GY - 0.5)}   # A near-left, B near-right
        self.pending = []
        self.resolutions = []
        self.signs = self._fiedler()
        self.log = []
        self.stale = 0
        self.last = "COLLIDER ONLINE · 48 tiles · 2 vantages"

    # ---- geometry / material ----
    def chi(self, t): return float(core.material_compliance_chi_514(stalk=t["stalk"])["chi"])
    def _tileH(self, t): return hashlib.sha256(np.round(t["stalk"], 6).tobytes()).hexdigest()[:16]
    def phase_of(self, chi): return "solid" if chi < 0.3 else ("glass" if chi < 0.7 else "fluid")

    def vclass(self, t, who):
        f = self.foc[who]; d = math.hypot(t["gx"] - f[0], t["gy"] - f[1])
        return "FULL_VALID" if d <= FOCUS_R else "LOD_RELAXED"

    def vaddr(self, t, who):
        h = self._tileH(t); vc = self.vclass(t, who)
        return h if vc == "FULL_VALID" else hashlib.sha256(("\x1f".join([h, vc, who, "exp523-v1"])).encode()).hexdigest()[:16]

    def _lod_eff(self, t, who):
        return 1.0 if self.vclass(t, who) == "FULL_VALID" else RELAX_EFF

    def _ray_cells(self, x0, y0, x1, y1):
        # Amanatides-Woo voxel traversal over unit grid cells -> every cell the segment enters.
        cx, cy = int(math.floor(x0)), int(math.floor(y0)); ex, ey = int(math.floor(x1)), int(math.floor(y1))
        dx, dy = x1 - x0, y1 - y0; cells = [(cx, cy)]
        if dx == 0 and dy == 0: return cells
        sx = 1 if dx > 0 else -1; sy = 1 if dy > 0 else -1; INF = float("inf")
        tmx = (((cx + (1 if sx > 0 else 0)) - x0) / dx) if dx != 0 else INF
        tmy = (((cy + (1 if sy > 0 else 0)) - y0) / dy) if dy != 0 else INF
        tdx = abs(1.0 / dx) if dx != 0 else INF; tdy = abs(1.0 / dy) if dy != 0 else INF; g = 0
        while (cx, cy) != (ex, ey) and g < 256:
            g += 1
            if tmx < tmy: tmx += tdx; cx += sx
            else: tmy += tdy; cy += sy
            cells.append((cx, cy))
        return cells

    def _opaque(self, cx, cy):
        if not (0 <= cx < GX and 0 <= cy < GY): return False
        return self.phase_of(self.chi(self.tiles[cy * GX + cx])) in ("solid", "glass")

    def _los_blocked(self, p0, target_sec):
        # opaque tile STRICTLY BETWEEN shooter centroid and target tile severs the lane (target itself is drillable).
        tgx, tgy = target_sec % GX, target_sec // GX
        for (cx, cy) in self._ray_cells(p0[0], p0[1], tgx + 0.5, tgy + 0.5)[1:-1]:
            if self._opaque(cx, cy): return True, cy * GX + cx
        return False, None

    def _los_centroids(self):
        a = self.foc["A"]; b = self.foc["B"]
        for (cx, cy) in self._ray_cells(a[0], a[1], b[0], b[1])[1:-1]:
            if self._opaque(cx, cy): return {"clear": False, "block": cy * GX + cx}
        return {"clear": True, "block": None}

    def _fiedler(self):
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

    # ---- L1 ingest: enqueue only (commit boundary is the tick) ----
    def enqueue(self, player, kind, section, wi, synced, gs, focus):
        with self.lock:
            if player not in ("A", "B"): return {"accepted": False, "reason": "bad_player"}
            if focus is not None and focus[0] is not None and focus[1] is not None:
                self.foc[player] = (float(focus[0]), float(focus[1]))
            if section is None or section < 0 or section >= len(self.tiles):
                return {"accepted": False, "reason": "no_target"}
            self.pending.append({"player": player, "kind": kind, "section": int(section),
                                 "wi": float(wi), "synced": bool(synced), "gs": gs, "recv": self.frame})
            return {"accepted": True, "queued": True, "player": player, "section": int(section),
                    "resolve_frame": self.frame + 1, "kind": kind}

    def set_focus(self, player, focus):
        # focus-only update (WASD drift): moves a player's FULL_VALID bubble without an intent
        with self.lock:
            if player not in ("A", "B"): return {"ok": False, "reason": "bad_player"}
            if focus is None or focus[0] is None or focus[1] is None: return {"ok": False, "reason": "no_focus"}
            fx = min(GX - 0.5, max(-0.5, float(focus[0]))); fy = min(GY - 0.5, max(-0.5, float(focus[1])))
            self.foc[player] = (fx, fy)
            return {"ok": True, "player": player, "focus": [round(fx, 3), round(fy, 3)],
                    "full": sum(1 for t in self.tiles if self.vclass(t, player) == "FULL_VALID")}

    # ---- the Truth Tick: drain + net-resolve, one verdict per contested tile ----
    def tick(self):
        with self.lock:
            self.frame += 1
            pend = self.pending; self.pending = []
            bysec = {}
            for it in pend:
                if it["recv"] < self.frame - 1 - REBASE_WINDOW:   # bounded rebase: drop stale
                    self.stale += 1; continue
                bysec.setdefault(it["section"], []).append(it)
            self.resolutions = [self._resolve(sec, its) for sec, its in bysec.items()]
            for t in self.tiles:
                t["wi"] = max(0.06, t["wi"] * 0.94); t["hit"] *= 0.82
            if bysec or self.frame % 8 == 0:
                self.signs = self._fiedler()

    def _resolve(self, sec, its):
        t = self.tiles[sec]; chi0 = self.chi(t)
        shear_eff = 0.0; anneal_eff = 0.0; blocked = 0; n_shear = 0
        for it in its:
            if it["kind"] == "shear":
                n_shear += 1
                blk, _bt = self._los_blocked(self.foc[it["player"]], sec)
                if blk: blocked += 1; continue            # firewall: no line-of-sight -> shot rejected
                shear_eff += it["wi"] * self._lod_eff(t, it["player"])
            else:
                anneal_eff += ANNEAL_BASE * self._lod_eff(t, it["player"])
        synced = any(it["synced"] for it in its)
        if n_shear and shear_eff == 0.0 and anneal_eff == 0.0:
            chi_b = self.chi(t); Hv = self.world_H()
            gs = {"section": sec, "verdict": "BLOCKED", "frame": self.frame}
            comp = composite_address(Hv, gs); attest = session_attest(Hv, gs, SERVER_SECRET)
            self.last = "tile %d · BLOCKED (no line-of-sight) · ⊕%s" % (sec, comp[:6])
            return {"tile_id": sec, "geometry": self._tileH(t),
                    "vantage_A": {"class": self.vclass(t, "A"), "address": self.vaddr(t, "A")},
                    "vantage_B": {"class": self.vclass(t, "B"), "address": self.vaddr(t, "B")},
                    "net_stress": {"strain": 0.0, "compliance": 0.0, "net_wi": 0.0, "verdict": "BLOCKED"},
                    "op": "occluded", "chi": round(chi_b, 4), "phase": self.phase_of(chi_b),
                    "dS_cit": 0.0, "H_verified": Hv, "composite": comp, "attestation": attest,
                    "frame": self.frame, "blocked": int(blocked)}
        net_wi = shear_eff - anneal_eff * ANNEAL_GAIN
        t["wi"] = min(1.2, max(0.06, t["wi"] + net_wi)); t["hit"] = 1.0
        beta_eff = BETA * (1 + 0.6 * (1.0 if synced else self.pulse()[1]))
        bc = core.bethe_citadel_strain_512(beta_eff, t["wi"] * VORT, NF, NG, vorticity=VORT, chi=chi0)
        shear_wins = shear_eff > anneal_eff * ANNEAL_GAIN
        verdict, op = "STABLE_GLASS", "none"
        if shear_wins and bc["dS_cit"] < 0 and bc["survivable_by_material"]:
            ns, w = enact_phase_change_515(t["stalk"], beta_eff, t["wi"] * VORT, NF, NG, vorticity=VORT, mode="minimal")
            if w["status"] == "melted":
                t["stalk"] = np.asarray(ns, float); verdict, op = "NET_MELT", "Geodesic_Melt_515"
        elif (not shear_wins) and chi0 > 0.30:
            ns, w = enact_recrystallization_521(t["stalk"], beta_eff, t["wi"] * VORT, NF, NG, vorticity=VORT)
            if w.get("status") == "recrystallized":
                t["stalk"] = np.asarray(ns, float); verdict, op = "NET_ANNEAL", "Re_crystallization_521"
        chi1 = self.chi(t)
        Hv = self.world_H()
        gs = {"section": sec, "chi": round(chi1, 6), "wi": round(t["wi"], 6), "verdict": verdict, "frame": self.frame}
        comp = composite_address(Hv, gs); attest = session_attest(Hv, gs, SERVER_SECRET)
        self.log.append({"frame": self.frame, "section": sec, "verdict": verdict, "op": op, "H": Hv, "composite": comp})
        self.last = "tile %d · %s · χ %.2f→%.2f · A%.2f/B%.2f · ⊕%s" % (
            sec, verdict, chi0, chi1, shear_eff, anneal_eff, comp[:6])
        return {"tile_id": sec, "geometry": self._tileH(t),
                "vantage_A": {"class": self.vclass(t, "A"), "address": self.vaddr(t, "A")},
                "vantage_B": {"class": self.vclass(t, "B"), "address": self.vaddr(t, "B")},
                "net_stress": {"strain": round(shear_eff, 4), "compliance": round(anneal_eff, 4),
                               "net_wi": round(net_wi, 4), "verdict": verdict},
                "op": op, "chi": round(chi1, 4), "phase": self.phase_of(chi1),
                "dS_cit": round(bc["dS_cit"], 3), "H_verified": Hv, "composite": comp,
                "attestation": attest, "frame": self.frame}

    def arena(self):
        with self.lock:
            return {"GX": GX, "GY": GY, "FOCUS_R": FOCUS_R, "RELAX_EFF": RELAX_EFF,
                    "tiles": [{"id": t["id"], "gx": t["gx"], "gy": t["gy"]} for t in self.tiles]}

    def telem(self):
        with self.lock:
            ph, pv = self.pulse(); out = []; red = blue = 0
            for i, t in enumerate(self.tiles):
                chi = self.chi(t); sg = self.signs[i]; red += sg > 0; blue += sg < 0
                out.append({"id": t["id"], "chi": round(chi, 3), "wi": round(t["wi"], 3),
                            "phase": self.phase_of(chi), "prox": round(t["wi"] / (EPS_REF * chi), 3),
                            "critical": bool(t["wi"] / (EPS_REF * chi) >= 0.9), "sign": sg, "hit": round(t["hit"], 3),
                            "vA": self.vclass(t, "A"), "vB": self.vclass(t, "B")})
            fa = sum(1 for t in self.tiles if self.vclass(t, "A") == "FULL_VALID")
            fb = sum(1 for t in self.tiles if self.vclass(t, "B") == "FULL_VALID")
            return {"frame": self.frame, "t": round(time.time() - self.t0, 2), "tiles": out,
                    "focA": [round(self.foc["A"][0], 2), round(self.foc["A"][1], 2)],
                    "focB": [round(self.foc["B"][0], 2), round(self.foc["B"][1], 2)],
                    "full_A": int(fa), "full_B": int(fb), "stale": self.stale,
                    "resolutions": self.resolutions[-6:], "H_verified": self.world_H(),
                    "pulse_ph": round(ph, 4), "pulse_val": round(pv, 4),
                    "red": int(red), "blue": int(blue), "los_AB": self._los_centroids(),
                    "event": self.last, "bpm": SEED["bpm"], "seed": SEED["hash"]}


WORLD = Collider()
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
        if self.path == "/" or self.path.startswith("/index") or self.path.startswith("/?"):
            try:
                with open(os.path.join(HERE, "collider_viewport.html"), "rb") as f: body = f.read()
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
        n = int(self.headers.get("Content-Length", "0")); req = json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/call/shear_fire":
            return self._json(WORLD.enqueue(req.get("player", "A"), "shear", req.get("section"),
                                            req.get("wi", 0.06), bool(req.get("synced")), req.get("game_stats"), req.get("focus")))
        if self.path == "/call/anneal":
            return self._json(WORLD.enqueue(req.get("player", "B"), "anneal", req.get("section"),
                                            req.get("wi", 0.0), bool(req.get("synced")), req.get("game_stats"), req.get("focus")))
        if self.path == "/focus":
            return self._json(WORLD.set_focus(req.get("player", "A"), req.get("focus")))
        self.send_response(404); self.end_headers()


if __name__ == "__main__":
    print("DENTATUS · COLLIDER ARENA  (two-player contested truth · %g Hz net-resolution tick)" % TICK_HZ)
    print("  open  http://localhost:%d/?player=A   and   http://localhost:%d/?player=B" % (PORT, PORT))
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
