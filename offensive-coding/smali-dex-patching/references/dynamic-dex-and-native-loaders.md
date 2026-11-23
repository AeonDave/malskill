# Dynamic DEX and native loaders

Load when the app or sample uses `DexClassLoader`, `InMemoryDexClassLoader`, `JNI_OnLoad`, or a native `.so` to decrypt or execute a second-stage payload. This is the main pattern behind hybrid Android malware and advanced app loaders.

## Table of contents

1. [Modern runtime diagnosis](#modern-runtime-diagnosis)
2. [What to look for](#what-to-look-for)
3. [Why the hybrid pattern matters](#why-the-hybrid-pattern-matters)
4. [Practical endpoint triage](#practical-endpoint-triage)
5. [Recovery pattern after loader capture](#recovery-pattern-after-loader-capture)
6. [In-the-wild examples](#in-the-wild-examples-20252026)
7. [Review a DEX-module host](#review-a-dex-module-host)
8. [Build a DEX-module host](#build-a-dex-module-host)
9. [Rust `.so` on Android](#rust-so-on-android)
10. [Anti-analysis patterns in native `.so`](#anti-analysis-patterns-in-native-so)
11. [Reverse-engineering notes](#reverse-engineering-notes)
12. [Related skills](#related-skills)

## Modern runtime diagnosis

Record runtime API/build, target SDK, ABI, library build IDs, class loader and the exact exception or crash. Distinguish a rejected load, a successful load and execution of a concrete method; none implies the others.

| Condition | Expected constraint | What to verify |
|---|---|---|
| Android 14+, target 34+, file-backed DEX/JAR/APK loading | Dynamically loaded files must be read-only | File state and the actual loader exception; do not apply a file rule to an in-memory buffer |
| Android 17+, target 37+, native files loaded with `System.load()` | Read-only required; otherwise `UnsatisfiedLinkError` | Actual path and permissions; distinguish this cause from ABI/dependency/linker errors |
| Android 17+, target 37+, mutation of a `static final` field | Reflection raises `IllegalAccessException`; JNI field mutation crashes | Call site and field modifiers before diagnosing memory corruption or an app anti-analysis check |
| Native code on a 16 KB device | Packaging, ELF alignment and runtime page assumptions matter independently | Use [16 KB checks](../../../coding/android-jni-ndk/references/16kb-page-size.md); record compatibility mode |

See [Android 14 target changes](https://developer.android.com/about/versions/14/behavior-changes-14#safer-dynamic-code-loading) and [Android 17 target changes](https://developer.android.com/about/versions/17/behavior-changes-17). Reproduce compatibility failures in a minimal test build using the same API/target/ABI; do not classify a platform rejection as a vulnerability or bypass it to claim production reachability.

For recovered modules, preserve container/DEX/native hashes, source path or buffer slice, parent class loader and observed invocation. An absent module or untriggered path is missing coverage, not proof of benign behavior. A staged loader also appears in legitimate modular software; classify behavior from the operations it performs.

## What to look for

### Java/Kotlin loader signs

```java
String dexPath = ...;
DexClassLoader cl = new DexClassLoader(
    dexPath,
    context.getCodeCacheDir().getAbsolutePath(),
    null,
    context.getClassLoader()
);
Class<?> cls = cl.loadClass("com.example.payload.Main");
```

```java
byte[] raw = ...;
InMemoryDexClassLoader loader = new InMemoryDexClassLoader(ByteBuffer.wrap(raw), getClassLoader());
```

Also search for:

- `Class.forName(...)`
- `getDeclaredMethod(...)`
- `Method.invoke(...)`
- reflection-based `Base64`, `AES`, `XOR`, or blob decoding
- asset or file reads followed immediately by a classloader call
- `createPackageContext` with `CONTEXT_INCLUDE_CODE` or `CONTEXT_IGNORE_SECURITY`: another package's code loaded into the caller. A package-name prefix or a matching class name is not a signer check; see [Context](https://developer.android.com/reference/android/content/Context#createPackageContext(java.lang.String,%20int))

### Native loader signs

```java
static {
    System.loadLibrary("loader");
}
```

```cpp
jint JNI_OnLoad(JavaVM* vm, void* reserved) {
    // decode, map, or load a payload
    return JNI_VERSION_1_6;
}
```

Search for:

- `JNI_OnLoad`
- `RegisterNatives`
- `dlopen`, `dlsym`, `android_dlopen_ext`
- `System.load`, `Runtime.load`, `loadLibrary`
- `fork`, `exec`, `ptrace`, sandbox checks, anti-debugging

## Why the hybrid pattern matters

Managed Java/Kotlin code is often the UI/entry shell. The actual malicious or security-sensitive logic may be moved into:

- a native `.so` that decodes and executes a payload
- a second-stage DEX fetched from C2 or a blob inside the APK
- a module loaded from app storage or a mounted zip archive

This is a major source of false negatives in static triage: the class you see first is only the bootstrap, not the payload logic.

## Practical endpoint triage

### Step 1: locate the entry point

```bash
grep -RIn "System.loadLibrary\|DexClassLoader\|InMemoryDexClassLoader\|JNI_OnLoad\|Class.forName\|Method.invoke" unpacked/smali* 2>/dev/null
```

### Step 2: inspect the asset or storage path

```bash
find unpacked -type f | grep -Ei "(dex|jar|apk|so|bin|blob)"
```

### Step 3: reverse the native bootstrap

```bash
unzip -j target.apk 'lib/arm64-v8a/*.so' -d libs/
llvm-nm -D libs/*.so | grep -E "JNI_OnLoad|Java_"
```

### Step 4: hook at the boundary

```javascript
Java.perform(() => {
    const DexClassLoader = Java.use('dalvik.system.DexClassLoader');
    DexClassLoader.$init.overload('java.lang.String', 'java.lang.String', 'java.lang.String', 'java.lang.ClassLoader')
        .implementation = function(dexPath, optDir, libPath, parent) {
            console.log('[DexClassLoader] dexPath=' + dexPath);
            return this.$init(dexPath, optDir, libPath, parent);
        };
});
```

```javascript
const loader = Process.findModuleByName('libloader.so');
const addr = loader === null ? null : loader.findExportByName('JNI_OnLoad');
if (addr) {
    Interceptor.attach(addr, {
        onEnter(args) {
            console.log('[JNI_OnLoad] loader active');
        }
    });
}
```

This lookup requires the observed library to be mapped and the export to exist. If initialization already ran, attaching now does not recover that event. Follow the [Frida session/timing checks](../../../offensive-tools/rev/frida/references/android-ios.md#android-session-and-hook-qualification) and confirm a hook hit before claiming loader coverage.

## Recovery pattern after loader capture

Choose the capture source from the loader path; a load event alone does not prove that payload bytes were collected:

- If the package DEX already contains the relevant logic, analyze it before runtime dumping.
- AOSP [`DexClassLoader`](https://android.googlesource.com/platform/libcore/+/refs/heads/main/dalvik/src/main/java/dalvik/system/DexClassLoader.java) loads classes from JAR/APK files with a `classes.dex` entry; preserve the observed archive and inspect its DEX entries.
- AOSP [`InMemoryDexClassLoader`](https://android.googlesource.com/platform/libcore/+/refs/heads/main/dalvik/src/main/java/dalvik/system/InMemoryDexClassLoader.java) takes DEX bytes from each supplied `ByteBuffer` slice between `position()` and `limit()`; capture those exact slices, not buffer capacity.
- If the payload is only reached at runtime, exercise the relevant app path and capture the loader's actual input. A loader hook or successful dumper exit alone is not evidence of a complete recovery.
- Parse the artifact with a DEX-aware tool and confirm expected app classes plus relevant concrete method implementations. The [DEX format](https://source.android.com/docs/core/runtime/dex-format) permits `code_off == 0` for abstract/native methods; missing code in relevant concrete methods means the capture may be partial or a stub.
- Export any native libs separately and analyze them with Ghidra / `llvm-nm`.

## In-the-wild examples (2025–2026)

These are documented, public-source architectures — use them to calibrate triage expectations.

### MiningDropper (Cyble, 2025–2026)

Modular Android dropper combining crypto mining with banking trojan / RAT delivery.

```
APK (trojanized Lumolight)
├── Application subclass → System.loadLibrary("requisitionerastomous")
│
├── lib/arm64-v8a/librequisitionerastomous.so
│   ├── XOR-obfuscated strings (device/emulator checks)
│   └── decrypts Stage 1 asset → AES key = SHA-1(filename)
│
├── assets/encrypted_blob
│   └── Stage 1 DEX (loaded via DexClassLoader)
│       ├── fake Google Play update overlay
│       └── decrypts Stage 2 config + payload archive
│           └── Stage 2 → split-APK installer
│               └── Final payload: BTMOB RAT / banking trojan / miner
```

Key patterns: filename-derived AES key, anti-emulation in native code, `DexClassLoader` chaining across 3+ stages, split-APK reconstruction.

### Triada firmware variant (Kaspersky, 2025)

Pre-installed in compromised firmware — not a normal APK install.

```
Compromised system framework
└── loads binder.so (native, in system partition)
    ├── hooks Zygote / app_process
    └── distributes additional modules
        ├── Java/DEX modules (injected into app processes)
        └── native modules
```

Key insight: even firmware-level infections are hybrid (native bootstrap → managed modules). `binder.so` is the loader; the functional payload includes DEX.

### ToxicPanda / TgToxic (Cleafy → Bitsight, 2024–2026)

Banking trojan with continuous evolution: DGA, sandbox evasion, encrypted C2.

```
APK
├── classes.dex
│   ├── Accessibility abuse (overlay, credential capture)
│   ├── DGA for C2 resolution
│   └── encrypted config → AES decrypt at runtime
│
└── lib/arm64-v8a/libnative.so
    ├── sandbox/emulator detection
    └── C2 crypto routines
```

Key patterns: native `.so` for anti-analysis + crypto, managed layer for Android framework abuse (Accessibility, overlays, SMS).

### Anatsa (ThreatFabric, 2024–2025)

Droppers on Google Play run as legitimate apps and turn malicious in an update weeks after release, once they have a user base. The update either installs Anatsa as a separate app or loads a stage in memory:

```
Play Store app (legitimate at install)
└── update, weeks later
    ├── downloads and installs the Anatsa APK          (2025 campaign)
    └── InMemoryDexClassLoader for the stage DEX       (2024 droppers)
        └── banker with overlay injection, target list refreshed from C2
```

Lesson: a store build reviewed at release says nothing about the next update. See [ThreatFabric 2024](https://www.threatfabric.com/blogs/anatsa-trojan-returns-targeting-europe-and-expanding-its-reach) and [ThreatFabric 2025](https://www.threatfabric.com/blogs/anatsa-targets-north-america-uses-proven-mobile-campaign-process).

### Mamont (Kaspersky, 2025)

The most prevalent banking trojan of 2025 in Kaspersky telemetry, with verdicts such as `Trojan-Banker.AndroidOS.Mamont.da` and `.db` among the year's most widespread. See [the mobile threat landscape in 2025](https://securelist.com/mobile-threat-report-2025/119076/).

## Review a DEX-module host

Trace the actual class-loader delegation and artifact provenance; neither file-backed nor in-memory loading creates a security sandbox. Inspect integrity/authenticity verification before execution, the trusted source of verification material, and the capabilities granted to loaded code. A public key embedded in native code is not a secret or an isolation boundary; moving a check from Java to native code does not establish resistance to a compromised process.

For failed module calls, distinguish missing/renamed host APIs, class identity mismatches, JNI linkage and lifecycle races from malformed DEX. Reproduce with the relevant build configuration before attributing a failure to obfuscation or a security control. See [Android dynamic code-loading risks](https://developer.android.com/privacy-and-security/risks/dynamic-code-loading) and the [ClassLoader contract](https://developer.android.com/reference/java/lang/ClassLoader).

## Build a DEX-module host

Design rules for an app that loads signed modules at runtime:

- **Delegation**: give the module loader the host class loader as parent, so host API classes resolve to the host's types. Same-named classes loaded by a separate loader are distinct types; pass objects only through the module API.
- **Keep surface**: keep what compiled modules link against (`-keep` on the module API package and on native bridge methods with their `<clinit>`). R8 renaming or inlining otherwise breaks modules with `NoClassDefFoundError` or `NoSuchMethodError` at runtime, not at build.
- **Verify before staging**: a signature over `header || module`, with the signature field excluded from the signed range, checked with a public key compiled into the host; then size cap and quarantine of rejected payloads. This protects against tampered delivery only: the public key is not a secret and verification inside the host process is hookable.
- **At rest and in flight**: keep modules encrypted with a Keystore key until use, stage to a temporary file and move it into place with `ATOMIC_MOVE`; contain module-supplied IDs against path traversal. File-backed loaders need read-only files on Android 14+ (target 34+); `InMemoryDexClassLoader` avoids the file.
- **Lifecycle**: hold an execution lease per module and release views, callbacks and threads before unloading; an unload that races a call into module code crashes the process.

## Rust `.so` on Android

Rust compiles to the same ELF ARM64 `.so` as C/C++ via NDK targets. From the loader's perspective it's identical — `System.loadLibrary` works the same.

### Build setup

```toml
# Cargo.toml
[lib]
crate-type = ["cdylib"]

[dependencies]
jni = { version = "0.21", default-features = false }
```

```bash
rustup target add aarch64-linux-android armv7-linux-androideabi
cargo install cargo-ndk
cargo ndk -t arm64-v8a -t armeabi-v7a --platform 21 -- build --release
# Output: target/aarch64-linux-android/release/libnativecore.so
```

### JNI export from Rust

```rust
use jni::objects::{JByteArray, JClass};
use jni::sys::jbyteArray;
use jni::JNIEnv;

#[unsafe(no_mangle)]
pub extern "system" fn Java_com_example_NativeCore_process(
    mut env: JNIEnv,
    _class: JClass,
    input: JByteArray,
) -> jbyteArray {
    let data = env.convert_byte_array(&input).unwrap();
    // ... process data ...
    let out = env.byte_array_from_slice(&data).unwrap();
    out.into_raw()
}
```

### Triage implication

A Rust `.so` is still an ELF — analyze with Ghidra/IDA/r2 the same way. Differences:

- symbol names are Rust-mangled (e.g., `_ZN4core3ops...`) — use `rustfilt` or Ghidra's Rust demangler
- no `libc` dependency for pure Rust code — uses `libdl` and `libm` directly
- panic handler generates `abort()` at JNI boundary — look for `rust_begin_unwind`
- `jni` crate registers via standard `JNI_OnLoad` → same `RegisterNatives` hook applies

For reverse engineering Rust `.so`, the same Frida hooks work: `RegisterNatives` interception, `dlopen` monitoring, pattern-based Interceptor. The function ABI is identical to C.

### Android targets

| ABI | Rust target | Notes |
|-----|------------|-------|
| `arm64-v8a` | `aarch64-linux-android` | Primary — 95%+ of modern devices |
| `armeabi-v7a` | `armv7-linux-androideabi` | Legacy 32-bit |
| `x86_64` | `x86_64-linux-android` | Emulators |
| `x86` | `i686-linux-android` | Old emulators |

## Anti-analysis patterns in native `.so`

Common techniques found in banking trojans and commercial packers:

| Technique | What it does | Triage approach |
|-----------|-------------|----------------|
| `JNI_OnLoad` + `RegisterNatives` | Hides JNI method names from `nm`/`strings` | Hook `RegisterNatives` in `libart.so` via Frida |
| `ptrace(TRACEME)` | Self-trace to block debugger attach | `Interceptor.replace(ptrace, ...)` → return 0 |
| `/proc/self/maps` scan | Detect Frida, debugger, injected libs | Filter-rewrite via `BufferedReader.readLine` hook |
| `/proc/self/status` check | Read `TracerPid` for debugger detection | Hook `fopen`/`fgets` to zero out TracerPid |
| Thread name scan | `/proc/self/task/<tid>/comm` for `gum-js-loop`, `gmain` | Hook `pthread_setname_np` to rename Frida threads |
| Timer-based detection | Measure execution time across hooks (slow = instrumented) | Minimize hook overhead; use `Interceptor.replace` over `attach` |
| Fork + child check | Fork, child traces parent, parent checks `/proc/<child>/status` | Hook `fork()` to return expected values |
| XOR/RC4/AES string obfuscation | Decrypt strings at runtime only | Dump after decryption via Frida memory read |
| `dlopen` from memory | Load `.so` from `memfd_create` or `/proc/self/fd/` | Hook `memfd_create` and `android_dlopen_ext` |

## Reverse-engineering notes

- `ClassLoader` + reflection is often used to hide code from static analysis.
- `JNI_OnLoad` often does the orchestration before the first Java method is called.
- Native stubs may decode XOR/RC4/AES payloads and then execute them in memory.
- Some malware libraries patch their own `JNI_OnLoad` or use `RegisterNatives` to hide the method names from simple `strings`-based triage.
- In hybrid samples, always dump the second-stage DEX/`.so` and analyze it as a separate artifact — the first-stage loader is often not the payload.
- MiningDropper-style chains can have 3+ stages; follow each `DexClassLoader` call until you reach the terminal payload.

## Related skills

- `android-jni-ndk` for native loading rules and crash triage
- `android-jni-ndk/references/rust-jni.md` for Rust-on-Android development patterns
- `smali-dex-patching` for patching the staged DEX after it is recovered
- `frida` for hooking the load path and dumping the payload; see `frida/references/android-ios.md` for RegisterNatives / dlopen hooks
- `mobile-technique` for full reverse and app risk triage
