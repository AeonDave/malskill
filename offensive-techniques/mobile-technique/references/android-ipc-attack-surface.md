# Android IPC Attack Surface

Load when auditing an Android app's exported components, intent extras, nested intents, PendingIntents, providers, Binder services or WebView bridges. For each class: vulnerable shape, static signature, test command, and the version rule that changes the result.

## Record the test context

- APK hash/version, runtime API/build/security patch, target SDK, user/work profile, WebView version when relevant.
- Caller package, UID, signing identity and granted permissions; separate an ordinary external app from shell, root, instrumentation and in-process hooks.
- Entry point, required app/session state, controlled input, authorization decision, observed outcome. Platform rejection and application rejection are different results.

`adb shell` runs as the shell UID (2000): more privileged than a third-party app, less than a system app. Use it to probe, then reproduce with a separate unprivileged lab app. `am` cannot build a nested `Intent` extra (`--esn` supplies a null string), so nested intents and PendingIntents need the lab app. Use marker records and files, a controlled receiver, an accepted baseline and a denied control.

## Enumerate effective exposure

Read the merged manifest of the shipped APK: library manifests, flavors and build types merge into it.

```bash
apkanalyzer manifest print app.apk > merged-manifest.xml
rg -n 'android:(exported|permission|readPermission|writePermission|grantUriPermissions|launchMode|taskAffinity|debuggable)|<path-permission|<grant-uri-permission' merged-manifest.xml
rg -n 'registerReceiver|RECEIVER_EXPORTED|RECEIVER_NOT_EXPORTED|sendBroadcast|setResult|getParcelableExtra|Intent\.parseUri|IntentSanitizer|PendingIntent\.|startIntentSender|onNewIntent|onBind|onTransact|addJavascriptInterface|postWebMessage' sources/
```

On the device, as shell:

```bash
adb shell dumpsys package com.victim                         # components, permissions with protectionLevel, flags, shared UID
adb shell cmd package resolve-activity --brief -a android.intent.action.VIEW -c android.intent.category.BROWSABLE -d "https://lab.example/"
adb shell cmd package query-receivers --brief -a com.victim.ACTION
```

With drozer ([ReversecLabs/drozer](https://github.com/ReversecLabs/drozer), 3.1.0 beta rewrite: agent on the device, console on the host; `adb forward tcp:31415 tcp:31415` then `drozer console connect`, no password by default), the caller is the drozer app, not shell:

```
run app.package.attacksurface com.victim
run app.activity.info -a com.victim -u -i
run app.service.info -a com.victim
run app.broadcast.info -a com.victim -u -i
run app.provider.info -a com.victim -u
run app.provider.finduri com.victim
run app.provider.read content://com.victim.provider/files/lab-marker /tmp/marker
run scanner.provider.injection -a com.victim
run scanner.provider.sqltables -a com.victim
run scanner.provider.traversal -a com.victim
run app.broadcast.sniff --action com.victim.ACTION
run scanner.activity.browsable -a com.victim
```

- For each component resolve enabled/exported state, application-level and component-level permissions, permission protection level and runtime checks. A grep match is a candidate, not a finding.
- A non-exported service admits its own application or the same UID. Exported partner interfaces still need the intended permission or per-operation authorization.
- Providers have their own exported default and URI-grant behavior; do not apply activity/service/receiver intent-filter defaults to them.
- For dynamic receivers read the registration overload, sender permission, protected action and flags together. `RECEIVER_EXPORTED` alone does not establish an unauthorized action.

Sources: [service manifest](https://developer.android.com/guide/topics/manifest/service-element), [provider manifest](https://developer.android.com/guide/topics/manifest/provider-element), [broadcast receiver guidance](https://developer.android.com/develop/background-work/background-tasks/broadcasts).

## Version conditions that change the result

| Runtime and target condition | Assessment consequence |
|---|---|
| Android 12+, target SDK 31+ | Activities, services and receivers with intent filters require explicit `android:exported`; PendingIntent creation requires a mutability flag. Separate requirements. |
| Android 14+, target SDK 34+ | Context-registered receivers require an export flag, except registrations for system broadcasts. |
| Android 14+, target SDK 34+ | Implicit intents are delivered only to exported components; a mutable PendingIntent needs a component or a package (`FLAG_ALLOW_UNSAFE_IMPLICIT_INTENT` opts out). |
| Android 14+, target SDK 34+ | A PendingIntent sender lends its background-activity-launch privilege only with `ActivityOptions.setPendingIntentBackgroundActivityStartMode(MODE_BACKGROUND_ACTIVITY_START_ALLOWED)`. |
| Android 15+, target SDK 35+ | PendingIntent creators block background activity launch by default. A blocked launch may be platform policy, not an app check. |
| Android 16, all apps | Default hardening affects nested-intent redirection. Observe the actual launch outcome and whether code opts out through `removeLaunchSecurityProtection()`. |
| Android 16, target SDK 36+ | `intentMatchingFlags="enforceIntentFilter"` opt-in: a cross-app explicit intent must match the target component's filter; an intent without action matches none. |
| Android 17, target SDK 37+ | Contacts Provider 2 applies strict columns/grammar checks to `ContactsContract.Data` queries made without `READ_CONTACTS`. A specific provider rule, not protection for every app provider. |

Check both all-app and target-gated changes. The Android 17 all-app documentation describes implicit URI-grant diagnostics and a restriction planned for Android 18; do not report that future restriction as enforced on Android 17.

Sources: [Android 12 target changes](https://developer.android.com/about/versions/12/behavior-changes-12), [Android 14 target changes](https://developer.android.com/about/versions/14/behavior-changes-14), [Android 15 target changes](https://developer.android.com/about/versions/15/behavior-changes-15), [PendingIntent implementation](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/core/java/android/app/PendingIntent.java), [Android 16 all-app changes](https://developer.android.com/about/versions/16/behavior-changes-all), [Android 16 intent matching](https://developer.android.com/about/versions/16/behavior-changes-16#safer-intents), [Android 17 target changes](https://developer.android.com/about/versions/17/behavior-changes-17), [Android 17 all-app changes](https://developer.android.com/about/versions/17/behavior-changes-all).

## Privileged extras on an exported component

An exported activity or receiver takes extras that select an operation meant for a trusted caller:

```kotlin
// meant for the app's own UI or an AIDL client; reachable by any zero-permission app
if (intent.getBooleanExtra("silent_import", false)) importFrom(intent.getStringExtra("path"), prompt = false)
```

- **Signature**: exported component, `getExtras()` values driving behavior switches, no caller check. An allow-list on the AIDL path does not cover the activity.
- **Test**: `adb shell am start -n com.victim/.ImportActivity --ez silent_import true --es path /sdcard/Download/lab-marker`, then confirm the marker state changed with no prompt. Repeat from the lab app.
- **Caller identity**: `getCallingActivity()`/`getCallingPackage()` are null unless the caller used `startActivityForResult`, so a null value does not mean an internal launch. `getReferrer()` returns what the launcher supplied.
- **Same rule, other direction**: `isAppEnabled()`-style predicates that return true for every caller turn an exported AIDL service into a public API. Enumerate its methods and call a harmless getter from the lab app.

Reference cases: [GHSL-2026-108](https://securitylab.github.com/advisories/GHSL-2026-108_osmand) (exported activity silently imports settings), [GHSL-2026-109](https://securitylab.github.com/advisories/GHSL-2026-109_osmand) (exported service approves any caller). Identity facts: [Activity](https://developer.android.com/reference/android/app/Activity).

## Nested intents and URI delegation

Vulnerable shapes:

```kotlin
startActivity(intent.getParcelableExtra("next", Intent::class.java))      // 1. forwarded nested Intent
startActivity(Intent.parseUri(intent.getStringExtra("url")!!, Intent.URI_INTENT_SCHEME))   // 2. intent: URI from a string extra
startIntentSender(intent.getParcelableExtra("pi", PendingIntent::class.java).intentSender, null, 0, 0, 0)
setResult(RESULT_OK, Intent().setData(secretUri).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION))
```

1. An `Intent` or `PendingIntent` taken from extras reaches `startActivity`, `startService`, `bindService`, `sendBroadcast`, `startActivities` or `startIntentSender`. The nested intent runs with the vulnerable app's identity: it reaches non-exported components, and its grant flags grant access to the app's `grantUriPermissions` providers.
2. `Intent.parseUri` over an attacker string. Shell can drive it: `adb shell am start -n com.victim/.EntryActivity --es url "intent:#Intent;action=com.victim.INTERNAL;package=com.victim;end"`. `toUri(URI_INTENT_SCHEME)` output is the syntax reference. `package=` and `component=` are honored; URI-grant flags in `launchFlags=` are stripped unless the app parses with `URI_ALLOW_UNSAFE`.
3. A result Intent delegates a URI to the requesting app without launching a component. Check `setResult` on exported activities and whether sensitive URIs are returned only after authorization.

**Signature**: `getParcelableExtra` (and `getParcelableArrayListExtra`) with an `Intent`/`PendingIntent` type or an `Intent.CREATOR` cast, `Intent.parseUri`, `getStringExtra` flowing into either, `startIntentSender`, `setResult(`. Then trace each site to the launch call.

**Lab PoC** (extra names and components from static review; `MarkerGrab` is a lab activity and the record is a test row in the victim's provider):

```kotlin
val nested = Intent().apply {
    setClassName("com.lab.caller", "com.lab.caller.MarkerGrab")
    data = Uri.parse("content://com.victim.provider/users/900001")
    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
}
startActivity(Intent().apply {
    setClassName("com.victim", "com.victim.EntryActivity")
    putExtra("next", nested)
})
```

- Inspect destination allow-lists and the handling of read/write/persistable/prefix grants. A custom validator can be correct; absence of `IntentSanitizer` alone is not a vulnerability.
- `IntentSanitizer`: verify its policy and use of the returned copy. `sanitizeByFiltering` removes disallowed fields, `sanitizeByThrowing` rejects them. Neither compensates for a permissive policy or for forwarding the original object.
- `grantUriPermissions` permits delegation, also for a non-exported provider; it does not itself create an unauthorized grant. Establish the exact URI, recipient, operations and data subset, and when access expires.
- On Android 16, record whether the launch is blocked by the default hardening and whether the code calls `removeLaunchSecurityProtection()`.

Sources: [intent redirection](https://developer.android.com/privacy-and-security/risks/intent-redirection), [IntentSanitizer API](https://developer.android.com/reference/kotlin/androidx/core/content/IntentSanitizer), [provider URI grants](https://developer.android.com/guide/topics/manifest/provider-element#grnturi).

## PendingIntent capabilities

**How a token leaks**: notification actions and content intents read by a `NotificationListenerService`, a `PendingIntent`/`IntentSender` passed to another app as a callback, `RemoteInput` replies, widgets and slices. Posting a notification does not mean every app possesses its token; identify the holder.

**What the holder controls** (`PendingIntentRecord.sendInner`, `Intent.fillIn`): only when the token is mutable, the system merges the sender's intent into the base intent:

- Null `action`, `data`+`type`, categories and `ClipData` of the base intent are replaced.
- Extras are merged, base keys win; flags are OR-ed.
- Component and selector stay those of the base intent; the operation type stays activity, broadcast or service. A null base `package` can be set by the sender.
- The token is dispatched in the creator's package with its UID.

For apps targeting below 34, a mutable token built on an implicit or empty intent is the full primitive: the sender supplies the package and reaches the creator's non-exported components. An explicit component does not make a mutable token safe either: null `data` lets the holder attach any provider URI of the creator plus `FLAG_GRANT_READ_URI_PERMISSION`, and a null `action` lets the holder select another behavior of that component.

**Audit**:

1. Creation site: mutability flag, base intent fields that are null, request code, `FLAG_ONE_SHOT`, `FLAG_UPDATE_CURRENT`.
2. Recipient component: what it does with `intent.data`, action and extras.
3. Holder set and how the token reaches it.
4. Background activity launch rules for the sender and creator.

**Lab PoC** from a lab notification listener that holds the token (`pi`):

```kotlin
val fill = Intent().setData(Uri.parse("content://com.victim.provider/users/900001"))
    .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
Log.i("lab", "creator=${pi.creatorPackage} uid=${pi.creatorUid}")
pi.send(applicationContext, 0, fill)
```

`FLAG_IMMUTABLE` constrains the invoker; the creator can still update an existing token with `FLAG_UPDATE_CURRENT`. `getCreatorPackage()`/`getCreatorUid()` identify the original creator, not the app that handed the token over.

Sources: [PendingIntent API](https://developer.android.com/reference/android/app/PendingIntent), [PendingIntentRecord](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/services/core/java/com/android/server/am/PendingIntentRecord.java), [background activity starts](https://developer.android.com/guide/components/activities/background-starts).

## ContentProvider checks

Treat query, write, file-open and `call()` paths separately. Resolve inherited permissions, path-specific permissions, URI grants and method-level authorization before testing data handling.

**Exposure**: `exported="true"` without `readPermission`/`writePermission`, `android:permission` weaker than the data needs, missing `<path-permission>` scoping, `grantUriPermissions="true"` combined with a forwarding gadget. Check every authority, including those of bundled SDKs.

**Queries**. Vulnerable shapes:

```kotlin
db.rawQuery("SELECT * FROM ${uri.lastPathSegment} WHERE $selection", null)   // table, selection from the caller
qb.setTables(uri.lastPathSegment)                                           // or: no setProjectionMap
```

```bash
adb shell content query --uri content://com.victim.provider/users
adb shell content query --uri content://com.victim.provider/users --projection "* FROM sqlite_master--"
adb shell content query --uri content://com.victim.provider/users --where "1=1 OR 1=1"
adb shell content query --uri content://com.victim.provider/users --sort "CASE WHEN (SELECT count(*) FROM users)>0 THEN name ELSE id END"
```

`--projection` splits on `:`, so a payload must be one colon-free string. `content` runs as shell: it proves exposure of exported providers, not access from an ordinary app. Follow caller-controlled projection, selection, arguments, sort order and table choice into the database operation. Bind values as parameters and constrain identifiers separately. Missing `setProjectionMap` is a review cue, not proof of injection. In `SQLiteQueryBuilder`, `setStrict` is API 14; `setStrictColumns` and `setStrictGrammar` are API 30; all are initially disabled. A SQL exception is not disclosure: compare a known marker row set against the returned schema and rows.

**Files**. Vulnerable shape:

```kotlin
override fun openFile(uri: Uri, mode: String): ParcelFileDescriptor =
    ParcelFileDescriptor.open(File(filesDir, uri.lastPathSegment!!), ParcelFileDescriptor.parseMode(mode))
```

`Uri` splits the path on literal `/` and decodes each segment afterwards, so `..%2F` stays inside one segment and `lastPathSegment` returns `../..`:

```bash
adb shell content read --uri 'content://com.victim.provider/files/..%2F..%2Fdatabases%2Flab-marker.db'
```

Trace URI decoding and normalization to the opened path. Containment must use canonical paths and path boundaries, not a bare string prefix; account for symlinks where the threat model includes them. The same flaw in a write path gives arbitrary file write: an extension check (`name.endsWith(".gpx")`) passes `../x.gpx`. Reference case: [GHSL-2026-106](https://securitylab.github.com/advisories/GHSL-2026-106_OsmAnd).

**`call()`**: custom methods often skip the checks applied to `query()`. List methods and arguments from source, then `adb shell content call --uri <uri> --method <name> --arg <arg>`.

**FileProvider chain**: `<provider android:name="androidx.core.content.FileProvider" android:exported="false" android:grantUriPermissions="true">` with `<meta-data android:name="android.support.FILE_PROVIDER_PATHS">` pointing to a paths XML. Each element maps a storage root: `files-path` (`getFilesDir()`), `cache-path`, `external-path`, `external-files-path`, `external-cache-path`, `external-media-path`, `root-path` (filesystem root). `getUriForFile` canonicalizes the target and throws when no configured root contains it, so the exposure is the breadth of the roots times the caller's influence on the file name: `root-path`, or an empty `path` on a wide root, turns a share feature into a read of any file the app can read. A recipient needs the grant flag on the intent.

Sources: [SQLiteQueryBuilder](https://developer.android.com/reference/android/database/sqlite/SQLiteQueryBuilder), [path traversal guidance](https://developer.android.com/privacy-and-security/risks/path-traversal), [FileProvider](https://developer.android.com/reference/androidx/core/content/FileProvider).

## Binder services and caller identity

Use manifest permissions to protect binding where appropriate, then authorize each sensitive operation inside the incoming Binder/AIDL transaction.

```kotlin
// trust in caller-supplied identity
override fun onBind(i: Intent): IBinder? = if (isTrusted(i.getStringExtra("caller"))) binder else null
// per-transaction identity
val uid = Binder.getCallingUid()
for (pkg in packageManager.getPackagesForUid(uid)) { /* match signing certificate */ }
```

- `Binder.getCallingUid()` identifies the sender of the current incoming transaction; outside one it returns the process's own UID.
- `onBind()` is lifecycle setup, not a per-client authorization callback: the returned binder can be cached and shared with later clients.
- Check identity before `clearCallingIdentity()` or before handing work to another thread; carry the validated context into asynchronous work.
- Package names and UIDs supplied in extras are not identity. Bind package/signing checks to the system-reported UID and handle multiple packages per UID and signing rotation.
- Exercise the same benign operation from an allowed client and a distinct denied client. Record the UID seen inside the transaction and the decision, not only that binding succeeded.

Sources: [Binder identity](https://developer.android.com/reference/android/os/Binder#getCallingUid()), [bound service lifecycle](https://developer.android.com/develop/background-work/services/bound-services).

## Activity state and WebView boundaries

**`onNewIntent`**: compare cold and warm launches, signed-out and signed-in state, repeated delivery, for `singleTop`, `singleTask` and `singleInstance` activities. The new intent must receive the same authorization and validation as `onCreate`; check whether processing reads the new parameter or stale `getIntent()` state.

**WebView bridge**:

1. Inventory `addJavascriptInterface` objects and their `@JavascriptInterface` methods by effect: load URL, file access, tokens, starting activities. The object is exposed to every frame, including iframes, and the platform cannot check the calling frame's origin. Methods need the annotation when targeting API 17+; reflection into the object's public fields is closed when targeting API 21+.
2. Establish which origins can run: allow-list, redirects, iframes, `loadDataWithBaseURL` base URL, third-party scripts. A bridge is as exposed as the least trusted origin loaded.
3. `shouldOverrideUrlLoading` and `intent:` scheme URLs: `Intent.parseUri(url)` followed by `startActivity` is the nested-intent shape. Safe handling strips the component and selector and adds `CATEGORY_BROWSABLE`.
4. File and content access: `setAllowFileAccess` defaults to false for target 30+ and true before, and never blocks `file:///android_asset` or `file:///android_res`. `setAllowContentAccess` is enabled by default. `setAllowFileAccessFromFileURLs` and `setAllowUniversalAccessFromFileURLs` matter only for content loaded from a `file://` URL (deprecated in API 30).
5. Custom stacks: `shouldInterceptRequest` proxies requests with the app's cookies or headers, and response headers such as `Access-Control-Allow-Origin: *` decide whether attacker-origin script can read authenticated responses. `onReceivedSslError` calling `proceed()` accepts any certificate.
6. Message-channel bridges (`WebViewCompat.postWebMessage`, `WebMessagePort.postMessage`): a target origin of `*` accepts messages from any sender.
7. Release builds calling `WebView.setWebContentsDebuggingEnabled(true)`: `chrome://inspect` lists the WebViews and runs script with the app's bridge, no root needed. The setting is independent of the manifest `debuggable` flag.

Sources: [WebView native bridges](https://developer.android.com/privacy-and-security/risks/insecure-webview-native-bridges), [WebSettings](https://developer.android.com/reference/android/webkit/WebSettings), [remote WebView debugging](https://developer.chrome.com/docs/devtools/remote-debugging/webviews), [WebView hijack with a custom stack](https://securitylab.github.com/advisories/GHSL-2026-103_apps-android-wikipedia).

## Outgoing IPC

- `sendBroadcast` without a receiver permission is delivered to every dynamic receiver of any app that matches the filter. Trace sensitive extras, then check for `sendBroadcast(intent, receiverPermission)`, `setPackage` or `RECEIVER_NOT_EXPORTED` on the receiving side.
- Ordered broadcasts pass result data between receivers; a later receiver reads what an earlier one returns.
- Exported activities that return sensitive data in `setResult`: the recipient is whoever started them for result.

## Triage

| Signal | Impact to prove | Confirms |
|---|---|---|
| Exported component, extras select a privileged operation | Operation runs from an unprivileged app | Marker state change with no prompt |
| Nested Intent from extras reaches a launch call | Non-exported component reached, or provider delegated | Lab activity reads the marker record |
| Mutable PendingIntent with null `data` or `action` | Holder attaches URI or selects behavior | Fill-in observed in the recipient |
| Exported provider, caller SQL reaches `rawQuery`/query builder | Read or write beyond the intended rows | Marker rows outside the allowed set |
| `openFile` joins `lastPathSegment` without canonicalization | Arbitrary file read in the app sandbox | Marker file outside the allowed directory |
| Caller identity taken from extras or `onBind` | Impersonation of a trusted partner | Denied client obtains the allowed result |
| Auth only in `onCreate`, `singleTop`/`singleTask` activity | Post-auth state with warm-launch input | Warm launch reaches protected state |
| WebView bridge with untrusted origin or debugging on | Bridge methods from attacker script | Marker call from lab content |

## Evidence and next route

Report the reachable entry point, caller identity, affected build/target combination, prerequisites, violated policy, marker result, negative control and observed rejection. Separate static suspicion, instrumentation-only observations and unprivileged reproduction. A crash, exported declaration, granted URI or discovered endpoint is not by itself RCE or data theft.

When mobile IPC exposes a backend path, keep its request/response evidence linked to the mobile entry point. Load [vuln-research](../../../knowledge-offensive/vuln-research/SKILL.md) for backend applicability and [web-exploit-technique](../../web-exploit-technique/SKILL.md) for a supported web finding.
