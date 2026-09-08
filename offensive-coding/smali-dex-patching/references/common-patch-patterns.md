# Common Patch Patterns

Load when you know the target check and need the right smali edit.

## Root detection

### RootBeer

Very common Android root-detection library (`com.scottyab.rootbeer.RootBeer`). Every check returns `boolean`:

```smali
# RootBeer.smali — patch every isRooted*() method
.method public isRooted()Z
    .registers 2
    const/4 v0, 0x0
    return v0
.end method

.method public isRootedWithBusyBoxCheck()Z
    .registers 2
    const/4 v0, 0x0
    return v0
.end method

.method public detectRootManagementApps()Z
    .registers 2
    const/4 v0, 0x0
    return v0
.end method
```

Grep for every `->isRooted` and `->detect` method in `RootBeer.smali` and neutralize.

### Custom root check

```smali
.method private static hasSu()Z
    .registers 3
    # complex logic checks /system/xbin/su, /system/bin/su, exec("su -v")
    ...
    return v0
.end method
```

Replace body:

```smali
.method private static hasSu()Z
    .registers 1
    const/4 v0, 0x0
    return v0
.end method
```

### Multiple call sites

If several classes call the check, patch the check method itself — one edit disables all callers. If the check is inlined into each caller, you must patch every call site individually.

## Emulator / VM detection

Common markers checked:

- Build.FINGERPRINT contains `generic`, `unknown`, `emulator`, `sdk`
- Build.MODEL contains `google_sdk`, `Emulator`, `Android SDK built for x86`
- Build.MANUFACTURER == `Genymotion`
- `/system/bin/qemu-props`, `/sys/qemu_trace`

```smali
.method public static isEmulator()Z
    .registers 2
    const/4 v0, 0x0
    return v0
.end method
```

## SSL pinning

### OkHttp CertificatePinner

Class `okhttp3.CertificatePinner` has `check(String hostname, List<Certificate> peerCertificates)` that throws on failure:

```smali
# okhttp3/CertificatePinner.smali → find:
.method public final check(Ljava/lang/String;Ljava/util/List;)V
    .registers ...
    # complex verification, throws SSLPeerUnverifiedException on failure
.end method

# Replace body with:
.method public final check(Ljava/lang/String;Ljava/util/List;)V
    .registers 3
    return-void
.end method
```

There are also `check$okhttp` (Kotlin generated), `check(String, Certificate[])` overloads — patch all.

### Custom X509TrustManager

```smali
# find your.package.YourTrustManager.smali → replace:
.method public checkServerTrusted([Ljava/security/cert/X509Certificate;Ljava/lang/String;)V
    .registers 4
    return-void
.end method

.method public checkClientTrusted([Ljava/security/cert/X509Certificate;Ljava/lang/String;)V
    .registers 4
    return-void
.end method
```

### TrustKit

`com.datatheorem.android.trustkit.pinning.OkHttp3Helper.getPinningTrustManager()` — replace with a trust-all manager:

```smali
.method public static getPinningTrustManager()Ljavax/net/ssl/X509TrustManager;
    .registers 1
    sget-object v0, Lcom/target/PatchedTrustManager;->INSTANCE:Lcom/target/PatchedTrustManager;
    return-object v0
.end method
```

Where `PatchedTrustManager` is a class you inject with an all-trusting implementation.

### Injecting a helper class

If you need a new class (rare — usually you can edit in place):

1. Write the Kotlin/Java class in a scratch project, compile to `.class` then `.dex`.
2. Extract `.smali` via `baksmali` and copy to `unpacked/smali_classesN/<pkg>/<Cls>.smali`.
3. Add references from the patched code.

Simpler: `apktool` handles new `.smali` files added to any `smali_classesN/` folder.

## Debuggable / debugger check

`android.os.Debug.isDebuggerConnected()`:

```smali
# Wherever the app calls it:
invoke-static { }, Landroid/os/Debug;->isDebuggerConnected()Z
move-result v0
# Change what follows: if-nez v0, :exit  →  goto :next_check (skip the check)
```

Simpler: rebuild with `android:debuggable="true"` in the manifest — some checks flip on this.

`ApplicationInfo.FLAG_DEBUGGABLE` (0x2):

```smali
iget v0, p1, Landroid/content/pm/ApplicationInfo;->flags:I
const v1, 0x2
and-int/2addr v0, v1
if-nez v0, :cond_debug   ← force taken/not-taken depending on need
```

## Frida / Magisk / Xposed detection

Common markers:

- `/system/framework/XposedBridge.jar`
- `/data/local/tmp/frida-server`
- Scan of `/proc/net/tcp` for port 27042 (Frida default)
- `Xposed.getMD5Sum()` reflection
- Magisk manager package: `com.topjohnwu.magisk`

Each check has a method returning a boolean; patch to return `false`. Standard `const/4 v0, 0x0; return v0`.

If the app scans `/proc/self/status` for `TracerPid` (Frida/gdb detector):

```smali
# find code that reads /proc/self/status and parses TracerPid
# neutralize the whole check by returning early
.method private hasDebugger()Z
    .registers 2
    const/4 v0, 0x0
    return v0
.end method
```

## License / premium unlock

Client-side license checks:

```smali
.method public isPremium()Z
    .registers 2
    const/4 v0, 0x1                  ← force true
    return v0
.end method
```

Do not attack server-verified subscriptions (they'll fail at API level). Client-side gated features flip trivially.

## Play Integrity API (partial)

`com.google.android.play.core.integrity.IntegrityManager.requestIntegrityToken(...)` returns a `Task<IntegrityTokenResponse>`. The token is server-verified — you cannot forge it from a patched client.

What you can do client-side:

- Skip the client-side call entirely (removes the client's contribution but the server sees no token → often rejects).
- Hook the token consumer to accept a stub response → useful only if the server-side verification is client-controlled or missing.

For real Play Integrity bypass, look at the server-side verification logic — that's out of scope for pure smali patching.

## Tamper detection (self-integrity checks)

Apps sometimes verify their own signature via `PackageManager.getPackageInfo(pkg, PackageManager.GET_SIGNING_CERTIFICATES)`:

```smali
.method public isTampered()Z
    .registers 4
    invoke-virtual { p0 }, Lcom/target/App;->getPackageManager()Landroid/content/pm/PackageManager;
    move-result-object v0
    # ... hash comparison against known good ...
    return v1
.end method
```

Patch to return `false`. Some apps do a CRC of `classes.dex` — after your edit, that CRC changes. You have to disable the check.

## Analytics / anti-analysis phone-home

Not strictly a bypass, but useful during pentests: neutralize analytics that would report the tampering:

```smali
# In FirebaseAnalytics wrapper class:
.method public logEvent(Ljava/lang/String;Landroid/os/Bundle;)V
    .registers 3
    return-void
.end method
```

## Injecting a log line

For "why did the check trigger" debugging:

```smali
.method public checkThing()Z
    .registers 4
    invoke-static { p0 }, Lcom/target/RootBeer;->isRooted(Landroid/content/Context;)Z
    move-result v0

    # inject log
    const-string v1, "DEBUG"
    const-string v2, "isRooted returned"
    if-eqz v0, :zero
    const-string v2, "true"
    goto :log
    :zero
    const-string v2, "false"
    :log
    invoke-static { v1, v2 }, Landroid/util/Log;->d(Ljava/lang/String;Ljava/lang/String;)I
    # end inject

    return v0
.end method
```

`adb logcat -s DEBUG:*` after install to see the check firing.

## Injecting a stack trace on any method entry

For finding where a check is called from:

```smali
.method public isBlocked()Z
    .registers 3
    new-instance v0, Ljava/lang/Exception;
    const-string v1, "TRACE"
    invoke-direct { v0, v1 }, Ljava/lang/Exception;-><init>(Ljava/lang/String;)V
    invoke-virtual { v0 }, Ljava/lang/Exception;->printStackTrace()V
    const/4 v0, 0x0
    return v0
.end method
```

`adb logcat System.err` for the stack trace.

## Constants-mapping table

Common return values:

| Java literal | Smali |
|--------------|-------|
| `true` | `const/4 v0, 0x1` |
| `false` | `const/4 v0, 0x0` |
| `null` | `const/4 v0, 0x0` (identical to false for reference types) |
| `-1` | `const/4 v0, -0x1` |
| `100` | `const/16 v0, 0x64` |
| `0x7fffffff` (Int.MAX) | `const v0, 0x7fffffff` |
| `1L` (long) | `const-wide/16 v0, 0x1` |
| `"hi"` | `const-string v0, "hi"` |

## Verification after patch

Always run the patched app and check logcat:

```bash
adb logcat -c && adb install patched.apk && adb shell am start -n com.target/.MainActivity && adb logcat *:E
```

Expected:

- No `java.lang.VerifyError` (verifier caught an inconsistency).
- No `SecurityException` from a tamper check firing.
- No process death from `System.exit()` in an integrity check.

If verifier error: recount `.registers` / `.locals` and fix any type-mismatched register use.
