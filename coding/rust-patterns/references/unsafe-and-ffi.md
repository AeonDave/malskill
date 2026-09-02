# Unsafe and FFI

Use this reference when writing or reviewing `unsafe` blocks, raw pointers, uninitialized
memory, layout-sensitive types, or foreign-function (C/ABI) boundaries. For auditing someone
else's crate for exploitable bugs, see `security-review.md`.

## Contents

- [Prime directive](#prime-directive)
- [The safety contract](#the-safety-contract)
- [Safety invariants you must uphold](#safety-invariants-you-must-uphold)
- [Uninitialized memory](#uninitialized-memory)
- [Raw pointers and provenance](#raw-pointers-and-provenance)
- [transmute and reinterpretation](#transmute-and-reinterpretation)
- [FFI boundaries](#ffi-boundaries)
- [Panics across FFI](#panics-across-ffi)
- [Verification](#verification)
- [Review checklist](#review-checklist)

## Prime directive

`unsafe` unlocks exactly five powers: deref a raw pointer, call an `unsafe` fn, access/modify a
mutable `static`, implement an `unsafe` trait, read `union` fields. It does **not** disable the
borrow checker — references built inside `unsafe` are still checked.

- Keep `unsafe` blocks minimal and encapsulate them behind a safe API that upholds all invariants.
- If a safe abstraction can express it (slices, `Vec`, `Cell`/`RefCell`, `bytemuck`), use that instead.
- The safe wrapper owns the proof; callers must not be able to trigger UB through the safe surface.

## The safety contract

- Every `unsafe fn` documents its precondition in a `/// # Safety` section.
- Every `unsafe { }` block carries a `// SAFETY:` comment proving the precondition holds *here*.
- Deny undocumented unsafe in the lint config: `#![warn(unsafe_op_in_unsafe_fn)]` and
  `#![deny(clippy::undocumented_unsafe_blocks)]`.

```rust
/// # Safety
/// `ptr` must be non-null, aligned, and point to an initialized `Widget`
/// that stays valid for `'a`.
unsafe fn widget_ref<'a>(ptr: *const Widget) -> &'a Widget {
    // SAFETY: caller guarantees ptr is valid, aligned, initialized, and outlives 'a.
    unsafe { &*ptr }
}
```

## Safety invariants you must uphold

A raw-pointer dereference or `slice::from_raw_parts` is UB unless *all* hold:

- **Non-null and aligned** for the pointee type (`ptr.is_aligned()` is your friend).
- **Dereferenceable** for the full size read/written — the whole `len * size_of::<T>()` span.
- **Initialized** to a valid value of `T` (see uninitialized memory below; `bool`, `char`, enum
  discriminants, `NonZero*`, and references have forbidden bit patterns).
- **Aliasing respected**: an `&mut T` must be unique; never hold two `&mut` to the same place, and
  never alias `&mut` with `&`.
- **Lifetime not outlived**: the borrow you fabricate must not outlive the real data.
- `Send`/`Sync` implemented (or `unsafe impl`'d) only when the type is genuinely thread-safe.

## Uninitialized memory

- Never use `mem::uninitialized`/`mem::zeroed` for types with invalid bit patterns — instant UB.
  Use `MaybeUninit<T>`.
- Do **not** create a reference (`&mut`/`&`) to uninitialized memory. Write through a raw pointer.
- Use `&raw mut`/`&raw const` (stable since 1.82; `addr_of_mut!`/`addr_of!` on older toolchains)
  to get a field pointer without materializing a reference.

```rust
use std::mem::MaybeUninit;

let role = unsafe {
    let mut uninit = MaybeUninit::<Role>::uninit();
    let p = uninit.as_mut_ptr();
    // &raw mut avoids an (illegal) &mut to uninitialized memory; write initializes each field.
    (&raw mut (*p).flag).write(1);
    (&raw mut (*p).name).write(String::from("basic"));
    uninit.assume_init() // SAFETY: every field is now initialized.
};
```

## Raw pointers and provenance

- A pointer carries **provenance** (which allocation it may access), not just an address. Casting an
  integer to a pointer fabricates provenance and is a common source of silent UB.
- Take an address without a reference via `&raw const x` / `&raw mut x`. Round-trip through integers
  with the strict-provenance APIs `ptr.expose_provenance()` / `ptr::with_exposed_provenance` when you
  truly must, and keep those sites rare and documented.
- Move bytes with `ptr::read`, `ptr::write`, `ptr::copy`/`copy_nonoverlapping`. For packed or
  unaligned sources use `read_unaligned`/`write_unaligned`.
- `ptr::read` performs a bitwise copy without running the source's destructor — pair reads/writes so
  you never double-drop or drop-then-use.

## transmute and reinterpretation

- Prefer, in order: `as` casts / `TryFrom` / `from_le_bytes` etc. → `bytemuck` or `zerocopy` for POD
  reinterpretation → `mem::transmute` only as a last resort.
- `transmute` requires identical size, never changes layout, and is UB if it produces an invalid
  value (a `bool` that isn't 0/1, a null reference, an out-of-range enum/`NonZero`).
- Reinterpreting types across an ABI requires `#[repr(C)]` or `#[repr(transparent)]`; the default
  `repr(Rust)` layout is unspecified and may reorder fields.

## FFI boundaries

- Mark every type crossing the boundary `#[repr(C)]`; use `#[repr(transparent)]` for newtype handle
  wrappers so the ABI is identical to the inner type.
- **Ownership is explicit and one-directional**: document who allocates and who frees. Never free a
  pointer with a different allocator than the one that produced it (no `free()` on a `Box`, no
  `Box::from_raw` on C-`malloc`'d memory).
- Strings: use `CString` (owns a nul-terminated buffer; errors on interior nul) and `CStr` (borrowed
  view). A classic bug is a dangling pointer from a temporary:

```rust
// BUG: the CString is dropped at the end of this statement; `p` dangles immediately.
let p = CString::new(user)?.as_ptr();
// OK: bind the owner, keep it alive across the call.
let c = CString::new(user)?;
unsafe { ffi_use(c.as_ptr()) };
```

- Bind foreign symbols in `extern "C"` blocks (themselves `unsafe` to call); keep the raw bindings in
  a small `sys`-style module and expose a safe wrapper above it.

## Panics across FFI

- A Rust `panic!` must not unwind into foreign frames. As of Rust 1.81 an unwinding panic that reaches
  a plain `extern "C"` boundary **aborts the process** (previously UB).
- For any Rust callback invoked by C, wrap the body in `std::panic::catch_unwind` and convert a caught
  panic into an error code — do not let it reach the boundary.
- Use the `extern "C-unwind"` ABI only when you deliberately want unwinding to cross languages
  (e.g. interop with C++ exceptions or `longjmp`).

## Verification

- `cargo +nightly miri test` interprets your code and flags UB: OOB access, use-after-free, invalid
  values, data races, alignment and **provenance** violations, and leaks. Tighten with
  `MIRIFLAGS=-Zmiri-strict-provenance`. Miri cannot run real FFI, inline asm, or most syscalls.
- For FFI-heavy code Miri can't cover, build with a sanitizer:
  `RUSTFLAGS="-Zsanitizer=address" cargo +nightly test` (also `thread`, `memory`, `leak`).
- Keep `cargo clippy` clean; enable the unsafe-related lints listed above.

## Review checklist

- Every `unsafe fn` has `# Safety`; every `unsafe` block has a proving `// SAFETY:` comment.
- Invariants (non-null, aligned, in-bounds for the full span, initialized, unique `&mut`, lifetime)
  are actually guaranteed by the caller-visible API, not merely assumed.
- No reference to uninitialized memory; `MaybeUninit` + `&raw mut` used for partial init.
- No integer-to-pointer casts fabricating provenance; `transmute` justified or replaced.
- FFI types are `#[repr(C)]`/`transparent`; allocation ownership is documented and consistent.
- Callbacks into Rust from C are `catch_unwind`-guarded; ABI is `extern "C"` (or `C-unwind` on purpose).
- `unsafe` is exercised under Miri and/or a sanitizer in CI.
