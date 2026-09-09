# Tooling essentials

## Commands

```bash
# Format
gofmt -w .

# Tests
go test ./...
go test -race ./...

# Static analysis
go vet ./...

# Dependencies
go mod tidy
```

Recommended CI baseline:

```bash
go test ./...
go test -race ./...
go vet ./...
```

## Recommended extras

- `goimports` — gofmt + import management
- `staticcheck` — high-signal static analysis
- `golangci-lint` — aggregator (configure to avoid noise)

## Notes

- Prefer a small, curated linter set.
- Make linting fast enough to run pre-push / in CI.
- Keep one canonical lint/test command set in repository docs to reduce drift.

## Language version and toolchain

The `go` line in `go.mod` is the **language version** for the module. A 1.27 toolchain will
not accept generic methods, `new(expr)`, or other newer syntax in a module whose `go`
directive is older than that feature. Need generic methods as ordinary language? Set
`go 1.27.0` (or later) and use a 1.27+ toolchain (`GOTOOLCHAIN=go1.27.1` or newer). See
https://go.dev/doc/toolchain.

Go 1.25 is out of support once 1.27.x is current. Go 1.27 requires macOS 13 Ventura or
later. Go 1.27.1 (2026-09-01) is a patch (cgo, compiler, runtime, `go fix`,
`encoding/json`, `net/http`, `os`, simd) — language/stdlib features are from 1.26 and
1.27.0; prefer 1.27.1 over 1.27.0.

`go test` (Go 1.27+) runs the `stdversion` vet check by default: stdlib symbols newer than
the file's language version are errors. Raise the `go` line, add a build tag, or stop using
that API — do not disable the check to hide a mismatch.

## go fix (Go 1.26+)

`go fix ./...` applies the modernizer suite (same analysis framework as `go vet`) and the
source-level inliner. Fixes are intended not to change behavior. Review the diff; rerun if
the tool reports conflicting edits.

```bash
go fix ./...
go fix -inline ./...   # only //go:fix inline rewrites
```

Mark a wrapper you want callers to drop:

```go
//go:fix inline
func Ptr(x int) *int { return new(x) } // Go 1.26+ new(expr)
```

Go 1.27 modernizers include `atomictypes`, `embedlit`, `slicesbackward`, `unsafefuncs`. The
`waitgroup` analyzer is named `waitgroupgo`. Do not treat `go fix` as a formatter.

## References

- gofmt: https://pkg.go.dev/cmd/gofmt
- go vet: https://pkg.go.dev/cmd/vet
- staticcheck: https://staticcheck.dev/
- golangci-lint: https://golangci-lint.run/
