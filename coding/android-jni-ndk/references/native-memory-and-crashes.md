# Native Memory and Ref Leaks

Load when investigating native heap growth, native OOM, or JNI reference leaks that don't appear in Java heap dumps.

## Native heap vs Java heap

- **Java heap** (Dalvik heap on legacy) — object allocations via `new`, tracked by ART GC, dumped via `.hprof`.
- **Native heap** — `malloc`/`new` from C/C++ code, tracked by libc's allocator, **invisible** to Java heap dumps.
- **JNI reference tables** — separate from both; leak indicators are process-wide counters.

`dumpsys meminfo <pkg>` breaks it down:

```
  Native Heap:     45312 kB     ← libc-allocated
  Dalvik Heap:     32540 kB     ← ART heap
  Stack:            2044 kB
  Ashmem:            156 kB     ← shared memory (GPU textures often)
  Other dev:         208 kB
  .so mmap:        18452 kB     ← code + rodata from .so files
  .apk mmap:        6144 kB
  .dex mmap:        4552 kB
  Unknown:         12480 kB     ← untracked; growing = suspicious
  TOTAL:          121888 kB
```

Growing "Native Heap" line under stable "Dalvik Heap" = native leak.

## `libc.debug.malloc` tracker (debug builds)

Available in userdebug builds (usually AOSP dev builds, not stock consumer devices):

```bash
adb shell setprop libc.debug.malloc.program com.example.app
adb shell setprop libc.debug.malloc.options backtrace=8
adb shell am force-stop com.example.app
# Launch app, run scenario
adb shell am dumpheap -n <pid> /data/local/tmp/native.txt
adb pull /data/local/tmp/native.txt
```

Output: per-allocation backtrace of every unfreed allocation. Sort by size for the largest offenders.

## LeakSanitizer (portable)

ASan runtime includes LSan; enable at build:

```cmake
target_compile_options(mylib PRIVATE -fsanitize=address)
target_link_options(mylib PRIVATE -fsanitize=address)
```

At process exit, LSan reports:

```
=================================================================
==15437==ERROR: LeakSanitizer: detected memory leaks
Direct leak of 4096 byte(s) in 1 object(s) allocated from:
    #0 0x7f... in operator new(unsigned long)
    #1 0x7f... in doStuff() /path/to/foo.cpp:42
    #2 0x7f... in Java_com_example_Native_stuff /path/to/jni.cpp:15
```

Requires the process to exit cleanly; Android apps often die by `am kill`. Set `LSAN_OPTIONS=exitcode=0` (else Play may flag the exit code as a crash) and trigger `System.exit(0)` from a test-only entry to force LSan report.

## Malloc-debug variants (userdebug only)

Alternative to LSan for AOSP-based devices without full ASan setup:

```bash
adb shell setprop libc.debug.malloc.options "leak_track backtrace=8 allocator=async"
```

Options:

- `leak_track` — record every allocation, report unfreed at process exit.
- `guard` — poison bytes around each allocation; detect adjacent overflow.
- `free_track` — keep freed allocations pinned; detect use-after-free.
- `backtrace=N` — retain N frames of stack per allocation.

## JNI reference leaks

Global refs don't show up in either heap. Symptoms:

- `LocalReferenceTable overflow (max=512)` — many local refs in one call; not usually a "leak" but a coding bug.
- Process OOM with `dumpsys meminfo` showing normal Java + Native but total memory > 1 GB — global refs, which count toward "Unknown" allocations.

Track from ART:

```bash
adb shell dumpsys meminfo <pkg> -a | grep -E "GlobalRefs|WeakGlobalRefs"
```

Output:

```
Global refs: 12432
Weak Global refs: 234
```

Baseline the count at app start; if it grows steadily under a repeated workflow, you're leaking globals.

Enable JNI check for verbose reporting:

```bash
adb shell setprop dalvik.vm.checkjni true
adb shell stop && adb shell start   # requires reboot; or use emulator with -writable-system
```

Then logcat prints warnings for every ref leak, invalid handle use, and thread-attach issues.

## Symptom → root cause

| Symptom | Likely cause |
|---------|--------------|
| `Native Heap` grows steadily; `Dalvik Heap` stable | `malloc`/`new` without matching `free`/`delete` in native module |
| `Ashmem` grows | Un-recycled `Bitmap`s, GPU textures, `MediaCodec` buffers |
| `Unknown` grows | Un-freed global JNI refs, direct `ByteBuffer.allocateDirect` not garbage-collected |
| `.so mmap` grows | Loading many `.so` (dynamic feature modules) without unload — usually acceptable but track |
| Process killed by `LMKD` (low memory) | Total footprint exceeded threshold; find largest category to attack first |
| `SIGSEGV` in unrelated code path | Use-after-free earlier corrupted a struct; LSan/ASan required |

## Direct `ByteBuffer` retention

```kotlin
val buf = ByteBuffer.allocateDirect(10 * 1024 * 1024)   // 10 MB off-heap
```

- Off-heap; GC counts only the ~8-byte wrapper.
- Released when the wrapper becomes unreachable + `PhantomReference` triggers cleaner.
- If wrapped in a `WeakReference` or referenced by a native global, may never be freed.

Fix: `sun.misc.Cleaner` explicitly on API 28+ via `((DirectBuffer) buf).cleaner().clean()` — reflective, requires HiddenApiBypass on API 29+. Prefer scoped ownership.

## Bitmap memory

`Bitmap` on API 26+ lives on the native heap. Recycled via `.recycle()` returns memory immediately; without recycle, GC eventually collects.

- Prefer image loaders (Coil, Glide) — they manage the pool.
- Manually loading `BitmapFactory.decodeStream(...)` in a loop without recycling exhausts native heap fast.
- `dumpsys meminfo <pkg>` — bitmap memory shows as "Graphics" or "GL mtrack" depending on OpenGL usage.

## Native profiling for allocation hot paths

`heapprofd` (Perfetto):

```
data_sources {
    config {
        name: "android.heapprofd"
        heapprofd_config {
            sampling_interval_bytes: 4096
            process_cmdline: "com.example.app"
        }
    }
}
```

Records every allocation attributed to backtrace. Load into Perfetto UI → Native heap profiles view → flame graph.

Alternative: `simpleperf record -e alloc-bytes:kmalloc` on rooted / userdebug devices.

## Anti-patterns

- Ignoring "Unknown" line in `dumpsys meminfo` — that's where global refs and untracked direct buffers show up.
- Recycling `Bitmap` manually while an image loader still references it → double-free crash later.
- LSan alone catches C++/Rust malloc leaks; use `-Xcheck:jni` for global ref leaks. They complement.
- Enabling `libc.debug.malloc.options` in production → 3× memory overhead, unusable.
- Blaming ART for growing Java heap when the culprit is native — always break down `dumpsys meminfo` before optimizing.
