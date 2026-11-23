# Android APK Analysis Procedure

Detailed workflow for analyzing Android APK files. Load this reference when the sample is identified as APK. For staged code and loader recovery, load [dynamic DEX and native loaders](../../../offensive-coding/smali-dex-patching/references/dynamic-dex-and-native-loaders.md); for runtime capture, [Frida DEX dumping](../../../offensive-tools/rev/frida/references/android-ios.md).

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
aapt2 dump badging sample.apk | rg "^package:|sdkVersion|uses-permission"

# Quick decompile to inspect package structure
jadx -d ./decompiled sample.apk
```

Read `targetSdkVersion` before predicting behavior: it selects which platform rules apply (next table), and Android 15 refuses to install apps targeting below 24.

If `jadx`/`aapt2` unavailable, use Python:
```python
import zipfile
with zipfile.ZipFile("sample.apk") as z:
    print([n for n in z.namelist() if not n.startswith("res/")])
```

## Platform rules that bound behavior

| Mechanism | Rule | Condition |
|---|---|---|
| Device Admin | Password and keyguard policies throw `SecurityException` (`RESET_PASSWORD` for target 24+, the others for target 29+). `WIPE_DATA` and `FORCE_LOCK` remain available | target 24+/29+ |
| Device Owner | Set only on an unprovisioned device | provisioning time |
| Restricted settings | Accessibility and notification-listener access cannot be enabled for sideloaded apps until the user allows restricted settings | Android 13+ |
| `BOOT_COMPLETED` | Delivered only after the first user launch; withheld for battery-restricted apps; pending intents cancelled when the app enters the stopped state | target 33+ for the battery rule; Android 15 for the stopped state |
| Foreground services | Each declares a type; a `BOOT_COMPLETED` receiver cannot start `dataSync`, `camera`, `mediaPlayback`, `phoneCall`, `mediaProjection` or `microphone` types | target 34+ / 35+ |
| Exact alarms | Need `SCHEDULE_EXACT_ALARM` or `USE_EXACT_ALARM`; the first is not pre-granted | target 31+ / 33+ |
| MediaProjection | Consent per capture session; projection stops when the screen locks | target 34+ / Android 15 QPR1 |
| OTP access | Untrusted notification listeners receive redacted OTP notifications; WebOTP-format SMS are withheld for three hours from all apps, standard OTP SMS from target 37+ | Android 15 / 17 |
| Dynamic loading | DEX/JAR/APK files read-only (target 34+); native files loaded with `System.load()` read-only, else `UnsatisfiedLinkError` (target 37+) | target 34+ / 37+ |

A sample's workaround for one of these rules is a triage cue: instructions to allow restricted settings, an Accessibility service that drives the install dialog, a VPN raised around installation, a bundled keybox for Play Integrity.

Sources: [Device Admin deprecation](https://developers.google.com/android/work/device-admin-deprecation), [restricted settings](https://support.google.com/android/answer/12623953), [broadcast exceptions](https://developer.android.com/develop/background-work/background-tasks/broadcasts/broadcast-exceptions), [Android 13 target changes](https://developer.android.com/about/versions/13/behavior-changes-13), [Android 14 target changes](https://developer.android.com/about/versions/14/behavior-changes-14), [Android 15 target changes](https://developer.android.com/about/versions/15/behavior-changes-15), [Android 15 all-app changes](https://developer.android.com/about/versions/15/behavior-changes-all), [Android 17 all-app changes](https://developer.android.com/about/versions/17/behavior-changes-all), [exact alarms](https://developer.android.com/develop/background-work/services/alarms/schedule).

## Manifest analysis

Read capabilities as clusters: the component that grants each one, and what to confirm in code.

| Capability | Manifest evidence | Confirm |
|---|---|---|
| Overlay and UI automation | `BIND_ACCESSIBILITY_SERVICE`, accessibility XML (`canRetrieveWindowContent`, `canPerformGestures`, `flagRequestFilterKeyEvents`), `SYSTEM_ALERT_WINDOW` | Target package list, injected HTML, permission self-grant |
| Device lockdown | `BIND_DEVICE_ADMIN`, device-admin XML (`force-lock`, `wipe-data`) | `lockNow()`, credential change through Accessibility |
| Screen capture | `foregroundServiceType="mediaProjection"`, `FOREGROUND_SERVICE_MEDIA_PROJECTION` | `createScreenCaptureIntent`, encoder, VNC or WebRTC session |
| Keylogging | `BIND_INPUT_METHOD`, or accessibility key-event filtering | Second input method, logging sink |
| SMS/OTP and call data | default-SMS role request, `RECEIVE_SMS`, `READ_SMS`, `READ_CALL_LOG`, `READ_CONTACTS`, `BIND_NOTIFICATION_LISTENER_SERVICE` | SMS receiver, default-handler prompt, notification access |
| Staging | `REQUEST_INSTALL_PACKAGES`, `BIND_VPN_SERVICE` | PackageInstaller session, VPN raised around install |
| Scheduling | `RECEIVE_BOOT_COMPLETED`, `SCHEDULE_EXACT_ALARM`, `foregroundServiceType` list | Boot receiver, exact-alarm request, job intervals |

High-risk permissions by effect: `READ_SMS`/`RECEIVE_SMS`/`SEND_SMS` (SMS theft, interception, premium fraud), `READ_CONTACTS`, `CAMERA`/`RECORD_AUDIO` (surveillance), `ACCESS_FINE_LOCATION` (tracking), `REQUEST_INSTALL_PACKAGES` (dropper), `SYSTEM_ALERT_WINDOW` (overlay), `BIND_ACCESSIBILITY_SERVICE` (gestures, key events, auto-grant), `BIND_DEVICE_ADMIN` (anti-uninstall).

Suspicious components: services that run in the foreground; receivers for `BOOT_COMPLETED`, `CONNECTIVITY_CHANGE`, `SMS_RECEIVED`; providers exposed without permissions; activities with intent filters for deep links.

## Distribution and staging

- **Store dropper with late switch**: stage one is quiet, without risky permissions, behind an "update" screen; the payload arrives later. Static review of the store build is incomplete by design: look for embedded encrypted stages and exercise the update path. See the [ThreatFabric dropper survey](https://www.threatfabric.com/blogs/android-droppers-the-silent-gatekeepers-of-malware).
- **Sideload lures**: fake stores, fake Play Protect or in-app update prompts; an Accessibility service drives the install of the next stage. See [BTMOB](https://www.welivesecurity.com/en/malware/btmob-stealthy-rat-burrowing-deep-android-devices/).
- **Preinstalled**: code in the system partition hooked into Zygote, not an APK install. See [Keenadu](https://securelist.com/keenadu-android-backdoor/118913/).
- **Stage layouts**: in-memory DEX (`InMemoryDexClassLoader`), DEX loaded with `DexClassLoader` from a downloaded plugin, native libraries that hook other apps. Recovery: loaders reference above.

## Decompilation

### jadx (preferred)

```bash
# Decompile to Java source
jadx -d ./decompiled sample.apk

# Decompile with deobfuscation
jadx -d ./decompiled --deobf sample.apk

# Search decompiled code
rg -n "http|https|api\.|\.com|\.net|\.org" ./decompiled/sources/
rg -n "encrypt|decrypt|AES|DES|RC4|XOR|Base64" ./decompiled/sources/
rg -n "Runtime|exec|ProcessBuilder|loadLibrary|loadClass" ./decompiled/sources/
```

### apktool (smali level)

```bash
# Decode to smali + resources
apktool d sample.apk -o ./decoded

# Inspect smali for:
rg -n "Ljava/net/URL|Ljava/net/HttpURLConnection" ./decoded/smali/
rg -n "Ljavax/crypto" ./decoded/smali/
rg -n "Ljava/lang/Runtime;->exec" ./decoded/smali/
```

Use smali when jadx output is damaged by obfuscation.

## Behaviours and how to confirm

| Behaviour | Needs | Confirmation | Example |
|---|---|---|---|
| Overlay on targeted apps | AccessibilityService or overlay window; target list | HTML or credential forms in assets or SQLite; list updated from C2 | [Rokarolla](https://zimperium.com/blog/rokarolla-android-banker-with-complete-device-takeover-capabilities), 217 targeted apps |
| Lock or PIN ransomware | Device Admin (`lockNow`) plus Accessibility | Lock and credential-change calls, ransom screen | [DroidLock](https://zimperium.com/blog/total-takeover-droidlock-hijacks-your-device) |
| SMS/OTP, contacts, call log | SMS role or `RECEIVE_SMS`, contacts and call-log permissions | SMS receiver, default-handler request, export sink | [Hirudo](https://www.threatfabric.com/blogs/hirudo-from-fake-updates-to-patched-banking-apps) SMS collection |
| Permission self-grant | Accessibility gestures | Permission prompts right after the service is enabled | [BTMOB](https://www.welivesecurity.com/en/malware/btmob-stealthy-rat-burrowing-deep-android-devices/) |
| Keylogging | Custom input method or accessibility key-event filter | Second keyboard, keylogger commands | [BeatBanker](https://securelist.com/beatbanker-miner-and-banker/119121/) virtual keyboard |
| Screen capture, live view | MediaProjection with a `mediaProjection` service | Capture intent, encoder, VNC or WebRTC session | [RedWing](https://zimperium.com/blog/redwing-a-mobile-malware-as-a-service-operation) |
| Protection defence | Commands or config that disable defenses | `<disable_google_play>`-style commands; install plus VPN in one app | [Rokarolla](https://zimperium.com/blog/rokarolla-android-banker-with-complete-device-takeover-capabilities), [StreamRat](https://www.threatfabric.com/blogs/from-meta-ads-to-full-device-takeover-uncovering-streamrat) |

Target lists are frequently delivered or updated by the C2: a sample that overlays nothing in the lab is not benign, it is unconfigured.

## Network communication

1. Search for URL/IP construction: `URL`, `HttpURLConnection`, `OkHttp`, `Retrofit`, `Volley`
2. Check for hardcoded endpoints in strings, SharedPreferences, assets, or raw resources
3. Firebase: `google-services.json` in assets, Firebase Realtime DB URLs
4. MQTT, WebSocket, raw socket connections
5. Telegram bot API usage: `api.telegram.org`
6. Legitimate services as transport: Firebase Realtime Database, Storage and Remote Config, FCM, Google Apps Script and Drive, GitHub, pastebin. Hostname allow-lists do not separate them from benign traffic: pivot on embedded project IDs, bot tokens, URLs, and on an SDK the app has no feature for. Examples: [Arsink](https://zimperium.com/blog/the-rise-of-arsink-rat) (Firebase, Telegram, Google Apps Script), [Necro](https://securelist.com/necro-trojan-is-back-on-google-play/113881) (Remote Config as C2), [LianSpy](https://securelist.com/lianspy-android-spyware/113253/) (cloud and pastebin).

## Dynamic loading

1. `DexClassLoader` / `InMemoryDexClassLoader` — DEX loaded at runtime
2. `Class.forName()` + `Method.invoke()` — reflection-based execution
3. Native libraries: `System.loadLibrary()` → check `lib/` for `.so` files
4. Downloaded DEX/APK from C2 → second-stage payload

## Native code

If `lib/` contains `.so` files:
1. Identify architecture: `armeabi-v7a`, `arm64-v8a`, `x86`, `x86_64`
2. Extract and analyze with `r2`, Ghidra, or `objdump`
3. Look for JNI functions: `Java_<package>_<class>_<method>`, `RegisterNatives`
4. Native code often handles: C2 communication, encryption, anti-debug, root detection, string decryption

## Anti-analysis

- **Protectors**: commercial packers with native-heavy loaders (SecAPK in [Necro](https://securelist.com/necro-trojan-is-back-on-google-play/113881) and [SoumniBot](https://securelist.com/soumnibot-android-banker-obfuscates-app-manifest/112334)) and OLLVM-obfuscated libraries. Expect to recover strings and the real entry point at runtime.
- **Malformed containers**: APKs that are non-standard yet still install, to break analysis tools. When `jadx`, `apktool` and an on-device install disagree, compare `unzip -l`, `aapt2 dump badging` and `apksigner verify`, then repair the working copy. See [Malformed APKs as an anti-analysis technique](https://www.cleafy.com/cleafy-labs/malformed-apks-as-an-anti-analysis-technique-malfixer-tool).
- **Environment checks**: debugger, ADB, emulator, root. Reactions include silent exit and clearing logcat (Necro). Run samples on a non-emulated image and capture logcat off-device.
- **Human-like input**: randomized delays between Accessibility actions hide automation from behavior-based detection.

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

Identify packer, compiler and obfuscator with [APKiD](https://github.com/rednaga/APKiD) (v3.2.0): `apkid app.apk`, `apkid -j app.apk` for JSON, `-r` for a directory, `-st` to list embedded trackers.

## Family indicators

- **Overlay bankers and RATs (2024–2026 reports)**: Anatsa, Necro, BeatBanker, Rokarolla, RedWing, Arsink, StreamRat, Hirudo, BTMOB. Shared core: Accessibility, C2-delivered target lists, staging, legitimate services as transport.
- **Ransomware**: DroidLock (lock and credential change).
- **Spyware**: LianSpy (cloud and pastebin exfiltration).
- **Firmware implants**: Keenadu.
- **Classic families in older samples**: Cerberus, Anubis, SharkBot (overlay, SMS interception, Device Admin).

Attribute by behavior and code, not by a label found in strings.

## Detection resources

- [ATT&CK for Mobile](https://attack.mitre.org/matrices/mobile/) for technique IDs.
- [Play Protect PHA categories](https://developers.google.com/android/play-protect/phacategories) for classification names.
- [ESET malware-ioc](https://github.com/eset/malware-ioc) for per-family network and file IoCs; [Android Security Bulletins](https://source.android.com/security/bulletin) for platform fixes.
- Public YARA collections carry little Android material: `mobile_malware/` in Yara-Rules/rules is empty.

## Report requirements

- Package name, main activity, target SDK and the platform rules that bound the behavior
- Permissions with risk assessment, grouped by capability
- C2 endpoints with provenance (hardcoded, config, native, legitimate service)
- Encryption algorithm and key material if recoverable
- Dynamic loading behavior and recovered stages
- Persistence mechanism
- Family attribution if supported
