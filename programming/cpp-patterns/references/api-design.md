# API design

## Principles

- Prefer small interfaces.
- Make lifetimes and ownership explicit.
- Keep exception safety guarantees clear (basic/strong/no-throw).

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

## Return by value

Return by value when reasonable; rely on move elision.

## Views

Use `std::span` and `std::string_view` for non-owning input parameters, but never store them without ensuring the backing storage outlives the view.
