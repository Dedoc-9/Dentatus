"""
conformance_suite/run.py — verify (or update) the cross-application conformance baseline.

  PYTHONHASHSEED=0 python3 run.py             # verify: exit 0 if every app matches the pinned baseline, 1 if drift
  PYTHONHASHSEED=0 python3 run.py --update     # re-pin the baseline (a deliberate, noted act)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runner as R


def main():
    update = "--update" in sys.argv
    current = R.collect()
    if update:
        pinned = R.write_baseline(current)
        print("Re-pinned %d application goldens:" % len(pinned))
        for app, v in sorted(pinned.items()):
            print("  %-16s %s" % (app, v["golden"][:24]))
        return 0
    ok, faults = R.compare(current, R.load_baseline())
    print("Cross-application conformance regression (%d apps):" % len(R.PROBES))
    base = R.load_baseline()
    for app in sorted(R.PROBES):
        cur = current.get(app, {})
        status = "ERROR" if "error" in cur else ("DRIFT" if base.get(app, {}).get("golden") != cur.get("golden") else "OK")
        print("  [%-5s] %-16s %s" % (status, app, cur.get("golden", cur.get("error", ""))[:24]))
    if ok:
        print("\n[CONFORMANCE STABLE] every application reproduces its pinned baseline.")
        return 0
    print("\n[CONFORMANCE DRIFT] foundation change altered a downstream application:")
    for f in faults:
        print("  - %s: %s %s" % (f["app"], f["reason"], f.get("detail", "%s != %s" % (f.get("baseline", ""), f.get("current", "")))))
    print("If intended, re-pin with: PYTHONHASHSEED=0 python3 run.py --update")
    return 1


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.stderr.write("set PYTHONHASHSEED=0\n"); raise SystemExit(2)
    sys.exit(main())
