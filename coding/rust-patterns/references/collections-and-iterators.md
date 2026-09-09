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
- `collect()` targets any `FromIterator` type — annotate the destination when ambiguous, and a
  `collect()` over `Result<T, E>` items short-circuits on the first error into `Result<Vec<T>, E>`

## `Box<[T]>` by-value vs `.into_iter()`

`IntoIterator` for `Box<[T]>` is 1.80 **all editions**: `for x in boxed` moves
`T`. The Edition 2024 change is the **`.into_iter()` method**: before 2024 it
still auto-deref'd to `&T`; in 2024 it moves `T`. Use `.iter()` / `&boxed` when
you meant borrows; on older editions use `IntoIterator::into_iter(boxed)` to
move.

## Drain and chunk helpers

- `HashMap`/`HashSet::extract_if` (1.88) — yields and **removes** matching
  entries; leftovers stay. Consume the iterator (it is lazy). Use `retain` if
  you only want to drop.
- `BTreeMap`/`BTreeSet::extract_if` (1.91) — same, plus a key **range**
  (`map.extract_if(a..b, |k, v| …)`; `..` for the whole tree).
- `<[T]>::as_chunks` / `as_rchunks` (1.88) — split into `&[[T; N]]` plus a
  remainder. Prefer this over `chunks_exact` when you want arrays (const `N`).
- `<[T]>::array_windows` (1.94) — overlapping `&[T; N]`. The closure pattern
  infers `N`.
- `slice::get_disjoint_mut` (1.86) — `Result`; overlapping or OOB is `Err`.
- `HashMap::get_disjoint_mut` (1.86) — `[Option<&mut V>; N]`; **panics** on
  duplicate keys; missing keys are `None`.

Default `HashMap` hasher is SipHash 1-3 (HashDoS-resistant). Faster hashers
belong in the `rust-performance` skill.

## Footguns to avoid

- Chaining so many adapters that the intent disappears
- Calling `collect()` just to iterate again immediately
- Cloning collection elements when borrowed access is enough
- Using `LinkedList` for ordinary queue/list work; `Vec` or `VecDeque` are usually better
