# Coroutines and Flow Performance

Load when async pipelines are slow, bursty, allocate excessively, or block the main thread.

## Dispatcher pool anatomy

| Dispatcher | Type | Default size | Use |
|------------|------|--------------|-----|
| `Dispatchers.Main` | Single-threaded | 1 (Android main looper) | UI, `ViewModel` boundary |
| `Dispatchers.Main.immediate` | Same-thread if possible | — | Compose collection, `viewModelScope.launch` |
| `Dispatchers.Default` | Shared pool | `max(2, availableProcessors())` | CPU-bound |
| `Dispatchers.IO` | Shared pool | 64 or `max(64, availableProcessors())` | Blocking I/O |
| `Dispatchers.Unconfined` | Caller thread | — | Testing, or explicit stay-on-caller |

`Default` and `IO` share underlying threads via a `DefaultScheduler`; heavy `IO` work can crowd out `Default`. Symptoms: main thread starves waiting for a `Default`-scheduled task.

## `limitedParallelism`

Cap concurrency without leaking the pool:

```kotlin
private val diskDispatcher = Dispatchers.IO.limitedParallelism(4)

suspend fun readFiles(paths: List<Path>): List<String> = coroutineScope {
    paths.map { async(diskDispatcher) { it.readText() } }.awaitAll()
}
```

- Backs onto `Dispatchers.IO`'s pool but restricts this consumer to N concurrent coroutines.
- Prevents thread starvation when a burst arrives.
- Useful for network clients, DB pools, image decoders.

## `withContext` overhead

- Every `withContext(other)` performs a dispatcher swap: ~500 ns – 5 µs, mostly allocation and continuation walking.
- For microsecond-scale work, the swap dominates. Move it up to the caller or batch.
- Do **not** wrap trivial computations. Wrap the boundary that actually blocks.

## `Flow` overhead

- `Flow` is cold: every terminal operator (`collect`, `first`, `toList`) triggers a fresh upstream pass.
- Each intermediate operator (`map`, `filter`) allocates a wrapper `Flow` per emission chain.
- Fusing operators (contiguous `map`/`filter`) are combined in the same emitter — no per-operator allocation.
- Prefer `flow { emit(x) }` over `flowOf(x, y, z)` when values are computed lazily.

## Backpressure operators

| Operator | Behavior | When |
|----------|----------|------|
| `collect { }` (no operator) | Sender and receiver rendezvous per emission | Order matters, every item processed |
| `buffer(n)` | Bounded queue of size `n`; emitter suspends when full (default `n = 64`) | Smooth bursts, all items processed |
| `buffer(n, BufferOverflow.DROP_OLDEST)` | Drops oldest when full | Latest N wins |
| `conflate()` | Keeps only latest; producer never suspends | UI state — latest matters |
| `collectLatest { }` | Cancels previous block on new emission | Search-as-you-type, previewing |
| `debounce(ms)` | Emits after `ms` of quiet | Rate-limit typed input |
| `sample(ms)` | Emits at most once per `ms` window | High-freq telemetry |

Combine two flows: `combine(a, b) { … }` — recomposes on any change. For sequenced flows, `flatMapLatest { }` cancels previous inner flows (correct choice for reactive search).

## `StateFlow` vs `SharedFlow`

- `StateFlow<T>` — always has a value, conflates identical emissions, replay=1. Zero-allocation reads via `.value`.
- `MutableSharedFlow<T>(replay = 0, extraBufferCapacity = 0, onBufferOverflow = SUSPEND)` — event stream. Default suspends emitter if no subscribers ready. Use `DROP_OLDEST` overflow for lossy telemetry.
- `MutableSharedFlow(replay = N)` for late subscribers to see history.
- **Never** allocate a `MutableSharedFlow` inside a hot Composable/coroutine — hoist to ViewModel scope.

## Channel vs Flow

- `Channel<T>` — hot, single or multi-consumer, primary use for cross-coroutine handoff without collecting Flow semantics.
- Use `Channel(capacity)` explicit sizing: `RENDEZVOUS` (0), `CONFLATED` (drop old), `BUFFERED` (64), `UNLIMITED` (only when you can prove memory bounded).
- `channelFlow { send(x) }` — used inside `flow { }`-style code when multiple producers must emit concurrently.

## `runBlocking` and `runCatching`

- `runBlocking { }` in production = blocks the calling thread; on Android main thread, deadlocks. Ban outside `main()` entry.
- `runCatching { }` catches `CancellationException` — breaks coroutine cancellation semantics. See `kotlin-patterns/references/errors-and-flow-control.md`.

## Async boundary allocation

Per launch/`async`:

- ~200–500 B for the `StandaloneCoroutine`/`DeferredCoroutine` + `CoroutineContext.Element` chain.
- Each `suspend` call site generates a `Continuation` — usually reused via the continuation stack; still costs the compiler-generated `label` and captured state.
- In a hot loop, prefer:
  ```kotlin
  flow { for (item in list) emit(process(item)) }
      .collect { … }
  ```
  over `list.map { launch { process(it) } }.joinAll()`.

## Coroutine cancellation cost

- Cancellation is cooperative: cancelled coroutines don't immediately stop. If a CPU-bound loop doesn't call `ensureActive()` or `yield()`, it runs to completion.
- Add `yield()` or `ensureActive()` every ~1 ms of work in a cancellable loop.
- `withTimeout(ms)` throws `TimeoutCancellationException` — a `CancellationException` subclass. Handle explicitly if you catch broadly.

## Benchmarking coroutines

Microbenchmark with `runBlockingTest` or, more cleanly, kotlinx-benchmark JMH:

```kotlin
@State(Scope.Benchmark)
open class FlowBench {
    private val items = (1..1000).toList()

    @Benchmark fun mapFilter(bh: Blackhole) = runBlocking {
        items.asFlow().map { it * 2 }.filter { it % 3 == 0 }
            .collect { bh.consume(it) }
    }
}
```

Measured on a JMH harness — not appropriate inside Android app process because dispatcher pools differ.

## Anti-patterns

- **`Dispatchers.IO` for CPU-bound work** — starves the pool used by other I/O; use `Default` or a `limitedParallelism` slice.
- **`SharingStarted.Eagerly` on repository Flows** — keeps upstream alive forever, leaks work and memory. Default to `WhileSubscribed(5_000)`.
- **`stateIn` with `initialValue = null` on non-null semantic type** — every consumer needs a null check. Use a sealed `Loading` state.
- **`Flow` chains with 20+ operators** — allocation + dispatch overhead dominates. Move to a single `transform { }` block for the fusion.
- **`launch { runCatching { … } }` swallowing exceptions** — coroutine still marked failed to parent scope; scope may cancel siblings. Handle the exception explicitly.
- **`GlobalScope.launch { }` for fire-and-forget** — no lifecycle, no observability. Use an injected app-scoped `CoroutineScope(SupervisorJob() + Dispatchers.Default)`.
- **`Thread.sleep` inside a `suspend` function** — blocks the dispatcher thread. Use `delay(ms)` (suspends).
