# Native Memory and Ref Leaks

Load when investigating native heap growth, native OOM, or retained JNI references. Use [native-crashes-and-debugging.md](native-crashes-and-debugging.md) for memory-corruption reports and detector selection.

## Separate retention from allocation growth

Compare the same workload and lifecycle state across repeated runs. Record native allocations, managed heap, mapped/shared memory, and the process exit reason.

- `dumpsys meminfo <pkg>` is a starting classification, not proof of a leak. Growth can reflect caches, allocator retention, mapped resources, or a changed workload.
- A JNI global reference keeps its managed referent reachable. Inspect JNI reference ownership and the managed objects retained by it; do not assign every increase in the `Unknown` category to JNI.
- Check actual allocation/free stacks before calling an OOM a native leak. A low-memory kill and a sanitizer-detected invalid access require different follow-up.

## Native allocation profiling

Use [Perfetto heapprofd](https://perfetto.dev/docs/data-sources/native-heap-profiler) on supported Android 10+ test environments. Check the target's profiling permissions and build configuration first.

```
data_sources {
    config {
        name: "android.heapprofd"
        heapprofd_config {
            sampling_interval_bytes: 4096
            process_cmdline: "com.example.app"
        }
    }
}
```

This is sampling, not an exhaustive allocation log. Inspect allocation/free trends and retained bytes by stack; capture startup when the suspected allocations precede attach. Keep symbols matching the loaded native build.

For allocation guards, backtraces, or exit-time tracking, use the options supported by the pinned [bionic malloc-debug implementation](https://android.googlesource.com/platform/bionic/+/refs/heads/main/libc/malloc_debug/README.md). App developers can use a properly packaged [debuggable-app wrap script](https://developer.android.com/ndk/guides/wrap-script); device-wide property workflows have different privilege requirements. Do not invent allocator options or assume a rooted-device recipe works on a stock app.

## LeakSanitizer qualification

[LSan](https://clang.llvm.org/docs/LeakSanitizer.html) supports Android, but verify the selected compiler/runtime/ABI and invocation rather than assuming any ASan build runs leak checks.

- Use a small test-only known leak to confirm that the configured detector produces a report.
- Establish when leak checking occurs. A process killed by a signal may never execute exit handlers; absence of an exit-time report is then inconclusive.
- Keep leak detection failures visible to the test runner. Do not suppress the exit code merely to obtain a green run.
- Treat a clean check as evidence for that run and root set; reachable retained objects can still violate application ownership expectations.

## JNI and direct-buffer ownership

Use Android Studio's JNI heap view to inspect global-reference creation/deletion and their retained objects. CheckJNI helps detect invalid JNI use, but is not a complete leak detector. Follow the [JNI reference contract](jni-refs-and-exceptions.md) for native-thread cleanup and reference lifetimes.

For direct buffers, define who owns the allocation and how long native code may retain its address. Retain a strong reference when ownership depends on a managed wrapper and release it when native use ends; avoid private cleaner APIs or hidden-API bypasses. A weak reference does not keep the buffer alive.

For repeated image/media work, verify ownership and release/reuse paths with the actual library. Do not manually recycle buffers still owned by another consumer.

## Completion evidence

Preserve the repeatable workload, build/device identity, memory profiles before and after cleanup, and the allocation or reference owner responsible. Re-run after the fix and separate a bounded cache plateau from unbounded retained growth. State profiling gaps, sampled coverage, and missing exit-time checks explicitly.
