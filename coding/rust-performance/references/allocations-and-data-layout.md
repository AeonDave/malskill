# Allocations and Data Layout

Use this reference when Rust code is losing time to cloning, heap churn, or poor locality.

## Reduce allocation churn

- Pre-allocate with `Vec::with_capacity` or `String::with_capacity` when sizes are predictable
- Reuse buffers instead of recreating them in tight loops
- Borrow data instead of cloning it when ownership is unnecessary
- Avoid building intermediate collections if a streaming iterator pipeline is enough

## Data-layout wins

- Favor contiguous data structures (`Vec`, slices) when iteration is hot
- Keep frequently accessed fields close together when structure layout matters
- Choose representations that match the workload: arrays for fixed-size hot data, enums for tight state machines
- Introduce `SmallVec` / `ArrayVec` only with evidence that small inline storage helps

## Global allocator choice

Swapping the allocator is one line (`#[global_allocator]`) but only pays when the profile shows
allocation-bound hot paths — measure with `dhat`/`heaptrack` first.

- Default: the system allocator (libc `malloc`); fine for single-threaded or low-churn code.
- `mimalloc` crate (`MiMalloc` as `#[global_allocator]`): general-purpose, performance-oriented;
  often helps under many small short-lived allocations across threads. Its `secure` feature adds
  measurable hardening overhead, so benchmark before enabling it on hot paths.
- `tikv-jemallocator` (`Jemalloc`): successor of the deprecated `jemallocator`; Linux/macOS
  targets — skip on `msvc`. Tunable/observable via `tikv-jemalloc-ctl`.
- Re-benchmark both allocator RSS and throughput: some workloads fragment or peak worse under a
  swapped allocator.

## SIMD

Escalate only after a profile shows a vectorizable inner loop:

1. Autovectorization first: iterator chains over slices, `chunks_exact` (drops bounds checks),
   power-of-two loop counters. Note the optimizer will not reorder float ops — it must preserve
   observable results.
2. `wide` crate: stable, portable 128/256-bit SIMD that falls back to autovectorizable code.
3. `std::simd` (`portable_simd`): nightly-only — still unstable as of 2025.
4. Raw intrinsics (`core::arch`) with `#[target_feature(enable = "...")]` + runtime dispatch:
   last resort, `unsafe`, needs multiversioning for distributed binaries.

## Hashers and containers

- The default hasher is safe but not always fastest
- Use faster hashers only when collision resistance is not part of the requirement
- Re-check performance after container changes; the “faster” structure on paper may not win for the real dataset

## Cross-references

- Hot per-thread atomics/fields landing on one cache line: see `concurrency-and-throughput.md`
  (false sharing).
- Build-wide instruction-set tuning: see `compiler-and-build-tuning.md` (`target-cpu`, SIMD
  dispatch alternatives).
