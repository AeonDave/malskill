# Language features (Rust 1.75–1.98, Edition 2024)

Load when writing or reviewing code that uses Edition 2024 semantics, `async fn` /
RPITIT in traits, async closures / `AsyncFn`, precise capturing (`use<>`), let
chains, if-let guards, `#[expect]`, `cfg_select!`, or edition-gated `unsafe`
attributes. Concurrency primitives live in `concurrency.md`. Capture/`Drop` traps
that show up as borrow-checker errors are summarized here; ownership defaults stay
in `ownership-and-borrowing.md`.

The **crate edition** (`edition` in `Cargo.toml`) and **MSRV** (`rust-version` /
CI toolchain) independently gate these. A 1.98 toolchain compiling `edition = "2021"`
keeps 2021 capture and drop-order rules.

## Contents

- [Edition 2024 (Rust 1.85+)](#edition-2024-rust-185)
- [RPIT capture and `use<>` (1.82+, Edition 2024 default)](#rpit-capture-and-use-182-edition-2024-default)
- [async fn and RPITIT in traits (1.75+)](#async-fn-and-rpitit-in-traits-175)
- [Async closures and `AsyncFn` (1.85+)](#async-closures-and-asyncfn-185)
- [Let chains (Edition 2024, 1.88+) and if-let guards (1.95+)](#let-chains-edition-2024-188-and-if-let-guards-195)
- [Tail-expression drop order (Edition 2024)](#tail-expression-drop-order-edition-2024)
- [`#[expect]` (1.81+)](#expect-181)
- [`cfg(true)` / `cfg_select!`](#cfgtrue--cfg_select)
- [Not stable as of 1.98](#not-stable-as-of-198)

## Edition 2024 (Rust 1.85+)

Set `edition = "2024"` then `cargo fix --edition`. Review the diff; the fixer
cannot prove `#[unsafe(no_mangle)]` uniqueness or `set_var` soundness.

Edition-gated rules that change generated code or required annotations:

- **RPIT captures every in-scope lifetime** unless you write `+ use<...>` (see
  below). `cargo fix --edition` inserts `use<>` where `impl_trait_overcaptures`
  fires.
- **Tail-expression temporaries drop before locals** (see drop-order section).
- **`unsafe_op_in_unsafe_fn` warns by default**: an `unsafe fn` body is *safe*
  unless wrapped in `unsafe { }`. It is **warn**, not deny. Put a `// SAFETY:`
  comment on each inner block — see `unsafe-and-ffi.md`.
- **`#[no_mangle]` / `#[export_name]` / `#[link_section]` require `#[unsafe(...)]`**.
  `unsafe extern { ... }` is required. Migration: `cargo fix --edition`.
- **`std::env::set_var` / `remove_var` are `unsafe`**: they race with C `getenv`
  and with other threads. Prefer arguments / a once-initialized config. If you
  must set env, do it before spawning threads and document the precondition.
- **Prelude** includes `Future` and `IntoFuture`.
- **`gen` is a reserved keyword** (rename identifiers to `r#gen`). `gen { }`
  blocks are **not** stable as of 1.98.

`let` chains need both the 2024 edition *and* rustc 1.88+.

## RPIT capture and `use<>` (1.82+, Edition 2024 default)

`impl Trait` in return position captures generic parameters into the opaque type.
Over-capturing makes the opaque invariant in those lifetimes and blocks `'static`
/ `Send` bounds you expected.

```rust
// 1.82+ all editions: capture only `'a` (and type params, which must be listed).
fn first<'a, 'b>(x: &'a str, _: &'b str) -> impl Iterator<Item = u8> + use<'a> {
    x.bytes()
}
```

- **Edition 2021 default:** lifetimes are captured only if they appear in bounds.
  The old `Captures<'a>` / `T: 'a` tricks are obsolete — replace with `use<'a, T>`.
- **Edition 2024 default:** all in-scope lifetimes *and* type parameters are
  captured. Opt *out* with `use<...>` so a leftover lifetime does not infect the
  opaque. You cannot omit an in-scope type/const parameter from `use<>`.
- **Traits (1.87+):** `fn m(&self) -> impl Trait + use<Self>` in a trait is
  legal; omitting `'a` from `use<>` is how you avoid a GAT-like capture of the
  method lifetime. `use<>` on RPITIT still cannot name arbitrary method
  lifetimes in every position — if rustc rejects it, keep capturing `Self` only
  and box, or wait; do not invent a `Captures` bound on the trait.

Public APIs: write `use<>` explicitly when the captured set *is* the contract
(so a later edition bump cannot silently capture more).

## async fn and RPITIT in traits (1.75+)

```rust
trait Fetch {
    async fn get(&self, url: &str) -> Result<Vec<u8>, Error>;
    fn items(&self) -> impl Iterator<Item = u32> + '_;
}
```

These desugar to anonymous associated types. Limits that still bite:

- **Not `dyn`-safe.** `dyn Fetch` cannot contain `async fn` / `-> impl Trait`.
  Keep a sync object-safe core, or use `async-trait` / `dynosaur` only when you
  truly need `dyn`. See `dynamic-dispatch-and-plugins.md`.
- Recursion and `Send` bounds on the hidden future are awkward without return-type
  notation (still **unstable** as of 1.98). If you need `F::get(..): Send`, either
  bound a boxed `Pin<Box<dyn Future<Output = ...> + Send>>` in the trait, or keep
  the trait generic over the future.
- `async-trait` boxing is no longer the default for static dispatch. Drop it when
  callers are generic / monomorphized.

## Async closures and `AsyncFn` (1.85+)

`async |...| { ... }` is a reusable async callable whose future may **borrow
captures** (lending). Bounds:

```rust
async fn map_ok<F>(f: F) -> String
where
    F: AsyncFnOnce(&str) -> String, // not FnOnce(&str) -> impl Future
{
    f("x").await
}

map_ok(async |s| s.to_string()).await;
```

- Write `AsyncFn` / `AsyncFnMut` / `AsyncFnOnce`, not `F: FnOnce() -> Fut` with a
  second type parameter. The old two-parameter bound cannot express a
  higher-ranked `for<'a>` future that borrows `s`.
- `async fn` items and `|| async { }` closures implement `AsyncFn*` when the
  future does not lend. Prefer real `async ||` when the future must borrow.
- `AsyncFn*` is **not dyn-safe**. `async Fn()` modifier syntax is **not**
  stabilized; name `AsyncFnOnce()` in bounds.
- Associated methods `async_call` / `CallRefFuture` stay **unstable**
  (`async_fn_traits`). Call the closure; do not name those items.

## Let chains (Edition 2024, 1.88+) and if-let guards (1.95+)

```rust
if let Channel::Stable(v) = info()
    && let Semver { major, minor, .. } = v
    && major == 1
{
    // ...
}

match value {
    Some(x) if let Ok(y) = compute(x) => { /* x and y in scope */ }
    _ => {}
}
```

- Let chains are **`&&` only**, top-level in `if` / `while`. Parenthesized
  `if (let ... || let ...)` is still illegal.
- They depend on 2024 `if let` temporary scopes — they will not compile on
  edition 2021 even with rustc 1.88+.
- `if let` guards (1.95+) do **not** participate in match exhaustiveness (same
  as `if` guards). Keep a `_` arm.

## Tail-expression drop order (Edition 2024)

In 2021, a temporary in a tail expression could outlive locals (`RefCell` /
`Mutex` guards then fail to compile, or drop *after* the lock they needed).
In 2024, that temporary drops at the end of the block, **before** locals.

```rust
// Compiles in 2024; 2021 dropped `c` before `c.borrow()`.
fn last(c: RefCell<i32>) -> i32 {
    *c.borrow()
}
```

The inverse: `{ &String::from("x") }.len()` can fail in 2024 because the
`String` temporary no longer lives for the outer statement. Bind a local.

`tail_expr_drop_order` (allowed-by-default) flags `Drop` types whose drop time
moves. Inspect lock/channel/`Drop` side effects; most changes are harmless.

## `#[expect]` (1.81+)

`#[expect(lint)]` is `#[allow]` plus a warning (`unfulfilled_lint_expectations`)
if the lint would *not* have fired. Prefer it over `#[allow]` when suppressing a
known, local diagnostic (dead code you are about to use, a clippy false positive
you want to notice if it disappears). Do not `expect` crate-wide.

## `cfg(true)` / `cfg_select!`

- `#[cfg(true)]` / `#[cfg(false)]` (1.88, `cfg_boolean_literals`) — feature-gate
  stubs and `cfg`-out examples without a fake feature name.
- `cfg_select!` (1.95) — first matching `cfg` arm, with `_ =>` fallback. Replaces
  `cfg-if` for new code:

```rust
cfg_select! {
    unix => { fn path_sep() -> char { '/' } }
    windows => { fn path_sep() -> char { '\\' } }
    _ => { compile_error!("unsupported target"); }
}
```

## Not stable as of 1.98

Do not write these without `#![feature(...)]` and an explicit nightly MSRV:

- `gen { }` / `async gen { }` — keyword reserved only
- `std::sync::mpmc` (`mpmc_channel`)
- `MutexGuard::map` / `MappedMutexGuard` (`mapped_lock_guards`)
- `std::alloc::Allocator` / `allocator_api` (use `allocator-api2` on stable)
- `std::error::Report` (`error_reporter`)
- return-type notation (`F::method(..): Send`)
- `std::simd` / `portable_simd`

Compiler-only nightly knobs (`-Z threads`, Cranelift) live in `rust-performance`
`compiler-and-build-tuning.md`.

## References

- https://doc.rust-lang.org/edition-guide/rust-2024/index.html
- https://blog.rust-lang.org/2025/02/20/Rust-1.85.0/
- https://blog.rust-lang.org/2024/10/17/Rust-1.82.0/
- https://blog.rust-lang.org/2023/12/21/async-fn-rpit-in-traits.html
- https://blog.rust-lang.org/2025/06/26/Rust-1.88.0/
- https://blog.rust-lang.org/2026/04/16/Rust-1.95.0/
- https://doc.rust-lang.org/std/ops/trait.AsyncFn.html
