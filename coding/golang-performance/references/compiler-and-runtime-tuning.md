# Compiler and Runtime Tuning

Use when profiling and code-level fixes have landed and you want the last runtime/build tuning. Do
the profile-and-benchstat cycle in `benchmarks.md` first — these knobs are the icing, not the cake.

## Contents

- [Escalation order](#escalation-order)
- [GOGC and GOMEMLIMIT](#gogc-and-gomemlimit)
- [GOMAXPROCS](#gomaxprocs)
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

- Defaults to the number of logical CPUs. Under Linux cgroup quotas, that number can be higher than
  the effective CPU quota — a container with 2 vCPUs but a quota of 1 will over-schedule.
- Set explicitly in containers: `GOMAXPROCS=$(nproc)` or link `go.uber.org/automaxprocs` to read the
  cgroup and set it at `init`. Fixes runaway scheduler contention on constrained hosts.

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
- `GODEBUG=allocfreetrace=1` — extremely verbose per-alloc trace; for narrow reproducers only.
- `GODEBUG=madvdontneed=1` — makes the runtime return memory to the OS eagerly (RSS drops faster
  post-load). Trades TLB refills for smaller RSS; measure both.
- `GODEBUG=cgocheck=2` — deep validation of Go pointers passed to C; run under this when auditing
  a cgo boundary.

These are diagnostics and one-off knobs, not permanent config — pin the specific setting once you
have measurable evidence, then remove it.
