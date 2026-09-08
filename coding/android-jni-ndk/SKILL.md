---
name: android-jni-ndk
description: "Kotlin/Java ↔ native (C/C++/Rust) bridging on Android: NDK setup, JNI mechanics, `System.loadLibrary`, `RegisterNatives`, `@FastNative`/`@CriticalNative`, reference hygiene, exception propagation, 16 KB page-size compliance, native crash triage. Use when building or debugging a native module, embedding a `.so` library, decoding a native ANR or SIGSEGV, or reverse-engineering an APK's native code paths."
license: MIT
compatibility: "Android SDK 26+ (guidance covers up to SDK 36; Android 15 mandates 16 KB page alignment for API 35+ from Nov 2025). NDK r27+ (r28 recommended for 16 KB page-size). CMake 3.22+ or ndk-build. Optional: Rust with cargo-ndk + jni-rs; async-profiler for native profiling; addr2line + ndk-stack for crash symbolication."
metadata:
  author: AeonDave
  version: "1.0"
---

# Android JNI & NDK

Everything that leaves the pure Kotlin/Java world: native shared libraries (`.so`), the JNI boundary, cross-boundary refs and exceptions, and the modern Android packaging constraints (16 KB pages, split APKs, App Bundles).

Pair with `kotlin-performance` for measuring native-call overhead, `smali-dex-patching` for offensive patching of the managed side, and `mobile-technique` for auditing shipped native code.

## When to activate

- Embedding a C/C++/Rust library in a Kotlin/Java app
- Debugging JNI reference leaks, `LocalReferenceTable overflow`, or `ArrayIndexOutOfBoundsException` originating in native code
- Diagnosing a native crash (`SIGSEGV`, `SIGABRT`) from a tombstone or Play Console ANR
- Migrating to 16 KB page-size compliance for Google Play (deadline Nov 2025 for apps targeting API 35+)
- Building AAB / APK with multiple ABIs and understanding split delivery
- Reverse-engineering a shipped `.so` to understand what native code an app runs

---

## Core mental model

- The **JVM (ART)** and **native code** share a process but different memory managers, exception systems, and reference tracking.
- Every call across the boundary has cost (~25–100 ns even for `@CriticalNative`) — batch and design coarse APIs, not chatty ones.
- Native code owns **local references** valid within one JNI call and **global references** valid until explicitly deleted. Losing track of either leaks or crashes.
- The GC cannot pause a thread running native code — long native work blocks the whole runtime's GC cycle.
- One process contains one ART instance; multiple `.so` files load into the same address space and can call each other freely.

---

## Native call cost tiers (from Android runtime docs, Angler 2016 baseline; still directional)

| Call type | Overhead | Restrictions |
|-----------|----------|--------------|
| Standard JNI | ~115 ns | Full `JNIEnv*` + `jobject this`/`jclass clazz` |
| `@FastNative` | ~35 ns | Skips locking; body cannot access `this` from arbitrary heap without care |
| `@CriticalNative` | ~25 ns | Removes `JNIEnv*` and `jclass` params; must be `static`, primitive-only args, cannot call back into JVM |

On Android 12+ the compiled managed→native call for `@CriticalNative` is nearly free — worth the constraints for hot paths. See `references/fast-critical-native.md`.

---

## Workflow: adding native code

1. **Add the NDK Gradle plugin** to `app/build.gradle.kts`:
   ```kotlin
   android {
       externalNativeBuild {
           cmake {
               path = file("src/main/cpp/CMakeLists.txt")
               version = "3.22.1"
           }
       }
       defaultConfig {
           externalNativeBuild {
               cmake {
                   cppFlags += listOf("-std=c++20", "-Wall", "-Wextra")
                   arguments += listOf(
                       "-DANDROID_STL=c++_shared",
                       "-DCMAKE_SHARED_LINKER_FLAGS=-Wl,-z,max-page-size=16384"
                   )
                   abiFilters += listOf("arm64-v8a", "armeabi-v7a", "x86_64")
               }
           }
       }
       ndkVersion = "27.2.12479018"
   }
   ```
2. **Declare native methods in Kotlin**:
   ```kotlin
   class NativeCrypto {
       external fun encrypt(input: ByteArray, key: ByteArray): ByteArray
       companion object { init { System.loadLibrary("native_crypto") } }
   }
   ```
3. **Implement in C++**:
   ```cpp
   #include <jni.h>
   extern "C" JNIEXPORT jbyteArray JNICALL
   Java_com_example_NativeCrypto_encrypt(JNIEnv* env, jobject /* this */,
                                          jbyteArray input, jbyteArray key) {
       // See references/jni-refs-and-exceptions.md for correct handling
   }
   ```
4. **Register natives explicitly** (faster startup, better obfuscation):
   ```cpp
   static const JNINativeMethod kMethods[] = {
       {"encrypt", "([B[B)[B", reinterpret_cast<void*>(NativeCrypto_encrypt)},
   };
   jint JNI_OnLoad(JavaVM* vm, void*) {
       JNIEnv* env;
       if (vm->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6) != JNI_OK) return -1;
       jclass cls = env->FindClass("com/example/NativeCrypto");
       env->RegisterNatives(cls, kMethods, sizeof(kMethods) / sizeof(*kMethods));
       return JNI_VERSION_1_6;
   }
   ```
5. **Build** with `./gradlew :app:externalNativeBuildDebug` to iterate quickly. `assembleRelease` handles ABI splits.
6. **Verify 16 KB alignment** (mandatory Nov 2025+ for API 35+ apps on Play):
   ```bash
   llvm-readelf -lW libnative_crypto.so | awk '/LOAD/ {print $NF}'
   # Every LOAD segment's Align field must be >= 0x4000 (16384) on arm64-v8a and x86_64.
   ```

---

## ABI reality check

| ABI | Use |
|-----|-----|
| `arm64-v8a` | Modern Android devices (2019+). **Required.** |
| `armeabi-v7a` | Older 32-bit ARM. Still ~10% of Play install base as of 2025. |
| `x86_64` | Emulators, Chromebooks, some Windows Subsystem for Android. Include for dev. |
| `x86` | Effectively dead; skip unless supporting legacy emulator paths. |

App Bundle (AAB) splits per-ABI automatically. `abiFilters` in the module controls what's built and shipped.

## 16 KB page size (Nov 2025 Play deadline)

- Android 15+ devices can boot with 16 KB kernel pages for improved performance.
- All `.so` files for `arm64-v8a` and `x86_64` (the 64-bit ABIs) must have LOAD segments aligned to 16 KB.
- NDK r27+ / AGP 8.3+ / CMake 3.22+ handle this automatically. NDK r26 and older need manual linker flags:
  ```cmake
  # CMakeLists.txt for older toolchains
  target_link_options(mylib PRIVATE
      "-Wl,-z,max-page-size=16384"
      "-Wl,-z,common-page-size=16384"
  )
  ```
- Verify per-`.so`:
  ```bash
  llvm-readelf -lW libmylib.so | grep -E "LOAD" | awk '{ print $NF }'
  # Expect Align = 0x4000 for each LOAD segment on 64-bit ABIs
  ```
- Third-party AARs must also comply — check every `.so` in `build/intermediates/merged_native_libs/`.
- Code must not assume `PAGE_SIZE = 4096`. Query at runtime via `sysconf(_SC_PAGESIZE)` or `getpagesize()`.

Full workflow with automation tools: `references/16kb-page-size.md`.

---

## Loading and packaging

- `System.loadLibrary("native_crypto")` looks for `libnative_crypto.so` in the APK's `lib/<abi>/` folder.
- `System.load("/absolute/path.so")` loads from arbitrary path — used for dynamic feature modules and (offensively) for injected libraries.
- `Runtime.getRuntime().load*()` are aliases.
- Compressed `.so` files (`android:extractNativeLibs="true"`) are the legacy default; modern AAPT2/AGP defaults to uncompressed for direct `mmap` from APK (faster load, no disk copy). Verify with `zipinfo -v app.apk | grep "\.so"` — flags should show "stored" not "deflated" for optimal load.
- Multiple `.so` files can depend on each other; use `System.loadLibrary` in dependency order or `Java_com_example_NativeCrypto_encrypt` will fail at first call because the dependency isn't loaded.

---

## JNI reference hygiene (top failure source)

- **Local refs** — automatically freed at JNI method return. Table default size 512 entries; exceed and JVM aborts with `LocalReferenceTable overflow`.
  - Explicitly `env->DeleteLocalRef(obj)` inside long loops.
  - Use `PushLocalFrame(capacity)` / `PopLocalFrame(nullptr)` for scoped batches.
- **Global refs** — survive across JNI calls. Free with `env->DeleteGlobalRef(g)`. **Every** global ref must be paired with a delete or it leaks until process exit.
- **Weak global refs** — GC can collect the referent; check with `IsSameObject(weakRef, nullptr)` before use.
- Never store a `JNIEnv*` — it's per-thread. Store `JavaVM*` and call `AttachCurrentThread` from other threads.
- Threads created in native code (`pthread_create`) that call back into Java **must** attach: `vm->AttachCurrentThread(&env, nullptr)`; detach in a cleanup handler via `DetachCurrentThread`.

Full patterns: `references/jni-refs-and-exceptions.md`.

---

## Exception propagation

- After **every** JNI call that can throw (`CallXxxMethod`, `NewObject`, `FindClass`, `GetFieldID`, ...), check with `env->ExceptionCheck()`.
- Native functions **cannot** call additional JNI functions with a pending exception (except a small allowlist: `DeleteLocalRef`, `ExceptionClear`, ...). Doing so aborts with `JNI DETECTED ERROR IN APPLICATION`.
- Handle by either propagating (return early — the Kotlin caller sees the exception) or clearing (`env->ExceptionClear()` — silently swallow, discouraged).
- Native code cannot throw C++ exceptions across the JNI boundary — they trigger `abort()`. Wrap C++ code in `try { } catch (const std::exception& e) { env->ThrowNew(env->FindClass("java/lang/RuntimeException"), e.what()); }`.

---

## Native crash triage

Tombstones live at `/data/tombstones/` (root only) or Play Console → Vitals → Crashes. Format:

```
signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), fault addr 0x0
   x0  0000000000000000  x1  00000073c98a7c00  ...
   pc  00000073c94a0234  libnative_crypto.so!encrypt+0x14
```

Symbolicate:

```bash
$NDK/ndk-stack -sym app/build/intermediates/cxx/RelWithDebInfo/*/obj/arm64-v8a < tombstone.txt
```

Or manually:

```bash
$NDK/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-addr2line -Cfe libnative_crypto.so 0x14
```

Rules:

- Ship `libmylib.so.debug` (via AGP `packagingOptions { doNotStrip("**/lib*.so") }` for local, or upload debug symbols to Play Console for production).
- Set CMake to `Release` with debug info: `-DCMAKE_BUILD_TYPE=RelWithDebInfo`. Strip separately for shipping.
- Enable Address Sanitizer on debug builds:
  ```cmake
  target_compile_options(mylib PRIVATE -fsanitize=address -fno-omit-frame-pointer)
  target_link_options(mylib PRIVATE -fsanitize=address)
  ```
  Add wrap script per NDK docs. Available for API 21+.

Full triage flow: `references/native-crashes-and-debugging.md`.

---

## Rust on Android (increasingly common)

- Use `cargo-ndk` + `jni-rs` crate:
  ```bash
  cargo install cargo-ndk
  cargo ndk -t arm64-v8a -t armeabi-v7a -t x86_64 -o app/src/main/jniLibs build --release
  ```
- `jni-rs` provides safe wrappers around `JNIEnv`, refs, and exceptions.
- Rust `panic` across JNI = process abort. Wrap in `catch_unwind` + convert to `ThrowNew`.
- 16 KB alignment: `rustflags = ["-Clink-arg=-Wl,-z,max-page-size=16384"]` in `.cargo/config.toml`.
- Chrome, Firefox, and increasing parts of AOSP use Rust for security-critical native code. Prefer Rust over C++ for new modules where practical.

Details: `references/rust-jni.md`.

---

## Native performance

- Include callers of native methods in the Baseline Profile (see `kotlin-performance/references/baseline-and-startup-profiles.md`) — ART pre-compiles the caller side, reducing transition overhead.
- Explicit `RegisterNatives` at `JNI_OnLoad` avoids name-based lookup at first call (faster) and hides method names from `strings` output.
- For hot paths that would otherwise pay the JNI transition per element, batch: pass a whole array + length once, not one element at a time.
- Prefer `GetPrimitiveArrayCritical` / `ReleasePrimitiveArrayCritical` for zero-copy access to primitive arrays — but **cannot** call JNI or block during the critical region.
- CPU affinity: `sched_setaffinity` is available on Android for pinning to big cores. Rarely worth it, but valid for realtime audio/video threads.

---

## Reverse-engineering a shipped `.so`

Offensive angle covered in depth by `mobile-technique/references/android-ipc-attack-surface.md` and the `reversing-technique` skill:

- `unzip -j app.apk 'lib/arm64-v8a/*.so' -d libs/`
- `llvm-nm -D libmylib.so | grep Java_` — lists JNI-exported symbols; the class/method mapping is in the name.
- `objdump -d libmylib.so | less` or Ghidra for structural analysis.
- Native anti-analysis: check for `ptrace` self-attach, `read /proc/self/status | grep TracerPid`, JNI reflection to hide method registration. Frida hooks work at the native symbol boundary.

---

## Quick review checklist

- Every `NewGlobalRef` paired with `DeleteGlobalRef`; every `GetStringUTFChars` paired with `ReleaseStringUTFChars`
- `ExceptionCheck()` after every JNI call that can throw
- No C++ exception escapes into JNI code
- Native methods declared `external fun` (Kotlin) or `native` (Java), `System.loadLibrary` inside a companion `init { }`
- `JNI_OnLoad` uses `RegisterNatives`; no reliance on name-based discovery in release builds
- `.so` files are 16 KB aligned for `arm64-v8a` and `x86_64`
- `abiFilters` explicitly listed; no accidental 32-bit-only or `x86` shipping
- Debug symbols uploaded to Play Console (or `.symbols.zip` archived in CI) for crash symbolication
- No `System.load` from a user-writable path (`/sdcard/...`) — DoS + code injection vector

---

## Common anti-patterns

- **Cached `JNIEnv*` used from another thread** — undefined behavior; store `JavaVM*` and `AttachCurrentThread`.
- **Local ref used across JNI calls** — only valid until the current native function returns. Convert to global if needed longer.
- **`GetStringChars` without matching `ReleaseStringChars`** — pins the string in memory until process exit.
- **Building for one ABI only** — most Play install groups need `arm64-v8a` + `armeabi-v7a` minimum.
- **`extractNativeLibs="true"`** in the manifest — legacy; costs disk and startup time. Remove; AGP handles it.
- **Assuming `PAGE_SIZE == 4096`** — breaks on 16 KB Android 15+ devices.
- **Passing a `ByteArray` back-and-forth per byte** — batch or use `ByteBuffer.allocateDirect` for zero-copy.
- **Loading `.so` from an intent-supplied path** — RCE. Fixed paths from installed APK only.

---

## Resources

Load on demand:

- [references/jni-refs-and-exceptions.md](references/jni-refs-and-exceptions.md) — local vs global refs, `PushLocalFrame`, `ExceptionCheck` after every fallible call, `JavaVM*` thread attach, common `LocalReferenceTable overflow` diagnosis; load when writing or debugging JNI implementation code
- [references/fast-critical-native.md](references/fast-critical-native.md) — `@FastNative` / `@CriticalNative` optimization, restrictions, DIY annotation classes (missing from public SDK), `RegisterNatives` binding, when the win is real; load when a native call is on a hot path measured at > 1 M ops/sec
- [references/16kb-page-size.md](references/16kb-page-size.md) — compliance workflow, CMake/ndk-build flags, verification tools (`android-16kb-validator`, `llvm-readelf`), third-party AAR audit, Play deadline; load when the app has any native code and targets API 35+
- [references/native-crashes-and-debugging.md](references/native-crashes-and-debugging.md) — tombstone anatomy, `ndk-stack`, `addr2line`, LLDB attach for on-device debugging, ASan/UBSan setup, Play Console symbol upload; load when triaging a native crash or setting up sanitizers
- [references/rust-jni.md](references/rust-jni.md) — `cargo-ndk` + `jni-rs` workflow, safe wrapper patterns, `catch_unwind` for panic containment, cross-build for all ABIs, 16 KB alignment; load when embedding a Rust library or evaluating Rust for a new native module
- [references/native-memory-and-crashes.md](references/native-memory-and-crashes.md) — native heap allocation tracking (`libc.debug.malloc`), LeakSanitizer setup, JNI ref leaks (not visible in Java heap dump), `dumpsys meminfo` native section triage; load when investigating native memory growth or OOM in a native module
