---
name: qiling
description: "Auth/lab ref: Qiling OS-layer binary emulation for PE/ELF/Mach-O/UEFI/shellcode with rootfs, syscall/API hooks, filesystem mapping, and runtime patching."
license: MIT
compatibility: "Python Qiling framework; targets require matching rootfs/assets supplied by the task or Qiling examples."
metadata:
  version: "1.0"
  category: tool
---

# Qiling

Qiling sits between CPU-only emulation and full-system emulation: it loads executable formats, models OS APIs/syscalls, maps files, and lets the analyst hook behavior.

## Use Qiling when

- the target is PE, ELF, Mach-O, UEFI, DOS, shellcode, or a supported MCU-style sample
- you need to fake files, registry keys, environment, argv, syscalls, or APIs
- dynamic unpacking/decryption needs OS calls but not real hardware
- anti-debug checks should be bypassed without a real debugger
- you want instruction/basic-block/memory/API/syscall hooks

Prefer QEMU user-mode when you only need faithful Linux syscall forwarding. Prefer full-system or board emulation when kernel, drivers, interrupts, or peripherals are central.

## Quick checks

```bash
qltool run -f ./rootfs/bin/target --rootfs ./rootfs
qltool run -f ./sample.exe --rootfs ./rootfs/x8664_windows --json
qltool code --os linux --arch arm --format hex -f shellcode.hex
```

Rootfs matters. Missing DLLs, dylibs, registry hives, interpreters, or Linux userspace files are environment gaps, not necessarily target bugs.

## Task-local harness pattern

When `qltool` is too small, create a temporary harness in the analysis workspace. Keep it minimal:

- set `argv`, `rootfs`, `env`, `archtype`, `ostype`, endian, and Thumb mode explicitly
- map only required host files into the guest namespace
- hook one syscall/API/address at a time
- log arguments and return values before patching them
- stop at a clear success signal or timeout

Do not build a large reusable framework before one dynamic question is proven.

## Hooking decisions

| Missing behavior | Good Qiling response |
|---|---|
| file path missing | map or create the exact path observed in logs |
| registry/config missing | provide minimal key/value expected by the target |
| unsupported API/syscall | hook only if it is environmental, not the behavior under study |
| decryption routine | hook output buffer or stop after the routine |
| anti-debug/time/randomness | patch return value and label it as an analysis fake |
| network API | log parameters first; emulate response only when protocol content is not the question |

## Evidence

- command or harness options
- rootfs/source of OS assets
- list of hooks and fake return values
- stdout/stderr/log output
- dumped memory/config after runtime transformation
- reason Qiling is sufficient or why escalation is needed

## Common boundaries

- Qiling is not a complete OS or hardware simulator.
- Some syscalls/APIs are unimplemented; that is a normal pivot point.
- Windows and macOS targets often need legally obtained runtime assets from matching systems.
- CPU-level success under Qiling does not prove kernel, driver, or peripheral behavior.

