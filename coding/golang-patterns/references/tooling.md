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

## References

- gofmt: https://pkg.go.dev/cmd/gofmt
- go vet: https://pkg.go.dev/cmd/vet
- staticcheck: https://staticcheck.dev/
- golangci-lint: https://golangci-lint.run/
