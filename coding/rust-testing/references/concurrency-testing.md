# Concurrency testing (Loom, Miri, races)

Load when tests must pin down locks, atomics, channels, or shutdown joins —
deadlocks, lost wakeups, weak-memory bugs — not when the code under test is
single-threaded logic. Fuzzing and ASan stay in `fuzzing-and-sanitizers.md`.
Async timeouts and `tokio::time` stay in `async-and-boundaries.md`.

## Contents

- [Pick the tool](#pick-the-tool)
- [Loom](#loom)
- [Miri vs Loom vs TSan](#miri-vs-loom-vs-tsan)
- [Deadlocks and leaks in tests](#deadlocks-and-leaks-in-tests)

## Pick the tool

| Symptom | Tool |
|---|---|
| Data race / invalid atomic ordering in **safe** code that uses `loom::*` shims | **Loom** — permutes C11 schedules |
| UB (provenance, uninit, race) in **the real `std` types** | **Miri** (`cargo +nightly miri test`) |
| Race in FFI / code Miri cannot interpret | **TSan** (`-Zsanitizer=thread`) |
| Async task never polled / stuck waker | `tokio-console` (see `rust-performance` `profiling.md`) |
| Test hangs on `.await` / clock | paused Tokio test (`async-and-boundaries.md`) |

Miri observes one (or a few) executions of real std atomics. Loom exhaustively
explores *its* model of atomics/Mutex/threads. They overlap; they do not
replace each other. Miri docs: for complicated atomics, also use Loom.

## Loom

Intercepts loads/stores/spawns. **Not automatic** — the crate under test must
compile against `loom::sync::*` / `loom::thread` when `cfg(loom)`.

```toml
[target.'cfg(loom)'.dependencies]
loom = "0.7"
```

```rust
#[cfg(loom)]
#[test]
fn inc_is_atomic() {
    loom::model(|| {
        use loom::sync::atomic::{AtomicUsize, Ordering::*};
        use loom::sync::Arc;
        let v = Arc::new(AtomicUsize::new(0));
        let handles: Vec<_> = (0..2)
            .map(|_| {
                let v = v.clone();
                loom::thread::spawn(move || {
                    v.fetch_add(1, SeqCst);
                })
            })
            .collect();
        for h in handles {
            h.join().unwrap();
        }
        assert_eq!(2, v.load(SeqCst));
    });
}
```

```bash
RUSTFLAGS="--cfg loom" cargo test --test loom_atomics --release
```

Rules:

- Keep the model **tiny** (2–3 threads, a handful of atomic ops). Exhaustive
  search explodes. `LOOM_MAX_PREEMPTIONS=2` (or 3) bounds it when the full
  space is too large — that is incomplete, say so in the test comment.
- Do not mix `std::thread` / `std::sync::atomic` inside `loom::model`. Those
  ops are invisible and the test is fiction.
- Production code: `#[cfg(not(loom))] use std::sync::atomic::AtomicUsize;`
  `#[cfg(loom)] use loom::sync::atomic::AtomicUsize;` behind a small `sync`
  module. Do not cfg-switch at every call site.
- Loom is for **lock-free / mutex protocols**, not for Tokio tasks. Do not
  put `#[tokio::test]` inside `loom::model`.

## Miri vs Loom vs TSan

- `cargo +nightly miri test` — UB, including some data races and weak-memory
  surprises Miri *can* produce. Incomplete weak-memory: legal behaviors Miri
  will never show. `MIRIFLAGS=-Zmiri-strict-provenance` for pointer games.
  Cannot run real FFI, inline asm, most syscalls.
- TSan — native speed, FFI-capable, still one schedule per run. Pair with
  stress (`--test-threads` > 1, `--count`).
- Absence of a Loom/Miri/TSan hit is not a proof. Keep a deterministic
  regression test for every bug they find.

## Deadlocks and leaks in tests

- `std` `Mutex` poison in a test usually means another test thread panicked
  in the critical section — fix that panic; do not `into_inner()` it away in
  the test unless you are testing poison recovery.
- `OnceLock::get_or_init` re-entered from `f` **deadlocks**. Tests that
  initialize a `static` from two paths must not call back into the same cell.
- Joined threads: `thread::scope` panics if a child panicked. `join` children
  you expect to fail before the scope ends.
- `cargo test -- --test-threads=1` when tests share a `static` mutex/file
  lock; prefer isolating state over serializing the suite. nextest default
  is process-per-test — that hides some static leaks and makes others
  obvious (the process exits).

## References

- https://docs.rs/loom
- https://github.com/rust-lang/miri
- https://doc.rust-lang.org/nightly/unstable-book/compiler-flags/sanitizer.html
