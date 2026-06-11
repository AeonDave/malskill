# Sub-GHz and LoRaWAN Attacks

**Load when**: Targeting long-range IoT, smart city nodes, industrial telemetry, smart meters, garage doors, fixed-code remotes, TPMS systems, or when analyzing the 433 MHz, 868 MHz, and 915 MHz ISM bands.

## 1. Sub-GHz Reconnaissance & Hardware

Sub-GHz operations operate below 1 GHz and bounce better around obstacles. Most standard radios (802.11, BT) cannot receive these frequencies.

- **RTL-SDR**: Cheap, RX only (receive). Good for waterfall analysis and checking if custom hardware is transmitting.
- **HackRF One**: RX/TX transceiver (1 MHz to 6 GHz). Ideal for capture and replay.
- **Flipper Zero**: Built-in sub-GHz RX/TX with parsers for standard fixed-code protocols.
- **LimeSDR / BladeRF**: Higher sampling rate needed for wide-band LoRa.

## 2. Proprietary Sub-GHz Protocols (OOK / FSK)

Older tech, like fixed-code garage doors, wireless doorbells, and cheap weather stations rely on simple OOK (On-Off Keying) or 2-FSK modulation.

1. **Capture**: Record raw IQ data when the device transmits.
   ```bash
   hackrf_transfer -r capture.iq -f 433920000 -s 2000000 -n 60000000
   ```
2. **Analysis**: Load `capture.iq` into **Inspectrum** or **Universal Radio Hacker (URH)**.
   - Demodulate the signal visually.
   - Extract the binary sequence (e.g., `10101111`).
3. **Replay**: Transmit the exact recorded waveform back to trigger the action.
   ```bash
   hackrf_transfer -t capture.iq -f 433920000 -s 2000000 -x 47
   ```
   *Quality Check*: Replays fail if the system uses rolling codes (like modern KeeLoq). In rolling code systems, replaying an old packet is rejected by the receiver.

## 3. LoRaWAN Exploitation

LoRaWAN adds a MAC layer over the LoRa physical layer (Chirp Spread Spectrum). It is the backbone of helium networks and smart-cities.

Devices provision to a network via two methods:
- **OTAA (Over-the-Air Activation)**: Derives dynamic session keys at join.
- **ABP (Activation By Personalization)**: Hardcodes the `AppSKey` and `NwkSKey` locally on the device.

If you suspect ABP and have physical access to a node:
1. Extract firmware (via `jtag-swd` or `spi-flash`).
2. Run `strings` or binwalk to find 16-byte hex keys (`AppSKey` and `NwkSKey`) and the `DevAddr`.
3. You can now spoof the node, polluting the industrial telemetry feed.

## 4. Key Reuse and Frame Counter Replay

If `AppSKey` is recovered:
- Packets can be decrypted and modified. 
- You can inject forged downlinks (commands sent to the device, like "shut down valve").

If the device disables Frame Counter (`FCnt`) checks (a common "quick fix" for sync problems in LoRa deployments):
- Old valid uplink packets can be captured via HackRF and replayed indefinitely to the gateway without knowing the keys, bypassing crypto entirely.
