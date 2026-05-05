---
name: androguard
description: "androguard: Python toolkit for Android APK, DEX, resources, manifest, and certificate analysis. Use when you want scriptable extraction of package metadata, permissions, activities, strings, resources, classes, or basic code analysis from Android apps instead of only manual GUI decompilation."
license: Apache-2.0
compatibility: "Linux, macOS, Windows; Python 3; pip install androguard"
metadata:
  author: AeonDave
  version: "1.0"
---

# Androguard

Scriptable Android static analysis for APK, DEX, XML, and resources.

## When to use Androguard

Use Androguard when you need:

- structured extraction of package metadata and app components
- repeatable Python-driven APK triage across many samples
- manifest, permission, certificate, or resource inspection without a GUI
- basic code and string analysis before deeper reversing

Use `jadx` for human-readable code browsing. Use Androguard when you want **automation and structured output**.

## Installation

```bash
pip install androguard
```

Official project notes that 4.x is the actively developed line and differs significantly from the older 3.3.5 branch.

## Canonical Python Workflow

```python
from androguard.misc import AnalyzeAPK

apk, dex, analysis = AnalyzeAPK("app.apk")

print(apk.get_package())
print(apk.get_app_name())
print(apk.get_permissions())
print(apk.get_activities())
print(apk.get_services())
print(apk.get_receivers())
```

This is the fastest route for repeatable APK metadata extraction.

## High-Value Triage Tasks

### Package, permissions, and components

```python
from androguard.misc import AnalyzeAPK

apk, dex, analysis = AnalyzeAPK("app.apk")

print("Package:", apk.get_package())
print("Permissions:", apk.get_permissions())
print("Activities:", apk.get_activities())
print("Services:", apk.get_services())
print("Receivers:", apk.get_receivers())
```

### File inventory inside the APK

```python
for name in apk.get_files():
    print(name)
```

Useful for spotting:

- embedded native libraries
- config files
- cert bundles
- assets with hardcoded secrets or models

### Certificate and signing clues

Use Androguard when you need to script certificate extraction or compare multiple APKs for shared signing material.

### Strings and code analysis

Use the `analysis` object when you need to inspect methods, classes, or search strings programmatically instead of manually hunting in a GUI.

## Practical Workflow

1. Start with Androguard for package/components/permissions/files
2. Open the same sample in `jadx` for readable code review
3. Move to `apktool` if you need patch-and-rebuild
4. Add `adb` or Frida later for dynamic validation

## Practical Notes

- Upstream docs explicitly note ongoing documentation refresh; prefer current GitHub pages and examples over old blog posts.
- The project supports APK, DEX, ODEX, binary XML, resources, disassembly, and a basic decompiler.
- Use it when you need batchable analysis or a Python-native pipeline.

## Caveats

- Documentation is in transition; APIs may differ from older tutorials.
- Decompiled output is not as convenient as `jadx` for large manual reviews.
- Use it for structured extraction first, not as the only source of truth for complicated control flow.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use upstream examples and current GitHub Pages docs for version-specific API details.
