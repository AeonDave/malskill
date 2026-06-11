# STM32 RDP (Read-Out Protection) Bypass

**Load when**: `OpenOCD` connects to an STM32 MCU via JTAG/SWD, but `mdw` or `dump_image` return `0x00000000`, `0xFFFFFFFF`, or fail completely.

## Overview

STM32 devices implement Read-Out Protection (RDP) via option bytes:
- **Level 0**: Unlocked (full debug and flash access).
- **Level 1**: Locked (debug access restricted, flash unreadable externally).
- **Level 2**: Permanently locked (debug port physically disabled).

## Level 1 Unlock (Destructive)

If the goal is to flash new firmware or wipe the device, you can downgrade from RDP Level 1 to Level 0. **Warning: This erases the flash memory entirely (mass erase).**

```bash
# In OpenOCD telnet console (localhost 4444)
halt
stm32f1x unlock 0   # Substitute f1x with f2x, f4x depending on target
reset halt
```

## Level 1 Bypass (Non-Destructive)

If the goal is firmvare extraction, bypassing Level 1 without triggering the mass erase requires physical fault injection (voltage or electromagnetic glitching).

1. **Target**: The option byte check occurs during the STM32 reset vector sequence.
2. **Method**: A voltage glitch (momentarily dropping VCC to ~0V) or an EM pulse is applied precisely when the boot ROM evaluates the RDP level from SRAM.
3. **Outcome**: The CPU skips the branch instruction that locks the JTAG port, dropping into the user code with full SWD/JTAG debug access enabled.
4. **Tooling**: Requires an FPGA-based glitcher (e.g., ChipWhisperer, PicoEMP) hooked to the target's VCAP or VDD lines, using `nSRST` as the trigger signal with a tuned nanosecond delay.
