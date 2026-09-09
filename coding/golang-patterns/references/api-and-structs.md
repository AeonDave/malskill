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

Go 1.27+ allows a struct-literal key to be any valid field selector (nested/embedded
fields). Syntax and inference live in `language.md`.

## ServeMux patterns (Go 1.22+)

`net/http.ServeMux` accepts methods and wildcards. Register method-specific patterns;
a method pattern beats a matching methodless one. `"GET /p"` also registers `"HEAD /p"`.

```go
mux.HandleFunc("GET /items/{id}", getItem)
mux.HandleFunc("POST /items", createItem)
mux.HandleFunc("/files/{path...}", serveFiles) // remaining segments
mux.HandleFunc("/exact/{$}", exact)            // exact trailing slash
id := r.PathValue("id")
```

More-specific overlapping patterns win; neither-more-specific is a conflict
(registration order does not matter). Patterns containing `{` `}` are wildcards —
do not put those characters in literal paths. `GODEBUG=httpmuxgo121=1` restores
pre-1.22 matching. Skip third-party routers unless you need middleware stacks the
stdlib mux does not provide.

## References

- https://go.dev/doc/effective_go#embedding
- https://github.com/golang/go/wiki/CodeReviewComments#receiver-names
