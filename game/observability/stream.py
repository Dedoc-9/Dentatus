"""
game/observability/stream.py — live telemetry push adapter (EXP-604, SSE).

Pioneering choice: do NOT poll (each poll re-runs the engine, O(N^3) Fiedler dominates). PUSH
Witness-style frames over Server-Sent Events, but CONTENT-ADDRESS every frame by H_state. A frame
whose H_state was already sent is transmitted as a lightweight reference (no geometry/Fiedler
payload) — the client renders from its cache. Because lc-transitions are rare at EMA equilibrium
(EXP-409), a live stream mostly cycles a handful of addresses => near-zero recompute and bandwidth.

This is a transport STUB (the contract); wire it to an SSE server (e.g. dentatus_service over
HTTP) in deployment. It is import-light and never touches engine.*.
"""
import json


def sse_frames(bundle):
    """Yield SSE-framed telemetry. First occurrence of an H_state carries full telemetry;
    repeats carry only the reference (client cache hit). Mirrors the live push contract."""
    seen = set()
    for fr in bundle["frames"]:
        H = fr["H_state"]
        if H in seen:
            payload = {"H_state": H, "ref": True, "K_budget": fr["K_budget"],
                       "B_ent": fr["B_ent"], "lambda_2": fr["lambda_2"]}   # reference: client renders from cache
        else:
            seen.add(H)
            payload = fr                                                   # full telemetry (geometry + Fiedler)
        yield f"event: frame\ndata: {json.dumps(payload)}\n\n"
    yield f"event: commit\ndata: {json.dumps({'H_verified': bundle['committed_H_verified']})}\n\n"
