---
name: satellite-ctf
description: "Lab/CTF: satellite and space-system challenges; CCSDS Space Packets, TC/TM/AOS/USLP Space Data Link transfer frames, CLTU/BCH/Reed-Solomon coding, COP-1/FARM sequence control, ECSS PUS services, SDLS/SDLS-EP link-layer crypto and CryptoLib CVEs, CubeSat Space Protocol (CSP), TLE/SGP4 orbits, GPS L1 GNSS spoofing with gps-sdr-sim/HackRF, and ground-segment targets (Yamcs, OpenC3 COSMOS, NASA cFS, NOS3, Kubos) including known 2025–2026 RCE/path-traversal/DoS CVEs. Use when a task mentions spacecraft ID, APID, virtual channel, telecommand/telemetry, transfer frame, ground station, modem, ASM 1ACFFC1D, SPI/OTAR/ARSN, or a downlink/uplink byte stream to build or decode."
license: MIT
compatibility: "AgentSkills-compatible agents; local artifacts; authorized isolated lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# Satellite CTF

Solve satellite and space-ground-link challenges by pinning the exact CCSDS/ECSS layer in play, then building or decoding one spec-compliant unit at a time and using the target's replies as the oracle.

## When this skill applies

- Wording: spacecraft/satellite, ground station, uplink/downlink, telecommand (TC), telemetry (TM), transfer frame, space packet, modem, mission control, onboard software, bus/payload.
- Identifiers: APID, VCID (virtual channel), SCID (spacecraft ID), MAP ID, packet sequence count, frame sequence number N(S), service/subservice `TC[x,y]`/`TM[x,y]`.
- Protocol cues: CCSDS, ECSS, PUS, CLTU, BCH, Reed-Solomon, Attached Sync Marker `0x1ACFFC1D`, pseudo-randomizer, COP-1, FARM/FOP, CLCW, AD/BD/BC frames, CubeSat Space Protocol (CSP), AX.25, KISS, AOS, USLP.
- Security cues (SDLS): **SPI**, IV, ARSN, MAC/tag, OTAR, Security Association (SA), Key Management Service (KMS), Extended Procedures (SDLS-EP), CryptoLib, GCM/CMAC, `clear-mode` VC.
- Ground-system cues: Yamcs, OpenC3 COSMOS, NASA cFS / cFE, NOS3, Kubos, Mission Database (MDB), JSON-RPC command API.
- Artifacts: a raw TCP "modem" service, an IQ/WAV/SDR recording, a hex frame dump, a PCAP of a link, a skeleton `client.py` with frame-builder stubs, a TLE set, a ground-system container image, or an RSA/AES key with an SPI number.

## Operating model

1. Identify the layer stack top-down and bottom-up: physical/coding (CLTU, ASM, RS, randomizer) → data link (TC/TM/AOS transfer frame) → network (space packet, CSP) → application (PUS service, custom command grammar). Most CTF services drop the RF/coding layers and hand you a raw framed byte stream over TCP.
2. Read the brief as a spec sheet. SCID, APID, VCID, and the exact payload string (e.g. `HEALTHCHECK`, `<counter>:BEGIN`) are usually stated verbatim — use them exactly, not the example values in any skeleton code.
3. Build the smallest valid unit first and send it. Probe for a banner: some services greet (`SPACECRAFT LINK ESTABLISHED`), others expect the frame first and only then reply — send-then-recv, do not block on a banner.
4. Treat every server reply as an oracle. Layered validators emit precise errors (`Expected TC frame with VCFC 1 but got 0`, `Expected SpacePacket with sequence count 1`, `invalid payload or sequence state`). Each names the next field to fix; walk the error chain instead of guessing.
5. When one field is genuinely ambiguous, brute the smallest matrix (counter × frame-seq × packet-seq × type bit), reconnecting/re-syncing per attempt, not a blind large space.
6. Prove the result with the flag from the reply. Extract with a regex, verify format, then submit.

## Protocol stack (fast map)

- **Space Packet (CCSDS 133.0-B):** 6-byte primary header — version(3) `000`, type(1) `1`=TC/`0`=TM, sec-hdr flag(1), APID(11) | seq-flags(2) `11`=unsegmented + seq-count(14) | data-length(16) = payload_len − 1. Payload follows. APID 2047 (`0x7FF`) = Idle Packet — dropped silently; 2045–2046 reserved (CFDP, ISO 8473).
- **TC transfer frame (CCSDS 232.0-B):** 5-byte header — TFVN(2) + bypass(1) + ctrl(1) + spare(2) + SCID(10) | VCID(6) + frame-length(10)=total−1 | frame-seq N(S)(8). Optional segment header, then data, then optional 2-byte FECF = **CRC-16-CCITT (poly 0x1021, init 0xFFFF)**. Frame type from bypass/ctrl: `00`=AD (sequence-controlled, FARM checks N(S)), `10`=BD (expedited), `11`=BC (control: Unlock / Set V(R)).
- **TM transfer frame (CCSDS 132.0-B):** 6-byte header (SCID/VCID/MC+VC frame counts/data-field-status), data field, optional OCF = **CLCW** (4 bytes, carries N(R)), optional 2-byte FECF.
- **USLP (CCSDS 732.1-B):** variable-length modern replacement for TC/TM/AOS; TFVN=`1100`; 16-bit SCID; SDLS applies the same way.
- **Coding layer (only when RF is in scope):** TC uplink wraps frames in a **CLTU** (start `0xEB90`, 8-byte BCH codeblocks, tail `C5C5C5C5C5C5C579`, optional randomizer). TM downlink prefixes each frame/codeblock with **ASM `0x1ACFFC1D`** (or inverted `0xE5300FE2` on NRZ-M/S bit-sense flip), optional **Reed-Solomon (255,223)** and pseudo-randomizer.
- **Link-layer security (CCSDS 355.0-B SDLS + 355.1-B SDLS-EP):** SDLS header (SPI, IV, ARSN) + encrypted data field + trailer (MAC) sit **inside** the transfer frame data field. Baseline crypto (CCSDS 352.0-B-2) = **AES-256 GCM** (96-bit IV, 128-bit MAC) or CMAC-only. SDLS deliberately does **not** protect BC directives or CLCW. `clear-mode` VC = header present, no crypto.
- **Application:** ECSS **PUS** service/subservice (`TC[17,1]` ping → `TM[17,2]`), or a mission-custom ASCII/binary command grammar.
- **CubeSat alt-stack:** **CSP** (32-bit v1 / 48-bit v2 header, ports 0–7 = ping/buffer), often over CAN/KISS/AX.25 on GOMspace hardware.

See [references/ccsds-frame-construction.md](references/ccsds-frame-construction.md) for exact bit layouts and a working Python builder; [references/cop1-and-pus.md](references/cop1-and-pus.md) for FARM/FOP sequence control and the PUS service catalog; [references/sdls-and-ground-cves.md](references/sdls-and-ground-cves.md) for SDLS/SDLS-EP grammar plus CryptoLib/cFS/OpenC3/Yamcs CVEs.

## Technique integration

Load these as decision engines when their domain appears:

- `technique-ctf` for the general challenge-solving loop, oracle-driven iteration, harness building, and parallelizing independent variants.
- `network-technique` and `pcap`-style analysis for link captures, service exposure, and stream reconstruction.
- `reversing-technique` for onboard-software binaries, custom modem servers, cFS/Kubos apps, and firmware.
- `wireless-technique` for IQ/SDR captures, demodulation, and physical-layer recovery before framing.
- `crypto-technique` when frames are authenticated/encrypted (SDLS, HMAC, XTEA on CSP) or a checksum must be forged.
- `python-patterns` for frame builders, parsers, and replay harnesses; `pwntools` for the socket loop.

## Tool routing

- **Frame build/parse (Python):** `spacepackets` (CCSDS Space Packet + ECSS PUS TC/TM, CRC-CCITT), `ccsdspy` (fixed/variable TM packet parsing), `construct`/`struct` for custom layouts, `crcmod` (`crc-ccitt-false`) for PUS/TC CRC, `pwntools` for the remote loop.
- **SDR / demod:** GNU Radio + `gr-satellites` (AX.25, GOMspace U482C/AX100, CCSDS, AO-40/FUNcube), SatNOGS, `inspectrum`, Universal Radio Hacker, `rtl_433`, `noaa-apt`/SSTV decoders for weather-image tasks.
- **Orbits:** `skyfield`, `sgp4`, `pyorbital`, `gpredict` for TLE propagation, pass prediction, azimuth/elevation and ECEF/geodetic conversion (Hack-A-Sat "AAAA"/ground-segment tasks).
- **Ground systems:** Yamcs, OpenC3 COSMOS, NASA cFS, NOS3, Kubos — for command/telemetry DB inspection, replay, and finding weak auth / plugin RCE in the ground segment itself.
- **Inspect:** Wireshark CCSDS/space dissectors, `xxd`/CyberChef for hand-decoding a hex frame, `libcsp` utils for CSP.

## Safety and scope gates

- CTF targets are isolated lab services — interact freely, but never transmit on real RF or licensed/amateur bands, and never command a real spacecraft.
- Prefer offline decode of a supplied capture over live interaction when the artifact already contains the answer.
- Keep a field ledger: layer hypothesis → evidence (server error / decoded bytes) → fix → next field. The layered errors are the map; do not brute blindly.
- State which fields are inferred vs. spec-stated; a wrong SCID/APID/VCID is silently dropped by a real validator, so confirm them against the brief first.

## Quick pivots

- **No banner ≠ dead:** if `recv()` times out on connect, the service is waiting for the frame — send first, then read.
- **Use stated params, not skeleton defaults:** a provided `client.py` often ships `apid=42, vcid=3` placeholders; the brief's real APID/VCID/SCID override them.
- **APID looks right but drops silently?** You may have rolled to a reserved value — 2045 (CFDP), 2046 (ISO 8473), or **2047 (Idle Packet, `0x7FF`)** — double-check your mask.
- **AD frame won't advance:** FARM requires `N(S) == V(R)`; V(R) starts at 0 and increments per accepted frame. The application may also carry its own counter in the payload — both must line up. Server errors reveal each expected value.
- **Stuck FARM / lockout:** recover with a **BC** frame — `Set V(R)` = `0x82 0x00 <VR>`, `Unlock` = `0x00` (bypass=1, ctrl=1).
- **CRC rejects the frame:** TC/PUS use CRC-16-CCITT (poly 0x1021, **init 0xFFFF**, no final XOR); confirm you hash the header+data with the FECF excluded.
- **PUS ack silent?** Toggle all four ack flags (acceptance/start/progress/completion) in the TC secondary header — each downlink report is an independent oracle for where the command was rejected.
- **Counter encoding is literal:** payloads like `0x00:BEGIN` may be the ASCII string `0x00`, not a raw byte — try both encodings when the app rejects a "valid" packet.
- **Downlink starts with 1ACFFC1D:** strip the 32-bit ASM, de-randomize, RS-decode, then parse the TM frame; flags often sit in the TM data field or a PUS `TM[x,y]` report. If the search misses, try the inverted ASM `0xE5300FE2` (NRZ-M/S bit-sense flip) and XOR the stream with `0xFF`.
- **Hex dump with no service:** identify by header — leading `1ACFFC1D` = TM/ASM; a 6-byte header with plausible APID = space packet; `EB90…C5C5` = CLTU.
- **CSP frame:** low ports (0–7) are ping/buffer/ident services; check HMAC/XTEA/RDP/CRC flag bits in the header before assuming plaintext.
- **Orbit challenge:** propagate the given TLE with SGP4 at the stated epoch, convert to the requested frame (ECEF/lat-lon/az-el), and match the expected observation.

### SDLS is on — what's still open

- **BC directives (Unlock / Set V(R)) and CLCW** are **not** covered by SDLS. Injecting BC frames or flipping CLCW bits (`Retransmit`, `Lockout`) disrupts commanding even against a fully secured link.
- **IV reuse** on a Security Association = **keystream oracle** (CryptoLib CVE-2025-46672). Capture multiple frames on the same VC/SA and inspect the Security Header IV — same IV twice = XOR-recover plaintext.
- **EP channel confusion** (CryptoLib CVE-2025-46675): CryptoLib matches EP PDUs by VCID **or** APID rather than the spec's reserved SPI 1 / SPI 65535. If a challenge notes this parser, forge an EP directive on the wrong-but-accepted channel → erase SAs → OTAR your own key → own the bird.
- **`clear-mode` VC** in a mission config = SDLS effectively off on that VC.
- Load `sdls-and-ground-cves.md` for full grammar and the OpenC3/cFS/Yamcs CVE catalog.

### Ground-segment fast paths

- **OpenC3 COSMOS** ver 5.0.6–6.10.1: **unauthenticated RCE** on `/openc3-api/api` — JSON-RPC `cmd` with array-form params executes Ruby before `authorize()`. Default creds: `openc3password`, `scriptrunnerpassword`, `openc3service`.
- **NASA cFS Aquila (2019)**: TC to Memory Management module = RCE (CVE-2025-25373, CVSS 9.8); OSAL path traversal (25371); MM segfault (25372); app-launch DoS (25374). Common lab wrapper: **NOS3** (cFS + COSMOS + Yamcs).
- **Yamcs**: enumerate the **Mission Database (MDB)** for command/parameter IDs before crafting a TC — the schema is the challenge.
- **Kubos over-the-space update**: the "auth checksum" is often a trivial CRC / fixed-key XOR; reverse the client instead of brute-forcing.

### GNSS spoofing (when a receiver, not a spacecraft, is the target)

- Toolchain: `gps-sdr-sim` (offline `.bin` from RINEX + target lat/lon/time) → `hackrf_transfer -f 1575420000 -s 2600000`.
- Spoof alone rarely wins vs. a live receiver — **jam L1 first** to force loss-of-lock, then broadcast the fake so the receiver reacquires on your signal.
- Sample rate must match end-to-end: `gps-sdr-sim` default 2.6 MHz vs `GNSS-SDR` default 4 MHz — one number off = channel loss.
- Multi-band (RTK, dual-freq) receivers cross-check L2/L5 — pure L1 spoof fails.
- Time-spoofing GPS → shift victim clock → TOTP replay window opens.
- Galileo **OSNMA** blocks bit-level modification spoof; **meaconing** (record-and-replay) bypasses NMA at signal level.

### Hack-A-Sat recurring shapes

- **Antenna pointing → satellite ID**: PWM from cable IQ → az/el → SGP4 across TLE catalog → intersection across captures = single sat name.
- **Ground bugs → space commanding**: web/DB vuln on the platform leaks other teams' radio config → inject TC on their VC.
- **ADCS control-constant sabotage**: no stability check on gain uploads → wheels saturate. Defence: set ADCS `uncontrolled` first, then re-enable safe mode.
- **RF RE**: unknown IQ → `inspectrum` (symbol rate) → GNU Radio demod → `gr-satellites` for known amateurs → hand-deframe otherwise. Failure modes: wrong bit sense (invert), wrong endianness (swap).
- **L4 / three-body**: analytical solutions don't work — numerical propagation with periodic corrections.

## Resources

- [references/ccsds-frame-construction.md](references/ccsds-frame-construction.md) — exact bit layouts for Space Packet, TC/TM/AOS/USLP transfer frames, CLTU (BCH start/tail/randomizer), TM ASM + Reed-Solomon + pseudo-randomizer, the CRC-16-CCITT routine, reserved APIDs, and a reusable Python build/parse harness. Load when constructing or decoding any frame at the byte level.
- [references/cop1-and-pus.md](references/cop1-and-pus.md) — COP-1 FARM-1/FOP-1 state and sequence logic, AD/BD/BC frame semantics, CLCW bit map, Unlock / Set V(R) directives and lockout recovery, the ECSS PUS service/subservice catalog with the TC/TM secondary-header format, and PUS ack-flag oracle usage. Load for sequence-controlled uplink or PUS application grammar.
- [references/sdls-and-ground-cves.md](references/sdls-and-ground-cves.md) — SDLS / SDLS-EP packet layout (SPI, IV, ARSN, MAC), AES-GCM/CMAC baseline, spec-level gaps (BC/CLCW/clear-mode), SDLS-EP directives (OTAR/KMS/SAMS/MCS), CryptoLib CVE-2025-46672 / -46675, NASA cFS Aquila CVE-2025-25371–25374 and CVE-2026-5475/-5476, OpenC3 COSMOS unauth RCE GHSA-w757-4qv9-mghp and the seven-CVE batch, Yamcs / Kubos notes, and kill-chain patterns. Load whenever the link is authenticated/encrypted, when SPI/OTAR/ARSN appear, or when a ground-system server (Yamcs, COSMOS, cFS) is the actual target.
- [references/ground-systems-and-rf.md](references/ground-systems-and-rf.md) — SDR reception and `gr-satellites` decode chains, AX.25/KISS, CubeSat CSP header (v1/v2, ports, libcsp, GOMspace modems), TLE/SGP4 orbital mechanics, ground-segment software as attack surface, weather-image downlinks (APT / SSTV), **GNSS spoofing with `gps-sdr-sim` + HackRF** (jam-then-spoof, sample-rate matching, multi-band caveats, OSNMA/meaconing), and **Hack-A-Sat winning patterns** (pointing-→-sat-ID, ground-→-space commanding, ADCS control-constant abuse, RF RE flow). Load for RF/IQ inputs, CubeSat links, orbit math, ground-system targets, or GNSS-receiver challenges.
