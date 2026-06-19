"""
integration/license_audit.py — make "every product declares its license track" a VERIFIED invariant.

The same discipline the workbench applies to integrity, applied to licensing: don't rely on a convention,
gate it. This asserts that

  - the root LICENSE (AGPL-3.0) and DUAL_LICENSE.md exist, and
  - every downstream APPLICATION carries a NOTICE that declares a recognized LICENSE-TRACK, and
  - every application's Python sources carry an SPDX-License-Identifier header.

It does NOT settle any legal question (license scope is fact-specific — see DUAL_LICENSE.md). It only verifies
that each product is *explicit* about its track, so the licensing uncertainty is legible rather than implicit.
Exit 0 iff every declaration is present and parseable. Stdlib only.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# downstream products (NOT siblings; never in the suite count) — kept in one place on purpose
APPLICATIONS = ["aegis_gate", "VeriSim", "VeriVerse", "AetherPulse", "AetherManifold"]

RECOGNIZED_TRACKS = ("AGPL-3.0-only", "AGPL-3.0", "Commercial", "MIT", "Apache-2.0")
TRACK_RE = re.compile(r"LICENSE-TRACK:\s*(.+)")
SPDX_RE = re.compile(r"SPDX-License-Identifier:\s*(\S+)")


def _check_root():
    problems = []
    for f in ("LICENSE", "DUAL_LICENSE.md"):
        if not os.path.exists(os.path.join(ROOT, f)):
            problems.append("root %s missing" % f)
    return problems


def _declared_track(notice_path):
    if not os.path.exists(notice_path):
        return None, "NOTICE missing"
    text = open(notice_path, encoding="utf-8").read()
    m = TRACK_RE.search(text)
    if not m:
        return None, "NOTICE has no LICENSE-TRACK: line"
    track = m.group(1).strip()
    if not any(track.startswith(t) for t in RECOGNIZED_TRACKS):
        return None, "unrecognized track %r" % track
    return track, None


def _spdx_coverage(app_dir):
    missing = []
    for dirpath, _dirs, files in os.walk(app_dir):
        if "__pycache__" in dirpath:
            continue
        for fn in files:
            if fn.endswith(".py"):
                p = os.path.join(dirpath, fn)
                head = open(p, encoding="utf-8").read(400)
                if not SPDX_RE.search(head):
                    missing.append(os.path.relpath(p, ROOT))
    return missing


def audit():
    print("Dentatus license audit — every product must declare its track (legibility, not legal advice).\n")
    problems = _check_root()
    for p in problems:
        print("  [FAIL] %s" % p)

    for app in APPLICATIONS:
        app_dir = os.path.join(ROOT, app)
        if not os.path.isdir(app_dir):
            print("  [FAIL] %-14s application directory missing" % app)
            problems.append(app)
            continue
        track, err = _declared_track(os.path.join(app_dir, "NOTICE"))
        spdx_missing = _spdx_coverage(app_dir)
        if err:
            print("  [FAIL] %-14s %s" % (app, err))
            problems.append(app)
        elif spdx_missing:
            print("  [FAIL] %-14s declares %s but %d source(s) lack an SPDX header (e.g. %s)"
                  % (app, track, len(spdx_missing), spdx_missing[0]))
            problems.append(app)
        else:
            print("  [PASS] %-14s LICENSE-TRACK: %s  (SPDX on all sources)" % (app, track))

    print()
    if problems:
        print("[LICENSE AUDIT BLOCKED] add a NOTICE with a LICENSE-TRACK line + SPDX headers to each product.")
        return 1
    print("[LICENSE AUDIT CLEAN] %d products each declare a recognized track; root LICENSE + DUAL_LICENSE present."
          % len(APPLICATIONS))
    return 0


if __name__ == "__main__":
    sys.exit(audit())
