# Screenshot Testing

Load when adding, migrating, or fixing screenshot coverage. Guides framework choice, matrix design, and baseline hygiene.

## Framework choice

| Framework | Runs on | Renders via | Notes |
|-----------|---------|-------------|-------|
| **Roborazzi** | JVM (Robolectric) | Robolectric graphics + `captureRoboImage` | Fast, works with existing Compose/Espresso tests. Diff PNGs on disk. Recommended primary. |
| **Paparazzi** | JVM (no Robolectric) | Android LayoutLib | Faster than Robolectric but incompatible with Robolectric-hosted tests; can't run Compose+Robolectric mixed. Older Compose support caveats. |
| **Compose Preview Screenshot Testing** | JVM (AGP task) | Compose renderer | AGP 8.5+ experimental. Renders every `@Preview` to PNG via `./gradlew validateReleaseScreenshotTest`. Zero test code required. |
| **Dropshots** | Device / emulator | Real Android rendering | For real-system scenarios (edge-to-edge with system bars, IME, notification shade, PiP). Slow, needs device. |

Pick **one** primary local framework per module. Add Dropshots on top only for scenarios that require the real system UI. Do not run Roborazzi and Paparazzi in the same module — their setup conflicts.

## Baseline hygiene

- Reference PNGs live under `src/test/screenshots/` (Roborazzi), `src/test/snapshots/` (Paparazzi), or the framework-specific directory.
- **Commit baselines to the repo.** A repo without stored baselines cannot regress.
- Store framework version and rendering settings in `AGENTS.md`/`docs/testing.md` — updating Compose UI or LayoutLib can shift pixels.
- Diff tolerance: keep it strict (0 or 1-pixel default). Non-zero tolerance silently accepts real regressions.

## Rendering determinism

Screenshot diffs must be byte-stable across runs. Sources of noise:

- **Fonts**: baseline OS font metrics differ between Linux CI, macOS, Windows dev machines. **Standardize CI on Linux**; do not commit baselines produced on macOS/Windows dev boxes.
- **GPU vs CPU rendering**: Robolectric uses CPU. Do not mix baselines from device (Dropshots) with local frameworks.
- **Animation state**: freeze animations. Set `compose.mainClock.autoAdvance = false` and advance to a stable frame before capture; disable indeterminate progress and shimmer effects with a test flag.
- **Time-based rendering**: relative timestamps ("2 min ago") render differently. Inject a `FakeClock` or pass fixed timestamps.
- **RNG-based visuals**: seed any randomness (avatar colors, backgrounds).
- **Locale / RTL**: capture explicitly for RTL if the UI has RTL variants; do not rely on default locale.

## Matrix design

### Screen-level (per screen)

Baseline 9 shots: widths `{400, 610, 900}` dp × heights `{400, 500, 1000}` dp.

Extra shots on the compact-mobile size (400 × 500):

- Alternate themes (dark/light, high-contrast if you ship one).
- Font scale `1.5` (accessibility).
- RTL locale if supported.
- Loading / empty / error states (inject via fake state).

### Component-level (per public composable)

Theme × font-scale matrix. Skip if the component has no theme-varying visual (text-only labels).

## Roborazzi baseline test

```kotlin
@RunWith(AndroidJUnit4::class)
@Config(sdk = [34])
class ProfileScreenshotTest {
    @get:Rule val compose = createAndroidComposeRule<ComponentActivity>()

    @Test fun light_compact() = capture("profile_light_compact", dark = false, size = DpSize(400.dp, 500.dp))
    @Test fun dark_compact()  = capture("profile_dark_compact",  dark = true,  size = DpSize(400.dp, 500.dp))
    @Test fun light_wide()    = capture("profile_light_wide",    dark = false, size = DpSize(900.dp, 1000.dp))

    private fun capture(name: String, dark: Boolean, size: DpSize) {
        compose.setContent {
            DeviceConfigurationOverride(DeviceConfigurationOverride.ForcedSize(size)) {
                MyTheme(dark = dark) { ProfileScreen(sampleUser) }
            }
        }
        compose.onRoot().captureRoboImage("src/test/screenshots/$name.png")
    }
}
```

## Compose Preview Screenshot Testing (AGP experimental)

- Enable in `gradle.properties`:
  ```
  android.experimental.enableScreenshotTest=true
  ```
- Enable in module:
  ```kotlin
  android {
      experimentalProperties["android.experimental.enableScreenshotTest"] = true
  }
  ```
- Every `@Preview` in `src/screenshotTest/` becomes a snapshot. Run `./gradlew :module:validateDebugScreenshotTest`; baseline via `./gradlew :module:updateDebugScreenshotTest`.
- Best for design-system component libraries: any new `@Preview` is auto-covered without writing test code.

## Dropshots (on-device)

- Add plugin `com.dropbox.dropshots` and JUnit rule `@get:Rule val dropshots = Dropshots()`.
- Assertion: `dropshots.assertSnapshot(activity, name = "profile_edge_to_edge")`.
- Baselines stored under `src/androidTest/screenshots/`. Different from local frameworks — do not conflate directories.
- Use only for scenarios that need real system UI. A full Dropshots-only suite is slow and expensive in CI.

## Handling updates

- Any UI change updates a screenshot. Review the diff PNG (frameworks produce a `_diff.png` alongside) — do not blindly regenerate baselines.
- Golden-update commands:
  - Roborazzi: `./gradlew recordRoborazziDebug`.
  - Paparazzi: `./gradlew recordPaparazziDebug`.
  - Compose Preview Screenshot: `./gradlew updateDebugScreenshotTest`.
- Update baselines in a separate PR when the change spans many screens; makes review tractable.

## CI integration

- Screenshot artifacts (diff PNGs) must be uploaded on failure — otherwise a red build is undiagnosable.
- Cache the framework's rendering cache (Robolectric JAR, Paparazzi native libs) between runs to reduce cold-start cost.
- Fail the build on any pixel diff — non-zero tolerance is a slow drift into no-coverage.

## Anti-patterns

- Non-zero pixel tolerance ("only 200 pixels different") → accepts real regressions.
- Recording baselines on a dev machine and committing to a CI that renders differently → perma-red or perma-updated baselines.
- Screenshotting scrollable content without deterministic scroll position.
- Testing behavior via screenshot ("clicking should highlight"). Use behavior tests for behavior; screenshots for visuals.
- Skipping baselines under `.gitignore` "to save space" → coverage is meaningless.
