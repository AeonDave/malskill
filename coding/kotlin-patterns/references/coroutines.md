# Kotlin Coroutines and Flow

Load when writing `suspend` code, `Flow` pipelines, or diagnosing coroutine leaks, cancellation bugs, or `runBlocking` misuse.

## Structured concurrency (mental model)

- Every coroutine belongs to a `CoroutineScope`. When the scope cancels, all its children cancel.
- A parent waits for all its children before completing.
- **Never** launch from `GlobalScope`. If a component owns work, it owns a scope: `viewModelScope`, `lifecycleScope`, `CoroutineScope(SupervisorJob() + Dispatchers.Default)` injected via DI.
- Use `SupervisorJob` at the scope root when child failure must not cancel siblings (e.g. multiple independent background jobs).

## Dispatchers

| Dispatcher | Use for |
|------------|---------|
| `Dispatchers.Main` (Android) | UI work, view updates; never CPU-heavy work |
| `Dispatchers.Main.immediate` | UI work already on main; skips re-post if already on Main |
| `Dispatchers.Default` | CPU-bound (JSON parsing, encryption, image processing) |
| `Dispatchers.IO` | Blocking I/O (file, network via blocking clients, JDBC, sqlite) |
| `Dispatchers.Unconfined` | Testing, or intentionally staying on the calling thread. Not for production code paths. |

- Declare dispatcher intent at the **leaf** where the blocking work happens: `suspend fun readFile() = withContext(Dispatchers.IO) { … }`. Callers stay dispatcher-agnostic.
- Never call blocking APIs (`Thread.sleep`, `File.readBytes` on a big file, `Socket.connect`) without `withContext(Dispatchers.IO)`.

## Cancellation

- Cancellation is cooperative. A CPU-bound loop must call `ensureActive()` or `yield()` periodically or check `isActive`.
- `CancellationException` is a control-flow signal, not an error. **Do not swallow it.**

```kotlin
try {
    doWork()
} catch (e: CancellationException) {
    throw e            // always re-throw
} catch (e: IOException) {
    // handle real error
}
```

Or, when catching broadly:

```kotlin
try {
    doWork()
} catch (e: Throwable) {
    if (e is CancellationException) throw e
    logger.error(e) { "unexpected" }
    fallback()
}
```

- `runCatching { }` swallows `CancellationException`. Do not use it inside `suspend` code without a manual re-throw. Prefer explicit `try/catch`.
- `withTimeout(ms) { }` throws `TimeoutCancellationException` — this is a `CancellationException` subclass; the current coroutine is cancelled. Use `withTimeoutOrNull` when you want a null on timeout without cancellation.

## `launch` vs `async`

- `launch { }` — fire-and-forget, returns `Job`. Use for side effects.
- `async { }` — returns `Deferred<T>`; **call `.await()` or you leak the exception silently** until the scope cancels.
- Parallel work: `coroutineScope { val a = async { … }; val b = async { … }; a.await() to b.await() }`. Any failure cancels the whole scope.
- Independent parallel work where one failure must not kill the rest: `supervisorScope { … }`.

## `runBlocking` rules

- **Production code**: never. It blocks the calling thread and can deadlock a coroutine dispatcher.
- **Tests**: use `runTest { }` (from `kotlinx-coroutines-test`), not `runBlocking`. `runTest` provides a virtual `TestScheduler` and auto-advances time.
- **`main` entry points / CLI**: acceptable at the top-level `fun main()` only.

## Flow

- `Flow<T>` is **cold**: the producer runs per collector. Multiple collectors = multiple upstream runs unless converted to hot (`stateIn`, `shareIn`).
- Operators (`map`, `filter`, `transform`) are cold; terminal operators (`collect`, `first`, `toList`, `stateIn`) start collection.
- Backpressure: `Flow` is sequential by default. `buffer(n)` decouples producer and consumer; `conflate()` drops intermediate values; `collectLatest { }` cancels the previous block on new emission.
- Combine sources with `combine(a, b) { av, bv -> … }`; sequence with `flatMapLatest { }` (cancels previous inner flow on new outer emission — right choice for search-as-you-type).

### `StateFlow` vs `SharedFlow`

| Type | When |
|------|------|
| `StateFlow<T>` | Represents current UI state; requires initial value; conflates; new collectors get the latest value. |
| `MutableSharedFlow<T>` | One-shot events (navigation, snackbars). `replay = 0`; use `extraBufferCapacity` and `onBufferOverflow = BufferOverflow.DROP_OLDEST` to prevent slow collectors from blocking emitters. |

- Do not model one-shot events as `StateFlow` — a config change re-collects and re-fires the last event.
- `stateIn(scope, SharingStarted.WhileSubscribed(5_000), initial)` in a ViewModel: shares upstream while a UI subscriber exists, keeps it alive 5s across config changes.

### Android UI collection

```kotlin
lifecycleScope.launch {
    repeatOnLifecycle(Lifecycle.State.STARTED) {
        viewModel.state.collect { render(it) }
    }
}
```

- `repeatOnLifecycle` cancels the block on `STOPPED` and re-launches on `STARTED`. Without it, collection continues on background screens and leaks work.
- In Compose: `val state by viewModel.state.collectAsStateWithLifecycle()`. `collectAsState` alone (without `WithLifecycle`) does not respect lifecycle.

## Testing coroutines

- `runTest { }` gives a virtual `TestScheduler`. `advanceTimeBy(1000)` and `advanceUntilIdle()` control time.
- Inject dispatchers (never call `Dispatchers.IO` directly in code under test). A common pattern: constructor-inject `CoroutineDispatcher` and swap for `StandardTestDispatcher` in tests.
- `MainDispatcherRule` (or manual `Dispatchers.setMain(...)` / `resetMain()` in `@Before`/`@After`) replaces `Dispatchers.Main` for tests.
- `Turbine` (cash/turbine) simplifies `Flow` assertions: `flow.test { assertEquals(x, awaitItem()); awaitComplete() }`.

## Common bugs to hunt

- `GlobalScope.launch { }` in a ViewModel or Activity → leaks across recreation.
- `viewModelScope.launch(Dispatchers.IO) { … }` — the launch dispatcher choice is often wrong; the ViewModel should stay on Main and delegate blocking work via `withContext` at the leaf.
- `flow.collect { }` in `lifecycleScope.launch { }` without `repeatOnLifecycle` — collection continues while the screen is stopped.
- `async { … }` without `await` — exception is swallowed until scope cancels.
- `runBlocking(Dispatchers.Main)` in Android — deadlocks the UI thread if the block suspends waiting for something on Main.
- Catching `Exception` and not re-throwing `CancellationException` — coroutine becomes uncancellable.
- Emitting from a different coroutine than the collector: `Flow` requires single-collector concurrency (`channelFlow { send(...) }` when producing from multiple coroutines).
