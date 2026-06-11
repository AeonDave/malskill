---
name: uart-console
description: Identification, connection, and exploitation of UART serial consoles (U-Boot/Barebox interrupt, bootargs patching) during hardware assessments.
---

# uart-console

Use when physical access is available, and you need an interactive root shell without desoldering chips or risking firmware corruption.

## 1. Pin identification

- **Visual**: Look for 3-4 unpopulated through-holes or test pads near the SoC.
- **Multimeter**:
  1. `GND`: 0 V (continuity with shielding).
  2. `VCC`: 3.3 V or 5 V (constant).
  3. `TX`: Idle HIGH (3.3 V), fluctuates during boot.
  4. `RX`: High-impedance (floats to ~0 V or pull-up).
- **JTAGulator**: Use UART scan capability if pads are unlabeled/dense.

## 2. Connection

**Rule**: Do NOT connect VCC if the device is self-powered. This causes voltage collision.
- Connect: `GND → GND`, `RX → TX_pad`, `TX → RX_pad`.

```bash
# Try standard baud rates: 115200, 57600, 38400, 19200, 9600
screen /dev/ttyUSB0 115200
# or
minicom -D /dev/ttyUSB0 -b 115200
```
*If output is garbled, cycle through baud rates. Check logic analyzer for precise rate if needed.*

## 3. Bootloader exploitation (U-Boot)

Monitor output closely on power-on.
- Prompt: `Hit any key to stop autoboot`. Press immediately.

**Key U-Boot commands:**
```bash
printenv         # Dump environment variables (credentials, boot paths, keys)
md 0x80000000    # Hex dump memory (hunt for loaded keys/passwords)
boot             # Resume boot process
```

**Drop to shell (root init bypass):**
```bash
# Replace normal init with a shell to bypass authentication
setenv bootargs 'console=ttyS0,115200 root=/dev/mtdblock2 init=/bin/sh'
boot
```

## 4. Secure boot bypass patterns

If U-Boot enforces verified boot (`CONFIG_SECUREBOOT`):
1. Read signing keys from NAND/SPI mapping (sometimes unprotected).
2. Patch U-Boot env locally to drop `CONFIG_SECUREBOOT` (requires SPI write).
3. Voltage glitching on SoC VCC rail exactly during signature verification branching.
