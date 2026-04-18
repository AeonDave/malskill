# API design

## Principles

- Prefer small interfaces.
- Make lifetimes and ownership explicit.
- Keep exception safety guarantees clear (basic/strong/no-throw).
- Encode invariants in types where practical.
- Keep one error strategy per API boundary.

## Prefer explicit constructors

```cpp
struct Port {
  explicit Port(int v) : value(v) {}
  int value;
};
```

## Error strategy

Pick one approach per layer:
- Exceptions (common for library boundaries)
- Status code + out-params
- `std::optional` for absence
- `std::expected`-style return (if available in your toolchain) or a local equivalent

Avoid mixing styles within a single API.

When exceptions are disabled, define and document a consistent error-value convention.

## Return by value

Return by value when reasonable; rely on move elision.

Prefer named result structs when a function naturally returns multiple values.

## Views

Use `std::span` and `std::string_view` for non-owning input parameters, but never store them without ensuring the backing storage outlives the view.

## Contract and ABI hygiene

- Prefer `explicit` for single-argument constructors.
- Keep virtual interfaces minimal and stable.
- Avoid leaking third-party or STL-heavy implementation details in ABI-sensitive public headers.
- Use `noexcept` when you can uphold it; do not mark speculative code paths as `noexcept`.

## Practical review prompts

- Can this API be used incorrectly without compiler help?
- Is nullability explicit (`T*`/`std::optional<T>` vs hidden sentinel values)?
- Are lifetime and threading expectations documented at call boundaries?
