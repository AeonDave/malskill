# APIs, structs, and method receivers

## Receiver consistency

Pick one receiver style per type:
- pointer receivers when the method mutates state or the type is large
- value receivers for small, immutable-ish types

## Functional options

Use when you have many optional parameters.

```go
type Server struct {
    addr    string
    timeout time.Duration
}

type Option func(*Server)

func WithTimeout(d time.Duration) Option {
    return func(s *Server) { s.timeout = d }
}

func NewServer(addr string, opts ...Option) *Server {
    s := &Server{addr: addr, timeout: 30 * time.Second}
    for _, opt := range opts { opt(s) }
    return s
}
```

## Embedding

Use embedding to compose behavior, not to create fragile inheritance chains.
Prefer explicit fields when it improves clarity.

## References

- https://go.dev/doc/effective_go#embedding
- https://github.com/golang/go/wiki/CodeReviewComments#receiver-names
