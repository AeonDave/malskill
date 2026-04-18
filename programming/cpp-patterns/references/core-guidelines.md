# C++ Core Guidelines (distilled)

Use as a checklist, not as a religion.

## High-signal themes

- Prefer RAII and deterministic cleanup.
- Make ownership explicit.
- Avoid naked `new` and `delete`.
- Keep interfaces simple and safe.
- Use types to encode invariants.
- Prefer compile-time checks over runtime checks.

## Useful clusters for daily reviews

- **R (Resource management)**: ownership, lifetime, and leak resistance
- **I/F (Interfaces/Functions)**: explicit contracts and low surprise APIs
- **E (Error handling)**: predictable error transport and recovery strategy
- **CP (Concurrency)**: data race prevention and cancellation discipline
- **Per (Performance)**: measure first, optimize what matters

## References

- C++ Core Guidelines: https://github.com/isocpp/CppCoreGuidelines/blob/master/CppCoreGuidelines.md
