# Errors and Flow Control

Load when designing repository/API error contracts, auditing exception handling, or deciding between `Result<T>`, sealed outcomes, and thrown exceptions.

## When to throw, when to return

- **Throw** for programmer errors (bad argument, illegal state, contract violation) — `require`, `check`, `error`, `IllegalArgumentException`, `IllegalStateException`.
- **Return** for expected failure modes (network down, not-found, validation failed) — sealed `Outcome` / `Either` / `Result<T>`.
- **Fatal errors** (`OutOfMemoryError`, `StackOverflowError`) are `Error` — never catch them broadly.
- **`CancellationException`** is control flow, not error. Always re-throw. See coroutines reference.

## `require` / `check` / `error`

| Function | Throws | Meaning |
|----------|--------|---------|
| `require(x > 0)` | `IllegalArgumentException` | Precondition on parameter |
| `requireNotNull(x)` | `IllegalArgumentException` | Non-null parameter |
| `check(state == READY)` | `IllegalStateException` | Object invariant/state |
| `checkNotNull(cache)` | `IllegalStateException` | State invariant on lazy field |
| `error("unreachable")` | `IllegalStateException` | Should never happen |

Use these at the top of functions and after state transitions. They document the contract and produce specific, greppable messages.

## `Result<T>` (stdlib)

- `Result.success(v)` / `Result.failure(e)`. Access with `getOrNull()`, `getOrThrow()`, `getOrElse { }`, `fold(onSuccess, onFailure)`.
- Not designed as a return type in general APIs — Kotlin docs warn against it and the compiler emits a warning by default for `Result` return types. Use it inside a function to capture-then-branch, or opt-in with `@OptIn(ExperimentalStdlibApi::class)` for library boundaries.
- `runCatching { }` builds a `Result`, catching `Throwable` **including `CancellationException`**. Inside `suspend` code, wrap:

```kotlin
val result = runCatching { risky() }
    .onFailure { if (it is CancellationException) throw it }
```

Or write the try/catch manually — usually clearer.

## Sealed `Outcome<T>` (idiomatic)

- Preferred for public repository/API contracts. Compiler enforces exhaustive handling and callers can pattern-match domain errors.

```kotlin
sealed interface Outcome<out T> {
    data class Success<T>(val value: T) : Outcome<T>
    sealed interface Error : Outcome<Nothing> {
        data object Network : Error
        data class Http(val code: Int) : Error
        data class Unknown(val cause: Throwable) : Error
    }
}

suspend fun fetchUser(id: UserId): Outcome<User> = try {
    Outcome.Success(api.getUser(id.raw))
} catch (e: CancellationException) {
    throw e
} catch (e: IOException) {
    Outcome.Error.Network
} catch (e: HttpException) {
    Outcome.Error.Http(e.code)
} catch (e: Throwable) {
    Outcome.Error.Unknown(e)
}
```

Callers `when` on the outcome and handle every branch.

## `try`/`catch` hygiene

- Catch the **narrowest** type that can actually be thrown. `catch (e: Exception)` is almost always too broad.
- Order specific-to-general.
- In `suspend` code, re-throw `CancellationException` (see coroutines reference).
- Do not use exceptions for control flow (`try { list[i] } catch (e: IndexOutOfBoundsException) { … }` — use `getOrNull(i)`).
- Do not log-and-swallow. Either handle (transform to `Outcome` / recover / default) or propagate.

## `elvis` and early returns

Prefer flat control flow with Elvis:

```kotlin
val cached = cache[key] ?: return fetchRemote(key)
val user = repo.find(id) ?: throw NotFoundException(id)
```

vs deeply nested `if (x != null) { … }`.

## `takeIf` / `takeUnless`

```kotlin
val trimmed = input.trim().takeIf { it.isNotEmpty() }
val nonAdmin = user.takeUnless { it.isAdmin }
```

Combines a filter and a nullable in one expression. Prefer over `if (x != null && cond(x)) x else null`.

## Scope functions (`let` / `run` / `apply` / `also` / `with`)

| Function | Receiver | Returns | Typical use |
|----------|----------|---------|-------------|
| `let { it -> }` | `it` | block result | nullable chain: `x?.let { f(it) }` |
| `run { this -> }` | `this` | block result | multi-step compute on a receiver |
| `apply { this -> }` | `this` | receiver | mutating builder-style config |
| `also { it -> }` | `it` | receiver | side-effect (log, debug) in a chain |
| `with(x) { this -> }` | `this` | block result | non-chained multi-op on a value |

Rule of thumb: use `let` for null-safety, `apply` for builder configuration, `also` for side effects. Do not nest scope functions — readability collapses fast.

## `TODO()` / `NotImplementedError`

- `TODO("finish auth")` — throws `NotImplementedError` with a message. Use as a stub, not a runtime "not supported" marker.
- Ship code with `TODO()` only in tests or scaffolding. Detekt/ktlint can be configured to fail on it.

## Coroutine-safe error handling checklist

- No `runCatching { }` in `suspend` code without a `CancellationException` re-throw.
- `catch (e: Exception)` and `catch (e: Throwable)` both catch `CancellationException` — audit and re-throw.
- `try/finally` around resource use: `finally` runs on cancellation too. Use `NonCancellable` (`withContext(NonCancellable) { … }`) only for cleanup that must complete.
- `supervisorScope { }` isolates child failure; a normal `coroutineScope { }` cancels siblings on any child failure — pick deliberately.

## Java interop

- Kotlin has no checked exceptions. Java code calling Kotlin gets unchecked exceptions.
- Annotate Kotlin functions with `@Throws(IOException::class)` when Java callers must declare `throws`. Without it, Java code cannot `catch (IOException)` for a checked exception path (the compiler will reject it).
- `Result<T>` and sealed hierarchies are awkward from Java — expose a Java-friendly overload that throws or a callback API for consumers stuck on Java.
