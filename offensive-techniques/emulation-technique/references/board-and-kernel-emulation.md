# Board and Kernel Emulation

Use this reference for MCU, RTOS, board-specific firmware, kernels, drivers, bootloaders, UEFI, and low-level code.

## MCU and RTOS lane

Static facts first:

- vector table, reset handler, entry point, load address
- arch/core, ARM/Thumb, FPU, endian, interrupt table
- RTOS markers: FreeRTOS, Zephyr, ThreadX, RT-Thread, bare metal
- MMIO ranges, UART/GPIO/timer/SPI/I2C accesses
- SVD, DTB, board name, linker script, map file, vendor SDK strings

Tool choice:

- Renode when the board/peripherals exist or can be modeled at register level.
- QEMU system when the exact board or a close machine model exists.
- Unicorn when only an isolated routine or boot stub needs CPU execution.
- Qiling MCU mode when the target matches supported profiles and hooks are useful.
- Ghidra/radare2 static reconstruction when peripheral behavior is too unknown.

Renode validation is board/peripheral validation, not just instruction stepping. Prove UART, GPIO, timers, memory, or a peripheral register relevant to the target.

## Renode profile approach

Renode uses `.repl` platform descriptions and `.resc` scripts. Prefer official platform descriptions first, then create a minimal custom profile when the goal only needs a small set of MMIO ranges.

Minimal monitor flow:

```text
mach create
machine LoadPlatformDescription @platforms/boards/<board>.repl
sysbus LoadELF @firmware.elf
showAnalyzer sysbus.uart0
machine StartGdbServer 3333
start
```

Use `peripherals`, `sysbus WhatPeripheralIsAt <addr>`, `sysbus ReadDoubleWord <addr>`, and `sysbus WriteDoubleWord <addr> <value>` to validate the memory/peripheral model.

Custom profiles should state what is modeled, what is stubbed, and what target behavior is invalid without more peripheral parity.

## Linux kernel lane

Use QEMU system for kernel study. Inputs should come from the task: kernel image, initrd/rootfs, DTB, symbols, config, modules, and command line.

```bash
qemu-system-x86_64 \
  -kernel bzImage \
  -initrd initramfs.cpio.gz \
  -append "console=ttyS0 panic=-1 nokaslr" \
  -serial stdio -display none \
  -S -gdb tcp:127.0.0.1:1234
```

For ARM/MIPS/RISC-V kernels, machine, console, DTB, and block-device names are usually the hard part. Use `strings`, kernel config, DTB `/chosen`, vendor bootargs, and known board docs to choose them.

Good kernel evidence:

- complete `Linux version ...` line
- initramfs marker or shell
- expected panic/oops with full first failure line
- GDB breakpoint on a symbol with matching `vmlinux` or `System.map`
- loaded module log line or device node interaction
- service response from a guest rootfs

Do not claim a kernel version or architecture is covered until that exact caller-supplied artifact boots or reaches the expected controlled failure.

## Drivers and bootloaders

- Linux `.ko`: inspect `modinfo`, unresolved symbols, `file_operations`, `ioctl`, `copy_from_user`, and kernel config requirements before booting.
- Windows `.sys`: static PE/DriverEntry analysis first; dynamic driver testing usually needs a Windows VM or kernel debugger, not generic emulation.
- UEFI: use OVMF/QEMU for DXE/app experiments; preserve NVRAM vars and Secure Boot state if relevant.
- MBR/boot sectors: QEMU with `-S -gdb` and GDB `set architecture i8086`; validate disk reads and control transfer.

## Board parity language

- **Instruction execution**: CPU stepped through code. Useful but weak.
- **Runtime boot**: reset/init reached expected code. Better, still may lack devices.
- **Peripheral parity**: UART/GPIO/timer/storage/network/MMIO behavior needed by the target is modeled well enough for the objective.
- **System parity**: OS, init, devices, and services interact closely enough to answer the runtime question.

Be explicit about which level was proven.

