# Rust on Android (JNI)

Load when embedding a Rust library in an Android app or evaluating Rust for a new native module.

## Why Rust for Android native code

- Memory safety without GC → fewer tombstones than equivalent C/C++.
- Rich ecosystem for security-critical code (`ring`, `rustls`, protobuf).
- Chrome (`libcronet`), Firefox, Cloudflare Warp, and AOSP itself (Bluetooth stack, KeyMint, DNS resolver) ship Rust on Android.
- `jni-rs` crate provides safe wrappers around JNI primitives.

## Toolchain: `cargo-ndk`

Install:

```bash
cargo install cargo-ndk
rustup target add aarch64-linux-android armv7-linux-androideabi x86_64-linux-android i686-linux-android
```

`cargo-ndk` invokes `cargo` with the correct target triple, sysroot, and linker per Android ABI.

## Cargo.toml

```toml
[package]
name = "my_native_lib"
version = "0.1.0"
edition = "2021"

[lib]
name = "my_native_lib"
crate-type = ["cdylib"]         # produces .so

[dependencies]
jni = { version = "0.21", default-features = false }
```

## Cross-building

```bash
cargo ndk \
    -t arm64-v8a -t armeabi-v7a -t x86_64 \
    -o app/src/main/jniLibs \
    build --release
```

Output structure matches what Android expects:

```
app/src/main/jniLibs/
├── arm64-v8a/libmy_native_lib.so
├── armeabi-v7a/libmy_native_lib.so
└── x86_64/libmy_native_lib.so
```

## 16 KB page alignment

`.cargo/config.toml`:

```toml
[target.aarch64-linux-android]
rustflags = ["-Clink-arg=-Wl,-z,max-page-size=16384"]

[target.x86_64-linux-android]
rustflags = ["-Clink-arg=-Wl,-z,max-page-size=16384"]
```

Verify with `llvm-readelf -lW libmy_native_lib.so`.

## Kotlin declaration

```kotlin
class RustHasher {
    external fun hash(input: ByteArray): Long
    companion object { init { System.loadLibrary("my_native_lib") } }
}
```

## Rust implementation

```rust
use jni::JNIEnv;
use jni::objects::{JClass, JByteArray};
use jni::sys::jlong;

#[no_mangle]
pub extern "system" fn Java_com_example_RustHasher_hash(
    mut env: JNIEnv,
    _class: JClass,
    input: JByteArray,
) -> jlong {
    let bytes = match env.convert_byte_array(&input) {
        Ok(b) => b,
        Err(_) => return 0,
    };
    doHash(&bytes) as jlong
}

fn doHash(bytes: &[u8]) -> u64 {
    bytes.iter().fold(0u64, |acc, &b| acc.wrapping_mul(31).wrapping_add(b as u64))
}
```

## Panic containment

A Rust `panic!` unwinding into JNI = process abort. Always wrap the entry:

```rust
use std::panic::{catch_unwind, AssertUnwindSafe};

#[no_mangle]
pub extern "system" fn Java_com_example_RustHasher_hash(
    mut env: JNIEnv,
    _class: JClass,
    input: JByteArray,
) -> jlong {
    let result = catch_unwind(AssertUnwindSafe(|| {
        let bytes = env.convert_byte_array(&input)?;
        Ok::<u64, jni::errors::Error>(doHash(&bytes))
    }));
    match result {
        Ok(Ok(v)) => v as jlong,
        Ok(Err(e)) => {
            let _ = env.throw_new("java/lang/RuntimeException", format!("{:?}", e));
            0
        }
        Err(_) => {
            let _ = env.throw_new("java/lang/RuntimeException", "rust panic");
            0
        }
    }
}
```

Or configure the crate for `panic = "abort"`:

```toml
[profile.release]
panic = "abort"
```

This trades panic messages for smaller binaries and no unwind cost. Use `catch_unwind` only when panic messages matter.

## Exception propagation

`jni-rs` returns `Result<_, jni::errors::Error>` — most operations can throw. Handle at the JNI boundary; do not let errors propagate as Rust `Result` past the `extern` function (Java caller sees a return value, not a Result).

Throw a Java exception:

```rust
if !env.exception_check()? {
    env.throw_new("java/lang/IllegalArgumentException", "bad input")?;
}
```

`jni::errors::Error::JavaException` is returned by any operation called with a pending exception — check with `exception_check()` before proceeding.

## Reference handling

`jni-rs` uses **auto-locals** — every operation returning an object reference (`JObject<'local>`) is tied to the enclosing `JNIEnv` frame lifetime; local refs auto-freed at scope end.

For work spanning multiple JNI calls, promote to global:

```rust
use jni::objects::GlobalRef;

let global: GlobalRef = env.new_global_ref(local_obj)?;
// use global across multiple calls
```

`GlobalRef` implements `Drop` — automatically calls `DeleteGlobalRef` when dropped.

## Threads and `JavaVM`

Get the VM once:

```rust
static VM: OnceCell<JavaVM> = OnceCell::new();

#[no_mangle]
pub extern "system" fn JNI_OnLoad(vm: JavaVM, _: *mut c_void) -> jint {
    VM.set(vm).expect("JNI_OnLoad called twice");
    JNI_VERSION_1_6
}
```

Attach a Rust-created thread:

```rust
std::thread::spawn(|| {
    let mut env = VM.get().unwrap().attach_current_thread().unwrap();
    // use env
});   // detaches on drop
```

`attach_current_thread` returns a guard that detaches when dropped. Do not manually call `DetachCurrentThread`.

## Async Rust across JNI

Callbacks: pass a Kotlin lambda (as `JObject`), promote to `GlobalRef`, invoke from a spawned thread.

Coroutine-friendly bridge with `tokio`:

```rust
static RUNTIME: OnceCell<tokio::runtime::Runtime> = OnceCell::new();

#[no_mangle]
pub extern "system" fn Java_com_example_Async_fetch(
    mut env: JNIEnv,
    _class: JClass,
    url: JString,
    callback: JObject,   // Kotlin (Result<String>) -> Unit
) {
    let rt = RUNTIME.get_or_init(|| tokio::runtime::Runtime::new().unwrap());
    let url_str = env.get_string(&url).unwrap().to_string_lossy().into_owned();
    let callback: GlobalRef = env.new_global_ref(callback).unwrap();
    let vm = VM.get().unwrap();

    rt.spawn(async move {
        let result = reqwest::get(&url_str).await;
        let mut env = vm.attach_current_thread().unwrap();
        match result {
            Ok(r) => {
                let body = r.text().await.unwrap_or_default();
                let jbody = env.new_string(body).unwrap();
                env.call_method(&callback, "invoke", "(Ljava/lang/Object;)Ljava/lang/Object;",
                                &[(&jbody).into()]).ok();
            }
            Err(_) => { /* propagate error to Kotlin */ }
        }
    });
}
```

Simpler: use `uniffi` (Mozilla) which generates bindings from a Rust interface. Or `mozilla/rust-android-gradle` for Gradle integration.

## Gradle integration

Manual (recommended for small projects): call `cargo ndk` from a Gradle task:

```kotlin
tasks.register<Exec>("cargoBuild") {
    workingDir = file("src/main/rust")
    commandLine("cargo", "ndk",
        "-t", "arm64-v8a", "-t", "armeabi-v7a", "-t", "x86_64",
        "-o", "../jniLibs", "build", "--release")
}
tasks.named("preBuild") { dependsOn("cargoBuild") }
```

Automated: `org.mozilla.rust-android-gradle:plugin` for large multi-module Rust builds. Handles ABI matrix and target syncing.

## Anti-patterns

- Ignoring `catch_unwind` → any `unwrap()` on unexpected input aborts the process.
- Returning `Result<T, E>` from an `extern "system"` function → Java caller sees a garbled return value.
- `.clone()` on `GlobalRef` in a hot path → each clone is a JNI call to `NewGlobalRef`. Cache references.
- Blocking Rust code on `Dispatchers.Main` — the callback lambda from Kotlin may capture a lifecycle. Always call back on a background thread.
- Depending on `std::thread::park` inside a JNI call — blocks the ART thread and eventually the GC.
- Using unstable Rust features that break `cargo-ndk` cross-compilation. Stick to stable.
- Panicking with sensitive info in the message → exception message shipped to Kotlin caller may leak to crash reporter.

## When to prefer Rust over C++

- Handling untrusted network / crypto / parsing — memory safety directly reduces attack surface.
- Sharing code with a desktop/server component (Rust supports macOS, Linux, Windows, Wasm from the same crate).
- New modules where the team has Rust expertise; migration piecemeal.

When to stay with C++:

- Existing large C++ codebase — `extern "C"` boundary is simpler than porting.
- Framework interop where types are C++ (e.g. NDK Camera2 API).
- Real-time audio/video paths where the C++ ecosystem (Oboe, MediaCodec extensions) is deeper.
