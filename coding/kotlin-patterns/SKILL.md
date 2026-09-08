---
name: kotlin-patterns
description: "Idiomatic Kotlin patterns for JVM and Android: null-safety, sealed hierarchies, coroutines and structured concurrency, immutable data modeling, error handling, and Java interop. Use when writing or reviewing `.kt` code, porting Java into Kotlin, designing Android app architecture (ViewModel, repository, Flow), or auditing coroutine cancellation, `runBlocking`, and lifecycle-scoped work."
license: MIT
compatibility: "Kotlin 2.0+ (K2 compiler baseline). Targets: JVM 17+, Android SDK 26+ (guidance covers up to SDK 36). Tools: kotlinc, gradle, detekt, ktlint. Optional: kotlinx-coroutines 1.8+, kotlinx-serialization, Android Jetpack (Lifecycle, ViewModel, Compose)."
metadata:
  author: AeonDave
  version: "1.0"
---

# Kotlin Patterns

Day-to-day idiomatic Kotlin for JVM and Android code. Use `android-testing` for test infrastructure and `mobile-technique` for offensive audit of shipped APKs.

## When to activate

- Writing or refactoring `.kt` modules, libraries, or Android features
- Porting Java code to Kotlin without carrying over Java idioms
- Reviewing PRs for null-safety, coroutine misuse, or leaky lifecycle scopes
- Designing sealed state hierarchies, `Flow` pipelines, or repository APIs
- Deciding between `data class`, `value class`, `object`, and `sealed class`

---

## Core rules (high signal)

- **Nullability is a type**, not a runtime check. Never use `!!` outside test scaffolding or provably non-null bridges — model with `?`, `requireNotNull`, or a sealed result.
- **Prefer immutability**: `val`, `List`/`Map` (read-only interfaces), `data class` with `copy()`. Reach for `var` and `MutableList` only when local mutation is clearer.
- **Suspend, don't block**. In any `suspend` function, blocking calls (JDBC, `Thread.sleep`, blocking I/O) must be wrapped in `withContext(Dispatchers.IO)`; never call `runBlocking` in library, Android UI, or coroutine code.
- **Structured concurrency**: every coroutine runs in a scope with a defined lifetime. `GlobalScope` is a smell; use `viewModelScope`, `lifecycleScope`, or an injected `CoroutineScope` with `SupervisorJob`.
- **Model states with `sealed class`/`sealed interface`**, not boolean flags or nullable pairs. Compiler-enforced exhaustive `when` is the primary correctness tool.
- **Errors as data at boundaries**: return `Result<T>`, a sealed `Outcome`, or a domain-specific type from network/repository layers; reserve exceptions for programmer errors and truly exceptional infra failures.
- **`data class` for values, `value class` for zero-cost typed wrappers, `object` for singletons, `class` when identity or inheritance matters.**
- **Extension functions extend readability, not surface area.** Keep them `internal` or file-private unless the API is intentionally public.

---

## Outcome expectations

- Public APIs make nullability, suspension, and threading obvious at call sites.
- Domain state is modeled with sealed hierarchies; `when` expressions are exhaustive without an `else` branch.
- No unscoped coroutines; cancellation propagates through the call graph.
- No `!!`, no `lateinit var` on shared state, no `runBlocking` in production paths.
- ktlint/detekt run clean; `-Werror` and `-Xexplicit-api=strict` on library modules.

---

## Recommended workflow

1. Sketch the domain: sealed states, value-typed IDs (`@JvmInline value class UserId(val raw: String)`), and repository contracts before implementation.
2. Choose the coroutine boundary. UI collects `StateFlow`; repositories return cold `Flow`; suspend functions declare their dispatcher intent (`withContext`) at the leaf, not the caller.
3. Implement with small `internal`/`private` helpers; split files by responsibility, not by class count.
4. Add null-safety and cancellation-awareness before adding features: every `suspend` fun must let `CancellationException` propagate (never swallow it in a broad `catch (e: Exception)`).
5. Run `./gradlew ktlintCheck detekt test` before review.

---

## Quick review checklist

- No `!!`; `lateinit` only for framework-injected non-null fields (`@Inject`, Android views)
- No `GlobalScope`, `runBlocking`, or `Thread.sleep` in production code paths
- `catch (e: Exception)` blocks re-throw `CancellationException` (or use `catch (e: Throwable)` with `if (e is CancellationException) throw e`)
- `Flow` collectors run in a lifecycle-aware scope (`repeatOnLifecycle(STARTED)` for UI); no `flow.collect { }` inside `lifecycleScope.launch` without a lifecycle state gate
- `sealed` state hierarchies use exhaustive `when` (no `else -> {}` catchall on domain states)
- Data classes representing domain state are `val`-only; mutation goes through `copy()`
- Coroutine builders (`launch`, `async`) attach to a named scope with a `SupervisorJob` when child failure must not cancel siblings
- Public API surface uses `internal` where possible; `expect`/`actual` reserved for genuine multiplatform boundaries

---

## Common anti-patterns to reject

- `!!` sprinkled to satisfy the compiler on nullable receivers
- `runBlocking { }` inside Android code (blocks the main thread) or library code (blocks the caller's thread)
- `GlobalScope.launch { }` — no lifecycle, leaks on config change
- `lateinit var` on shared mutable state instead of `val` + constructor injection
- Swallowing `CancellationException` in a generic `try/catch`
- `when` with `else -> {}` on a sealed hierarchy (silently ignores states added later)
- Extension functions on `Any?` in public APIs (pollutes autocompletion project-wide)
- Java-style getters/setters via `@JvmField`/`@get:JvmName` when the Kotlin property already works for Kotlin consumers

---

## Android-specific patterns

- **ViewModel** owns UI state (`StateFlow<UiState>`); it never touches `Context`, views, or navigation directly. Inject an application-scoped context only when strictly needed.
- **`viewModelScope`** for work tied to the ViewModel; **`lifecycleScope` + `repeatOnLifecycle(Lifecycle.State.STARTED)`** for UI-tied collection. Without the state gate, background work continues on stopped screens.
- **Repository returns cold `Flow`**; caching via `stateIn(scope, SharingStarted.WhileSubscribed(5_000), initial)` at the ViewModel boundary. `SharingStarted.Eagerly` leaks work; `Lazily` never stops.
- **Do not hold `Context`/`View`/`Activity` references across suspend points.** Use `applicationContext` for long-lived scopes; capture what you need before `withContext`.
- **Room DAOs** expose `suspend` for one-shots and `Flow<T>` for queries; never call blocking DAO methods from the main thread.
- **Compose**: state hoisting; `remember` for local UI state; `derivedStateOf` for computed state; `LaunchedEffect(key)` for side effects; never mutate state during composition.

---

## Resources

Load on demand (progressive disclosure):

- [references/coroutines.md](references/coroutines.md) — structured concurrency, dispatchers, cancellation, `Flow` operators, `StateFlow`/`SharedFlow`, testing with `runTest` and virtual time; load when writing or reviewing `suspend` code or diagnosing coroutine leaks
- [references/nullability-and-types.md](references/nullability-and-types.md) — null-safety strategies, platform types from Java, `value class`, `sealed` modeling, delegated properties; load when designing domain types or auditing `!!` and `lateinit` usage
- [references/errors-and-flow-control.md](references/errors-and-flow-control.md) — `Result<T>` vs sealed `Outcome`, exception hygiene, cancellation-safe try/catch, `require`/`check`/`error`; load when designing repository/API error contracts
- [references/java-interop.md](references/java-interop.md) — nullability annotations, `@JvmStatic`/`@JvmOverloads`/`@JvmField`, SAM conversions, checked-exception boundary, calling Kotlin from Java without pain; load when publishing a Kotlin API consumed by Java or wrapping a Java library
- [references/android-architecture.md](references/android-architecture.md) — ViewModel/repository/Flow shape, Hilt DI patterns, lifecycle-aware collection, Compose state hoisting; load when scaffolding a feature module or reviewing lifecycle/leak bugs
