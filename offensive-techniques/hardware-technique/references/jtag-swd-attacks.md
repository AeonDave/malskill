# JTAG/SWD Attack Reference

Practical workflow for JTAG (IEEE 1149.1) and SWD (ARM Serial Wire Debug) interfaces on embedded targets.

## Pin identification

**Standard JTAG pinout (TAP)**
- `TCK` — Test Clock
- `TMS` — Test Mode Select
- `TDI` — Test Data In
- `TDO` — Test Data Out
- `TRST` — Test Reset (optional)
- `GND`, `VTREF` — reference voltage (read-only, do not source)

**SWD pinout (2-wire ARM)**
- `SWCLK` — clock
- `SWDIO` — bidirectional data
- `SWO` — trace output (optional)
- `nRESET` — system reset

**Common header footprints**
- 20-pin 0.1" ARM JTAG, 10-pin 0.05" Cortex Debug, 14-pin TI, 6-pin SWD, undocumented test pads/vias.

## Pin discovery

When pins are unmarked:

1. **Visual / continuity** — multimeter buzzer for pullup resistors near MCU; TDO usually weakly driven, TMS/TDI pulled high.
2. **JTAGulator** — brute-forces TDI/TDO/TCK/TMS combinations over test channels, decodes IDCODE.
3. **JTAGenum** — Arduino sketch alternative; slower but free.
4. **Logic analyzer** — capture during boot, look for clocked serial activity on suspect pads.

**Mandatory before probing**: confirm `VTREF` with multimeter; level-shift if target is 1.8V/3.3V and adapter is 5V.

## Hardware adapters

| Adapter | Cost | Notes |
|---------|------|-------|
| Bus Pirate v3/v4 | $30 | OpenOCD-supported, slow but flexible |
| Black Magic Probe | $60 | Standalone GDB server, no OpenOCD needed |
| Segger J-Link EDU | $60 | Fast, broad MCU support, non-commercial license |
| ST-Link V2 (clone) | $5 | SWD only, ARM Cortex-M |
| FT2232H breakout | $25 | Generic, OpenOCD interface=ftdi |
| Raspberry Pi (bcm2835) | — | Bit-bang JTAG via OpenOCD `interface/raspberrypi-native.cfg` |

## OpenOCD baseline workflow

```bash
# Identify target — start with generic config, watch IDCODE
openocd -f interface/jlink.cfg -c "transport select jtag" \
        -c "adapter speed 100" -c "init" -c "scan_chain" -c "exit"

# Once IDCODE matches a known MCU, load full target config
openocd -f interface/jlink.cfg -f target/stm32f1x.cfg

# In another terminal: GDB or telnet
telnet localhost 4444
> halt
> flash banks
> dump_image firmware.bin 0x08000000 0x20000
> exit
```

**Common DAP IDCODE/DPIDR patterns** (these identify the ARM debug port, not the core — same DAP is reused across families; confirm with target-config match):
- `0x4ba00477` — ARM CoreSight generic DAP (Cortex-A5/A7/A8/A9/A15, also STM32F4 JTAG SWJ-DP)
- `0x2ba01477` — ARM SW-DP v1 (Cortex-M3/M4 SWD, STM32F1/F4 SWD path)
- `0x0bc11477` — ARM SW-DP v2 (Cortex-M0+ / STM32F0)
- `0x6ba02477` — ARM SW-DP v2 multi-drop (Cortex-M33, newer STM32L5/U5)

## Flash dump

```bash
# After halt, dump entire flash region
> dump_image fw.bin <flash_base> <size>

# Verify: re-read and compare
> verify_image fw.bin <flash_base>
```

For SPI flash on board (separate from MCU): desolder or in-circuit clip → `flashrom -p ch341a_spi -r dump.bin`.

## Read protection bypass

| MCU family | Protection | Bypass notes |
|------------|------------|--------------|
| STM32 RDP Level 1 | Debug disabled, mass erase allowed | RDP1→RDP0 via voltage glitch on `bootrom` RDP check (ChipWhisperer/PicoGlitcher, well-documented) |
| STM32 RDP Level 2 | Nominally permanent | RDP2→RDP1 downgrade reproduced via voltage glitching (SEC-Consult SECGlitcher 2020; voidstarsec CSW-2024 low-cost EMFI; SySS STM32L05 2023). Then read as RDP1. Not effective on newest STM32 with dual-glitch mitigations. |
| Nordic nRF52 APPROTECT | SWD blocked | Classic bypass: single voltage glitch on APPROTECT read (LimitedResults 2020). Improved APPROTECT in nRF52840 rev3 (Fx0), nRF52832 rev3 (Gx0), nRF52833 rev2 (Bx0) etc. hardens the single-glitch path; still bypassable per 2023–2024 research (Matias Soler nRF52832 bypass; O'Reilly *Microcontroller Exploits* ch.16, 2024). Confirm build code before campaign. |
| ESP32 eFuse Secure Boot | Encrypted flash | Side-channel on early revisions; current revisions hardened |
| NXP LPC CRP1/CRP2/CRP3 | Tiered | CRP1 keeps ISP; can sometimes read via ISP commands |

Always check the latest research before declaring a target unrecoverable; vendor mitigations evolve.

## SWD-specific notes

- 2-wire only; identification via DPIDR register read.
- OpenOCD: `transport select swd` and matching `target/*.cfg`.
- ARM Cortex-M: SWD provides full debug (halt, register access, memory R/W) equivalent to JTAG for most operations.
- Multi-drop SWD (newer Cortex-M) requires `dap apsel`/`dap dpreg` tuning.

## Halt-and-extract gotchas

- Halting MCU may freeze peripherals (watchdog, motor controllers, safety interlocks). On safety-critical targets, halt only in controlled bench environment.
- Some bootloaders disable JTAG after boot — interrupt with `reset halt` immediately on power-up.
- Code RAM may differ from flash if bootloader decrypts in place; dump RAM region post-boot for runtime image.

## Fault injection adjuncts

Voltage glitching (ChipWhisperer, PicoEMP, custom MOSFET rig) can bypass:
- Secure boot signature checks
- RDP/APPROTECT lifecycle bits
- PIN comparison loops in bootloader

Successful glitch parameters (delay/width) are target-specific; campaign requires 10^3–10^6 attempts with success-detection oracle.

## Evidence to capture

- IDCODE / DPIDR full chain
- Flash dump SHA-256
- Memory map (RAM, flash, peripheral regions)
- Protection bit states pre/post operation
- OpenOCD logs (`-d3` for debug)

## References

- OpenOCD User's Guide — https://openocd.org/doc/html/
- ARM ADIv5/ADIv6 Architecture Specification (debug protocol)
- JTAGulator project — http://www.grandideastudio.com/jtagulator/
- "Hardware Hacking Handbook" (Woudenberg & O'Flynn, 2021) — fault injection chapters
