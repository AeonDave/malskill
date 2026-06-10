# Android APK Analysis Procedure

Detailed workflow for analyzing Android APK files. Load this reference when the sample is identified as APK.

## Identification

APK files are ZIP archives containing Android application components.
- Magic: `PK\x03\x04` (ZIP)
- Contains: `AndroidManifest.xml`, `classes.dex`, `resources.arsc`, `META-INF/`
- Confirm with: `file sample.apk` → should report "Java archive" or "Android package"

## Triage

```bash
# List APK contents
unzip -l sample.apk

# Extract manifest info (requires aapt2 or apktool)
aapt2 dump badging sample.apk

# Quick decompile to inspect package structure
jadx -d ./decompiled sample.apk
```

If `jadx`/`aapt2` unavailable, use Python:
```python
import zipfile
with zipfile.ZipFile("sample.apk") as z:
    print([n for n in z.namelist() if not n.startswith("res/")])
```

## Manifest analysis

Focus on these indicators in `AndroidManifest.xml`:

**Dangerous permissions:**
- `android.permission.READ_SMS` / `RECEIVE_SMS` / `SEND_SMS` — SMS theft/interception
- `android.permission.CALL_PHONE` — premium-rate call fraud
- `android.permission.READ_CONTACTS` — contact exfiltration
- `android.permission.CAMERA` / `RECORD_AUDIO` — surveillance
- `android.permission.ACCESS_FINE_LOCATION` — tracking
- `android.permission.REQUEST_INSTALL_PACKAGES` — dropper behavior
- `android.permission.SYSTEM_ALERT_WINDOW` — overlay attacks
- `android.permission.BIND_ACCESSIBILITY_SERVICE` — accessibility abuse (keylogging, auto-clicking)
- `android.permission.BIND_DEVICE_ADMIN` — device admin abuse (anti-uninstall)

**Suspicious components:**
- Services that run in the foreground or as background
- Broadcast receivers for `BOOT_COMPLETED`, `CONNECTIVITY_CHANGE`, `SMS_RECEIVED`
- Content providers exposed without permissions
- Activities with intent filters for deep links (phishing)

## Decompilation

### jadx (preferred)

```bash
# Decompile to Java source
jadx -d ./decompiled sample.apk

# Decompile with deobfuscation
jadx -d ./decompiled --deobf sample.apk

# Search decompiled code
grep -rn "http\|https\|api\.\|\.com\|\.net\|\.org" ./decompiled/sources/
grep -rn "encrypt\|decrypt\|AES\|DES\|RC4\|XOR\|Base64" ./decompiled/sources/
grep -rn "Runtime\|exec\|ProcessBuilder\|loadLibrary\|loadClass" ./decompiled/sources/
```

### apktool (smali level)

```bash
# Decode to smali + resources
apktool d sample.apk -o ./decoded

# Inspect smali for:
grep -rn "Ljava/net/URL\|Ljava/net/HttpURLConnection" ./decoded/smali/
grep -rn "Ljavax/crypto" ./decoded/smali/
grep -rn "Ljava/lang/Runtime;->exec" ./decoded/smali/
```

Use smali when jadx output is damaged by obfuscation.

## Key analysis targets

### Network communication
1. Search for URL/IP construction: `URL`, `HttpURLConnection`, `OkHttp`, `Retrofit`, `Volley`
2. Check for hardcoded endpoints in strings, SharedPreferences, assets, or raw resources
3. Firebase: `google-services.json` in assets, Firebase Realtime DB URLs
4. MQTT, WebSocket, raw socket connections
5. Telegram bot API usage: `api.telegram.org`

### Crypto and obfuscation
1. `javax.crypto.*` usage: `Cipher`, `SecretKeySpec`, `IvParameterSpec`
2. Custom encoding: XOR loops, Base64, character shifting
3. Hardcoded keys in source, assets, or native libraries
4. String encryption: look for methods called at static init that decrypt string arrays

### Dynamic loading
1. `DexClassLoader` / `PathClassLoader` — loading DEX at runtime (dropper behavior)
2. `Class.forName()` + `Method.invoke()` — reflection-based execution
3. Native libraries: `System.loadLibrary()` → check `lib/` directory for `.so` files
4. Downloaded DEX/APK from C2 → second-stage payload

### Native code
If `lib/` contains `.so` files:
1. Identify architecture: `armeabi-v7a`, `arm64-v8a`, `x86`, `x86_64`
2. Extract and analyze with `r2`, Ghidra, or `objdump`
3. Look for JNI functions: `Java_<package>_<class>_<method>`
4. Native code often handles: C2 communication, encryption, anti-debug, root detection

## Obfuscation identification

Common APK obfuscators:
- **ProGuard** — basic name obfuscation (a, b, c class names), open-source
- **R8** — default Android compiler obfuscation, similar to ProGuard
- **DexGuard** — commercial, aggressive string encryption, class encryption, native protection
- **Allatori** — commercial, string encryption, control flow
- **Custom** — app-specific encryption, asset packaging, reflection chains

Signs of heavy obfuscation:
- Single-letter class/method/field names throughout
- Encrypted string arrays decrypted at runtime
- Control flow flattening (switch-case state machines)
- Opaque predicates (always-true/false conditions)
- Classes loaded from encrypted assets

## Family indicators

Common Android malware families and their traits:
- **Bankers** (Cerberus, Anubis, Sharkbot): overlay attacks, accessibility abuse, SMS interception, device admin
- **Spyware** (Pegasus-like): camera, mic, location, contacts, encrypted exfil
- **Adware/Fleeceware**: aggressive ad SDKs, subscription fraud
- **Ransomware**: device admin to lock screen, file encryption
- **Droppers**: minimal permissions, download DEX at runtime, masquerade as utility apps

## Report requirements

- Package name, main activity, target SDK
- Permissions with risk assessment
- C2 endpoints with provenance (hardcoded, config, native)
- Encryption algorithm and key material if recoverable
- Dynamic loading behavior
- Persistence mechanism
- Family attribution if supported
