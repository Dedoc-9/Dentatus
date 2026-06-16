"""
game/observability/stream.py — EXP-605 Live SSE Reality Stream (keyframe+delta codec).

Pioneering bitrate design (like a video codec): the Galerkin coarse Fiedler is a GLOBAL mode, so
a naive anchor "diff" is nearly full. Instead:
  * COARSE channel (keyed by H_coarse): periodic KEYFRAME (full anchor vector, an I-frame for
    resync) + per-frame thresholded DELTAS (only c[s]/sigma[s] that moved beyond eps).
  * SECTION channel (keyed by the 507 section signature): first occurrence carries full leaf
    telemetry; repeats carry a one-line section_ref (client renders from cache).
  * HEARTBEAT when H_state is unchanged -> at EMA equilibrium the stream goes near-silent.

Result: stream bitrate is proportional to the RATE OF CHANGE, not world size (mirrors EXP-507's
memory bound). Because each leaf's stitched value depends only on the coarse + centroids
(EXP-507), a section renders the instant its anchor + sigma arrive -> no cross-section render
dependency -> sections pulse in without seams even half-loaded (no pop-in).

Decoupled: reaches the core only via dentatus.api (telemetry). Never imports engine.*.
"""
import json
import hashlib
import numpy as np

from .sectioned_fiedler import stitched_fiedler, build_adjacency, _section_signature

KEYFRAME_EVERY = 4          # I-frame interval (resync for late subscribers)
DELTA_EPS = 1e-3            # anchor quantization: send c[s]/sigma[s] only if it moved beyond this


def frame_coarse(leaves):
    """Coarse descriptor for a world-state: per-section Galerkin anchor c, sigma, centroids,
    section signatures, and the content hash H_coarse."""
    st = stitched_fiedler(leaves)
    ctr, siz, edges, nbr = build_adjacency(leaves)
    so = st["section_of"]; S = st["n_sections"]
    scen = [ctr[so == s].mean(axis=0).round(6).tolist() for s in range(S)]
    c = [round(float(x), 6) for x in st["coarse"]]
    sg = [round(float(x), 6) for x in st["halo_sigma"]]
    H_coarse = hashlib.sha256(json.dumps({"c": c, "sg": sg, "sc": scen}, sort_keys=True).encode()).hexdigest()[:12]
    secsig = [_section_signature(np.where(so == s)[0], ctr, siz) for s in range(S)]
    sec_leaves = {secsig[s]: [leaves[i] for i in np.where(so == s)[0]] for s in range(S)}
    return {"H_coarse": H_coarse, "S": S, "c": c, "centroids": scen, "sigma": sg,
            "section_sigs": secsig, "sec_leaves": sec_leaves}


def encode_reality_stream(states, keyframe_every=KEYFRAME_EVERY, eps=DELTA_EPS):
    """Encode a sequence of world-states (each {H_state, leaves}) into SSE events.
    Returns list of (event_name, data_dict). Deterministic under PYTHONHASHSEED=0."""
    events = []; prevHs = prevC = prevHc = None; sent = set(); n = 0; kf_since = 0
    _b = lambda d: len(json.dumps(d, separators=(",", ":")))
    for fr in states:
        n += 1; Hs = fr["H_state"]
        if Hs == prevHs:                                   # world unchanged -> heartbeat
            events.append(("world", {"seq": n, "H_state": Hs, "hb": 1}))
            events.append(("heartbeat", {})); continue
        F = frame_coarse(fr["leaves"])
        events.append(("world", {"seq": n, "H_state": Hs, "H_coarse": F["H_coarse"],
                                  "n_leaves": len(fr["leaves"]), "sigs": F["section_sigs"]}))
        # COARSE CHANNEL: content-addressed by H_coarse, then adaptive keyframe-vs-delta
        if F["H_coarse"] != prevHc:
            kf_since += 1
            kf = {"c": F["c"], "sigma": F["sigma"], "centroids": F["centroids"]}
            force_kf = (prevC is None or kf_since >= keyframe_every or len(prevC["c"]) != F["S"])
            if not force_kf:
                ch = [[s, F["c"][s], F["sigma"][s], F["centroids"][s]] for s in range(F["S"])
                      if abs(F["c"][s] - prevC["c"][s]) > eps or abs(F["sigma"][s] - prevC["sigma"][s]) > eps]
                delta = {"changed": ch}
                if _b(delta) < _b(kf):                     # adaptive: send the smaller frame
                    events.append(("coarse_delta", delta))
                else:
                    events.append(("coarse_keyframe", kf)); kf_since = 0
            else:
                events.append(("coarse_keyframe", kf)); kf_since = 0
            prevC = F; prevHc = F["H_coarse"]
        # (else: coarse unchanged -> no coarse event; client reuses the cached anchors)
        for sg in F["section_sigs"]:
            if sg in sent:
                events.append(("section_ref", {"sig": sg}))
            else:
                sent.add(sg); events.append(("section", {"sig": sg, "leaves": F["sec_leaves"][sg]}))
        prevHs = Hs
    return events


def decode_reality_stream(events):
    """Reconstruct per-frame state (coarse field + section signatures) from the event stream.
    Verifies the codec: decode(encode(states)) recovers the coarse field bit-exactly."""
    coarse = None; cache = {}; frames = []; cur = None
    for ev, d in events:
        if ev == "world":
            if cur is not None:
                frames.append(cur)
            cur = {"H_state": d["H_state"], "coarse": (list(coarse["c"]) if coarse else None),
                   "sigs": d.get("sigs")}
        elif ev == "heartbeat":
            cur["coarse"] = list(coarse["c"]) if coarse else None
            cur["sigs"] = frames[-1]["sigs"] if frames else None
        elif ev == "coarse_keyframe":
            coarse = {"c": list(d["c"]), "sigma": list(d["sigma"]), "centroids": d["centroids"]}
            cur["coarse"] = list(coarse["c"])
        elif ev == "coarse_delta":
            for s, cs, sg, ce in d["changed"]:
                coarse["c"][s] = cs; coarse["sigma"][s] = sg; coarse["centroids"][s] = ce
            cur["coarse"] = list(coarse["c"])
        elif ev == "section":
            cache[d["sig"]] = d["leaves"]
    if cur is not None:
        frames.append(cur)
    return frames


def sse_format(event, data):
    """Server-Sent Events wire format for one event."""
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


# Backward-compatible alias (EXP-604 stub): one-shot bundle -> SSE frames.
def sse_frames(bundle):
    for fr in bundle.get("frames", []):
        yield sse_format("frame", fr)
    yield sse_format("commit", {"H_verified": bundle.get("committed_H_verified")})
