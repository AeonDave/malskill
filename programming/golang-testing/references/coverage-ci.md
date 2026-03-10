# Coverage and CI

## Coverage basics

```bash
go test -cover ./...
go test -coverprofile=coverage.out ./...
go tool cover -func=coverage.out
go tool cover -html=coverage.out
```

## Coverage targets

Treat coverage as a *signal*, not a goal.
- critical logic should be well-covered
- prefer meaningful assertions over “line hits”

## About excluding files

Excluding generated code or packages from coverage is **repo-specific**.
Common approaches include:
- generating a combined profile and filtering paths
- using `-coverpkg` to include relevant packages

Avoid recommending build-tag tricks generically unless the repo already uses them.

## CI integration

Run at least:
- `go test ./...`
- `go test -race ./...` (where feasible)
- coverage profile generation
