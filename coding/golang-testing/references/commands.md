# go test command recipes

```bash
# Run all tests
go test ./...

# Verbose output
go test -v ./...

# Run one test by name
go test -run TestAdd ./...

# Run tests in one package only
go test ./internal/service

# Run a subtest
go test -run "TestUser/Create" ./...

# Race detector
go test -race ./...

# Timeout
go test -timeout 30s ./...

# Repeat to detect flakiness
go test -count=10 ./...

# Disable test cache when investigating flakes
go test -count=1 ./...

# Benchmarks
go test -run=^$ -bench=. -benchmem ./...

# Fuzzing
go test -fuzz=FuzzParse -fuzztime=30s ./...
# Longer campaign against a single target; commit shrunk crashers under testdata/fuzz/.
go test -run=^$ -fuzz=FuzzParse -fuzztime=1h ./parser

# Coverage
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out
```
