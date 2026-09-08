# JNI References and Exceptions

Load when writing or debugging JNI code: reference lifetimes, exception propagation across the boundary, and thread-attach mechanics.

## Reference types

| Type | Created by | Lifetime | Free with |
|------|-----------|----------|-----------|
| **Local** | Any `Find*`, `New*`, `Call*` returning `jobject` | Current JNI call frame | `DeleteLocalRef` (automatic on return) |
| **Global** | `NewGlobalRef(local)` | Until explicit delete or process exit | `DeleteGlobalRef` |
| **Weak Global** | `NewWeakGlobalRef(local)` | Until GC decides / explicit delete | `DeleteWeakGlobalRef` |

Local references default table size is **512 entries per frame** in Android's implementation (larger than the JNI spec's 16-entry minimum). Overflow aborts with:

```
JNI ERROR (app bug): local reference table overflow (max=512)
```

Symptoms: a loop that creates many locals without freeing.

## Local reference discipline

Wrong (leaks locals):

```cpp
for (jint i = 0; i < 10000; i++) {
    jstring s = env->NewStringUTF("x");
    // use s
    // MISSING: env->DeleteLocalRef(s);
}
```

Right (explicit delete):

```cpp
for (jint i = 0; i < 10000; i++) {
    jstring s = env->NewStringUTF("x");
    // use s
    env->DeleteLocalRef(s);
}
```

Better (scoped frame):

```cpp
env->PushLocalFrame(32);
for (jint i = 0; i < 10000; i++) {
    // batch of ~30 locals here
    if (i % 30 == 29) {
        env->PopLocalFrame(nullptr);
        env->PushLocalFrame(32);
    }
}
env->PopLocalFrame(nullptr);
```

## Global refs

- Convert a local to global when you need to keep it across JNI calls (e.g. store in a native struct, use from a callback thread).
- **Every** `NewGlobalRef` must be paired with `DeleteGlobalRef`; the JVM does not track them per-call. Leaks last until process exit.
- Store globals in a C++ RAII wrapper:
  ```cpp
  class GlobalRef {
      JavaVM* vm_;
      jobject ref_;
   public:
      GlobalRef(JNIEnv* env, jobject local) {
          env->GetJavaVM(&vm_);
          ref_ = env->NewGlobalRef(local);
      }
      ~GlobalRef() {
          JNIEnv* env;
          if (vm_->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6) == JNI_OK) {
              env->DeleteGlobalRef(ref_);
          }
      }
      jobject get() const { return ref_; }
  };
  ```

## Weak global refs

- Referent may be GC'd. Before use, get a strong ref:
  ```cpp
  jobject strong = env->NewLocalRef(weak);
  if (env->IsSameObject(strong, nullptr)) {
      // GC'd — bail out
  } else {
      // use strong
      env->DeleteLocalRef(strong);
  }
  ```
- Rarely needed. Only for observer patterns where the observer must not extend the observed object's lifetime.

## `JNIEnv*` and threads

- `JNIEnv*` is **per-thread**. Do not cache or share across threads.
- Cache `JavaVM*` once (usually in `JNI_OnLoad`) — it's process-wide:
  ```cpp
  static JavaVM* g_vm = nullptr;
  jint JNI_OnLoad(JavaVM* vm, void*) {
      g_vm = vm;
      return JNI_VERSION_1_6;
  }
  ```
- Get the current thread's env, or attach if none:
  ```cpp
  JNIEnv* getEnv() {
      JNIEnv* env;
      jint status = g_vm->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6);
      if (status == JNI_EDETACHED) {
          if (g_vm->AttachCurrentThread(&env, nullptr) != JNI_OK) return nullptr;
      } else if (status != JNI_OK) {
          return nullptr;
      }
      return env;
  }
  ```
- Threads created by pthread that call into Java **must detach before exit**:
  ```cpp
  pthread_key_t key;
  pthread_key_create(&key, [](void*) { g_vm->DetachCurrentThread(); });
  pthread_setspecific(key, reinterpret_cast<void*>(1));
  ```
  Otherwise the JVM leaks per-thread state and eventually crashes.

## Exception model

- Any JNI function that can throw (`FindClass`, `GetFieldID`, `NewObject`, `Call*Method`, ...) may leave an exception pending.
- **A JNI function called with an exception pending is undefined behavior** except for a small allowlist:
  - `DeleteGlobalRef`, `DeleteLocalRef`, `DeleteWeakGlobalRef`
  - `ExceptionCheck`, `ExceptionClear`, `ExceptionDescribe`, `ExceptionOccurred`
  - `MonitorExit`, `PushLocalFrame`, `PopLocalFrame`
  - `Release*Chars`, `Release*ArrayElements`, `ReleasePrimitiveArrayCritical`
- Check after every call that can throw:
  ```cpp
  jclass cls = env->FindClass("com/example/Foo");
  if (env->ExceptionCheck()) return nullptr;
  ```
- Propagate to caller: return early. The Kotlin/Java caller sees the exception.
- Clear (rare, discouraged): `env->ExceptionClear()`. Only when the native code has a real fallback and the exception is truly recoverable.
- Log for debugging: `env->ExceptionDescribe()` prints to logcat then clears.

## C++ exceptions do not cross JNI

A C++ exception unwinding into JNI code aborts the process:

```
terminate called after throwing an instance of 'std::runtime_error'
Aborted (core dumped)
```

Wrap C++ code at the JNI entry point:

```cpp
extern "C" JNIEXPORT jbyteArray JNICALL
Java_com_example_Native_encrypt(JNIEnv* env, jobject, jbyteArray input) {
    try {
        return doEncrypt(env, input);
    } catch (const std::bad_alloc&) {
        env->ThrowNew(env->FindClass("java/lang/OutOfMemoryError"), "native alloc failed");
        return nullptr;
    } catch (const std::exception& e) {
        env->ThrowNew(env->FindClass("java/lang/RuntimeException"), e.what());
        return nullptr;
    } catch (...) {
        env->ThrowNew(env->FindClass("java/lang/RuntimeException"), "unknown native error");
        return nullptr;
    }
}
```

## String access

- `GetStringUTFChars(str, isCopy)` — returns UTF-8 bytes (modified — see below). Must `ReleaseStringUTFChars`.
- `GetStringChars(str, isCopy)` — UTF-16 code units. Must `ReleaseStringChars`.
- `GetStringCritical(str, isCopy)` — pinned UTF-16; must `ReleaseStringCritical` promptly and no JNI calls during the critical region.
- **Modified UTF-8 gotcha**: `GetStringUTFChars` returns **Modified UTF-8** — NUL is encoded as two bytes, characters outside BMP as surrogate pairs. For real UTF-8, use `GetStringChars` then encode manually or use `env->NewString` + your own converter.

## Array access

- `Get<Type>ArrayElements` — copies or pins, `mode` in `Release`:
  - `0` — copy back changes, free
  - `JNI_COMMIT` — copy back but do not free
  - `JNI_ABORT` — free without copy-back
- `Get<Type>ArrayRegion` / `Set<Type>ArrayRegion` — copy a subrange in/out; simpler and safe.
- `GetPrimitiveArrayCritical` — zero-copy pin; **no JNI calls or blocking** during the critical region:
  ```cpp
  auto* buf = static_cast<jbyte*>(env->GetPrimitiveArrayCritical(arr, nullptr));
  if (env->ExceptionCheck()) return;
  // use buf — MUST NOT call any JNI or blocking function
  env->ReleasePrimitiveArrayCritical(arr, buf, 0);
  ```
  Ideal for tight numeric loops. Extended critical regions block the GC and other threads.

## `ByteBuffer` direct buffers (zero-copy option)

For large buffers shared between Kotlin and native:

```kotlin
val buffer = ByteBuffer.allocateDirect(1024 * 1024)
native.processBuffer(buffer)
```

```cpp
JNIEXPORT void JNICALL
Java_com_example_Native_processBuffer(JNIEnv* env, jobject, jobject buffer) {
    void* addr = env->GetDirectBufferAddress(buffer);
    jlong cap = env->GetDirectBufferCapacity(buffer);
    // use addr directly, no copy
}
```

- Zero-copy for the buffer contents.
- Kotlin `ByteBuffer.allocateDirect(n)` allocates off-heap; released when the ByteBuffer becomes unreachable.
- Not suitable if the native side must retain the pointer past the JNI call — the JVM may move or free the buffer.

## Method / field IDs

- `GetMethodID` / `GetFieldID` return an ID valid for the lifetime of the loaded class. Cache once, use forever:
  ```cpp
  static jmethodID g_callbackMethod = nullptr;
  jint JNI_OnLoad(JavaVM* vm, void*) {
      JNIEnv* env;
      vm->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6);
      jclass cls = env->FindClass("com/example/Callback");
      g_callbackMethod = env->GetMethodID(cls, "onResult", "(I)V");
      env->DeleteLocalRef(cls);
      return JNI_VERSION_1_6;
  }
  ```
- Do not cache IDs across class-loader reloads (rare in Android — dynamic feature modules can trigger).

## Common diagnostic messages

| Message | Cause |
|---------|-------|
| `JNI ERROR (app bug): local reference table overflow (max=512)` | Loop creating locals without freeing |
| `JNI DETECTED ERROR IN APPLICATION: use of invalid jobject` | Using a local after JNI return, or a deleted global |
| `JNI DETECTED ERROR IN APPLICATION: called with exception pending` | Missing `ExceptionCheck` after a throwing call |
| `art_quick_generic_jni_trampoline` in stack trace | Native call is happening; source is one frame down |
| `JavaVM::GetEnv() failed` | Called from a non-attached native thread |
