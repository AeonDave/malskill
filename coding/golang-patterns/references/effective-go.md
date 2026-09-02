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

- `min(a, b)` / `max(a, b)` builtins (Go 1.21) — replace `math.Min`/`math.Max`, work on any ordered
  type, no `float64` cast dance.
- `slices` and `maps` packages (Go 1.21) — `slices.Contains`, `slices.Equal`, `slices.SortFunc`,
  `slices.Clone`, `maps.Keys`, `maps.Values`, `maps.Clone`. Replace hand-rolled loops.
- `cmp.Compare` / `cmp.Or` (Go 1.21) — total ordering helpers for `slices.SortFunc` and default
  fallbacks.
- `for i := range n` (Go 1.22) — cleaner than `for i := 0; i < n; i++`; the loop variable is scoped
  per iteration (also true for `range` since 1.22, so the old `i := i` capture dance is gone).
- `log/slog` (Go 1.21) — structured logging as stdlib; prefer over ad-hoc `log.Printf` in new code
  and over `zap`/`zerolog` unless the throughput demands it.
- `errors.Join` (Go 1.20) — see `errors.md`.

## Canonical references


- Effective Go: https://go.dev/doc/effective_go
- Go Code Review Comments: https://github.com/golang/go/wiki/CodeReviewComments
- Standard library: treat it as the style baseline (APIs, naming, error handling)
