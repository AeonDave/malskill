# encoding/json/v2 (Go 1.27+)

Load when adding JSON APIs, migrating off `encoding/json`, or debugging marshal
output that changed after a 1.27 toolchain upgrade. v1 `omitzero` (Go 1.24+) is
here because the tag is shared; HTTP handler tests stay in `golang-testing`.

## Stay on v1 unless you need v2 defaults

`encoding/json` is not deprecated. Go 1.27 implements it **on top of** the v2
engine and **keeps v1 semantics**. Unmarshal is faster; marshal is roughly at
parity. Error **text** may differ. You are not required to change imports.

A toolchain bump to 1.27 and a JSON **API** migration are separate tests. First
confirm v1 callers still pass, then migrate types/call sites that want v2
defaults.

`GOEXPERIMENT=nojsonv2` restores the pre-1.27 v1 implementation. It is a
temporary escape hatch, not a long-term pin.

## When to import encoding/json/v2

Switch a package to `encoding/json/v2` when you want at least one of:

- stricter decode (reject invalid UTF-8; reject duplicate object names)
- `MarshalWrite` / `UnmarshalRead` without building an Encoder/Decoder
- per-call `Options` (case folding, nil-slice formatting, custom marshalers)
- `omitzero` / v2 `omitempty` semantics on new structs

`encoding/json/jsontext` is the token/value streaming layer. Use it for
transformers and validators that should not interpret Go structs.

v1 and v2 interoperate: a `json/v2.MarshalerTo` is visible to `encoding/json.Marshal`,
and new struct tags work on both.

## Defaults that bite on a naive import swap

Changing `import "encoding/json"` to `encoding/json/v2` usually still **compiles**.
Behavior does not:

| Topic | v1 | v2 default |
|---|---|---|
| JSON field match | case-insensitive | case-sensitive (`MatchCaseInsensitiveNames` to restore) |
| invalid UTF-8 | replacement rune | error |
| duplicate names | last wins | error |
| nil slice / map | JSON `null` | empty array / object |
| `omitempty` | omit empty **Go** value | omit empty **JSON** value (null / `""` / `[]` / `{}`) |
| bad struct tags | ignored | runtime error |

`omitzero` (also on v1 since Go 1.24) omits a field when `IsZero() bool` is true,
else when the Go value is zero. Prefer `omitzero` for `time.Time`, `netip.Addr`,
and other types with a meaningful zero — a nil slice omits, an empty non-nil
slice encodes as `[]`. Prefer `omitempty` when you mean "omit if the JSON encoding
is empty" (v1 and v2 agree for strings, slices, arrays, and maps). Both tags
together omit if either applies.

```go
type Pet struct {
    Name      string    `json:"name"`
    Nicknames []string  `json:"nicknames,omitzero"` // nil omitted; empty [] encoded
    Born      time.Time `json:"born,omitzero"`
}
```

A v1 program that encoded a nil `[]string` as `null` will encode `[]` after a
raw v2 swap. Downstream clients that branch on `null` break. Fix the type, the
tag, or pass an option — do not paper over it in tests with string compare.

## Migration sequence

1. Keep `encoding/json` imports. Run the existing suite on a 1.27 toolchain.
2. For a low-risk package, switch the import and fix compile + tests.
3. For a high-risk package, call v2 with `jsonv1.DefaultOptionsV1()` first
   (identical behavior, v2 API). Flip one option at a time toward v2 defaults.
4. Do not mix "compiler upgrade CI" with "JSON golden files rewritten".

```go
import (
    jsonv1 "encoding/json"
    "encoding/json/v2"
)

b, err := json.Marshal(v, jsonv1.DefaultOptionsV1())
```

Later options override earlier ones, so
`json.Marshal(v, jsonv1.DefaultOptionsV1(), json.FormatNilSliceAsNull(false))`
is v1 except nil slices become `[]`.

Need production diff without changing responses: the
`github.com/go-json-experiment/jsonsplit` helper can marshal both and report
which option diverges. It doubles marshal cost; sample in prod.

## References

- https://go.dev/doc/go1.27
- https://go.dev/doc/jsonv2-migration
- https://pkg.go.dev/encoding/json/v2
- https://pkg.go.dev/encoding/json#hdr-Migrating_to_v2
