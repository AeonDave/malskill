# 16 KB Page Size Compliance

Load when the app has any native code (own `.so` or vendored dependency) and targets Android 15+ (API 35+). Mandatory for Play submissions from **November 1, 2025**.

## What changed

- Android 15+ devices may boot with **16 KB kernel page size** (up from the historical 4 KB) for I/O and memory-allocation performance wins.
- `.so` files must have LOAD segments aligned to at least 16 KB for `arm64-v8a` and `x86_64` ABIs — 32-bit ABIs (`armeabi-v7a`, `x86`) stay 4 KB.
- Apps that ship 4 KB-aligned `.so` files **cannot run** on 16 KB-page-size devices.

## Play Store deadline

- **New apps + updates** targeting API 35+: must be 16 KB-compliant from **November 1, 2025** (Play submission gate).
- **All app updates** targeting API 35+: hard block from **February 1, 2027** — Play refuses updates that ship 4 KB-aligned `.so` files. Confirmed on the official [Support 16 KB page sizes](https://developer.android.com/guide/practices/page-sizes) page.

## Verifying alignment

Per `.so`:

```bash
# NDK-provided readelf (llvm-readelf works too)
$NDK/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-readelf -lW libmylib.so | grep LOAD

# Expected output columns: Type Offset VirtAddr PhysAddr FileSize MemSize Flg Align
# LOAD  0x000000 0x0000000000000000 0x0000000000000000 0x004234 0x004234 R E 0x4000
#                                                                            ^^^^^^ 0x4000 = 16384 bytes = 16 KB ✓
```

Any LOAD segment with `Align < 0x4000` = non-compliant.

## Automated verification

Google ships the reference script in AOSP: [`check_elf_alignment.sh`](https://cs.android.com/android/platform/superproject/main/+/main:system/extras/tools/check_elf_alignment.sh). It walks every `.so` in an APK/AAB and prints `ALIGNED` / `UNALIGNED` per library.

```bash
curl -o check_elf_alignment.sh https://cs.android.com/android/platform/superproject/main/+/main:system/extras/tools/check_elf_alignment.sh?format=TEXT | base64 -d > check_elf_alignment.sh
chmod +x check_elf_alignment.sh
./check_elf_alignment.sh app-release.apk
```

Per-`.so` cross-check with `zipalign` (needs Android SDK build-tools 35.0.0+ for `-P 16`):

```bash
$ANDROID_HOME/build-tools/35.0.0/zipalign -v -c -P 16 4 app-release.apk
# Last line: "Verification successful" when every uncompressed .so is 16 KB-aligned.
```

Manual sweep when neither tool is available:

```bash
unzip -j app.aab 'base/lib/*.so' -d libs/
find libs/ -name '*.so' | while read f; do
    align=$(llvm-readelf -lW "$f" | awk '/LOAD/ { print $NF; exit }')
    echo "$f align=$align"
done
```

## AGP + NDK version matrix

| AGP | NDK | Behavior |
|-----|-----|----------|
| 8.5.1+ | r28+ | 16 KB compilation + zip alignment fully automatic; recommended baseline. |
| 8.5.1+ | r27 | 16 KB compilation on by default; may need manual flags for prebuilts and `libc++_shared.so`. |
| 8.3–8.5 | r26–r27 | Compiles 16 KB-aligned `.so`, but `bundletool` does **not** zipalign APKs from bundles by default — apps may run locally yet fail install from Play. Upgrade AGP. |
| < 8.3 | r26 or older | Manual linker flags (below) required; `libc++_shared.so` may be misaligned until you upgrade NDK. |

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
                arguments += "-DCMAKE_SHARED_LINKER_FLAGS=-Wl,-z,max-page-size=16384"
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
rustflags = ["-Clink-arg=-Wl,-z,max-page-size=16384"]

[target.x86_64-linux-android]
rustflags = ["-Clink-arg=-Wl,-z,max-page-size=16384"]
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

Code must not assume `PAGE_SIZE == 4096`. On NDK r27+, `PAGE_SIZE` is **not defined** by default for `arm64-v8a` / `x86_64`. Restore it (not recommended) with:

```
# ndk-build:
APP_SUPPORT_FLEXIBLE_PAGE_SIZES := false

# CMake:
-DANDROID_SUPPORT_FLEXIBLE_PAGE_SIZES=false
```

Better: query at runtime.

```c
long page_size = sysconf(_SC_PAGESIZE);   // returns 4096 or 16384
```

Common bugs:

- `mmap()` with `length = 4096` — wastes space on 16 KB, but usually still works (kernel rounds up).
- `mmap()` with `offset` not aligned to page size — `EINVAL` on 16 KB systems if hard-coded to 4 KB.
- Buffer allocators using compile-time `#define PAGE_SIZE 4096` — fragmented allocation, wasted memory.
- `posix_memalign(&ptr, 4096, size)` — should be `posix_memalign(&ptr, page_size, size)` where `page_size` is dynamic.

## Testing on a 16 KB device

- **Cuttlefish** (AOSP virtual device): boots with 16 KB pages when compiled with `PRODUCT_16K_DEVELOPER_OPTION=true`. Best for CI.
- **Pixel Tablet + Pixel 8+** on Android 15: developer option "Boot with 16 KB pages" (Settings → System → Developer options → 16 KB page size). Requires factory reset when toggled.
- **Android Studio emulator**: system images labeled "16 KB" available for API 35+.

Verify:

```bash
adb shell getconf PAGE_SIZE      # 16384 on a 16 KB device
```

For 4 KB physical devices, use the Android Studio 16 KB emulator image or a Pixel with the developer option enabled — there is no supported way to fake a 16 KB page size at runtime.

## Zipalign

`zipalign -P 16` (page-alignment specifier introduced with the 16 KB migration) — aligns uncompressed native libraries to 16 KB within the APK/AAB so they can be mmap'd directly:

```bash
zipalign -P 16 -f -v 4 unsigned.apk aligned.apk
```

This is separate from ELF LOAD alignment — you need both:
1. ELF LOAD segments 16 KB aligned (linker flag) — the `.so` itself.
2. APK entries 16 KB aligned (`zipalign -P 16`) — the `.so` position inside the APK.

## CI gate

Add a Gradle task to fail the build on non-compliant `.so`:

```kotlin
tasks.register("verify16KBAlignment") {
    dependsOn("mergeReleaseNativeLibs")
    doLast {
        val nativeDir = layout.buildDirectory.dir("intermediates/merged_native_libs/release").get().asFile
        val abis = listOf("arm64-v8a", "x86_64")
        val bad = mutableListOf<String>()
        abis.forEach { abi ->
            file(nativeDir.resolve("out/lib/$abi")).walk()
                .filter { it.extension == "so" }
                .forEach { so ->
                    val out = ProcessBuilder("llvm-readelf", "-lW", so.absolutePath)
                        .redirectErrorStream(true).start().inputStream.bufferedReader().readText()
                    val bad16k = out.lines().filter { "LOAD" in it }.any { line ->
                        val align = line.trim().split(Regex("\\s+")).last()
                        val alignInt = if (align.startsWith("0x")) align.substring(2).toLong(16) else align.toLong()
                        alignInt < 16384
                    }
                    if (bad16k) bad += "${so.name} ($abi)"
                }
        }
        if (bad.isNotEmpty()) error("Non-16KB-aligned .so files: $bad")
    }
}
tasks.named("assembleRelease") { finalizedBy("verify16KBAlignment") }
```

## Anti-patterns

- Assuming AGP handles third-party AAR compliance automatically (it doesn't).
- Ignoring `armeabi-v7a` — stays 4 KB. Do not add 16 KB flags for 32-bit ABIs; can break loading.
- Setting `APP_SUPPORT_FLEXIBLE_PAGE_SIZES=false` to make old code compile — masks the underlying bug and blocks future device compatibility.
- Zipalign `-P 4` — legacy alignment; explicitly need `-P 16` for compressed `.so` scenarios.
- Skipping the runtime `sysconf(_SC_PAGESIZE)` audit — code that compiles clean can still crash on a 16 KB device.
