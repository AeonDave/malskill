---
name: kotlin-performance
description: "Measurement-first performance workflow for Kotlin on JVM and Android: Macrobenchmark, Microbenchmark, Baseline Profiles, Startup Profiles, R8 full mode, Compose recomposition analysis, coroutine/Flow throughput, Perfetto/JIT tracing, LeakCanary heap analysis. Use when investigating cold-start latency, jank, scroll frames, memory growth, or when tuning R8/PGO output for an Android app or JVM Kotlin library."
license: MIT
compatibility: "Kotlin 2.0+ (K2), Android SDK 26+ (guidance covers up to SDK 36). AGP 8.5+ (features noted per version through 9.x). Tools: androidx.benchmark 1.4+ (Macro/Microbenchmark), androidx.baselineprofile 1.4+, Perfetto, Android Studio Profiler (Otter/Panda). Optional: kotlinx-benchmark (JMH), LeakCanary, vkompose."
metadata:
  author: AeonDave
  version: "1.0"
---

# Kotlin Performance

Measurement-first performance work for Kotlin. Pair with `kotlin-patterns` for idiomatic code and `android-testing` for the test harness that hosts benchmarks.

If the target is a pure JVM library or CLI, most guidance transfers — skip the Android sections.

## When to activate

- Investigating cold/warm/hot start latency, first-frame time, or ANR reports
- Diagnosing scroll jank, animation stutter, or Compose recomposition storms
- Tracing memory growth, GC churn, or leaks in a shipping app
- Deciding whether to enable R8 full mode, ship a Baseline Profile, or add a Startup Profile
- Benchmarking a JVM Kotlin hot path (JMH / kotlinx-benchmark) before proposing a redesign

---

## Rules of engagement

- **Measure on-device against release builds.** Debug APKs run interpreted or with limited AOT; measurements are worthless. Macrobenchmark demands `release` (or a `benchmark` buildType with `signingConfig` + `debuggable = false` + `profileable`).
- **Change one variable at a time.** Log the baseline (before) and delta (after) with the same device, thermal state, and driver.
- **Cold vs warm vs hot** are three different problems — pick the `StartupMode` explicitly.
- **Fix algorithm and data-structure issues first**, then allocations, then micro-optimizations.
- **Do not benchmark on emulators for latency claims.** Use a physical device profile with locked CPU governor (`adb shell cmd power set-fixed-performance-mode-enabled true` when supported, or Gradle-managed devices with `enablePerformanceMode = true`).

---

## Outcome expectations

- Every performance claim is backed by a reproducible Macrobenchmark or JMH run with mean + p50/p90/p99.
- Baseline Profile coverage of hot paths ≥ 30%; JIT-compilation ratio during target flow is quantified.
- R8 full mode + Baseline Profile deltas measured separately, not lumped together.
- No `Thread.sleep` warm-ups; iterations are enforced by the harness.
- Behavior is unchanged: correctness tests pass on the optimized build.

---

## Workflow

1. **Define the symptom precisely.** Cold start / TTID / TTFD, scroll frame time p99, memory retained after N cycles, or throughput ops/sec. Choose one first.
2. **Choose the harness.**
   - Cold/warm/hot start, jank, TTID/TTFD → **Macrobenchmark** (`androidx.benchmark:benchmark-macro-junit4`).
   - Function-level JVM hot path → **Microbenchmark** (`androidx.benchmark:benchmark-junit4`) on device, or **kotlinx-benchmark** / JMH for pure JVM.
   - Memory/leaks → LeakCanary + Android Studio Memory Profiler; heap dumps for retention.
   - System-level (jank, GC, I/O) → Perfetto trace (`adb shell perfetto -c config.pbtx -o trace.perfetto-trace`).
3. **Capture a signed baseline** on the target device. Record mean/p50/p90/p99, allocation, and one Perfetto trace.
4. **Analyze**. In Perfetto or Android Studio: find hot slices (JIT compilation, GC, layout inflation, `androidx.compose.runtime.snapshots`). In Compose reports, find non-restartable/non-skippable functions.
5. **Apply one change.** Enable R8 full mode, add a Baseline Profile, refactor a specific `@Composable`, switch a `Dispatchers.Default` to a bounded pool — one at a time.
6. **Verify.** Re-run the same harness on the same device profile. Compare against baseline; reject changes that regress p99 or introduce non-deterministic variance.

---

## Symptom → first tool mapping

| Symptom | First tool | Second tool |
|---------|------------|-------------|
| Cold start too slow | Macrobenchmark `StartupMode.COLD` + `StartupTimingMetric` | Baseline Profile + Startup Profile |
| Warm/hot start slow | Macrobenchmark `WARM`/`HOT` | Perfetto trace on `bindApplication` |
| Scroll jank (p99 frame > 16 ms) | Macrobenchmark `FrameTimingMetric` | Perfetto + Compose recomposition trace |
| Compose recomposition storm | Compose compiler report + `Modifier.Node` audit | `androidx.compose.runtime.tooling.CompositionData` snapshot |
| Memory growth after N screens | LeakCanary + heap dump comparison | `adb shell dumpsys meminfo <pkg>` |
| Allocations/GC pressure | Microbenchmark `MetricType.Alloc` | Async Profiler + allocation profiler |
| APK size regression | `./gradlew :app:analyzeReleaseBundle` | R8 dictionary + baseline profile diff |
| Native call latency | Microbenchmark + `TraceSectionMetric("JNI transition")` | `@FastNative`/`@CriticalNative` — see `android-jni-ndk` |
| JVM hot path (no Android) | kotlinx-benchmark / JMH | Async Profiler / JFR |

---

## Android release-build knobs (measure each in isolation)

- **R8 full mode**: `android.enableR8.fullMode=true` in `gradle.properties` **and** switch `proguardFiles` from `proguard-android.txt` to `proguard-android-optimize.txt`. Typical: 5–15% smaller APK + faster startup. Full mode enables horizontal class merging, vertical class merging, and interface-method rewriting — will break some reflection-heavy libraries. Verify at runtime, not just compile.
- **`shrinkResources = true`** (paired with `minifyEnabled = true`) — required to strip unused resources. AGP 8.7+ supports **optimized resource shrinking** for ~30% resource file reduction.
- **Baseline Profile**: `androidx.baselineprofile` Gradle plugin generates `baseline-prof.txt` from a Macrobenchmark journey run on a `nonMinified` build. R8 rewrites the rules to match the minified release (introduced in Baseline Profile 8.2+; ~30% method coverage improvement).
- **Startup Profile**: same generator, `includeInStartupProfile = true`. Rearranges DEX layout so critical startup classes land in `classes.dex` — measurable startup win on top of Baseline Profile.
- **PGO for the app process itself**: profiles collected via `adb shell pm dump-profiles <pkg>` can be committed as Cloud Profile input — reserved for late-cycle tuning.

Enable together only after each has been measured separately.

---

## Compose performance

- Enable the Compose compiler stability/metrics report:
  ```kotlin
  composeCompiler {
      reportsDestination = layout.buildDirectory.dir("compose_compiler")
      metricsDestination  = layout.buildDirectory.dir("compose_compiler")
      stabilityConfigurationFile = rootProject.layout.projectDirectory.file("compose_stability.conf")
  }
  ```
  Review the `*-classes.txt` output: every class not marked `stable` breaks skipping. Fix by marking stable in the config file, using `@Immutable`/`@Stable`, or wrapping in a stable holder.
- **Strong skipping mode** (Compose Compiler 1.5.4+, default in newer AGP): treats unstable parameters as `@Stable` when they're equal by structural equality. Reduces recomposition for common patterns (e.g. lambdas with unstable captures) but must be verified with a trace — some hot Composables still need explicit fixes.
- **Recomposition tracing**: Macrobenchmark 1.4+ supports `perfettoSdkTracing = true` — recompositions appear in the Perfetto trace as named slices. Look for slice counts that exceed expected recomposition rounds per user interaction.
- Modifier chain hot paths: prefer `Modifier.Node` API (Compose 1.7+) for custom modifiers over `Modifier.composed { }`, which allocates on every recomposition.
- Lists: `LazyColumn` with unstable `key = { … }` lambda captures triggers full recomposition. Prefer stable, comparable keys (`item.id`); avoid `key = { it.hashCode() }`.

---

## Coroutines & Flow performance

- **Dispatcher choice at the leaf, not the caller.** `withContext(Dispatchers.IO)` around genuine blocking I/O; `Default` for CPU-bound. `IO` has an unbounded thread pool (~64 threads by default) — starving `Default` with I/O work is a common jank source.
- **`limitedParallelism(n)`** on `Dispatchers.IO` for controlled parallelism (`Dispatchers.IO.limitedParallelism(4)`). Prevents thread explosion under load spikes.
- **Backpressure operators** on `Flow`:
  - `buffer(n)` — decouples producer and consumer with a bounded queue. Use when both are CPU-bound but at different rates.
  - `conflate()` — drops intermediate values, keeps only the latest. UI state pipelines.
  - `collectLatest { }` — cancels the previous block on new emission. Search-as-you-type.
  - `debounce(ms)` / `sample(ms)` — throttle by time. User input flows.
- Every `launch { }` allocates a `StandaloneCoroutine`; `async { }` allocates a `DeferredCoroutine`. In a hot loop, prefer `map { }` on a `Flow` over launching per-item.
- Avoid `withContext(Dispatchers.Main)` in the middle of a leaf function — the context switch cost dominates for microsecond-scale work.

---

## Memory & leaks

- **LeakCanary** is now natively integrated into Android Studio Otter (2025.12+) Profiler as a "LeakCanary task"; still install the library on debug builds for continuous detection. In CI/dev, keep `LeakCanary.config = LeakCanary.config.copy(retainedVisibleThreshold = 1)` for aggressive detection.
- Typical Android leak sources:
  - `Context`/`Activity`/`View` held in singletons, static fields, or `object` bodies.
  - `Fragment` view listeners bound to `Fragment.lifecycleOwner` instead of `viewLifecycleOwner`.
  - `Handler(Looper.getMainLooper())` with `postDelayed` referencing a `View`.
  - `GlobalScope.launch { }` capturing an Activity.
- **Heap dumps**: Android Studio → Memory Profiler → Capture Heap Dump. Filter by class, sort by "Retained Size". Compare two dumps N minutes apart to find growth.
- `adb shell dumpsys meminfo <pkg>` gives a quick view of PSS, private clean/dirty, DEX/code. Compare across builds.
- Native memory: `libmemunreachable` (`adb shell dumpsys meminfo <pkg> -a` shows unaccounted native RSS). NDK bugs surface here.

---

## Perfetto tracing

Prefer Perfetto over legacy `systrace`:

```bash
# Interactive: https://ui.perfetto.dev — record via chrome://inspect
# Command line (device):
adb shell perfetto \
  -o /data/misc/perfetto-traces/trace.perfetto-trace \
  -t 20s \
  -b 32mb \
  sched freq idle am wm gfx view binder_driver hal dalvik camera input res
adb pull /data/misc/perfetto-traces/trace.perfetto-trace
```

Key tracks to inspect:

- `am_activity_launch_time` — cold-start slice.
- `Choreographer#doFrame` — every frame; look for slices > 16 ms (60 Hz) or > 8 ms (120 Hz).
- `JIT Compiling %` — significant % during startup = missing Baseline Profile coverage.
- `HeapTaskDaemon` bursts — GC pressure; correlate with allocation profile.
- `Compose:recompose` slices (with `perfettoSdkTracing = true`) — recomposition count per Composable.

Add custom slices for domain workflows:

```kotlin
trace("MyFeature:refresh") {
    // Work
}
```

Or `TraceSectionMetric("MyFeature:%")` in a Macrobenchmark for regression tracking.

---

## JMH / kotlinx-benchmark (pure JVM)

For non-Android Kotlin (backend libraries, tooling) or when isolating a hot function:

```kotlin
// build.gradle.kts
plugins { id("org.jetbrains.kotlinx.benchmark") version "0.4.13" }
benchmark {
    configurations { named("main") { iterations = 5; warmups = 3; iterationTime = 1.seconds } }
    targets { register("main") }
}
```

```kotlin
@State(Scope.Benchmark)
open class ParseBench {
    private val input = "…".toByteArray()
    @Benchmark fun parseA(bh: Blackhole) { bh.consume(parseA(input)) }
    @Benchmark fun parseB(bh: Blackhole) { bh.consume(parseB(input)) }
}
```

Rules:

- Always `Blackhole.consume(result)` — otherwise JIT dead-code-eliminates the whole benchmark.
- Warmups must run enough iterations to reach steady-state JIT (3–5 typically).
- Compare with `benchstat`-style stats, not point comparisons.

---

## Quick review checklist

- Measurement uses `release`/`benchmark` buildType, not `debug`
- Macrobenchmark `StartupMode` is explicit; Frame metrics use realistic user actions (`UiAutomator` scroll, not `Thread.sleep`)
- Baseline Profile includes the actual entry Activity **and** dependency framework calls (auth SDK, image loader, network client init)
- R8 mapping file is preserved (`obfuscated.map`) for crash symbolication
- Compose compiler report has been read; unstable public data classes are annotated or added to the stability config
- Every claimed improvement has a p50/p90/p99 delta, not just mean
- Trace or heap-dump files are committed alongside PR notes for reviewer verification
- No `System.currentTimeMillis()`-based DIY timers — Macrobenchmark or `trace()` sections only

---

## Common anti-patterns

- **Measuring on debug builds** → interpreter overhead dominates; conclusions are wrong.
- **Enabling R8 full mode without testing** → reflection-heavy libraries (Gson, Retrofit, Room without keep rules, older Moshi) break at runtime with `NoSuchMethodException`. Ship staged rollout.
- **Baseline Profile generated on a non-representative journey** → covers the wrong methods. Use realistic user flows, not synthetic loops.
- **`SharingStarted.Eagerly` on repository `Flow`s** → keeps upstream alive forever, leaks work and memory. Use `WhileSubscribed(5_000)`.
- **`Dispatchers.IO` for CPU-bound work** → starves the shared thread pool; use `Default` or a `limitedParallelism` slice.
- **Unstable lambdas captured in a hot `@Composable`** → busts skipping. Hoist state or convert to `remember { }`-scoped values.
- **`for (i in 0..list.size - 1)` in a hot loop with an `Iterable`** → boxes `Int`; use `forEach` / `for (item in list)` for concrete lists.

---

## Resources

Load on demand:

- [references/macrobenchmark-and-microbenchmark.md](references/macrobenchmark-and-microbenchmark.md) — end-to-end setup, StartupTimingMetric, FrameTimingMetric, TraceSectionMetric, allocation metrics, Gradle-managed devices, running on Firebase Test Lab; load when setting up the harness
- [references/baseline-and-startup-profiles.md](references/baseline-and-startup-profiles.md) — Baseline Profile Gradle plugin, generation via BaselineProfileRule, Startup Profile `includeInStartupProfile`, coverage measurement, Cloud Profile pipeline; load when creating or auditing profiles
- [references/compose-recomposition.md](references/compose-recomposition.md) — compiler stability report, strong skipping, `Modifier.Node`, `LazyColumn` key stability, `derivedStateOf`, Perfetto recomposition tracing; load when Compose scroll or animation is the bottleneck
- [references/coroutines-and-flow-performance.md](references/coroutines-and-flow-performance.md) — dispatcher pool sizing, `limitedParallelism`, backpressure operator selection, `Flow` overhead vs `Channel` vs suspend, cold-hot conversion cost; load when async pipelines are slow or bursty
- [references/memory-and-leaks.md](references/memory-and-leaks.md) — LeakCanary integration, heap dump comparison, retained size analysis, Android memory model (PSS/RSS/SwapPss/DEX/code), native memory triage; load when diagnosing OOM, growth, or leak reports
- [references/perfetto-and-tracing.md](references/perfetto-and-tracing.md) — Perfetto config, custom trace sections, Compose SDK tracing, common track cheatsheet, offline trace analysis with the Trace Processor; load when a symptom needs system-level attribution
- [references/jvm-benchmarking.md](references/jvm-benchmarking.md) — kotlinx-benchmark / JMH setup, dead-code elimination, warmup strategy, Blackhole usage, comparing runs, running on CI; load when the hot path is non-Android or must be isolated from the runtime
