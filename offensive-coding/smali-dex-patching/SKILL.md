---
name: smali-dex-patching
description: "Auth/lab dev: patch shipped Android APKs at the DEX/smali level — bypass root/emulator checks, disable SSL pinning, strip license verification, inject logging, or alter arbitrary managed-code logic. Covers apktool decompile/rebuild, smali syntax, common patch patterns (return-void, const/4 v0 + return, method-body neutralization), multi-DEX and split-APK handling, zipalign, and v1–v4 APK signing with apksigner and uber-apk-signer. Use for authorized RE, mobile pentest, and CTF work; not for tampering with software you don't own or aren't authorized to test."
license: MIT
compatibility: "apktool 2.11+ (smali/baksmali 3.0+), Android build-tools 34.0.0+ (apksigner, zipalign), Java 17+. Optional: uber-apk-signer (multi-scheme signing), jadx-cli / jadx-gui (Java view of DEX), apk-mitm (fast pinning bypass), apksigner v4 for idsig files, apk.sh for split-APK bundling."
metadata:
  author: AeonDave
  version: "1.0"
---

# Smali / DEX Patching

Patch the managed-code side of an Android APK: locate the check, edit the smali, rebuild, re-sign, install. Pair with `mobile-technique` for triage and target identification, `offensive-tools/rev/jadx` for the readable Java view, `android-jni-ndk` when the check lives in a native `.so`, and `reversing-technique` for deep obfuscated / packed samples.

Use only against APKs you are authorized to test.

---

## When to activate

- Confirmed pentest scope on an Android APK you can extract from a device or ship a build of.
- Frida hook exists in theory but the target detects Frida (`ptrace`, `/proc/self/status`, `TracerPid`) — static patching is a resilient alternative.
- Bug bounty writeup requires PoC via a rebuilt APK.
- CTF challenge distributes a single `.apk` file with the flag or a check to defeat.
- Confirming a vulnerability class ("this crypto key is embedded") by editing the check-in-place.

Not for: dynamic-only findings, native-code-only checks (use JNI/NDK skill + Frida + Ghidra), or app resigning without authorization on Play-distributed software.

---

## Core workflow (memorize)

```bash
# 1. Decompile
apktool d target.apk -o unpacked/

# 2. Locate the check in Java via jadx-gui or grep in unpacked/
grep -rn "isRooted\|isDebuggable\|SafetyNet\|Frida\|selinux\|Xposed\|Magisk\|su\|/system/xbin" unpacked/smali*/

# 3. Edit the .smali file → change return value / neutralize body

# 4. Rebuild (produces dist/target.apk unsigned)
apktool b unpacked/ -o patched-unsigned.apk

# 5. zipalign — REQUIRED before v2+ signing
zipalign -P 16 -f -v 4 patched-unsigned.apk patched-aligned.apk

# 6. Sign (creates or reuses a debug keystore)
apksigner sign --ks debug.keystore --ks-pass pass:android --key-pass pass:android \
    --ks-key-alias androiddebugkey --out patched-signed.apk patched-aligned.apk

# 7. Verify
apksigner verify --verbose --print-certs patched-signed.apk

# 8. Install
adb install -r patched-signed.apk
# If the app was previously installed with a different signing key, uninstall first:
adb uninstall com.target.app && adb install patched-signed.apk
```

Golden rule: **decompile → find in Java → edit in smali → rebuild → align → sign → install**. Skipping any step (especially `zipalign -P 16`) breaks the install path on modern devices.

---

## DEX and smali essentials

- Every APK contains one or more DEX files (`classes.dex`, `classes2.dex`, ...); apktool disassembles each into `smali/`, `smali_classes2/`, ...
- Smali is the human-readable form of Dalvik bytecode. Assembling and disassembling are lossless.
- Compact DEX (**CDEX**) is a runtime-optimized format used by ART's `dex2oat`; it's not in the APK, and you don't touch it directly.
- ART verifies method signatures — a broken register count or unbalanced local frame fails at load.
- Real malware and modern apps often split logic across **Java/Kotlin managed code + native `.so` + runtime-loaded DEX**. If the check is not in the obvious Java class, look for `System.loadLibrary`, `JNI_OnLoad`, `DexClassLoader`, `InMemoryDexClassLoader`, and asset/blob extraction before assuming the app is static-only.

### Dynamic DEX / hybrid loader signs

- `DexClassLoader` / `InMemoryDexClassLoader` in `dalvik.system` = code shipped or decoded at runtime.
- `Class.forName` / `getDeclaredMethod` + reflection after `loadDex` = second-stage module execution.
- `System.loadLibrary` + `JNI_OnLoad` + `RegisterNatives` = native bootstrap path that may decode or load a payload.
- `FileInputStream` or `AssetManager` reads from a blob/zip inside APK or from a downloaded file, followed by `DexClassLoader` = typical dropper pattern.
- `Frida` is useful at this boundary to watch the loader, dump the DEX buffer, or hook the `JNI_OnLoad` symbol before the app hides its logic.

These patterns are covered in the deep-dive: [references/dynamic-dex-and-native-loaders.md](references/dynamic-dex-and-native-loaders.md).

### Types (single-letter descriptors)

| Descriptor | Java type |
|------------|-----------|
| `V` | `void` (return only) |
| `Z` | `boolean` |
| `B` | `byte` |
| `S` | `short` |
| `C` | `char` |
| `I` | `int` |
| `J` | `long` (uses two registers) |
| `F` | `float` |
| `D` | `double` (uses two registers) |
| `L<class>;` | Reference to class, e.g. `Ljava/lang/String;` |
| `[<type>` | Array, e.g. `[B` (`byte[]`), `[Ljava/lang/String;` (`String[]`) |

Method descriptor form: `(<args>)<returnType>`. Example: `(Ljava/lang/String;I)Z` = `boolean method(String, int)`.

### Registers

- Every method declares its register count. Two conventions:
  - `.registers N` — total registers including parameters.
  - `.locals M` — non-parameter registers; ART computes total.
- Register names:
  - `v0`, `v1`, ..., `vN` — locals, indexed from 0.
  - `p0`, `p1`, ..., `pM` — parameters. In a non-static method, `p0` = `this`.
- Wide types (`J`, `D`) occupy two consecutive registers.
- Register count > 16 requires the `/from16` variant of instructions (e.g. `move-object/from16`).

### Common opcodes (top 20 you'll see)

| Opcode | Meaning |
|--------|---------|
| `const/4 vA, #B` | Load 4-bit signed constant into `vA` (fast path for 0..7, -8..-1) |
| `const/16 vA, #BB` | Load 16-bit signed constant |
| `const-string vA, "text"` | Load string reference |
| `move-result vA` / `move-result-object vA` | Copy the last invoked method's return value |
| `return-void` | Return from void method |
| `return vA` | Return primitive |
| `return-object vA` | Return object reference |
| `invoke-virtual { }, Lcls;->method(...)T` | Instance-method call (dynamic dispatch) |
| `invoke-static { }, Lcls;->method(...)T` | Static method call |
| `invoke-direct { }, Lcls;-><init>(...)V` | `<init>` / private / super — no dispatch |
| `invoke-super { }, Lcls;->method(...)T` | Superclass method |
| `if-eqz vA, :label` | Branch if `vA == 0` (used for `boolean false`) |
| `if-nez vA, :label` | Branch if `vA != 0` |
| `iget vA, vB, Lcls;->field:T` | Read instance field of `vB` into `vA` |
| `iput vA, vB, Lcls;->field:T` | Write `vA` into instance field of `vB` |
| `sget vA, Lcls;->field:T` | Static field read |
| `sput vA, Lcls;->field:T` | Static field write |
| `new-instance vA, Lcls;` | Allocate uninitialized object |
| `check-cast vA, Lcls;` | Cast check |
| `goto :label` | Unconditional branch |

For the full opcode table: [source.android.com/docs/core/runtime/dalvik-bytecode](https://source.android.com/docs/core/runtime/dalvik-bytecode).

---

## Common patch patterns (memorize five)

### 1. Force boolean return `false`

Original:

```smali
.method public isRooted()Z
    .registers 4
    # complex logic checks for su, magisk, etc.
    invoke-direct { p0 }, Lcom/target/RootDetect;->hasSu()Z
    move-result v0
    return v0
.end method
```

Patched (always return `false`):

```smali
.method public isRooted()Z
    .registers 2
    const/4 v0, 0x0
    return v0
.end method
```

- `.registers 2` — 1 local (`v0`) + 1 parameter (`p0` = `this`). Reduce to match the new body.
- `const/4 v0, 0x0` — load `false` (0) into `v0`.
- `return v0` — return.

### 2. Force boolean return `true`

```smali
.method public isValidLicense()Z
    .registers 2
    const/4 v0, 0x1
    return v0
.end method
```

### 3. Void method neutralization

Original constructor / init that runs a check:

```smali
.method public onCreate(Landroid/os/Bundle;)V
    .registers 3
    invoke-super { p0, p1 }, Landroid/app/Activity;->onCreate(Landroid/os/Bundle;)V
    invoke-direct { p0 }, Lcom/target/App;->checkIntegrity()V   # this line kills the app on tamper
    return-void
.end method
```

Patched (remove the check, keep the super call):

```smali
.method public onCreate(Landroid/os/Bundle;)V
    .registers 3
    invoke-super { p0, p1 }, Landroid/app/Activity;->onCreate(Landroid/os/Bundle;)V
    return-void
.end method
```

Do not `return-void` before `invoke-super` — the parent must run for lifecycle to work.

### 4. Bypass an equality check

Original:

```smali
    invoke-virtual { p1 }, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :cond_fail
    # ... success path ...
    :cond_fail
    # ... fail path ...
```

Patched (invert the branch):

```smali
    invoke-virtual { p1 }, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-nez v0, :cond_fail                                       ← changed eqz → nez
```

Or force the check to succeed unconditionally:

```smali
    const/4 v0, 0x1
    # ... skip to success path
```

### 5. Neutralize SSL pinning by editing `check` result

OkHttp `CertificatePinner.check`:

```smali
.method public final check(Ljava/lang/String;Ljava/util/List;)V
    .registers 6
    return-void                          ← accept anything
.end method
```

For custom `TrustManager`:

```smali
.method public checkServerTrusted([Ljava/security/cert/X509Certificate;Ljava/lang/String;)V
    .registers 4
    return-void
.end method
```

Combine with clearing `network_security_config.xml` pinning rules in `res/xml/network_security_config.xml`.

---

## Locating the target check

Read in Java (jadx), patch in smali. Two tools:

```bash
# Fast readable view
jadx-gui target.apk

# Search all smali for markers
grep -rEn 'RootBeer|isRooted|SafetyNet|Xposed|Magisk|Frida|/system/xbin/su|isDebuggerConnected|Debug.isDebuggerConnected' unpacked/

# Search AndroidManifest for debuggable/allowBackup
grep -E 'android:debuggable|android:allowBackup' unpacked/AndroidManifest.xml
```

Common Java classes to grep for:

- `RootBeer` (`com.scottyab.rootbeer.RootBeer`) — very common root detector; every `isRooted*()` method returns `Z`.
- `okhttp3.CertificatePinner`, `com.datatheorem.android.trustkit.pinning`.
- `SafetyNetClient.attest(...)` — now retired; likely replaced by `IntegrityManager.requestIntegrityToken()` (Play Integrity API).
- `com.google.android.play.core.integrity.IntegrityManager` — Play Integrity; server-side verification means patching only breaks the client hint, not the server verdict.
- `Debug.isDebuggerConnected()`, `ApplicationInfo.FLAG_DEBUGGABLE`.

Locate the corresponding `.smali` file: `smali/<full/qualified/name>.smali` or under `smali_classesN/`.

Multi-DEX targets: your class may live in `classes2.dex` or `classes3.dex` → after `apktool d` these become `smali_classes2/`, `smali_classes3/`. Search across all of them.

---

## Manifest patches (concrete)

Enable debuggable + trust user CA (needed for Burp interception on Android 7+):

```bash
# Make debuggable
sed -i 's|<application |<application android:debuggable="true" |' unpacked/AndroidManifest.xml

# Trust user certs — replace or add network_security_config.xml
cat > unpacked/res/xml/network_security_config.xml <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="true">
        <trust-anchors>
            <certificates src="system" />
            <certificates src="user" />
        </trust-anchors>
    </base-config>
</network-security-config>
EOF

# Reference it in the manifest (if not already)
sed -i 's|<application |<application android:networkSecurityConfig="@xml/network_security_config" |' unpacked/AndroidManifest.xml
```

- Trusting user certs works from Android 7+ only if `network_security_config.xml` declares it.
- Some apps set `android:extractNativeLibs="false"` — do not change unless needed; APK layout differs.

---

## Multi-DEX and split APKs

- **Multi-DEX**: apktool handles automatically. Locate your target class in the correct `smali_classesN/`; apktool assigns DEX numbers at build.
- **Split APKs (App Bundle → APK Set)**: modern apps ship as `base.apk` + `split_<density>.apk` + `split_<language>.apk` + `split_<abi>.apk`. Install:
  ```bash
  adb install-multiple base.apk split_arm64_v8a.apk split_xxhdpi.apk split_en.apk
  ```
- To patch a split-APK app:
  - Extract from device: `adb shell pm path com.target.app` → returns paths; pull each.
  - Use **`apk.sh`** (github.com/ax/apk.sh) to combine splits into a single patchable APK. Then patch, rebuild, re-split or install as single.
  - Alternative: patch only `base.apk` where the check lives, resign, install alongside untouched splits with `adb install-multiple`.

Reason: signature verification is per-split; re-signing base but not splits fails install with a mismatched-signature error.

---

## Signing schemes v1–v4

| Scheme | What it signs | When required |
|--------|---------------|---------------|
| v1 (JAR signing) | Individual entries via `META-INF/*.SF`, `.RSA`, `.MF` | Android 6- default; still checked on newer versions if v2+ absent |
| v2 (APK Signature Scheme v2) | Whole-file signature block outside the JAR structure | Android 7+ minimum for compatibility; per-file entries can't be tampered |
| v3 | v2 + **signature lineage** for key rotation | Android 9+; use if you need to rotate signing keys |
| v3.1 | v3 with per-signer scope constraints | Android 13+; niche |
| v4 | Fs-verity / streaming compatibility; produces `<apk>.idsig` sidecar file | Android 11+; required for Play delivery of certain configurations |

`apksigner` handles all four. Modern flow:

```bash
# Sign v1 + v2 + v3 in one shot
apksigner sign \
    --ks debug.keystore --ks-pass pass:android --key-pass pass:android \
    --ks-key-alias androiddebugkey \
    --v1-signing-enabled true \
    --v2-signing-enabled true \
    --v3-signing-enabled true \
    --out patched-signed.apk patched-aligned.apk

# Verify
apksigner verify --verbose --print-certs patched-signed.apk
```

`uber-apk-signer` wraps this with an embedded debug keystore for one-liners:

```bash
java -jar uber-apk-signer.jar -a patched-aligned.apk
```

Auto-verifies. Supports v1/v2/v3/v4 + lineage.

Debug keystore (one-time creation):

```bash
keytool -genkey -v -keystore debug.keystore -storepass android \
    -alias androiddebugkey -keypass android -keyalg RSA -keysize 2048 \
    -validity 10000 -dname "CN=Android Debug,O=Android,C=US"
```

Or use the one Android Studio auto-generates at `~/.android/debug.keystore`.

---

## Reinstall over previously-signed APK

Android refuses to install an APK signed with a different key on top of an existing install of the same package:

```
INSTALL_FAILED_UPDATE_INCOMPATIBLE: Package … signatures do not match
```

Options:

1. **Uninstall first**: `adb uninstall com.target.app` (loses app data).
2. **Change the package name** (extreme; breaks intents/uris — only works for standalone reversing).
3. **Rotate the original signature** with a lineage file (requires the original private key — you don't have it).

Realistic answer: uninstall and reinstall. For persistent data testing, use `adb backup` before uninstall (if the app allows), or run against an emulator with snapshot support.

---

## Verification checklist before install

- `apksigner verify --verbose patched-signed.apk` — reports which schemes are signed. Fail = broken.
- `unzip -p patched-signed.apk AndroidManifest.xml | file -` → should be "Android binary XML" (means apktool assembled correctly).
- `aapt dump badging patched-signed.apk | head` — package name, permissions, min/target SDK.
- `zipalign -c -v 4 patched-signed.apk` — verify alignment. `-P 16` for 16 KB `.so` alignment on modern APKs.

---

## When patching fails at rebuild

`apktool b` errors are usually one of:

| Error | Fix |
|-------|-----|
| `resource id 0x7f0x0000 already used` | Two mods added to `public.xml`; delete duplicate or use `apk.sh` bundling |
| `Error: could not decode arsc file` | Resource decoding failed on decompile — retry with `apktool d -r` (skip resources); patch and rebuild without resources |
| `Invalid resource directory name` | Non-standard folder in res/; check `apktool.yml` `doNotCompress` list |
| `Method too large` (V/DEX opcodes) | Method size limit; smali edit added too many instructions. Refactor into a helper method |
| `unresolved reference to <class>;` | You referenced a class that doesn't exist; check descriptor spelling |
| `.registers` mismatch | Explicit register count doesn't match usage; recount or use `.locals` |

---

## Bulk-run pinning bypass (fast triage)

`apk-mitm` — automated pinning strip (network_security_config + common libs):

```bash
npm install -g apk-mitm
apk-mitm target.apk        # produces target-patched.apk
```

Doesn't cover custom pinning implementations — for those, patch smali or hook with Frida.

---

## Anti-patterns

- **Blindly `return-void` on `<clinit>`** — static initializer skipped; static fields remain `null`, NullPointerException at first use.
- **Ignoring `.registers` after editing** — mismatched local count = load-time verifier error, silent install fail.
- **Signing with v1 only** — Android 7+ prefers v2. v1-only APKs work but fail Play Integrity and modern hardware attestation.
- **Assuming Play Integrity bypass** — server verifies the token independently; patching the client only breaks the client-side hint. Real bypass requires forging server-side attestation, which is out of scope for this skill.
- **Editing `META-INF/*.SF` manually** — signature invalid after apktool rebuild; always use `apksigner sign`.
- **Adding `zipalign -f 4` without `-P 16`** — legacy 4-byte alignment; modern APKs with uncompressed `.so` need page alignment.
- **Patching a modified app in place, then re-decompiling for a second edit** — apktool bookkeeping (`apktool.yml`) drifts; start each edit from the pristine target APK.
- **Not testing with `apksigner verify` before install** — install fails silently with an unhelpful `INSTALL_PARSE_FAILED_NO_CERTIFICATES`.

---

## Resources

Load on demand:

- [references/smali-syntax-and-opcodes.md](references/smali-syntax-and-opcodes.md) — full opcode groups, register conventions, type descriptors, method invocation forms, `try/catch`, `.line` directives, common gotchas; load when writing non-trivial patches
- [references/common-patch-patterns.md](references/common-patch-patterns.md) — root detection (RootBeer, custom checks), emulator/VM detection, Frida/Magisk/Xposed detection, SSL pinning (OkHttp, TrustKit, custom TrustManagers), debug/tamper checks, license verification, Play Integrity client-side hints; load when you know the target class and need the right patch shape
- [references/apktool-rebuild-and-signing.md](references/apktool-rebuild-and-signing.md) — apktool options, `apktool.yml`, aapt/aapt2 selection, zipalign parameters, apksigner v1/v2/v3/v4 flow, uber-apk-signer, debug keystore, split-APK bundling with apk.sh; load when the rebuild/sign step misbehaves
- [references/dex-format-and-multidex.md](references/dex-format-and-multidex.md) — DEX file structure, string/type/proto/method/field tables, CDEX quick note, multi-DEX layout, MethodID limit (64k) workarounds, DEX injection, custom class loading; load when the target has DEX limits or you need to add substantial new code
- [references/dynamic-dex-and-native-loaders.md](references/dynamic-dex-and-native-loaders.md) — hybrid Java/Kotlin + native `.so` + runtime DEX loader patterns (`DexClassLoader`, `InMemoryDexClassLoader`, `JNI_OnLoad`, `RegisterNatives`), Frida boundary hooks, payload recovery flow; load when the target logic is staged or hidden behind loader stubs
- [references/detection-evasion.md](references/detection-evasion.md) — anti-tamper checks embedded in target (CRC of APK, signature verification, hash of `classes.dex`), how to identify and neutralize; hidden API restrictions (LSPosed HiddenApiBypass), integrity attestation client-side handling; load when a patched APK crashes or bricks itself post-install
- [references/hooking-vs-patching.md](references/hooking-vs-patching.md) — decision matrix: static patch (this skill) vs runtime hook (Frida/LSPosed) vs manifest-only edits; when to combine; workflows for handoff between hooks and patches; load when planning the intervention strategy
