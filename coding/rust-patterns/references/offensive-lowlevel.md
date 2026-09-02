# Offensive and Low-Level Rust

Load this for offensive tooling in Rust: RE-resistance, string obfuscation, memory protection,
`no_std` entry points, inline asm/syscalls, or malware-style modular architecture. Safety rules for
the `unsafe` work itself live in `unsafe-and-ffi.md`; secret-handling rules in `security-review.md`.

## Contents

- [RE-resistance baseline](#re-resistance-baseline)
- [String and data obfuscation](#string-and-data-obfuscation)
- [Memory protection](#memory-protection)
- [Build-time diversification](#build-time-diversification)
- [no_std / no_main binaries](#no_std--no_main-binaries)
- [Inline assembly and direct syscalls](#inline-assembly-and-direct-syscalls)
- [Offensive architecture patterns](#offensive-architecture-patterns)

## RE-resistance baseline

Rust release binaries often statically link much of the crate graph, and generic instantiations
spawn specialized copies (monomorphization). Symbols are mangled under the Rust scheme. A trivial
program can still yield thousands of functions; attacker logic drowns in library code.

Microsoft's RIFT (REcon 2025, `github.com/microsoft/RIFT`, MSTIC blog) closes the gap with FLIRT
signatures and metadata extraction — assume library code **is** separable from yours and strip
signal anyway: generic `std`/crate names tell an analyzer exactly what to filter.

## String and data obfuscation

- `obfstr` / `litcrypt` — compile-time XOR of literals, decrypted at the use site; set the key via
  env (`LITCRYPT_ENCRYPT_KEY`) so source stays clean. Use on IOC-y strings (URLs, mutexes, paths).
- Verify on the **release** artifact: debug builds and `panic = "unwind"` paths can leave plaintext
  behind. Check with `strings`/`binwalk` before shipping.
- Do not obfuscate what you must not print: keep `Debug` impls off secret-carrying types (rule in
  `security-review.md`).

## Memory protection

- Flip page permissions around sensitive buffers with `windows-sys`
  (`Win32::System::Memory::VirtualProtect`) or `libc::mprotect`, e.g. RW→NoAccess/RX when idle.
- `mlock` (or `VirtualLock` on Windows) keeps secrets out of swap.
- Wipe with `zeroize`/`Zeroizing<_>` after use (canonical rule in `security-review.md`).

## Build-time diversification

- Cargo features + `cfg!` include/exclude capability modules per build; a feature matrix yields
  diverse binaries from one codebase.
- `build.rs` injects per-build keys (feed to `obfstr`/`litcrypt` at compile time) — keep generated
  keys out of git.
- Proc macros can rewrite identifiers/literals; `const` generics parameterize per-build values.
- `garble` (rustc-driver obfuscator) covers control-flow and identifier renaming when the plain
  toolchain is not enough.

Release-profile floor for shipped artifacts:

```toml
[profile.release]
strip = true
lto = "fat"
codegen-units = 1
panic = "abort"
```

## no_std / no_main binaries

`#![no_std]` + `#![no_main]` removes the standard runtime; you provide the entry point and panic
handler. Tiny outputs, no runtime baggage.

```rust
#![no_std]
#![no_main]
use core::panic::PanicInfo;

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! { loop {} }

#[unsafe(no_mangle)]
pub extern "C" fn _start() -> ! { loop {} }
```

- Compile with `panic = "abort"`; without unwinding the handler still must exist.
- Only `core` is available — allocation needs a custom allocator; plan `alloc` accordingly.
- On Windows, `#![windows_subsystem = "windows"]` is a cheaper middle step than full `no_std`.

## Inline assembly and direct syscalls

- `core::arch::asm!` takes plain/raw types in registers only; cast structured results back after the
  block. Declare clobbers (`out`, `options`) correctly — `noreturn` needs no clobber list.
- Direct-syscall patterns (Hell's Gate family) resolve syscall numbers at runtime by walking the
  PEB/export table, then issue `syscall` from inline asm. Keep the resolver and the asm in a small
  private module with a safe facade.
- Prefer `windows-sys` feature-gated imports over hand bindings; manually `#[repr(C)]`-mirroring PE
  headers is error-prone (layout rules: `unsafe-and-ffi.md`).

```rust
use core::arch::asm;
// Linux x86_64 exit(0): syscall wrapper — clobber-free because noreturn.
unsafe { asm!("syscall", in("rax") 60u64, in("rdi") 0i64, options(noreturn)) }
```

## Offensive architecture patterns

Patterns distilled from real Rust families (BlackCat/ALPHV, Hive analyses):

- **Capability-oriented modular monolith**: one module per capability (encrypt, spread, exfil,
  persistence) behind a small trait; a registry assembles the build from a feature matrix. See
  `dynamic-dispatch-and-plugins.md` for the registry/dispatch mechanics. Shape seen in real families
  (BlackCat, Hive):

  ```text
  src/
  ├── runtime/        # dispatcher, scheduler, state
  ├── protocol/       # typed Command/Response (serde enums)
  ├── capabilities/   # one module per capability
  ├── platform/       # #[cfg(target_os)] per-OS backends
  └── ffi/            # the unsafe boundary
  ```
- **Typed command dispatcher**: a `serde` enum of operator commands, one exhaustive `match`; the
  capability surface is auditable in one file.
- **Pipeline + worker pool + supervisor**: bounded channels give backpressure; a supervisor restarts
  failed workers and aggregates results. Concurrency mechanics: `concurrency.md`.
- **Platform abstraction modules**: `#[cfg(target_os = ...)]` platforms return the same public
  types; the shared path stays platform-free and the per-OS modules isolate `windows-sys`/syscall
  differences.
- **Unsafe islands**: a safe core with a tiny `unsafe` FFI boundary — the boundary module owns
  invariants, the rest of the codebase never sees raw pointers.
- **Config-driven behavior**: encrypted runtime config (BlackCat embeds an encrypted config blob
  gated on an access token) — capabilities activate from validated config, not literal flags.
- **State machine / typestate**: model the lifecycle as an `enum State` driven by an exhaustive
  `match`; when transitions must not be bypassable, use the typestate pattern
  (`Runtime<Uninitialized>` consumed to produce `Runtime<Running>`) so illegal transitions are
  compile errors.
- **Actor-style workers**: each long-lived component owns its state and communicates only through a
  message channel (`Receiver<Message>` loop in a spawned task); the supervisor holds the senders.
  Fits task pools and per-connection handlers — channel mechanics in `concurrency.md`.
