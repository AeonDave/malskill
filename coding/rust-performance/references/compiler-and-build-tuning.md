# Compiler and Build Tuning

Use when the `[profile.release]` knobs in `measurement-workflow.md` are measured and not enough,
or when shipping a binary tuned for a known deployment CPU. Escalate one step at a time and
re-benchmark at each step.

## Contents

- [Escalation order](#escalation-order)
- [target-cpu and target features](#target-cpu-and-target-features)
- [PGO](#pgo)
- [BOLT](#bolt)
- [Faster linkers](#faster-linkers)
- [Compile graph: cargo --timings](#compile-graph-cargo---timings)
- [Nightly compile-time experiments](#nightly-compile-time-experiments)

## Escalation order

1. Baseline: plain `--release`, measured
2. Profile knobs (`lto`, `codegen-units`, `panic`, `strip`) — see `measurement-workflow.md`
3. `-C target-cpu` for the deployment target
4. PGO (profile-guided optimization)
5. BOLT (post-link binary optimization, Linux)

## target-cpu and target features

`-C target-cpu=native` lets LLVM use the host's full instruction set, including wider SIMD for
autovectorized loops.

```toml
# .cargo/config.toml — applies to every build of this project
[target.x86_64-unknown-linux-gnu]
rustflags = ["-C", "target-cpu=native"]
```

- Only for binaries that run on the build machine or identical hardware; a `native` build crashes
  (SIGILL) on older CPUs.
- For distributed binaries: prefer a baseline tier (`-C target-cpu=x86-64-v2` / `v3`) for the whole
  binary, or multiversion the few genuinely SIMD-bound functions with `#[target_feature(enable)]
  + unsafe` instead of raising the whole binary's baseline.
- When also using `cargo-pgo`, put custom flags under `[target.<triple>.rustflags]`, not
  `[build].rustflags` — `cargo-pgo` overrides the latter.

## PGO

PGO feeds rustc a runtime profile so inlining and branch layout match real usage. Gains depend
heavily on workload shape: sometimes it helps materially, sometimes it is noise, and a bad
training profile can regress the binary — measure, don't assume.

`cargo-pgo` (needs `rustup component add llvm-tools-preview` for `llvm-profdata`):

```bash
cargo pgo build        # instrumented binary at target/<triple>/release/<name>
# run the instrumented binary on a REPRESENTATIVE workload (real inputs, real branch patterns)
cargo pgo optimize     # rebuild using the collected profiles
```

Raw flags without the tool:

```bash
RUSTFLAGS="-Cprofile-generate=./pgo_data" cargo build --release
# run the binary on the training workload
RUSTFLAGS="-Cprofile-use=./pgo_data" cargo build --release
```

- A training workload that misrepresents production can make PGO output *slower* than plain
  release; if a regression appears, the profile, not PGO itself, is the suspect.
- PGO pays off on the final binary. Building a library with PGO does not carry to consumer
  binaries unless they are themselves built with PGO.

## BOLT

BOLT is a post-link optimizer that rewrites branch layout using recorded profiles. Driven by the
same tool (`cargo pgo bolt build` → run instrumented binary → `cargo pgo bolt optimize`);
optimized binary lands as `<name>-bolt-optimized`.

- Experimental; needs `llvm-bolt` and `merge-fdata` (build LLVM with `-DLLVM_ENABLE_PROJECTS="bolt"`
  or use a release artifact). Linux, hardware perf counters required.
- Composes with PGO via `cargo pgo bolt optimize --with-pgo`.
- Do NOT strip symbols from the release binary when using BOLT — it can cause linker errors.

## Faster linkers

Rust 1.90+ uses **LLD by default** on `x86_64-unknown-linux-gnu` (not a
dev-only opt-in). Expect faster links on large debug/incremental builds. If a
custom linker script or BFD-only flag breaks:

```toml
# .cargo/config.toml
[target.x86_64-unknown-linux-gnu]
rustflags = ["-C", "linker-features=-lld"]
```

`mold` / `lld` on other targets still cut **dev-loop** link time with zero
runtime effect. They are not a substitute for LTO/`codegen-units` on the
shipped binary.

## Compile graph: cargo --timings

`cargo build --timings` writes an HTML chart of crate-level parallelism. Use it
when **compile time** is the symptom (not runtime). A crate that stays red
("waiting") while others sit idle is the unit to split or to stop feeding a
proc-macro. This does not change generated code.

## Nightly compile-time experiments

Do **not** enable these on a stable MSRV or in release CI.

**Parallel rustc frontend** (`-Z threads=8`, nightly): Cargo book still marks
it experimental. Caps around 8 threads; can cut *frontend* time substantially
on large crates, with higher RAM. Default thread count remains 1.

```toml
# nightly only
[build]
rustflags = ["-Z", "threads=8"]
```

**Cranelift backend** (nightly component `rustc-codegen-cranelift-preview`):
faster **dev** codegen, worse runtime code. Not production-ready as of 1.98
(missing features on large graphs). Dev profile only:

```bash
rustup component add rustc-codegen-cranelift-preview --toolchain nightly
CARGO_PROFILE_DEV_CODEGEN_BACKEND=cranelift cargo +nightly build -Zcodegen-backend
```

Never set Cranelift on `[profile.release]`.
