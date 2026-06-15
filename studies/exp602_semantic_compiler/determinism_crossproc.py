"""EXP-602 cross-process determinism: with PYTHONHASHSEED=0 the realized-state address is
identical across separate Python processes (true content-addressability). Without the pin it
varies (hash-randomized set/dict iteration order in the gamma recursion -> S_A summation order)."""
import os, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
REALITY = os.path.dirname(os.path.dirname(HERE))
ONE = ("import sys; sys.path.insert(0,%r); from dentatus import api; "
       "print(api.observe({'op':'observe','intent':{'title':'docking_bay','seed':{'density':1.0,"
       "'material':[0.55,0.57,0.62],'normal':[0,0,1],'curvature':2.0,'stress':{'axes':[3.0,2.0,0.4],"
       "'plane':'xy','tilt_deg':35}},'bbox':[[0,0,0],[1,1,1]],'zeeman':{'focus':[0.5,0.5,0.0],"
       "'budget':2048}},'steps':8})['H_verified'])" % REALITY)
def run(seed):
    env = dict(os.environ); env["PYTHONHASHSEED"] = str(seed)
    return subprocess.run([sys.executable, "-c", ONE], capture_output=True, text=True, env=env).stdout.strip()
pinned = [run(0) for _ in range(3)]
assert len(set(pinned)) == 1, f"FAIL: pinned not stable {pinned}"
print(f"[1] PASS  PYTHONHASHSEED=0 cross-process stable: {pinned[0][:20]}... (x3 separate processes)")
varied = {run(0), run(1), run(2)}
assert len(varied) > 1, "expected different seeds to differ"
print(f"[2] PASS  different hash seeds -> different address ({len(varied)} distinct) -> pin is required")
print(f"\n=== EXP-602 cross-process determinism: PASS (requires PYTHONHASHSEED=0) ===")
