# Android fuzzing boundaries and replay

Load when designing a lab campaign for an Android native library, JNI interface, managed parser, or Binder service. Use [harness-writing.md](harness-writing.md) for generic determinism and [crash-triage-and-reproducibility.md](crash-triage-and-reproducibility.md) for bucketing and minimization.

## Choose the boundary before the engine

| Target | Initial harness | What the result does not establish |
|---|---|---|
| Portable native parser with source | Narrow host libFuzzer/AFL++ target with sanitizers | Android allocator, bionic, ABI, loader, or production ingress behavior |
| Native code requiring Android dependencies | Device-side NDK target, or AOSP `cc_fuzz` for platform code | Reachability from another app or remote input |
| JNI conversion or lifetime handling | Real JNI entry with valid objects, class loader, and attached threads | A direct native helper call does not exercise the bridge |
| Pure Java/Kotlin parser | Host JVM target, such as Jazzer, when dependencies permit | ART behavior, Android permissions, framework services, or JNI equivalence |
| AIDL/Binder service implementation | Service instance plus the applicable AOSP Binder fuzz driver | A local service harness does not prove kernel-driver coverage or cross-process authorization |
| Binder kernel driver | Separate kernel/VM campaign with kernel coverage and recovery | Userspace service coverage is not kernel coverage |

[Jazzer's supported platforms](https://github.com/CodeIntelligenceTesting/jazzer) are host JVM platforms; do not assume its host runner executes an APK on ART. [AOSP libFuzzer](https://source.android.com/docs/security/test/libfuzzer) supports host execution only when the target library is host-supported. For [AIDL fuzzing](https://source.android.com/docs/core/architecture/aidl/aidl-fuzzing), inspect the pinned backend and build rules: do not infer Java/Rust/backend support from a C++ example or transfer a platform `cc_fuzz` recipe directly into an app's Gradle build.

## Preserve the Android contract

- Record the APK/split set or source revision, native build IDs, device build fingerprint and security patch level, ABI, relevant CPU features, OS API level, `minSdk`, `targetSdk`, NDK, instrumentation, and page size. OS version and target SDK are separate inputs; include only matrix cells relevant to the suspected behavior.
- Trace the production entry to the harness boundary. Record the actual caller identity, permissions, URI grants, input transformations, and reachable state. An `adb shell` caller is not an ordinary third-party app. A hook-injected value or direct helper invocation proves only that selected path until replay through the supported ingress confirms it.
- Keep JNI arrays, strings, direct-buffer capacities, pending exceptions, and references valid unless the target itself creates the invalid condition. Use the existing [JNI lifetime rules](../../../coding/android-jni-ndk/references/jni-refs-and-exceptions.md); a fake `JNIEnv` or host stub is not ART coverage.
- For Binder, preserve transaction order, parcel/object relationships, file-descriptor ownership, callbacks, and dependency services. Distinguish denied access from successful handler execution; do not remove identity checks and then claim unauthorized reachability.
- Reset files, preferences, database rows, permissions/grants, native globals, threads, and asynchronous callbacks that the scenario changes. Recreate the service/process when isolation cannot be proved; retain the required prefix sequence when minimizing stateful failures.

## Verify signal before scaling

1. Confirm valid seeds reach the intended parser/handler using target coverage or an explicit checkpoint. Count target blocks/states, not only harness branches or request volume.
2. Exercise the selected detector with a test-only known fault separately from the target corpus. Use [Android sanitizer conditions](../../../coding/android-jni-ndk/references/native-crashes-and-debugging.md#sanitizers); host ASan settings are not an Android app deployment recipe.
3. Separate expected parse rejection, permission denial, JNI contract errors, loader failure, sanitizer findings, ANRs, and resource kills. Missing logs or a monitor failure is inconclusive.
4. Check [16 KB packaging and runtime behavior](../../../coding/android-jni-ndk/references/16kb-page-size.md) when native code is involved. Record backcompat mode; successful launch under that mode does not establish native 16 KB support.

## Reproduction package

Keep the minimized input **and** setup sequence, exact build/symbol identity, instrumentation and reset configuration, execution trace, relevant logcat/tombstone, and expected failure. Symbolicate with matching native build IDs. Replay on the relevant Android environment and through the production entry where feasible; report host-only findings and changed harness preconditions explicitly. Confirm that written/imported data is actually consumed rather than overridden by a higher-priority source.

After a fix, replay the regression artifact and a valid neighboring case. Distinguish a confirmed target defect from a harness defect and a demonstrated security impact from an unexplained crash.
