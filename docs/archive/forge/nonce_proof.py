"""
forge/nonce_proof.py — EXP-528 rolling nonce-chaining: property proof against the real witness module.
Proves: backward-compat, replay-reproducibility (EXP-520), replay immunity, forge resistance, fork
sensitivity. Deterministic. Exit 0 iff all properties hold.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
for p in (REPO, os.path.join(REPO, "game/observability")):
    if p not in sys.path: sys.path.insert(0, p)
import composite_witness as W

SECRET = b"forge_demo_secret"; SID = "session-7"
# a plausible sealed-H sequence (what the engine would advance through)
H_seq = ["%016x" % (0xA11CE + 7 * i * i + 3 * i) for i in range(12)]
stats = [{"section": i % 5, "chi": round(0.2 + 0.05 * i, 6)} for i in range(12)]
fails = []

# 1) BACKWARD COMPAT — nonce=None reproduces the pre-528 contract byte-for-byte
a_legacy = W.session_attest(H_seq[0], stats[0], SECRET)                      # no nonce arg
a_none   = W.session_attest(H_seq[0], stats[0], SECRET, nonce=None)
if a_legacy != a_none: fails.append("backward-compat: nonce=None diverges from legacy")
if not W.verify_attest(H_seq[0], stats[0], SECRET, a_legacy):
    fails.append("legacy receipt no longer verifies")
if W.composite_address(H_seq[0], stats[0]) != W.composite_address(H_seq[0], stats[0], nonce=None):
    fails.append("composite_address legacy path changed")

# 2) REPLAY-REPRODUCIBILITY (EXP-520) — two independent passes produce identical (seq,nonce,attest)
def run_chain():
    ch = W.NonceChain(SID); out = []
    for i, H in enumerate(H_seq):
        seq, nonce = ch.issue(H)
        att = W.session_attest(H, stats[i], SECRET, nonce=nonce)
        out.append((seq, nonce, att))
    return out
r1, r2 = run_chain(), run_chain()
if r1 != r2: fails.append("nonce chain not bit-reproducible across runs")
# the pure replay oracle must match the issued nonces from the command log alone
ch0 = W.NonceChain(SID)
if any(ch0.expected_nonce(H_seq, i) != r1[i][1] for i in range(len(H_seq))):
    fails.append("expected_nonce (replay oracle) disagrees with issued chain")

# 3) REPLAY IMMUNITY — a captured valid frame re-presented after the head advances is rejected
V = W.NonceChain(SID)
# accept frames 0..k in order
for k in range(6):
    if not V.accept(k, H_seq, r1[k][1]): fails.append("fresh frame %d wrongly rejected" % k)
# now replay frame 3 (a perfectly valid, signed, old frame)
captured_seq, captured_nonce, captured_att = r1[3]
if V.accept(captured_seq, H_seq, captured_nonce):
    fails.append("REPLAY ACCEPTED: stale frame 3 passed the freshness guard")
if not V.accept(6, H_seq, r1[6][1]): fails.append("next live frame 6 wrongly rejected after replay attempt")

# 4) FORGE RESISTANCE — correct nonce, WRONG secret -> attestation fails
forged = W.session_attest(H_seq[7], stats[7], b"WRONG_SECRET", nonce=r1[7][1])
if W.verify_attest(H_seq[7], stats[7], SECRET, forged, nonce=r1[7][1]):
    fails.append("forged-secret attestation verified")
# correct secret + correct nonce verifies; correct secret + WRONG nonce fails
if not W.verify_attest(H_seq[7], stats[7], SECRET, r1[7][2], nonce=r1[7][1]):
    fails.append("genuine nonce-bound attestation failed to verify")
if W.verify_attest(H_seq[7], stats[7], SECRET, r1[7][2], nonce="deadbeefdeadbeef"):
    fails.append("attestation verified under a substituted nonce")

# 5) FORK SENSITIVITY — diverge ONE H mid-stream -> all subsequent nonces fork
H_fork = list(H_seq); H_fork[5] = "ffffffffffffffff"
base = W.NonceChain(SID); frk = W.NonceChain(SID)
diverged_from = None
for i in range(len(H_seq)):
    _, nb = base.issue(H_seq[i]); _, nf = frk.issue(H_fork[i])
    if nb != nf and diverged_from is None: diverged_from = i
# nonces are issued BEFORE folding H_i, so the fork shows up at i=6 (first nonce after the changed H_5)
if diverged_from != 6: fails.append("fork did not propagate at the expected step (got %r)" % diverged_from)
if base.expected_nonce(H_seq, 11) == frk.expected_nonce(H_fork, 11):
    fails.append("forked chains reconverged")

print("EXP-528 rolling nonce-chaining — property proof")
print("  1 backward-compat (nonce=None == legacy) ......", "PASS" if not any('compat' in f or 'legacy' in f for f in fails) else "FAIL")
print("  2 replay-reproducible (EXP-520) ..............", "PASS" if not any('reproducib' in f or 'oracle' in f for f in fails) else "FAIL")
print("  3 replay immunity (stale frame rejected) .....", "PASS" if not any('REPLAY' in f or 'frame' in f for f in fails) else "FAIL")
print("  4 forge resistance (secret + nonce binding) ..", "PASS" if not any('forged' in f or 'substituted' in f or 'genuine' in f for f in fails) else "FAIL")
print("  5 fork sensitivity (1 H diverges chain) ......", "PASS" if not any('fork' in f or 'reconverg' in f for f in fails) else "FAIL")
print("  VIOLATIONS:", len(fails))
for f in fails: print("   !", f)
sys.exit(1 if fails else 0)
