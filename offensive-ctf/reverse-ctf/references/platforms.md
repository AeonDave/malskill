# CTF Reverse - Platform and Architecture Reversing

Environment-specific reversing: Apple, firmware/embedded, kernel, mobile apps, game engines, and exotic architectures. For language-binary recognition see [languages.md](languages.md); for tools see [tools.md](tools.md).

## Table of Contents
- [Apple / Mach-O / iOS](#apple--mach-o--ios)
- [Firmware and Embedded](#firmware-and-embedded)
- [Kernel Drivers](#kernel-drivers)
- [Mobile Apps (Android)](#mobile-apps-android)
- [Desktop App Bundles](#desktop-app-bundles)
- [Game Engines](#game-engines)
- [Exotic Architectures](#exotic-architectures)

## Apple / Mach-O / iOS

```bash
otool -l binary                       # load commands; LC_MAIN=entry, LC_LOAD_DYLIB=deps
lipo binary -thin arm64 -output b64   # split fat binaries
codesign -d --entitlements - binary   # entitlements; -f -s - to re-sign a patched binary
class-dump binary > classes.h         # Objective-C headers (alt: dsdump, otool -oV)
swift demangle '<mangled>'
```

- ObjC dispatch: `objc_msgSend(receiver=RDI, selector=RSI, …)`.
- Swift: `__swift5_*` sections, witness tables, `swift_*` runtime helpers.
- iOS apps: `LC_ENCRYPTION_INFO` ⇒ FairPlay-encrypted; decrypt with `frida-ios-dump`, then `class-dump`. Bypass jailbreak detection by hooking `access`/`stat` for paths like `/Applications/Cydia.app`, `/bin/sh`.
- Patched Mach-O must be re-signed (`codesign -f -s -`) to run.

## Firmware and Embedded

```bash
binwalk -Me firmware.bin              # recursive extraction
unsquashfs / jefferson / ubireader_extract_files / cpio -idv   # by filesystem
dtc -I dtb -O dts device_tree.dtb     # device tree
```

- Magic sniff: `hsqs` (SquashFS), `UBI#` (UBI). Hardware dumps via UART (console/bootloader), JTAG (halt/flash), SPI/eMMC (direct flash).
- Emulate userland with QEMU: `qemu-arm -L /usr/arm-linux-gnueabihf ./bin` (add `-g 1234` for `gdb-multiarch` remote). Same for `qemu-mips`/`qemu-mipsel`.
- RTOS markers: FreeRTOS (`xTaskCreate`, `xQueueSend`), Zephyr (`k_thread_create`, `CONFIG_*`), bare metal (vector table + polling loop + MMIO map).

## Kernel Drivers

- **Linux `.ko`** — `modinfo`, `nm | grep -v ' U '`. Find the ioctl handler via `file_operations`; trace `copy_from_user`/`copy_to_user`. Debug with `qemu-system-x86_64 … -s -S` + `gdb vmlinux` (`target remote :1234`, `lx-symbols`).
- **eBPF** — `bpftool prog dump xlated/jited id <N>`; key calls `bpf_map_lookup_elem`, `bpf_probe_read`, `bpf_trace_printk`.
- **Windows `.sys`** — PE format; entry `DriverEntry(PDRIVER_OBJECT,…)`. Key patterns: `IoCreateDevice`, `IRP_MJ_DEVICE_CONTROL`, `MmMapIoSpace`, `Zw*File`.

## Mobile Apps (Android)

- **JNI RegisterNatives** — when native names don't map to `Java_pkg_Class_method`, trace `JNI_OnLoad → RegisterNatives → fnPtr` to find the real handler. Prefer the x86_64 `.so` for best Ghidra output.
- **DEX runtime patching** — a native `.so` may rewrite Dalvik bytecode in memory (`/proc/self/maps`+`mprotect`+XOR); reconstruct the patched DEX offline from the native XOR key/offsets/checksums.
- **`.so` loading bypass** — recreate only the package/class/native signature in a clean project and call the original native method directly.
- **Frida** — bypass TLS pinning or cloud-function validators by hooking post-auth and invoking the method/Cloud Function directly with a valid payload; call JNI-accessible secret methods straight from Frida.
- **Anti-debug / root** — model `TracerPid` → `su`/root-binary → system properties → emulator markers; derive the success path statically or patch the gate.
- **Other recovery paths** — mine `logcat` for crypto material; dump the post-deobfuscation key + redirect which parameter is signed; relocate `LocalBroadcastManager` receiver logic into an auto-running path and log it; toolchain `apktool d` / `jadx` / `unzip`.

## Desktop App Bundles

- **Electron** — unpack the ASAR archive, then find the real native binary and JS glue (argument shapes, file locations, crypto flow).
- **Node.js packages** — for heavy obfuscation, runtime reflection (`Object.getOwnPropertyNames`) beats static beautification.
- **Tauri** — Brotli-compressed frontend assets embedded in the exe; find `index.html` xrefs, dump blobs, Brotli-decompress.
- **Intel SGX** — enclave code is still x86-64; focus on ECALL tables, attestation flow, and deterministic key derivation.

## Game Engines

- **Unreal** — extract `.pak` (UnrealPak/FModel); Blueprints compile to Kismet bytecode in `.uasset` (look for `K2_SetTimer`, `Branch`, custom events).
- **Unity** — Mono: decompile `Assembly-CSharp.dll` (dnSpy/ILSpy), repackage via `apktool b` + re-sign. IL2CPP: `Il2CppDumper` on `libil2cpp.so` + `global-metadata.dat` (recovers strings/endpoints/types); if metadata is encrypted, reverse the loader first. Assets via AssetStudio/AssetRipper/UABE.
- **Lua** — `luadec`/`unluac` for bytecode; `luajit -bl` for LuaJIT.
- **Anti-cheat (EAC/BattlEye/VAC)** — identify the specific check first; don't assume you must defeat the whole stack.

## Exotic Architectures

- **ARM64/AArch64** — args `x0-x7`, link register `x30`, fixed 4-byte instructions, PC-relative `ADRP+ADD`; ROP leans on `LDP …; RET`. `qemu-aarch64-static -L /usr/aarch64-linux-gnu ./bin`.
- **RISC-V** — Capstone compressed mode + `qemu-riscv64 -L ./sysroot`; watch Bitmanip (`clz`,`cpop`,`clmul`) and crypto (`aes32*`,`sha256sig*`) extensions and CSRs (`mstatus`, `satp`). When a glibc symbol-version mismatch blocks execution, patch both the version string and its hash slot.
- **MIPS** — `qemu-mips`/`qemu-mipsel`; Cavium OCTEON exposes hardware AES/SHA via CP2 (`dmtc2`/`dmfc2`) — treat CP2 writes as crypto setup.
- **CAN bus / automotive** — `candump`/`cansend`/`canplayer`; patterns: ECU seed-key bypass, message replay, UDS/KWP2000 firmware extraction.
- **MBR / bootloader** — `qemu-system-x86_64 -fda disk.img -s -S` + `gdb -ex 'set architecture i8086' -ex 'target remote :1234'`.
- **Game Boy (Sharp SM83)** — debug in bgb; comparisons against `(hl)` leak the expected byte directly.
- **Microcontroller MMIO** — register-level crypto reconstruction (read key parts, rebuild the cipher) is usually easier than full-firmware emulation.
