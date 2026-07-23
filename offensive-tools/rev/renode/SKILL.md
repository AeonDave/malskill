---
name: renode
description: "Auth/lab ref: Renode board and SoC simulation for MCU/RTOS firmware, UART/GPIO/peripheral modeling, GDB remote debugging, REPL platforms, and RESC scripts."
license: MIT
compatibility: "Renode on Linux/macOS/Windows; target support depends on available platform descriptions and modeled peripherals."
metadata:
  version: "1.0"
  category: tool
---

# Renode

Renode is the first public tool to try when firmware behavior depends on a modeled MCU board, RTOS peripherals, UART, GPIO, timers, storage, or multi-core SoC state.

## Use Renode when

- the artifact is MCU/RTOS firmware and a board or close SoC model exists
- UART/GPIO/timer/storage/network peripheral behavior matters
- QEMU lacks the exact board, or CPU-only emulation hangs on MMIO
- you need deterministic virtual time and GDB remote debugging
- you can write or adapt a `.repl` platform description for the minimum needed peripherals

Do not treat CPU stepping as board parity. Prove the peripheral behavior relevant to the objective.

## Core objects

- `.repl`: platform description; CPUs, memory maps, buses, UARTs, GPIOs, timers, and peripherals.
- `.resc`: Renode monitor script; creates machines, loads platforms, loads binaries, configures analyzers, starts emulation.
- Monitor: interactive command surface for machines, sysbus, peripherals, memory, UART analyzers, and GDB server.
- Robot Framework: useful for validation harnesses that assert UART/peripheral output; keep it as test infrastructure, not the only evidence.

## Minimal monitor flow

```text
mach create
machine LoadPlatformDescription @platforms/boards/<board>.repl
sysbus LoadELF @firmware.elf
showAnalyzer sysbus.uart0
machine StartGdbServer 3333
start
```

Useful commands:

```text
peripherals
sysbus WhatPeripheralIsAt 0x40000000
sysbus ReadDoubleWord 0x40000000
sysbus WriteDoubleWord 0x40000000 0x1
sysbus.cpu Step
pause
quit
```

For raw binaries, set load address and reset vector deliberately; ELF is safer when available because it carries sections and entry point.

## Custom platform guidance

When no board exists:

1. Build the smallest `.repl` from known CPU, RAM/flash, and MMIO ranges.
2. Add UART first if console output is needed.
3. Add timers/interrupt controller before assuming RTOS scheduler failure.
4. Stub unknown peripherals only enough to pass non-target checks.
5. Label the result as partial parity and list unmodeled peripherals.

Sources for modeling clues: vendor datasheet, SVD, linker script, map file, DTB, SDK headers, strings, disassembly xrefs to MMIO addresses, and logic/UART captures.

## GDB

```text
machine StartGdbServer 3333
```

Then connect with the matching toolchain:

```bash
arm-none-eabi-gdb firmware.elf
(gdb) target remote :3333
```

Use GDB to prove reset handler, RTOS task creation, peripheral driver paths, memory state, and breakpoints on fault handlers.

## Evidence

- exact `.repl`/`.resc` or monitor command sequence
- board/profile source and any custom modeled/stubbed devices
- UART transcript, GPIO/peripheral read/write, memory state, or GDB breakpoint
- whether proof is instruction execution, runtime boot, peripheral parity, or system parity

## Failure pivots

- no UART: wrong UART instance, firmware uses semihosting/RTT, clocks not modeled, or boot never reaches init
- stuck in default handler: missing IRQ/timer/peripheral model
- fault after reset: wrong load address, vector table, stack pointer, Thumb bit, or memory map
- GDB oddities on multicore boards: start/select the correct CPU-specific GDB server

