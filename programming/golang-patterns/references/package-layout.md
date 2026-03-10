# Package organization

## A pragmatic layout

Keep package boundaries aligned with ownership and responsibilities.

Example:

- `cmd/<app>/` — entry points
- `internal/` — private packages
- `pkg/` — public packages (only if you truly have a public API)

## Package naming

- short, lower-case
- avoid redundant suffixes like `Service`, `Manager`, `Handler` unless meaningful

## Avoid package-level state

Prefer dependency injection to hidden globals.

```go
type Server struct { db *sql.DB }
func NewServer(db *sql.DB) *Server { return &Server{db: db} }
```

## References

- https://go.dev/blog/package-names
- https://github.com/golang/go/wiki/CodeReviewComments#package-names
