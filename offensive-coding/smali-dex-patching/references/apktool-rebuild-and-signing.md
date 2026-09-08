# Apktool Rebuild and APK Signing

Load when the rebuild/sign step fails, when handling split APKs, or when choosing between v1/v2/v3/v4 signing schemes.

## Apktool workflow

```bash
# Decompile — separates resources, extracts smali per DEX
apktool d target.apk -o unpacked/
apktool d target.apk -o unpacked/ -r          # skip resources (if arsc decode fails)
apktool d target.apk -o unpacked/ -s          # skip smali (resources only)

# Rebuild
apktool b unpacked/ -o patched-unsigned.apk
apktool b unpacked/ -o patched-unsigned.apk --use-aapt2   # AAPT2 (default on modern apktool)
apktool b unpacked/ --no-crunch                # skip 9-patch/PNG optimization
```

Output goes to `dist/<name>.apk` unless `-o` overrides. Not signed, not aligned.

## `apktool.yml` — the bookkeeping file

Created during decompile at `unpacked/apktool.yml`. Contains:

```yaml
apkFileName: target.apk
compressionType: false
doNotCompress:
- resources.arsc
- assets/prof.data
- lib/arm64-v8a/libnative.so
isFrameworkApk: false
packageInfo:
  forcedPackageId: '127'
  renameManifestPackage: null
sdkInfo:
  minSdkVersion: '26'
  targetSdkVersion: '34'
sharedLibrary: false
sparseResources: false
unknownFiles: {}
usesFramework:
  ids:
  - 1
  tag: null
version: 2.11.0
versionInfo:
  versionCode: '42'
  versionName: 1.2.3
```

Key fields:

- `doNotCompress` — files kept uncompressed. `.so` files here are directly `mmap`-able (faster load, required for 16 KB page alignment).
- `minSdkVersion` — passed to apksigner via `--min-sdk-version`.
- `packageInfo.forcedPackageId` — if not `127` (0x7f, standard), you're editing a shared-library APK; do not merge resources across.

## AAPT vs AAPT2

- AAPT (v1) — deprecated; only for very old APKs that use compact resource formats AAPT2 can't parse.
- AAPT2 — default since apktool 2.8+; supports Android 12+ resource formats.
- Force with `--use-aapt2` (usually redundant on modern apktool).

## Common rebuild failures

| Error | Cause | Fix |
|-------|-------|-----|
| `Error: could not decode arsc file` | Original APK uses unsupported resource format | Retry with `apktool d -s` (skip resources); patch only smali |
| `resource id 0x7f0x0000 already used` | Two `public.xml` entries for the same ID | Deduplicate; usually from combining two split APKs |
| `Method too large` | Smali method has too many instructions after edit | Refactor edit into a helper method; use `.method static synthetic` |
| `Invalid resource directory name: res/font-v26` | Non-standard folder | Add to `doNotCompress` in `apktool.yml`, or accept the warning |
| `unknown file .../BootReceiver.class` | Leftover Java `.class` from a partial edit | Remove; apktool only wants `.smali` |
| `no framework file: 1` | Missing SDK framework | `apktool if <path>/android.jar` to install |
| `unresolved reference to Lcom/foo;` | Class referenced in smali doesn't exist | Fix typo, or copy the class from source APK |

## zipalign

**Required** before v2+ signing; must run on unsigned APK, then sign.

```bash
zipalign -p -f 4 unsigned.apk aligned.apk        # legacy 4-byte alignment
zipalign -P 16 -f -v 4 unsigned.apk aligned.apk  # 16 KB page alignment for uncompressed .so files
zipalign -c -v 4 aligned.apk                     # verify only
```

Options:

- `-f` — overwrite if exists.
- `-v` — verbose.
- `-p` — page-align uncompressed `.so` files (4 KB).
- `-P 16` — page-align to 16 KB (**required** for APKs targeting Android 15+ with native code from Nov 2025).
- `4` — the trailing "4" is the byte alignment for other entries; standard.

**Signing before aligning breaks the v2 signature.** Always align first.

## apksigner (canonical signer)

Distributed with Android build-tools. Handles v1, v2, v3, v3.1, v4.

```bash
apksigner sign \
    --ks debug.keystore \
    --ks-pass pass:android \
    --key-pass pass:android \
    --ks-key-alias androiddebugkey \
    --v1-signing-enabled true \
    --v2-signing-enabled true \
    --v3-signing-enabled true \
    --v4-signing-enabled false \
    --min-sdk-version 26 \
    --out patched-signed.apk aligned.apk
```

Verify:

```bash
apksigner verify --verbose --print-certs patched-signed.apk
```

Expected output:

```
Verifies
Verified using v1 scheme (JAR signing): true
Verified using v2 scheme (APK Signature Scheme v2): true
Verified using v3 scheme (APK Signature Scheme v3): true
Verified using v4 scheme (APK Signature Scheme v4): false
Number of signers: 1
Signer #1 certificate DN: CN=Android Debug, O=Android, C=US
Signer #1 certificate SHA-256 digest: <hash>
```

## v1, v2, v3, v4 — pick the right combo

| Target SDK | Minimum |
|------------|---------|
| < 24 (Android 6-) | v1 (JAR) alone; v2 supported but unnecessary |
| 24–27 | v1 + v2 |
| 28+ | v2 + v3 minimum; v1 optional |
| 30+ (streaming, fs-verity) | v4 optional (produces `.idsig` sidecar) |

Modern APKs sign with all four schemes when possible. Missing v2 or v3 means:

- Play Store rejects the upload.
- Play Integrity produces `MEETS_BASIC_INTEGRITY` at best (no `MEETS_STRONG_INTEGRITY`).
- Some devices refuse update from a v1-only APK when a v2-signed version was previously installed.

## Debug keystore

One-time creation (or reuse Android Studio's `~/.android/debug.keystore`):

```bash
keytool -genkey -v -keystore debug.keystore \
    -storepass android -keypass android \
    -alias androiddebugkey \
    -keyalg RSA -keysize 2048 -validity 10000 \
    -dname "CN=Android Debug, O=Android, C=US"
```

Password `android` is a convention; some tools (uber-apk-signer) auto-detect this and prompt if different.

## uber-apk-signer (wrapper)

github.com/patrickfav/uber-apk-signer — bundled apksigner + zipalign + embedded debug keystore.

```bash
# Sign with embedded debug keystore
java -jar uber-apk-signer.jar -a unsigned.apk

# Batch a directory
java -jar uber-apk-signer.jar -a /path/to/apks/

# With custom keystore
java -jar uber-apk-signer.jar -a unsigned.apk --ks release.keystore --ksAlias mykey

# With v3 rotation (lineage file)
java -jar uber-apk-signer.jar -a unsigned.apk --lineage sig.lineage \
    --ks old.keystore --ks new.keystore
```

Auto-verifies with `apksigner verify` and reports.

## Signature lineage (v3 key rotation)

Only relevant if you have the ORIGINAL app's signing keys and want to migrate to a new key while keeping install/update compatibility. Not for patching-third-party-apps workflows.

Create a lineage:

```bash
apksigner rotate \
    --out sig.lineage \
    --old-signer --ks old.keystore --ks-key-alias old \
    --new-signer --ks new.keystore --ks-key-alias new
```

Sign with the lineage:

```bash
apksigner sign \
    --ks new.keystore --ks-key-alias new \
    --lineage sig.lineage \
    --out signed.apk aligned.apk
```

## Split APKs (App Bundles)

Modern apps distribute as `.aab` → Play generates per-device APK splits:

- `base.apk` — code + core resources
- `split_config.<density>.apk` — density-specific resources
- `split_config.<language>.apk` — language resources
- `split_config.<abi>.apk` — architecture-specific `.so`

### Extracting installed splits

```bash
adb shell pm path com.target.app
# → package:/data/app/~~xxx/com.target.app-yyy/base.apk
# → package:/data/app/~~xxx/com.target.app-yyy/split_config.arm64_v8a.apk
# → package:/data/app/~~xxx/com.target.app-yyy/split_config.xxhdpi.apk

# Pull each
adb pull /data/app/~~xxx/com.target.app-yyy/base.apk
adb pull /data/app/~~xxx/com.target.app-yyy/split_config.arm64_v8a.apk
# ...
```

### Patching a split-APK app

**Option 1: patch only base.apk**

1. Extract, patch, rebuild, sign only `base.apk`.
2. Install with `adb install-multiple base.apk split_*.apk`.

Fails if splits are v3-signed with the original certificate and your patched base uses a different certificate — installs demand consistent signing key across all splits.

**Option 2: combine splits into one APK** (recommended)

Use **`apk.sh`** (github.com/ax/apk.sh):

```bash
apk.sh pull com.target.app                        # pulls splits from device
apk.sh patch com.target.app.apk                   # decompiles, prompts for edits
apk.sh build com.target.app.apk                   # rebuilds, signs with debug key
adb install com.target.app-patched.apk
```

`apk.sh` fixes resource ID conflicts between splits automatically.

**Option 3: manual combine**

1. `unzip` each split to a single directory.
2. Merge `resources.arsc` — non-trivial; usually easier to use `apk.sh` or `APKEditor` (github.com/REAndroid/APKEditor).
3. Rebuild as single APK.

## Install failures

| Error | Meaning | Fix |
|-------|---------|-----|
| `INSTALL_FAILED_UPDATE_INCOMPATIBLE` | Signing key differs from installed version | `adb uninstall com.target.app` first |
| `INSTALL_PARSE_FAILED_NO_CERTIFICATES` | Sign step failed silently | Re-run `apksigner sign`; verify with `apksigner verify` |
| `INSTALL_PARSE_FAILED_INCONSISTENT_CERTIFICATES` | Multi-APK install with mismatched signers | Sign every split with the same key |
| `INSTALL_FAILED_INVALID_APK` | zipalign missing or corrupted | Re-align with `zipalign -P 16 -f -v 4` |
| `INSTALL_FAILED_INSUFFICIENT_STORAGE` | Device out of space | Uninstall test apps; `adb shell pm trim-caches 999G` |
| `INSTALL_FAILED_VERSION_DOWNGRADE` | Target versionCode < installed | Increment `versionCode` in manifest, or uninstall first |

## Quick verification checklist

```bash
# 1. Signed correctly
apksigner verify --verbose --print-certs patched.apk

# 2. Aligned correctly
zipalign -c -v 4 patched.apk

# 3. Manifest sane
aapt2 dump badging patched.apk | head -20

# 4. .so files 16 KB aligned (for API 35+ targets)
unzip -j patched.apk 'lib/arm64-v8a/*.so' -d /tmp/native/
find /tmp/native/ -name '*.so' -exec sh -c '
    align=$(llvm-readelf -lW "$1" | awk "/LOAD/ { print \$NF; exit }")
    echo "$1 align=$align"
' _ {} \;

# 5. DEX class count sane
find unpacked/ -name '*.smali' | wc -l    # rough baseline

# 6. Install
adb install patched.apk
```

## Anti-patterns

- Signing before zipalign → v2 signature invalid.
- Using outdated apktool (< 2.9) on modern APKs → resource decode fails.
- Signing with jarsigner (Java's built-in) → v1 only; modern APKs need v2+.
- Missing `--min-sdk-version` on apksigner → uses default (usually 24); signature scheme may not match manifest declaration.
- Editing `META-INF/*.SF` or `.RSA` files manually → signature invalidated; ignored by apksigner rebuild.
- Rebuilding without deleting old `dist/` → apktool may cache stale state; `rm -rf dist/` before rebuild.
