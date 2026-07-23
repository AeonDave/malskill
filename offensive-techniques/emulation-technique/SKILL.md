---
name: emulation-technique
description: "Auth/lab: generic emulation methodology for binaries, firmware, kernels, and MCU/board targets; static-to-dynamic routing, tool choice, validation signals."
license: MIT
compatibility: "AgentSkills-compatible agents; local artifacts; authorized isolated labs; QEMU, Qiling, Unicorn, Renode, GDB, Frida, and firmware extraction tools optional."
metadata:
  version: "1.0"
  category: analysis
---

# Emulation Technique

Use emulation to answer a runtime question with the smallest faithful environment that can produce evidence.

## When this skill applies

- You have a binary, firmware image, rootfs, kernel, bootloader, shellcode, driver, MCU image, or unknown architecture artifact.
- Static analysis found architecture, format, APIs, strings, init scripts, vector tables, MMIO, network services, unpacking, decryption, or anti-analysis behavior, but runtime evidence is needed.
- You need to decide between native execution, user-mode emulation, OS-layer emulation, full-system emulation, board simulation, CPU-only emulation, or hardware.

## Safety and scope gates

- Treat every dynamic run as untrusted execution. Use an isolated VM/container, snapshots, no shared secrets, controlled networking, and localhost-only forwards unless scope explicitly permits more.
- Do not run unknown malware or firmware on the analyst host natively.
- Preserve the original artifact. Work from copies and record hashes of every input and modified output.
- Prefer read-only mounts and explicit scratch directories until the workflow requires mutation.
- Do not expose guest services broadly. Bind forwards to localhost and capture traffic/transcripts as evidence.

## Static-to-dynamic gate

Do not emulate blindly. Before the first run, record:

- Artifact type: ELF, PE, Mach-O, raw blob, shellcode, kernel, rootfs, disk image, bootloader, MCU firmware, UEFI, archive, filesystem.
- CPU and ABI: arch, bits, endian, ARM/Thumb mode, hard/soft float, libc, interpreter, OS ABI, privilege level.
- Loader facts: entry point, base/load address, program headers, imports, required libraries, rootfs or DLL/framework dependency set.
- Environment facts: config paths, expected devices, NVRAM, `/proc`, registry, network ports, UARTs, GPIO/JTAG/SWD, MMIO ranges, DTB/SVD clues.
- Runtime question: what output, branch, API call, packet, decrypted data, crash, console line, service response, or memory/register state will prove progress.

Escalate to dynamic analysis when static analysis cannot answer behavior, unpacking, anti-analysis, runtime config, syscall/API effects, service binding, interrupt/peripheral behavior, or kernel/driver reachability.

## Choose the lane

| Target need | First dynamic lane | Public tools |
|---|---|---|
| Isolated decode loop, shellcode, custom VM handler, no OS | CPU-only emulation | Unicorn, Ghidra emulator, radare2 ESIL |
| Linux/BSD user-mode executable with known sysroot | Process emulation | QEMU user-mode, `strace`, `ltrace`, GDB |
| PE/Mach-O/ELF with OS APIs to hook or fake | OS-layer emulation | Qiling, Frida, debugger API hooks |
| Router/camera/IoT Linux firmware services | Firmware rehosting | binwalk, unsquashfs, ubi_reader, QEMU user/system, FirmAE/Firmadyne |
| Kernel, initramfs, disk, driver, bootloader, UEFI | Full-system emulation | QEMU system, OVMF/SeaBIOS, GDB remote, `qemu-img` |
| MCU/RTOS/board firmware with MMIO, UART, GPIO, timers | Board simulation | Renode, QEMU system board models, OpenOCD/GDB, SVD-aware RE |
| Peripheral parity is missing but routine is clear | Partial model | Unicorn/Qiling hooks, Renode custom platform, MMIO stubs |
| Emulator cannot model the target and the objective requires hardware behavior | Physical lab | UART/JTAG/SWD/SPI tools, logic analyzer |

Pick the weakest lane that can answer the question. If a lane fails because it lacks OS, syscalls, files, devices, interrupts, or peripherals, move one level closer to the real environment.

## Core loop

1. **Triage**: identify format, arch, dependencies, and expected environment.
2. **Hypothesis**: state exactly what runtime behavior you expect and how you will observe it.
3. **Minimal run**: use the narrowest emulator setup with timeouts and bounded output.
4. **Instrument**: add tracing only where needed: syscalls, APIs, blocks, memory, UART, GDB, network, MMIO.
5. **Patch or stub**: fake missing environment only when the missing piece is not the behavior under study.
6. **Validate**: capture one replayable signal: console line, response, branch hit, memory dump, register state, trace, packet, crash, or file mutation.
7. **Escalate or stop**: if the signal answers the question, stop. If not, update the missing-environment model and rerun.

## Evidence standards

- "It started" is not enough. Record what executed, what was observed, and why it proves the claim.
- For services, prove a bound endpoint and one protocol-level interaction with external tooling.
- For firmware, preserve extraction logs, init path, architecture, chosen emulator command, and network/UART transcript.
- For MCU/board work, distinguish CPU instruction execution from board/peripheral parity.
- For kernel work, capture boot banner, panic/oops text, GDB stop, or driver interaction evidence.
- For hooks and patches, label every fake response and do not confuse it with native target behavior.

## Common failure pivots

- `exec format error` or illegal instruction: wrong arch, endian, ABI, CPU extension, ARM/Thumb mode, or loader.
- Missing interpreter/library: build or extract a sysroot; set `-L`, `QEMU_LD_PREFIX`, `LD_LIBRARY_PATH`, or Qiling rootfs.
- Missing syscall/API: hook or stub in Qiling/Frida, or switch to QEMU/full-system.
- Hangs in MMIO loop: identify address range; use Renode/custom peripheral model or stub reads/writes.
- No serial output: wrong console device, baud irrelevant in virtual UART, wrong DTB, wrong machine, guest waiting on storage or init.
- Service unreachable: wrong guest IP, daemon did not start, firewall/init script missing, port forward bound to wrong NIC, service needs NVRAM/config.
- Dynamic run changes behavior: anti-debug/anti-VM/time/network checks; patch or emulate the check explicitly and record it.

## Resources

- [references/static-to-dynamic-gates.md](references/static-to-dynamic-gates.md) — load before choosing dynamic execution when the target class is still uncertain.
- [references/userland-emulation.md](references/userland-emulation.md) — Linux/BSD user-mode, OS-layer emulation, sysroots, syscall/API tracing, and service processes.
- [references/firmware-rehosting.md](references/firmware-rehosting.md) — Linux firmware/rootfs extraction, init/service rehosting, NVRAM/config grafting, and network validation.
- [references/board-and-kernel-emulation.md](references/board-and-kernel-emulation.md) — MCU/RTOS, Renode/QEMU board choice, Linux kernel boot/debug, DTB/SVD/MMIO decisions.

