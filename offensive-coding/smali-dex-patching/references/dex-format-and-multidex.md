# DEX Format and Multi-DEX

Load when hitting the 64K method limit, adding substantial new code, or reasoning about DEX-level constraints (custom class loading, dex injection).

## DEX file overview

A `.dex` file (Dalvik Executable) is a bytecode container consumed by ART. Structure:

```
header (0x70 bytes)
├── magic ("dex\n<version>\0", e.g. "dex\n038\0")
├── checksum (adler32 of rest)
├── signature (SHA-1 of header + data)
├── file_size, header_size, endian_tag
└── offsets/sizes for each table below

string_ids     — offsets into string data
type_ids       — indices into strings for class names
proto_ids      — method signatures (return + params)
field_ids      — class + name + type
method_ids     — class + name + proto
class_defs     — full class definitions
data           — actual bytecode, string data, annotations
link_data      — statically-linked data (rare)
map_list       — index of all sections
```

Key limit: **method_ids has a 16-bit index → max 65,536 references per DEX** (0x10000). This is the "64K method limit" that historically required multi-DEX.

Beyond 65,536: split code across multiple DEX files (`classes.dex`, `classes2.dex`, ...).

## CDEX (Compact DEX)

- Runtime-optimized format produced by `dex2oat` during install/AOT.
- Lives on-device (`/data/dalvik-cache/.../<apk>.oat` contains embedded CDEX).
- Not in the APK. You don't touch it directly. If you're reversing an OAT/CDEX from a device dump, you need `vdexExtractor` or the AOSP `oatdump` tool.
- Format is a strict subset of DEX with additional metadata for the ART interpreter; specific data-layout changes across Android versions.

## Multi-DEX in APKs

Modern APKs almost always have multi-DEX:

```
classes.dex     — primary; loaded first
classes2.dex    — secondary
classes3.dex    — ...
```

apktool disassembles each into `smali/`, `smali_classes2/`, `smali_classes3/`. Rebuild round-trips them.

### Primary DEX and Startup Profile

- The primary `classes.dex` is loaded and referenced first. Classes needed at app start should live here for faster startup.
- R8 uses the Startup Profile (see `kotlin-performance/references/baseline-and-startup-profiles.md`) to influence this layout.
- **Patching implication**: moving a class between DEX files may change startup behavior. Add new classes to the highest-numbered `smali_classesN/` (or a new `smali_classesN+1/`) unless startup coverage matters.

## Adding new smali classes

Drop a new `.smali` file into any `smali/`, `smali_classes2/`, ..., folder. apktool assembles it into the corresponding DEX.

Example: inject a helper class for pinning bypass:

```smali
# unpacked/smali/com/patch/TrustAll.smali
.class public Lcom/patch/TrustAll;
.super Ljavax/net/ssl/X509ExtendedTrustManager;

.method public constructor <init>()V
    .registers 1
    invoke-direct { p0 }, Ljavax/net/ssl/X509ExtendedTrustManager;-><init>()V
    return-void
.end method

.method public checkClientTrusted([Ljava/security/cert/X509Certificate;Ljava/lang/String;)V
    .registers 3
    return-void
.end method

.method public checkClientTrusted([Ljava/security/cert/X509Certificate;Ljava/lang/String;Ljava/net/Socket;)V
    .registers 4
    return-void
.end method

.method public checkClientTrusted([Ljava/security/cert/X509Certificate;Ljava/lang/String;Ljavax/net/ssl/SSLEngine;)V
    .registers 4
    return-void
.end method

.method public checkServerTrusted([Ljava/security/cert/X509Certificate;Ljava/lang/String;)V
    .registers 3
    return-void
.end method

.method public checkServerTrusted([Ljava/security/cert/X509Certificate;Ljava/lang/String;Ljava/net/Socket;)V
    .registers 4
    return-void
.end method

.method public checkServerTrusted([Ljava/security/cert/X509Certificate;Ljava/lang/String;Ljavax/net/ssl/SSLEngine;)V
    .registers 4
    return-void
.end method

.method public getAcceptedIssuers()[Ljava/security/cert/X509Certificate;
    .registers 2
    const/4 v0, 0x0
    new-array v0, v0, [Ljava/security/cert/X509Certificate;
    return-object v0
.end method
```

Then reference `Lcom/patch/TrustAll;` from any patched call site.

## Hitting the 64K method limit

If your target APK is already at the DEX limit and your edits push it over:

```
Error: [smali] classes.dex: main method reference too many methods (65537)
```

Options:

1. Move your added smali to a new DEX bucket:
   ```
   mkdir unpacked/smali_classes<N+1>
   mv unpacked/smali/com/patch/*.smali unpacked/smali_classes<N+1>/com/patch/
   ```
   apktool assembles it into a new `classes<N+1>.dex`.
2. Remove unused classes from the target — often analytics or unused splits — to reclaim methodID slots. Risky (may break paths you didn't test).
3. Use a helper library injected via `MultiDex.install()` — advanced; requires a custom Application class edit.

## Method / field ID sharing

`method_ids` and `field_ids` are per-DEX. Adding a class that references thousands of external methods increases the `method_ids` count of that DEX only. So distributing new code across DEX files can dodge the limit.

## DEX injection (advanced)

Instead of patching in place, inject a stub DEX at runtime:

- **`DexClassLoader`** — Android's standard mechanism for loading DEX at runtime. Attackers use it for stealth; defenders use it for hot-patching.
- Requires read/write access to a filesystem path Android can execute from — usually `code_cache/` or per-user data.
- Load a companion DEX from `assets/`:
  ```kotlin
  val extra = File(context.codeCacheDir, "patch.dex").also {
      context.assets.open("patch.dex").copyTo(it.outputStream())
  }
  val loader = DexClassLoader(extra.absolutePath, context.codeCacheDir.absolutePath, null, javaClass.classLoader)
  val cls = loader.loadClass("com.patch.Foo")
  cls.getMethod("run").invoke(null)
  ```
- Modern Android may block execution from user-writable paths depending on SELinux + `AndroidManifest` `android:extractNativeLibs`.

Static patching is almost always simpler than runtime DEX injection for pentest work. Injection is worth it when:

- The target APK is very large and rebuilding is slow to iterate.
- You need to bypass an integrity check that compares hash of the shipped `classes.dex` — inject at load time so the on-disk file is unchanged.

## Reading DEX programmatically

- **androguard** — Python; excellent for scripted analysis (`AnalyzeAPK`).
- **dexlib2** (Java, part of smali/baksmali) — programmatic DEX read/write.
- **dexdump** — Android SDK tool; textual dump.
- **baksmali** / **smali** — CLI equivalents to apktool's assemble/disassemble (apktool wraps them + resource handling).

Quick scripted patch example (androguard):

```python
from androguard.core.apk import APK
from androguard.core.dex import DEX

apk = APK("target.apk")
for dex_bytes in apk.get_all_dex():
    dex = DEX(dex_bytes)
    for cls in dex.get_classes():
        if "RootBeer" in cls.name:
            for m in cls.get_methods():
                if m.name.startswith("isRooted"):
                    print(m.name, m.descriptor)
```

Full programmatic patch pipelines are rare; apktool + hand edits + rebuild is the standard flow.

## Common decompile problems

- **String encryption**: strings are byte-array constants decrypted at runtime. `const-string` alone doesn't help. Find the decryption method, hook or emulate it (Frida / androguard) to dump plaintext.
- **Control-flow flattening / opaque predicates**: `switch(state)` on an ever-changing local. `deobfuscate` tools (Simplify, JEB pro) help.
- **Reflection-heavy code**: method names appear as strings, not references. `grep` for the string in smali to find call sites.
- **DEX packers** (BangCle, Tencent MdexProtector, Bitwise): the shipped DEX is a stub loader; the real DEX is decrypted at runtime. Requires runtime dumping (Frida `Java.enumerateLoadedClasses`, `dex-repair`, or `blutter`).

## Handoff

- If checks live in native code (`.so`), see `android-jni-ndk` for JNI-level triage and `reversing-technique` for reversing the shared library.
- If runtime hooking is more appropriate than patching, see `references/hooking-vs-patching.md`.
