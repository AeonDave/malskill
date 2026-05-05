---
name: dex2jar
description: "dex2jar: Android DEX-to-JAR conversion toolkit for feeding Java bytecode into desktop decompilers and analysis tools. Use when you want a `.jar` or `.class`-oriented workflow from an APK or DEX file, especially when comparing output across `jadx`, CFR, JD-GUI, or custom JVM tooling."
compatibility: "Linux, macOS, Windows; Java runtime required; shell and batch launchers included"
metadata:
  author: AeonDave
  version: "1.0"
---

# dex2jar

Bridges Android DEX artifacts into traditional Java tooling.

## When to use dex2jar

Use dex2jar when you need to:

- convert `.dex` or `.apk` input into `.jar` output for JVM tools
- compare decompiler results across different Java-oriented pipelines
- inspect bytecode with tooling that expects `.class` files instead of Dalvik directly

## Quick Start

```bash
# Convert a DEX file
d2j-dex2jar.sh classes.dex

# Convert an APK directly
d2j-dex2jar.sh app.apk

# Windows launcher equivalent
d2j-dex2jar.bat app.apk
```

## Practical Workflow

1. Use `apktool`, `jadx`, or `androguard` first for broad APK triage.
2. Run dex2jar when you specifically want a JVM-style jar/class workflow.
3. Open the resulting JAR in CFR, JD-GUI, Bytecode Viewer, or custom Java analysis scripts.

## Practical Notes

- dex2jar is most useful as a compatibility bridge, not as the only Android reversing tool.
- Keep `jadx` nearby; its direct APK/DEX support is often better for large manual review.
- When multiple `classes*.dex` files exist, convert each or start from the full APK.

## Caveats

- Complex apps, obfuscation, or unusual bytecode can convert imperfectly.
- Output is only as useful as the downstream Java decompiler you feed it into.
- Prefer current launcher names from the packaged toolset instead of old blog-post aliases.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the upstream dex2jar project docs for exact launcher names and auxiliary conversion helpers.
