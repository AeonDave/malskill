# RF and SDR Decoding Workflow

Load when the task involves IQ samples, SDR captures, burst protocols, BLE traffic, or unknown radio framing.

## Core loop

1. Lock capture assumptions: sample format, sample rate, center frequency, bandwidth.
2. Visualize first: waterfall, spectrum, burst timing, and repeated structures.
3. Recover physical-layer properties before parsing payloads.
4. Validate the decode on multiple frames, not one lucky packet.

## Minimal SDR workflow

1. Identify file type: `.cfile`, `.cu8`, IQ WAV, GNU Radio output, or tool-specific export.
2. Open the capture in a visualization tool.
3. Estimate:
   - center frequency offset
   - occupied bandwidth
   - burst timing
   - symbol or bit rate
   - likely modulation
4. Apply frequency shift and filtering before demodulation.
5. Recover framing: preamble, sync word, whitening, checksums, counters, or CRC.
6. Only then interpret payload semantics.

Useful tool roles:

- URH: quick protocol inference, packet slicing, replay simulation, bit-level edits
- Inspectrum: symbol timing, pulse width, preamble alignment, burst inspection
- GNU Radio: custom demodulation or repeated decode pipelines
- Wireshark/PCAP bridge: validate higher-layer payloads after radio decode

## Validation signals

A decode is credible when at least one of these holds:

- repeated frames decode consistently
- checksums or CRCs verify
- counters or timestamps increment correctly
- decoded bytes match a known higher-layer structure
- side-channel oracle confirms the decoded command changed device state

## BLE-specific workflow

Use this when the capture is BLE or BLE-like.

### First principles

- advertisement channels: `37`, `38`, `39`
- data channels: `0`–`36`
- a valid connection depends on the `CONNECT_IND` fields: access address, interval, channel map, hopping parameters

### If the connection setup was captured

1. Extract access address and connection interval.
2. Extract channel map and channel-selection parameters.
3. Use those values to follow connection events and decode data PDUs.

### If the connection setup was missed

1. Capture any data packet and extract the access address.
2. Recover the connection interval from anchor timing.
3. Treat the hidden event counter as unknown state.
4. Eliminate impossible counter values using observed channel/time pairs.
5. Once the counter is stable, track channel hopping deterministically.

### Practical failure sources

- near/far power imbalance between the two endpoints
- channel-switch latency that is slower than the hop schedule
- trying to decode too few channels at once
- demodulating before symbol-center alignment is correct

### BLE validation cues

- preamble correlation gives stable symbol centers
- access address repeats correctly across packets
- channel sequence stays consistent with later bursts
- resulting packets open cleanly in a BLE-aware parser or PCAP consumer

## Generic RF pitfalls

- parsing bytes before locking modulation and timing
- confusing sample rate with symbol rate
- ignoring inversion, whitening, or byte/bit order
- trusting one frame without checking repetition
- assuming the same deployment uses the same packet bytes on a later capture
- replaying or transmitting before the decode is stable and the lab scope allows it
