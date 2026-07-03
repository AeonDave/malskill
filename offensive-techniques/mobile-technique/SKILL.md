---
name: mobile-technique
description: "Auth assessment: mobile app security; Android/iOS static, storage, Frida/runtime, traffic, pinning, platform, API and crypto checks."
license: MIT
compatibility: "Android (APK, AAB), iOS (IPA); physical devices or emulators; Burp Suite / mitmproxy for traffic interception."
metadata:
  author: AeonDave
  version: "1.0"
  category: offensive-techniques
  language: multi
---

# Mobile Pentest Technique

Goal: systematically identify security weaknesses in Android and iOS applications following OWASP MASTG/MASVS.

## When this technique applies

- Mobile application (Android or iOS) in scope for pentest or bug bounty.
- Need to test authentication, storage, network, or platform-specific controls.
- Reverse engineering mobile app logic or extracting secrets.

## Boundary

- **CTF mobile tasks**: flag-extraction from APK/IPA/backup → `mobile-ctf` (faster, CTF-specific patterns including .ab, Unity/IL2CPP, asset stego).
- **Input from `web-exploit-technique`**: API-level findings from mobile app traffic.
- **Deep binary analysis**: `reversing-technique` for obfuscated native libraries and IL2CPP binaries.
- **Tool skills**: `offensive-tools/rev/jadx/`, `offensive-tools/rev/apktool/`, `offensive-tools/rev/dex2jar/`, `offensive-tools/rev/androguard/`, `offensive-tools/rev/frida/`.

## Initial triage

Before decompiling or hooking broadly, classify the app, the platform, and the control family most likely to fail first.

- **Starting state**: are you testing Android or iOS, do you have only the package or also a device/emulator, and is the priority storage, auth, transport, local trust, or backend API behavior?
- **First questions**: what protections are present (pinning, root/jailbreak checks, obfuscation, native code), what app paths matter most, and what can be validated statically before runtime work?
- **Immediate actions**: extract package metadata, map exposed components and trust boundaries, then choose the first lane: static review, traffic interception, dynamic instrumentation, or backend/API analysis.
- **Tool-family direction**: use decompilation skills (`jadx`, `apktool`, `androguard`, `dex2jar`) first for structure and secrets, then instrumentation (`frida`) and proxy skills after you know what runtime behavior must be observed or bypassed.
- **Escalation rule**: do not jump to native reversing or bypass scripts until the simpler Java/Kotlin/ObjC/Swift and network paths are exhausted.

## Agent operating model

```
Per mobile application:
  1. Static analysis — decompile, inspect manifest, search secrets.
  2. Dynamic analysis — instrument with Frida, bypass SSL pinning.
  3. Traffic interception — proxy through Burp/mitmproxy.
  4. Storage analysis — inspect SharedPreferences, SQLite, KeyStore.
  5. Authentication testing — test local auth, biometrics, session handling.
  6. API testing — apply web-exploit-technique to backend APIs.
```

## Android testing

### Static analysis

```bash
# Quick win: strings on the raw APK first (zip container: unzip -p for embedded files)
strings target.apk | grep -iE "api[_-]?key|secret|password|token|bearer|firebaseio\.com|s3\.amazonaws"

# Decompile
jadx -d output_dir target.apk
apktool d target.apk -o output_dir   # smali + decoded manifest + resources

# Manifest analysis: exported components, debuggable, allowBackup, permissions
aapt2 dump badging target.apk       # aapt is deprecated; aapt2 in modern SDK build-tools

# Hardcoded crypto (SecretKeySpec, Cipher.getInstance — common leak point)
grep -r "SecretKeySpec\|Cipher\|AES\|DES\|encrypt\|decrypt\|base64" output_dir/ | grep -v "^Binary"
# Look for the hardcoded key argument passed to SecretKeySpec(key, "AES")

# Firebase and remote config leaks
cat output_dir/res/values/google-services.json 2>/dev/null
cat output_dir/assets/google-services.json 2>/dev/null

# Certificate analysis
apksigner verify --print-certs target.apk

# Asset inspection (images, data files bundled with APK)
find output_dir/assets/ -type f | xargs file
# Large images → potential steganography (zsteg, steghide, visual inspection)
```

### Dynamic analysis

```bash
# Frida — SSL pinning bypass (spawn+resume is default since frida-tools 12+; do not pass --no-pause)
frida -U -f com.target.app -l ssl_pinning_bypass.js

# Objection — rapid assessment
objection -g com.target.app explore
# android sslpinning disable          # OkHttp3, TrustManagerImpl, SSLContext, Conscrypt, etc.
# android root disable
# android hooking list activities

# Drozer (community fork WithSecureLabs/drozer) — exposed components
dz> run app.package.attacksurface com.target.app
dz> run app.provider.query content://com.target.app.provider/
```

### Traffic interception

- Configure device/emulator proxy to Burp Suite.
- Install CA certificate (user store for Android 7+; system store requires root).
- SSL pinning bypass: Frida universal scripts (httptoolkit/frida-interception-and-unpinning) > Objection > LSPosed module (TrustMeAlready, JustTrustMe) > smali patching + repackage + resign.

### Storage analysis

```bash
adb shell cat /data/data/com.target.app/shared_prefs/*.xml
adb pull /data/data/com.target.app/databases/
adb shell ls /data/data/com.target.app/files/
```

### Android backup (.ab) analysis

`.ab` is a legacy channel. `adb backup` is restricted since Android 12 and requires `android:debuggable=true` for most apps; on Android 13+ most stock apps refuse it outright. Still useful for older/debuggable builds and forensic images.

```bash
# Header: "ANDROID BACKUP\n<ver>\n<compressed>\n<encryption>\n" (variable length — do NOT hardcode skip=)
python3 - <<'PY'
import zlib, pathlib
raw = pathlib.Path('backup.ab').read_bytes()
# Skip 4 newline-terminated header fields, then decompress the zlib stream that follows.
p = 0
for _ in range(4):
    p = raw.index(b'\n', p) + 1
pathlib.Path('backup.tar').write_bytes(zlib.decompress(raw[p:]))
PY
tar xf backup.tar -C extracted/

# Triage extracted content
grep -rE "password|token|secret|api[_-]?key|bearer" extracted/ 2>/dev/null
find extracted/ -name "*.db" -exec sqlite3 {} ".tables" \; 2>/dev/null
```

### Unity / IL2CPP APK

Unity games compile C# to native ARM via IL2CPP. jadx shows only stubs — reverse `libil2cpp.so` with metadata.

```bash
# Verify IL2CPP
ls apk_unzip/lib/arm64-v8a/   # → libil2cpp.so, libmain.so, libunity.so

# Il2CppDumper: recovers full class/method/field names from binary + metadata
# https://github.com/Perfare/Il2CppDumper
# Input: libil2cpp.so + assets/global-metadata.dat
# Output: dump.cs (all C# stubs with offsets), script.py (Ghidra import)

grep -i "flag\|key\|secret\|password\|cheat\|unlock" dump.cs
strings libil2cpp.so | grep -i "flag{"

# Load into Ghidra with Il2CppDumper's script.py for guided reversing
```

## iOS testing

### Static analysis

- Decrypt App Store IPA (jailbroken device required on iOS 15+): `frida-ios-dump`, `bagbak`, or `ipadecrypt`. `bfinject` is dead (iOS 11 Electra-era); Needle is archived (Reversec Labs, May 2025) — do not use.
- Off-device sideload for testing on stock iOS: TrollStore (iOS 14.0–17.0 unpatched) or a paid developer profile for re-signing.
- Decompile with Hopper, Ghidra, or Binary Ninja; entitlements via `ldid -e`, `codesign -d --entitlements :-`.
- Inspect `Info.plist` for URL schemes, ATS exceptions, `UIBackgroundModes`, associated domains, and entitlements (keychain access groups, app groups).
- Search for hardcoded secrets in Mach-O binaries and bundled resources (`strings -a`, `rabin2 -zzz`).

### Dynamic analysis

- Frida: `frida -U -f com.target.app -l script.js` (frida-tools spawns and auto-resumes; do not pass `--no-pause`).
- Objection: `objection -g com.target.app explore` — `ios sslpinning disable`, `ios jailbreak disable`, `ios cookies get`, `ios ui dump`.
- r2frida (in-process r2 session): `r2 frida://spawn/usb//com.target.app` for interactive dump/hook without a separate Frida script.
- App Attest / DeviceCheck: modern iOS apps bind API calls to a hardware attestation key; server-side rejection of forged attestations is common — validate via traffic replay, not just Frida hook success.

### Keychain and storage

```bash
# Objection keychain dump
ios keychain dump

# NSUserDefaults
ios nsuserdefaults get

# SQLite databases
ls /var/mobile/Containers/Data/Application/<UUID>/Library/
```

## OWASP MASVS mapping

| MASVS Category | Key tests |
|----------------|-----------|
| MASVS-STORAGE | SharedPreferences, SQLite, Keychain, logs, screenshots |
| MASVS-CRYPTO | Hardcoded keys, weak algorithms, custom crypto |
| MASVS-AUTH | Local auth, biometrics, session handling |
| MASVS-NETWORK | SSL pinning, certificate validation, proxy detection |
| MASVS-PLATFORM | Exported components, intent handling, WebView |
| MASVS-CODE | Code tampering, debugging, root/jailbreak detection |

## Modern platform gotchas

Android:
- **Play Integrity API** replaced SafetyNet Attestation (fully retired 2025-01-31). Server verdicts (`MEETS_DEVICE_INTEGRITY`, `MEETS_BASIC_INTEGRITY`, `MEETS_STRONG_INTEGRITY`) are backed by hardware key attestation on Android 13+; Magisk `zygisk-assistant` / `PlayIntegrityFix` bypass basic, not strong.
- **Explicit `android:exported`** required on Android 12+ (targetSdk ≥ 31) for any activity/service/receiver with an `<intent-filter>`; missing attribute = install failure. Old "exported by intent-filter" implicit exports are gone — re-check attack surface.
- **Runtime broadcast receivers** on Android 14+ (targetSdk ≥ 34) must pass `RECEIVER_EXPORTED` or `RECEIVER_NOT_EXPORTED` to `registerReceiver` — grep for these flags to map dynamic IPC exposure.
- **`adb backup`** restricted since Android 12; requires `android:debuggable=true`. Most production apps yield an empty archive — pivot to root+`tar` of `/data/data/<pkg>/` or Frida file dump.
- **Xposed original** is dead; use **LSPosed** (Zygisk module) on Android 8.1–15 for system-wide hooking modules.

iOS:
- **TrustCache** + **CoreTrust** enforce signed-binary allow-lists in the kernel; unsigned/adhoc binaries need a jailbreak or a TrollStore-style CoreTrust bypass (patched in iOS 17.0). No `bfinject`/`Needle` era techniques apply.
- **App Attest** (`DCAppAttestService`) binds requests to a Secure Enclave key; server rejects forged attestations even with a working Frida hook — always validate bypass end-to-end against the backend, not just on-device.
- **Universal SSL pinning bypass** landscape: httptoolkit/frida-interception-and-unpinning covers OkHttp/Conscrypt/BoringSSL/NSURLSession/CFNetwork; fall back to per-library hooks (`SSL_CTX_set_custom_verify`, `SecTrustEvaluateWithError`) when custom pinners are used.
