# ENGINE_AXIOMS_exp605 — Live SSE Reality Stream (keyframe+delta codec)

**Protocol:** exp605-v1 · **Series:** 600 · **Inherits:** exp604-v1
**Primary architect:** Daniel J. Dillberg — bigdilly95@gmail.com
**Declaration hash:** `7e682b51a229f7e68925f6e609d96354e17ec11c8386ebe41552584af1317c73`
**Status:** open · **Location:** `game/observability/stream.py`, `sse_server.py`, dashboard live client

---

## Axiom 1 — The bitrate question, answered

The Galerkin coarse Fiedler is a GLOBAL eigenvector, so a naive anchor "diff" is nearly full.
The codec instead has two content-addressed channels plus a video-style keyframe/delta:

```
COARSE channel  (keyed by H_coarse):
   - H_coarse unchanged  -> NO coarse event (anchors re-used from cache)
   - H_coarse changed    -> KEYFRAME (full anchor vector) or DELTA (only c[s]/sigma[s] moved > eps),
                            whichever is SMALLER (adaptive); periodic keyframe for resync
SECTION channel (keyed by 507 section signature):
   - new section -> full leaf telemetry ;  repeat -> section_ref (client cache)
HEARTBEAT when H_state unchanged -> at EMA equilibrium the stream goes near-silent
```

So the answer is **both, content-addressed**: the full coarse is pushed only when `H_coarse`
actually changes, and even then a thresholded delta is used when it is the smaller frame. Two
worlds that share geometry send the coarse **once** (verified: 2 worlds -> 1 coarse event).

## Axiom 2 — Bitrate is proportional to rate of change, not world size

Mirroring the EXP-507 memory bound, the stream's bitrate decouples from world size. At equilibrium
a repeated world costs one heartbeat (~0 bytes). Verified: 8 repeated worlds -> 7 heartbeats,
codec 15.8 KiB vs full-resend 114.7 KiB (7.3x), and the ratio grows with stream length.

## Axiom 3 — No pop-in (structural)

Each leaf's stitched value depends only on the coarse field and section centroids (EXP-507),
never on neighbour leaves. So a section renders the instant its anchor + sigma arrive, and section
events are self-contained (carry all their leaves). Sections **pulse in** independently with no
cross-section render dependency -> no seams even half-loaded.

## Axiom 4 — Transport

`sse_server.py` (stdlib `http.server`, self-pins `PYTHONHASHSEED=0`) serves the dashboard at `/`
and the SSE stream at `/stream`; the dashboard `connectLive()` client decodes the codec and renders
sections as they pulse in. Verified end to end over HTTP: 12 worlds reconstructed, each world's
sections received == announced, 7 heartbeats. Fork A 10/10, Fork B 5/5 (stream P_yz-invariant).

## Ghost Notes

**Ghost #41 — Coarse history depth:** the codec content-addresses against the IMMEDIATE previous
H_coarse, not full history; a world returning to an earlier coarse re-sends it. A small LRU of
recent H_coarse -> anchor vectors would make returns free (cheap, O(few)).

## Scope

`game/observability/stream.py` + `sse_server.py` + dashboard live client. No engine change; the
EXP-604 `sse_frames` stub remains for compatibility. `PYTHONHASHSEED=0`.
