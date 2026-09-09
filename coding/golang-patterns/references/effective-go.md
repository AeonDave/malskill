# Effective Go — distilled notes

Use this reference when you want canonical, idiomatic Go guidance beyond the patterns in `SKILL.md`.

## Non-negotiables

- **Always run `gofmt`** (and ideally `goimports`). Formatting consistency is part of Go culture.
- Prefer **clarity over cleverness**: short functions, obvious control flow, early returns.

## Naming

- No underscores in identifiers.
- Exported names use **MixedCaps**; unexported use **mixedCaps**.
- Package names are short, lower-case, and usually singular.

## Errors

- Errors are values: return them, wrap them with context, and handle them explicitly.
- Don’t use `panic` for control flow; reserve it for truly unrecoverable programmer errors.

## Concurrency

- Prefer “**share memory by communicating**” (channels) over shared mutable state.
- If you must share memory, keep ownership clear and guard with `sync` primitives.

## Interfaces

- Keep interfaces small (often 1–3 methods).
- **Accept interfaces, return concrete types**.
- Define interfaces where they’re consumed (usually in the calling package).

## Documentation

- Exported identifiers should have doc comments.
- Comments for exported identifiers should start with the identifier name.

## Modern stdlib (Go 1.21+)

Reach for the standard library before pulling in a helper crate — most "utility" imports are now
stdlib.

- `min(a, b)` / `max(a, b)` / `clear(x)` builtins (Go 1.21) — replace `math.Min`/`math.Max`, work on
  any ordered type; `clear` zeroes a map or slice (len unchanged for slices).
- `slices` and `maps` packages (Go 1.21) — `slices.Contains`, `slices.Equal`, `slices.SortFunc`,
  `slices.Clone`, `maps.Clone`. Go 1.23+: `maps.Keys`/`maps.Values` are iterators; collect with
  `slices.Sorted(maps.Keys(m))` rather than a hand-rolled loop. See `language.md` for range-over-func.
- `cmp.Compare` / `cmp.Or` (Go 1.21) — total ordering helpers for `slices.SortFunc` and default
  fallbacks.
- `for i := range n` (Go 1.22) — cleaner than `for i := 0; i < n; i++`; loop vars are per-iteration
  when the `go` directive is 1.22+ (see `language.md`).
- `log/slog` (Go 1.21) — structured logging as stdlib; prefer over ad-hoc `log.Printf` in new code
  and over `zap`/`zerolog` unless the throughput demands it. `slog.NewMultiHandler` (Go 1.26+) fans
  a record out to several handlers (Enabled is OR; Handle/WithAttrs/WithGroup call each enabled
  handler) — use it instead of a custom tee.
- `math/rand/v2` (Go 1.22) — new code: `rand.N(n)` for any integer/duration upper bound; ChaCha8
  global source, auto-seeded. Still **not** `crypto/rand`. Do not call `Read` on v2 (removed); use
  `crypto/rand.Read` for tokens.
- `unique.Make` (Go 1.23) — intern comparable values; `Handle[T]` equality is cheap. Use as map
  keys when the payload is large and compared often. Not a string pool for tiny ints.
- `uuid` (Go 1.27) — generate/parse UUIDs in stdlib; drop a UUID helper module unless you need
  a version the stdlib package does not implement. Check `go doc uuid` for the constructors you
  actually need.
- `crypto/hpke` (Go 1.26) — Hybrid Public Key Encryption (RFC 9180), including post-quantum hybrid
  KEMs. `crypto/mldsa` (Go 1.27) — ML-DSA (FIPS 204); `crypto/x509` and `crypto/tls` (TLS 1.3) accept
  those keys/signatures. Reach for these instead of third-party PQ wrappers when you are on 1.27+.
- `errors.Join` (Go 1.20) — see `errors.md`. `errors.AsType` (Go 1.26) lives there too.
- JSON: `omitzero` on v1 since Go 1.24; `encoding/json/v2` in Go 1.27 — see `json-v2.md`.

Go 1.26+ language syntax (`new(expr)`, generic methods, …) is in `language.md`. Run `go fix ./...`
to apply safe modernizers — see `tooling.md`.

## Canonical references


- Effective Go: https://go.dev/doc/effective_go
- Go Code Review Comments: https://github.com/golang/go/wiki/CodeReviewComments
- Standard library: treat it as the style baseline (APIs, naming, error handling)
