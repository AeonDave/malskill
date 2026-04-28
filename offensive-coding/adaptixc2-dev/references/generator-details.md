# Template Generator Details

Full details on the scaffold system at `AdaptixC2-Template-Generators/`.

---

## Placeholder System

All must be substituted — zero survivors in output:

| Placeholder | Value | Context |
|-------------|-------|---------|
| `__NAME__` | lowercase name | All files |
| `__NAME_CAP__` | Capitalized | Class names |
| `__WATERMARK__` | 8-char hex | Agent config |
| `__PACKAGE__` | `main`/`crypto`/`protocol` | Go package name |
| `__BUILD_TOOL__` | From toolchain YAML | Build command |
| `__PROTOCOL__` | Protocol name | Wire format |
| `__PROTOCOL_CAP__` | Capitalized protocol | Listener names |
| `__LISTENER_TYPE__` | `external`/`internal` | Listener behavior |

## Protocol Overlay Mechanism

Protocols live in `protocols/<name>/` and can override plugin templates:

1. `types.go.tmpl` + `constants.go.tmpl` → merged into `pl_utils.go` (repackaged as `main`)
2. `crypto.go.tmpl` → injected into `src_<name>/crypto/crypto.go` (repackaged as `crypto`)
3. `pl_main.go.tmpl` → **replaces** base `pl_main.go` entirely
4. `pl_transport.go.tmpl` → replaces listener transport
5. `pl_internal.go.tmpl` → replaces internal listener handler
6. `pl_build_<lang>.go.tmpl` → replaces build handler for that language
7. `implant/` overlays → merged into implant source tree

## Toolchains

Default safe toolchains: Go → `go-standard`, C++ → `mingw`, Rust → `cargo`.

Toolchain YAML format:
```yaml
name: go-standard
language: go
compiler:
  binary: go
build:
  command: "go build"
  env: { CGO_ENABLED: "0" }
  flags: ["-trimpath"]
  ldflags: "-s -w"
targets:
  - { goos: linux, goarch: amd64, suffix: "_linux_amd64" }
  - { goos: windows, goarch: amd64, suffix: "_windows_amd64.exe" }
```

## Evasion Gate

Generated with `-Evasion` flag. Scaffolds `evasion/` directory with a `Gate` interface (5 methods). Markers in templates:

- Go: `// __EVASION_IMPORT__`, `// __EVASION_FIELD__`, `// __EVASION_INIT__`
- C++: `// __EVASION_INCLUDE__`, `// __EVASION_MEMBER__`, `// __EVASION_CTOR__`
- Rust: `// __EVASION_MOD__`, `# __EVASION_FEATURES__` (must stay inside `[features]` in Cargo.toml)

Without `-Evasion`: all markers are stripped, no `evasion/` directory.
