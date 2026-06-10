# Debug Ports and Firmware Extraction

Load when the task needs UART/JTAG/SWD/SPI/eMMC access, firmware dumping, or bootloader-level pivots.

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
