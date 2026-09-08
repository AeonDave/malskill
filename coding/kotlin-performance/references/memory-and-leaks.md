# Memory and Leaks

Load when investigating memory growth, OOM, retained-heap regressions, or when integrating leak detection into a debug/CI build.

## Android memory model quick reference

Per-process metrics (`adb shell dumpsys meminfo <pkg>`):

| Metric | Meaning |
|--------|---------|
| **PSS** (Proportional Set Size) | Physical memory attributed proportionally to this process |
| **Private Dirty** | Modified pages not shared — the "real" leak indicator |
| **Private Clean** | Read-only pages exclusive to this process |
| **DEX** | DEX code memory (typically ~stable) |
| **Native Heap** | `malloc`-backed NDK allocations |
| **Graphics** | GL surfaces, textures, EGL |
| **`.oat`/`.art`** | AOT-compiled code and image |

`SwapPss` shows swapped-out pages (Android 8+); not a leak in itself but a signal of pressure.

Sample:

```bash
adb shell dumpsys meminfo com.example.app -d
# → look at TOTAL PSS, "Private Dirty" for user classes
```

## LeakCanary

- Now natively integrated into Android Studio Otter (2025.12+) Profiler as a "LeakCanary task" — the IDE runs the same detector against the target process.
- Standalone library still preferred for continuous dev-build detection.

Setup:

```kotlin
debugImplementation("com.squareup.leakcanary:leakcanary-android:2.14")
```

Configuration (in `Application.onCreate`):

```kotlin
if (BuildConfig.DEBUG) {
    LeakCanary.config = LeakCanary.config.copy(
        retainedVisibleThreshold = 1,          // aggressive in dev
        computeRetainedHeapSize = true,
    )
}
```

Interpreting a leak trace:

1. Read from top to bottom — the top of the trace is the leak trigger (Activity destroyed, ViewModel cleared).
2. The bottom is the GC root holding the reference.
3. Every arrow says "field X of class Y references Z". Find the last arrow going into your code — the fix is usually there.
4. Common root types:
   - `Thread` — background worker holding a captured reference.
   - `AndroidLeakFixes` — LeakCanary auto-tracked framework leaks (usually not your bug).
   - `WeakReference` in a `Handler` message queue — canonical `Handler(Looper.getMainLooper()).postDelayed({ view.doThing() }, 1000)`.

## Manual heap dumps

Android Studio → Profiler → Memory → Capture Heap Dump. Or programmatically:

```kotlin
Debug.dumpHprofData("/sdcard/dump.hprof")
```

Pull and convert to Java-standard format:

```bash
adb pull /sdcard/dump.hprof
$ANDROID_SDK/platform-tools/hprof-conv dump.hprof dump-std.hprof
```

Open in **Eclipse MAT** (Memory Analyzer Tool) — much better path-to-GC-root queries than Android Studio's built-in viewer.

Workflow:

1. Take dump A at a stable state (after warmup, after N cycles).
2. Perform the suspected leaky action.
3. Take dump B.
4. In MAT: **Compare** or **Path to GC Roots (exclude weak references)**. Retained objects in B but not A = leak candidates.

## Retained size

- **Shallow size** — size of the object itself.
- **Retained size** — total memory freed if this object is GC'd (self + everything only reachable through it).
- Sort by retained size when hunting leaks; a `View` with retained size 500 KB usually holds a `Context` chain into `MotherActivity` with its whole layout.

## Fragment / ViewBinding leaks

The most common pattern:

```kotlin
private var _binding: FragmentFooBinding? = null
private val binding get() = _binding!!

override fun onCreateView(…) = FragmentFooBinding.inflate(…).also { _binding = it }.root

override fun onDestroyView() {
    super.onDestroyView()
    _binding = null           // ← required; otherwise the binding holds every view
}
```

Miss the `onDestroyView` reset and every rotation duplicates the retained view graph.

## Coroutine / listener leaks

- `GlobalScope.launch { }` capturing a `View` or `Activity` — no lifecycle, leak persists to app termination.
- `Handler(Looper.getMainLooper()).postDelayed(runnable, 1000)` where `runnable` captures a view — leak lasts until the delay fires.
- `Room` `LiveData.observeForever { }` without `removeObserver` — leaks the observer.
- Registering a `BroadcastReceiver` in `onCreate` and unregistering in `onDestroy` (should be `onStart`/`onStop` for lifecycle-safe listeners).

## Native memory (NDK)

- Not visible in the Java heap dump. Track via `adb shell dumpsys meminfo <pkg>` → "Native Heap" line.
- Use `adb shell setprop libc.debug.malloc.program <pkg>` + `adb shell setprop libc.debug.malloc.options backtrace` to enable the libc allocation tracker (debug builds only).
- LeakSanitizer available for NDK builds targeting API 30+:
  ```
  externalNativeBuild {
      cmake {
          arguments += "-DANDROID_STL=c++_shared"
          cppFlags += "-fsanitize=leak"
      }
  }
  ```
  Ships a stack backtrace on process exit for anything not `free()`d.
- See `android-jni-ndk/references/native-memory-and-crashes.md` for JNI local/global ref leaks (not visible in either heap).

## `dumpsys` cheatsheet

```bash
adb shell dumpsys meminfo <pkg> -d          # full per-category breakdown
adb shell dumpsys procstats --hours 3       # process history for the last 3h
adb shell dumpsys gfxinfo <pkg> framestats  # per-frame render timing
adb shell dumpsys activity <pkg>            # activity/task stack
adb shell dumpsys package <pkg>             # component + permission dump
adb shell cmd package dump-profiles <pkg>   # baseline profile inspection
```

## Anti-patterns

- Using `Debug.dumpHprofData` in production without gate → writes to sdcard on every run, floods analytics.
- Only looking at total PSS → shared pages inflate the number. Focus on Private Dirty.
- Ignoring native memory — a growing Native Heap under a stable Java heap is a JNI leak.
- Chasing LeakCanary reports for framework-internal leaks (`InputMethodManager`, `Choreographer`) — LeakCanary auto-suppresses most; if not, verify against upstream Android issues before "fixing" your code.
- Comparing PSS across OS versions → memory accounting changed multiple times (Android 8, 11, 14). Only compare same-OS.
- Not disabling animations before benchmarking memory: animation callbacks keep GC candidates alive briefly. `settings put global window_animation_scale 0`.
