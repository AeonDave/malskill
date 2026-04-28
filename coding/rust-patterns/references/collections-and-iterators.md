# Collections and Iterators

Use this reference when choosing collections or cleaning up loop-heavy Rust.

## Collection defaults

- `Vec<T>` is the default sequence type
- `HashMap<K, V>` is the default key/value structure when ordering does not matter
- `BTreeMap` / `BTreeSet` are useful when order, range queries, or deterministic iteration matter
- Reach for specialized containers only after measuring or when the semantics demand them

## Iterator guidance

- Prefer iterator adapters when they make the transformation clearer than a manual loop
- Prefer a manual loop when stateful control flow or error handling would become harder to read
- Avoid collecting intermediate `Vec`s unless you truly need ownership or random access
- Use `filter_map`, `find_map`, `flat_map`, and `try_fold` to compress common patterns cleanly

## Footguns to avoid

- Chaining so many adapters that the intent disappears
- Calling `collect()` just to iterate again immediately
- Cloning collection elements when borrowed access is enough
- Using `LinkedList` for ordinary queue/list work; `Vec` or `VecDeque` are usually better
