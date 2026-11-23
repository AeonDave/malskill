# 16 KB Page Size Compliance

Load when building, testing, or triaging native code on a 16 KB device, including vendored libraries and fuzz targets. Runtime page size matters independently of the app's target SDK.

## What changed

- Android 15+ devices may boot with **16 KB kernel page size** (up from the historical 4 KB) for I/O and memory-allocation performance wins.
- `.so` files must have LOAD segments aligned to at least 16 KB for `arm64-v8a` and `x86_64` ABIs — 32-bit ABIs (`armeabi-v7a`, `x86`) stay 4 KB.
- Some 4 KB-aligned apps run through Android's 16 KB backcompat mode. Record that mode during testing; a successful launch under it is not proof of native 16 KB compatibility.

## Play Store deadline

- The current [Android compatibility guide](https://developer.android.com/guide/practices/page-sizes) requires support for apps targeting API 35+ on 64-bit devices and states that unsupported updates cannot be released from **February 1, 2027**. Recheck the current Play requirement when making a release decision; do not use a store deadline to decide whether a runtime defect matters.

## Verifying alignment

Per `.so`:

```bash
# NDK-provided readelf (llvm-readelf works too)
$NDK/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-readelf -lW libmylib.so | grep LOAD

# Expected output columns: Type Offset VirtAddr PhysAddr FileSize MemSize Flg Align
# LOAD  0x000000 0x0000000000000000 0x0000000000000000 0x004234 0x004234 R E 0x4000
#                                                                            ^^^^^^ 0x4000 = 16384 bytes = 16 KB ✓
```

Inspect every LOAD segment of each shipped 64-bit `.so`, not just the first or the app-owned library. An alignment below `0x4000` fails the ELF alignment check.

Also inspect `GNU_RELRO`: when writable data follows it in the same LOAD segment, its end address (`VirtAddr + MemSiz`) must be 16 KB aligned. Otherwise page protection can make neighboring writable data read-only and cause a runtime crash. Do not remove RELRO to make the check pass; fix the layout with a current toolchain or the documented linker flags.

## Automated verification

Use APK Analyzer or the checking script linked from the official compatibility guide. Inspect its accepted artifact format before use. For an AAB, verify generated installable APKs and their native libraries rather than treating the bundle itself as an APK.

Separately check ZIP entry alignment with `zipalign` (SDK Build-Tools 35.0.0+):

```bash
$ANDROID_HOME/build-tools/35.0.0/zipalign -v -c -P 16 4 app-release.apk
# Last line: "Verification successful" when every uncompressed .so is 16 KB-aligned.
```

Keep ABI and module directories when extracting libraries; flattening identically named files can silently discard evidence. `zipalign` checks APK layout, not ELF program headers or runtime page-size assumptions.

## AGP + NDK version matrix

| AGP | NDK | Behavior |
|-----|-----|----------|
| 8.5.1+ | r28+ | New builds default to 16 KB ELF alignment; AGP aligns uncompressed libraries in the APK. Check third-party prebuilts separately. |
| 8.5.1+ | r27 or lower | Configure ELF alignment explicitly. Packaging alignment cannot repair a misaligned ELF segment. |
| < 8.5.1 | any | Prefer upgrading AGP. For uncompressed libraries, do not infer bundle-generated APK alignment from a local APK. The documented compressed-library fallback changes packaging only. |

**Recommended baseline: AGP 8.5.1 + NDK r28** (matches the official Android guide).

## Manual linker flags (older toolchains)

### CMake

`CMakeLists.txt`:

```cmake
target_link_options(mylib PRIVATE
    "-Wl,-z,max-page-size=16384"
    "-Wl,-z,common-page-size=16384"
)
```

Or as a global setting in the module `build.gradle.kts`:

```kotlin
android {
    defaultConfig {
        externalNativeBuild {
            cmake {
                arguments += "-DCMAKE_SHARED_LINKER_FLAGS=-Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384"
            }
        }
    }
}
```

### ndk-build

`Android.mk`:

```make
LOCAL_LDFLAGS += -Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384
```

### Rust (cargo-ndk)

`.cargo/config.toml`:

```toml
[target.aarch64-linux-android]
rustflags = ["-Clink-arg=-Wl,-z,max-page-size=16384", "-Clink-arg=-Wl,-z,common-page-size=16384"]

[target.x86_64-linux-android]
rustflags = ["-Clink-arg=-Wl,-z,max-page-size=16384", "-Clink-arg=-Wl,-z,common-page-size=16384"]
```

## Third-party AARs and vendored `.so` files

Third-party dependencies may ship 4 KB-aligned `.so` files. Audit the merged output:

```bash
./gradlew :app:mergeReleaseNativeLibs
find app/build/intermediates/merged_native_libs/release/ -name '*.so' -exec \
    sh -c 'echo "=== $1 ==="; llvm-readelf -lW "$1" | grep LOAD' _ {} \;
```

If a dependency is non-compliant:

1. Upgrade to a newer version if available.
2. File an issue with the maintainer.
3. If you have the sources, rebuild with `-Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384`. `patchelf` alone cannot retro-align existing LOAD segments — relinking is required.
4. If nothing works and the dependency is non-critical, drop it or replace it.

## Runtime `PAGE_SIZE` assumptions

Code must not assume `PAGE_SIZE == 4096`. With flexible page sizes enabled on NDK r27+, `PAGE_SIZE` is undefined. Query the runtime rather than restoring a compile-time constant.

```c
long page_size = sysconf(_SC_PAGESIZE);   // returns 4096 or 16384
```

Common bugs:

- `mmap()` with `length = 4096` — wastes space on 16 KB, but usually still works (kernel rounds up).
- `mmap()` with `offset` not aligned to page size — `EINVAL` on 16 KB systems if hard-coded to 4 KB.
- Buffer allocators using compile-time `#define PAGE_SIZE 4096` — fragmented allocation, wasted memory.
- Fixed alignment passed to `posix_memalign` is a problem when the consumer requires page alignment; use the runtime page size for that requirement, not for every ordinary allocation.

## Testing on a 16 KB device

- **Cuttlefish**: use the documented 16 KB build/image configuration for the pinned AOSP branch.
- **Supported Pixel devices**: the developer option depends on the model and OS/QPR version. Check the device list in the official guide before changing the boot configuration; do not infer support from the model generation alone.
- **Android Studio emulator**: system images labeled "16 KB" available for API 35+.

Verify:

```bash
adb shell getconf PAGE_SIZE      # 16384 on a 16 KB device
```

For 4 KB physical devices, use the Android Studio 16 KB emulator image or a Pixel with the developer option enabled — there is no supported way to fake a 16 KB page size at runtime.

## Zipalign

`zipalign -P 16` aligns uncompressed native libraries within an APK so they can be mmap'd directly. Align before APK signing:

```bash
zipalign -P 16 -f -v 4 unsigned.apk aligned.apk
```

This is separate from ELF LOAD alignment — you need both:
1. ELF LOAD segments 16 KB aligned (linker flag) — the `.so` itself.
2. APK entries 16 KB aligned (`zipalign -P 16`) — the `.so` position inside the APK.

## CI gate

Gate the final installable artifacts, including feature modules and third-party libraries. Fail on missing expected artifacts, tool errors, unparseable headers, or failed ELF/ZIP/RELRO checks; an empty scan must not pass as native compatibility evidence. Keep a device/emulator runtime check for hard-coded page assumptions: a static alignment check alone cannot establish them.

## Anti-patterns

- Assuming AGP handles third-party AAR compliance automatically (it doesn't).
- Treating a check of one ABI or one app-owned library as verification of every delivered native dependency.
- Setting `APP_SUPPORT_FLEXIBLE_PAGE_SIZES=false` to make old code compile — masks the underlying bug and blocks future device compatibility.
- Using ZIP alignment to claim ELF alignment, or testing only with backcompat enabled.
- Skipping the runtime `sysconf(_SC_PAGESIZE)` audit — code that compiles clean can still crash on a 16 KB device.
