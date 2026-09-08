# Compose UI Testing

Load when writing or fixing Compose UI tests, choosing between Robolectric-hosted and instrumented runs, or building semantic matchers.

## Baseline setup

Dependencies (module `build.gradle.kts`):

```kotlin
dependencies {
    testImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-test-manifest")   // provides an empty Activity for the test host
    testImplementation("org.robolectric:robolectric")
    testImplementation("androidx.test:runner")
    testImplementation("androidx.test.ext:junit")
}

android {
    testOptions {
        unitTests.isIncludeAndroidResources = true
    }
}
```

Rule choice:

- `createComposeRule()` — pure composable test, no Activity.
- `createAndroidComposeRule<ComponentActivity>()` — needed for `context`, resources, `LocalContext.current` reads, state restoration.

## Robolectric vs on-device

Run Compose tests **in `src/test/`** under Robolectric by default: fast, no emulator. Move to `src/androidTest/` only for:

- Real system UI (edge-to-edge, IME insets, notification shade)
- IPC dialogs (share sheet, permission requests)
- Hardware-backed operations (biometric, camera preview)
- WebView content rendering fidelity

For Robolectric-hosted Compose tests, annotate:

```kotlin
@RunWith(AndroidJUnit4::class)
@Config(sdk = [34])
class FeedScreenTest {
    @get:Rule val compose = createAndroidComposeRule<ComponentActivity>()
    // …
}
```

## Semantic matchers (matcher priority)

Order:

1. **Semantic role/action**: `onNodeWithText("Login")`, `onNodeWithContentDescription("Profile picture")`, `onNode(hasClickAction() and hasText("Save"))`.
2. **Merged tree** for user-visible content: `onNodeWithText("Item 1", useUnmergedTree = false)` (default).
3. **Unmerged tree** when a child is not surfaced in a parent's semantic: `useUnmergedTree = true`.
4. **`testTag`** as last resort — mark the composable with `Modifier.testTag("save-btn")`, match with `onNodeWithTag("save-btn")`.

Rule of thumb: if you need three or more chained matchers, add a `testTag` — it will be easier to maintain than fragile semantic queries.

## Actions

```kotlin
compose.onNodeWithTag("email").performTextInput("a@b.c")
compose.onNodeWithText("Submit").performClick()
compose.onNodeWithTag("list").performScrollToIndex(20)
compose.onNodeWithTag("item-5").performTouchInput { longClick() }
```

Do not chain `assert`/`perform` on the same node reference across a state change — recomposition invalidates. Re-query.

## Waiting

```kotlin
compose.waitUntil(timeoutMillis = 2_000) {
    compose.onAllNodesWithTag("row").fetchSemanticsNodes().isNotEmpty()
}
```

- `waitForIdle()` — flushes pending recompositions and animations.
- `waitUntil { }` — polls the condition; use when a `Flow` collection or coroutine drives visibility.
- Never `Thread.sleep`. `mainClock.autoAdvance = false` + `mainClock.advanceTimeBy(ms)` for animation-driven UI where you need precise frame control.

## Animation and clock control

Compose runs its own `mainClock`. Disable auto-advance to step frames:

```kotlin
compose.mainClock.autoAdvance = false
compose.setContent { FadeInBanner() }
compose.mainClock.advanceTimeBy(150)   // one frame
compose.onNodeWithText("Hi").assertExists()
```

## Coroutines inside composables

- `LaunchedEffect { }` bodies run on `Dispatchers.Main.immediate`. With `MainDispatcherRule + StandardTestDispatcher`, you need `advanceUntilIdle()` before assertions.
- `rememberCoroutineScope()`-launched work is bound to composition; leaving the composition cancels it.

## State restoration

```kotlin
val restore = StateRestorationTester(compose)
restore.setContent { FeedScreen(vm) }
compose.onNodeWithTag("expand").performClick()
restore.emulateSavedInstanceStateRestore()
compose.onNodeWithTag("expanded").assertExists()   // survives restore?
```

Every screen with `rememberSaveable` or a `SavedStateHandle`-backed VM should have at least one restoration test.

## Device configuration overrides

Test different window sizes and font scales without instrumented tests:

```kotlin
compose.setContent {
    DeviceConfigurationOverride(DeviceConfigurationOverride.ForcedSize(DpSize(400.dp, 500.dp))) {
        DeviceConfigurationOverride(DeviceConfigurationOverride.FontScale(1.5f)) {
            FeedScreen(state)
        }
    }
}
```

Also drive `LocalConfiguration`/`LocalDensity`/`LocalLayoutDirection` directly when needed.

## Hilt in Compose tests

- Custom test runner (`HiltTestRunner`) returning `HiltTestApplication`.
- `@HiltAndroidTest` on the test class, `HiltAndroidRule(this)` first, `createAndroidComposeRule` second, `hilt.inject()` in `@Before`.
- `hiltViewModel()` in composables works if the test Activity is `@AndroidEntryPoint`. `ui-test-manifest` provides a generic Activity — use a custom `@AndroidEntryPoint TestActivity` for Hilt-VM composables.

## Preview-driven tests

- Any `@Preview` composable is testable as a plain composable. Do not put behavior tests in `@Preview` bodies; use them as reusable state fixtures:

```kotlin
@Preview @Composable
private fun FeedLoadedPreview() = FeedContent(sampleLoaded)

@Test fun loaded() {
    compose.setContent { FeedLoadedPreview() }
    compose.onNodeWithText("Item 1").assertIsDisplayed()
}
```

## Assertions catalog

| Intent | API |
|--------|-----|
| Exists in tree | `.assertExists()` |
| Visible on screen | `.assertIsDisplayed()` |
| Clickable | `.assert(hasClickAction())` |
| Text equals | `.assertTextEquals("Login")` |
| Text contains | `.assert(hasText("prefix", substring = true))` |
| Selected/checked | `.assertIsSelected()` / `.assertIsOn()` |
| Enabled/disabled | `.assertIsEnabled()` / `.assertIsNotEnabled()` |
| Count | `.assertCountEquals(3)` |

## Debugging failing matches

```kotlin
compose.onRoot(useUnmergedTree = true).printToLog("test")
```

Prints the semantic tree to logcat. Robolectric captures it in test output. When a matcher fails, print the tree first before adding `testTag`s.

## Common footguns

- `onNodeWithText` matches the merged tree; child text inside a merged parent may not appear as its own node. Use `useUnmergedTree = true`.
- Modal dialogs, popup menus, and `PopupProperties(focusable = true)` create separate windows. Query with `onNode(isDialog())` or explicit tags in the popup.
- `LazyColumn` items outside the viewport don't exist in semantics. `performScrollToNode(...)` first.
- Compose test rule does NOT reset `LocalConfiguration` between tests — use `DeviceConfigurationOverride` scoped inside `setContent`, not module-level state.
