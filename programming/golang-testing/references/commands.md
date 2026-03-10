# go test command recipes

```bash
# Run all tests
go test ./...

# Verbose output
go test -v ./...

# Run one test by name
go test -run TestAdd ./...

# Run a subtest
go test -run "TestUser/Create" ./...

# Race detector
go test -race ./...

# Timeout
go test -timeout 30s ./...

# Repeat to detect flakiness
go test -count=10 ./...

# Benchmarks
go test -run=^$ -bench=. -benchmem ./...

# Fuzzing
go test -fuzz=FuzzParse -fuzztime=30s ./...

# Coverage
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out
```
