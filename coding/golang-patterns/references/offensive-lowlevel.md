# Offensive and Low-Level Go

Load this for offensive tooling in Go: RE-resistance, symbol/metadata stripping, string
obfuscation, syscall dispatch strategy, static/cross-compiled artifacts, and in-memory execution
patterns. Safety of the underlying `unsafe`/cgo/syscall work lives in `unsafe-cgo.md`; audit rules
for callers live in `security-review.md`; runtime module loading (plugin/RPC/WASM/scripting) lives
in `dispatch-and-plugins.md`.

## Contents

- [Threat model against a Go binary](#threat-model-against-a-go-binary)
- [Metadata and symbol stripping](#metadata-and-symbol-stripping)
- [garble](#garble)
- [String and payload obfuscation](#string-and-payload-obfuscation)
- [Syscall dispatch strategy](#syscall-dispatch-strategy)
- [Static and cross-compiled artifacts](#static-and-cross-compiled-artifacts)
- [In-memory execution and payload delivery](#in-memory-execution-and-payload-delivery)
- [Anti-analysis footnotes](#anti-analysis-footnotes)
- [Verification](#verification)

## Threat model against a Go binary

Go binaries are structurally different from C/C++ malware and analysts know this:

- The runtime embeds a large `pclntab` and `moduledata` block that recovers function names, file
  paths, types, and interface tables even from stripped binaries. Mandiant's **`GoReSym`** parses
  these directly against `pclntab`/`moduledata` and works across Go 1.2 through current releases
  (including patch for stripped-`pclntab-magic` variants).
- Every dependency is statically linked and every generic use produces a monomorphized copy — a
  trivial program yields thousands of functions, but library code is separable by any FLIRT-style
  signature or a `GoReSym -d` pass.
- The default symbol scheme (`main.func1`, `crypto/aes.NewCipher`, `github.com/x/y.(*T).Method`) is
  extremely informative. Stripping helps; obfuscation helps more; both together are the baseline.

Design goal: raise the analyst's cost per hour, not to be "unbreakable" — any obfuscation short of a
full custom loader is reversible with enough effort (see garble's own `-literals` caveats).

## Metadata and symbol stripping

Baseline hardening every shipped tool should have:

```bash
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
  go build \
    -trimpath \
    -buildvcs=false \
    -ldflags="-s -w -buildid=" \
    -o payload ./cmd/payload
```

- `-ldflags="-s"` — drops the symbol table (function/global names lost by ordinary `nm`).
- `-ldflags="-w"` — drops DWARF debug info (no source lines in stack traces or `objdump -g`).
- `-trimpath` — removes build-host source paths (e.g. `/path/to/src/...`) from `runtime.FuncForPC`
  and error strings.
- `-buildvcs=false` — removes the VCS stamp (commit hash + dirty flag) the linker adds by default
  since Go 1.18.
- `-ldflags="-buildid="` — zeros out the Go build ID stamp used for cache dedup and also embedded as
  an ELF `NT_GNU_BUILD_ID` note by default since Go 1.24; use `-ldflags="-B none"` (linker `-B`
  flag) to skip the GNU/Mach-O build ID entirely.

Even after all of this, `GoReSym -d -p -t` will still recover most function names and file paths
from `pclntab`. Reducing that surface is `garble`'s job.

## garble

`github.com/burrowers/garble` is the de-facto Go obfuscator; it wraps the toolchain and rewrites
package/identifier names, positions, and (optionally) literals.

```bash
go install mvdan.cc/garble@latest

# Basic obfuscation: rename identifiers, hash positions, strip build info.
garble build -o payload ./cmd/payload

# Add literal obfuscation (imperfect — see caveats).
garble -literals build -o payload ./cmd/payload

# Deterministic obfuscation with a seed (for reproducible builds + reverse mapping).
garble -seed=random -literals build -o payload ./cmd/payload

# `-tiny` drops even more metadata (filenames, line numbers, panic info).
garble -literals -tiny build -o payload ./cmd/payload

# Reverse a stack trace using the seed.
garble -seed=<seed> reverse ./cmd/payload panic.log
```

Two important honest caveats from garble's own maintainers:

- **Destructive** transforms (metadata removal, identifier hashing) are effectively irreversible
  without source. Keep these on.
- **Transformative** ones (`-literals`, control flow) must reproduce program behavior, so the
  original semantics are still in the binary. Tools like **`GoStringUngarbler`** (Mandiant/FireEye)
  already automate `-literals` recovery. Treat literal obfuscation as "raises cost for grep and
  cheap static tools", not as a secret keeper.

Combine with the stripping flags above; garble runs them under the hood but `-tiny` is the extra
switch that matters for size and metadata.

## String and payload obfuscation

Even with `-literals`, treat plaintext IOCs (C2 URLs, mutex names, key material) as recoverable and
plan accordingly.

- Encode with a build-time key + `//go:embed` a ciphertext blob; decrypt on first use, wipe the
  plaintext (`for i := range b { b[i] = 0 }`) after consumption.
- The build-time key can be injected via `-ldflags="-X main.key=..."` per build so no key ever hits
  git.
- Avoid `String()`/`Error()`/`fmt.Stringer` methods that would leak secret-carrying fields; keep
  secrets in a small wrapper type without a `Stringer` impl (rule from `security-review.md`).
- Store larger blobs (models, rules, sub-binaries) as `//go:embed` byte slices decrypted at load
  time; single-file deploy, zero disk artifacts before use.

## Syscall dispatch strategy

Go does **not** support inline assembly in ordinary user code — no `asm { ... }` block, no
`core::arch::asm!` equivalent. You have three practical dispatch paths:

1. **`golang.org/x/sys/{unix,windows}`** — the maintained path. `syscall` itself is frozen; new
   flags and new platforms only land in `x/sys`. Prefer this everywhere it fits.

2. **Direct `unix.Syscall`/`SyscallN`** with an `SYS_*` constant when the wrapper doesn't exist:

   ```go
   import "golang.org/x/sys/unix"

   // Linux x86_64 exit(0). No return.
   func exit0() { unix.Syscall(unix.SYS_EXIT, 0, 0, 0) }
   ```

   Numbers are per-arch; a wrong build tag fails at link, not at ABI break.

3. **Windows dynamic import** with `windows.NewLazyDLL` / `NewLazySystemDLL` + `.NewProc().Call(...)`.
   This is the idiomatic path for `VirtualProtect`, `CreateRemoteThread`, `NtQuerySystemInformation`,
   etc. It looks safe but every `Call` returns raw `uintptr` you must interpret carefully.

For techniques that require true syscall stubs (Hell's Gate / indirect syscalls) or manual PE
mapping, the mainstream Go approach is a small **cgo** module compiled with clang/gcc: put the asm
in a `.s`/`.c` file, expose a C entrypoint, and call it from a `//go:build !cgo` — gated Go wrapper.
This trades cgo's cost and static-linkage headaches for having actual inline asm. Keep that surface
tiny and put the `unsafe` around it (see `unsafe-cgo.md`).

Runtime-integrity note: the Go runtime uses signals extensively (SIGURG for preemption, SIGPROF for
profiling). Anything that installs its own SIGSEGV/SIGILL handler must chain through
`runtime.SetSigTramp`-friendly code or the runtime crashes; use `signal.Notify` where possible.

## Static and cross-compiled artifacts

Static, self-contained binaries are Go's superpower — deploy anywhere, no libc dependency.

```bash
# Fully static Linux, no cgo, no debug symbols, VCS/build-id scrubbed.
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
  go build -trimpath -buildvcs=false -ldflags="-s -w -buildid= -B none" \
  -o payload ./cmd/payload

# Windows GUI-subsystem cross-compile from Linux (no console window on launch).
CGO_ENABLED=0 GOOS=windows GOARCH=amd64 \
  go build -trimpath -buildvcs=false \
    -ldflags="-s -w -H=windowsgui -buildid=" \
    -o payload.exe ./cmd/payload

# When cgo is required but static linking must be preserved: netgo, osusergo tags
# replace the cgo-linked resolvers with pure-Go equivalents.
CGO_ENABLED=1 go build -tags netgo,osusergo -ldflags="-s -w -extldflags=-static" ...
```

- Enabling PGO alongside these flags is free: drop a `default.pgo` next to `main` (`-pgo=auto` is
  default). See `golang-performance/references/compiler-and-runtime-tuning.md`.
- UPX packing changes some AV signatures but breaks others; also complicates `GoReSym` unless the
  `-strings` pass is used against the unpacked image. Measure before assuming a win.
- Reproducibility for shipped artifacts: pin the toolchain (`GOTOOLCHAIN=go1.24.0`), set
  `SOURCE_DATE_EPOCH`, and use the flag set above; identical inputs on two hosts must produce
  byte-identical binaries.

## In-memory execution and payload delivery

The offensive value of Go's single-static-binary is real: no dropped .so/.dll ecosystem, no ldconfig
dance. When a second stage is truly needed:

- **Compile-time inclusion** first: `//go:embed` a second stage (WASM, encrypted Go plugin, or a
  script) — see `dispatch-and-plugins.md` for the loader options. This is the simplest, safest, and
  easiest to sign.
- **Runtime module load** (Linux/macOS only via stdlib `plugin`; cross-platform via
  `hashicorp/go-plugin` subprocess RPC; sandboxed via `wazero`/`extism`) — same reference.
- **Fileless execution on Linux**: `memfd_create(2)` (`unix.MemfdCreate`) creates an anonymous fd,
  write the ELF, then `execveat` (`unix.Execveat`) from `/proc/self/fd/<fd>`. Real families in
  Go (e.g. the Sliver C2 framework) implement this pattern; the ecosystem has ready helpers
  (`github.com/amenzhinsky/go-memexec` and forks).
- **Fileless execution on Windows**: `LoadLibrary` needs a real path, so this is a manual PE-mapper
  (`VirtualAlloc` → copy sections → resolve imports → apply relocs → jump entry). Substantial
  `unsafe` + `windows.NewLazySystemDLL`; isolate behind a facade and test on Windows Server SKUs,
  not just workstations.

The C2 frameworks worth reading as prior art for legitimate red-team engagements: **Sliver**
(BishopFox, Go implants + gRPC C2), **Merlin** (Go HTTP/2 implants), Tyler McMullen's talk material
on real-world Go malware analysis. Study the loader and the transport, not the payload.

## Anti-analysis footnotes

- `runtime.GOOS`/`runtime.GOARCH` are baked at build; using them to gate offensive behavior is a
  trivial static string tell — put the gate behind an obfuscated constant or an env-var check.
- `time.Sleep` / `runtime.Gosched` do not defeat modern sandboxes; expect them to skip time.
- `debug.ReadBuildInfo()` exposes the module list at runtime — an analyst can read that field to
  fingerprint your third-party dependencies. Strip it via `-buildvcs=false` and consider vendoring
  + rewriting import paths for internal capabilities.
- Panic backtraces leak function names post-stripping if `-tiny` was not applied under garble —
  handlers should `recover()` and return a neutral error string.

## Verification

- Confirm the binary's exposed metadata: `go version -m ./payload`, `strings ./payload | head`,
  `readelf -s ./payload | head`. Expect empty function tables and no VCS stamp after the flags
  above; expect `GoReSym` output to still recover *some* function names unless garble was applied.
- Run `GoReSym -d -p -t ./payload` yourself before shipping — assume the analyst does the same and
  redact accordingly.
- Verify on the target OS/SKU, not the build host; Windows GUI subsystem behavior in particular
  differs across Server and Client SKUs.
