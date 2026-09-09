# HTTP handler testing

Use `net/http/httptest` for deterministic request/response testing.

Go 1.27+: prefer `httptest.NewTestServer(t, handler)` for anything that needs a real
`http.Client` round-trip. It uses an **in-memory** network (synctest-safe), fails the test on
handler panic, and registers `t.Cleanup` to close the server. `Client()` sends **all** HTTP/HTTPS
requests to that server regardless of host. Do not call `Start`/`StartTLS` unless you need a
loopback port.

```go
func TestHealthRoundTrip(t *testing.T) {
    srv := httptest.NewTestServer(t, http.HandlerFunc(HealthHandler))
    res, err := srv.Client().Get("http://example.com/health")
    requireNoError(t, err)
    t.Cleanup(func() { _ = res.Body.Close() })
    if res.StatusCode != http.StatusOK {
        t.Fatalf("status=%d; want %d", res.StatusCode, http.StatusOK)
    }
}
```

Handler-only tests still use `NewRequest` + `NewRecorder`:

```go
func TestHealth(t *testing.T) {
    req := httptest.NewRequest(http.MethodGet, "/health", nil)
    rec := httptest.NewRecorder()

    HealthHandler(rec, req)

    res := rec.Result()
    t.Cleanup(func() { _ = res.Body.Close() })

    if res.StatusCode != http.StatusOK {
        t.Fatalf("status=%d; want %d", res.StatusCode, http.StatusOK)
    }
}
```

`NewServer` / `NewTLSServer` still exist (loopback). Prefer `NewTestServer` for new tests so
cleanup and synctest isolation are default.

## JSON assertions

Prefer decoding JSON and comparing structs/maps instead of string equality.

```go
var got map[string]any
requireNoError(t, json.NewDecoder(res.Body).Decode(&got))

if got["id"] != "123" {
    t.Fatalf("id=%v; want %q", got["id"], "123")
}
```

Tip: for stable output, ensure you control key ordering only when encoding (but decode+compare avoids the issue).

A toolchain upgrade to Go 1.27 does **not** change `encoding/json` v1 semantics. A migration to
`encoding/json/v2` does — keep those test suites separate (`golang-patterns` `json-v2.md`).

For timeout/cancellation behavior, wrap the test in `synctest.Test` and use `NewTestServer`
instead of sleeps. Loopback `httptest.NewServer` blocks the bubble on real I/O.
