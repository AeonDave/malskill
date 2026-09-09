# Compiler and Runtime Tuning

Use when profiling and code-level fixes have landed and you want the last runtime/build tuning. Do
the profile-and-benchstat cycle in `benchmarks.md` first — these knobs are the icing, not the cake.

## Contents

- [Escalation order](#escalation-order)
- [GOGC and GOMEMLIMIT](#gogc-and-gomemlimit)
- [GOMAXPROCS](#gomaxprocs)
- [Green Tea GC and cgo](#green-tea-gc-and-cgo)
- [Threads, timers, SIMD](#threads-timers-simd)
- [Profile-guided optimization](#profile-guided-optimization)
- [Build flags for shipped binaries](#build-flags-for-shipped-binaries)
- [GODEBUG runtime knobs](#godebug-runtime-knobs)

## Escalation order

1. Baseline benchmark + pprof; make one code-level fix, remeasure with `benchstat`.
2. Tune `GOGC` / `GOMEMLIMIT` when the profile shows GC-bound work or memory pressure.
3. Enable PGO (Go 1.21+) — cheap once you have a representative profile.
4. Ship the binary with `-trimpath -ldflags="-s -w"` and, if scale demands it, tune the compiler
   inliner or force GC parameters via `GODEBUG`.

Every step is measured; skipping the measurement step is why "the optimization didn't help".

## GOGC and GOMEMLIMIT

- `GOGC` (default `100`): controls when the GC runs, expressed as heap growth over live-set before
  the next cycle. Raising to `200` or `off` reduces GC CPU at the cost of RSS; useful for
  batch/CLI where latency doesn't matter.
- `GOMEMLIMIT` (Go 1.19+): a **soft** memory limit for the whole runtime (heap + stacks + runtime
  overhead, minus off-heap sources like cgo/mmap). The runtime tightens `GOGC` behavior as usage
  approaches the limit and returns memory to the OS more aggressively.
- The two work together: a common shape is `GOGC=off GOMEMLIMIT=6GiB` — grow the heap freely until
  the memory budget, then GC hard. Prevents the classic OOM in a bursty service with a soft cap on
  the container.
- The runtime caps GC CPU at ~50% when close to `GOMEMLIMIT` to avoid a GC death spiral; the
  `/gc/limiter/last-enabled:gc-cycle` metric reports when that happened.

## GOMAXPROCS

Go 1.25+ (still the 1.27 default): if `GOMAXPROCS` is **unset**, the runtime picks
`min(logical CPUs, affinity, Linux cgroup CPU quota)`, never below 2 unless the machine/affinity
is below 2. Fractional quotas round **up**. Kubernetes **limits** map to the cgroup quota;
**requests** are ignored. The runtime refreshes at most once per second (`updatemaxprocs`).

Do **not** set `GOMAXPROCS` or call `runtime.GOMAXPROCS` in containers just to "match the limit"
— that **disables** cgroup awareness and periodic updates. Drop `automaxprocs` on 1.25+ unless
you are pinning a value on purpose.

- Need the default back after an explicit set: `runtime.SetDefaultGOMAXPROCS()` (Go 1.25+).
- Opt out of cgroup / updates: `GODEBUG=containermaxprocs=0` and/or `updatemaxprocs=0` (Linux
  cgroup path only for the former). Language version ≤1.24 keeps the old `NumCPU` default.
- `errgroup.SetLimit(runtime.GOMAXPROCS(0))` remains a valid fan-out cap; read the current value,
  don't write it.

## Green Tea GC and cgo

Go 1.26+ uses the Green Tea GC by default. GC-heavy programs typically see **10–40% less GC
overhead** (not wall-clock of the whole process). Extra ~10% GC-overhead cut is documented on
Ice Lake / Zen 4+ via vector scan. Do **not** add these percentages to the 1.27 allocator or
cgo numbers.

Go 1.26 allowed `GOEXPERIMENT=nogreenteagc`; Go 1.27 release notes do not document that opt-out.
If a GC regression appears, measure with `GODEBUG=gctrace=1` and file an issue — don't cargo-cult
the 1.25 experiment flag (`greenteagc`) on 1.26+.

Go 1.26 cut **baseline cgo call overhead ~30%**. Calls still bind an M; batch them. Details of
the cgo pointer rules are in `golang-patterns` `unsafe-cgo.md`.

Go 1.27 size-specialized malloc: some allocations **under 80 bytes** cost up to ~30% less;
allocation-heavy programs see about **~1%** overall. Binary grows ~60 KB.
`GOEXPERIMENT=nosizespecializedmalloc` disables it (expected gone in 1.28).

## Threads, timers, SIMD

- `runtime.LockOSThread` pins the goroutine to its OS thread. Use for C APIs that store
  thread-local state, not to "force parallelism". Unlock with `UnlockOSThread` in the same
  goroutine. Extra cgo threads are still expensive after the 1.26 overhead cut.
- Timer/ticker channels are unbuffered as of `go 1.23` and **cannot** be reverted in Go 1.27
  (`asynctimerchan` removed). See `golang-patterns` `concurrency.md`.
- Experimental SIMD (`GOEXPERIMENT=simd`): Go 1.26 `simd/archsimd` (arch-specific);
  Go 1.27 also `simd` (portable, size-agnostic, emulated where needed). API is **unstable**.
  Use portable `simd` for numeric kernels you must ship across amd64/arm64/wasm; drop to
  `archsimd` only for a width/instruction the portable subset lacks. Always keep a scalar
  `//go:build !goexperiment.simd` path until the experiment graduates.
- `runtime/metrics` (Go 1.26+) exposes `/sched/goroutines-*`, `/sched/threads:threads`,
  `/sched/goroutines-created:goroutines` — prefer these over scraping goroutine profiles for
  dashboards.

## Profile-guided optimization

Go 1.21+ enables PGO when a `default.pgo` sits next to the `main` package. Typical wins are modest
(2–7% on representative workloads) but essentially free once the profile pipeline exists.

```bash
# 1. Build unoptimized, run against production-shaped load.
go build -o svc ./cmd/svc
./svc &   # exercise it

# 2. Capture a CPU profile from the running process.
curl -o cpu.pprof 'http://127.0.0.1:6060/debug/pprof/profile?seconds=60'

# 3. Move it in and rebuild; `-pgo=auto` (default in 1.21+) picks it up.
mv cpu.pprof cmd/svc/default.pgo
go build -o svc ./cmd/svc

# Confirm PGO was applied.
go version -m svc | grep pgo
```

- Commit `default.pgo` for reproducible builds.
- Refresh it when the workload shifts materially; a stale profile pessimizes the paths you care
  about.
- PGO composes with everything else here — enable it alongside `-trimpath`/`-ldflags`.

## Build flags for shipped binaries

For released or offensive-tool artifacts:

```bash
CGO_ENABLED=0 go build \
  -trimpath \
  -ldflags="-s -w -buildid=" \
  -pgo=auto \
  -o payload ./cmd/payload
```

- `-trimpath` — removes local filesystem paths from `.debug_line`, `runtime.FuncForPC`, and error
  strings; also a step toward reproducible builds.
- `-ldflags="-s -w"` — drops symbol table (`-s`) and DWARF (`-w`); ~30% smaller binary and less
  attacker/analyst signal. Combine with `-buildid=` to zero out the Go build ID for reproducibility.
- `CGO_ENABLED=0` — pure-Go binary, no libc; cross-compiles cleanly to any `GOOS`/`GOARCH`. See
  `golang-patterns/references/unsafe-cgo.md` for `netgo`/`osusergo` tags when cgo is unavoidable but
  static linking is still required.

## GODEBUG runtime knobs

Runtime observability first, tuning second. Set via env var; do not hardcode.

- `GODEBUG=gctrace=1` — one line per GC cycle: pause, CPU %, heap sizes. First stop for GC-bound
  investigations.
- `GODEBUG=schedtrace=1000,scheddetail=1` — scheduler dump every 1 s; use when goroutines look
  stalled or scheduler-bound.
- `GODEBUG=tracebacklabels=0` — Go 1.27+ modules include pprof goroutine labels in traceback
  headers; disable if labels may contain secrets.
- `GODEBUG=allocfreetrace=1` — extremely verbose per-alloc trace; for narrow reproducers only.
- `GODEBUG=madvdontneed=1` — makes the runtime return memory to the OS eagerly (RSS drops faster
  post-load). Trades TLB refills for smaller RSS; measure both.
- `GODEBUG=cgocheck=2` — deep validation of Go pointers passed to C; run under this when auditing
  a cgo boundary.

These are diagnostics and one-off knobs, not permanent config — pin the specific setting once you
have measurable evidence, then remove it.
