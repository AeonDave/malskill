---
name: unicorn
description: "Auth/lab ref: Unicorn Engine CPU-only emulation for shellcode, decryptors, custom VM handlers, instruction tracing, memory hooks, and register-level experiments."
license: MIT
compatibility: "Unicorn Engine bindings; no OS, loader, filesystem, syscall, or peripheral model."
metadata:
  version: "1.0"
  category: tool
---

# Unicorn

Unicorn is a CPU emulator. It is the right tool when you can define memory, registers, and stop conditions yourself.

## Use Unicorn when

- the target is shellcode, a decoder, checksum loop, custom VM handler, crypto primitive, or small boot stub
- OS behavior would be noise
- you know or can infer load address, entry address, mapped memory, stack, registers, and inputs
- memory/register hooks are the evidence you need

Do not use Unicorn as a shortcut for real userland execution. If the target needs syscalls, files, dynamic linking, registry, interrupts, or hardware peripherals, use Qiling, QEMU, or Renode instead.

## Setup checklist

- architecture, mode, endian, ARM/Thumb state
- code mapping address and permissions
- stack address and size
- input buffers and output buffers
- initial registers and calling convention
- imported function stubs or syscall stop points
- maximum instruction count or address stop

## Hook strategy

| Hook | Use |
|---|---|
| basic block | coverage, control-flow sketch, custom VM dispatch |
| instruction | exact trace, self-modifying code, privileged instruction stop |
| memory read/write | watchpoints, decrypted output, MMIO discovery |
| unmapped memory | identify missing mapping, import thunk, stack growth, bad pointer |
| interrupt/syscall | stop or fake external behavior |

Keep hooks narrow. Broad instruction hooks over large regions can make emulation painfully slow.

## Good targets

- XOR/RC4/AES wrapper that fills a plaintext buffer
- password checker inner loop
- architecture-specific shellcode decoder
- VM bytecode dispatcher over a byte array
- bare-metal reset stub before first peripheral wait
- opaque predicate or anti-debug gadget

## Bad targets

- dynamically linked application with many libc calls
- Windows or macOS binary that needs real APIs
- Linux service that opens files, forks, listens on sockets, or uses `/proc`
- MCU firmware stuck in timer/UART/GPIO MMIO loops unless those reads/writes are stubbed deliberately
- kernel boot, drivers, or interrupt-heavy RTOS behavior

## Evidence

- initial register/memory state
- hook outputs and stop reason
- memory dump of transformed buffers
- branch or address coverage proving the target path
- exact stubs used for external calls

State clearly that the proof is CPU-level unless OS or board behavior was validated elsewhere.

