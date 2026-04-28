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

## Canonical references

- Effective Go: https://go.dev/doc/effective_go
- Go Code Review Comments: https://github.com/golang/go/wiki/CodeReviewComments
- Standard library: treat it as the style baseline (APIs, naming, error handling)
