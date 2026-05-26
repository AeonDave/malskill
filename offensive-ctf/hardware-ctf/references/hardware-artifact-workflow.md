# Hardware Artifact Workflow

Use this reference when `hardware-ctf` is active and the task needs a deeper, artifact-specific path.

## Capture triage matrix

| Artifact cue | First questions | Primary workflow |
|---|---|---|
| `.sal`, sigrok, CSV transitions | sample rate, channel order, idle level, clock, trigger point | logic analyzer decode |
| UART-like waveform or WAV | baud, inversion, parity, stop bits, bit order | serial reconstruction |
| I2C/SPI traces | clock/data/chip-select, address/opcode, endian | bus transaction decoding |
| CAN log or PCAP | bitrate, arbitration IDs, counters, checksum, scaling | signal inference |
| USB/Bluetooth PCAP | device class, HID report descriptor, endpoints, pairing/session | peripheral reconstruction |
| IQ samples | sample format, center frequency, bandwidth, modulation, symbol rate | RF demodulation |
| firmware/SPI dump | container, filesystem, architecture, bootloader, entropy | extraction and reversing |
| GPIO/LCD trace | pin mapping, clock edge, data width, controller command set | display reconstruction |
| side-channel traces | alignment, axes, leakage model, noise, target operation | statistical key/value recovery |
| CAD/G-code or printer video | compression, metadata, thumbnails, coordinates, layers, camera perspective | geometry/metadata or nozzle-motion extraction |

## Logic analyzer workflow

1. Inspect file container before decoding. Saleae `.sal` files are archives; sigrok sessions are often ZIP-like containers.
2. List channels and transitions; identify idle-high versus idle-low lines.
3. Recover clocks where possible. For asynchronous UART, infer bit period from edge spacing.
4. Test decoder settings systematically: baud, parity, stop bits, bit order, inversion, CPOL/CPHA, address width.
5. Export decoded bytes and raw timing together; errors often hide in a single wrong physical assumption.
6. Validate by reconstructing known framing: printable strings, checksums, command-response rhythm, or repeated packet lengths.

## Firmware and embedded workflow

1. Run file identification and entropy checks.
2. Carve containers and filesystems before reversing raw blobs.
3. Identify architecture using headers, strings, opcode density, vector tables, reset handler patterns, or tool output.
4. Search for secrets, command names, debug strings, firmware version, network endpoints, and validation functions.
5. Reconstruct runtime environment only as needed: QEMU user/system, emulator stubs, or hardware debugger.
6. If patching, keep original hashes and produce a minimal diff that explains the changed control flow.

## RF and SDR workflow

1. Lock sample format: complex float32, complex int16, unsigned int8, interleaved IQ, sample rate, and center frequency.
2. Visualize spectrum and waterfall; identify bursts, carriers, bandwidth, and repeated frames.
3. Estimate symbol rate and modulation; downconvert, filter, clock recover, and demodulate.
4. Test framing: preamble, sync word, whitening/scrambling, Manchester or NRZ, CRC/checksum, and endian.
5. Decode payloads only after the physical layer is stable.
6. Validate by reproducing multiple frames, not a one-off lucky decode.

## RF + application control-plane crossover

1. Decode and validate the physical layer first. If the lab also exposes a web/API "transceiver", treat it as a shim around the decoded protocol, not as a substitute for RF analysis.
2. Prime companion state before state-changing requests. Hybrid labs often seed session or UI state from the landing page; otherwise accepted frames can look invalid because the control plane is uninitialized.
3. Use application-visible state as an oracle: status tables, mission text, download endpoints, client-visible session fields, or health indicators can classify packet families faster than page-diffing alone.
4. Re-decode every fresh capture or service instance. Symbol timing and CRC may stay stable while preamble bytes, headers, addresses, or command families change between deployments.
5. Test state-gated families under different prerequisite states. A packet family that causes alarms from baseline may correctly disable a component only after a separate suppress family has already changed the system state.
6. Group results by resulting device or mission state, not just response status. Distinguish no-op, safe-progress, and fail-state tuples before widening search.

## Peripheral capture workflow

- USB HID keyboard: parse report descriptors, modifiers, keycodes, rollover, and backspaces/arrows.
- USB HID mouse or pen: integrate relative movement or draw absolute coordinates; account for button state.
- USB MIDI: map note/control messages and time deltas into grids, colors, or sequenced events.
- Bluetooth RFCOMM/BLE: reassemble streams or attributes before interpreting application payloads.
- LED/video side channels: extract frame timing, threshold states, then decode Morse, binary, or pulse-width data.
- HD44780-style LCD GPIO traces: infer clock from transition density, map RS/data lines, sample nibbles on the correct edge, assemble bytes, then map DDRAM addresses to display rows.

## Architecture and board-level reversing crossover

- Treat firmware architecture as part of hardware evidence: ARM/AArch64, MIPS, RISC-V, AVR, Xtensa, and bootloader formats can change endian, reset vectors, and peripheral assumptions.
- For RISC-V targets, check standard bitmanip/crypto extensions and custom opcodes before assuming invalid disassembly.
- Inspect privileged-mode and CSR usage (`mstatus`, `mtvec`, `mepc`, `mcause`, `satp`) when firmware, bootloader, or trap-handler behavior matters.
- Use QEMU/OpenOCD/GDB-style emulation or debugging only after artifact triage identifies architecture, memory map, and expected validation signal.

## Side-channel workflow

1. Align traces by trigger, correlation, or dynamic time warping if necessary.
2. Average repeated traces to reduce noise.
3. Identify leakage sample by variance, correlation, or difference of means.
4. Test a simple leakage model before complex machine learning.
5. Validate recovered material by decrypting, hashing, or replaying against an independent oracle.

## CAD, G-code, and 3D-printing workflow

- Inspect comments, slicer metadata, thumbnails, custom sections, and compressed blocks.
- Decode known thumbnail formats such as QOI or zlib-compressed previews when present.
- Project toolpaths by layer, extrusion, travel moves, and comments; hidden text often appears in coordinates or layer changes.
- Compare model geometry and generated G-code when both are available.
- For a video of a 3D printer, track nozzle or bed positions frame-by-frame, filter to active extrusion on the visible text/top layer, then plot a 2D scatter or histogram of physical X/Y positions to reveal printed letters.
- Calibrate camera axes: the print head may represent one physical axis while the moving bed represents the other.

## Common pitfalls

- Decoding payload before recovering correct timing or bus mode.
- Assuming UART text is non-inverted or standard baud.
- Ignoring chip-select in SPI captures.
- Treating firmware compression as encryption without entropy and magic-byte evidence.
- Using RF replay before understanding framing and legal/lab boundaries.
- Reusing an earlier instance's exact packet bytes because the UI or service name looks the same.
- Judging packet validity only by HTTP status or a static page diff instead of the resulting device or session state.
- Forgetting that side-channel datasets may have axes in positions, guesses, traces, samples rather than traces, samples.
