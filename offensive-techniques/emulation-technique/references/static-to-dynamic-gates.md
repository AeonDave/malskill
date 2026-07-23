# Static-to-Dynamic Gates

Use this reference when the next step could be either more reversing or a dynamic run.

## First-pass artifact facts

Collect these with `file`, `strings`, `readelf`, `objdump`, `rabin2`, `radare2`, `lief`, `binwalk`, `hexdump`, `xxd`, `dtc`, `fdtdump`, `unsquashfs`, `ubi_reader`, `7z`, and `exiftool` as applicable.

| Fact | Why it matters |
|---|---|
| Format and container | Selects loader: ELF/PE/Mach-O/raw/kernel/rootfs/disk/MCU/UEFI. |
| Arch/bits/endian/mode | Selects emulator binary, disassembler mode, register model, and calling convention. |
| ABI and interpreter | User-mode emulation needs loader/libc/sysroot compatibility. |
| Entry point and base | Raw blobs and MCU firmware need explicit load address. |
| Imports/syscalls/APIs | Decides QEMU user vs Qiling/Frida/debugger hooks. |
| Filesystem/config/NVRAM | Firmware usually fails dynamically until config paths exist. |
| DTB/SVD/vector table | Board/kernel lane needs device tree, MMIO, IRQ, UART, and reset clues. |
| Strings and service hints | Ports, paths, UART prompts, URLs, creds, init commands become dynamic probes. |
| Entropy and packer hints | Dynamic may be needed to dump unpacked/decrypted payloads. |

## Dynamic is justified when

- The artifact decrypts, decompresses, or unpacks data only at runtime.
- A branch condition, comparison, syscall/API result, timer, randomness, or network response controls the answer.
- Static analysis found service binaries but not their runtime config or bind address.
- A kernel/driver/bootloader needs privilege-level behavior, interrupts, or device state.
- MCU firmware polls MMIO, uses timers/UART/GPIO, or depends on reset/vector behavior.
- You need a crash, console prompt, packet, memory dump, or trace to validate a hypothesis.

## Static should continue when

- The architecture, endian, loader, or base address is still unknown.
- Required libraries/rootfs/DLLs/frameworks are missing and no substitute is justified.
- The desired answer is a constant, config value, string, symbol, or simple transform visible statically.
- Emulation would require faking the exact behavior being studied.
- The target is unsafe to run and an isolated lab is not ready.

## Minimum run contract

Before launching, write down:

- command or emulator configuration
- input artifact hashes
- timeout and output limits
- expected success signal
- allowed network behavior
- environment fakes, hooks, stubs, and patches

After launching, record:

- whether code executed past entry/init
- stdout/stderr/UART/serial/network trace
- syscall/API/hook evidence
- crash/panic/exception if any
- files or memory ranges changed
- next missing dependency if it failed

