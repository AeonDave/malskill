# Ground Systems, CubeSat CSP, RF and Orbits

Load for SDR/IQ inputs, CubeSat links, orbital-mechanics tasks, or ground-segment software as a target.

## Contents

- SDR reception and gr-satellites
- ZMQ "SDR modem" endpoints
- Link layers: AX.25 / KISS
- CubeSat Space Protocol (CSP)
- TLE / SGP4 orbital mechanics
- Ground-segment software as attack surface
- Weather-image downlinks (APT / SSTV)
- GNSS spoofing (GPS L1 / Galileo E1)
- Hack-A-Sat winning patterns

## SDR reception and gr-satellites

When the artifact is an IQ recording, WAV, or a live SDR task rather than a framed byte stream:

- **Chain:** SDR front-end (RTL-SDR, HackRF, USRP) → coarse filter/resample → demodulate (FSK/GMSK/BPSK/AFSK) → clock recovery → deframe → FEC decode → telemetry/frames.
- **`gr-satellites`** (GNU Radio OOT, `daniestevez/gr-satellites`) decodes most amateur satellites out of the box: AX.25, GOMspace NanoCom **U482C / AX100** modems, a large part of the CCSDS stack, and AO-40 (FUNcube). Run `gr_satellites <SATNAME> --wavfile capture.wav` (or from a conventional flowgraph) to emit hex frames, decoded telemetry values, or reassembled files/images.
- **SatNOGS** provides recorded observations (audio/IQ + waterfall) for thousands of passes — a supplied `.ogg`/`.wav` from SatNOGS is a common challenge input; feed it to `gr-satellites`.
- Support tools: `inspectrum` (visualize bursts, measure symbol rate), Universal Radio Hacker (interactive demod/deframe), `rtl_433` (ISM), GNU Radio Companion for custom flowgraphs.
- Identify before decoding: sample format/rate, center frequency, modulation, symbol rate, framing, whitening/randomizer, and FEC. A wrong symbol rate or inverted bit sense is the usual reason a "correct" decoder outputs garbage.
- **Check the bit budget before assuming a link layer:** `duration x baud` = total bits. A 0.2 s AFSK1200 clip is 240 bits — far too few for an AX.25 preamble, flags, addresses and FCS. When the budget is that tight the bits *are* the message: take mark/space straight to bits and try plain ASCII (MSB-first, then LSB-first) before any NRZI decode, bit de-stuffing, or `0x7E` flag search. Hunting for CRC-valid HDLC frames in such a clip returns nothing and misreads as "my demodulator is broken".

## ZMQ "SDR modem" endpoints

Some tasks expose the radio as a pair of ZeroMQ endpoints instead of a capture file or a TCP frame service ("an SDR modem is available through ZMQ endpoints"). Pin the interface down before investing in waveform design — guessing modulation against an interface you have not characterised burns hours.

- **Confirm it is ZMQ:** a raw TCP read returns the ZMTP greeting `ff 00 00 00 00 00 00 00 00 7f` followed by a version byte.
- **Identify each socket type by handshake, not by guessing.** ZMTP 3.x carries a `Socket-Type` property and the peer rejects incompatible pairings, so connect with each type in turn and watch the socket monitor for `EVENT_HANDSHAKE_SUCCEEDED` vs `EVENT_HANDSHAKE_FAILED_PROTOCOL`. Compatibility: PUB↔SUB/XSUB, PUSH↔PULL, REQ↔REP/ROUTER, DEALER↔ROUTER/REP/DEALER, PAIR↔PAIR. A peer that is PULL is the uplink (you PUSH); a peer that is PUSH is the downlink (you PULL).

```python
s = ctx.socket(zmq.PUSH); mon = s.get_monitor_socket(); s.connect(f"tcp://{h}:{p}")
ev = recv_monitor_message(mon)      # SUCCEEDED => peer is PULL => this is the uplink
# close the monitor socket before ctx.destroy(), or termination hangs
```

- **A bound socket is not a running consumer.** Before blaming your modulation, prove the far side actually reads: set a low `SNDHWM`, push fixed-size messages until `EAGAIN`, then keep pushing for ~30 s and measure steady-state throughput. Sending a few hundred messages proves nothing — ZMQ buffers `SNDHWM + peer RCVHWM` (default **1000**) messages with no reader at all, so an early "it accepted everything" reads as success when nothing is listening. Zero steady-state drain means no waveform will ever work.
- Steady-state drain rate also *characterises* the modem: bytes/s ÷ item size = sample rate, which resolves float32-vs-complex64 and the rate together.
- A downlink that stays silent while the uplink is genuinely draining means the sink emits only on a successful decode — treat it as a pass/fail decode oracle, not a stream you can characterise passively.
- **Stream vs message mode changes the payload entirely.** GNU Radio stream ZMQ blocks carry bare little-endian samples; the `*_msg_*` blocks carry **PMT-serialized** PDUs (`pmt::serialize_str`), where a PDU is `cons(metadata, u8vector)`. Tags from `pmt_serial_tags.h`: `PST_NULL 0x06`, `PST_PAIR 0x07`, `PST_UNIFORM_VECTOR 0x0a` (then a uniform-vector subtype byte, `0x00` = u8). Confirm the uniform-vector header field order (element count vs pad byte) against a real captured message before trusting a hand-rolled serializer — a malformed PDU is dropped silently and is indistinguishable from a bad waveform.

## Link layers: AX.25 / KISS

- **AX.25** — amateur packet-radio link layer used by many CubeSat beacons; frames carry source/destination callsigns, control, PID, then payload, with an FCS. Often AFSK1200 or GMSK9600.
- **KISS** — the TNC framing that wraps AX.25 for host transport: `0xC0` frame delimiters, a type/port command byte, and byte-stuffing (`0xDB 0xDC` for `0xC0`, `0xDB 0xDD` for `0xDB`). A `.kiss` capture decodes to AX.25 frames; strip KISS framing first.
- Soundmodem / `direwolf` turn audio into KISS frames when a task hands you raw beacon audio.

## CubeSat Space Protocol (CSP)

Lightweight network+transport protocol (`libcsp`, Aalborg University), common on GOMspace hardware; runs over CAN, I2C, KISS/AX.25, UART, or RF.

- **CSP v1 — 32-bit header:** Priority(2) | Source(5) | Destination(5) | Destination Port(6) | Source Port(6) | flags(4) = HMAC, XTEA, RDP, CRC. Then 0–65535 data bytes.
- **CSP v2 — 48-bit header:** Priority(2) | Destination(14) | Source(14) | Destination Port(6) | Source Port(6) | flags. Wider addresses for larger networks.
- **Ports:** 0–7 = general services (ping, buffer status, ident, uptime, reboot) handled by the CSP service handler; 8–47 = subsystem services; 48–63 = ephemeral.
- **Flags:** check the low bits before assuming plaintext — HMAC (authenticated), XTEA (encrypted), RDP (reliable, adds a header *after* the data), CRC-32 (trailing checksum).
- **Over CAN:** CFP fragments a CSP packet across 29-bit extended CAN IDs built from source/destination/type — reassemble before parsing. A ground↔space bridge often encapsulates CSP TM/TC inside CCSDS/ECSS transfer frames, so a CSP packet may sit *inside* a CCSDS frame.
- Inspect with `libcsp` utils and the Wireshark CSP dissector; ping/ident on port 0–1 is the fastest liveness/enumeration check.

## TLE / SGP4 orbital mechanics

For pass-prediction, pointing, and position challenges (Hack-A-Sat "AAAA" and ground-segment categories):

- A **TLE** (two-line element set) plus **SGP4** propagation gives a satellite's position/velocity at any epoch. Use `sgp4`, `skyfield`, or `pyorbital` in Python; `gpredict` interactively.
- Typical asks: compute position at a stated UTC in **ECEF** (X,Y,Z) or geodetic (lat/lon/alt); compute **azimuth/elevation** from a ground-station lat/lon/alt at a time; find which satellite an antenna pointed at; drive antenna PWM/servo duty cycles from az/el over a pass.
- Watch coordinate frames (TEME → ECEF/ITRF → geodetic), time systems (UTC vs. GMST), and units (degrees vs. radians). Match the exact frame the challenge asks for.

Pass-window and pointing answers are graded against the server's own sample instants, so match its clock, not just its physics:

- **"Next" window means the next pass that *starts* after now.** If the satellite is already above the mask angle when you connect, skip that pass entirely and use the following one.
- Bracket the rising edge on a coarse grid (10 s over a 24–48 h horizon), then **bisect to the exact crossing**. A coarse-only search silently misses short grazing passes.
- **Sample-grid phase is the classic silent failure.** These services mint the TLE at connect time, so the TLE epoch carries the server's sub-second phase and its 1 s output grid is `epoch + n` seconds — *not* whole UTC seconds. Sampling on whole seconds sits up to 1 s off: harmless on a slow pass, fatal on a fast-azimuth one. Anchor with `n = ceil((crossing - sat.epoch.utc_datetime()).total_seconds())`.
- **A numeric deviation in the reject message is a solvable oracle.** Divide each reported deviation by that quantity's local per-second rate; if elevation and azimuth both imply the same time offset, the bug is timing, not the orbital model — a model error would not produce one consistent offset.
- Emit values exactly as the example formats them; `str(round(v, 4))` drops trailing zeros, which is usually what is shown.

```python
from sgp4.api import Satrec, jday
sat = Satrec.twoline2rv(line1, line2)
e, r, v = sat.sgp4(*jday(2020, 3, 26, 21, 52, 7))   # r = TEME position (km)
# convert TEME->ECEF with GMST, then ECEF->geodetic, or use skyfield for topocentric az/el
```

## Ground-segment software as attack surface

The ground segment is often the actual target, not the RF link:

- **Yamcs** — mission control (telemetry visualization, command DB); inspect the MDB for command/parameter definitions and weak auth. Path traversal + XSS were disclosed 2023–2025.
- **OpenC3 COSMOS** — command & control; Docker-deployable. **Unauth RCE (GHSA-w757-4qv9-mghp, 5.0.6–6.10.1)** via JSON-RPC `String#convert_to_value` → `eval()` on array-form params, evaluated **before `authorize()`** (returns 401 but Ruby already ran). Also: plugin RCE (`setup.py` on install), XSS in Script Runner / Command Sender, path traversal in APIs, credential leakage via env vars (defaults `openc3password` / `openc3service` / `scriptrunnerpassword`). Load `sdls-and-ground-cves.md` for the exploit shape.
- **NASA cFS (core Flight System)** — flight-software framework; apps talk over the software bus. **Aquila CVEs 2025**: CVE-2025-25373 (MM insecure permissions → **RCE**, CVSS 9.8), CVE-2025-25371 (OSAL path traversal), CVE-2025-25372 (MM segfault via TC), CVE-2025-25374 (app-launch DoS). CVE-2026-5475 buffer overflow in `CFE_SB_TransmitMsg` CCSDS header handler (cFS ≤ 7.0.0). **NOS3** bundles cFS + COSMOS + Yamcs as a full satellite simulator — a single container to practice the whole chain end-to-end.
- **Kubos** — CubeSat flight-software/mission framework; historic Hack-A-Sat challenges leaned on **over-the-space update flows** whose "authenticating checksum" was a trivial CRC or fixed-key XOR — reverse the client before assuming HMAC.
- Treat these like any web/service target: default creds, exposed admin panels, insecure command endpoints, and injection into telemetry/command paths. Pair with `web-ctf`/`network-technique` once you are past the space-protocol layer.

Full SDLS/SDLS-EP layout, CryptoLib CVEs, cFS CVE table, OpenC3 exploit shape, and kill-chain patterns: `sdls-and-ground-cves.md`.

## Weather-image downlinks (APT / SSTV)

- **NOAA APT** (137 MHz, NFM, RTL-SDR): each image line is 0.5 s (2 lines/s), two video channels A/B with sync tones and telemetry wedges. Decode a recorded WAV with `noaa-apt` or WXtoImg; the flag may hide in the image, the telemetry wedge, or false-color output.
- **SSTV** downlinks (e.g. ISS): decode audio with `qsstv`/RX-SSTV to recover the transmitted image.
- These are AM-envelope / audio-subcarrier tasks — demodulate to an image, then treat as a forensics/stego artifact.

## GNSS spoofing (GPS L1 / Galileo E1)

Relevant when a challenge asks you to force a receiver to report a specific position/time, or to compute the signal a target receiver would see. Do this only in a shielded lab or over a wired feed; **transmitting on L1 in open air is illegal** in most jurisdictions.

**Standard toolchain:**
- `gps-sdr-sim` (Osqzss) — offline: RINEX ephemeris + target lat/lon/alt/time → IQ `.bin` for HackRF / BladeRF / USRP. Fixed-scene, easy to reproduce.
- `bladeGPS` — real-time GPS signal generation on BladeRF; supports live coordinate updates.
- `GNSS-SDR` — open-source software-defined receiver; use to decode your own generated signal and to consume live ephemeris via UDP protobuf streams.
- `gpsd` + a real receiver — verify the victim actually locked to your fake.

**Fixed-scene flow:**

```bash
# 1. Generate 300 s of L1 C/A samples at 2.6 MHz for target 36.10, -115.24
gps-sdr-sim -e brdc.n -l 36.10,-115.24,10 -d 300 -o out.bin
# 2. Transmit over HackRF (L1 = 1575.42 MHz)
hackrf_transfer -t out.bin -f 1575420000 -s 2600000 -a 1 -x 0
```

**Key operational rules (from GPSPATRON / bladeRF field tests):**
- **Sample rate must match end-to-end.** `gps-sdr-sim` defaults to `-s 2600000`; `GNSS-SDR` config `SignalSource.sampling_frequency=4000000` — mismatch = channel loss-of-lock even though signal is technically present.
- **Spoofing alone rarely wins against a live receiver.** Real satellites already have correlator lock. Either: (a) jam L1 first (broadband CW near 1575.42), let the receiver drop lock, then broadcast the spoof — receiver reacquires on your signal; or (b) do a smooth **takeover** by matching amplitude/Doppler of the real signal (advanced).
- **Multi-band receivers** (RTK, dual-frequency automotive): spoofing only L1 usually fails because the receiver cross-checks with L2/L5. Attack multi-band or accept partial spoof.
- **Time-spoofing gives TOTP replay.** Push GPS-derived clock back a few minutes on a device that uses GPS as time source; TOTP tokens for the target window become reusable.
- **OSNMA (Galileo Open Service NMA)** authenticates the navigation message — basic bit-modification spoofing fails. **Meaconing** (record real signals, replay with delay) bypasses NMA at the signal level because the bits are unchanged; delay-and-replay attacks add symbol errors that OSNMA does catch, so precise timing hardware is required.

**Detection in a challenge target:**
- Sudden position jump / velocity discontinuity.
- SNR of visible satellites unusually uniform (real constellations have geometry-dependent variance).
- Ephemeris data age inconsistent with observed sat set.
- If the challenge hands you an IQ file and asks "where was the receiver told it was?" — feed it to `GNSS-SDR` with default L1 CA settings and read the PVT output.

## Hack-A-Sat winning patterns

Recognizable challenge shapes from HAS 2020–2023 that reappear in other space CTFs:

- **Track The Sat / Ground Segment (HAS 2020)** — recover **PWM control signals** from a captured cable IQ file → convert PWM duty cycles to **antenna azimuth/elevation** → propagate every TLE in a supplied catalog at the capture epoch → the satellite visible at *every* observation is the answer (e.g. `CANX-7`). Use `sgp4`/`skyfield` for propagation, intersect visible sets across multiple captures to narrow to one.
- **SpaceDB / Kubos (HAS 2020)** — mission-planning framework with ASCII UI; the "authenticating checksum" for `ADCS CFG_POS` looked like a signature but was a fixed algorithm derivable from the client source. **Always reverse the client checksum before brute-forcing.**
- **'403 Denied' (HAS 2022 Finals)** — webserver bug in the ground-station platform → scrape a DB shared across 27 ground stations → **radio config leaks every 30 s** → send commands to another team's satellite. Pattern: compromise the *ground* to attack the *space*.
- **ADCS attack (HAS 2022 Finals)** — ADCS did not validate that control constants keep the system stable; feed unstable gains → wheels saturate. Recovery: set ADCS to `uncontrolled` first (stops positive control), then re-enable safe mode to despin.
- **RF RE (HAS 2023)** — IQ file, unknown modulation. Chain: `inspectrum` to eyeball bursts and symbol rate → GNU Radio Companion for demod (FSK/GMSK/QPSK) → `gr-satellites` if it matches a known amateur sat → hand-deframe otherwise. Typical failure: wrong bit sense (invert the whole stream) or wrong endianness on framing.
- **L4 station-keeping (HAS Finals late years)** — three-body perturbations mean L4 is not a fixed point; small periodic corrections keep you close. Solve with numerical propagation, not analytical.
- **Single Event Upset (SEU)** — challenges inject bit-flips into telemetry / control state. Recovery = safe mode, then reconcile. Recognize by intermittent "impossible" telemetry values with correct checksums.

See `sdls-and-ground-cves.md` for the ground-segment CVE catalog these patterns often chain through.
