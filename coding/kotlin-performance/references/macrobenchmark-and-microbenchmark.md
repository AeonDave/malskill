# Macrobenchmark and Microbenchmark

Load when setting up the Android performance harness or diagnosing why a benchmark is unstable.

## Which to use

| Question | Harness |
|----------|---------|
| Cold/warm/hot start, TTID/TTFD, ANR, jank on real journeys | **Macrobenchmark** — runs on a device against a release-ish APK |
| CPU-bound function-level timing on device | **Microbenchmark** — hosted in `androidTest`, same process as target |
| Non-Android JVM library hot path | kotlinx-benchmark / JMH (see `jvm-benchmarking.md`) |

Never use Microbenchmark to measure app startup — it's in-process; use Macrobenchmark's `StartupMode`.

## Macrobenchmark setup

Separate Gradle module for the benchmark harness:

```
app/
benchmark/          <-- com.android.test module
```

`benchmark/build.gradle.kts`:

```kotlin
plugins {
    id("com.android.test")
    id("org.jetbrains.kotlin.android")
}
android {
    compileSdk = 36
    namespace = "com.example.benchmark"
    defaultConfig {
        minSdk = 26
        targetSdk = 36
        testInstrumentationRunner = "androidx.benchmark.junit4.AndroidBenchmarkRunner"
    }
    targetProjectPath = ":app"
    experimentalProperties["android.experimental.self-instrumenting"] = true
    buildTypes {
        create("benchmark") {
            initWith(buildTypes.getByName("release"))
            signingConfig = signingConfigs.getByName("debug")
            matchingFallbacks += listOf("release")
        }
    }
}
dependencies {
    implementation("androidx.benchmark:benchmark-macro-junit4:1.4.0")
    implementation("androidx.test.uiautomator:uiautomator:2.3.0")
}
```

Target `app/build.gradle.kts` release buildType needs `profileable = true`:

```kotlin
buildTypes {
    release {
        isMinifyEnabled = true
        isShrinkResources = true
        proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
    }
    create("benchmark") {
        initWith(release)
        isMinifyEnabled = true
        isProfileable = true                 // required by Macrobenchmark
        signingConfig = signingConfigs.getByName("debug")
    }
}
```

## Cold start benchmark

```kotlin
@RunWith(AndroidJUnit4::class)
class ColdStartBenchmark {
    @get:Rule val rule = MacrobenchmarkRule()

    @Test fun startup() = rule.measureRepeated(
        packageName = "com.example.app",
        metrics = listOf(StartupTimingMetric()),
        iterations = 10,
        startupMode = StartupMode.COLD,
        setupBlock = { pressHome() }
    ) {
        startActivityAndWait()
    }
}
```

- `iterations = 10` gives stable p50/p90; increase to 20–30 for noisy targets.
- `StartupMode.COLD` — process is killed between iterations (via `am force-stop`).
- `StartupMode.WARM` — activity destroyed, process kept; measures re-inflate.
- `StartupMode.HOT` — activity destroyed but instance held; measures re-render only.
- `pressHome()` in `setupBlock` — realistic cold-start baseline.

## Frame timing (jank)

```kotlin
@Test fun scroll() = rule.measureRepeated(
    packageName = "com.example.app",
    metrics = listOf(FrameTimingMetric()),
    iterations = 5,
    startupMode = StartupMode.WARM,
    setupBlock = { startActivityAndWait() }
) {
    val list = device.findObject(By.res(packageName, "feed"))
    list.setGestureMargin(device.displayWidth / 5)
    repeat(5) {
        list.fling(Direction.DOWN)
        device.waitForIdle()
    }
}
```

- Reports p50/p90/p95/p99 frame durations. p99 > 16 ms (60 Hz) = perceptible jank.
- On 120 Hz devices: budget is 8.3 ms. Set `enablePerformanceMode = true` in Gradle-managed devices to lock refresh rate.
- `list.setGestureMargin` — avoids swipe from edge triggering system gestures (back navigation).

## Custom trace sections

Add slices in the target app:

```kotlin
androidx.tracing.trace("Feed:load") {
    repo.load()
}
```

Then measure them from the benchmark:

```kotlin
metrics = listOf(
    StartupTimingMetric(),
    TraceSectionMetric("Feed:load", TraceSectionMetric.Mode.Sum),
    TraceSectionMetric("JIT Compiling %", label = "JIT compilation"),
)
```

The JIT compilation slice quantifies exactly how much startup time is spent on-device Just-In-Time compilation — directly attributable to missing Baseline Profile coverage.

## Microbenchmark setup

For CPU-bound function-level timing on device:

`app/build.gradle.kts`:

```kotlin
android {
    defaultConfig {
        testInstrumentationRunner = "androidx.benchmark.junit4.AndroidBenchmarkRunner"
    }
}
dependencies {
    androidTestImplementation("androidx.benchmark:benchmark-junit4:1.4.0")
}
```

```kotlin
@RunWith(AndroidJUnit4::class)
class ParserBenchmark {
    @get:Rule val rule = BenchmarkRule()

    private val input = "…".toByteArray()

    @Test fun parseA() = rule.measureRepeated {
        runWithMeasurementDisabled {
            /* setup that must not be timed */
        }
        parseA(input)
    }
}
```

- Microbenchmark auto-handles warmup, thermal throttle detection, and JIT stabilization.
- `runWithMeasurementDisabled { }` for setup inside the timed block.
- Enable allocation counting:
  ```kotlin
  @Test fun parseA_allocs() = rule.measureRepeated(measurementType = MetricType.ALLOC) { … }
  ```

## Running

- Local device: `./gradlew :benchmark:connectedBenchmarkAndroidTest`
- Gradle-managed devices (recommended for CI):
  ```kotlin
  testOptions {
      managedDevices.localDevices {
          create("pixel7api34") {
              device = "Pixel 7"
              apiLevel = 34
              systemImageSource = "aosp"
              enablePerformanceMode = true
          }
      }
  }
  ```
  Then `./gradlew pixel7api34BenchmarkAndroidTest`.
- Firebase Test Lab: `gcloud firebase test android run --type instrumentation --app app.apk --test benchmark.apk`.

## Result inspection

- JSON output: `benchmark/build/outputs/connected_android_test_additional_output/…/*.json`.
- Perfetto traces are attached per iteration under `traces/*.perfetto-trace`. Open in `https://ui.perfetto.dev`.
- The `benchmarkData.json` contains per-iteration stats; feed into a diffing tool (Vkompose, custom scripts) for regression bots.

## Common pitfalls

- Running on emulator → timing is 3–10× off, thermal throttle unpredictable. Only physical devices for latency claims.
- Not fully closing the target app between iterations → `StartupMode.COLD` requires the process to actually die; verify with `adb shell dumpsys activity processes | grep <pkg>`.
- Baseline Profile not applied → the target APK's `assets/dexopt/baseline.prof` must be present. Rebuild with the profile generator enabled.
- Comparing across different devices/OS versions → measurements are not portable. Always fix the device profile.
- Setting `iterations = 1` → single-shot is noisy; ART warmup dominates. Minimum 5 for stability.
- Debuggable target → Macrobenchmark refuses to run against debuggable APKs; the error message is clear but the fix (add a benchmark buildType with `profileable=true, debuggable=false`) is easy to miss.
