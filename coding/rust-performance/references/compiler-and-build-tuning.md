# Compiler and Build Tuning

Use when the `[profile.release]` knobs in `measurement-workflow.md` are measured and not enough,
or when shipping a binary tuned for a known deployment CPU. Escalate one step at a time and
re-benchmark at each step.

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

## Faster linkers (dev-loop only)

`mold` (Linux/macOS) or `lld` cut link times on large crates with zero runtime effect — a
build-latency fix, not a runtime optimization.
