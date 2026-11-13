---
name: jtag-swd
description: Non-destructive JTAG/SWD pin identification, OpenOCD configuration, CPU halting, and runtime memory dumping.
---

# jtag-swd

Use when firmware extraction is needed but direct SPI flash reading is physically impossible (BGA chips, eMMC), or live debugging/execution flow control is required.

## 1. Interface identification

- **Standard JTAG**: `TCK`, `TMS`, `TDI`, `TDO`, `nTRST`, `nSRST`, `GND`, `VCC`.
- **ARM SWD**: Compact 2-wire alternative (`SWDIO`, `SWDCLK`, `GND`, `VCC`).
- Use tools like *JTAGulator* or *JTAGenum* on unknown pin headers to automatically scan for TDO responses without manual probing.

## 2. Electrical and target preflight

Before connecting, confirm the target's I/O voltage, probe voltage compatibility, supported transport (JTAG or SWD), pinout, and any required level shifting from the target and probe documentation. Do not assume VTref powers the target or has the same function on every probe; check that probe's manual before wiring or powering anything. See the [OpenOCD adapter guidance](https://openocd.org/doc/html/Debug-Adapter-Configuration.html).

For the original ESP32, use JTAG, not SWD. ESP-IDF v6.1 documents JTAG I/O on `VDD_3P3_RTC` (normally 3.3 V); ensure the adapter supports the target's I/O level. Do not generalize this pin, voltage, or transport note to other ESP32-family chips; check the exact device documentation. See [ESP-IDF v6.1 JTAG debugging](https://docs.espressif.com/projects/esp-idf/en/v6.1/esp32/api-guides/jtag-debugging/index.html).

ESP-IDF v6.1 documents a configuration-dependent case where flash-encryption setup disables JTAG by burning the relevant eFuse on first boot. Check the project's flash-encryption configuration and actual eFuse state for the specific original ESP32 before expecting debug access; flash encryption alone is not evidence that this eFuse was burned. See [ESP-IDF v6.1 flash encryption](https://docs.espressif.com/projects/esp-idf/en/v6.1/esp32/security/flash-encryption.html#jtag-debugging).

## 3. OpenOCD connection

Map the physical interface (e.g., FTDI-based programmer like Olimex or TIAO) and the target MCU architecture.

```bash
# Example: Connect to an STM32F4 via an Olimex ARM-USB-OCD-H programmer
openocd -f interface/ftdi/olimex-arm-usb-ocd-h.cfg -f target/stm32f4x.cfg
```

## 4. Execution control & dumping

Connect to OpenOCD's telnet control interface (`localhost:4444`).

```text
> telnet localhost 4444
# Halt the CPU execution cleanly
> halt

# Inspect CPU state and registers
> reg

# Dump specific memory region (e.g., 1MB starting from flash base 0x08000000)
> dump_image firmware.bin 0x08000000 0x100000

# Resume normal execution
> resume
```

## 5. Risks & Considerations
- **Watchdog Timers**: Halting via JTAG may trigger hardware watchdogs, causing abrupt resets.
- **Read-out Protection (RDP)**: Microcontrollers (especially STM32/NRF) often set internal fuses disabling JTAG debug access or flash reads. Bypassing requires chip-specific glitching workflows.

## References
- [references/stm32-rdp-bypass.md](references/stm32-rdp-bypass.md) — Load when an STM32 Read-Out Protection (RDP) prevents memory extraction in OpenOCD.
