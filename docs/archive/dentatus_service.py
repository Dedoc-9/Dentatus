#!/usr/bin/env python3
"""
dentatus_service.py — process-boundary handshake (the Clean Room license firewall).

Reads one JSON request per line on stdin, writes one JSON response per line on stdout.
A game layer in ANY language talks to the AGPL-3.0 oracle across this process boundary, so
the game is a separate program communicating by Intent JSON -> Verified State Hash, not an
in-process linked derivative. See DEV_NOTES_clean_room.md.

Request:  {"op":"observe","intent":{...}}  or  {"op":"observe","declaration":{...}}
Response: {... observables, firewall, H_verified ...}
"""
import sys, os, json
# EXP-602 determinism: a content-addressed reality store needs cross-process bit-stability.
# PYTHONHASHSEED randomizes string set/dict iteration order, which perturbs the gamma-recursion
# summation. Pin it to 0 (re-exec once) so H_verified is identical across processes/machines.
if os.environ.get("PYTHONHASHSEED") != "0":
    os.environ["PYTHONHASHSEED"] = "0"
    os.execv(sys.executable, [sys.executable] + sys.argv)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dentatus import api

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            op = req.get("op", "observe")
            resp = api.observe(req) if op == "observe" else {"error": f"unknown op {op!r}"}
        except Exception as e:  # boundary stays alive; errors are data
            resp = {"error": str(e)}
        sys.stdout.write(json.dumps(resp) + "\n"); sys.stdout.flush()

if __name__ == "__main__":
    main()
