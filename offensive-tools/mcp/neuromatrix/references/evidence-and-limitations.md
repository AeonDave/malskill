# NeuroMatrix Evidence and Limitations

Use this reference before reporting what NeuroMatrix can or cannot do for a target.

## Evidence ladder

| Claim | Minimum evidence |
|---|---|
| Artifact was accepted | `request_upload` hash/size match or `analyze_artifact` metadata |
| Static classification | `analyze_artifact` / `inspect_binary` facts with format, arch, loader, signatures |
| Raw CPU execution | register/PC change, breakpoint hit, trace, memory mutation |
| Userland execution | exit code, syscall/API trace, stdout/stderr, hook event, filesystem effect |
| Full-system boot | QMP running plus serial console, boot banner, panic/oops, or expected halt |
| Linux kernel boot | `Linux version ...`, init marker, structured panic/failure facts, GDB symbol evidence, or service endpoint |
| Firmware boot | firmware banner, NVRAM persistence, ESP boot marker, Secure Boot A/B result, TPM/QMP evidence |
| MCU board execution | firmware loaded, CPU step, reset handler reached, UART/GDB/peripheral evidence |
| Board/peripheral parity | target-relevant UART/GPIO/timer/storage/network/MMIO behavior observed |
| Service rehosting | session-scoped endpoint plus external protocol interaction |

Say which level was proven. Do not compress "profile exists", "process started", and "target behavior worked" into one claim.

## Caller-supplied inputs

NeuroMatrix is intentionally input-driven. The agent or user supplies the exact:

- binaries, firmware, kernels, initrds, rootfs/disk images, DTBs
- symbols such as `System.map` or `vmlinux`
- kernel configs and modules
- bootloaders, ESP contents, NVRAM stores
- Windows DLLs/registry hives and macOS dyld/dylibs when legally available
- custom QEMU/Renode/ESP runtimes when the bundled runtime lacks the needed board

Do not claim broad support based on packaged smoke fixtures alone.

## Known limitation patterns

- **Windows/macOS Qiling**: readiness depends on legitimate proprietary rootfs overlays. Missing assets are expected on fresh installs.
- **macOS arm64/arm64e**: asset presence does not automatically prove dynamic Mach-O parity; record the actual runtime outcome.
- **Qiling EVM**: not a CPU/firmware lane in current Qiling installs; use an EVM-specific interpreter if the task is smart-contract execution.
- **ESP8266/Xtensa**: generic `qemu-system-xtensa` is not ESP8266 parity. Use `esp8266_runtime_status`, `build_esp_flash_artifact`, and a real ESP8266-aware runtime override when available.
- **Vendor MCU boards**: generic Cortex-M instruction stepping is not MAX78000/TM4C/vendor-board support. Use Renode/custom profiles or label the result as instruction-level only.
- **Renode profile count**: hundreds of `.repl`/`.resc` files are inventory, not all validated firmware runs.
- **OVMF/SeaBIOS/Secure Boot/TPM**: strong firmware-lane evidence is possible, but it is not a blanket claim of SMM/SMRAM/Ring -2 platform parity.
- **Linux kernel profiles**: profiles are QEMU launch presets. They do not bundle kernels and do not prove every kernel version/arch until caller artifacts boot.
- **Firmware rehosting**: extraction and userland execution do not prove full device parity; watchdogs, NVRAM, storage, DTB, NIC, and peripheral behavior may still be missing.

## Reporting template

When finishing a NeuroMatrix run, report:

- session id, backend, arch, OS/profile
- input artifact IDs and filenames
- catalog tools used
- job IDs and final status for detached work
- endpoints created and how they were touched
- evidence level reached
- hooks/stubs/patches/fakes used
- limitations and next pivot
- cleanup performed or intentionally left running

