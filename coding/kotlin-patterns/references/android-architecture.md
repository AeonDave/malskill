# Android Architecture Patterns

Load when scaffolding a feature module, reviewing lifecycle/leak bugs, or choosing between fragment/activity/compose-nav shapes for UI state and side effects.

## Layered shape (minimum viable)

```
UI (Compose or View) ──► ViewModel ──► Repository ──► Data source (DAO / Retrofit / DataStore)
                                                       └──► Mapper (DTO → Domain)
```

- **UI** collects `StateFlow<UiState>`; emits events (`onClick`, `onSubmit`) into the ViewModel.
- **ViewModel** owns `UiState`, exposes it as `StateFlow`, and translates domain results into UI state. No `Context`, no `View`, no navigation calls.
- **Repository** exposes `suspend` one-shots and cold `Flow` streams. Chooses cache-vs-network, deduplicates, converts DTO → domain models. No `Context`.
- **Data sources** are boring wrappers over Retrofit/Room/DataStore. Return DTOs or entities.

## UI state contract

```kotlin
sealed interface UiState {
    data object Loading : UiState
    data class Loaded(val items: List<Item>, val refreshing: Boolean = false) : UiState
    data class Error(val message: String, val retryable: Boolean) : UiState
}

class FeedViewModel @Inject constructor(
    private val repo: FeedRepository,
) : ViewModel() {
    private val _state = MutableStateFlow<UiState>(UiState.Loading)
    val state: StateFlow<UiState> = _state.asStateFlow()

    fun refresh() = viewModelScope.launch {
        _state.update { (it as? UiState.Loaded)?.copy(refreshing = true) ?: UiState.Loading }
        when (val r = repo.load()) {
            is Outcome.Success -> _state.value = UiState.Loaded(r.value)
            is Outcome.Error   -> _state.value = UiState.Error(r.describe(), retryable = true)
        }
    }
}
```

- One `UiState` sealed hierarchy per screen. Do not fan out into many independent `StateFlow`s that must stay consistent.
- Use `_state.update { … }` (atomic) instead of `_state.value = …` for reads-then-writes.
- Never expose `MutableStateFlow` externally; expose `StateFlow` (immutable view).

## Side effects vs state

- **State** (persistent between recompositions/config changes): `StateFlow<UiState>`.
- **Events** (one-shot: navigation, snackbars, dialogs): **not** `StateFlow` — a re-collection would fire the event again after rotation.
  - Option A: `Channel<Event>(Channel.BUFFERED).receiveAsFlow()` — consumed once by the UI.
  - Option B: model as part of the state with an explicit "consume" call: `data class UiState(..., val navigateTo: Route? = null)`; UI calls `viewModel.consumeNavigation()` after handling.

## Lifecycle-aware collection

```kotlin
// View / Fragment
lifecycleScope.launch {
    repeatOnLifecycle(Lifecycle.State.STARTED) {
        viewModel.state.collect(::render)
    }
}

// Compose
val state by viewModel.state.collectAsStateWithLifecycle()
```

- `repeatOnLifecycle(STARTED)` cancels collection on `onStop`; re-launches on `onStart`. Without it, upstream work runs while the screen is not visible.
- `collectAsStateWithLifecycle()` (from `androidx.lifecycle:lifecycle-runtime-compose`) is the Compose equivalent; plain `collectAsState()` does not respect lifecycle.
- For events channel: same pattern — `.receiveAsFlow().collect { … }` inside `repeatOnLifecycle`.

## DI shape (Hilt)

- `@HiltAndroidApp` on Application; `@AndroidEntryPoint` on Activity/Fragment/View/Service.
- `@HiltViewModel class FeedViewModel @Inject constructor(...)`. Retrieve with `hiltViewModel()` in Compose or `viewModels()` in Fragment/Activity.
- Modules: prefer `@InstallIn(SingletonComponent::class)` for stateless singletons; `ViewModelComponent` for VM-scoped bindings; `ActivityRetainedComponent` for across-config-change state.
- Provide dispatchers via qualifiers:
  ```kotlin
  @Qualifier annotation class IoDispatcher
  @Module @InstallIn(SingletonComponent::class)
  object DispatchersModule {
      @Provides @IoDispatcher fun io(): CoroutineDispatcher = Dispatchers.IO
  }
  ```
  Inject `@IoDispatcher private val io: CoroutineDispatcher` — trivially swappable for `StandardTestDispatcher` in tests.
- Do not inject `Context` when you mean `Application`. Use `@ApplicationContext context: Context`; never `@ActivityContext` in a ViewModel.

## Repository patterns

- **Cold Flow** default: `fun observeItems(): Flow<List<Item>> = dao.observe().map { it.map(::toDomain) }`.
- **`stateIn`** at the ViewModel boundary to share across UI collectors:
  ```kotlin
  val items: StateFlow<List<Item>> = repo.observeItems()
      .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
  ```
  `WhileSubscribed(5_000)` keeps upstream alive 5s across config changes; `Eagerly` leaks; `Lazily` never stops.
- **Single-flight** deduplication for network-heavy operations:
  ```kotlin
  private val inFlight = ConcurrentHashMap<UserId, Deferred<User>>()
  suspend fun fetch(id: UserId): User = coroutineScope {
      inFlight.getOrPut(id) { async { api.get(id.raw) } }
          .also { it.invokeOnCompletion { inFlight.remove(id) } }
          .await()
  }
  ```

## Navigation

- With Compose Navigation: pass primitive IDs, not objects. Rehydrate the model in the destination's ViewModel via `SavedStateHandle`.
- `SavedStateHandle` is the ViewModel-level state bag: process-death survivable, per-destination.
- Deep links: register in the `NavGraph`; validate arguments before use. Treat all deep-link args as untrusted input.

## Compose state hoisting

- Stateless composables take state + callbacks: `@Composable fun Feed(state: UiState, onRefresh: () -> Unit)`.
- Stateful wrappers hold `remember { … }` or hoist to ViewModel.
- `remember(key) { … }` re-computes when `key` changes. Use for derived local caches.
- `derivedStateOf { … }` for state derived from multiple `State` reads inside `remember`.
- `LaunchedEffect(key) { … }` for side effects tied to composition; cancelled when the composition leaves or `key` changes.
- `DisposableEffect(key) { onDispose { … } }` for callbacks / listeners that need cleanup.
- Never mutate `MutableState` inside a composable's body — only inside effects or event handlers.

## Room usage

- DAO methods: `suspend fun get(id: Long): Entity?` for one-shots; `fun observe(): Flow<List<Entity>>` for streams.
- Never call blocking DAO from the main thread — Room detects and throws `IllegalStateException`.
- Multi-table transactions: `@Transaction suspend fun updateBoth(...)`. Room wraps in a database transaction on the query dispatcher.
- Migrations: write explicit `Migration(from, to)` objects; test them with `MigrationTestHelper`. `fallbackToDestructiveMigration()` deletes user data — never in shipped builds.

## Common leak patterns

- **Long-lived callback holding a View/Activity**: unregister in `onStop`/`onDestroy`; prefer `Flow` collection under `repeatOnLifecycle`.
- **`GlobalScope.launch` in a Fragment**: leaks across recreation. Use `viewLifecycleOwner.lifecycleScope` (Fragment view scope, not Fragment scope, or the reference lives longer than the view).
- **`viewLifecycleOwner` vs Fragment `lifecycleOwner`**: views are recreated on config change while the Fragment persists. Always bind view listeners to `viewLifecycleOwner` in Fragments.
- **Static context references**: `object AppHolder { lateinit var ctx: Context }` — leaks the whole application on process reuse. Never store `Activity` or `View` in top-level objects.
- **`AsyncTask`, `Handler(Looper.getMainLooper())` with `postDelayed`**: legacy; leak on rotation. Use coroutines with the right scope.

## Boundaries with `mobile-technique`

- This reference is **defensive/design guidance**. When auditing a shipped APK for exploitable IPC (Intents, PendingIntent, ContentProvider) or credential exposure, load `offensive-techniques/mobile-technique/references/android-ipc-attack-surface.md` and the parent `mobile-technique` skill instead.
