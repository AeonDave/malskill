# NeuroMatrix Backend Routing

Use this reference when selecting an emulation lane or triaging a backend failure.

## Contents

- [First calls](#first-calls)
- [Unicorn](#unicorn)
- [Qiling](#qiling)
- [QEMU](#qemu)
- [Renode](#renode)
- [Common pivots](#common-pivots)

## First calls

```json
{"tool":"supported_architectures","arguments":{}}
{"tool":"list_catalog","arguments":{"category":"backend","backend":"qemu","include_schema":true}}
{"tool":"get_tool","arguments":{"name":"qemu_linux_start"}}
```

Create the session after the target facts are known enough:

```json
{"tool":"create_session","arguments":{"backend":"qemu","arch":"x64","os_name":"linux","session_id":"vm1"}}
```

## Unicorn

Use for CPU-level work with explicit memory and registers:

- raw bytes, shellcode, decryptors, custom VM handlers
- instruction tracing, memory hooks, breakpoints, watchpoints
- patching or stepping without OS behavior

Typical flow:

1. `create_session(backend="unicorn", arch=...)`
2. `load_binary(..., base_address=..., data/path=...)`
3. discover `disassemble`, `read_memory`, `write_memory`, `set_breakpoint`, `step`, `continue`, `run_until`, trace/coverage/patch tools through the catalog
4. capture register/memory/trace evidence

Escalate if the target needs syscalls, files, dynamic loaders, interrupts, or peripherals.

## Qiling

Use for OS-layer executable emulation:

- Linux/Windows/macOS/FreeBSD/QNX/DOS/UEFI style target binaries when rootfs/assets exist
- syscall/API hooks, filesystem mapping, registry/config fakes, hotpatching
- UEFI target/API lane: `.efi` application/driver behavior, not full firmware-platform boot
- long-running userland services that publish session-scoped endpoints

Typical flow:

1. `qiling_native_status` or `qiling_set_rootfs` when assets/rootfs matter
2. `create_session(backend="qiling", arch=..., os_name=..., rootfs=...)`
3. `get_tool("qiling_run_os_binary")`
4. `run_tool("qiling_run_os_binary", {...}, detach=true)` for non-trivial runs
5. add `qiling_hook_syscall`, `qiling_hook_api`, or scripted hooks only when needed and trusted

Escalate to QEMU/Renode if kernel, driver, interrupt, board, device, or full firmware behavior is the question.

## QEMU

Use for Linux user/system execution, full-system firmware, kernels, disks, QMP/GDB, and Hexagon DSP.

Main lanes:

- `qemu_start_process`: qemu-user process execution
- `qemu_system_start`: generic full-system VM
- `qemu_linux_start`: caller-supplied kernel/initrd/DTB/rootfs study
- `qemu_firmware_start`: OVMF/SeaBIOS/AAVMF firmware boot
- `qemu_drive_add`: attach artifact/workspace disks with explicit format/interface
- `qemu_serial_add`: UART-style channels
- `qemu_port_forward`: localhost-bound guest service exposure
- `qemu_gdbserver_start`, QMP tools, monitor tools

Kernel rule: NeuroMatrix does not bundle a default kernel. Upload the exact kernel/initrd/DTB/config/symbol/rootfs artifacts for the task and preserve their artifact IDs in the evidence.

Firmware rule: OVMF/SeaBIOS/AAVMF assets may be bundled, but boot payloads still come from the caller. Secure Boot/TPM/ESP support is evidence for those configured flows, not broad platform parity.

Hexagon rule: Hexagon is a QEMU/LLVM lane, not Qiling. Use caller-supplied Hexagon ELF/DSP artifacts and capture QEMU execution or LLVM disassembly evidence.

## Renode

Use for MCU/RTOS/SoC board behavior when peripheral modeling matters.

Main lanes:

- `renode_status`, `renode_list_profiles`, `renode_configure_profile`
- `renode_start` with discovered profile, `.repl`, `.resc`, or artifact-backed custom profile
- `renode_list_peripherals` before choosing endpoint/peripheral operations
- `renode_load_elf` for artifact-backed ELF loading
- `renode_uart_endpoint`, `renode_start_gdbserver`, `renode_peripheral_endpoint`
- `renode_read_memory`, `renode_write_memory`, `renode_read_registers`, `renode_step`, `renode_continue`

Profile discovery is only an inventory. Runtime proof requires firmware load/CPU step/UART/GDB/peripheral observation or a controlled expected failure.

For unsupported boards, an agent may create a minimal `.repl`/`.resc` in the workspace or upload one as an artifact. Label unmodeled peripherals and do not claim full board parity.

## Common pivots

| Failure | Likely pivot |
|---|---|
| Qiling missing syscall/API | hook if environmental, or switch to QEMU |
| QEMU user loader/libc mismatch | upload/import matching sysroot or use Qiling with rootfs |
| QEMU no serial output | check console, machine, DTB, drive root, pause/attach order |
| Generic Xtensa rejects ESP flash | use ESP8266-aware QEMU override or report unsupported |
| Renode stuck in fault/default handler | wrong load address/vector/Thumb/memory map or missing IRQ/peripheral |
| Renode UART absent | wrong UART object, no firmware, or profile lacks that peripheral |
| Windows/macOS Qiling asset missing | collect/import legitimate overlays outside the repo |
