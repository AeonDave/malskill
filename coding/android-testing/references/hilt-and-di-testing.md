# Hilt and DI Testing

Load when setting up test dependency injection for Hilt, Koin, or plain manual DI. Covers custom test runner, binding replacement, and Compose interop.

## Hilt

### Custom test runner

Required so tests use `HiltTestApplication` instead of your production `Application`.

```kotlin
// src/androidTest/java/com/example/HiltTestRunner.kt
class HiltTestRunner : AndroidJUnitRunner() {
    override fun newApplication(cl: ClassLoader?, name: String?, ctx: Context?): Application =
        super.newApplication(cl, HiltTestApplication::class.java.name, ctx)
}
```

Wire it in `build.gradle.kts`:

```kotlin
android {
    defaultConfig {
        testInstrumentationRunner = "com.example.HiltTestRunner"
    }
}
```

Add Hilt test deps:

```kotlin
androidTestImplementation("com.google.dagger:hilt-android-testing:<version>")
kspAndroidTest("com.google.dagger:hilt-android-compiler:<version>")
// For local tests as well:
testImplementation("com.google.dagger:hilt-android-testing:<version>")
kspTest("com.google.dagger:hilt-android-compiler:<version>")
```

Robolectric-hosted local Hilt tests need an application override too — add `@HiltAndroidTest` + `@Config(application = HiltTestApplication::class)`.

### Test class shape

```kotlin
@HiltAndroidTest
@Config(application = HiltTestApplication::class)   // for Robolectric
class FeedRepositoryTest {
    @get:Rule(order = 0) val hilt = HiltAndroidRule(this)
    @get:Rule(order = 1) val main = MainDispatcherRule()

    @Inject lateinit var repo: FeedRepository

    @Before fun setup() { hilt.inject() }

    @Test fun x() = runTest { … }
}
```

Rule order matters: `HiltAndroidRule` must come first. If you use a Compose rule, it comes after `HiltAndroidRule`.

### Replacing a binding

Two options:

**`@BindValue`** — per-test override:

```kotlin
@BindValue
@JvmField
val fakeApi: Api = FakeApi()
```

Simple, no module changes, only visible to this test class. Prefer for one-off fakes.

**`@TestInstallIn`** — module-wide override:

```kotlin
@Module
@TestInstallIn(components = [SingletonComponent::class], replaces = [ApiModule::class])
object FakeApiModule {
    @Provides @Singleton fun api(): Api = FakeApi()
}
```

Applies to every test in the sourceset. Use for cross-test replacements (fake network, fake DataStore).

### Test-only components

`@InstallIn(TestComponent::class)` isolates bindings to tests. Rarely needed — most test overrides use `SingletonComponent`.

### Hilt + Compose

- If the composable uses `hiltViewModel()`, the test Activity must be `@AndroidEntryPoint`.
- `androidx.compose.ui:ui-test-manifest` provides a generic Activity that is **not** `@AndroidEntryPoint`. Provide your own:

```kotlin
@AndroidEntryPoint
class TestActivity : ComponentActivity()
```

Declare in the test manifest (`src/androidTest/AndroidManifest.xml` or `src/test/AndroidManifest.xml`), then `createAndroidComposeRule<TestActivity>()`.

### Fragments and Hilt

- `launchFragmentInHiltContainer` (from `androidx.fragment:fragment-testing`) is not Hilt-aware. Use `launchFragmentInContainer` inside a Hilt test Activity you declare yourself, or the community `HiltExt` pattern.

### Common failure modes

- `NoClassDefFoundError: HiltTestApplication` → missing `hilt-android-testing` in the correct sourceset (`testImplementation` for JVM, `androidTestImplementation` for device).
- `Test does not have @HiltAndroidTest` or `inject() not called` → forgot `hilt.inject()` in `@Before`.
- `MultipleInstallInFoundException` → two `@TestInstallIn` modules replacing the same production module; only one may replace a given target.
- ViewModel-scoped fake not replaced → `@BindValue` is scoped to Singleton by default; use `@TestInstallIn` targeting `ViewModelComponent` for VM-scoped bindings.

## Koin

### `KoinTestRule`

```kotlin
@get:Rule
val koin = KoinTestRule.create {
    modules(module {
        single<Api> { FakeApi() }
        viewModel { FeedViewModel(get()) }
    })
}
```

- No custom runner needed; Koin does not tie to `Application` the way Hilt does.
- Reset between tests is automatic when the rule is per-method.
- For multi-module apps: `modules(prodModule, testOverrides)` where `testOverrides` uses `single(override = true) { … }`.

### `KoinTest` interface

Alternative: implement `KoinTest` and use `stopKoin()` in `@After`. The rule is preferred for cleanliness.

## Plain manual DI

Simplest approach: constructor injection. Tests instantiate directly with fakes.

```kotlin
class FeedViewModel(private val repo: FeedRepository) : ViewModel()

@Test fun x() = runTest {
    val vm = FeedViewModel(FakeFeedRepository())
    // …
}
```

Prefer this in library modules with no framework dependency. DI frameworks earn their weight only when the wiring becomes unwieldy.

## Fakes vs mocks

- **Fakes**: in-memory implementations. `class FakeFeedRepository(var items: List<Item> = emptyList()) : FeedRepository { … }`. Reusable across tests, cheap to maintain when the interface changes (Kotlin's compile-time exhaustiveness helps).
- **Mocks**: use only for boundary interfaces you cannot re-implement (retrofit `Service` with 50 methods you don't call). MockK integrates well with coroutines (`coEvery { }`, `coVerify { }`).
- Mocking a class you own with 30 methods is a smell — write a fake instead.

## Testing dispatchers via DI

Provide `CoroutineDispatcher` bindings via qualifiers:

```kotlin
@Module @InstallIn(SingletonComponent::class)
object DispatchersModule {
    @Provides @IoDispatcher fun io(): CoroutineDispatcher = Dispatchers.IO
}

@Module
@TestInstallIn(components = [SingletonComponent::class], replaces = [DispatchersModule::class])
object TestDispatchersModule {
    @Provides @IoDispatcher fun io(): CoroutineDispatcher = StandardTestDispatcher()
}
```

But: the `StandardTestDispatcher` must belong to the same `TestScheduler` your `MainDispatcherRule` uses, otherwise ordering diverges. Prefer manual injection via constructor for coroutine-heavy code — cleaner than DI-swapped dispatchers.
