---
name: mobile-technique
description: "Auth assessment: mobile app security; Android/iOS static, storage, Frida/runtime, traffic, pinning, platform, API and crypto checks."
license: MIT
compatibility: "Android (APK, AAB), iOS (IPA); physical devices or emulators; Burp Suite / mitmproxy for traffic interception."
metadata:
  author: AeonDave
  version: "1.2"
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
- **Flutter/Dart AOT or React Native/Hermes**: load [mobile framework artifact notes](../../offensive-ctf/mobile-ctf/references/modern-app-frameworks.md) for framework cues and tool-version limits; use only the relevant reversing guidance outside CTF work.
- **Tool skills**: `offensive-tools/rev/jadx/`, `offensive-tools/rev/apktool/`, `offensive-tools/rev/dex2jar/`, `offensive-tools/rev/androguard/`, `offensive-tools/rev/frida/`.
- **Android IPC**: load [Android IPC attack surface](references/android-ipc-attack-surface.md) for exported components, privileged extras, nested intents, PendingIntents, providers, Binder identity and WebView bridges: shell and drozer commands, static signatures, lab PoC shapes and version rules.
- **Opaque mobile traffic**: load [Android traffic and custom protocols](references/android-traffic-and-custom-protocols.md) when TLS interception leaves application encryption, binary serialization or a client-to-backend command boundary unresolved.
- **Android fuzzing**: load [fuzzing-technique](../fuzzing-technique/SKILL.md), then [Android fuzzing](../fuzzing-technique/references/android-fuzzing.md) to choose host, ART/JNI, Binder or device execution and qualify crash reachability.

## Initial triage

Before decompiling or hooking broadly, classify the app, the platform, and the control family most likely to fail first.

- **Starting state**: are you testing Android or iOS, do you have only the package or also a device/emulator, and is the priority storage, auth, transport, local trust, or backend API behavior?
- **First questions**: what protections are present (pinning, root/jailbreak checks, obfuscation, native code), what app paths matter most, and what can be validated statically before runtime work?
- **Immediate actions**: extract package metadata, map exposed components and trust boundaries, then choose the first lane: static review, traffic interception, dynamic instrumentation, or backend/API analysis.
- **Tool-family direction**: use decompilation skills (`jadx`, `apktool`, `androguard`, `dex2jar`) first for structure and secrets, then instrumentation (`frida`) and proxy skills after you know what runtime behavior must be observed or bypassed.
- **Escalation rule**: follow the observed trust boundary. Go directly to native code when the relevant input reaches JNI; use instrumentation only to resolve a specific uncertainty.

For Android, record package/version, source, hashes and signing certificate/rotation lineage; OS API/build/security patch, target SDK, ABI, WebView provider, root/debug state and test caller identity. A re-signed package, debug build or privileged harness is a different test condition.

Inventory base, configuration and feature splits; a base APK alone may omit relevant DEX, resources or native libraries. Record missing on-demand/downloaded code as a coverage gap. Use [apkanalyzer](https://developer.android.com/tools/apkanalyzer), [bundletool](https://developer.android.com/tools/bundletool) and [apksigner](https://developer.android.com/tools/apksigner) for the actual artifact format. A certificate mismatch needs provenance/rotation investigation; a self-signed certificate alone is normal for Android apps, not malware evidence.

Acquire complete, authentic artifacts before analysis. `adb shell pm path <pkg>` lists every split installed on a device. For store builds use [apkeep](https://github.com/EFForg/apkeep): exchange the single-use OAuth token for an AAS token (`apkeep -e <email> --oauth-token <token>`), then `apkeep -a <app>[@version] -e <email> -t <aas> -o split_apk=true <outdir>`; `--list-versions` gives the version history. Check the signer against the developer's published lineage before investing time: mirrors are a source of old builds, not of provenance.

For old/new APK comparisons, hold tooling, device configuration and test state constant. Map manifest, DEX, native and resource deltas to a reachable behavior and replay the same harmless test on both versions. A removed string or library is neither a confirmed vulnerability nor proof of a fix.

```bash
apktool d -o old old.apk && apktool d -o new new.apk && diff -r old new
jadx --deobf -d old-src old.apk && jadx --deobf -d new-src new.apk && diff -r old-src new-src
```

Read deltas as candidates: added validation (sibling entry points may lack it), removed debug or staging endpoints, new permissions, components and SDKs, changed crypto or pinning.

## Agent operating model

```
Per mobile application:
  1. Static analysis — decompile, inspect manifest, search secrets.
  2. Dynamic analysis — observe the selected entry point and process.
  3. Traffic analysis — distinguish routing, TLS trust and application encoding.
  4. Storage analysis — inspect SharedPreferences, SQLite, KeyStore.
  5. Authentication testing — test local auth, biometrics, session handling.
  6. API testing — apply web-exploit-technique to backend APIs.
```

For source-assisted or AI-assisted review, first separate mobile entry points from backend/desktop code. Assign each independent entry point to a relevant vulnerability class, then trace controllable fields through validation, normalization and state precedence to the sensitive operation. Include reachable SDK/dependency code. Confirm cold/warm state and rejection controls before assigning impact: an external value overwritten by trusted internal state does not reach the alleged sink. See the [GitHub Android audit case study](https://github.blog/security/how-we-found-24-android-vulnerabilities-using-our-open-source-ai-security-agent/).

Untrusted mobile inputs to assign: deep links and URL schemes, intents, network responses and push messages, shared content, external storage, clipboard, UI input. Persisted values are trusted by origin, not by location. Every client-side control that a patch, hook or repackaging removes ends at the backend: send the request the client refused and record the server decision before calling it a finding.

## Android testing

### Static analysis

```bash
# Decompile
jadx -d java_out target.apk
apktool d target.apk -o apk_out   # smali + decoded manifest + resources

# Manifest analysis: exported components, debuggable, allowBackup, permissions
apkanalyzer manifest print target.apk
# Defaults: debuggable false, allowBackup true; usesCleartextTraffic true for target <= 27,
# false for >= 28, ignored for >= 38 (Network Security Configuration only)
rg -n 'android:(debuggable|allowBackup|usesCleartextTraffic|networkSecurityConfig|dataExtractionRules|targetSdkVersion)' apk_out/AndroidManifest.xml

# Hardcoded crypto (SecretKeySpec, Cipher.getInstance — common leak point)
rg -n 'SecretKeySpec|Cipher|AES|DES|encrypt|decrypt|base64' java_out apk_out
# Look for the hardcoded key argument passed to SecretKeySpec(key, "AES")

# Configuration candidates: generated resources and XML configs as well as code/assets
rg -n 'google_api_key|google_app_id|firebase_database_url|https?://' java_out apk_out/res/values apk_out/res/xml apk_out/assets

# Certificate analysis
apksigner verify --print-certs target.apk

# Asset inspection (images, data files bundled with APK)
rg --files apk_out/assets
```

Classify embedded values by capability before reporting: public client IDs, service configuration, credentials and private keys are different. Firebase client API keys identify projects; access depends on rules/authentication and the API used. Test read and write independently on controlled resources. See [Firebase API keys](https://firebase.google.com/docs/projects/api-keys).

Automated pass with MobSF (v4.6.9), read with manual verification: it flags common issues and misses business logic and context.

```bash
H='X-Mobsf-Api-Key: <key>'
HASH=$(curl -s -H "$H" -F 'file=@target.apk' http://127.0.0.1:8000/api/v1/upload | jq -r .hash)
curl -s -H "$H" -F "hash=$HASH" http://127.0.0.1:8000/api/v1/scan | jq    # returns when the scan finishes
curl -s -H "$H" -F "hash=$HASH" http://127.0.0.1:8000/api/v1/report_json | jq
```

### Dynamic analysis

```bash
# Instrument the selected boundary; load the Frida skill for runtime prerequisites
frida -U -f com.target.app -l observe_boundary.js

# Objection 1.12: REPL on the running app; -g and explore are deprecated aliases
objection -n com.target.app start
objection -n com.target.app start -s "android sslpinning disable" -s "android root disable"
#   android hooking list activities|services|receivers|class_loaders
#   android hooking watch class_method com.target.Class.method
#   android keystore list|detail|watch

# Drozer (ReversecLabs/drozer, 3.1.0 beta): exposed components called from a third-party app; module list in the IPC reference
adb forward tcp:31415 tcp:31415 && drozer console connect
dz> run app.package.attacksurface com.target.app
dz> run app.provider.query content://com.target.app.provider/
```

### Traffic interception

- Establish a baseline request through the configured proxy and identify the actual network stack.
- For CA trust, pinning failures and application-layer encryption, load [Android traffic and custom protocols](references/android-traffic-and-custom-protocols.md). A successful hook is not proof of backend acceptance.

### Storage analysis

Use the app's debug/test access or an explicitly privileged lab image to inspect private storage; ordinary `adb shell` cannot read another app's sandbox. Record the identity used for collection. Locate writers with `rg -n 'getSharedPreferences|openFileOutput|FileOutputStream|getDatabasePath|getExternalFilesDir|MediaStore' java_out`. Check preferences, databases, files, caches and logs against the sensitive operation, then confirm any cross-app exposure from the actual unprivileged caller. Jetpack `security-crypto` 1.1.0 deprecates all its APIs (`EncryptedSharedPreferences`, `EncryptedFile`) in favour of platform APIs and direct Keystore use: review it as legacy key management, not as protection.

### Android backup (.ab) analysis

On Android 12+, app data is excluded from `adb backup` for apps targeting API 31+ unless the documented debuggable opt-in applies. Check device/build support and actual archive contents; do not promise a backup before uninstalling. See [Android 12 restrictions](https://developer.android.com/about/versions/12/behavior-changes-12#adb-backup-restrictions). For existing `.ab` artifacts, read the header's compression/encryption fields and use [backup forensics](../../offensive-ctf/mobile-ctf/references/android-backup-forensics.md); do not assume every body is an unencrypted zlib stream.

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
- Objection: `objection -n com.target.app start` — `ios sslpinning disable`, `ios jailbreak disable`, `ios cookies get`, `ios ui dump`.
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
| MASVS-CODE | Untrusted input processing, dependencies and updates |
| MASVS-RESILIENCE | Code tampering, debugging, root/jailbreak detection |
| MASVS-PRIVACY | Data minimization, tracking and user controls |

Use the current [MASVS control groups](https://mas.owasp.org/MASVS/) when labeling findings; a control category is not a severity rating.

## Hybrid Android triage cue

Keep this layer at routing depth. When a sample shows both loader and native signs, treat it as a hybrid app and pivot to offensive-coding skills for implementation-level work.

- Managed entry: `classes*.dex` Java/Kotlin orchestration
- Native boundary: `System.loadLibrary`, `JNI_OnLoad`, `.so` checks/unpackers
- Runtime payload: `DexClassLoader` / `InMemoryDexClassLoader` second-stage code
- Instrumentation bridge: Frida hooks Java + native loader points

Deep-dive and patch path:

- `smali-dex-patching/references/dynamic-dex-and-native-loaders.md`
- `android-jni-ndk`
- `frida`

## Modern platform gotchas

Android:
- Separate runtime-version changes from target-SDK-gated changes; record compatibility flags and OEM behavior instead of assuming "latest Android" has one policy.
- **Play Integrity**: test the backend, not the device. Replay a token twice (the standard API degrades reused tokens to an empty device verdict and `UNEVALUATED` app and licensing verdicts; a backend must neither cache nor accept it); use a token minted for another package or a re-signed build (the backend must require `PLAY_RECOGNIZED` and match `appIntegrity.packageName`); change the request body under the same token (`requestDetails.requestHash`); wait past the freshness window (`requestDetails.timestampMillis`); install outside Play (`appLicensingVerdict` must be `LICENSED`); replay a classic-request nonce. `MEETS_BASIC_INTEGRITY` and `MEETS_STRONG_INTEGRITY` are optional labels on Android 13+: record which ones the backend accepts. A local patch or root-hiding module does not establish server acceptance. See [verdict definitions](https://developer.android.com/google/play/integrity/verdicts).
- **IPC**: use [Android IPC attack surface](references/android-ipc-attack-surface.md) for API/target-specific export, receiver, intent and grant conditions.
- **Native runtime**: use [android-jni-ndk](../../coding/android-jni-ndk/SKILL.md) for ABI, sanitizer, crash and 16 KB page-size constraints.
- **Staged code**: load [dynamic DEX and native loaders](../../offensive-coding/smali-dex-patching/references/dynamic-dex-and-native-loaders.md) for loader evidence, artifact completeness and modern runtime restrictions. A loader's presence alone does not classify an app as malware.

iOS:
- **TrustCache** + **CoreTrust** enforce signed-binary allow-lists in the kernel; unsigned/adhoc binaries need a jailbreak or a TrollStore-style CoreTrust bypass (patched in iOS 17.0). No `bfinject`/`Needle` era techniques apply.
- **App Attest** (`DCAppAttestService`) binds requests to a Secure Enclave key; server rejects forged attestations even with a working Frida hook — always validate bypass end-to-end against the backend, not just on-device.
- **Universal SSL pinning bypass** landscape: httptoolkit/frida-interception-and-unpinning covers OkHttp/Conscrypt/BoringSSL/NSURLSession/CFNetwork; fall back to per-library hooks (`SSL_CTX_set_custom_verify`, `SecTrustEvaluateWithError`) when custom pinners are used.
