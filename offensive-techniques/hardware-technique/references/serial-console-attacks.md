# Serial Console Attacks (UART)

Reference for UART/serial console exploitation in hardware assessments.

---

## UART fundamentals

UART (Universal Asynchronous Receiver-Transmitter) is the most common debug interface on embedded devices. It requires 3 connections: TX (transmit), RX (receive), GND. VCC is optional and dangerous — never connect VCC if the target is self-powered.

Voltage levels: 3.3 V is most common on modern SoCs; older devices and industrial hardware may use 5 V or 1.8 V. Always measure before connecting.

---

## Pin identification workflow

```
1. Power on device, observe boot activity.
2. Locate 3–4 adjacent unpopulated pads/holes near the SoC (often labeled J1, J2, DEBUG).
3. Multimeter in DC voltage mode:
   - GND: ~0 V (relative to known ground reference)
   - VCC: constant 3.3 V or 5 V
   - TX: ~3.3 V at idle, toggles during boot
   - RX: measured as high-impedance input; inject known signal from adapter to verify
4. Logic analyzer on TX pin confirms boot data at specific baud rate.
```

### JTAGulator — automated pin identification

```bash
# JTAGulator can scan UART pins automatically
# Connect all candidate pins to JTAGulator channels
# Run UART discovery: JTAGulator sends known strings at multiple baud rates
# Reports detected TX pin and baud rate
```

---

## Connection setup

```bash
# Required: USB-UART adapter (CP2102, CH340, FT232RL)
# Wire: adapter-TX → device-RX, adapter-RX → device-TX, adapter-GND → device-GND

# Linux: adapter appears as /dev/ttyUSB0 or /dev/ttyACM0
ls /dev/ttyUSB*

# Connect with screen (Ctrl-A, K to exit)
screen /dev/ttyUSB0 115200

# Connect with minicom
minicom -D /dev/ttyUSB0 -b 115200

# Log session to file (useful for reporting)
screen -L -Logfile uart_session.log /dev/ttyUSB0 115200
```

---

## Baud rate identification

If output is garbled, cycle through standard baud rates. Most embedded Linux devices use 115200; industrial/legacy may use lower rates.

```bash
# Common baud rates in priority order:
# 115200  57600  38400  19200  9600  4800  2400

# Automated brute-force with minicom:
for baud in 115200 57600 38400 19200 9600; do
  echo "Trying $baud..."
  timeout 5 minicom -D /dev/ttyUSB0 -b $baud -C /tmp/uart_${baud}.log
done

# Inspect logs for readable ASCII — correct baud shows boot messages
```

---

## Boot console exploitation

### U-Boot (most common embedded bootloader)

```
During power-on, watch for: "Hit any key to stop autoboot: X"
→ Press any key immediately to enter U-Boot shell

U-Boot commands:
  printenv              — dump all environment variables
  setenv <var> <val>    — set variable
  saveenv               — persist to flash
  boot                  — continue boot with current args
  md 0x80000000 100     — memory dump (hex dump) at address, 100 words
  mw 0x80000000 0 1     — memory write (careful)
  sf probe; sf read ... — SPI flash operations
  nand read ...         — NAND flash read
  tftp <addr> <file>    — load image over TFTP
```

### Modify kernel boot args for immediate root shell

```bash
# In U-Boot:
printenv bootargs                    # record original (for rollback)
setenv bootargs 'console=ttyS0,115200 root=/dev/mtdblock2 rw init=/bin/sh'
boot
# → drops to /bin/sh as root before any OS init

# Alternative: append to existing args
setenv bootargs "${bootargs} init=/bin/sh"
boot
```

### Barebox bootloader

```bash
# Similar to U-Boot; interactive shell available
devinfo               # list devices
ls /                  # filesystem view
boot                  # continue
# Modify bootargs: edit /env/boot/default or use 'global bootargs'
```

---

## Common UART console scenarios

### Scenario 1: Root shell directly

Some devices drop straight to a root shell on serial console with no authentication. Enumerate immediately:

```bash
id; uname -a; cat /etc/passwd; cat /etc/shadow; ifconfig; netstat -tlnp
```

### Scenario 2: Login prompt with unknown credentials

```bash
# Try before bruteforcing:
root:(empty)
root:root
root:admin
root:password
root:toor
admin:admin
# Device model-specific defaults (check vendor manuals, FCC filings)

# Bruteforce with minicom scripting or custom expect script:
expect -c "
spawn minicom -D /dev/ttyUSB0 -b 115200
expect \"login:\" { send \"root\r\" }
expect \"Password:\" { send \"\r\" }
expect \$ { send \"id\r\" }
interact
"
```

### Scenario 3: Restricted shell (rbash, ash limited)

```bash
# Escape techniques:
vi               # :!/bin/sh
more /etc/passwd # !/bin/sh
python3 -c 'import pty; pty.spawn("/bin/sh")'
# Set PATH: export PATH=/bin:/sbin:/usr/bin:/usr/sbin
```

### Scenario 4: Single-user mode (systemd/SysV)

```bash
# On kernel with systemd — add to bootargs:
systemd.unit=rescue.target   # or emergency.target

# On SysV init:
init=/bin/sh
# or:
single
```

---

## Secure boot bypass techniques

When U-Boot enforces verified boot (signature check on kernel image):

1. **Read environment from flash**: U-Boot config and signing keys are often stored unprotected in a separate flash partition. Dump with SPI programmer and look for key material.
2. **Environment override via UART**: some builds allow `setenv verify 0` to disable signature check.
3. **Voltage glitching**: inject a brief voltage drop on VCC during the signature verification window to cause a computation fault. Requires a glitching tool (ChipWhisperer, self-built crowbar circuit) and timing calibration.
4. **Downgrade attack**: if key rotation hasn't occurred, sign a vulnerable older U-Boot binary with the device's known key (extracted from another unit or leaked firmware).
5. **Flash write bypass**: reflash a modified U-Boot without secure boot enabled using SPI programmer after chip-off.

---

## Tools summary

| Tool | Use |
|------|-----|
| `screen` | Terminal emulator for UART sessions |
| `minicom` | Configurable serial terminal with logging |
| `picocom` | Lightweight alternative to minicom |
| JTAGulator | Automated UART/JTAG pin identification |
| Bus Pirate | Multi-protocol interface (UART, SPI, I2C, 1-Wire) |
| CP2102 / CH340 / FT232RL USB-UART | Common USB-to-UART adapters |
| `expect` | Scripted interaction for automated login attempts |
| ChipWhisperer | Voltage glitching and power side-channel platform |
