# JVM Benchmarking (kotlinx-benchmark / JMH)

Load when benchmarking non-Android Kotlin code (backend libraries, CLI tools, shared modules) or isolating a hot function outside the Android runtime.

## Why JMH and not just `System.nanoTime()`

- JIT warmup takes 5–15k iterations before steady state. Untimed rounds are noise.
- Dead-code elimination: `for (i in 0..1_000_000) hash(x)` compiles to nothing if the result is unused.
- Loop unrolling, escape analysis, inlining — all optimizations that skew hand-rolled timers.
- CPU frequency scaling, thermal throttling, GC pauses — JMH controls for or reports each.

kotlinx-benchmark wraps JMH so Kotlin/Multiplatform code benchmarks with the same annotations.

## Setup

`build.gradle.kts`:

```kotlin
plugins {
    kotlin("jvm") version "2.0.21"
    id("org.jetbrains.kotlinx.benchmark") version "0.4.13"
    kotlin("plugin.allopen") version "2.0.21"
}
allOpen { annotation("org.openjdk.jmh.annotations.State") }

dependencies {
    implementation("org.jetbrains.kotlinx:kotlinx-benchmark-runtime:0.4.13")
}

benchmark {
    configurations {
        named("main") {
            iterations = 5
            warmups = 3
            iterationTime = 1
            iterationTimeUnit = "sec"
            outputTimeUnit = "us"
        }
    }
    targets { register("main") }
}
```

- `allOpen` on `@State` — JMH generates subclasses; Kotlin classes are `final` by default.
- `iterationTime = 1 sec` × `iterations = 5` = 5 s of measured data per benchmark.
- Warmups = 3 rounds not counted toward results.

## Anatomy of a benchmark

```kotlin
import kotlinx.benchmark.*
import org.openjdk.jmh.annotations.OutputTimeUnit
import java.util.concurrent.TimeUnit

@State(Scope.Benchmark)
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MICROSECONDS)
open class ParseBench {
    private lateinit var input: ByteArray

    @Setup fun setup() {
        input = ByteArray(64 * 1024).also { Random(42).nextBytes(it) }
    }

    @Benchmark fun parseA(bh: Blackhole) {
        bh.consume(parseA(input))
    }

    @Benchmark fun parseB(bh: Blackhole) {
        bh.consume(parseB(input))
    }
}
```

Rules:

- Every result must be consumed by `Blackhole.consume(x)`. Otherwise JIT eliminates the whole benchmark and reports absurd throughput.
- `@Setup` is per-iteration or per-invocation (choose with `@Setup(Level.Invocation)`, expensive; usually `Level.Trial`).
- `@State(Scope.Benchmark)` — shared instance across threads (default for single-threaded). Use `Scope.Thread` for per-thread state.
- Do not print inside a benchmark — I/O crashes the measurement.

## Modes

| Mode | What it measures |
|------|------------------|
| `Throughput` (default) | Ops/time — good for high-frequency operations |
| `AverageTime` | Mean time per op — most intuitive for latency |
| `SampleTime` | Samples times — useful for distribution (p50/p90/p99) |
| `SingleShotTime` | One invocation — cold measurement (JIT not stable) |
| `All` | All of the above |

For latency-sensitive work: `Mode.AverageTime` + `Mode.SampleTime` combined.

## Running

```bash
./gradlew :module:benchmark
```

Output under `build/reports/benchmarks/main/<timestamp>/`. Includes JSON, CSV, and human-readable summary.

## Running a subset

```bash
./gradlew :module:benchmark --tests "*ParseBench.parseA"
```

Or `-Pkotlinx.benchmarks.mode=Throughput` to override modes for a run.

## Result stability

Report:

- **Score** ± **error** at 99.9% confidence.
- If error is > 5% of score, run more iterations or check for interference (background processes, thermal, other builds).
- Never report a single-run number. Always ± error.
- Multiple JVM forks (`@Fork(2)` for two separate JVMs) — accounts for JVM-startup variance.

## Comparing runs

- Save baseline JSON: `--rff baseline.json`.
- Save contender JSON: `--rff contender.json`.
- Compare with `jmh-benchmark-report` or a Python diff script: mean delta + overlap of confidence intervals.
- Only claim a win if intervals do not overlap.

## Common gotchas

- **Loop in the benchmark body**:
  ```kotlin
  @Benchmark fun bad() {
      for (i in 0..1000) hash(i.toString())     // JIT unrolls; result ambiguous
  }
  ```
  Move the loop into `@State` setup and benchmark one iteration.
- **Nano-second scale benchmarks** below ~10 ns are dominated by JMH's own overhead. Batch the work.
- **Autoboxing** in generic code: `List<Int>` is `List<Integer>` under the hood. Use `IntArray` or specialized collections for primitives in hot paths.
- **Kotlin `inline` functions**: JMH is applied to the *caller* — so `list.forEach { … }` where `forEach` is `inline` benchmarks the inlined loop, not the abstraction cost.
- **`@State(Scope.Thread)` on a shared mutable state** — cross-thread benchmarks silently race.
- **Building the benchmark JAR with kapt/ksp processors** — increases classpath cost; run against `runtimeClasspath` only.
- **Comparing benchmarks across CI hosts** — noise dominates. Fix the runner or use containers with pinned CPUs.

## JMH options worth knowing

- `-p paramName=v1,v2,v3` — parameterized runs on `@Param("v1")`-annotated fields.
- `-t 4` — thread count for concurrent benchmarks.
- `-prof gc` — collect GC statistics per benchmark (allocations, pause count).
- `-prof stack` — sampling stack profiler to find where time actually goes.
- `-prof jfr` — Java Flight Recorder integration for deep JVM profiling.

## When to prefer Android Microbenchmark over JMH

- The code depends on Android framework APIs (`Context`, `Bitmap`, `Choreographer`).
- The target device (Pixel, budget phone) has different thermal/CPU profile than a server JVM.
- You care about ART-specific behavior (`@FastNative`, DEX layout) — JMH runs on OpenJDK.

Otherwise, JMH is faster to iterate, more stable, and better instrumented than Microbenchmark.
