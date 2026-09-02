# Unsafe, cgo, and Low-Level Boundaries

Use this reference when Go code crosses a low-level boundary: `unsafe.Pointer`, `reflect` layout
tricks, `syscall`/`golang.org/x/sys`, `cgo`, or when producing static/cross-compiled binaries for
offensive tooling. Security-audit rules for callers live in `security-review.md`.

## Contents

- [When you need unsafe](#when-you-need-unsafe)
- [unsafe.Pointer rules](#unsafepointer-rules)
- [Slice, string, and header helpers](#slice-string-and-header-helpers)
- [Alignment and size](#alignment-and-size)
- [Runtime pinning and finalizers](#runtime-pinning-and-finalizers)
- [syscall vs golang.org/x/sys](#syscall-vs-golangorgxsys)
- [cgo boundary](#cgo-boundary)
- [Static, stripped, and cross-compiled builds](#static-stripped-and-cross-compiled-builds)
- [Verification](#verification)
- [Review checklist](#review-checklist)

## When you need unsafe

Reach for `unsafe` only when the safe path cannot express it: FFI structs, hot-path zero-copy
between `[]byte` and `string`, atomic access to a field the runtime doesn't expose, mapping a
memory-mapped file or ioctl buffer. Every other `unsafe.Pointer` is a bug waiting for a Go release
to change the layout.

## unsafe.Pointer rules

`unsafe.Pointer` is only sound under the six patterns documented in `pkg.go.dev/unsafe`. The ones
you hit in practice:

- **Cast to `*T` and back** for a value the caller owns. The type on both sides must match the
  actual bytes; violating this is UB even if it "seems" to work.
- **Pointer + offset** via `unsafe.Add(p, off)` — clearer and safer than manual `uintptr` math.
  Never store `uintptr` between operations; the GC may move the object and your `uintptr` is now a
  stale integer.
- **Reading pointer as `uintptr` only inside a single call expression** (e.g. `syscall.Syscall(...,
  uintptr(unsafe.Pointer(&x)), ...)`). The `uintptr` must not survive past the call.
- **Conversion between compatible layouts** requires *identical* size and layout — use
  `unsafe.Sizeof` and `unsafe.Offsetof` to prove it, or use `//go:notinheap` types.

## Slice, string, and header helpers

Use the modern helpers, not `reflect.SliceHeader`/`reflect.StringHeader` (both are deprecated /
unsafe to construct manually):

- `unsafe.Slice(*T, len) []T` — build a slice from a pointer + length (e.g. from a C buffer).
- `unsafe.SliceData([]T) *T` — get the backing pointer of a slice.
- `unsafe.String(*byte, len) string` — build a string from a `*byte` + length; the bytes must not
  change or `string` immutability breaks.
- `unsafe.StringData(string) *byte` — get the backing pointer of a string.

```go
// Zero-copy view of a []byte as string (bytes must not mutate afterwards).
s := unsafe.String(unsafe.SliceData(b), len(b))
```

## Alignment and size

- `unsafe.Alignof(T)` / `unsafe.Sizeof(T)` are compile-time constants; use them in tests to guard
  layout assumptions.
- Struct field order matters for size on 64-bit targets: place larger/aligned fields first to avoid
  padding holes. `structlayout` (`go install honnef.co/go/tools/cmd/structlayout@latest`) prints
  the packing.
- ARM/32-bit atomic footgun: an `atomic.Int64` field on a struct must be 8-byte aligned; placing
  it after a smaller field on 32-bit ARM crashes at runtime. Put it first, or use the typed atomics
  from `sync/atomic` (Go 1.19+) which handle alignment.

## Runtime pinning and finalizers

- `runtime.KeepAlive(x)` prevents the GC from collecting `x` until the call — required when passing
  a pointer *derived* from `x` (e.g. into a syscall) so the object isn't reclaimed mid-call.
- `runtime.Pinner{}.Pin(&x)` pins a Go object at its address so it's safe to hand its pointer to C
  or the kernel; call `Unpin()` at the end. Prefer this over `KeepAlive` when the pointer must
  survive the call (e.g. stored on the C side for a callback).
- Finalizers: prefer `runtime.AddCleanup` (Go 1.24+) over `runtime.SetFinalizer` — multiple cleanups
  per object, no leaks on reference cycles, no delayed free. Neither should replace a `Close()`
  method; treat them as leak nets, not the primary release path.

## syscall vs golang.org/x/sys

- `syscall` is **frozen**. New syscalls, new flags, and new platforms land in `golang.org/x/sys/unix`
  (Linux/BSD/macOS/Solaris) and `golang.org/x/sys/windows`. Prefer those for anything post-Go 1.4.
- Direct `SYS_*` numbers go through `unix.Syscall`/`SyscallN` — types are per-arch, so
  cross-compilation with the wrong build tag fails at link, not at ABI break.
- On Windows, `windows.NewLazyDLL("kernel32.dll").NewProc("VirtualProtect").Call(...)` is the
  idiomatic dynamic import path; still `unsafe` on inputs and return values, so wrap in a safe
  facade like any FFI.

## cgo boundary

`cgo` is a full language boundary with its own rules — cheap in code, expensive at runtime and
build time.

- **Cost**: each cgo call is ~10x a Go call and blocks the current M (may spawn a new one). Batch
  calls; do not put `C.foo()` in a tight loop.
- **Pointer rules** (enforced by `GODEBUG=cgocheck=1`, on by default; `cgocheck=2` catches more):
  - A Go pointer passed to C must not point to memory containing other Go pointers.
  - C code must not store a Go pointer past the return of the call (the GC may move the object).
  - Convert `*C.char` from a `string` with `C.CString`; free it with `C.free(unsafe.Pointer(cs))`
    — `C.CString` is a `malloc`, not a Go allocation.
  - Read `*C.char` back to Go with `C.GoString(cs)` (copies) or `C.GoStringN(cs, n)` for lengths.
- **Panics don't cross cgo**: a Go panic that unwinds into a C frame aborts the process. Recover at
  the Go entry point of any C-invoked callback.
- **Static analysis loses coverage**: `go vet`, race detector, and coverage don't see through cgo.
  Keep the cgo surface tiny and put the Go-facing wrappers in a small package with high test cover.
- **Cross-compilation**: `cgo` requires a C toolchain for the target — cross-compiling with
  `CGO_ENABLED=1` and a foreign `GOOS`/`GOARCH` fails unless you set `CC=<target-gcc>` and friends.
  Prefer `CGO_ENABLED=0` unless a C dep is truly required.

## Static, stripped, and cross-compiled builds

For offensive tooling and reproducible artifacts:

```bash
# Fully static Linux binary, no cgo, no debug symbols, stripped path.
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
  go build -trimpath -ldflags="-s -w" -o payload ./cmd/payload

# Windows cross-compile from Linux, GUI subsystem (no console window).
CGO_ENABLED=0 GOOS=windows GOARCH=amd64 \
  go build -trimpath -ldflags="-s -w -H=windowsgui" -o payload.exe ./cmd/payload
```

- `CGO_ENABLED=0` gives a truly static binary — no libc dependency, deploys anywhere. When cgo is
  needed but static linking still is, add `-tags netgo,osusergo` so `net` and `os/user` use pure-Go
  resolvers.
- `-trimpath` removes local filesystem paths from the binary (a leak into `.debug_line` otherwise).
- `-ldflags="-s -w"` drops symbol table and DWARF; combine with UPX if size is the goal (breaks some
  AV signatures too — sometimes useful, sometimes counterproductive).
- Go 1.24 embeds a **GNU build ID** (ELF `NT_GNU_BUILD_ID`) and macOS `LC_UUID` by default. Disable
  with `-ldflags="-B none"` if identifying the toolchain build is a concern.
- Reproducible builds: pin the toolchain (`GOTOOLCHAIN=go1.24.0`), use `-trimpath -buildvcs=false`,
  set `SOURCE_DATE_EPOCH`. Two hosts with the same source and toolchain must produce byte-identical
  binaries.
- `//go:embed` bakes assets into the binary at compile time — clean, no runtime IO; useful for
  self-contained tooling.

## Verification

- `go vet -unsafeptr ./...` — flags improper `uintptr` <-> `unsafe.Pointer` conversions.
- `GODEBUG=cgocheck=2 go test ./...` — deeper checking of Go pointers passed to C.
- `go test -race ./...` — catches data races the compiler can't see through `unsafe`.
- Test alignment/size assumptions with `unsafe.Alignof`/`unsafe.Sizeof` in a compile-time-checked
  test; a change in Go version that breaks layout fails the test, not production.

## Review checklist

- Every `unsafe.Pointer` conversion matches one of the documented patterns; no `uintptr` stored
  between operations.
- Slice/string reinterpretations use `unsafe.Slice`/`unsafe.String` (or their `Data` counterparts),
  not manual header structs.
- Any pointer handed to C is either allocated in C or covered by `runtime.KeepAlive` /
  `runtime.Pinner` for the call's lifetime.
- `cgo` callbacks recover panics before returning to C.
- Static/cross builds document `CGO_ENABLED`, tags (`netgo`, `osusergo`), and any linker flags.
- `syscall` calls that could migrate to `golang.org/x/sys/{unix,windows}` do.
