"""
forge/signature_proof.py — EXP-531 registry-signing airlock proof. Exit 0 iff all properties hold.
Proves an authorized signature boots; any tamper to the registry, the signature, or the signer identity
fails closed with RegistryCryptographicBreach.
"""
import os, sys, json, shutil, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import registry_signing as RS

fails = []
work = tempfile.mkdtemp(prefix="sigproof_")
REG = os.path.join(work, "reg.json"); SIG = os.path.join(work, "reg.sig"); KEYS = os.path.join(work, "keys.json")
json.dump({"protocol": "mcl-invariant-v1", "licensed": [{"name": "chi_bounds", "lo": 0.05, "hi": 1.0}], "errata": []},
          open(REG, "w"), indent=2, sort_keys=True)

sk_hex, pk_hex = RS.generate_keypair()
json.dump({"protocol": RS.AUTHORITY_PROTOCOL, "keys": [{"pubkey": pk_hex, "holder": "Authority"}]}, open(KEYS, "w"))
RS.sign_registry(REG, sk_hex, SIG)

def breach(label, fn):
    try:
        fn(); fails.append(label + ": expected RegistryCryptographicBreach, none raised")
    except RS.RegistryCryptographicBreach:
        pass
    except Exception as e:
        fails.append(label + ": wrong exception %r" % e)

# 1) AUTHORIZED signature boots
try:
    r = RS.airlock(REG, SIG, KEYS, require=True)
    if not (r["signed"] and r["holder"] == "Authority"): fails.append("valid signature did not boot")
except Exception as e:
    fails.append("valid signature raised: %r" % e)

# 2) ONE-BYTE registry tamper -> breach (attacker swaps a bound but keeps the old signature)
def tamper_reg():
    d = json.load(open(REG)); d["licensed"][0]["hi"] = 5.0; json.dump(d, open(REG + ".bad", "w"))
    RS.verify_registry(REG + ".bad", SIG, {pk_hex: "Authority"})
breach("registry-tamper", tamper_reg)

# 3) SIGNATURE tamper -> breach (flip one hex char of the signature)
def tamper_sig():
    b = json.load(open(SIG)); s = list(b["signature"]); s[0] = "0" if s[0] != "0" else "1"; b["signature"] = "".join(s)
    p = SIG + ".bad"; json.dump(b, open(p, "w")); RS.verify_registry(REG, p, {pk_hex: "Authority"})
breach("signature-tamper", tamper_sig)

# 4) UNAUTHORIZED signer -> breach (a structurally valid key NOT on the allowlist)
def unauthorized():
    sk2, pk2 = RS.generate_keypair(); p = SIG + ".rogue"; RS.sign_registry(REG, sk2, p)
    RS.verify_registry(REG, p, {pk_hex: "Authority"})   # allowlist only knows the real key
breach("unauthorized-signer", unauthorized)

# 5) ATTACKER REPLACES the whole registry AND re-signs with their own key -> still rejected (not allowlisted)
def wholesale_replace():
    json.dump({"protocol": "mcl-invariant-v1", "licensed": [{"name": "evil", "lo": -1e9, "hi": 1e9}], "errata": []},
              open(REG + ".evil", "w"), indent=2, sort_keys=True)
    sk2, _ = RS.generate_keypair(); p = SIG + ".evil"; RS.sign_registry(REG + ".evil", sk2, p)
    RS.verify_registry(REG + ".evil", p, {pk_hex: "Authority"})
breach("wholesale-replace-resigned", wholesale_replace)

# 6) MISSING signature under strict mode -> breach; dev mode (require=False) tolerates absence
def missing_strict():
    RS.airlock(REG, SIG + ".nope", KEYS, require=True)
breach("missing-sig-strict", missing_strict)
try:
    if RS.airlock(REG, SIG + ".nope", KEYS, require=False)["signed"]:
        fails.append("dev mode wrongly reported signed with no sig")
except Exception as e:
    fails.append("dev mode raised on absent sig: %r" % e)

# 7) PRESENT-BUT-BAD signature fails even in dev mode (a present sig is always enforced)
def present_bad_devmode():
    RS.airlock(REG + ".bad", SIG, KEYS, require=False)   # reg.bad bytes != signed bytes
breach("present-bad-devmode", present_bad_devmode)

shutil.rmtree(work, ignore_errors=True)
print("EXP-531 · registry-signing airlock proof")
def P(k): return "PASS" if not any(k in f for f in fails) else "FAIL"
print("  1 authorized signature boots ...............", "PASS" if not any('valid signature' in f for f in fails) else "FAIL")
print("  2 one-byte registry tamper -> breach .......", P("registry-tamper"))
print("  3 signature tamper -> breach ...............", P("signature-tamper"))
print("  4 unauthorized signer -> breach ............", P("unauthorized-signer"))
print("  5 wholesale replace + re-sign -> breach ....", P("wholesale-replace"))
print("  6 missing sig strict -> breach .............", P("missing-sig-strict") if not any('dev mode' in f for f in fails) else "FAIL")
print("  7 present-but-bad sig fails in dev mode ....", P("present-bad-devmode"))
print("  VIOLATIONS:", len(fails))
for f in fails: print("   !", f)
sys.exit(1 if fails else 0)
