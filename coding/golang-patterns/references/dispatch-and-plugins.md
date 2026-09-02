# Dispatch, Polymorphism, and Plugins

Load this when choosing between interfaces, generics, and enum dispatch; designing a command
dispatcher; or adding functionality to an already-compiled binary via a static registry, a plugin
loader, RPC, WebAssembly, or an embedded script engine. For the safety of `unsafe`/cgo/syscall
edges, see `unsafe-cgo.md`; for the security review of the extension surface, see
`security-review.md`.

## Contents

- [Choosing a dispatch mechanism](#choosing-a-dispatch-mechanism)
- [Small interfaces and optional behavior](#small-interfaces-and-optional-behavior)
- [Enum dispatch and closed sets](#enum-dispatch-and-closed-sets)
- [Registries and command dispatchers](#registries-and-command-dispatchers)
- [Compile-time registration and embed](#compile-time-registration-and-embed)
- [The `plugin` package (stdlib)](#the-plugin-package-stdlib)
- [HashiCorp go-plugin (RPC / gRPC)](#hashicorp-go-plugin-rpc--grpc)
- [WebAssembly plugins (wazero, extism)](#webassembly-plugins-wazero-extism)
- [Embedded interpreters (yaegi, others)](#embedded-interpreters-yaegi-others)
- [Self-update and hot-reload](#self-update-and-hot-reload)
- [Choosing between mechanisms](#choosing-between-mechanisms)

## Choosing a dispatch mechanism

- **Generics** (Go 1.18+): closed set, hot path, needs identical operations across types. Zero
  boxing, one specialized copy per instantiation. Best for containers/algorithms.
- **Interfaces (`type T interface { ... }`)**: open set or runtime extensibility. One-word type +
  data pointer, one v-table indirection per method call. Default for pluggable seams.
- **Enum dispatch (typed const + `switch`)**: closed protocol, fastest to reason about, exhaustive
  behavior in one place. Default for wire commands and state machines.

Rule of thumb: generics until the set is heterogeneous at runtime; enum if the set is closed and
central; interface if callers or plugins extend it.

## Small interfaces and optional behavior

Interfaces are Go's polymorphism; keep them 1–3 methods and define them **at the consumer**, never
at the provider.

```go
// Consumer defines what it needs; providers just satisfy it.
type UserReader interface {
    Get(ctx context.Context, id string) (User, error)
}

// Compile-time contract check next to the type.
var _ UserReader = (*PostgresStore)(nil)
```

Optional behavior uses a smaller interface + type assertion — the pattern `io.Writer` uses for
`Flush`, `WriteString`, `ReadFrom`:

```go
type Flusher interface{ Flush() error }

func WriteAndMaybeFlush(w io.Writer, p []byte) error {
    if _, err := w.Write(p); err != nil { return err }
    if f, ok := w.(Flusher); ok { return f.Flush() }
    return nil
}
```

Typed-nil trap: a `(*T)(nil)` inside an interface is **not** `== nil`. Return `nil` explicitly at
the interface level; don't return a typed nil struct pointer.

## Enum dispatch and closed sets

Place `Unknown` at iota 0 so a zero-valued variable isn't a valid state, and drive with a total
`switch`:

```go
type Status uint8
const (
    StatusUnknown Status = iota
    StatusPending
    StatusRunning
    StatusDone
)

func (s Status) String() string {
    switch s {
    case StatusPending: return "pending"
    case StatusRunning: return "running"
    case StatusDone:    return "done"
    default:            return "unknown"
    }
}
```

`go vet`'s `exhaustive` (via `golangci-lint`) analyzer catches missed cases when the set grows.

## Registries and command dispatchers

Model wire/runtime commands as a discriminated union: a struct with a `Type` field plus a raw
payload, dispatched through a `map[string]Handler`:

```go
type Envelope struct {
    Type    string          `json:"type"`
    Payload json.RawMessage `json:"payload"`
}

type Handler func(ctx context.Context, payload json.RawMessage) (any, error)

var registry = map[string]Handler{}

func Register(kind string, h Handler) { registry[kind] = h }

func Dispatch(ctx context.Context, e Envelope) (any, error) {
    h, ok := registry[e.Type]
    if !ok { return nil, fmt.Errorf("unknown command %q", e.Type) }
    return h(ctx, e.Payload)
}
```

The dispatcher is auditable in one file; adding a command means one `Register` call plus a handler
function. Protobuf `oneof` is the schema equivalent.

## Compile-time registration and embed

Extending a compiled binary at build time (not runtime) is often what you actually want: one static
executable, no ABI matching, no dlopen.

- **`init()`-time registration**: a subpackage self-registers by calling `Register(...)` inside its
  `init()`. The `main` binary imports the subpackage (often blank-import `_ "myapp/plugins/x"`) to
  pull it in. Feature matrix = which subpackages are imported.
- **`//go:build tags`**: gate whole files with `//go:build feature_x` so the feature ships in one
  build and not another. Combines with the blank-import registry for capability-scoped binaries.
- **`//go:embed` (Go 1.16+)**: bake assets, templates, WASM modules, configs, or encrypted payloads
  directly into the binary. Zero runtime IO, single-file deploy.

```go
import _ "embed"

//go:embed rules.wasm
var rulesModule []byte // available at runtime with no filesystem dependency
```

## The `plugin` package (stdlib)

`plugin` opens a Go shared object built with `-buildmode=plugin`. It exists — it's just narrower
than most projects expect.

Limits (from `pkg.go.dev/plugin`, stable across releases):

- **Linux / macOS / FreeBSD only**. No Windows support.
- Plugin and host must be built with **the exact same Go toolchain, build tags, and shared-dep
  source**. Even a patch-version mismatch fails at load.
- **No unload**. Once opened, the `.so` stays in the process until exit; you cannot reopen the same
  path — design hot-reload around new filenames or full restarts.
- The race detector's coverage across the plugin boundary is limited.

The docs themselves recommend that if you already control host and plugin, you're usually better
off blank-importing the plugin packages and shipping one static binary — the compile-time registry
pattern above.

## HashiCorp go-plugin (RPC / gRPC)

`github.com/hashicorp/go-plugin` is the widely-used cross-platform alternative. It runs the plugin
as a **subprocess** and talks over `net/rpc` or gRPC.

Wins vs stdlib `plugin`:

- Cross-platform (Windows included).
- Language-agnostic on the gRPC path — plugins can be written in any language.
- Version and toolchain independence at both ends.
- Crash isolation: a panicking plugin dies alone; the host keeps running.
- Bidirectional: the plugin can call back into the host through a `MuxBroker`-brokered stream.

Cost: per-call serialization, subprocess lifecycle, protocol design work.

Handshake keeps a host from accidentally launching an unrelated binary:

```go
var handshake = plugin.HandshakeConfig{
    ProtocolVersion:  1,
    MagicCookieKey:   "MYAPP_PLUGIN",
    MagicCookieValue: "d5e7f3...",
}
```

Terraform, Vault, Nomad, Packer, Waypoint all ship on this model — it's battle-tested for
capability-extending compiled binaries.

## WebAssembly plugins (wazero, extism)

WebAssembly is the modern portable-plugin story, especially when plugin code is untrusted or must
run cross-platform without a subprocess.

- **`wazero`** — pure-Go WebAssembly runtime, zero dependencies, no cgo. Interpreter runs
  anywhere Go runs; Compiler mode (AOT) runs 10x+ faster on `amd64`/`arm64`. Register Go host
  functions with `Runtime.NewHostModuleBuilder(...)`; expose only what the plugin should touch.
- **`extism` / `github.com/extism/go-sdk`** — a plugin framework on top of `wazero` with a `Manifest`
  API: `AllowedHosts`, `AllowedPaths` (host→plugin dir mapping), memory caps, timeouts, allowlisted
  host functions. Plugins are compiled from any language with an Extism PDK (Rust, Go via TinyGo,
  Python, JS/TS, ...).
- WASM guests can only see numeric types; strings/bytes cross via memory. The runtime provides the
  `wasi_snapshot_preview1` interface (like `x/sys`) if you enable it — grant it deliberately.

Reach for WASM when plugin code is not trusted, must be sandboxed, or must be portable across host
languages. Reach for `hashicorp/go-plugin` when the plugin is trusted Go code and you want native
performance without a WASM ABI in the middle.

## Embedded interpreters (yaegi, others)

When behavior must change without recompiling and native performance isn't required, embed an
interpreter:

- **`github.com/traefik/yaegi`** — pure-Go interpreter of Go source. `Use(stdlib.Symbols)` exposes
  stdlib; `unsafe` and `syscall` packages are **not** exposed by default (Traefik's own plugin
  system rides on this). Slower than compiled Go, but you get real Go source as your extension
  language.
- **`starlark-go`** — pure-Go Starlark (Python-subset), sandboxed by design, popular for
  configuration DSLs.
- **`expr` / `github.com/expr-lang/expr`** — small expression language for rule engines.
- **`cel-go`** — Google's Common Expression Language; used by Envoy, K8s admission, etc.
- **`otto` / `goja`** — embedded ECMAScript engines when JavaScript is the extension language.

Scripts work best for operator-configurable logic (tasking, rules, decisions). Compiled plugins win
on performance and type safety.

## Self-update and hot-reload

Two distinct problems: **replace the whole binary** vs **swap behavior in-process**.

Whole-binary replace:

- `github.com/minio/selfupdate` (fork of `inconshreveable/go-update`) — download → optional bsdiff
  patch → checksum → **signature verification** (`Verifier` + `LoadFromURL`) → atomic swap into
  place → automatic rollback on failure. The signature verification step is non-negotiable for
  anything shipped over the network.
- Rollout hygiene: verify before swap, keep the old binary, expose a `--rollback` path.

In-process reload for servers (zero-downtime restart, not really "hot code swap"):

- `github.com/cloudflare/tableflip` — upgrades the running binary by exec'ing a new one and passing
  listening sockets over a Unix domain socket; old process drains, new one serves.
- SIGHUP-based config reload is a simpler pattern: `signal.Notify(ch, syscall.SIGHUP)` → re-read
  config → atomically swap the `*Config` pointer under an `atomic.Pointer[Config]`.

For true in-process capability swaps, one of the plugin mechanisms above is what you want — `plugin`
if you're on Linux/macOS and control both sides, `go-plugin` for crash isolation and cross-platform,
WASM/scripting for untrusted or user-provided modules.

## Choosing between mechanisms

| Need | First choice |
|---|---|
| Feature matrix in one binary | Blank-import registry + `//go:embed` |
| Trusted native Go plugin, all OSes, crash isolation | `hashicorp/go-plugin` (gRPC) |
| Untrusted third-party plugin code, sandboxed | `wazero` / `extism` |
| Operator-configurable rules, no recompile | `cel-go` / `starlark-go` / `expr` |
| Script-driven extension in Go source | `yaegi` |
| Replace the shipped binary on release | `minio/selfupdate` with signature verification |
| Zero-downtime server upgrade | `tableflip` + Unix-socket handoff |

Prefer the simplest option that actually meets the constraint; every extra loader is another
security surface and another version-skew failure mode.
