# Instrumented and End-to-End Testing

Load when a test must run on a real device or emulator: Room migrations, `WorkManager`, biometric, notifications, cross-app IPC via UI Automator.

## When to go on-device

- **Real SQLite** behavior (Room migrations, FTS, triggers) — Robolectric's SQLite is close but not identical; migration tests must run on device.
- **`WorkManager`** — has instrumented test harness (`WorkManagerTestInitHelper`); local `Robolectric` fakes exist but lag features.
- **Biometric, camera, notifications, IME insets, edge-to-edge with system bars.**
- **Cross-app flows** (share sheet, permission dialogs, notification shade) via UI Automator.
- **Release-candidate journeys** across the app.

Everything else stays in `src/test/` under Robolectric.

## androidTest sourceset baseline

```kotlin
dependencies {
    androidTestImplementation("androidx.test:runner")
    androidTestImplementation("androidx.test:rules")
    androidTestImplementation("androidx.test.ext:junit")
    androidTestImplementation("androidx.test.espresso:espresso-core")
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
    androidTestImplementation("androidx.test.uiautomator:uiautomator")
    androidTestImplementation("androidx.room:room-testing")
    androidTestImplementation("androidx.work:work-testing")
}
```

## Room migration tests

Reproduce prior schemas and step migrations:

```kotlin
@RunWith(AndroidJUnit4::class)
class MigrationTest {
    private val DB = "test.db"

    @get:Rule val helper = MigrationTestHelper(
        InstrumentationRegistry.getInstrumentation(),
        AppDb::class.java,
        listOf(AppDb.Migration1_2, AppDb.Migration2_3),
    )

    @Test fun migrate1To2() {
        helper.createDatabase(DB, 1).apply {
            execSQL("INSERT INTO user (id, name) VALUES (1, 'a')")
            close()
        }
        val db = helper.runMigrationsAndValidate(DB, 2, true, AppDb.Migration1_2)
        db.query("SELECT name FROM user WHERE id=1").use {
            assertTrue(it.moveToFirst())
            assertEquals("a", it.getString(0))
        }
    }

    @Test fun migrateAll() {
        helper.createDatabase(DB, 1).close()
        Room.databaseBuilder(context, AppDb::class.java, DB)
            .addMigrations(AppDb.Migration1_2, AppDb.Migration2_3)
            .build().openHelper.writableDatabase.close()
    }
}
```

Rules:

- Schema JSONs must be exported (`room.schemaLocation` in `ksp {}` args) and committed. `MigrationTestHelper` reads them.
- Test each migration with representative data. A migration that "compiles" can silently drop columns.
- Add one "run all migrations" smoke test.

## Room instrumented DAO tests

```kotlin
@RunWith(AndroidJUnit4::class)
class UserDaoTest {
    private lateinit var db: AppDb
    private lateinit var dao: UserDao

    @Before fun setup() {
        val ctx = ApplicationProvider.getApplicationContext<Context>()
        db = Room.inMemoryDatabaseBuilder(ctx, AppDb::class.java).build()
        dao = db.userDao()
    }
    @After fun tearDown() { db.close() }

    @Test fun insertAndQuery() = runTest {
        dao.insert(User(1, "a"))
        assertEquals(User(1, "a"), dao.findById(1))
    }
}
```

- `inMemoryDatabaseBuilder` avoids leaking a file across tests.
- Do not use `allowMainThreadQueries()` unless you specifically need it; it hides accidental main-thread DAO calls.

## WorkManager tests

```kotlin
@Before fun initWorkManager() {
    val config = Configuration.Builder()
        .setMinimumLoggingLevel(Log.DEBUG)
        .setExecutor(SynchronousExecutor())
        .build()
    WorkManagerTestInitHelper.initializeTestWorkManager(context, config)
}

@Test fun runs() = runTest {
    val request = OneTimeWorkRequestBuilder<MyWorker>().build()
    val wm = WorkManager.getInstance(context)
    wm.enqueue(request).result.get()
    WorkManagerTestInitHelper.getTestDriver(context)!!.setAllConstraintsMet(request.id)
    val info = wm.getWorkInfoById(request.id).get()
    assertEquals(WorkInfo.State.SUCCEEDED, info.state)
}
```

- `TestDriver` lets you satisfy delays, initial delays, and constraints on demand — never wait for real network/battery state.
- Foreground work: use `TestListenableWorkerBuilder` for direct unit-style execution without WorkManager scheduling.

## UI Automator

For cross-app flows (system settings, notification shade, share sheet):

```kotlin
val device = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation())
device.pressHome()
device.openNotification()
device.wait(Until.hasObject(By.text("My notification")), 5_000)
device.findObject(UiSelector().text("My notification")).click()
```

- Selectors are resource-ID-based (`By.res("com.android.systemui:id/notification_stack_scroller")`) or text-based.
- Prefer text/content-desc selectors; resource IDs vary across OEMs and Android versions.
- `SIGTERM`s and screen-off events between tests break selectors — start each test from a known home state.

## Espresso (for legacy XML)

```kotlin
onView(withId(R.id.email)).perform(typeText("a@b.c"), closeSoftKeyboard())
onView(withId(R.id.submit)).perform(click())
onView(withText(R.string.welcome)).check(matches(isDisplayed()))
```

- Espresso auto-waits for the UI thread and known idling resources (`RecyclerView`, `Loader`). Custom async work needs a custom `IdlingResource`.
- `IntentSubject` / `Intents.intended(hasComponent(...))` validates started intents (`Intents.init()` in `@Before`, `Intents.release()` in `@After`).

## Test orchestrator

For clean per-test process state:

```kotlin
android {
    defaultConfig {
        testInstrumentationRunnerArguments["clearPackageData"] = "true"
    }
    testOptions.execution = "ANDROIDX_TEST_ORCHESTRATOR"
}
dependencies {
    androidTestUtil("androidx.test:orchestrator")
}
```

Runs each `@Test` in its own instrumentation process — expensive but eliminates static state carry-over.

## Gradle-managed devices (CI)

Recommended for CI over ad-hoc emulators:

```kotlin
android {
    testOptions {
        managedDevices.localDevices {
            create("pixel8api34") {
                device = "Pixel 8"
                apiLevel = 34
                systemImageSource = "aosp-atd"
            }
        }
    }
}
```

Then `./gradlew pixel8api34DebugAndroidTest`. AGP provisions, boots, runs, and destroys the AVD. `aosp-atd` (Automated Test Device) is minimal and boots faster than a full system image.

## End-to-end journey design

- One journey per critical flow (login, purchase, primary content view). Aim for roughly 5% of total test count.
- Prefer Compose Test / Espresso for in-app steps; hand off to UI Automator only for cross-app boundaries.
- Use Test Orchestrator + `clearPackageData` between journeys to avoid state leaks.
- Fail loudly on flakes — a single retry masks real issues. Investigate every intermittent failure before adding `@RetryRule` or `@FlakyTest`.

## Common flake sources on device

- Animation state (system animations enabled). Disable in the device: `settings put global window_animation_scale 0`; do the same for `transition_animation_scale` and `animator_duration_scale`. `GrantPermissionRule.grant(...)` cannot handle this; use a Gradle `deviceProvisioning` script or ADB pre-step.
- Real IME → intermittent focus. Use `Espresso.closeSoftKeyboard()` or `UiDevice.pressBack()` deterministically.
- Cold-start network calls hitting real endpoints. Use `MockWebServer` (`okhttp3.mockwebserver:mockwebserver`) with a base URL injected via DI.
- Notifications from other apps polluting UI Automator. Run tests in airplane mode + do-not-disturb.
- Different display densities across CI shards. Pin one device profile for a stable baseline.
