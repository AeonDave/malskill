---
name: mobile-ctf
description: "Challenge-solving methodology for mobile CTF tasks involving Android APKs, Android backups (.ab), iOS IPAs, Unity/IL2CPP games, and mobile-adjacent forensics. Use when artifacts are APK files, AAB bundles, Android backup archives, IPA files, DEX/smali code, mobile SQLite databases, SharedPreferences XML, Keystore files, or mobile game binaries. Covers: static DEX analysis and jadx decompilation, hardcoded secret extraction (AES keys, tokens, credentials), Android backup extraction and forensics, steganography in APK assets, Unity IL2CPP binary dumping, native library reversing, Frida hooking for runtime flag capture, and visual/metadata analysis of images extracted from device backups. Routes deep binary reversing to reversing-technique and dynamic instrumentation details to mobile-technique."
license: MIT
compatibility: "Linux/macOS; APK/IPA/AB artifacts; jadx, apktool, Python 3, optional frida/objection for dynamic tasks."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# Mobile CTF

Solve mobile CTF challenges by classifying the artifact type first, then choosing the narrowest extraction path before escalating to dynamic or native analysis.

## When this skill applies

- Artifact is an APK, AAB, IPA, `.ab` (Android backup), DEX file, or mobile game binary.
- Challenge asks to find a flag, key, secret, PIN, or hidden data from a mobile app or device backup.
- Artifact contains images, SQLite databases, or SharedPreferences with embedded or encoded flag content.

## Operating model

```
1. Classify artifact: APK | Android backup (.ab) | IPA | Unity game
2. Quick-win attempt: strings + grep flag{ on raw artifact
3. Static analysis path per artifact type
4. If flag not found: dynamic analysis (Frida/objection) or native reversing
5. Validate and submit
```

Always try `strings <file> | grep -i "flag{"` first. Saves time on ~30% of challenges.

## Technique integration

- `reversing-technique` for obfuscated native `.so` libraries, IL2CPP dumps, or complex custom crypto.
- `mobile-technique` for dynamic instrumentation details, SSL pinning bypass, and runtime hooking.
- `forensic-technique` if the artifact is a full device image or PCAP from a mobile session.

---

## Artifact type 1 — APK / AAB static analysis

### Quick triage

```bash
# 1. Strings grep (fast — catches plaintext flags immediately)
strings target.apk | grep -i "flag{"

# 2. Unzip and inspect structure
unzip -o target.apk -d apk_out/
find apk_out/ -type f | grep -v META-INF | sort

# Key files to check immediately:
#   apk_out/classes*.dex       — Java bytecode (decompile with jadx)
#   apk_out/lib/               — native .so libraries
#   apk_out/assets/            — bundled files (images, data, configs)
#   apk_out/res/               — resources (strings.xml, layout XMLs)
#   apk_out/AndroidManifest.xml — decoded manifest
```

### jadx decompilation

```bash
# Install jadx: https://github.com/skylot/jadx/releases
jadx -d jadx_out/ target.apk

# Grep for flag and common patterns
grep -r "flag{" jadx_out/
grep -r "SecretKeySpec\|AES\|cipher\|encrypt\|decrypt\|base64\|sha\|md5" jadx_out/ | grep -v "^Binary"

# Find main activity entry point
cat jadx_out/resources/AndroidManifest.xml | grep -i "MAIN\|LAUNCHER" -B2
```

### Hardcoded crypto (most common easy/medium pattern)

When `strings` or jadx shows `SecretKeySpec`, `Cipher.getInstance`, or a suspicious short string near crypto imports:

```bash
# Find the key and algorithm in DEX strings
strings apk_out/classes.dex | grep -E "^[A-Za-z0-9+/]{8,32}$" | head -20
# Look for: AES key (16/24/32 chars), IV (16 chars), mode string (AES/ECB/PKCS5Padding)

# Decrypt with Python once key/IV/ciphertext found
python3 - <<'EOF'
from Crypto.Cipher import AES
import base64

key = b'<key_from_apk>'           # exact bytes from hardcoded string
ct  = base64.b64decode('<b64_ct>') # ciphertext found in app
iv  = b'\x00'*16                   # ECB has no IV; CBC: extract IV from app

# AES-ECB (most common in easy CTF challenges)
cipher = AES.new(key, AES.MODE_ECB)
pt = cipher.decrypt(ct)
print(pt.rstrip(b'\x00\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10'))

# AES-CBC
# cipher = AES.new(key, AES.MODE_CBC, iv=iv)
# pt = cipher.decrypt(ct)
EOF
```

### Asset and resource analysis

```bash
# Check assets for unusual files (large images, non-standard files)
ls -lh apk_out/assets/
find apk_out/assets/ -type f | xargs file

# Stego on asset images
zsteg apk_out/assets/suspicious.png    # LSB stego (PNG/BMP)
steghide info apk_out/assets/suspicious.jpg  # JPEG stego (needs passphrase)
strings apk_out/assets/suspicious.png | grep -i "HTB\|flag"
# Check data after EOF marker
python3 -c "
data=open('apk_out/assets/suspicious.png','rb').read()
eof=data.rfind(b'\\x89PNG')
print(repr(data[-200:]))  # check tail for appended data
"

# strings.xml — often contains hardcoded values
cat jadx_out/resources/res/values/strings.xml | grep -i "key\|secret\|flag\|token\|pass"
```

### Firebase and remote config leaks

```bash
# Google Services config — Firebase API key, project ID
cat apk_out/google-services.json 2>/dev/null

# Firebase Realtime Database (default rules often public)
# URL pattern: https://<project-id>.firebaseio.com/.json
curl "https://<project-id-from-config>.firebaseio.com/.json"
```

---

## Artifact type 2 — Android backup (.ab)

Android backups contain app data, shared storage, and sometimes sensitive files.

### Extraction

```bash
# Read and validate header
python3 -c "
with open('backup.ab','rb') as f: print(repr(f.read(60)))
"
# Expected: b'ANDROID BACKUP\n<version>\n<compressed>\n<encryption>\n'
# Header size = length of that ASCII block (often 24 bytes, count manually)

# Extract: skip header, decompress zlib, untar
HEADER_SIZE=24   # adjust if header content differs
dd if=backup.ab bs=$HEADER_SIZE skip=1 2>/dev/null \
  | python3 -c "import sys,zlib; sys.stdout.buffer.write(zlib.decompress(sys.stdin.buffer.read()))" \
  > backup.tar
tar xf backup.tar -C extracted/

# List all non-manifest files
find extracted/ -type f | grep -v "_manifest" | sort
```

### Triage after extraction

```bash
# 1. Grep everything for the flag
grep -r "flag{" extracted/ 2>/dev/null

# 2. Binary search (flag might be in SQLite or binary files)
python3 -c "
import os, re
for root, _, files in os.walk('extracted/'):
    for f in files:
        p = os.path.join(root, f)
        try:
            d = open(p,'rb').read()
            m = re.findall(b'HTB\{[^}]{1,60}\}', d)
            if m: print(p, m)
        except: pass
"

# 3. Visual inspection of images — check ALL images, including Photos/
# Flag may be PRINTED ON A DOCUMENT photographed by the device owner
# View each with an image viewer or multimodal LLM — "Easy leaks" style
find extracted/ -name "*.jpg" -o -name "*.png" | sort

# 4. SQLite databases
for db in $(find extracted/ -name "*.db" | grep -v shm | grep -v wal); do
    python3 -c "
import sqlite3, sys
c = sqlite3.connect(sys.argv[1])
for t in c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall():
    rows = c.execute(f'SELECT * FROM \"{t[0]}\" LIMIT 5').fetchall()
    if rows: print(sys.argv[1], t[0], rows[:3])
" "$db" 2>/dev/null
done

# 5. SharedPreferences XML
find extracted/ -name "*.xml" | xargs grep -l "." | xargs cat 2>/dev/null
```

### Key backup paths to check

| Path | Content |
|------|---------|
| `extracted/apps/<package>/sp/*.xml` | SharedPreferences — app settings, tokens |
| `extracted/apps/<package>/db/*.db` | App databases |
| `extracted/shared/0/Pictures/` | Device camera roll — may show documents |
| `extracted/shared/0/DCIM/` | Camera photos |
| `extracted/shared/0/Download/` | Downloaded files |

---

## Artifact type 3 — Unity / IL2CPP APK

Arno-style: Unity game with `libil2cpp.so`. The game logic (C# code) is compiled into native ARM binary — jadx shows only Unity wrapper stubs.

```bash
# Confirm IL2CPP: look for these .so files
ls apk_out/lib/arm64-v8a/
# libil2cpp.so   → compiled C# game code (all classes, methods, strings)
# libgame.so     → optional additional native code
# global-metadata.dat in assets/ → type/method metadata for IL2CPP

# Extract metadata
find apk_out/assets/ -name "*.dat" -o -name "global-metadata*"

# Il2CppDumper — recovers class/method names from IL2CPP binary
git clone https://github.com/Perfare/Il2CppDumper
# Run: Il2CppDumper libil2cpp.so global-metadata.dat output/
# Produces: dump.cs (C# class stubs with all method names and field offsets)

# Search dump.cs for flag/key
grep -i "flag\|key\|secret\|password\|htb\|cheat\|unlock" output/dump.cs -i | head -20

# strings on libil2cpp.so (may expose flag directly in read-only data)
strings apk_out/lib/arm64-v8a/libil2cpp.so | grep -i "flag{\|flag\|key"

# Ghidra: load libil2cpp.so with Il2CppDumper output for guided reversing
# → reversing-technique for full binary analysis
```

---

## Artifact type 4 — iOS IPA

```bash
# IPA is a ZIP
unzip -o target.ipa -d ipa_out/
find ipa_out/Payload/ -type f | sort

# Main binary: ipa_out/Payload/<AppName>.app/<AppName>
file ipa_out/Payload/AppName.app/AppName   # Mach-O universal binary or ARM64

# Quick flag search
strings ipa_out/Payload/AppName.app/AppName | grep -i "flag{"
grep -r "flag{" ipa_out/ 2>/dev/null

# If App Store encrypted: frida-ios-dump or bfinject on real device
# → mobile-technique for dynamic analysis
```

---

## Dynamic analysis (when static fails)

Use when: flag is constructed at runtime, key is derived (not hardcoded), or logic is obfuscated.

```bash
# Frida — hook the decryption function and capture plaintext
frida -U -f <package_name> -l hook_crypto.js --no-pause

# Generic crypto hook (catches AES/DES decryption output):
# See mobile-technique for full Frida script patterns

# Objection — rapid assessment
objection -g <package_name> explore
# android sslpinning disable
# android hooking watch class com.example.CryptoClass
```

---

## Quick pivots by symptom

| Symptom | Action |
|---------|--------|
| `strings` finds `flag{` in APK | Done — submit |
| `SecretKeySpec` + short string in dex | AES hardcoded key → decrypt with Python |
| Large image in `assets/` | Stego → zsteg / visual inspection |
| `.ab` file, photos in extracted backup | View ALL photos — flag may be on photographed document |
| `libil2cpp.so` + `global-metadata.dat` | Unity/IL2CPP → Il2CppDumper |
| `Firebase` config in APK | Check Realtime DB public endpoint |
| Multi-dex, no obvious strings | jadx + grep → Frida if static fails |
| Native `.so` with JNI_ exports | reversing-technique for binary analysis |

## Resources

- [references/android-backup-forensics.md](references/android-backup-forensics.md) — Full .ab extraction workflow, header format variants, SQLite triage, photo inspection patterns.
- [references/apk-crypto-patterns.md](references/apk-crypto-patterns.md) — AES/DES/RSA hardcoded key patterns, SecretKeySpec extraction, common CTF crypto idioms, Python decrypt templates.
- [references/unity-il2cpp-reversing.md](references/unity-il2cpp-reversing.md) — Il2CppDumper workflow, dump.cs interpretation, Ghidra IL2CPP analysis, game-flag extraction patterns.
