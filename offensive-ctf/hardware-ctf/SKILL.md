---
name: hardware-ctf
description: "Lab/CTF: hardware/embedded/RF challenges; Saleae/sigrok traces, UART/I2C/SPI/CAN/JTAG/SWD/USB/BLE/RF, firmware, side-channel data."
license: MIT
compatibility: "AgentSkills-compatible agents; local artifacts; authorized isolated lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# Hardware CTF

Solve hardware and embedded lab tasks by identifying the capture or device interface first, then decoding with timing, voltage, framing, and architecture assumptions made explicit.

## When this skill applies

- Logic analyzer captures, Saleae `.sal` files, sigrok sessions, CSV edge traces, oscilloscope traces, audio captures of serial data, or display-signal samples.
- UART, I2C, SPI, CAN, CANopen, JTAG, SWD, USB HID, USB MIDI, Bluetooth RFCOMM/BLE, RF/SDR, RFID/NFC, or peripheral PCAPs.
- Firmware images, SPI flash dumps, UEFI/BIOS blobs, bootloaders, microcontroller binaries, extracted filesystems, board photos, pinouts, schematics, CAD, G-code, or 3D-printing artifacts.
- Side-channel data such as power traces, timing traces, acoustic keyboard samples, LED Morse, or EM/RF measurements.

## Operating model

1. Preserve evidence and identify artifact class: capture, firmware, board/interface, RF sample, side-channel dataset, or CAD/G-code.
2. Lock physical assumptions: sample rate, voltage domain, channel order, idle level, clock, endian, bit order, modulation, architecture, and toolchain.
3. Decode the transport before interpreting payloads: bus framing, packet boundaries, checksums, compression, filesystem, or symbol timing.
4. Choose the narrowest tool path: protocol decoder, firmware extractor, disassembler, emulator, SDR flowgraph, side-channel statistic, or visualization.
5. Validate by reconstructing an observable: secret bytes, image, waveform, register trace, firmware string, UART console output, HID path, RF message, or 3D geometry.
6. Record every assumption that affects decoding so the proof can be replayed or corrected.

## Technique integration

Load these as needed:

- `forensic-technique` for evidence handling, carving, metadata, timelines, and PCAP/peripheral reconstruction.
- `reversing-technique` for firmware, bootloaders, microcontroller binaries, and custom parsers.
- `wireless-technique` for RF/SDR, Bluetooth, Wi-Fi-derived, or radio telemetry tasks.
- `network-technique` for USB/Bluetooth/CAN PCAPs and protocol captures.
- `web-ctf` when a hardware challenge exposes an HTTP or browser-based transceiver, status panel, or session-backed control plane around the decoded protocol.
- `arduino` when a task requires real microcontroller wiring, sketches, Arduino CLI, PlatformIO, or board bring-up.
- `python-patterns` and `systematic-debugging` for decoders, parsers, visualization, and reproducible notebooks/scripts.

## Tool routing

- Logic/bus: `saleae-logic-2`, sigrok/PulseView, sigrok-cli, logic2 automation, Python edge decoders, and protocol decoders.
- Firmware: `binwalk`, `strings`, dd, unsquashfs, UEFITool, chipsec, flashrom, `ghidra`, `radare2`, `binaryninja`, QEMU, and OpenOCD.
- RF/SDR: GNU Radio, Universal Radio Hacker, rtl_433, inspectrum, spectrum tooling, numpy/scipy, and custom demodulators.
- Peripheral captures: `wireshark`, `tcpdump`, usbmon, `bluez`, HID report parsers, MIDI decoders, and image/path reconstruction scripts.
- Side-channel: numpy, scipy, pandas, matplotlib, correlation/DPA scripts, FFT/spectrogram tooling, and clustering/classification only after the signal is understood.
- CAD/G-code: slicer-aware parsers, zlib/heatshrink/QOI decoders, mesh viewers, coordinate projection, and metadata extraction.

## Safety and scope gates

- Do not recommend wiring, flashing, or probing real hardware until voltage, ground, pin role, and target ownership are explicit.
- Prefer offline decoding over physical interaction when artifacts are sufficient.
- Avoid write operations through JTAG/SWD/SPI/flashrom unless an isolated lab target and recovery path are clear.
- Treat unknown pins as unsafe; identify power, ground, reset, boot, UART, and debug pins before connecting tools.
- For RF, follow local legal and lab constraints; passive analysis and replay in shielded or simulated environments are safer defaults.

## Quick pivots

- Logic capture: infer sample rate, channels, idle levels, clock, start/stop bits, and bus decoder settings.
- UART: test baud, parity, stop bits, inversion, and line endings before parsing text.
- I2C/SPI: identify clock/data/chip-select, address or opcode patterns, and multi-byte endian.
- CAN: group arbitration IDs, infer periodic frames, counters, checksums, and signal scaling.
- JTAG/SWD: identify pins non-destructively, confirm chain/device ID, then dump or halt only in lab scope.
- Firmware: extract filesystem, identify architecture, search strings/configs, then reverse validation paths.
- RF/SDR: identify sample format, center frequency, symbol rate, modulation, framing, whitening, and checksum.
- Hybrid RF + web control plane: decode the burst offline first, then use UI state, session fields, or mission text as a control-plane oracle; re-decode each fresh capture instead of assuming a prior instance's exact bytes still apply.
- Side-channel: align traces, average noise, find leakage point, then validate recovered key/material independently.

## Resources

- [references/hardware-artifact-workflow.md](references/hardware-artifact-workflow.md) — detailed triage and workflows for captures, buses, firmware, RF, side-channel, and CAD/G-code.
