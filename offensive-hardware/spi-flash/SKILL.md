---
name: spi-flash
description: In-circuit and out-of-circuit SPI/NAND flash dumping and writing using flashrom and CH341A/FT232H.
---

# spi-flash

Use when UART is unavailable, or a full firmware extraction/patching loop is required.

## 1. Identification and connection

- Look for 8-pin or 16-pin SOIC chips near the SoC (e.g., Winbond `W25Q*`, Macronix `MX25L*` or GigaDevice `GD25Q*`).
- **In-circuit**: Attach a SOIC clip. Ensure the target board is completely powered off to prevent SoC interference.
- **Out-of-circuit**: Desolder using hot air, clean pads, mount in programming socket. (Safest for signal integrity, but destructive).

## 2. Reading firmware (flashrom)

**Rule**: Read at least twice, and ensure hashes match before proceeding. Variance indicates bad clip contact or SoC contention.

```bash
# Read attempt 1
flashrom -p ch341a_spi -r fw_dump1.bin

# Read attempt 2
flashrom -p ch341a_spi -r fw_dump2.bin

# Verification
md5sum fw_dump1.bin fw_dump2.bin
```
*If hashes differ, reseat the clip, shorten cables, or power the target board VCC slightly if SoC is draining programmer current.*

## 3. Writing firmware

**Rule**: Always backup original raw dump offline before writing.

```bash
# Write modified firmware back
flashrom -p ch341a_spi -w fw_patched.bin
```

## 4. Flash layout verification
Use `binwalk` to verify the read was successful and contains expected headers (not just `0xFF` or `0x00`).
```bash
binwalk fw_dump1.bin
# Expect: U-Boot header, Squashfs, JFFS2, TRX, or CramFS
```

## References
- [references/ch341a-voltage-fix.md](references/ch341a-voltage-fix.md) — Load when using a CH341A programmer on 1.8V or 3.3V target flash chips.
