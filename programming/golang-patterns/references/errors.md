# Errors (idiomatic Go)

## Wrap with context

Prefer adding context at boundaries (I/O, parsing, RPC) and keep inner loops lean.

```go
data, err := os.ReadFile(path)
if err != nil {
    return nil, fmt.Errorf("read config %q: %w", path, err)
}
```

## Use errors.Is / errors.As

```go
if errors.Is(err, sql.ErrNoRows) {
    // handle not found
}

var ve *ValidationError
if errors.As(err, &ve) {
    // handle typed error
}
```

## Sentinel vs typed errors

- Sentinel (`var ErrX = errors.New(...)`) is good for stable, broad categories.
- Typed errors are good when the caller needs structured fields.

```go
type ValidationError struct {
    Field string
    Msg   string
}
func (e *ValidationError) Error() string {
    return fmt.Sprintf("invalid %s: %s", e.Field, e.Msg)
}
```

## Don’t ignore errors

If you truly must ignore an error, make it obvious and rare.

```go
_ = f.Close() // best-effort cleanup; error handled elsewhere
```

## Retryable vs non-retryable

Model this explicitly. A common approach:
- return a typed error (e.g., `*TemporaryError`) or
- wrap with `fmt.Errorf("...: %w", err)` and expose a helper `IsRetryable(err)`.

## References

- https://go.dev/blog/errors-are-values
- https://go.dev/blog/go1.13-errors
- https://github.com/golang/go/wiki/CodeReviewComments#error-strings
