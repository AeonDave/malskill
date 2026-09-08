# `@FastNative` and `@CriticalNative`

Load when a native call is on a measured hot path (> 1 M ops/sec) and the JNI transition dominates the profile.

## Cost tiers (Android runtime docs baseline, still directional in 2026)

| Call type | ns/call (Android 8+ arm64) |
|-----------|----------------------------|
| Regular JNI | ~115 ns |
| `!bang` JNI (deprecated) | ~60 ns |
| `@FastNative` | ~35 ns |
| `@CriticalNative` | ~25 ns (nearly free on Android 12+ from compiled managed code) |

Numbers scale down on newer devices; ordering is stable.

## The catch: annotations not in the public SDK

The annotations live in `dalvik.annotation.optimization` — not shipped in the public `android.jar`. To use them, declare the classes in your project (they're purely marker annotations recognized by ART):

`app/src/main/java/dalvik/annotation/optimization/FastNative.java`:

```java
package dalvik.annotation.optimization;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

@Retention(RetentionPolicy.CLASS)
@Target(ElementType.METHOD)
public @interface FastNative {}
```

`app/src/main/java/dalvik/annotation/optimization/CriticalNative.java`:

```java
package dalvik.annotation.optimization;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

@Retention(RetentionPolicy.CLASS)
@Target(ElementType.METHOD)
public @interface CriticalNative {}
```

ART sees the package name and treats the annotation as its own. No JAR conflict — dalvik.annotation.optimization is only present in your own app.

## `@FastNative` — restrictions

- Removes internal locking around the JNI transition.
- **GC cannot suspend** the thread during a `@FastNative` call → do not perform long I/O, do not acquire long-held native locks.
- Otherwise same signature as regular JNI (`JNIEnv*` + `jobject this` still present).
- Safe for cheap, bounded operations: hashing, small buffer transforms, primitive computation.

Example:

```kotlin
class Hasher {
    @dalvik.annotation.optimization.FastNative
    external fun hash(input: ByteArray, len: Int): Long
    companion object { init { System.loadLibrary("hasher") } }
}
```

```cpp
extern "C" JNIEXPORT jlong JNICALL
Java_com_example_Hasher_hash(JNIEnv* env, jobject /* this */,
                              jbyteArray input, jint len) {
    jbyte buf[512];
    env->GetByteArrayRegion(input, 0, len, buf);
    return doHash(buf, len);
}
```

## `@CriticalNative` — restrictions

- Removes **both** `JNIEnv*` and `jobject this`/`jclass` parameters.
- Must be `static`.
- Parameters and return must be **primitive types only** (no `jobject`, no arrays, no `jstring`).
- Cannot call back into JVM.
- GC cannot suspend, same as `@FastNative`.

Kotlin declaration:

```kotlin
object CryptoMath {
    @dalvik.annotation.optimization.CriticalNative
    @JvmStatic external fun mixInts(a: Int, b: Int, c: Int): Int

    init { System.loadLibrary("crypto_math") }
}
```

Native declaration (drop `JNIEnv*` and `jclass`):

```cpp
extern "C" JNIEXPORT jint JNICALL
Java_com_example_CryptoMath_mixInts(jint a, jint b, jint c) {
    return (a * 0x9E3779B1) ^ (b << 13) ^ (c >> 7);
}
```

The C linkage name is `Java_<class>_<method>` as usual, but the parameter list omits the standard first two — ART generates a compatible calling convention.

## `RegisterNatives` recommendation

Google explicitly recommends explicit `RegisterNatives` binding for `@FastNative`/`@CriticalNative` methods rather than name-based JNI discovery:

- Faster resolution (no first-call lookup cost).
- Removes symbol names from the shipped `.so` (offensive: harder to hook by symbol; defensive: harder for attackers to find).
- Required correctness for `@CriticalNative` since the JNI signature differs from the standard.

```cpp
static const JNINativeMethod kMethods[] = {
    {"mixInts", "(III)I", reinterpret_cast<void*>(mixInts_impl)},
};

jint JNI_OnLoad(JavaVM* vm, void*) {
    JNIEnv* env;
    if (vm->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6) != JNI_OK) return -1;
    jclass cls = env->FindClass("com/example/CryptoMath");
    env->RegisterNatives(cls, kMethods, sizeof(kMethods) / sizeof(*kMethods));
    env->DeleteLocalRef(cls);
    return JNI_VERSION_1_6;
}
```

## Baseline Profile

Include callers of `@FastNative`/`@CriticalNative` methods in the Baseline Profile — ART pre-compiles the caller side, achieving near-zero transition cost. See `kotlin-performance/references/baseline-and-startup-profiles.md`.

## When the win is real

- Call frequency > 100k ops/sec on a hot path.
- Native work per call is small (< 1 µs) — otherwise the native code dominates and the transition savings are noise.
- The function is called from Kotlin/Java code that itself is compiled (baseline profiled or in-app JIT'd).

If you're calling a JNI function 100 times per second, the savings are irrelevant. Focus on real bottlenecks per Perfetto trace or Microbenchmark first.

## Anti-patterns

- **`@CriticalNative` on a function that internally calls `env->NewStringUTF`** — undefined behavior, no `JNIEnv*` available. Compiler cannot catch this.
- **`@FastNative`/`@CriticalNative` on a function that does synchronous I/O** — blocks the whole process's GC.
- **Copying the entire `dalvik.annotation.optimization` package into a shared library** — unnecessary; only your app needs the class definitions.
- **Enabling on cold paths** — no measurable win, adds testing surface.
- **Ignoring RegisterNatives** — first call still pays name-based lookup and per-lookup cost. Explicit registration is a one-line win.
- **Assuming behavior on emulator** — measurements vary widely; test on a physical device.

## Verifying the annotation is honored

Profile with `simpleperf` and look at what stub the caller lands in:

```bash
adb shell simpleperf record -p $(pidof com.example.app) -o /data/local/tmp/perf.data
adb pull /data/local/tmp/perf.data
simpleperf report -g | grep -E "mixInts|art_quick|art_jni"
```

`art_quick_generic_jni_trampoline` in the caller's stack means the transition is going through the generic (slow) path — the annotation is not being honored (typical causes: annotation class not on the class path, method not `static`, non-primitive param on a `@CriticalNative` method, or the caller itself is not compiled).

When `@FastNative` / `@CriticalNative` is honored, the compiled caller inlines a direct call to the native symbol; you will not see the generic JNI trampoline for that frame. Confirm by disassembling the ART-compiled method with `oatdump`:

```bash
adb shell cmd package compile -m speed -f com.example.app
adb shell find /data/misc/apexdata/com.android.art -name '*.odex' | head
# Pull the .odex and run oatdump from the host NDK/AOSP prebuilts:
oatdump --oat-file=base.odex --method="long com.example.Hasher.hash(byte[], int)"
```

AOT logging (`dalvik.vm.extra-opts -verbose:jit` per AOSP JIT docs) shows JIT decisions but does not surface a dedicated fast-native marker — use `simpleperf` + `oatdump` instead.
