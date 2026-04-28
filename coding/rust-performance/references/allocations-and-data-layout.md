# Allocations and Data Layout

Use this reference when Rust code is losing time to cloning, heap churn, or poor locality.

## Reduce allocation churn

- Pre-allocate with `Vec::with_capacity` or `String::with_capacity` when sizes are predictable
- Reuse buffers instead of recreating them in tight loops
- Borrow data instead of cloning it when ownership is unnecessary
- Avoid building intermediate collections if a streaming iterator pipeline is enough

## Data-layout wins

- Favor contiguous data structures (`Vec`, slices) when iteration is hot
- Keep frequently accessed fields close together when structure layout matters
- Choose representations that match the workload: arrays for fixed-size hot data, enums for tight state machines
- Introduce `SmallVec` / `ArrayVec` only with evidence that small inline storage helps

## Hashers and containers

- The default hasher is safe but not always fastest
- Use faster hashers only when collision resistance is not part of the requirement
- Re-check performance after container changes; the “faster” structure on paper may not win for the real dataset
