# Firmware Extraction and Analysis

Reference for obtaining and analyzing firmware from embedded devices.

---

## Acquisition paths (prioritize least invasive)

| Path | Invasiveness | Requires | When to use |
|------|-------------|----------|-------------|
| Vendor download | None | Model + firmware version | Always try first |
| UART / U-Boot dump | Low | Serial access, U-Boot shell | UART accessible |
| JTAG dump | Medium | Debug probe, pin access | UART blocked |
| SPI in-circuit dump | Medium-High | Clip + programmer | Device powered off |
| Chip-off (NAND/NOR) | High | Rework station, BGA skills | All else blocked |

---

## Vendor download

```bash
# Search: "<vendor> <model> firmware download"
# Common sources:
#   - Vendor support portal (often requires serial/MAC registration)
#   - FCC database (https://www.fcc.gov/oet/ea/fccid) — firmware in test reports
#   - firmware.re, openwrt firmware selector, exploit-db firmware mirrors
#   - GitHub (vendor open-source components, GPL releases)

# Extract once downloaded
binwalk -e <firmware.bin>
```

---

## SPI flash extraction (in-circuit)

```bash
# Tools: ch341a USB programmer + SOIC-8 clip
# Identify chip: Winbond W25Q128, Macronix MX25L12835F, GigaDevice GD25Q127C

# Install flashrom
sudo apt install flashrom

# Probe chip type
flashrom -p ch341a_spi

# Dump (always do twice and compare)
flashrom -p ch341a_spi -r firmware1.bin
flashrom -p ch341a_spi -r firmware2.bin
md5sum firmware1.bin firmware2.bin   # must match — if not, check clip connection

# Write modified firmware (lab only, authorized)
flashrom -p ch341a_spi -w modified.bin --verify
```

---

## NAND flash extraction

NAND is more complex than SPI: requires ECC (error correction), bad block mapping, and OOB (out-of-band) data handling.

```bash
# Tools: NAND Flash programmer (e.g., Dediprog, RT809H, TNM5000)
# Extract raw NAND image including OOB
# Then use nanddump or ubi-utils to reconstruct filesystem:
nanddump --oob --bb=skipbad /dev/mtd0 -f nand_raw.bin
ubiformat /dev/mtd0; ubimkvol /dev/ubi0 -N rootfs -m
```

---

## Firmware analysis with binwalk

```bash
# Identify contents
binwalk firmware.bin

# Extract all recognized formats recursively
binwalk -Me firmware.bin
# Output in: _firmware.bin.extracted/

# Common extractions:
#   squashfs → squashfs-root/ (Linux root FS)
#   cramfs   → cramfs-root/
#   jffs2    → jffs2-root/
#   ubifs    → ubifs-root/
#   gzip/lzma compressed data → auto-decompressed

# Manual SquashFS extraction (if binwalk fails)
unsquashfs -d squashfs-root squashfs.img
```

---

## Credential and secret hunting

```bash
cd _firmware.bin.extracted/

# Passwords and hashes
find . -name "shadow" -o -name "passwd" 2>/dev/null
grep -r "password\|passwd\|secret\|api_key\|token\|pass=" --include="*.conf" --include="*.cfg" --include="*.ini" --include="*.json" --include="*.xml" -l 2>/dev/null | head -20

# Private keys and certificates
find . -name "*.pem" -o -name "*.key" -o -name "*.crt" -o -name "*.p12" 2>/dev/null
grep -r "BEGIN PRIVATE KEY\|BEGIN RSA PRIVATE KEY\|BEGIN EC PRIVATE KEY" . -l 2>/dev/null

# Hardcoded strings in binaries
strings squashfs-root/usr/sbin/httpd | grep -i "pass\|admin\|secret\|key\|token\|auth"

# Backdoor indicators
find . -name "*.sh" | xargs grep -l "nc \|netcat\|/dev/tcp\|bash -i" 2>/dev/null
```

---

## Architecture identification for reversing handoff

```bash
file squashfs-root/bin/busybox
# Common results:
#   ELF 32-bit LSB, ARM → Ghidra ARM (LE), IDA ARM
#   ELF 32-bit MSB, MIPS → Ghidra MIPS (BE), radare2 -a mips -b 32
#   ELF 64-bit LSB, AArch64 → Ghidra AARCH64
#   ELF 32-bit LSB, Intel 80386 → standard x86

# Cross-architecture emulation for dynamic analysis
# Use QEMU user-mode or system emulation:
qemu-arm-static -L squashfs-root squashfs-root/usr/sbin/httpd
# Or full system with firmwalker/FirmAE for complex setups
```

---

## Key files to examine after extraction

| Path | Content |
|------|---------|
| `/etc/passwd`, `/etc/shadow` | User accounts and password hashes |
| `/etc/config/` | OpenWrt UCI config (network, firewall, credentials) |
| `/etc/init.d/` | Init scripts — startup services, privesc vectors |
| `/usr/lib/cgi-bin/` | Web CGI — often vulnerable to command injection |
| `/www/` or `/htdocs/` | Web root — source review for auth bypass, LFI |
| `/etc/ssl/` | TLS certificates and private keys |
| `/tmp/` (in running device) | Temp credentials, session tokens |
| Build artifacts | Debug symbols, hardcoded IPs, internal hostnames |

---

## Tools summary

| Tool | Purpose |
|------|---------|
| `binwalk` | Firmware identification, extraction, entropy analysis |
| `flashrom` | SPI/NOR flash read/write via programmer |
| `unsquashfs` | Manual SquashFS extraction |
| `ubi-utils` | UBIFS / UBI volume reconstruction |
| `strings` | Printable string extraction from binaries |
| `file` | Binary type/architecture identification |
| `qemu-*-static` | Cross-architecture emulation for dynamic analysis |
| `firmwalker` | Automated filesystem triage for common secrets |
| `FirmAE` | Full-system firmware emulation framework |
| Ghidra, radare2 | Reverse engineering — hand off to `reversing-technique` |
