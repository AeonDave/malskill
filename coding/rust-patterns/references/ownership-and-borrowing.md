# Ownership and Borrowing

Use this reference when signatures, moves, lifetimes, or borrow-checker friction are the main problem.

## Default rules

- Borrow read-only inputs by default: `&str`, `&[T]`, `&Path`, `&T`
- Borrow mutably only when the caller expects in-place mutation: `&mut T`
- Take ownership when the function stores data, spawns work, or returns transformed values with an independent lifetime
- Return owned values at parsing / IO / process boundaries; use borrowing inside hot inner code

## High-signal fixes for borrow-checker friction

- Narrow scopes so borrows end sooner
- Extract helper functions to shorten conflicting borrows
- Compute lookup keys before taking mutable references
- Prefer stable keys or indexes over long-lived references into collections
- Use `Option::take`, `std::mem::take`, or `std::mem::replace` for move-out patterns

## Avoid these habits

- `clone()` used only to appease the compiler
- `Rc<RefCell<T>>` as a default design instead of a deliberate interior-mutability choice
- `Arc<Mutex<T>>` for every shared value without first designing ownership and synchronization clearly
- self-referential structs in safe code

## Ownership signals in common types

- `Box<T>` — owned heap value with single owner
- `Rc<T>` / `Arc<T>` — shared ownership; use only when the sharing is real
- `Cow<'a, T>` — sometimes borrow, sometimes own
- `String` vs `&str`, `Vec<T>` vs `&[T]` — own only when storage or mutation is required
