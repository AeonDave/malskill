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
# Quick win: strings on the raw APK first
strings target.apk | grep -iE "api[_-]?key|secret|password|token|HTB\{"

# Decompile
jadx -d output_dir target.apk
apktool d target.apk -o output_dir   # smali + decoded manifest + resources

# Manifest analysis: exported components, debuggable, allowBackup, permissions
aapt dump badging target.apk

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
# Frida — SSL pinning bypass
frida -U -f com.target.app -l ssl_pinning_bypass.js --no-pause

# Objection — rapid assessment
objection -g com.target.app explore
# android sslpinning disable
# android root disable
# android hooking list activities

# Drozer — exposed components
dz> run app.package.attacksurface com.target.app
dz> run app.provider.query content://com.target.app.provider/
```

### Traffic interception

- Configure device/emulator proxy to Burp Suite.
- Install CA certificate (user store for Android 7+; system store requires root).
- SSL pinning bypass: Frida universal scripts > Objection > Xposed > smali patching.

### Storage analysis

```bash
adb shell cat /data/data/com.target.app/shared_prefs/*.xml
adb pull /data/data/com.target.app/databases/
adb shell ls /data/data/com.target.app/files/
```

### Android backup (.ab) analysis

Android backup files are unencrypted by default and contain full app data + shared storage.

```bash
# Header: "ANDROID BACKUP\n<ver>\n<compressed>\n<encryption>\n"
# Measure header length exactly before extracting
python3 -c "
with open('backup.ab','rb') as f: h=f.read(60)
print(repr(h))
idx = h.find(b'x\xda') or h.find(b'x\x9c')  # zlib magic
print('zlib starts at byte', idx)
"

# Extract (adjust skip= to header byte count)
dd if=backup.ab bs=24 skip=1 2>/dev/null \
  | python3 -c "import sys,zlib; sys.stdout.buffer.write(zlib.decompress(sys.stdin.buffer.read()))" \
  > backup.tar && tar xf backup.tar -C extracted/

# Triage extracted content
grep -r "password\|token\|secret\|key" extracted/ 2>/dev/null
find extracted/ -name "*.db" | xargs -I{} sqlite3 {} ".tables" 2>/dev/null
find extracted/ -name "*.jpg" -o -name "*.png" | sort   # inspect visually
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

- Decrypt IPA (if App Store): `frida-ios-dump` or `bfinject`.
- Decompile with Hopper, Ghidra, or Binary Ninja.
- Inspect `Info.plist` for URL schemes, app transport security, entitlements.
- Search for hardcoded secrets in Mach-O binaries and bundled resources.

### Dynamic analysis

- Frida: `frida -U -f com.target.app -l script.js`.
- Objection: `objection -g com.target.app explore` — `ios sslpinning disable`, `ios jailbreak disable`.
- Needle: modular iOS testing framework.

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
