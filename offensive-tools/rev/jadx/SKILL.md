---
name: jadx
description: "jadx: Android Dex-to-Java decompiler with CLI and GUI support. Use when you need readable Java/Kotlin-like output from APK, DEX, AAB, or JAR files, want fast static triage of Android apps, need deobfuscation support, or want to export a Gradle-like project for analysis."
license: Apache-2.0
compatibility: "Linux, macOS, Windows; Java 11+ 64-bit; release zip or package manager install"
metadata:
  author: AeonDave
  version: "1.0"
---

# JADX

Readable Android decompilation with both CLI and GUI workflows.

## When to use JADX

Use JADX when you want to:

- read application logic quickly in Java-like form
- inspect classes, methods, and strings from APK/DEX/AAB/JAR files
- export a Gradle-like project for deeper review
- deobfuscate names or isolate one class without rebuilding anything

Use `apktool` when you need to **edit and rebuild** the APK.

## Quick Start

```bash
# CLI decompile to folder
jadx -d out app.apk

# Open GUI for interactive analysis
jadx-gui app.apk

# Export as Gradle-like project
jadx -e -d out app.apk
```

## High-Value Flags

| Flag | Purpose |
|------|---------|
| `-d, --output-dir` | Write decompiled output to a directory |
| `-e, --export-gradle` | Export a Gradle-like project |
| `--show-bad-code` | Keep inconsistent code instead of hiding it |
| `--deobf` | Enable deobfuscation |
| `--single-class` | Decompile only one class |
| `--single-class-output` | Write single-class output to file or dir |
| `--output-format json` | Emit JSON instead of Java output |
| `--cfg` / `--raw-cfg` | Export control-flow graphs |
| `-q` / `-v` | Quiet or verbose logging |

## Common Workflows

### Fast APK triage

```bash
jadx -d out app.apk
```

Then inspect:

- `sources/` for business logic
- `resources/AndroidManifest.xml`
- suspicious packages, hardcoded endpoints, auth logic, root checks

### Interactive GUI review

```bash
jadx-gui app.apk
```

Best for:

- cross-reference browsing
- full-text search
- jumping between call sites
- comparing decompiled code and resources quickly

### Handle ugly or obfuscated output

```bash
jadx --deobf --show-bad-code -d out app.apk
```

Use this when normal output hides code paths or when identifiers are too mangled.

### Isolate one class

```bash
jadx --single-class com.example.auth.LoginActivity app.apk
```

Useful when you already know the package/class name from logs, manifest, or previous triage.

## Practical Notes

- JADX explicitly warns that it cannot decompile every app perfectly; always verify sensitive logic in smali if output looks suspicious.
- Use `jadx-gui` first for orientation, then rerun CLI with focused flags for reproducible output.
- If imports or dependencies are broken, analyze the whole project root rather than one isolated file when possible.
- For final patching, move from `jadx` to `apktool` or direct smali edits.

## Caveats

- Decompiled Java is an approximation, not source-of-truth.
- Obfuscated Kotlin apps may still require fallback mode or smali verification.
- If integrity or control-flow logic matters, cross-check with `apktool` smali or another RE tool.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the official README and wiki for plugin management, GUI-specific features, and advanced renaming options.
