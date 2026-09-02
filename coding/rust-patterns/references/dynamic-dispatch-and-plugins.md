# Dynamic Dispatch and Plugins

Load this when choosing between trait objects, generics, and enum dispatch, designing plugin
architectures (registries, runtime loading, scripting), or structuring command dispatchers.

## Contents

- [Choosing a dispatch mechanism](#choosing-a-dispatch-mechanism)
- [Trait-object registries](#trait-object-registries)
- [Enum dispatch for closed sets](#enum-dispatch-for-closed-sets)
- [Compile-time discovery](#compile-time-discovery)
- [Runtime loading of dynamic libraries](#runtime-loading-of-dynamic-libraries)
- [Why the Rust ABI is unstable](#why-the-rust-abi-is-unstable)
- [In-memory loading](#in-memory-loading)
- [Sandboxed alternatives: WASM and IPC](#sandboxed-alternatives-wasm-and-ipc)
- [Embedded scripting](#embedded-scripting)
- [Command dispatcher pattern](#command-dispatcher-pattern)

## Choosing a dispatch mechanism

- **Generics / monomorphization**: closed set, hot path. Each use of a generic function generates a
  specialized copy — zero dispatch overhead, but per-copy code bloat and compile time. Default for
  libraries and `impl Trait` signatures.
- **`dyn Trait`**: open set or runtime extensibility; the only way to hold heterogeneous
  implementations in one collection. Costs a v-table indirection per call and requires an
  **object-safe** trait (no generic methods, no `Self` return by value). Add `Send + Sync` bounds
  when objects will cross threads.
- **Enum dispatch**: closed set in one container with near-static performance — the `match` compiles
  to a jump table and can be inlined. Use the `enum_dispatch` crate to remove match boilerplate.

Rule of thumb: generics until you need a heterogeneous collection; enum if the set is closed;
`dyn` if callers or runtime loading extend it.

Scope note: this is Rust's *software* polymorphism — one binary, many behaviors. It is unrelated to
polymorphic malware (representation mutated across generations): monomorphization plus feature
gated builds already give per-build binary diversity, and a runtime mutation engine is neither
natural nor useful in Rust. For the practical equivalent, see build-time diversification in
`offensive-lowlevel.md`.

## Trait-object registries

Use `Box<dyn Trait>` for exclusive ownership, `Arc<dyn Trait>` when lookups share the plugin, and
`dyn-clone` when boxed objects must be cloneable.

```rust
trait Plugin: Send + Sync {
    fn name(&self) -> &str;
    fn run(&self, ctx: &Ctx) -> Result<()>;
}

#[derive(Default)]
struct Registry {
    by_name: HashMap<String, Arc<dyn Plugin>>,
}

impl Registry {
    fn register(&mut self, p: Arc<dyn Plugin>) {
        self.by_name.insert(p.name().to_string(), p);
    }
    fn get(&self, name: &str) -> Option<Arc<dyn Plugin>> {
        self.by_name.get(name).cloned()
    }
}
```

A name-keyed registry (`HashMap<String, Arc<dyn Trait>>`) suits lookup-by-name (commands, modules);
a `Vec<Box<dyn Trait>>` suits ordered pipelines (middleware, hooks).

## Enum dispatch for closed sets

```rust
#[enum_dispatch::enum_dispatch(Capability)]
enum CapabilityKind {
    InfoGather(InfoGather),
    Exec(Exec),
    Exfil(Exfil),
}
// One enum per closed set; dispatched calls inline to the concrete impl.
```

New variants require editing the enum — that is the point: the compiler forces every dispatch site
to handle it. Prefer this over a boolean/flag registry in a closed system.

## Compile-time discovery

When modules must self-register without editing a central list, use `inventory` (or `linkme`):
modules publish themselves via a macro at link time; the registry iterates the collected entries.
Cheaper than dynamic loading and still extensible — but only within one binary's build.

## Runtime loading of dynamic libraries

- Set `crate-type = ["cdylib"]` for a plugin library and export `extern "C"` entry points. `dylib`
  links Rust-to-Rust but is only safe when everything is compiled with the same rustc version and
  settings — treat it as "same build graph or cdylib".
- `libloading` is the low-level loader; use C-safe handles and functions at the ABI boundary, not
  `dyn Trait`, slices, or `&str` directly:

```rust
use std::ffi::c_void;
use libloading::{Library, Symbol};

type PluginInit = unsafe extern "C" fn() -> *mut c_void;

// SAFETY: the library path is trusted, the symbol signature matches, and `lib` stays alive.
let lib = unsafe { Library::new(path)? };
let init: Symbol<PluginInit> = unsafe { lib.get(b"plugin_init")? };
let handle = unsafe { init() };
```

- Behind the raw loader, wrap in a safe facade and leak or track the `Library` handle; unloading
  while objects exist is UB.
- Version the plugin ABI with an explicit version check at load.

## Why the Rust ABI is unstable

Rust's only stable ABI today is the **C ABI**. The default `repr(Rust)` layout is intentionally
unspecified (fields may be reordered, niches exploited), symbol mangling is a Rust-specific scheme
(v0/legacy), and generic code is instantiated per-crate. Consequences:

- Cross-binary boundaries must be `repr(C)` (see `unsafe-and-ffi.md`) or use a stable-ABI layer.
- `abi_stable` provides a stable ABI with **load-time layout checking** (`StableAbi` derive,
  `RVec`/`RString` replacements); it intentionally leaks the library on load to prevent UAF.
- `stabby` provides a **versioned** ABI selected per-type — good when plugins need rich Rust types
  (enums, niche-optimized layouts) across the boundary.

Choose `abi_stable`/`stabby` when plain `extern "C"` handles and POD structs are not enough.

## In-memory loading

File-less loading keeps payloads off disk:

- **Linux**: `memfd_create` an anonymous fd, write the ELF, then `dlopen` via
  `/proc/self/fd/<fd>` — `libloading` accepts that path.
- **Windows**: `LoadLibrary` needs a path, so in-memory loading means **manual mapping**: allocate,
  copy PE sections, resolve the import table, apply relocations, call the entry point. This is a
  hand-rolled `windows-sys` procedure — substantial `unsafe`; keep it isolated behind a facade and
  prefer documented loaders when a path on disk is acceptable.

## Sandboxed alternatives: WASM and IPC

- **WASM**: `extism` (built on `wasmtime`) loads `.wasm` modules through a `Manifest`; host
  functions and capabilities are allowlisted. Best when plugin code is untrusted — the sandbox
  constrains file/network access.
- **IPC**: run the plugin as a child process with a `serde`-framed protocol (JSON, MessagePack)
  over stdio or a pipe. Crash isolation beats both DLL and WASM loading; pay for it with
  serialization + process overhead.

Reach for DLL loading first for trusted in-process speed; WASM/IPC first for untrusted plugin code.

## Embedded scripting

When behavior must change without recompiling, embed an interpreter instead of shipping plugins:

- `rhai` — pure-Rust scripting, `no_std`-capable, tight host integration.
- `mlua` — Lua/Luau (vendored LuaJIT or Lua 5.x), good when users already know Lua.
- Keep scripts data-driven at boundaries: pass structured inputs, return structured outputs; do not
  let strings of script drive FFI directly.

Script engines beat plugin loaders for operator-configurable logic (tasking, decision tables);
compiled plugins win on performance and type safety.

## Command dispatcher pattern

Model remote/runtime commands as a `serde`-deserializable enum and dispatch with `match`:

```rust
#[derive(Deserialize)]
enum Command {
    Sleep { millis: u64 },
    Exec { path: String, args: Vec<String> },
    Persist(PersistOp),
}

fn dispatch(cmd: Command, ctx: &Context) -> Result<Response> {
    match cmd {
        Command::Sleep { millis } => sleep(millis).map(Response::Slept),
        Command::Exec { path, args } => exec(&path, &args).map(Response::Output),
        Command::Persist(op) => persist::run(op, ctx).map(Response::Ack),
    }
}
```

The enum is the wire protocol and the exhaustive `match` is the dispatcher — one place to audit
capabilities, one compiler check when the protocol grows.
