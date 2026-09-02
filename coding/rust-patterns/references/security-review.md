# Security Review

Use this reference when auditing Rust source for security bugs: reviewing a crate you don't own,
hardening code against untrusted input, or checking a dependency tree. For writing/reviewing the
`unsafe` internals themselves, see `unsafe-and-ffi.md`. For fuzzing and sanitizers, see the
`rust-testing` skill's `fuzzing-and-sanitizers.md`.

## Contents

- [Orient in an unfamiliar crate](#orient-in-an-unfamiliar-crate)
- [Grep patterns for risky constructs](#grep-patterns-for-risky-constructs)
- [Denial of service](#denial-of-service)
- [Integer handling](#integer-handling)
- [Untrusted input](#untrusted-input)
- [Secrets and crypto](#secrets-and-crypto)
- [Supply chain](#supply-chain)
- [What to hand off](#what-to-hand-off)

## Orient in an unfamiliar crate

- `cargo tree` / `cargo tree -i <crate>` — full dependency graph and reverse "who pulls this in".
- `cargo doc --open` and rust-analyzer (go-to-definition, find-references, call hierarchy, list
  implementors) to trace how untrusted input flows to sensitive sinks.
- Identify **trust boundaries** first: `main`/`lib.rs` entry points, network/`serde`/parser inputs,
  `pub` API surface, `build.rs`, and every `extern`/FFI edge. Attacker-controlled data starts there.

## Grep patterns for risky constructs

Fast first pass with ripgrep; each hit is a lead, not a verdict:

```
rg -n "unsafe|transmute|from_raw|set_len|get_unchecked|assume_init"   # memory-safety escapes
rg -n "unwrap\(|expect\(|panic!|unreachable!|todo!|\[[0-9a-z_]+\]"     # panic / DoS on bad input
rg -n "Command::new|process::|std::env|Stdio"                          # command / env exposure
rg -n "std::fs|File::open|read_to_end|read_to_string|create|remove"    # filesystem sinks
rg -n "PathBuf|\.join\(|canonicalize"                                  # path traversal candidates
rg -n "from_utf8_unchecked|mem::forget|ManuallyDrop"                   # soundness / leak risks
rg -n "deserialize|from_str|from_slice|bincode|serde_json::from"       # deserialization entry points
```

## Denial of service

Rust prevents memory corruption but not resource exhaustion or panics-as-crash:

- **Panics on attacker input** are a DoS in most services: `unwrap`/`expect`, slice indexing `v[i]`,
  `assert!`, integer division by zero, `unreachable!` reached by malformed data. Use `get()`,
  `checked_*`, `?`, and total matches on untrusted paths.
- **Unbounded allocation**: `Vec::with_capacity(n)` / `String::with_capacity(n)` where `n` comes from
  the wire; `read_to_end`/`read_to_string` without a cap. Bound with `Read::take(limit)` and validate
  lengths before reserving.
- **Amplification / bombs**: decompression (zip/gzip) and nested-structure parsers can expand far
  beyond input size — cap output size and nesting depth.
- **Unbounded recursion** in recursive descent parsers or recursive data — enforce a depth limit.
- **Regex** built from untrusted patterns, or catastrophic backtracking — the `regex` crate is
  linear, but ReDoS applies to backtracking engines and user-supplied patterns.

## Integer handling

- Arithmetic **panics in debug** but **wraps in release** by default — a silent wrap can bypass a
  length or bounds check. For security-sensitive builds set `overflow-checks = true` in
  `[profile.release]`, and make intent explicit with `checked_*`, `saturating_*`, or `wrapping_*`.
- `as` casts **truncate** silently (`300u32 as u8 == 44`). Prefer `TryFrom`/`try_into` and handle the
  error when narrowing a size/length/index derived from input.

## Untrusted input

- **Path traversal**: reject paths containing `..` or absolute components, then `canonicalize()` and
  verify the result is still under the intended root prefix (`starts_with`). Do the check on the
  resolved path, not the raw string.
- **Command injection**: never build a shell string. Use `Command::new(prog).args([...])` with a
  fixed program and separate arguments; do not pass user data to `sh -c`/`cmd /C`. Sanitize/allowlist
  when the program name itself is dynamic.
- **Deserialization**: constrain formats — set size/depth limits (e.g. `bincode` config limits),
  avoid formats that can instantiate arbitrary types, and validate invariants after decode rather
  than trusting them. Treat `serde` inputs as attacker-controlled.
- **SSRF / URL handling**: validate host/scheme against an allowlist after parsing; block internal
  addresses when fetching user-supplied URLs.
- **TOCTOU**: prefer open-then-operate on the returned handle over check-path-then-open-path.

## Secrets and crypto

- Wipe key material with `zeroize` (`Zeroizing<_>`) or hold it in `secrecy::Secret<_>`; never derive
  `Debug` on a type that would print a secret.
- Compare secrets/MACs/tokens in constant time with `subtle::ConstantTimeEq`, not `==`.
- Don't roll your own crypto; use vetted crates (`ring`, RustCrypto). Seed keys/nonces from a CSPRNG
  (`getrandom`, `rand::rngs::OsRng`) — not `thread_rng`/`SmallRng` for key generation.
- Keep secrets out of logs, error messages, and panic payloads.

## Supply chain

- `cargo audit` — scans `Cargo.lock` against the RustSec advisory DB. In CI it exits 0 even on
  findings unless you fail explicitly (`cargo audit --deny warnings`).
- `cargo deny check` — one `deny.toml` enforcing advisories, license policy, banned crates, duplicate
  versions, and allowed sources. Good default gate for most projects.
- `cargo vet` / `cargo crev` — human audit records; `cargo vet import mozilla`/`google` reuses large
  shared audit pools. Worth the friction for crypto/firmware/financial code.
- `cargo geiger` — counts `unsafe` usage across the dependency tree to focus review.
- Pin with a committed `Cargo.lock` and build `--locked`; review `build.rs` and proc-macro crates —
  they run arbitrary code at build time and are a prime supply-chain vector.

## What to hand off

For each finding: the source location, the untrusted-input path that reaches it, the concrete impact
(crash/DoS, memory unsafety, secret leak, RCE), and a minimal fix or reproducer. Separate *proven*
issues (repro or Miri/fuzz evidence) from *suspected* ones needing confirmation.
