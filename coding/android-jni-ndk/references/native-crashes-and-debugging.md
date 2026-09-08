# Native Crashes and Debugging

Load when triaging a native crash (tombstone), setting up sanitizers, uploading symbols, or attaching a debugger to on-device native code.

## Tombstone anatomy

Tombstones are the kernel-level crash records for native process crashes. Stored on device:

- `/data/tombstones/tombstone_00` .. `tombstone_09` (root only)
- Newer Android (11+): `/data/tombstones/tombstone_00.pb` (protobuf format; `tombstonecat` to read)

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

The tombstone shows offsets (`+0x14`) not symbols. Symbolication requires debug builds of the `.so` retained locally.

### `ndk-stack` (easiest)

Pipe the raw tombstone through `ndk-stack` with the symbols directory:

```bash
$NDK/ndk-stack -sym app/build/intermediates/cxx/RelWithDebInfo/*/obj/arm64-v8a < tombstone.txt
```

Output includes source file + line for each frame.

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

### AddressSanitizer (ASan)

Detects heap/stack/global buffer overflows, use-after-free, use-after-return. API 21+.

```kotlin
android {
    defaultConfig {
        ndk { abiFilters += listOf("arm64-v8a") }    // ASan only supported on 64-bit for release
    }
    buildTypes {
        debug {
            packagingOptions.jniLibs.useLegacyPackaging = true
            ndk { debugSymbolLevel = "FULL" }
        }
    }
    externalNativeBuild {
        cmake {
            arguments += "-DANDROID_SANITIZE=address"
        }
    }
}
```

`CMakeLists.txt`:

```cmake
if (ANDROID_SANITIZE STREQUAL "address")
    target_compile_options(mylib PRIVATE -fsanitize=address -fno-omit-frame-pointer)
    target_link_options(mylib PRIVATE -fsanitize=address)
endif()
```

Add wrap script (`app/src/main/resources/lib/<abi>/wrap.sh` for AGP 8+ or `wrap.sh` in the APK):

```bash
#!/system/bin/sh
HERE="$(cd "$(dirname "$0")" && pwd)"
export ASAN_OPTIONS=log_to_syslog=false,allow_user_segv_handler=1
LD_PRELOAD="$HERE/libclang_rt.asan-aarch64-android.so" "$@"
```

Bundle `libclang_rt.asan-aarch64-android.so` from `$NDK/toolchains/llvm/prebuilt/*/lib/clang/*/lib/linux/`.

Runtime: ASan reports fire to logcat with tag `ASAN:DEADLYSIGNAL`. Symbolicated frames included if the debug `.so` is loaded.

### HWASan (Hardware-Assisted ASan)

Faster, lower memory overhead than ASan. Requires ARM64 with MTE (memory tagging extension) — Android 14+ on Pixel 8+. Not portable but worth using in CI for high-fidelity bug detection.

```
-DANDROID_SANITIZE=hwaddress
```

### UndefinedBehaviorSanitizer (UBSan)

Detects integer overflow, null deref, misaligned access, unreachable code.

```cmake
target_compile_options(mylib PRIVATE -fsanitize=undefined -fno-sanitize-recover=undefined)
```

Zero runtime overhead when disabled; small overhead when enabled. Ship-safe for debug/beta builds.

### LeakSanitizer

Detects native heap leaks at process exit. Combine with ASan:

```cmake
target_compile_options(mylib PRIVATE -fsanitize=address)
```

ASan runtime includes LSan; on Android LSan reports at exit.

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
Local ref used after JNI return, or a deleted global. Enable `-Xcheck:jni` in the emulator:
```bash
adb shell setprop dalvik.vm.checkjni true
adb shell stop && adb shell start    # requires reboot
```

### Stack overflow
```
signal 11 (SIGSEGV), code 2 (SEGV_ACCERR), fault addr 0x7ff...
```
Usually deep recursion. Android threads have small stacks (~1 MB main, ~64 KB others).

### Use-after-free
Only visible with ASan. Regular tombstone often shows a garbage pointer offset:
```
pc 000000000badbeef ??? (null)
```

### `abort()` from `__android_log_assert`
```
Abort message: 'Check failed: input != nullptr'
```
Explicit check triggered. Message is verbatim.

## Anti-patterns

- Not preserving symbols → tombstones are unactionable.
- Enabling ASan in a release build → 2× memory overhead, unshippable.
- Using `printf` for debug → often flushes late, missing right before crash. Use `__android_log_print(ANDROID_LOG_ERROR, tag, fmt, ...)`.
- Debugging with `gdb` remote → deprecated on Android; LLDB has better ART integration.
- Ignoring Play Console pre-symbolicated crashes and manually symbolicating instead → wastes time; the auto-symbolicated view is more accurate.
- Not enabling `strictly-typed` JNI checks in dev: `-Xcheck:jni` in the ART command line catches many issues cheaply.
