# Coroutine and Flow Testing

Load when writing tests for `suspend` functions, `Flow` pipelines, or diagnosing timing-related flakes.

## The `runTest` model

- `runTest { }` from `kotlinx-coroutines-test` gives you a virtual `TestScheduler`.
- Time is virtual: `delay(5_000)` completes instantly (advanced by the scheduler).
- `advanceUntilIdle()` runs all scheduled work; `advanceTimeBy(ms)` advances the clock by exactly `ms`; `runCurrent()` runs work scheduled at the current virtual time.
- Never use `runBlocking { }` in tests — it uses a real dispatcher and blocks the thread; scheduler behavior differs.

## Dispatcher injection

Production code should never hard-code `Dispatchers.IO` if you want to test it:

```kotlin
class Repo(
    private val io: CoroutineDispatcher = Dispatchers.IO,
) {
    suspend fun readAll() = withContext(io) { file.readBytes() }
}
```

In tests, pass `StandardTestDispatcher()` (from the same `runTest` scheduler) so time and ordering are deterministic.

## `MainDispatcherRule`

```kotlin
class MainDispatcherRule(
    val dispatcher: TestDispatcher = StandardTestDispatcher(),
) : TestWatcher() {
    override fun starting(d: Description) = Dispatchers.setMain(dispatcher)
    override fun finished(d: Description) = Dispatchers.resetMain()
}
```

Apply as `@get:Rule val main = MainDispatcherRule()`. All code using `Dispatchers.Main` or `viewModelScope` (which uses `Main.immediate`) is now driven by your `TestScheduler`.

## `StandardTestDispatcher` vs `UnconfinedTestDispatcher`

- `StandardTestDispatcher` — coroutines are queued; you must `advance…()` to run them. Best default; matches production ordering semantics.
- `UnconfinedTestDispatcher` — eager execution up to the first suspension. Convenient for quick tests where ordering does not matter; hides real ordering bugs. Use sparingly.

## Turbine for `Flow`

```kotlin
@Test fun emits() = runTest {
    val flow = flow { emit(1); delay(100); emit(2) }
    flow.test {
        assertEquals(1, awaitItem())
        assertEquals(2, awaitItem())
        awaitComplete()
    }
}
```

- `test { }` collects the flow in a coroutine and gives you `awaitItem()`, `awaitComplete()`, `awaitError()`, `cancel()`.
- Default timeout is 3s; override with `test(timeout = 10.seconds) { }`.
- For `StateFlow`, prefer `flow.value` for one-shot reads and `flow.test { … }` only when you need to observe transitions.

## Testing `StateFlow` from a ViewModel

```kotlin
@Test fun loads() = runTest {
    val vm = FeedViewModel(FakeRepo())
    vm.state.test {
        assertEquals(UiState.Loading, awaitItem())
        vm.refresh()
        assertEquals(UiState.Loaded(emptyList()), awaitItem())
        cancelAndConsumeRemainingEvents()
    }
}
```

`StateFlow` is hot; Turbine emits the current value first. Always `cancel()` (or `cancelAndConsumeRemainingEvents()`) to end collection.

## Testing cancellation

```kotlin
@Test fun cancelStops() = runTest {
    val job = launch {
        try { withContext(Dispatchers.IO) { longRunning() } }
        finally { cleanupCalled = true }
    }
    advanceTimeBy(50)
    job.cancelAndJoin()
    assertTrue(cleanupCalled)
}
```

- `cancelAndJoin()` waits for cancellation to complete before assertions.
- Verify `finally` blocks run.
- Verify `CancellationException` is not swallowed: assert that after cancel, no more work happens (e.g. `mockRepo.callCount` stays constant across `advanceTimeBy`).

## Timeouts

- `withTimeout(ms) { … }` throws `TimeoutCancellationException`. Test both success (finishes in time) and timeout paths.
- `runTest { … }` has an implicit 60s default wall-clock timeout for the whole test body — long virtual-time tests still finish instantly; only if real-time `delay` (via `Dispatchers.IO`) sneaks in will it hit.

## Async and `Deferred`

```kotlin
@Test fun parallelResults() = runTest {
    val a = async { fetchA() }
    val b = async { fetchB() }
    assertEquals(Pair("a", "b"), a.await() to b.await())
}
```

- If a launched `async` throws and you don't `await`, the exception surfaces at test-end. Turbine and `runTest` will fail the test.

## Testing hot flows (`SharedFlow`, `Channel`)

- `MutableSharedFlow(replay=0)` for events: `flow.test { }` misses events emitted before subscription. Emit **after** starting the Turbine collector, or use `subscriptionCount` to wait.
- `Channel<T>().receiveAsFlow()`: single-consumer only — do not `test { }` twice.

## Testing time-dependent code

Prefer injecting a `Clock` (`kotlinx.datetime.Clock` or a simple `interface Clock { fun nowMs(): Long }`) instead of calling `System.currentTimeMillis()` directly. Then swap with a `FakeClock` in tests. Virtual time in `runTest` handles `delay`, not wall-clock reads.

## Anti-patterns

- `runBlocking` in tests → real dispatcher, breaks scheduler control.
- `delay(1000)` in tests without `advanceTimeBy` → hangs 1 second per test (`runTest` with real `Dispatchers.IO` gets stuck).
- Reading `MutableStateFlow.value` immediately after `launch { … update … }` without `advanceUntilIdle()` → assertion fires before update.
- `GlobalScope.launch { }` inside code under test → runs on a real dispatcher; test cannot control it. Refactor to injectable scope.
- `runCatching { }` swallowing `CancellationException` → tests pass but cancellation is broken; add explicit `if (e is CancellationException) throw e` assertions.
