# Native Crashes and Debugging

Load when triaging a native crash (tombstone), setting up sanitizers, uploading symbols, or attaching a debugger to on-device native code.

## Tombstone anatomy

Tombstones are native process crash reports produced by Android's userspace crash machinery. Preserve the full report and nearby logcat before records rotate.

- Direct access to `/data/tombstones/` requires appropriate device privileges; do not assume an app or ordinary shell can read it.
- On API 31+, an app can obtain its own native-crash protobuf through `ApplicationExitInfo.getTraceInputStream()` for `REASON_CRASH_NATIVE`. It can return null when the circular trace buffer has overwritten the record. See the [API contract](https://developer.android.com/reference/android/app/ApplicationExitInfo#getTraceInputStream()).

Play Console → Vitals → Android Vitals → Crashes surfaces them for shipped apps.

Fields of interest:

```
signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), fault addr 0x0     ← what and where
Cause: null pointer dereference                                 ← libbacktrace hint

Abort message: 'Check failed: input != nullptr'                 ← for SIGABRT

pid: 12345, tid: 12345, name: com.example.app  >>> com.example.app <<<

x0  0000000000000000  x1  00000073c98a7c00  ...                 ← register state
sp  00000073c94a0000  pc  00000073c94a0234                      ← stack + program counter

backtrace:
  #00 pc 0000000000000234  libnative_crypto.so (encrypt+0x14) (BuildId: ab12cd34)
  #01 pc 0000000000000f88  libnative_crypto.so (Java_..._encrypt+0x48)
  #02 pc 000000000041e2ac  libart.so (art_quick_generic_jni_trampoline+0x1c)
  #03 pc 000000000012ef60  base.apk (com.example.NativeCrypto.encrypt)     ← managed frame
```

Signals worth memorizing:

| Signal | Meaning | Common cause |
|--------|---------|--------------|
| SIGSEGV (11) | Segmentation fault | NULL deref, bad pointer, use-after-free |
| SIGABRT (6) | Explicit abort | `assert()`, `__android_log_assert`, C++ terminate |
| SIGBUS (7) | Bus error | Misaligned access, mmap I/O error |
| SIGFPE (8) | Arithmetic exception | Division by zero, integer overflow with -ftrapv |
| SIGILL (4) | Illegal instruction | Corrupted code, ISA extension not supported |

## Symbolication

Match the crashed ABI and native build ID to retained unstripped libraries or debug symbols. A tombstone can already contain function names; file/line recovery still needs matching symbols. Use the module-relative `pc` column, not the function displacement (`+0x14`) or a raw ASLR address, with `addr2line`.

### `ndk-stack` (easiest)

Pipe the raw tombstone through `ndk-stack` with the symbols directory:

```bash
$NDK/ndk-stack -sym app/build/intermediates/cxx/RelWithDebInfo/*/obj/arm64-v8a < tombstone.txt
```

Output can include source file and line when the matching debug information exists. Preserve the initial asterisk line in copied logcat traces; [ndk-stack](https://developer.android.com/ndk/guides/ndk-stack) uses it to recognize the dump.

### `llvm-addr2line` (single address)

```bash
$NDK/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-addr2line \
    -e libnative_crypto.so -f -i -C 0x234
```

- `-e` — executable
- `-f` — show function name
- `-i` — inline callers
- `-C` — demangle C++

### AGP symbol packaging

Retain unstripped `.so` for symbolication without shipping them:

```kotlin
android {
    buildTypes {
        release {
            ndk {
                debugSymbolLevel = "FULL"      // or "SYMBOL_TABLE"
            }
            packagingOptions {
                jniLibs {
                    keepDebugSymbols += "**/*.so"    // when shipping local test builds
                }
            }
        }
    }
}
```

Play Console → App bundle explorer → Debug symbols to upload; Play Store then symbolicates production tombstones for you.

## Sanitizers

### HWASan for Android native tests

Prefer [HWASan](https://developer.android.com/ndk/guides/hwasan) for supported native test builds. It supports 64-bit Arm from NDK r21 / Android 10 (API 29); it does **not** require MTE hardware.

- Android 14+ supports a debuggable app with a packaged `arm64-v8a` `wrap.sh` using `LD_HWASAN=1 exec "$@"`. Follow the [wrap-script packaging requirements](https://developer.android.com/ndk/guides/wrap-script), including `useLegacyPackaging = true` for that test variant. This route is incompatible with `android:useAppZygote`; use the documented alternative system-image setup when that feature must remain enabled.
- Android 13 and earlier require a compatible HWASan Android system image, not merely the compiler flag.
- Use shared libc++ when needed, not `c++_static`. With NDK r27+, `-DANDROID_SANITIZE=hwaddress` is supported by the standard CMake toolchain; it does not work with `ANDROID_USE_LEGACY_TOOLCHAIN_FILE=false`.
- Standalone HWASan executables on Android 14+ need NDK r26b or newer. Deploy their runtime dependencies as well as the executable.

For per-target CMake instrumentation, apply both compile and link options in the test variant:

```cmake
target_compile_options(mylib PRIVATE -fsanitize=hwaddress -fno-omit-frame-pointer)
target_link_options(mylib PRIVATE -fsanitize=hwaddress)
```

Keep an explicit test-only known-fault check to confirm the runtime is active before interpreting a clean campaign. Missing instrumentation in dependencies limits what a clean run establishes.

### ASan, MTE, and sampled detectors

The [NDK ASan app workflow](https://developer.android.com/ndk/guides/asan) starts at API 27 and has been unsupported since 2023. Use it only as a documented fallback when HWASan cannot serve the target, and verify its runtime; host ASan and AOSP platform build recipes have different conditions.

[MTE and GWP-ASan](https://developer.android.com/ndk/guides/memory-debug) are distinct from HWASan. MTE needs supporting hardware/software; GWP-ASan samples allocations. Record which detector actually fired. Absence of a sampled report is not evidence that every access was checked.

### UndefinedBehaviorSanitizer (UBSan)

Choose the required checks and instrument the code that contains them; `undefined` includes signed integer overflow, not every possible integer error.

```cmake
target_compile_options(mylib PRIVATE -fsanitize=undefined -fno-sanitize-recover=undefined)
target_link_options(mylib PRIVATE -fsanitize=undefined)
```

Keep the sanitizer policy and abort/recovery behavior explicit in the test configuration.

### LeakSanitizer

For native leak detection, load [native-memory-and-crashes.md](native-memory-and-crashes.md). Do not infer that an Android runtime runs leak checks merely because the build uses an address sanitizer.

## On-device debugging with LLDB

Attach LLDB to a running process:

```bash
# Push lldb-server to device
adb push $NDK/toolchains/llvm/prebuilt/linux-x86_64/lib/clang/*/lib/linux/aarch64/lldb-server /data/local/tmp/
adb shell chmod +x /data/local/tmp/lldb-server

# Start it on device
adb shell "/data/local/tmp/lldb-server platform --server --listen '*:1234'"

# Forward port
adb forward tcp:1234 tcp:1234

# Attach from host
lldb
(lldb) platform select remote-android
(lldb) platform connect connect://localhost:1234
(lldb) process attach --name com.example.app
```

Or launch with Android Studio's native debugger — it wires all of this automatically.

`ndk-gdb` is deprecated; use LLDB.

## `simpleperf` for native profiling

```bash
adb shell simpleperf record -e task-clock -f 1000 -p $(pidof com.example.app) -o /data/local/tmp/perf.data --duration 10
adb pull /data/local/tmp/perf.data
$NDK/simpleperf/simpleperf report --sort dso,symbol
```

Or from Android Studio Profiler: CPU → Callee tree → System Trace or Native Callchain.

Common flags:

- `-e task-clock` — CPU time (default). Alternative: `-e cpu-cycles`, `-e cache-misses`.
- `-g` — call graph.
- `--call-graph fp` — frame-pointer unwinding (faster, requires `-fno-omit-frame-pointer` build).
- `--symfs <dir>` on report — path to unstripped `.so` for symbolication.

## Common crash patterns

### NULL deref
```
signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), fault addr 0x0
Cause: null pointer dereference
```
Standard C bug. Usually a missing `nullptr` check on a return from Java, e.g. `env->GetStringUTFChars` returning null on OOM.

### JNI misuse
```
JNI DETECTED ERROR IN APPLICATION: use of invalid jobject 0x71ac000000
Aborted
```
Local ref used after JNI return, or a deleted global. CheckJNI is normally enabled on the emulator. For subsequently launched apps on a regular test device:
```bash
adb shell setprop debug.checkjni 1
```
Restart the test app and verify `Late-enabling CheckJNI` in logcat; restore the property afterward. A debuggable app also enables CheckJNI. See [JNI diagnostics](https://developer.android.com/ndk/guides/jni-tips#extended-checking).

### Stack overflow
```
signal 11 (SIGSEGV), code 2 (SEGV_ACCERR), fault addr 0x7ff...
```
Inspect recursion depth, guard-page faults, and the actual thread stack configuration; do not infer the stack size from the thread being managed or native.

### Use-after-free
A plain tombstone may show only a later invalid access. HWASan or another applicable memory detector can provide the access and allocation/free history. Confirm object lifetime from that evidence; an unusual pointer value alone does not establish use-after-free.

### `abort()` from `__android_log_assert`
```
Abort message: 'Check failed: input != nullptr'
```
Explicit check triggered. Message is verbatim.

## Anti-patterns

- Not preserving symbols → tombstones are unactionable.
- Treating a test sanitizer runtime as a production deployment default.
- Using `printf` for debug → often flushes late, missing right before crash. Use `__android_log_print(ANDROID_LOG_ERROR, tag, fmt, ...)`.
- Debugging with `gdb` remote → deprecated on Android; LLDB has better ART integration.
- Trusting symbolized output without checking the crashed build identity; hosted and local symbolication both depend on the correct artifacts.
- Not enabling `strictly-typed` JNI checks in dev: `-Xcheck:jni` in the ART command line catches many issues cheaply.

For signal interpretation and examples, use [AOSP native crash diagnosis](https://source.android.com/docs/core/tests/debug/native-crash).
