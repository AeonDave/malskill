# Dynamic DEX and native loaders

Load when the app or sample uses `DexClassLoader`, `InMemoryDexClassLoader`, `JNI_OnLoad`, or a native `.so` to decrypt or execute a second-stage payload. This is the main pattern behind hybrid Android malware and advanced app loaders.

## Table of contents

1. [What to look for](#what-to-look-for)
2. [Why the hybrid pattern matters](#why-the-hybrid-pattern-matters)
3. [Practical endpoint triage](#practical-endpoint-triage)
4. [Recovery pattern after loader capture](#recovery-pattern-after-loader-capture)
5. [Reverse-engineering notes](#reverse-engineering-notes)
6. [Related skills](#related-skills)

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
const addr = Module.getExportByName('libloader.so', 'JNI_OnLoad');
if (addr) {
    Interceptor.attach(addr, {
        onEnter(args) {
            console.log('[JNI_OnLoad] loader active');
        }
    });
}
```

## Recovery pattern after loader capture

Once the loader is identified, dump the exact second-stage asset and then inspect it as a new DEX or native module:

- dump the decrypted buffer to `/sdcard/`
- pull it with `adb pull`
- run `dex2jar`, `jadx`, or `baksmali` on it
- export any native libs and analyze with Ghidra / `llvm-nm`

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

### Anatsa / TeaBot (2025 resurgence)

Distributed via trojanized Play Store apps (document readers, cleaners). Malicious code appears only in a delayed update weeks after install.

```
Legitimate app (initial install)
└── update mechanism
    └── downloads + decrypts payload DEX
        └── InMemoryDexClassLoader or DexClassLoader
            └── Banking trojan with overlay injection
```

Key insight: no native `.so` in many variants — the loader is pure Java reflection + encrypted assets. ~90K users reached on Play Store (2025).

### Mamont (Kaspersky, 2025 top banker)

Top detected banking trojan family (15.6% of banker detections in 2025 per Securelist). Multiple variants (`da`, `db`, `bc`, `ev`, `ek`, `cb`, `hi`). Primarily targets Russian-speaking users.

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
