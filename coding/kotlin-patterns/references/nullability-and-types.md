# Null-safety, Value Types, and Sealed Modeling

Load when designing domain types, auditing `!!`/`lateinit` usage, or wrapping Java APIs whose nullability is unclear.

## Nullability

- `T` is non-null. `T?` is nullable. There is no third state.
- The compiler tracks smart-casts within a scope: `if (x != null) { x.foo() }` works if `x` is a `val` (or a local `var` not captured by a closure).
- `?.` (safe call) returns `null` on receiver null. `?:` (Elvis) supplies a default: `name ?: "unknown"`.
- `!!` asserts non-null and throws `NullPointerException` on failure. Every `!!` is a runtime assertion — treat it as a bug in review.

### Platform types (Java interop)

- A Java `String` reference is `String!` in Kotlin — nullability unknown. The compiler will not warn.
- Fix by annotating the Java source (`@Nullable`, `@NotNull` from Jetbrains or JSR-305) or by explicit null-check in the Kotlin call site.
- Never assign a platform type to a non-null Kotlin `val` without a check — you get a delayed NPE at first use.

### `lateinit` vs nullable `var` vs delegate

- `lateinit var` — non-null reference initialized after construction. Use for DI-injected fields (`@Inject`, Dagger/Hilt), test setup (`@Before`), and Android view refs.
  - Restrictions: not for primitives, not for nullable types, not for `val`. Reading before init throws `UninitializedPropertyAccessException`.
  - Check with `::field.isInitialized` when initialization is conditional.
- `var x: T? = null` — when null is a legitimate state.
- `by lazy { }` — thread-safe (`LazyThreadSafetyMode.SYNCHRONIZED` default) one-time initialization for immutable references.
- `by Delegates.notNull<T>()` — like `lateinit` but for primitives.

## Value classes (`@JvmInline value class`)

- Zero-cost wrapper around a single value. Compiler erases the wrapper at the JVM bytecode level when possible.

```kotlin
@JvmInline
value class UserId(val raw: String) {
    init { require(raw.isNotBlank()) }
}
@JvmInline
value class Millis(val value: Long)
```

- Use for typed IDs, units, currency amounts — anything where mixing raw types is a bug (calling `deleteUser(orderId)` compiles when both are `String`).
- Restrictions: single `val` property, no init blocks that mutate, no backing fields on other properties, cannot extend classes.
- Boxing happens when: used as generic type parameter, put in a collection, passed as `Any`, used in reflection. Design accordingly for hot paths.

## `data class` vs `class` vs `object`

- `data class` — compiler generates `equals`/`hashCode`/`toString`/`copy`/`componentN`. Use for values (DTOs, UI state). Prefer `val` properties.
  - `copy()` uses structural equality; use for immutable updates: `state.copy(loading = false)`.
  - Avoid `data class` with `var` — mutation defeats structural equality and breaks `HashMap` invariants.
- `class` — identity-based equality by default. Use when identity matters (services, stateful objects) or when you need custom `equals`.
- `object` — singleton with lazy thread-safe init. Use for stateless helpers, sealed subclasses with no state (`data object Loading` since Kotlin 1.9), and companion objects.
- `data object` — like `object` but with a nicer `toString`. Use for singleton members of a sealed hierarchy.

## Sealed hierarchies

- `sealed class` / `sealed interface` — closed hierarchy known at compile time. Subclasses declared in the same package (or same module for `sealed interface`).
- Enables exhaustive `when` **as an expression**:

```kotlin
sealed interface UiState {
    data object Loading : UiState
    data class Loaded(val items: List<Item>) : UiState
    data class Error(val cause: Throwable) : UiState
}

val text = when (state) {
    is UiState.Loading -> "…"
    is UiState.Loaded  -> "${state.items.size} items"
    is UiState.Error   -> state.cause.message ?: "error"
}
```

- **No `else -> {}`** on domain sealed hierarchies. Adding a new subclass is a compile error at every `when` — that's the point.
- Prefer `sealed interface` for open extension across modules; prefer `sealed class` when you need shared state or a common constructor.

## `enum` vs sealed

| Use | Shape |
|-----|-------|
| Fixed set of value-only cases with no per-case state | `enum class` |
| Cases may carry different data | `sealed class`/`sealed interface` |
| Serialization must be a string constant | `enum class` (with `@SerialName`) |

## Nullable collections

- `List<T>?` vs `List<T?>` vs `List<T?>?` are three different things. Choose deliberately.
- Return an empty list, never `null`, from repository queries: `emptyList()` is free (singleton) and eliminates a null check at every call site.
- `mapNotNull { }`, `filterNotNull()`, `getOrNull()`, `firstOrNull()` — canonical operators for null-tolerant flows.

## Delegates worth knowing

- `by lazy { }` — one-time init, thread-safe by default.
- `Delegates.observable(initial) { _, old, new -> … }` — callback on every set.
- `Delegates.vetoable(initial) { _, old, new -> new > old }` — reject writes returning `false`.
- Custom delegate: implement `getValue`/`setValue` or use `ReadOnlyProperty`/`ReadWriteProperty`. Useful for `SharedPreferences` wrappers, DataStore accessors, `SavedStateHandle` bindings.

## Extension functions

- Resolved statically at the call site's compile-time type, not the runtime type. `open` receivers do not give polymorphic behavior via extensions.
- Do not extend `Any?` in public APIs — pollutes autocompletion everywhere.
- File-private extensions (`private fun String.…`) are the right home for one-off helpers.
- Do not shadow a member function with an extension — the member always wins, silently.
