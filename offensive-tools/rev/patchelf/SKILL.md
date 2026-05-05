---
name: patchelf
description: "patchelf: ELF patching utility for changing interpreters, RPATH/RUNPATH, DT_NEEDED entries, and SONAME fields. Use when redirecting a binary to a custom loader or libc, fixing packaged ELF dependencies, or preparing local exploit environments that must run against a specific runtime."
license: GPL-3.0
compatibility: "Linux primary; ELF binaries and shared libraries only"
metadata:
  author: AeonDave
  version: "1.0"
---

# patchelf

Patch existing ELF metadata without recompiling the target.

## When to use patchelf

Use patchelf when you need to:

- force an ELF to use a specific dynamic loader
- point a binary at a custom libc or bundled libraries
- trim or rewrite RPATH/RUNPATH entries
- add, remove, or replace `DT_NEEDED` dependencies
- change a shared library `SONAME`

This is especially useful in exploit labs, portable bundles, and offline ELF repair workflows.

## Quick Start

```bash
# Set custom loader
patchelf --set-interpreter /lib64/ld-linux-x86-64.so.2 ./prog

# Set custom RPATH
patchelf --set-rpath '$ORIGIN/libs' ./prog

# Replace one needed library with another
patchelf --replace-needed libold.so libnew.so ./prog
```

## High-Value Operations

### Change interpreter

```bash
patchelf --set-interpreter /path/to/ld-linux.so.2 ./prog
```

Use when a binary must run with a matching loader for a bundled libc.

### Set or shrink RPATH

```bash
patchelf --set-rpath /opt/app/lib:/other/lib ./prog
patchelf --shrink-rpath ./prog
patchelf --shrink-rpath --allowed-rpath-prefixes /usr/lib:/opt/app/lib ./prog
```

### Change dependencies

```bash
patchelf --remove-needed libfoo.so.1 ./prog
patchelf --add-needed libbar.so.1 ./prog
patchelf --replace-needed libold.so.1 libnew.so.1 ./prog
```

### Change shared library SONAME

```bash
patchelf --set-soname libcustom.so.1 ./libtarget.so
```

## Canonical Exploit-Lab Workflow

```bash
cp ./vuln ./vuln.patched
patchelf --set-interpreter ./ld-linux-x86-64.so.2 ./vuln.patched
patchelf --set-rpath '$ORIGIN' ./vuln.patched
```

Then verify with `ldd`, `readelf`, or by executing under a controlled directory.

## Practical Notes

- Always patch a copy first.
- Verify before and after with `readelf -l`, `readelf -d`, and `ldd`.
- Prefer `$ORIGIN`-based RPATHs for portable bundles.
- Use patchelf for loader/runtime metadata, not for arbitrary code patching.

## Caveats

- ELF only.
- Bad interpreter or dependency changes can make the binary unloadable.
- Patching dependency layout does not fix ABI mismatches by itself.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use upstream README for build/install variants and the complete option set.
