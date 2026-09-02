# Concurrency

Load this when choosing shared-state, channel, or async patterns. The whole-program point: design
ownership first; reach for `Arc<Mutex<T>>` only when sharing is real.

## Choose the mechanism

- **Channels** for hand-off between producers/consumers — prefer bounded channels so
  backpressure is explicit; unbounded channels hide bugs. `std::sync::mpsc` is single-consumer, so
  worker-pool fan-out usually wants `crossbeam_channel::bounded` or `flume::bounded`.
- **`Arc<Mutex<T>>`** for genuinely shared mutable state; clone the `Arc` before `thread::spawn`.
- **Atomics** for primitives (flags, counters) — cheaper than a mutex; pick an ordering
  (`Relaxed` for counters, `Acquire`/`Release` pairs for handoff; `SeqCst` while unsure).

```rust
let (tx, rx) = crossbeam_channel::bounded::<Task>(16); // bounded = backpressure
for _ in 0..workers {
    let rx = rx.clone();
    std::thread::spawn(move || {
        for task in &rx {
            run(task);
        }
    });
}
```

## Lock discipline

- Lock ordering: when several locks coexist, document one global acquisition order to kill
  deadlock classes.
- Hold locks for the shortest span; never hold a `std::sync::Mutex` guard across `.await` — drop it
  or scope it before the await point (async-aware alternatives: `tokio::sync::Mutex`).

## Async footing

- Use async for I/O-bound concurrency, sync threads for CPU-bound work.
- Never `std::thread::sleep` or run blocking I/O on an executor thread — that stalls the scheduler;
  use `tokio::time::sleep(...).await`, or offload with `tokio::task::spawn_blocking`.
- `tokio` is idiomatic here, `std::future` alone is not a runtime; a chosen executor is mandatory.

## Global state and shared values

- `OnceLock` (Rust 1.70) / `LazyLock` (Rust 1.80) replace `lazy_static!`/`once_cell` for globals.
- `Send`/`Sync` tell you whether a type may move or be shared across threads; `spawn` closures,
  channels, and `Arc` targets generally need `'static`.

## Review checklist

- No unbounded channel in a pipeline that must apply backpressure.
- Shared mutable state boxed into the plainest feasible wrapper (`Mutex`/`RwLock` as needed — no more).
- No lock held across `.await`; no blocking call on an executor thread.
- Atomics' orderings named deliberately; `SeqCst` documented when it is only a placeholder.
