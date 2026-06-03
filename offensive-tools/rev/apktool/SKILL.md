---
name: apktool
description: "Auth/lab ref: decode and rebuild Android APK resources and smali for patching, manifest edits, resource inspection, and repackaging."
license: Apache-2.0
compatibility: "Linux, macOS, Windows; Java 11+."
metadata:
  author: AeonDave
  version: "1.0"
---

# Apktool

Resource and smali decode/rebuild workflow for Android APKs.

## When to use Apktool

Use Apktool when you need to:

- decode `AndroidManifest.xml`, resources, and smali from an APK
- patch permissions, intents, strings, layouts, or smali logic
- rebuild a modified APK for testing
- inspect resources without full Java decompilation

Use `jadx` when you want readable Java/Kotlin. Use Apktool when you intend to **edit** the app.

## Quick Start

```bash
# Decode APK into a project-like directory
apktool d app.apk

# Decode for analysis-only resource inspection
apktool d -m app.apk

# Rebuild after edits
apktool b app
```

Typical output after rebuild is under `app/dist/`.

## Core Workflow

### 1. Decode

```bash
apktool d target.apk
```

This produces a folder containing at least:

- `AndroidManifest.xml`
- `apktool.yml`
- `res/`
- `smali/` or `smali_classes*/`
- `assets/`

### 2. Patch

Common edit points:

- `AndroidManifest.xml` — exported components, permissions, debuggable flags
- `res/values/strings.xml` — hardcoded UI strings and toggles
- `res/xml/` — config and network security settings
- `smali/` — bypass checks, short-circuit logic, redirect flow

### 3. Rebuild

```bash
apktool b target
```

### 4. Sign and reinstall

Apktool rebuilds the APK but does **not** make it production-signed. Sign it separately before install.

```bash
apksigner sign --ks debug.keystore target/dist/target.apk
adb install -r target/dist/target.apk
```

## Common Use Cases

### Patch app logic in smali

Use when the decompiled Java in `jadx` shows the method to change, but you need a reliable rebuild path.

```bash
apktool d app.apk
# edit smali/com/example/MainActivity.smali
apktool b app
```

### Change manifest or resources

```bash
apktool d app.apk
# edit AndroidManifest.xml or res/values/*.xml
apktool b app
```

### Pair with `adb`

```bash
adb shell pm path com.example.app
adb pull /data/app/.../base.apk app.apk
apktool d app.apk
```

## Practical Notes

- Apktool is strongest for **resource decode + smali round-trip**, not for pretty source code.
- If rebuild succeeds but install fails, check signing, package conflicts, and `android:sharedUserId` or min SDK constraints.
- If static analysis is the goal, open the same APK in `jadx` alongside Apktool output.
- `-m` is useful when you mainly want manifests/resources and do not care about a rebuild-ready tree.

## Caveats

- Complex OEM apps may require extra framework handling before clean decode/rebuild.
- Rebuilt apps may still fail at runtime because of integrity checks, signature checks, or native anti-tamper logic.
- Some Java-level edits are easier to understand in `jadx`, but safer to apply in smali.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use upstream docs at `apktool.org` for version-specific CLI details and build caveats.
