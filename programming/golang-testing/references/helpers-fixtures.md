# Helpers, fixtures, temp dirs, and golden files

## Helpers

```go
func requireNoError(t *testing.T, err error) {
    t.Helper()
    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }
}
```

## TempDir and Cleanup

Prefer `t.TempDir()` and `t.Cleanup()` to avoid leaking files/resources.

```go
tmp := t.TempDir()
path := filepath.Join(tmp, "in.txt")
requireNoError(t, os.WriteFile(path, []byte("hi"), 0o644))
```

## testdata

Put fixtures under `testdata/` (Go tooling ignores it for packages).

## Golden files

Golden tests are useful for renderers/formatters. Keep an update flag.

```go
var update = flag.Bool("update", false, "update golden files")
```

Cautions:
- normalize line endings where needed
- keep golden outputs small and meaningful
- prefer structured assertions for JSON where possible
