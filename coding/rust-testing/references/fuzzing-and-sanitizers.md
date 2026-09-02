# Fuzzing and Sanitizers

Use this reference when example and property tests aren't enough: finding panics, memory-safety bugs,
and undefined behavior on arbitrary input — especially for parsers, decoders, deserializers, `unsafe`
internals, and FFI-facing code. Property tests (`proptest`, see `property-snapshot-and-mocks.md`) are
in-process and deterministic; fuzzing is coverage-guided and runs for as long as you let it.

## Contents

- [What to fuzz and the oracle](#what-to-fuzz-and-the-oracle)
- [cargo-fuzz (libFuzzer)](#cargo-fuzz-libfuzzer)
- [Writing harnesses](#writing-harnesses)
- [Corpus, minimization, reproduction](#corpus-minimization-reproduction)
- [AFL via cargo-afl](#afl-via-cargo-afl)
- [Miri for undefined behavior](#miri-for-undefined-behavior)
- [Standalone sanitizers](#standalone-sanitizers)
- [Turning findings into regressions](#turning-findings-into-regressions)

## What to fuzz and the oracle

- Best targets take untrusted bytes and produce structure: `&[u8]`/`&str` → parsed value, format
  decoders, `serde` inputs, protocol framing, anything with `unsafe` or FFI in the path.
- A fuzzer needs an **oracle** — something that decides a run is bad. Free oracles: any panic, an
  ASan/UBSan report, a debug assertion. Add stronger ones inside the harness: round-trip equality
  (`decode(encode(x)) == x`), agreement with a reference impl, or invariant checks.
- On fuzzed paths, a panic *is* the bug — do not "fix" it with `#[should_panic]`; make the code
  return an error instead.

## cargo-fuzz (libFuzzer)

`cargo-fuzz` is the default Rust fuzzer; it wraps libFuzzer through `libfuzzer-sys`. Building fuzz
targets needs **nightly** (for coverage/sanitizer flags); your crate's production code stays on stable.

```bash
cargo +nightly install cargo-fuzz
cargo fuzz init                 # creates the fuzz/ sub-crate (#![no_main])
cargo fuzz add parse_url        # new target at fuzz/fuzz_targets/parse_url.rs
cargo +nightly fuzz run parse_url    # builds with ASan on, then fuzzes
```

- AddressSanitizer is enabled automatically. Add UBSan with `--sanitizer address,undefined`; disable
  with `--sanitizer none` for pure logic/panic fuzzing.
- Cap input size with `-- -max_len=4096`; bound a CI run with `-- -runs=1000000` or
  `-- -max_total_time=60`.

## Writing harnesses

Keep the harness thin — it maps raw bytes to your API and lets the oracle fire.

```rust
#![no_main]
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    // Must not panic for any input; parse errors are expected and fine.
    let _ = mycrate::parse(data);
});
```

For typed, structure-aware inputs, use the `arbitrary` crate so the fuzzer explores valid-shaped data
instead of wasting runs on bytes your parser rejects immediately:

```rust
use arbitrary::Arbitrary;

#[derive(Arbitrary, Debug)]
struct Op { key: String, value: Vec<u8> }

fuzz_target!(|ops: Vec<Op>| {
    let mut db = mycrate::Db::new();
    for op in ops { db.apply(op); }        // assert invariants inside apply/here
});
```

## Corpus, minimization, reproduction

- Seed `fuzz/corpus/<target>/` with real, valid samples — coverage grows far faster from good seeds.
- A crash is written to `fuzz/artifacts/<target>/`. Reproduce deterministically:
  `cargo fuzz run <target> fuzz/artifacts/<target>/crash-<hash>`.
- Shrink a crasher with `cargo fuzz tmin <target> <crash-file>`; shrink the corpus with
  `cargo fuzz cmin <target>`.
- Add a format-aware dictionary with `-- -dict=keywords.dict` for keyword-heavy grammars.

## AFL via cargo-afl

Use `cargo-afl` (afl.rs, an AFL++ frontend) when you want multi-core fuzzing, persistent-mode on a
non-Cargo target, or AFL's mutators:

```bash
cargo install cargo-afl
cargo afl build                              # instrumented build
cargo afl fuzz -i seeds/ -o out/ target/debug/mytarget
```

Otherwise cargo-fuzz is the lower-friction default.

## Miri for undefined behavior

Fuzzing finds crashers; Miri proves whether a path is UB. Run the suite (or targeted tests that
exercise `unsafe`) under the interpreter:

```bash
cargo +nightly miri test
```

It catches out-of-bounds access, use-after-free, invalid values, data races, misalignment, and
provenance violations. It cannot execute real FFI, inline asm, or most syscalls — cover those with a
sanitizer build instead.

## Standalone sanitizers

For FFI/unsafe code Miri can't run, instrument a normal test build (nightly-only):

```bash
RUSTFLAGS="-Zsanitizer=address" cargo +nightly test   # ASan: OOB, use-after-free, leaks
```

Swap `address` for `thread` (data races), `memory` (uninitialized reads), or `leak`. Sanitizers run
at near-native speed and complement fuzzing, which supplies the inputs that trip them.

## Turning findings into regressions

- Commit the minimized corpus so future runs don't rediscover the same coverage from scratch.
- Convert each fixed crash into a fast deterministic unit test that feeds the exact bytes and asserts
  the graceful outcome — this guards the fix without a fuzzer running.
- Keep fuzzing as a scheduled/long-running job, not a PR gate; run Miri and sanitizer builds in a
  separate nightly CI lane because they are slow.
