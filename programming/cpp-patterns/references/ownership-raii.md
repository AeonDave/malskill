# Ownership and RAII

## Mental model

- Ownership answers: who is responsible for releasing a resource.
- Lifetime answers: how long an object remains valid.

Express these in types.

## Prefer value types

Use values and composition first.

```cpp
struct Config {
  std::string host;
  int port{0};
};
```

## Smart pointers

- `std::unique_ptr<T>`: exclusive ownership
- `std::shared_ptr<T>`: shared ownership (avoid by default)
- `std::weak_ptr<T>`: non-owning observer to break cycles

Avoid returning owning raw pointers.

## Non-owning references

- `T&`: required reference
- `T*`: optional pointer (nullable)
- `std::span<T>`: non-owning view over contiguous memory
- `std::string_view`: non-owning view over a string; must not outlive source

## RAII patterns

Wrap resources with types that acquire in constructor and release in destructor.

Examples:
- `std::lock_guard` / `std::unique_lock`
- `std::unique_ptr` with custom deleter
- file handles wrapped in a small class

## Common footguns

- Returning `std::string_view` to a temporary
- Storing pointer/reference to a vector element across reallocation
- Capturing `this` in async work without a lifetime strategy
