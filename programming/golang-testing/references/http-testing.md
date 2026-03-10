# HTTP handler testing

Use `net/http/httptest` for deterministic request/response testing.

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
