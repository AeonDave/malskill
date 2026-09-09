# Concurrency

Load this when choosing shared-state, channel, thread, or async patterns. The
whole-program point: design ownership first; reach for `Arc<Mutex<T>>` only when
sharing is real.

Thread-pool sizing, false sharing, and async *throughput* live in the
`rust-performance` skill (`concurrency-and-throughput.md`). Loom / Miri for
concurrency tests live in `rust-testing` (`concurrency-testing.md`).

## Contents

- [Choose the mechanism](#choose-the-mechanism)
- [Scoped threads](#scoped-threads)
- [Lock discipline and poison](#lock-discipline-and-poison)
- [OnceLock and LazyLock](#oncelock-and-lazylock)
- [Atomics](#atomics)
- [Async footing](#async-footing)
- [File locks](#file-locks)
- [Review checklist](#review-checklist)

## Choose the mechanism

- **Channels** for hand-off between producers/consumers — prefer bounded channels
  so backpressure is explicit; unbounded channels hide bugs. `std::sync::mpsc` is
  **single-consumer** (`Receiver` is not `Clone`). Worker-pool fan-out wants
  `crossbeam_channel::bounded` or `flume::bounded`.
- **`std::sync::mpmc` is not stable as of 1.98** (`#![feature(mpmc_channel)]`). Do
  not import it on stable; keep crossbeam/flume.
- **`Arc<Mutex<T>>`** for genuinely shared mutable state; clone the `Arc` before
  `thread::spawn`. Prefer **`thread::scope`** when the work can borrow the stack
  instead of cloning into `'static`.
- **Atomics** for primitives (flags, counters) — cheaper than a mutex; pick an
  ordering (`Relaxed` for counters, `Acquire`/`Release` pairs for handoff;
  `SeqCst` while unsure).

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

Cap `workers` with `std::thread::available_parallelism()` (see performance skill);
do not spawn one OS thread per request.

## Scoped threads

`thread::scope` (1.63+) spawns threads that may borrow non-`'static` locals. The
scope **joins every still-running child** before returning; if a child panicked
and was not `join`ed, `scope` panics.

```rust
fn par_sum(xs: &[i64]) -> i64 {
    let mid = xs.len() / 2;
    thread::scope(|s| {
        let left = s.spawn(|| xs[..mid].iter().sum::<i64>());
        let right = xs[mid..].iter().sum::<i64>();
        left.join().unwrap() + right
    })
}
```

- Use scope when the borrowed data outlives the parallel region (slices, `&Mutex`,
  stack buffers). Use `thread::spawn` + `Arc` when the thread must outlive the
  caller (background workers, `'static` tasks).
- `JoinHandle::is_finished` (1.61) is a non-blocking poll; it does not replace
  `join`.

## Lock discipline and poison

- Lock ordering: when several locks coexist, document one global acquisition
  order to kill deadlock classes.
- Hold locks for the shortest span; never hold a `std::sync::Mutex` guard across
  `.await` — drop it or scope it before the await point (async-aware alternative:
  `tokio::sync::Mutex`).
- **`MutexGuard` is `!Send`** (POSIX: unlock on the same thread). Do not send a
  guard to another thread; drop it first.
- **Poison:** `std` `Mutex`/`RwLock` poison when a thread panics while holding
  the guard. `lock()` then returns `Err(PoisonError)`. The inner data may be
  inconsistent. Libraries: propagate or map to an error. Binaries that treat
  poison as "the other thread already crashed":
  `mutex.lock().unwrap_or_else(|p| p.into_inner())`. Do not `.unwrap()` poison
  in library paths unless poisoning is part of the contract.
- `OnceLock` / `LazyLock` **never poison**.
- Mapped guards (`MutexGuard::map`) are **nightly** (`mapped_lock_guards`). On
  stable, extract the field you need inside the lock scope or split into smaller
  mutexes.

## OnceLock and LazyLock

- `OnceLock` (1.70) / `LazyLock` (1.80) replace `lazy_static!` / `once_cell` for
  process-wide init. `LazyLock` deref-inits; `OnceLock` when init needs extra
  arguments (`get_or_init(|| load(path))`).
- `OnceLock::wait` (1.86) blocks until another thread `set`s / `get_or_init`s.
  Re-entrant `get_or_init` from `f` currently **deadlocks**.
- `LazyLock::get` / `get_mut` / `force_mut` (1.94) inspect without forcing, or
  force with `&mut` when you uniquely own the cell.
- `Send`/`Sync` tell you whether a type may move or be shared across threads;
  `spawn` closures, channels, and `Arc` targets generally need `'static` unless
  you are inside `thread::scope`.

## Atomics

- Name orderings deliberately; `SeqCst` documented when it is only a placeholder.
- `Atomic*::update` / `try_update` and `AtomicPtr::update` (1.95) — CAS loops
  with a closure; prefer these over hand-rolled `compare_exchange` for
  read-modify-write of a single word.
- `Atomic::from_mut` / `from_mut_slice` / `get_mut_slice` (1.98) — view `&mut T`
  as an atomic when you already have unique access (tests, single-threaded
  setup). Do not use this to paper over missing `UnsafeCell`.

## Async footing

- Use async for I/O-bound concurrency, sync threads / Rayon for CPU-bound work.
- Never `std::thread::sleep` or run blocking I/O on an executor thread — that
  stalls the scheduler; use `tokio::time::sleep(...).await`, or offload with
  `tokio::task::spawn_blocking`.
- `tokio` is a runtime; `std::future` alone is not. A chosen executor is
  mandatory.
- Callbacks: `AsyncFn` / `async ||` (1.85), not `F: Fn() -> impl Future`. See
  `language.md`.
- Pin locals with `std::pin::pin!(fut)` (1.68) before polling; `Box::pin` when
  the future must be `'static` and heap-allocated. Do not `mem::transmute` to
  `Pin`.
- `Waker::noop()` (1.85) for APIs that demand a `Context` in tests or
  poll-once checks — it wakes nothing. Production waiters need a real waker.
- `File::lock` is blocking; never call it on an async worker. Use
  `spawn_blocking` or a dedicated thread.

## File locks

`std::fs::File::lock` / `lock_shared` / `try_lock` / `try_lock_shared` / `unlock`
(1.89) — advisory OS file locks for **cross-process** exclusion (PID files, cache
writers). Not a substitute for `Mutex` inside one process. Released when **all**
duplicated/inherited handles are closed, or via `unlock`. Call `unlock` if you
keep the `File` open; `try_clone`/`dup` means dropping one handle does not unlock.
Windows: lock fails if the file is opened append-only — open with read or write.

## Review checklist

- No unbounded channel in a pipeline that must apply backpressure.
- Shared mutable state boxed into the plainest feasible wrapper (`Mutex`/`RwLock`
  as needed — no more).
- No lock held across `.await`; no blocking call on an executor thread.
- Atomics' orderings named deliberately; `SeqCst` documented when it is only a
  placeholder.
- `thread::scope` used instead of `Arc` when borrows suffice; `mpmc` not used on
  stable.
- Poison handled at library boundaries; `OnceLock` used when a panic during init
  must not poison a mutex.

## References

- https://doc.rust-lang.org/std/thread/fn.scope.html
- https://doc.rust-lang.org/std/thread/fn.available_parallelism.html
- https://doc.rust-lang.org/std/sync/struct.OnceLock.html
- https://doc.rust-lang.org/std/sync/struct.Mutex.html
- https://doc.rust-lang.org/std/ops/trait.AsyncFn.html
