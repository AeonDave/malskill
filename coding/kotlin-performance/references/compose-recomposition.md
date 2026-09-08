# Compose Recomposition and Rendering Performance

Load when Compose UI is the bottleneck: scroll jank, animation stutter, unnecessary recomposition, or slow first frame.

## The compiler stability report

Enable in `build.gradle.kts`:

```kotlin
composeCompiler {
    reportsDestination = layout.buildDirectory.dir("compose_compiler")
    metricsDestination  = layout.buildDirectory.dir("compose_compiler")
    stabilityConfigurationFile = rootProject.layout.projectDirectory.file("compose_stability.conf")
}
```

Then `./gradlew :app:assembleRelease`. Output under `app/build/compose_compiler/`:

- `<module>-classes.txt` — every class the compiler saw + stability verdict (`stable`, `unstable`, `runtime`).
- `<module>-composables.txt` — every `@Composable` + `restartable` / `skippable` verdict.
- `<module>-module.json` — summary counts.

Rules to read:

- **`unstable`** class = anything referencing it in a `@Composable` triggers recomposition even when equal. Fix: make the fields `val`; use immutable collections (`kotlinx.collections.immutable`); mark stable in `compose_stability.conf`; wrap in an `@Immutable` value class.
- **`restartable=false, skippable=false`** on a `@Composable` = every ancestor recomposition re-runs its body. Usually because a return type is unstable or the body reads a `MutableState` outside the intended scope.
- Public `data class` used in Compose parameters should be either `@Immutable` (all-val + stable field types) or listed in the stability config.

`compose_stability.conf` format (one FQN per line):

```
// External library that we know is safe
com.google.common.collect.ImmutableList
kotlinx.collections.immutable.*
com.example.dto.*
```

## Strong skipping mode

Enabled by default in Compose Compiler 1.5.4+ (bundled with Kotlin 2.0 + AGP 8.5+):

- Composables that would otherwise be non-skippable (unstable params) become skippable **if params are equal by structural equality**.
- Reduces recomposition surface for common patterns (lambdas captured in unstable classes, `List<T>` where `T` is unstable).
- Not a substitute for stability — a truly unstable class still needs `equals` to be meaningful, otherwise skipping never triggers.
- Verify in the compiler report: composables that flipped to `skippable` count against the win.

## Recomposition tracing with Perfetto

Enable in Macrobenchmark:

```kotlin
@get:Rule val rule = MacrobenchmarkRule()

@Test fun scroll() = rule.measureRepeated(
    packageName = "com.example.app",
    metrics = listOf(FrameTimingMetric()),
    iterations = 5,
    startupMode = StartupMode.WARM,
    experimentalConfig = com.example.PerfettoConfig().withCompose(),   // enable
    setupBlock = { startActivityAndWait() }
) {
    /* scroll */
}
```

Simpler: set `perfettoSdkTracing = true` in the benchmark rule (androidx.benchmark 1.4+):

```kotlin
androidx.benchmark {
    perfettoSdkTracing = true
}
```

In the Perfetto trace, each recomposition of a named composable appears as a slice `Compose:Recompose <FunctionName>`. Look for:

- Composables recomposing more times than user actions warrant.
- Composables recomposing on every frame during scroll (usually a `MutableState` read in a parent triggers a cascade).
- Composables with `SlotTable` inspection showing deep nested recompositions.

## `derivedStateOf`, `remember`, and read tracking

- `remember { … }` — caches across recompositions; the `key` argument re-computes when the key changes. Overuse: cheap allocation with a key that's already stable (defeats the point).
- `derivedStateOf { … }` — creates a `State` that recomputes only when its inputs change. Use when reading multiple `State`s but the result is a derived boolean/int used in conditions.
  ```kotlin
  val showFab by remember(scrollState) {
      derivedStateOf { scrollState.firstVisibleItemIndex == 0 }
  }
  ```
- Avoid reading a `MutableState.value` in a Composable **body** unless you want that Composable to recompose on every change. Push reads down into leaf Composables that actually render the value.
- **`LaunchedEffect(key) { … }`** — restarts the coroutine when `key` changes. If `key = Unit`, the effect runs once for the composition lifetime. If `key = someState.value`, every state change relaunches.

## Modifier performance

- `Modifier.composed { … }` allocates per recomposition — replace with `Modifier.Node` (Compose 1.7+):
  ```kotlin
  class MyModifierNode : Modifier.Node(), LayoutModifierNode { … }
  class MyElement : ModifierNodeElement<MyModifierNode>() {
      override fun create() = MyModifierNode()
      override fun update(node: MyModifierNode) { /* update in-place */ }
  }
  fun Modifier.my() = this then MyElement()
  ```
- Chain order matters: `Modifier.padding(8.dp).size(100.dp)` differs from `size(100.dp).padding(8.dp)`. Common bug source.
- `Modifier.background()` before `Modifier.padding()` — background extends beyond padding; usually not the intent.

## Lists (`LazyColumn`, `LazyRow`, `LazyVerticalGrid`)

- **Provide stable, comparable `key`s**:
  ```kotlin
  LazyColumn {
      items(feed, key = { it.id }) { row -> Row(row) }
  }
  ```
- Instability example: `key = { it.hashCode() }` — collisions and misidentification cause recomposition + animation glitches.
- `contentType` optimizes reuse for heterogeneous lists:
  ```kotlin
  items(feed, key = { it.id }, contentType = { it::class }) { … }
  ```
- Avoid capturing unstable values in the item lambda. Pull them into `remember { … }` inside the item, or make the row a stable composable that takes only stable params.

## First frame / TTFD

- Use `ReportDrawn` / `ReportDrawnWhen`:
  ```kotlin
  ComposeContentActivity {
      val ready by feedViewModel.ready.collectAsStateWithLifecycle()
      ReportDrawnWhen { ready }
      FeedScreen()
  }
  ```
  Signals to `ActivityManager` that the screen is fully drawn — reflected in `am_activity_launch_time` and `Time to Full Display` metrics.
- `Modifier.drawWithCache { }` caches expensive draw operations (gradients, path computation) across frames.

## Anti-patterns

- Passing large lambdas capturing unstable state to a `@Composable` — even with strong skipping, the parameter identity may not match. Hoist state or use `remember { }` with correct keys.
- `ViewModel` state consumed as `collectAsState` (non-lifecycle-aware) — recomposes even when the screen is off. Use `collectAsStateWithLifecycle`.
- Deeply nested `Column`/`Row` for layout that should be `ConstraintLayout` or `Layout { }` — measure passes multiply.
- Every `@Composable` reads `LocalConfiguration.current` unconditionally — every orientation change recomposes the whole tree. Read once in a container.
- `Text(state.value.count.toString())` where `state.value` is a large object — full object read; extract just the primitive.
