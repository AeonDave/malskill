---
name: android-testing
description: "Android testing patterns for unit tests, instrumented tests, Compose UI tests, screenshot tests, and end-to-end journeys. Use when setting up JUnit4/JUnit5 + Robolectric, wiring Hilt/Koin for tests, choosing between Espresso and Compose Test APIs, adding Roborazzi/Paparazzi/Dropshots screenshot tests, or diagnosing flaky Android tests."
license: MIT
compatibility: "AGP 8.5+ (guidance covers up to AGP 9.x), Kotlin 2.0+. Baseline: JUnit4, Robolectric 4.13+, AndroidX Test 1.6+, Espresso 3.6+, Compose 1.7+. Optional: Hilt, Koin, Roborazzi, Paparazzi, Dropshots, MockK, Turbine, UI Automator."
metadata:
  author: AeonDave
  version: "1.0"
---

# Android Testing

Test infrastructure and strategy for native Android apps. Pair with `kotlin-patterns` for Kotlin/coroutine idioms and `test-driven-development` when implementing test-first.

## When to activate

- Bootstrapping a testing setup on a new or legacy Android module
- Adding coverage for ViewModels, repositories, Compose screens, or navigation
- Choosing between unit, Robolectric-hosted, or on-device tests
- Introducing screenshot testing (local vs on-device)
- Diagnosing flakes in Espresso/Compose tests or emulator CI runs

---

## Core rules (high signal)

- **Match the existing test stack** — do not silently swap JUnit4 for JUnit5, or Mockito for MockK, in a codebase committed to the other. Migrate deliberately.
- **Push tests down**. Prefer JVM unit tests (`src/test/`) with fakes; use Robolectric only when the code under test genuinely needs Android framework classes; use instrumented tests (`src/androidTest/`) only for on-device concerns (Room migrations, `WorkManager`, biometric, camera, notifications, IME).
- **Coroutines**: inject dispatchers; use `runTest { }` (not `runBlocking`) with `MainDispatcherRule` (or `Dispatchers.setMain(StandardTestDispatcher())` in `@Before`/`@After`).
- **Fakes over mocks** when the collaborator has behavior; mocks only for boundary interfaces you cannot re-implement cheaply. Mocking a DAO with 30 methods is a smell.
- **Compose UI tests run under Robolectric** (`RobolectricTestRunner` + `AndroidJUnit4`) for speed; run on-device only when validating system UI (edge-to-edge, notifications, IME insets, IPC dialogs).
- **Never `Thread.sleep` in a test.** Use `IdlingResource`, `composeTestRule.waitUntil { }`, `advanceTimeBy(...)`, or `Turbine.awaitItem()`.

---

## Setup baseline

If no framework is chosen, install:

- **JUnit4** (`junit:junit`) — still the standard for AndroidX Test/Espresso/Compose; JUnit5 requires the `de.mannodermaus.gradle.plugins.android-junit5` plugin and does not work for instrumented tests.
- **AndroidX Test** (`androidx.test:core`, `androidx.test:runner`, `androidx.test:rules`, `androidx.test.ext:junit`).
- **Robolectric** (`org.robolectric:robolectric`) for JVM-hosted Android tests.
- **Compose Test** (`androidx.compose.ui:ui-test-junit4`, `androidx.compose.ui:ui-test-manifest` in `debugImplementation`).
- **Coroutines test** (`org.jetbrains.kotlinx:kotlinx-coroutines-test`).
- **Turbine** (`app.cash.turbine:turbine`) for `Flow` assertions.
- **MockK** (`io.mockk:mockk`) only if mocking is actually needed; do not preinstall.
- **Jacoco** for coverage (`jacoco` plugin per module).

Optional based on need:

- **Espresso** (`androidx.test.espresso:espresso-core`, `-contrib`, `-intents`) — for XML/View tests.
- **UI Automator** (`androidx.test.uiautomator:uiautomator`) — for cross-app end-to-end.
- Screenshot testing: pick **one** primary local framework:
  - **Roborazzi** (`io.github.takahirom.roborazzi:roborazzi`) — Robolectric-based, cross-platform PNG diff, fast.
  - **Paparazzi** (`app.cash.paparazzi:paparazzi`) — LayoutLib-based, no Robolectric, no emulator.
  - **Compose Preview Screenshot Testing** (AGP 8.5+ experimental) — renders `@Preview` composables to PNG via Gradle task.
  - **Dropshots** (`com.dropbox.dropshots:dropshots`) — on-device screenshots for scenarios that require real system UI.

Add the AndroidX test instrumentation runner to the module `build.gradle.kts`:

```kotlin
android {
    defaultConfig {
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        // With Hilt: "com.example.HiltTestRunner"
    }
    testOptions {
        unitTests.isIncludeAndroidResources = true   // required for Robolectric to read res/
        unitTests.isReturnDefaultValues = true       // avoid throwing on unmocked Android calls in pure JVM tests
    }
}
```

---

## Test placement

| Sourceset | Runs on | Use for |
|-----------|---------|---------|
| `src/test/` | JVM (host) | Pure Kotlin logic, ViewModels with fake repositories, coroutines with `runTest`, Robolectric-hosted UI tests, local screenshot tests |
| `src/androidTest/` | Device / emulator | Room DB (real SQLite), `WorkManager`, biometric, camera, notifications, IME insets, edge-to-edge, cross-app IPC (`UI Automator`) |
| `src/testFixtures/` | Both | Shared test doubles (fakes, factories) usable from `test` and `androidTest` |

- Do not place Espresso or Compose UI tests in `androidTest/` by default — run them under Robolectric in `test/` for speed unless a real device concern is being validated.

---

## Coroutine test pattern

```kotlin
class MainDispatcherRule(
    private val dispatcher: TestDispatcher = StandardTestDispatcher(),
) : TestWatcher() {
    override fun starting(d: Description) = Dispatchers.setMain(dispatcher)
    override fun finished(d: Description) = Dispatchers.resetMain()
}

class FeedViewModelTest {
    @get:Rule val main = MainDispatcherRule()

    @Test fun loads() = runTest {
        val vm = FeedViewModel(FakeRepo(items = listOf(Item("a"))))
        vm.refresh()
        advanceUntilIdle()
        assertEquals(UiState.Loaded(listOf(Item("a"))), vm.state.value)
    }
}
```

Rules:

- Inject dispatchers (never call `Dispatchers.IO` directly in production code you want to test).
- Use `advanceUntilIdle()`, `advanceTimeBy(ms)`, or `runCurrent()` — never `Thread.sleep`.
- Turbine for `Flow` assertions:
  ```kotlin
  vm.state.test {
      assertEquals(UiState.Loading, awaitItem())
      vm.refresh()
      assertEquals(UiState.Loaded(...), awaitItem())
  }
  ```

---

## Compose UI tests

```kotlin
@RunWith(AndroidJUnit4::class)     // Robolectric-hosted when in src/test/
class FeedScreenTest {
    @get:Rule val compose = createAndroidComposeRule<ComponentActivity>()

    @Test fun rendersItems() {
        compose.setContent { MyTheme { FeedScreen(state = loaded(listOf("a"))) } }
        compose.onNodeWithText("a").assertIsDisplayed()
        compose.onNodeWithTag("refresh").performClick()
        compose.waitUntil { compose.onAllNodesWithTag("row").fetchSemanticsNodes().size >= 2 }
    }
}
```

Matcher order: semantic first (`onNodeWithText`, `onNodeWithContentDescription`, `hasSetTextAction()`). Fall back to `testTag("…")` only when three or more semantic matchers would be needed.

State restoration is a common regression source. Wrap the composable in a `StateRestorationTester(compose)` and call `emulateSavedInstanceStateRestore()` in tests for screens with saved state.

---

## Espresso (View-based)

- Base matchers: `onView(withId(R.id.…))`, `onView(withText("…"))`.
- Actions: `perform(click(), typeText(), scrollTo())`.
- Assertions: `check(matches(isDisplayed()))`.
- Idling: register a custom `IdlingResource` for background work; do not `Thread.sleep`.

Only load Espresso when the module still has XML views; do not use it in Compose-only modules.

---

## Screenshot tests

Local (fast) shape:

- **Screen-level**: 9-cell grid — widths `{400, 610, 900}` dp × heights `{400, 500, 1000}` dp. One PNG per cell per screen. Add extra shots for alt themes and font scale `1.5`.
- **Component-level**: theme × font-scale matrix per public composable.

Roborazzi example (JVM/Robolectric):

```kotlin
@RunWith(AndroidJUnit4::class)
class ProfileScreenshotTest {
    @get:Rule val compose = createAndroidComposeRule<ComponentActivity>()

    @Test fun light() {
        compose.setContent { MyTheme(dark = false) { ProfileScreen(sampleUser) } }
        compose.onRoot().captureRoboImage("build/reports/screenshots/profile_light.png")
    }
}
```

- Reference PNGs go under `src/test/screenshots/` (Roborazzi) or `src/test/snapshots/` (Paparazzi). Commit them; a repo without stored baselines cannot regress.
- On-device screenshot tests (Dropshots) only for real-system scenarios (edge-to-edge with system bars, IME rendering, notification shade, PiP).

---

## Room and databases

- Instrumented tests: use in-memory Room to avoid file pollution:
  ```kotlin
  Room.inMemoryDatabaseBuilder(context, AppDb::class.java)
      .allowMainThreadQueries()     // tests only
      .build()
  ```
- Migrations: `MigrationTestHelper` reproduces prior schemas; verify each migration and add a bulk test that runs all migrations end-to-end.

---

## Dependency injection for tests

- **Hilt**: `@HiltAndroidTest` on the class, `@get:Rule val hilt = HiltAndroidRule(this)`. Use a custom `HiltTestRunner` extending `AndroidJUnitRunner` that returns `HiltTestApplication`.
- Replace bindings per test with `@BindValue` (single-test) or `@Module @TestInstallIn(...)` (per module).
- **Koin**: `KoinTestRule` with an override `module { single<Repo> { FakeRepo() } }`.

Do not add production seams solely for tests; use DI to inject fakes.

---

## Navigation tests

- Compose Navigation: use `TestNavHostController` (Compose) — set the graph, drive the ViewModel, assert on `navController.currentBackStackEntry?.destination?.route`.
- Test back handling, deep links, and multi-back-stack "exit through home" flows separately.

---

## End-to-end (release-candidate) tests

- Keep the count small (roughly 5% of total tests). One journey per critical flow.
- Use Compose Test / Espresso for in-app; hand off to UI Automator for cross-app (notification panel, share sheet, system settings).
- Prefer running on a real device profile in CI (Firebase Test Lab, Gradle-managed devices) over headless emulator for these.

---

## Quick review checklist

- No `runBlocking`; every coroutine test uses `runTest` with a `MainDispatcherRule`
- No `Thread.sleep`; every wait uses `advanceTimeBy`, `waitUntil`, `IdlingResource`, or Turbine
- Espresso tests do not exist in Compose-only modules
- Compose UI tests use semantic matchers first, `testTag` only when needed
- Screenshot references are committed; baselines exist for every added test
- Room instrumented tests use in-memory DB; migrations have explicit tests
- Hilt tests use `HiltTestApplication` via a custom runner; `@BindValue` swaps are scoped
- CI runs `-race`-equivalent invariants: `./gradlew test` and `connectedDebugAndroidTest` (or Gradle-managed device tasks) both green

---

## Common flake sources

- Real `Dispatchers.IO` / `Dispatchers.Default` used inside code under test → intermittent ordering. Fix: inject dispatchers.
- Global mutable state (companion object caches, `object` singletons) across tests → order-dependent failures. Fix: reset in `@After` or scope to DI.
- `SharedFlow` / `Channel` consumed via `first()` when no emission is guaranteed → hang. Fix: Turbine with a timeout.
- Espresso `IdlingResource` not unregistered → next test hangs waiting on stale registry. Fix: register/unregister via `@Rule`.
- Screenshot diffs on different host OS (font rendering differs between Linux CI and macOS/Windows dev). Fix: standardize on Linux for baselines; use Docker if needed.
- Robolectric SDK level mismatch between test and app → resource lookups fail. Set `@Config(sdk = [34])` or configure globally in `robolectric.properties`.

---

## Resources

Load on demand:

- [references/coroutine-and-flow-testing.md](references/coroutine-and-flow-testing.md) — `runTest`, virtual time, dispatcher injection, Turbine patterns, cancellation testing; load when writing suspend/Flow tests
- [references/compose-ui-testing.md](references/compose-ui-testing.md) — semantic matchers, `waitUntil`, `StateRestorationTester`, gesture testing, hilt-in-compose tests; load when writing Compose tests
- [references/screenshot-testing.md](references/screenshot-testing.md) — framework comparison (Roborazzi, Paparazzi, Compose Preview Screenshot, Dropshots), matrix design, baseline hygiene; load when adding or fixing screenshot coverage
- [references/hilt-and-di-testing.md](references/hilt-and-di-testing.md) — `HiltTestApplication`, custom runner, `@BindValue`/`@TestInstallIn`, Koin `KoinTestRule`; load when setting up DI-aware tests
- [references/instrumented-and-e2e.md](references/instrumented-and-e2e.md) — androidTest sourceset, in-memory Room, `MigrationTestHelper`, `WorkManager` testing, UI Automator for cross-app flows; load when a test must run on a device or emulator
