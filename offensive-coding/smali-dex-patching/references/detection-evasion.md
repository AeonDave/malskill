# Detection Evasion (Anti-Tamper)

Load when a patched APK installs but crashes on launch, refuses to run, or silently reports tampering. Covers self-integrity checks, signature validation, hidden API restrictions, and PlayIntegrity/attestation client-side hints.

## Self-integrity checks

Apps commonly verify their own integrity via:

1. **Signature check** — `PackageManager.getPackageInfo(pkg, PackageManager.GET_SIGNING_CERTIFICATES)` and compare hash of the signing certificate.
2. **DEX hash check** — read `classes.dex` from own APK, compute SHA-256, compare against baked-in expected.
3. **CRC of `AndroidManifest.xml`** or other resources.
4. **APK size check** — trivial but common; original APK is X bytes.
5. **Installer package check** — `getInstallerPackageName()` = `com.android.vending` (Play Store).

Each becomes a boolean method returning "tampered" — patch to return `false`.

### Signature check example

Java:

```java
private boolean isValidSignature() {
    try {
        PackageInfo info = pm.getPackageInfo(getPackageName(), PackageManager.GET_SIGNING_CERTIFICATES);
        for (Signature sig : info.signingInfo.getApkContentsSigners()) {
            String hash = sha256(sig.toByteArray());
            if (!hash.equals(EXPECTED_HASH)) return false;
        }
        return true;
    } catch (Exception e) {
        return false;
    }
}
```

Smali equivalent (near the top of the method — force `true` return):

```smali
.method private isValidSignature()Z
    .registers 2
    const/4 v0, 0x1
    return v0
.end method
```

### DEX hash check example

Common pattern:

```java
byte[] dex = readAsset("classes.dex");                 // or File(applicationInfo.sourceDir)
String actual = sha256(dex);
if (!actual.equals(BUILT_IN_HASH)) killApp();
```

Patch by replacing the entire check with a no-op, OR by making `killApp()` a no-op:

```smali
.method private killApp()V
    .registers 1
    return-void
.end method
```

Second option is often safer — kills the entire tamper-response ability without needing to find every callsite.

### Installer package check

```java
String installer = getPackageManager().getInstallerPackageName(getPackageName());
if (!"com.android.vending".equals(installer)) return DEV_MODE;
```

Patch return value in the method that gates on this, or force `getInstallerPackageName()` to return "com.android.vending":

```smali
# Hard to patch getInstallerPackageName without extra work.
# Easier: patch the caller's if/else.
```

## APK size check

```java
File apk = new File(getApplicationInfo().sourceDir);
if (apk.length() != EXPECTED_SIZE) markTampered();
```

Simple: patch `markTampered()` to no-op, or patch the constant `EXPECTED_SIZE` to match your rebuild size.

## Hidden API restrictions bypass

Android 9+ restricts reflection access to non-SDK APIs (`AccessDeniedException`, warnings, or silent failure). If your patch injects code that calls hidden APIs (e.g. `ActivityThread.currentApplication()` reflectively), you'll hit this.

### Detection

Symptoms:

```
NoSuchMethodException: android.app.ActivityThread#currentApplication
NoSuchFieldException: dalvik.system.VMRuntime#setHiddenApiExemptions
Accessing hidden method [...] (max target o, reflection, denied)
```

### LSPosed HiddenApiBypass

Library that lifts the restriction from within your app process:

```gradle
implementation 'org.lsposed.hiddenapibypass:hiddenapibypass:4.3'
```

```kotlin
// In Application.onCreate() BEFORE any hidden API is used
if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
    HiddenApiBypass.addHiddenApiExemptions("L")   // exempt everything
}
```

Or explicit prefixes:

```kotlin
HiddenApiBypass.addHiddenApiExemptions(
    "Landroid/app/",
    "Ldalvik/system/",
)
```

Approach:

- Primary `HiddenApiBypass` — uses `Unsafe`; stable across Android 10+.
- Alternative `LSPass` — faster init, doesn't use `Unsafe`; may be blocked in future Android releases.

Both expose the same API.

### Not needed for `@FastNative`/`@CriticalNative`

The `dalvik.annotation.optimization.FastNative`/`CriticalNative` annotations are recognized by ART based on their FQN. Declare the annotation classes in your app package (see `android-jni-ndk/references/fast-critical-native.md`). No hidden-API bypass needed.

## Play Integrity API — the reality

`IntegrityManager.requestIntegrityToken(...)` returns a token. The token is:

- Signed by Google servers.
- Contains: package name, hash of the APK signing cert, request nonce, device integrity verdict (`MEETS_DEVICE_INTEGRITY`, `MEETS_BASIC_INTEGRITY`, `MEETS_STRONG_INTEGRITY`).
- Verified server-side by the app backend.

You **cannot** forge this token from a patched client. What you can do:

1. **Skip the client-side check** — patch the callsite that requests the token to skip and pretend success. Server-side, no token = usually rejected. Only works if the server implements Integrity as advisory, not gating.
2. **Server-side bypass** — out of scope for smali patching; requires server code access or a MITM against the backend.
3. **Bypass the client-side "integrity failed → show error" logic** — the app receives a real "not integrity-checked" verdict but you patch the UI code that acts on it. Server may still reject API calls.

Realistic: Play Integrity gates trivially defeat unauthorized bypass. Focus on the specific check the pentest scope requires, not "bypass Play Integrity" as a general goal.

### Verdicts in a nutshell

- `MEETS_DEVICE_INTEGRITY` — hardware-backed, requires unmodified bootloader + Play Protect (Android 13+ uses key attestation).
- `MEETS_BASIC_INTEGRITY` — recognizable Android + Play Services present.
- `MEETS_STRONG_INTEGRITY` — hardware key attestation + valid state.

Magisk `PlayIntegrityFix` module bypasses `MEETS_BASIC_INTEGRITY` on rooted devices; does not bypass `MEETS_STRONG_INTEGRITY`.

## SafetyNet (fully retired 2025-01-31)

The pre-Play-Integrity API. No longer functional. If a target APK uses `SafetyNetClient.attest(...)`, the call returns an error. Ideally patch the callsite to short-circuit with a success stub.

## Anti-Frida detection

Common markers:

```java
// Check /proc/self/status for TracerPid
public boolean isDebugged() {
    try (BufferedReader br = new BufferedReader(new FileReader("/proc/self/status"))) {
        String line;
        while ((line = br.readLine()) != null) {
            if (line.startsWith("TracerPid:")) {
                return Integer.parseInt(line.split("\\s+")[1]) != 0;
            }
        }
    } catch (Exception e) { }
    return false;
}

// Scan for frida-server on default port 27042
public boolean fridaListening() {
    try (Socket s = new Socket("127.0.0.1", 27042)) { return true; }
    catch (IOException e) { return false; }
}
```

Patch each method to return `false`.

`ptrace(TRACEME)` self-check — usually in native code; requires patching the `.so` (see `android-jni-ndk` and Ghidra).

## Bricking prevention

Some apps, on tamper detection, wipe local data or refuse to launch permanently:

```java
if (tampered) {
    getSharedPreferences("integrity", 0).edit().putBoolean("locked", true).apply();
    System.exit(1);
}
```

If your patched APK triggers this before you've patched all checks:

```bash
adb shell pm clear com.target.app          # wipes data, sharedprefs
adb uninstall com.target.app && adb install patched.apk   # clean slate
```

## Order of neutralization

Recommended sequence when reversing a heavily-protected app:

1. Root detection (RootBeer, custom) → `false`.
2. Emulator detection → `false`.
3. Frida/Magisk/Xposed detection → `false`.
4. Debugger detection → `false`.
5. Signature / DEX / APK integrity → skip check.
6. Play Integrity / SafetyNet → skip client-side, expect server-side to still enforce.
7. SSL pinning → OkHttp `CertificatePinner`, custom TrustManagers, `network_security_config.xml`.
8. Manifest: `android:debuggable="true"`, trust user CA in network config.

Rebuild, sign, install, test after each step — not in one huge batch. If it crashes, you know exactly which patch introduced the issue.

## Verifying patch success

```bash
adb logcat -c
adb install -r patched.apk
adb shell am start -n com.target/.MainActivity
adb logcat | grep -E 'AndroidRuntime|System.err|E/'
```

Common failures:

| Log excerpt | Cause |
|-------------|-------|
| `java.lang.VerifyError` | Smali edit broke bytecode structure (register count, type) |
| `java.lang.SecurityException: … tamper …` | Missed a check |
| `Failure calling remote service` | Server-side integrity gate; not a local issue |
| `System.exit(1)` in logcat before crash | Integrity check fires; find and patch the caller |
| App silently exits after launch | Splash screen check; usually a `finish()` in a lifecycle callback triggered by a check |
| Zygote refuses to load | DEX corruption; recheck apktool output |

## Anti-patterns

- Patching all checks at once → can't attribute a crash to a specific patch.
- Not enabling `adb logcat` before install → you miss the exact exception.
- Using `HiddenApiBypass` when you didn't need to → adds a runtime dependency and log spam. Only use if you actually reflectively access hidden APIs.
- Assuming `Play Integrity` is a client-side gate → server verifies. Patching the client is often useless.
- Skipping the manifest `android:networkSecurityConfig` edit → Android 7+ rejects user CA even after all smali pinning bypasses.
- Not disabling the tampering **response** (`System.exit`, `killApp`, `finish`) → check still fires but does nothing useful; you get intermittent bugs.
