# Kotlin ↔ Java Interop

Load when publishing a Kotlin API consumed by Java, wrapping a Java library from Kotlin, or debugging why a Java caller cannot use a Kotlin construct cleanly.

## Nullability across the boundary

- **Java → Kotlin**: unannotated Java references arrive as **platform types** (`String!`). No compiler check; NPE at first dereference if actually null.
  - Fix at the Java source: add `@Nullable` / `@NotNull` (`org.jetbrains.annotations`, `androidx.annotation`, or JSR-305 `javax.annotation`).
  - Fix at the Kotlin call site: assign to a nullable type and null-check, or `checkNotNull(x)` with a clear message.
- **Kotlin → Java**: `T` becomes `@NotNull T`, `T?` becomes `@Nullable T`. IntelliJ/Kotlin JSR-305 annotations propagate; Java sees non-null contracts (but only tools enforce them; the JVM does not).

## Making Kotlin ergonomic from Java

Kotlin features that don't exist in Java need annotations to expose:

| Kotlin feature | Annotation | Effect for Java caller |
|----------------|------------|-------------------------|
| Top-level function in `Utils.kt` | `@file:JvmName("Utils")` at file top | `Utils.foo()` instead of `UtilsKt.foo()` |
| `companion object` function | `@JvmStatic` on the fun | `MyClass.foo()` instead of `MyClass.Companion.foo()` |
| `companion object` const `val` | `const val` (compile-time constant) or `@JvmField` | `MyClass.NAME` as a static field |
| Property with backing field | `@JvmField` | Direct field access, no getter/setter |
| Default arguments | `@JvmOverloads` on the fun | Java sees overloads for each combination |
| Checked exceptions | `@Throws(IOException::class)` | Java `throws` declaration allowed |
| Rename generated method | `@JvmName("readBytes")` | Avoids name clashes / mangling |
| Property getter/setter rename | `@get:JvmName("isReady")` / `@set:JvmName(...)` | Clean bean-style access |

### `@JvmOverloads` example

```kotlin
@JvmOverloads
fun connect(host: String, port: Int = 443, timeoutMs: Int = 5_000): Socket = error("stub")
```

Java sees three overloads (`connect(host)`, `connect(host, port)`, `connect(host, port, timeoutMs)`).

### `@JvmStatic` example

```kotlin
class Metrics {
    companion object {
        @JvmStatic fun record(event: String) { /* … */ }
    }
}
// Java: Metrics.record("x")   // without @JvmStatic: Metrics.Companion.record("x")
```

### `@JvmField` example

```kotlin
class Config {
    @JvmField val version = 1
}
// Java: config.version   // without @JvmField: config.getVersion()
```

Do not use `@JvmField` on `open`/`override` properties or with custom accessors — the field must be a plain backing field.

## SAM conversions

- Java **single-abstract-method interfaces** convert from Kotlin lambdas automatically:
  ```kotlin
  executor.execute { doWork() }  // Runnable
  ```
- Kotlin `fun interface` also supports SAM conversion from Kotlin callers:
  ```kotlin
  fun interface Predicate<T> { fun test(t: T): Boolean }
  val nonEmpty = Predicate<String> { it.isNotEmpty() }
  ```
- Ordinary Kotlin `interface` (non-`fun`) requires an explicit `object : Predicate<String> { override fun test(t: String) = … }` when called from Kotlin, but Java still can't SAM-convert to a Kotlin `interface` unless you make it `fun interface`.

## Exposing suspending functions to Java

- Java cannot call `suspend` functions directly (they carry a hidden `Continuation` parameter).
- Bridge options:
  - Wrap with a callback: `fun fetchAsync(callback: (Outcome<User>) -> Unit)`.
  - Return a `CompletableFuture<T>` via `kotlinx-coroutines-jdk8`:
    ```kotlin
    fun fetchAsync(): CompletableFuture<User> =
        scope.future { fetch() }
    ```
  - Return a `Flow<T>` and consume via `kotlinx-coroutines-reactive` / `Publisher`.

## Collections

- Kotlin `List<T>` = Java `java.util.List<T>` at runtime, but **read-only in Kotlin's type system**.
- A Kotlin function accepting `List<T>` will be given a mutable Java `ArrayList` at runtime — do not cast to `MutableList` inside Kotlin; that's a bug waiting to happen at the Kotlin call site.
- To return a defensive copy: `.toList()` (copies to an immutable-view `ArrayList`).

## Properties vs getters/setters

- Kotlin properties compile to `getX()`/`setX()` (or `isX()` for `Boolean` properties starting with `is`).
  ```kotlin
  var isReady: Boolean = false
  // Java sees: boolean isReady() / void setReady(boolean)
  ```
- If you want a Kotlin `val name: String` seen as a plain field from Java, use `@JvmField` (no `val`/`var` restriction beyond backing field rules).
- To keep symmetric naming (`getName()`/`setName()`), name the property `name` (without `is` prefix).

## Extension functions from Java

- Kotlin extension functions compile to **static** methods with the receiver as the first parameter.
- Java calls them as `StringUtilsKt.trimToNull(myString)` (or the `@file:JvmName` you set).

## Object → Static conversion

- Kotlin `object` = Java `MyObject.INSTANCE.foo()`.
- Add `@JvmStatic` inside the object body to expose members as true static methods:
  ```kotlin
  object Log {
      @JvmStatic fun info(msg: String) { /* … */ }
  }
  // Java: Log.info("x") — without @JvmStatic: Log.INSTANCE.info("x")
  ```

## Data classes from Java

- Java sees `equals`/`hashCode`/`toString`/`getX()` accessors. `copy()` is awkward from Java (all parameters required, no defaults without `@JvmOverloads` — and `@JvmOverloads` on `copy` is not supported).
- Provide a Java-friendly builder if Java consumers need convenient mutation.

## Common footguns

- **Checked exceptions**: Java code calling Kotlin will not require `throws` unless the Kotlin function is annotated `@Throws(...)`. Add it or Java code cannot `catch (IOException)` in a way the compiler accepts for checked handling — the `catch` is rejected as "unreachable".
- **`@JvmField` on delegated properties, `open`, `override`, or `const`**: not allowed; compiler error.
- **Companion object visibility**: private members of a companion object are visible only from Kotlin. Use `@JvmSynthetic` to hide Kotlin-only members from Java.
- **Function types**: `(Int) -> String` compiles to `Function1<Integer, String>`. Java callers must `apply(...)`, not `invoke(...)`. Prefer `fun interface` for API surfaces intended for Java.
- **Reified generics**: `inline fun <reified T>` only works from Kotlin. For Java, take a `Class<T>` parameter.
- **Unsigned types** (`UInt`, `ULong`): still experimental for JVM interop; treated as their signed counterparts from Java. Avoid on public API surfaces consumed by Java.
- **`Nothing` return type**: Java sees `void`. Kotlin uses it for functions that always throw — Java callers must add unreachable code after the call.

## When wrapping a Java library

- Introduce a Kotlin idiomatic facade: sealed `Outcome` instead of `throws`, `Flow<T>` instead of callbacks, `suspend fun` instead of `Future.get()`.
- Bridge via `suspendCancellableCoroutine { cont -> … }` when the Java API is callback-based:
  ```kotlin
  suspend fun fetch(): User = suspendCancellableCoroutine { cont ->
      val call = javaClient.fetch(object : Callback {
          override fun onSuccess(u: User) { cont.resume(u) }
          override fun onError(e: Throwable) { cont.resumeWithException(e) }
      })
      cont.invokeOnCancellation { call.cancel() }
  }
  ```
- Wrap `Future<T>` via `future.await()` (from `kotlinx-coroutines-jdk8`), which respects cancellation.
