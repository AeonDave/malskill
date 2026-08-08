# Debug Ports and Firmware Extraction

Load when the task needs UART/JTAG/SWD/SPI/eMMC access, firmware dumping, or bootloader-level pivots.

Scope: CTF artifact triage and lab-lite pivots (interpret `printenv`/boot logs, validate a dump, choose a next step). For live-hardware attack workflow with concrete commands (JTAGulator sweeps, OpenOCD IDCODE tables, RDP/APPROTECT bypass, `flashrom -p ch341a_spi`, U-Boot bootargs abuse), delegate to `hardware-technique/references/serial-console-attacks.md`, `jtag-swd-attacks.md`, and `firmware-extraction.md` instead of restating them here.

## Fast path

1. Prefer official firmware or update packages first.
2. If that fails, look for debug ports and storage chips.
3. Dump before modifying anything.
4. Validate the dump by identifying partitions, filesystems, or boot strings.

## Interface triage

Look for these before touching the board:

- unpopulated 3–5 pin headers
- vias near the SoC or flash
- silkscreen labels such as `TX`, `RX`, `GND`, `JTAG`, `SWD`, `TCK`, `TMS`
- missing series resistors or jumpers near suspicious pads
- exposed SPI flash, eMMC, or NAND packages

Lock these assumptions early:

- voltage domain (`5V`, `3.3V`, `1.8V`)
- shared ground reference
- probable bus family
- whether in-circuit reads are realistic

## UART workflow

Use UART when the board likely exposes a boot or debug console.

1. Measure pins with a multimeter against ground.
2. Find one stable power pin and one ground pin before guessing TX/RX.
3. If a line fluctuates on boot, capture it with a logic analyzer.
4. Decode with a UART analyzer using likely defaults first: `115200 8N1`, no parity, no inversion.
5. If output is garbage, vary baud, inversion, parity, or stop bits.

Quick rules:

- TX is often idle-high.
- Voltage fluctuation is a clue, not proof; check with a logic analyzer if unsure.
- A valid boot log is the validation signal, not just visible toggling.

Useful tools:

- multimeter
- logic analyzer + PulseView/sigrok
- FTDI/UART adapter
- `screen`, `minicom`, or equivalent serial terminal

## Bootloader pivot

If UART gives a bootloader prompt:

1. Interrupt autoboot only if the lab scope allows it.
2. Read `help` and `printenv` before running writes.
3. Identify storage backend (`spi`, `nand`, `mmc`, `usb`, vendor flash controller).
4. Read partitions or raw flash into RAM first.
5. Copy dumps to removable media or a host before experimenting.

Validation signals:

- partition table matches the running system
- extracted image contains expected bootloader/kernel/filesystem markers
- dump can be mounted, carved, or unpacked cleanly

### U-Boot environment recovery

A board that "cannot finish booting" still holds its previous configuration in env storage, and the boot log tells you where:

1. `*** Warning - bad CRC, using default environment` means `printenv` is showing the **compiled-in default**, not the saved config — the stale env is still on the chip, merely not loaded. Author-added defaults such as `env_offset=0x800` name the offset to read.
2. Enumerate before reading: `i2c bus`, then per bus `i2c dev <n>` and `i2c probe`. `0x50` is the usual EEPROM, `0x68` an RTC (with battery-backed NVRAM), `0x18` a sensor.
3. Read raw with `i2c md <chip> <off>.2 <len>` (`.2` = 16-bit addressing, length in hex). The env blob is a 4-byte CRC followed by NUL-separated `key=value` pairs ending in a double NUL — parse those bytes yourself rather than trying to make U-Boot accept them.
4. Redundant env means two copies (commonly `0x0` and `env_offset`). **Diff them** — the differences are exactly the "previous configuration" the task wants.

**Scan each chip's whole address space; spot-checking lies.** A boot log calling one EEPROM "erased" only means the offsets *U-Boot* checked read `0xFF`. Key material can sit anywhere else on that same device — e.g. an `AES_KEY=` / `IV=` / `AES_MODE=` block at `0x100` on the very bus whose env area was blank, while the ciphertext sits on the other bus. Dump the full device on every bus and grep; do not conclude "blank" from two sampled offsets.

**Read ciphertext and key from the same instance.** Emulated/containerised targets often regenerate the key or IV per spawn, so the stored ciphertext changes every boot while the plaintext flag stays constant. Mixing a dump from one instance with key material from another fails silently and looks like a wrong algorithm.

`md`'s address radix is build-dependent: if `md 40000000` prints `02625a00` it parsed the argument as decimal, so pass `0x`-prefixed addresses.

## SPI flash extraction

Use SPI extraction when the flash chip is identifiable and read access is enough.

Workflow:

1. Identify the chip and find its datasheet.
2. Try in-circuit read first only if the host CPU is not contending for the bus.
3. If in-circuit read fails, hold the target in reset or move to chip-off extraction.
4. Read with `flashrom` or the programmer-native tool.
5. Hash and archive the original dump immediately.
6. Run `binwalk`, `file`, strings, and filesystem extraction on the image.

Common validation signals:

- flash chip ID is detected
- repeated reads match hashes
- dump contains bootloader strings, partitions, or known filesystem headers

Common failure causes:

- wrong voltage
- chip-select not driven cleanly
- CPU still driving the bus
- unstable clips or bad ground
- reading too fast for the setup

## JTAG and SWD workflow

Use these only when UART or firmware-package paths are insufficient.

1. Identify likely debug pins non-destructively.
2. Start with chain or target ID only.
3. Confirm the tool sees the device before halting or dumping memory.
4. Dump or inspect in the smallest scope first.
5. Do not write, unlock, mass-erase, or reflash unless the objective requires it and recovery exists.

Typical goals:

- halt the CPU
- inspect memory maps
- dump flash or RAM
- recover firmware when no filesystem image is otherwise available

## Pitfalls

- Treating every 4-pin header as UART.
- Writing to flash before proving the backup is valid.
- Assuming online firmware packages contain bootloader and calibration partitions.
- Reading a raw dump once and trusting it without a repeat hash check.
- Confusing a bootloader shell with full root access; verify mounts, block devices, and read/write limits.
- Forgetting that firmware packages and raw flash dumps answer different questions.
