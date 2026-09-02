# Measurement Workflow

Use this reference when a Rust performance claim needs a real baseline.

## Start with the symptom

- Define the metric: latency, throughput, alloc count, heap size, CPU time, lock wait, or tail latency
- Reproduce the issue with a stable workload before changing code
- Prefer release-mode measurements unless debug behavior is the actual problem

## Benchmark hygiene

- Use Criterion for stable benchmark comparisons and statistics
- Use `black_box` around benchmark inputs to avoid dead-code elimination
- Compare before vs after under the same environment
- Run enough iterations to smooth noise; do not trust a single lucky run

## Release-profile basics

- Measure optimized code with `cargo bench` or `cargo run --release`
- Tune release settings only after confirming they matter for the workload
- Record what changed so future regressions have a baseline to compare against

## Release-profile knobs

Defaults for `[profile.release]` are `opt-level = 3`, `lto = false`, `codegen-units = 16`,
`panic = "unwind"`, `overflow-checks = false`. Change these one at a time and re-benchmark — each
trades compile time (or behavior) for runtime.

```toml
[profile.release]
lto = "fat"          # cross-crate inlining; "thin" gets most of the win far cheaper to compile
codegen-units = 1    # more optimization, slower build; pairs with LTO
panic = "abort"      # smaller/slightly faster, but disables unwinding and catch_unwind
strip = "symbols"    # smaller binary; keep symbols when you still need to profile
```

- `-C target-cpu=native` (via `RUSTFLAGS` or `.cargo/config.toml`) lets codegen use the host's
  instruction set — only when the binary won't run on older/other CPUs.
- Use a faster linker (`lld`/`mold`) when available; it cuts link time with no runtime downside.
- For size instead of speed: `opt-level = "z"` (or `"s"`), plus `lto`, `codegen-units = 1`,
  `panic = "abort"`, `strip`.
- Once the knobs above are measured and exhausted, escalate to `-C target-cpu`, PGO, or BOLT —
  see `compiler-and-build-tuning.md`.
- For security-sensitive builds, keep `overflow-checks = true` in release despite the cost.

Note: `cargo bench` uses the `bench` profile, which inherits from `release`; benchmark with the same
profile knobs you intend to ship.

## Detecting regressions in CI

Wall-clock benchmarks are too noisy for CI. Deterministic alternatives:

- `iai-callgrind`: counts executed instructions (and L1/L2/RAM accesses) under Valgrind
  Callgrind — near-zero run-to-run variance, ideal for CI gates; ~10x slowdown per benchmark and
  Valgrind serializes threads, so it is for single-threaded hot paths, not parallel throughput.
- `divan`: lightweight Criterion alternative — benchmarks collocate in `#[cfg(test)]`-style
  modules, faster iteration, built-in allocation counts and thread-contention insights.
- `criterion --save-baseline` + `--baseline` to compare a run against a stored reference instead
  of only the previous run.
- `hyperfine`: A/B two CLI binaries end-to-end (includes startup/IO noise), when whole-binary
  latency is the metric.

Practical note: keep benchmark environment (CPU governor, workload shape, feature flags) stable across before/after runs.
