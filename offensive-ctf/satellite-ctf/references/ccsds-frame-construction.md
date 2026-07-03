# CCSDS Frame Construction

Byte-level layouts and a reusable Python harness for building and decoding CCSDS units. Load when a task requires constructing a valid uplink frame or decoding a raw downlink stream.

## Contents

- Space Packet (133.0-B)
- TC Transfer Frame (232.0-B) + Frame Error Control Field
- TM Transfer Frame (132.0-B) + OCF
- AOS Transfer Frame (732.0-B)
- USLP Transfer Frame (732.1-B)
- CLTU / BCH / randomizer (uplink coding, 231.0-B)
- ASM / Reed-Solomon / pseudo-randomizer (downlink coding, 131.0-B)
- CRC-16-CCITT routine
- Python build/parse harness
- SDLS placement (bytes overview)

## Space Packet (CCSDS 133.0-B)

6-octet primary header, big-endian, followed by the packet data field.

| Field | Bits | Notes |
|---|---|---|
| Packet Version Number | 3 | `000` |
| Packet Type | 1 | `1` = TC (uplink command), `0` = TM (downlink report) |
| Secondary Header Flag | 1 | `1` if a secondary header (e.g. PUS) is present |
| APID | 11 | Application Process ID — from the brief |
| Sequence Flags | 2 | `11` = unsegmented (standalone packet) |
| Packet Sequence Count | 14 | per-APID counter, wraps at 16383 |
| Packet Data Length | 16 | **(octets in data field) − 1** |

Word layout: `w1 = (ver<<13)|(type<<12)|(sechdr<<11)|apid`, `w2 = (seqflags<<14)|seqcount`, `w3 = len(payload)-1`. Header = `struct.pack(">HHH", w1, w2, w3)`.

A PUS packet is a space packet with `sechdr=1` and a PUS secondary header at the start of the data field (see `cop1-and-pus.md`).

### Reserved APIDs (SANA, `CCSDS 135.0-B` Space Link Identifiers)

Do not use these for your own traffic — many onboard parsers hard-drop or hard-route on them, giving false negatives on the oracle:

| APID (decimal) | Meaning |
|---|---|
| 2040–2044 | Reserved for future CCSDS use |
| 2045 | CFDP (CCSDS File Delivery Protocol) |
| 2046 | ISO 8473 |
| **2047** (`0x7FF`) | **Idle Packet** — all-ones APID; parsers drop these silently. If your "valid" packet is silently dropped, check you did not roll to 2047 via a mask error. |

APIDs 0–2046 are otherwise mission-managed; the brief's value overrides any placeholder.

## TC Transfer Frame (CCSDS 232.0-B)

5-octet primary header, optional 1-octet segment header, data field, optional 2-octet FECF.

| Field | Bits | Notes |
|---|---|---|
| Transfer Frame Version Number | 2 | `00` |
| Bypass Flag | 1 | `0` = AD (FARM-checked), `1` = BD/BC |
| Control Command Flag | 1 | `0` = data (AD/BD), `1` = control (BC) |
| Reserved Spare | 2 | `00` |
| Spacecraft ID | 10 | from the brief |
| Virtual Channel ID | 6 | from the brief |
| Frame Length | 10 | **(total octets in frame) − 1**, includes FECF |
| Frame Sequence Number N(S) | 8 | FARM sequence number for AD frames |

Type from the two flags: `00`=AD (Sequence-Controlled), `10`=BD (Expedited), `11`=BC (Control — Unlock / Set V(R)); `01` reserved.

Word layout: `w1 = (0<<14)|(bypass<<13)|(ctrl<<12)|(0<<10)|scid`, `w2 = (vcid<<10)|(total_len-1)`, then `struct.pack(">HHB", w1, w2, n_s)`.

**Segment header (optional):** if segmentation is configured, one octet between primary header and data — sequence flags(2) + MAP ID(6). Most CTF services omit it; add only if the validator complains about the data offset.

### Frame Error Control Field (FECF, section 4.1.4)

Optional 2 octets immediately after the data field: **CRC-16-CCITT, poly `0x1021`, init `0xFFFF`, no final XOR**, computed over the primary header + data field (everything before the FECF). Present or absent per mission config — if the brief says "with CRC", it is present and mandatory.

## TM Transfer Frame (CCSDS 132.0-B)

6-octet primary header, data field, optional Operational Control Field (OCF), optional FECF.

Primary header:

| Field | Bits |
|---|---|
| Transfer Frame Version Number | 2 |
| Spacecraft ID | 10 |
| Virtual Channel ID | 3 |
| OCF Flag | 1 |
| Master Channel Frame Count | 8 |
| Virtual Channel Frame Count | 8 |
| Transfer Frame Data Field Status | 16 |

Data Field Status packs: sec-hdr flag(1), sync flag(1), packet-order flag(1), segment-length ID(2), **First Header Pointer(11)** — offset of the first space-packet header inside the data field (`0x7FF` = no packet starts here / idle).

If OCF Flag = 1, the 4-octet OCF trailer is the **CLCW** (see `cop1-and-pus.md`). If FECF present, final 2 octets are CRC-16-CCITT as above.

To parse a downlink: read header → follow First Header Pointer to the first space packet → parse space-packet header → extract payload / PUS report.

## AOS Transfer Frame (CCSDS 732.0-B)

High-rate alternative to TM. Primary header: Master Channel ID = TFVN(2)+SCID(8)+VCID(6), then Virtual Channel Frame Count(24), Signaling Field(8). Optional insert zone, then M_PDU/B_PDU/VCA data. M_PDU has a First Header Pointer like TM. Recognize AOS when VCID is 6 bits and frame counts are 24-bit.

## USLP Transfer Frame (CCSDS 732.1-B)

Unified Space Data Link Protocol — the modern replacement covering TC/TM/AOS with a **variable-length frame** and 4-bit TFVN=`1100`. Primary header carries an extended SCID (16-bit) and VCID (6-bit) with sequence controls similar to TC/TM. Recognize USLP by TFVN=`1100` and by variable frame length (a `Frame Length` field in bytes rather than a fixed-per-VC size). SDLS layers on top the same way it does on TC/TM — the SPI/IV/MAC sit in the data field.

## Uplink coding: CLTU / BCH / randomizer (CCSDS 231.0-B)

Only relevant when the physical/RF layer is in scope (rare for TCP "modem" services).

- **CLTU** = Start Sequence + Encoded Data + Tail Sequence.
- **BCH:** Start Sequence `0xEB90` (16 bits). Encoded data is a run of **8-octet BCH codeblocks**: 7 octets of frame data (56 info bits) + 7 parity bits + 1 fill bit per codeblock. Pad the final block with fill (`0x55`/`0xAA` per mission) to a whole codeblock.
- **Tail Sequence** (BCH): 64-bit non-correctable pattern `C5 C5 C5 C5 C5 C5 C5 79`.
- **Randomizer:** optional with BCH (mandatory with LDPC). 8-bit LFSR, polynomial `h(x)=x^8+x^7+x^5+x^3+1`, seed all-ones (`0xFF`); XOR the frame octets before BCH encoding.
- LDPC variant uses a 64-bit start sequence and 128/512-bit codewords, randomized after encoding.
- **PLOP-1 vs PLOP-2** (Physical Layer Operation Procedure): PLOP-1 has a per-CLTU acquisition sequence and idle sequence; PLOP-2 uses a continuous carrier with a single acquisition and back-to-back CLTUs. The brief will name one; if a lab hands you "raw bits after the acquisition sequence", it is PLOP-2 in a byte-stream harness.
- **Modulation below CLTU** (RF only): `PCM/PSK/PM` (residual-carrier) is the classic TC waveform with a data subcarrier; `SP-L` (Split-Phase Level, biphase-L / Manchester) is the newer suppressed-carrier form used at higher rates.

## Downlink coding: ASM / Reed-Solomon / randomizer (CCSDS 131.0-B)

- **Attached Sync Marker (ASM):** 32-bit `0x1ACFFC1D` prefixed to every transmitted codeblock/frame. Frame sync = search for this pattern; strip it before decoding.
- **Reed-Solomon (255,223):** E=16 (32 check symbols), interleaving depth I ∈ {1,2,3,4,5,8}. Codeblock length = 255·I octets carrying 223·I of frame. Check symbols are the trailing 32·I octets.
- **Pseudo-randomizer:** same 8-bit polynomial/seed family; applied to the frame/codeblock after ASM, synchronized by the ASM. De-randomize by XOR after frame sync, before RS decode.
- Convolutional (r=1/2, k=7) and Turbo/LDPC codes may sit under RS; a supplied capture is usually already demodulated to bits/frames.
- **Inverted ASM `0xE5300FE2`** signals **NRZ-M/NRZ-S bit-sense inversion** on the line. If your `0x1ACFFC1D` search finds nothing but the inverted pattern hits, XOR the whole stream with `0xFF` before framing.
- **Coding stack order** on a downlink is typically: Reed-Solomon → pseudo-randomizer → convolutional / Turbo / LDPC → ASM prepended → modulation. Undo in reverse.

## CRC-16-CCITT routine

```python
def crc16_ccitt(data, crc=0xFFFF):
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if (crc & 0x8000) else (crc << 1) & 0xFFFF
    return crc
```

This is the FECF for TC frames and the packet CRC for PUS (`crcmod` name `crc-ccitt-false`). No reflection, no final XOR.

## Python build/parse harness

Reusable builder for the common CTF case: a raw TCP service that accepts one AD-type TC frame carrying one space packet, and replies with a framed/plain response. Adjust `ptype`, counters, and payload to the brief.

```python
import socket, struct, re

def crc16_ccitt(data, crc=0xFFFF):
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if (crc & 0x8000) else (crc << 1) & 0xFFFF
    return crc

def space_packet(apid, seq, payload, ptype=1, sec_hdr=0):
    w1 = (ptype << 12) | (sec_hdr << 11) | (apid & 0x7FF)   # ver=0
    w2 = (0b11 << 14) | (seq & 0x3FFF)                      # unsegmented
    w3 = (len(payload) - 1) & 0xFFFF
    return struct.pack(">HHH", w1, w2, w3) + payload

def tc_frame(scid, vcid, n_s, payload, bypass=0, ctrl=0, fecf=True):
    total = 5 + len(payload) + (2 if fecf else 0)
    w1 = (bypass << 13) | (ctrl << 12) | (scid & 0x3FF)     # tfvn=0, spare=0
    w2 = ((vcid & 0x3F) << 10) | ((total - 1) & 0x3FF)
    body = struct.pack(">HHB", w1, w2, n_s & 0xFF) + payload
    return body + struct.pack(">H", crc16_ccitt(body)) if fecf else body

def bc_set_vr(scid, vcid, vr):                              # unlock FARM lockout
    return tc_frame(scid, vcid, 0, b"\x82\x00" + bytes([vr]), bypass=1, ctrl=1)

def send_and_recv(host, port, frame, expect_banner=None, timeout=8):
    s = socket.socket(); s.settimeout(timeout); s.connect((host, port))
    if expect_banner:                # some services greet, others wait for the frame
        try: print("banner:", s.recv(1024).decode(errors="replace").strip())
        except socket.timeout: pass
    s.send(frame)
    resp = s.recv(8192); s.close()
    return resp

# Example: single HEALTHCHECK-style command
# f = tc_frame(scid=12, vcid=3, n_s=0, payload=space_packet(apid=42, seq=0, payload=b"HEALTHCHECK"))
# r = send_and_recv("target", 31337, f)
# print(r); m = re.search(rb"HTB\{[^}]+\}", r); print(m and m.group())
```

For a stateful, counter-driven service: send the first frame, parse the reply for the next expected counter (the server echoes it, e.g. `0x01:ACK`), then send the next command with the frame sequence number, packet sequence count, and application counter all advanced to match — reconnect and re-sync if a field is ambiguous and you need to brute a small matrix.

## SDLS placement (bytes overview)

When the challenge notes SDLS / SPI / MAC / OTAR, the frame layout becomes:

```
[ Frame Primary Header ]           <- plaintext (SCID / VCID / N(S) / FECF visible)
[ SDLS Security Header ]           <- SPI(16) + IV + ARSN + PadLen
[ (encrypted) Data Field ]         <- space packets / PUS commands
[ SDLS Security Trailer ]          <- MAC (CMAC or GCM tag)
[ Optional FECF (2) ]              <- CRC-16-CCITT over header+trailer (still applied)
```

Baseline crypto (CCSDS 352.0-B-2): **AES-256 GCM**, 96-bit IV, 128-bit MAC. Load `sdls-and-ground-cves.md` for SA/OTAR/ARSN semantics, the CryptoLib CVEs, and the parts of a frame SDLS deliberately does **not** protect (BC directives, CLCW).
