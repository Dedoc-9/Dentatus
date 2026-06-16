"""
collider_duel.py — Two-Combatant Tactical Duel over Dentatus (the Kinetic Skeleton Frame).

The release-ready combat slice. Built on the proven collider internals (native sheaf-Fiedler EXP-527.B,
tick-batched net resolution, dual-vantage EXP-523, Amanatides-Woo line-of-sight, nonce/attest), this
module adds the three things that make it a GAME, all enforced server-authoritatively at the 10 Hz tick:

  1. BODY vs AIM (twin-stick). Each combatant has an independent physical body (`pos`, the FULL_VALID
     proximity centroid moved by /move = WASD/left-stick) and an aim vector (`aim` + `look_h`, moved by
     /aim = mouse/right-stick). The body drives the Integrity-axis fog-of-war; the aim drives the
     line-of-sight raycast. `look_h` is stored so a 3rd-person or 1st-person external client reads the
     SAME authoritative occlusion — the camera is a projection of one authoritative truth.

  2. WIN CONDITION (Citadel Breach). A combatant's structural shield = the fraction of tiles within their
     FOCUS_R that still provide cover (solid/glass). Melt an opponent's local cover to fluid and their
     shield collapses; at <= BREACH_SHIELD the firewall rejects their continued existence (Citadel
     Breach), the round ends, the breach is sealed into H_verified, and the whole round replays
     bit-for-bit from the command log (EXP-520). Anneal rebuilds cover to survive; move to keep your own
     cover solid while drilling theirs. All three axes, contested.

  3. THE HYGIENE PASS (EXP-530.L at the duel boundary). The licensed property clamps run inside _resolve,
     AFTER the operator but BEFORE the seal: a hard-clamp breach reverts the tile to its pre-op snapshot
     and holds the last valid hash (fail-closed), so anomalous strain can never enter the committed chain.

    python3 collider_duel.py     # open  http://localhost:8782/?player=A   and   /?player=B
"""
import os, sys, json, time, math, threading, hashlib
from collections import deque
if os.environ.get("PYTHONHASHSEED") != "0":
    os.environ["PYTHONHASHSEED"] = "0"; os.execv(sys.executable, [sys.executable] + sys.argv)
HERE = os.path.dirname(os.path.abspath(__file__))
def _find_repo():
    p = os.path.dirname(HERE); g = os.path.dirname(p)
    for c in (os.environ.get("DENTATUS_REPO"), p, os.path.join(p, "Reality_Engine"), os.path.join(g, "Reality_Engine"), g):
        if c and os.path.isdir(os.path.join(c, "dentatus")): return c
    return p
REPO = _find_repo()
for _p in (REPO, os.path.join(REPO, "game/agency"), os.path.join(REPO, "game/observability"), os.path.join(REPO, "forge")):
    if _p not in sys.path: sys.path.insert(0, _p)
import numpy as np
from dentatus import core
from phase_change import enact_phase_change_515
from recrystallize import enact_recrystallization_521
from composite_witness import composite_address, session_attest, NonceChain
import sectioned_fiedler as sf
from invariant_synthesis import active_clamps          # EXP-530.L licensed property clamps
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SEED = {"hash": "9671566edf7b1103", "bpm": 39, "T": 1.5385, "phase0": 0.873}
BETA, NF, NG, VORT, EPS_REF = 12.0, 64, 96, 0.40, 0.5
GX, GY = 8, 6
TICK_HZ = 10.0
FOCUS_R = 2.2
RELAX_EFF = 0.45
ANNEAL_BASE = 0.06
ANNEAL_GAIN = 1.0
REBASE_WINDOW = 3
MOVE_SPEED = 0.55              # tiles per /move pulse (body drift)
BREACH_SHIELD = 0.18          # shield (local cover fraction) at/below which the firewall breaches the combatant
BOT_B_DEFAULT = os.environ.get("DENTATUS_BOT_B", "0") == "1"   # scripted server-side opponent (iteration lab)
PORT = int(os.environ.get("DUEL_PORT", "8782"))
SERVER_SECRET = os.environ.get("DENTATUS_SERVER_SECRET", "DEV_INSECURE_KEY").encode()


def _solid_stalk():
    s = np.zeros(18); s[0:4] = [1.0, 0.55, 0.57, 0.62]; s[8:11] = [0, 0, 1]
    s[12:18] = [0.9, -0.3, -0.6, 0.0, 0.0, 0.0]
    return s


class Duel:
    def __init__(self):
        self.lock = threading.Lock()
        self.t0 = time.time(); self.frame = 0
        self.tiles = [{"id": y * GX + x, "gx": x, "gy": y, "stalk": _solid_stalk(), "wi": 0.06, "hit": 0.0}
                      for y in range(GY) for x in range(GX)]
        self.players = {
            "A": {"pos": [1.5, GY - 0.5], "aim": [GX - 1.5, 0.5], "look_h": 1.6, "alive": True, "shield": 1.0},
            "B": {"pos": [GX - 1.5, GY - 0.5], "aim": [1.5, 0.5], "look_h": 1.6, "alive": True, "shield": 1.0},
        }
        self.round = {"n": 1, "over": False, "winner": None, "breach_H": None, "started": self.frame}
        self.pending = []
        self.resolutions = []
        self.leaves = [{"center": [t["gx"] + 0.5, t["gy"] + 0.5, 0.5], "size": [1.0, 1.0, 1.0]} for t in self.tiles]
        _c, _s2, self.fed_edges, _nb = sf.build_adjacency(self.leaves)
        self.signs = self._fiedler()
        self.log = []; self.stale = 0
        self.clamps = active_clamps()                   # EXP-530.L licensed guards {name:(field,pred,enf)}
        self.nonces = NonceChain(os.environ.get("DENTATUS_SESSION", "duel-default"))
        self.last_valid_H = self.world_H()
        self.tick_ms = deque(maxlen=300)               # frame-time profiler (the empirical instrument)
        self.bot_b = BOT_B_DEFAULT
        self.last = "DUEL ONLINE · 48 tiles · A vs B" + (" · BOT_B" if BOT_B_DEFAULT else "")

    # ---- geometry / material (mirrors collider_arena, verified) ----
    def chi(self, t): return float(core.material_compliance_chi_514(stalk=t["stalk"])["chi"])
    def _tileH(self, t): return hashlib.sha256(np.round(t["stalk"], 6).tobytes()).hexdigest()[:16]
    def phase_of(self, chi): return "solid" if chi < 0.3 else ("glass" if chi < 0.7 else "fluid")
    def _pos(self, who): return self.players[who]["pos"]

    def vclass(self, t, who):
        f = self._pos(who); d = math.hypot(t["gx"] - f[0], t["gy"] - f[1])
        return "FULL_VALID" if d <= FOCUS_R else "LOD_RELAXED"

    def vaddr(self, t, who):
        h = self._tileH(t); vc = self.vclass(t, who)
        return h if vc == "FULL_VALID" else hashlib.sha256(("\x1f".join([h, vc, who, "exp523-v1"])).encode()).hexdigest()[:16]

    def _lod_eff(self, t, who): return 1.0 if self.vclass(t, who) == "FULL_VALID" else RELAX_EFF

    def _ray_cells(self, x0, y0, x1, y1):
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
        tgx, tgy = target_sec % GX, target_sec // GX
        for (cx, cy) in self._ray_cells(p0[0], p0[1], tgx + 0.5, tgy + 0.5)[1:-1]:
            if self._opaque(cx, cy): return True, cy * GX + cx
        return False, None

    def _los_pair(self):
        a = self._pos("A"); b = self._pos("B")
        for (cx, cy) in self._ray_cells(a[0], a[1], b[0], b[1])[1:-1]:
            if self._opaque(cx, cy): return {"clear": False, "block": cy * GX + cx}
        return {"clear": True, "block": None}

    def _fiedler(self):
        n = len(self.tiles); stiff = [max(1e-3, 1.0 - self.chi(t)) for t in self.tiles]
        A = np.zeros((n, n))
        for i, j in self.fed_edges:
            w = min(stiff[i], stiff[j]); A[i, i] += w; A[j, j] += w; A[i, j] -= w; A[j, i] -= w
        f = sf._fiedler(A)
        if n and f[int(np.argmax(np.abs(f)))] < 0: f = -f
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

    def _shield(self, who):
        px, py = self._pos(who); cover = 0; tot = 0
        for t in self.tiles:
            if math.hypot(t["gx"] - px, t["gy"] - py) <= FOCUS_R:
                tot += 1
                if self.phase_of(self.chi(t)) in ("solid", "glass"): cover += 1
        return (cover / tot) if tot else 1.0

    # ---- combatant control ----
    def move(self, who, dx, dy):
        with self.lock:
            if who not in self.players or self.round["over"] or not self.players[who]["alive"]:
                return {"ok": False}
            p = self.players[who]["pos"]
            n = math.hypot(dx, dy) or 1.0
            p[0] = min(GX - 0.5, max(-0.5, p[0] + (dx / n) * MOVE_SPEED))
            p[1] = min(GY - 0.5, max(-0.5, p[1] + (dy / n) * MOVE_SPEED))
            return {"ok": True, "pos": [round(p[0], 3), round(p[1], 3)]}

    def aim(self, who, ax, ay, look_h=None):
        with self.lock:
            if who not in self.players: return {"ok": False}
            self.players[who]["aim"] = [float(ax), float(ay)]
            if look_h is not None: self.players[who]["look_h"] = float(look_h)
            return {"ok": True}

    def reset(self):
        with self.lock:
            for t in self.tiles: t["stalk"] = _solid_stalk(); t["wi"] = 0.06; t["hit"] = 0.0
            self.players["A"].update(pos=[1.5, GY - 0.5], alive=True, shield=1.0)
            self.players["B"].update(pos=[GX - 1.5, GY - 0.5], alive=True, shield=1.0)
            self.round = {"n": self.round["n"] + 1, "over": False, "winner": None, "breach_H": None, "started": self.frame}
            self.signs = self._fiedler(); self.last = "ROUND %d · reset" % self.round["n"]
            return {"ok": True, "round": self.round["n"]}

    def enqueue(self, player, kind, section, wi, synced, gs):
        with self.lock:
            if player not in ("A", "B"): return {"accepted": False, "reason": "bad_player"}
            if self.round["over"] or not self.players[player]["alive"]:
                return {"accepted": False, "reason": "round_over" if self.round["over"] else "breached"}
            if section is None or section < 0 or section >= len(self.tiles):
                return {"accepted": False, "reason": "no_target"}
            self.pending.append({"player": player, "kind": kind, "section": int(section),
                                 "wi": float(wi), "synced": bool(synced), "gs": gs, "recv": self.frame})
            return {"accepted": True, "queued": True, "player": player, "section": int(section),
                    "resolve_frame": self.frame + 1, "kind": kind}

    # ---- the Truth Tick ----
    def tick(self):
        with self.lock:
            _t0 = time.perf_counter()
            self.frame += 1
            if self.bot_b: self._bot_step()           # authoritative B policy enqueues its intents this tick
            pend = self.pending; self.pending = []
            bysec = {}
            for it in pend:
                if it["recv"] < self.frame - 1 - REBASE_WINDOW: self.stale += 1; continue
                bysec.setdefault(it["section"], []).append(it)
            self.resolutions = [self._resolve(sec, its) for sec, its in bysec.items()]
            for t in self.tiles:
                t["wi"] = max(0.06, t["wi"] * 0.94); t["hit"] *= 0.82
            if bysec or self.frame % 8 == 0:
                self.signs = self._fiedler()
            self._evaluate_breach()
            self.tick_ms.append((time.perf_counter() - _t0) * 1000.0)

    def _bot_step(self):
        # Deterministic server-side B policy (state -> intents). Runs inside the locked tick; appends to
        # self.pending exactly like a human combatant, so EXP-520 replay reproduces the round bit-for-bit.
        B = self.players["B"]
        if not B["alive"] or self.round["over"] or (self.frame % 2): return
        bx, by = B["pos"]; ax, ay = self.players["A"]["pos"]; B["aim"] = [ax, ay]
        sh = self._shield("B")
        if sh < 0.45:                                  # REBUILD: anneal nearest local fluid back to cover
            cand = sorted((t for t in self.tiles if math.hypot(t["gx"] - bx, t["gy"] - by) <= FOCUS_R
                           and self.phase_of(self.chi(t)) == "fluid"), key=lambda t: math.hypot(t["gx"] - bx, t["gy"] - by))
            for t in cand[:2]:
                self.pending.append({"player": "B", "kind": "anneal", "section": t["id"], "wi": 0.0,
                                     "synced": False, "gs": {"bot": 1}, "recv": self.frame})
            self.last = "BOT B · REBUILD shield %.0f%%" % (100 * sh); return
        dx, dy = ax - bx, ay - by; n = math.hypot(dx, dy) or 1.0   # ADVANCE toward A (push the bubble)
        if n > 2.0:
            B["pos"][0] = min(GX - 0.5, max(-0.5, bx + dx / n * MOVE_SPEED * 0.6))
            B["pos"][1] = min(GY - 0.5, max(-0.5, by + dy / n * MOVE_SPEED * 0.6))
        los = self._los_pair()
        if not los["clear"] and los["block"] is not None:          # DRILL the wall blocking the lane
            self.pending.append({"player": "B", "kind": "shear", "section": los["block"], "wi": 0.10,
                                 "synced": False, "gs": {"bot": 1}, "recv": self.frame})
            self.last = "BOT B · DRILL tile %d" % los["block"]; return
        cov = sorted((t for t in self.tiles if math.hypot(t["gx"] - ax, t["gy"] - ay) <= FOCUS_R
                      and self.phase_of(self.chi(t)) in ("solid", "glass")), key=lambda t: math.hypot(t["gx"] - ax, t["gy"] - ay))
        for t in cov:                                              # ASSAULT A's cover (a tile B can see)
            blk, _b = self._los_blocked(B["pos"], t["id"])
            if not blk:
                self.pending.append({"player": "B", "kind": "shear", "section": t["id"], "wi": 0.10,
                                     "synced": False, "gs": {"bot": 1}, "recv": self.frame})
                self.last = "BOT B · ASSAULT tile %d" % t["id"]; break

    def profile(self):
        a = sorted(self.tick_ms)
        if not a: return {"n": 0}
        n = len(a)
        return {"n": n, "mean_ms": round(sum(a) / n, 3), "p50_ms": round(a[n // 2], 3),
                "p95_ms": round(a[min(n - 1, int(0.95 * n))], 3), "max_ms": round(a[-1], 3),
                "headroom_hz": round(1000.0 / max(a[-1], 1e-3), 0), "tick_budget_ms": round(1000.0 / TICK_HZ, 1)}

    def set_bot(self, on):
        with self.lock:
            self.bot_b = bool(on); return {"ok": True, "bot_b": self.bot_b}

    def _evaluate_breach(self):
        if self.round["over"]: return
        for who in ("A", "B"):
            if not self.players[who]["alive"]: continue
            sh = self._shield(who); self.players[who]["shield"] = round(sh, 3)
            if sh <= BREACH_SHIELD:
                self.players[who]["alive"] = False
                other = "B" if who == "A" else "A"
                Hb = self.world_H()
                self.round.update(over=True, winner=other, breach_H=Hb)
                gs = {"event": "citadel_breach", "loser": who, "winner": other, "shield": round(sh, 4)}
                comp = composite_address(Hb, gs); att = session_attest(Hb, gs, SERVER_SECRET, nonce=self.nonces.issue(Hb)[1])
                self.log.append({"frame": self.frame, "breach": who, "winner": other, "H": Hb, "composite": comp, "attestation": att})
                self.last = "CITADEL BREACH · %s shield→%.0f%% · WINNER %s · ⊕%s" % (who, 100 * sh, other, comp[:6])

    def _resolve(self, sec, its):
        t = self.tiles[sec]; chi0 = self.chi(t)
        stalk_before = t["stalk"].copy(); wi_before = t["wi"]      # snapshot for the fail-closed clamp gate
        shear_eff = 0.0; anneal_eff = 0.0; blocked = 0; n_shear = 0
        for it in its:
            if it["kind"] == "shear":
                n_shear += 1
                blk, _bt = self._los_blocked(self._pos(it["player"]), sec)
                if blk: blocked += 1; continue
                shear_eff += it["wi"] * self._lod_eff(t, it["player"])
            else:
                anneal_eff += ANNEAL_BASE * self._lod_eff(t, it["player"])
        synced = any(it["synced"] for it in its)
        if n_shear and shear_eff == 0.0 and anneal_eff == 0.0:
            return self._receipt(sec, t, chi0, 0.0, 0.0, 0.0, "BLOCKED", "occluded", 0.0, blocked=blocked)
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
        # ── EXP-530.L HYGIENE PASS: licensed clamps run AFTER the operator, BEFORE the seal ──────────────
        bc1 = core.bethe_citadel_strain_512(beta_eff, t["wi"] * VORT, NF, NG, vorticity=VORT, chi=chi1)
        frame_vals = {"chi": round(chi1, 9), "E_strain_frac": bc1["E_strain_frac"],
                      "E_star_eff": bc1["E_star_eff"], "dS_cit": bc1["dS_cit"]}
        for _cn, (_cf, _cp, _ce) in sorted(self.clamps.items()):
            if _cf not in frame_vals or _ce != "hard": continue
            ok, _why = _cp(frame_vals[_cf])
            if not ok:                                            # FAIL-CLOSED: revert to last valid hashed state
                t["stalk"] = stalk_before; t["wi"] = wi_before
                self.last = "tile %d · CLAMP_REJECT %s · reverted" % (sec, _cn)
                return self._receipt(sec, t, chi0, shear_eff, anneal_eff, net_wi, "CLAMP_REJECT", "reverted",
                                     0.0, clamp=_cn)
        Hv = self.world_H(); self.last_valid_H = Hv
        self.log.append({"frame": self.frame, "section": sec, "verdict": verdict, "op": op, "H": Hv})
        self.last = "tile %d · %s · χ %.2f→%.2f · A%.2f/B%.2f" % (sec, verdict, chi0, chi1, shear_eff, anneal_eff)
        return self._receipt(sec, t, chi1, shear_eff, anneal_eff, net_wi, verdict, op, round(bc["dS_cit"], 3))

    def _receipt(self, sec, t, chi, strain, compliance, net_wi, verdict, op, ds, blocked=0, clamp=None):
        Hv = self.world_H()
        gs = {"section": sec, "chi": round(chi, 6), "verdict": verdict, "frame": self.frame}
        comp = composite_address(Hv, gs); _, nonce = self.nonces.issue(Hv)
        att = session_attest(Hv, gs, SERVER_SECRET, nonce=nonce)
        r = {"tile_id": sec, "geometry": self._tileH(t),
             "vantage_A": {"class": self.vclass(t, "A"), "address": self.vaddr(t, "A")},
             "vantage_B": {"class": self.vclass(t, "B"), "address": self.vaddr(t, "B")},
             "net_stress": {"strain": round(strain, 4), "compliance": round(compliance, 4),
                            "net_wi": round(net_wi, 4), "verdict": verdict},
             "op": op, "chi": round(chi, 4), "phase": self.phase_of(chi), "dS_cit": ds,
             "H_verified": Hv, "composite": comp, "attestation": att, "nonce": nonce, "frame": self.frame}
        if blocked: r["blocked"] = int(blocked)
        if clamp: r["clamp"] = clamp
        return r

    def arena(self):
        with self.lock:
            return {"GX": GX, "GY": GY, "FOCUS_R": FOCUS_R, "RELAX_EFF": RELAX_EFF, "breach_shield": BREACH_SHIELD,
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
            pl = {who: {"pos": [round(p["pos"][0], 2), round(p["pos"][1], 2)], "aim": [round(p["aim"][0], 2), round(p["aim"][1], 2)],
                        "look_h": p["look_h"], "alive": p["alive"], "shield": p["shield"],
                        "full": sum(1 for t in self.tiles if self.vclass(t, who) == "FULL_VALID")}
                  for who, p in self.players.items()}
            return {"frame": self.frame, "t": round(time.time() - self.t0, 2), "tiles": out,
                    "players": pl, "round": self.round, "stale": self.stale,
                    "resolutions": self.resolutions[-6:], "H_verified": self.world_H(),
                    "pulse_ph": round(ph, 4), "pulse_val": round(pv, 4),
                    "red": int(red), "blue": int(blue), "los_AB": self._los_pair(),
                    "tick_ms": self.profile(), "bot_b": self.bot_b,
                    "event": self.last, "bpm": SEED["bpm"], "seed": SEED["hash"]}


WORLD = Duel()
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
    def _serve_html(self):
        for name in ("collider_duel_viewport.html", "collider_viewport.html"):
            p = os.path.join(HERE, name)
            if os.path.exists(p):
                body = open(p, "rb").read(); self.send_response(200); self.send_header("Content-Type", "text/html")
                self._cors(); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        self.send_response(404); self.end_headers()
    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index") or self.path.startswith("/?"): return self._serve_html()
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
        path = self.path
        if path == "/move":  return self._json(WORLD.move(req.get("player", "A"), float(req.get("dx", 0)), float(req.get("dy", 0))))
        if path == "/aim":   return self._json(WORLD.aim(req.get("player", "A"), req.get("ax", 0), req.get("ay", 0), req.get("look_h")))
        if path == "/reset": return self._json(WORLD.reset())
        if path == "/bot":   return self._json(WORLD.set_bot(req.get("on", True)))
        if path == "/call/shear_fire":
            return self._json(WORLD.enqueue(req.get("player", "A"), "shear", req.get("section"),
                                            req.get("wi", 0.07), bool(req.get("synced")), req.get("game_stats")))
        if path == "/call/anneal":
            return self._json(WORLD.enqueue(req.get("player", "B"), "anneal", req.get("section"),
                                            req.get("wi", 0.0), bool(req.get("synced")), req.get("game_stats")))
        self.send_response(404); self.end_headers()


if __name__ == "__main__":
    print("DENTATUS · COLLIDER DUEL  (two-combatant tactical loop · %g Hz truth tick)" % TICK_HZ)
    print("  open  http://localhost:%d/?player=A   and   http://localhost:%d/?player=B" % (PORT, PORT))
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
