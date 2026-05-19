# Signal Decoding, Modus Operandi, and Change Analysis

How a PLC actually behaves over time, how to turn raw register/coil/tag bytes into engineering values, and how to design a write/test/verify loop that proves an effect without breaking the process.

## PLC modus operandi

Every PLC runs a deterministic loop, usually 1–50 ms:

1. **Input scan** — copy physical inputs into the input image (`%I`, `I:`, `DI`, IW).
2. **Program scan** — evaluate ladder/ST/FBD/IL/SFC top-to-bottom against the input image, updating the output image (`%Q`, `O:`, `DO`, QW) and internal memory (`%M`, `B3:`, `DB`, MW).
3. **Output scan** — copy the output image to physical outputs.
4. **Housekeeping** — communications, diagnostics, watchdog refresh.

Consequences for testing:

- Writes to the output image (`%Q`/coils) are overwritten next scan unless the ladder logic clears the input that drives them; flipping a coil with FC 5 may last one scan only.
- Writes to internal memory (`%M`/holding registers used as setpoints) usually persist across scans and are the real attack surface for setpoint manipulation.
- Retentive memory (`%MW`, retentive `DB`, `N7:` in retentive files) survives power cycle; non-retentive does not. PLC `STOP`→`RUN` reinitializes non-retentive only.
- Forces (`force on`/`force off`) override input/output image regardless of ladder; many CTFs gate the flag behind "no forces active".

Operating-mode states (vendor-neutral): `STOP`, `PROG`/`PROGRAM`, `RUN`, `REM RUN`, `REM PROG`, `FAULT`. Mode change is a high-signal event in PCAPs — search for it before chasing register writes.

## Memory area cheatsheet

| Vendor family | Bit | Byte | Word | Notes |
| --- | --- | --- | --- | --- |
| IEC 61131-3 | `%IX`, `%QX`, `%MX` | `%IB`, `%QB`, `%MB` | `%IW`, `%QW`, `%MW` | Standard, used by Codesys, OpenPLC, Beckhoff. |
| Rockwell (Logix 5000) | `BOOL` tag | `SINT` | `INT`/`DINT`/`REAL` | Tag-based, no addresses; user-defined types (UDT) common. |
| Rockwell (PLC-5/SLC) | `B3:0/0` | `N7:0` (16-bit) | `N7:0` | File-based, integer file `N7`, float `F8`, output `O:`, input `I:`. |
| Siemens (S7) | `M0.0`, `I0.0`, `Q0.0` | `MB0`, `IB0`, `QB0` | `MW0`, `IW0`, `QW0`, `MD0` | DB blocks `DB1.DBW0`, `DB1.DBD4` for word/dword. |
| Modicon | `0xxxxx` (coils), `1xxxxx` (DI) | — | `3xxxxx` (input reg), `4xxxxx` (holding reg) | Classic Modbus addressing; 4-digit reference = address+1. |
| Mitsubishi | `M0`, `X0`, `Y0` | — | `D0`, `R0` | `D` = data register, `R` = file register. |

## Modbus register-to-value decoding

Modbus carries 16-bit words. Anything wider is two or more words and you must guess endianness from physics or PCAP context.

### Integer types

| Type | Words | Range | Notes |
| --- | --- | --- | --- |
| `UINT16` | 1 | 0..65535 | Most common; pump speeds, counts. |
| `INT16` | 1 | −32768..32767 | Temperatures, signed offsets. |
| `UINT32` / `INT32` | 2 | 0..2³²−1 / signed | Big-endian word order is common but vendor-specific. |
| `UINT64` / `INT64` | 4 | wide | Energy totals, accumulated counters. |

### Float types

`REAL` (IEEE 754 single, 32-bit) is two registers. Four byte orders exist in the wild:

```
AB CD   big-endian, big-endian word        "ABCD"   (most schneider, default)
CD AB   little-endian, big-endian word     "CDAB"   (most rockwell, common siemens)
BA DC   big-endian, little-endian word     "BADC"   (rare)
DC BA   little-endian, little-endian word  "DCBA"   (some legacy)
```

Decode helper (Python):

```python
import struct

def regs_to_float(regs, order="ABCD"):
    # regs: list of two 16-bit ints from Modbus
    hi, lo = regs[0], regs[1]
    b = bytes([hi >> 8, hi & 0xFF, lo >> 8, lo & 0xFF])    # ABCD
    if order == "CDAB": b = bytes([lo >> 8, lo & 0xFF, hi >> 8, hi & 0xFF])
    if order == "BADC": b = bytes([b[1], b[0], b[3], b[2]])
    if order == "DCBA": b = b[::-1]
    return struct.unpack(">f", b)[0]
```

Algorithmic byte-order detection: pick a register pair likely to encode a temperature, pressure, or level in a known range; try all four orders; the one yielding a plausible value (e.g. 20–40 °C, 0–10 bar, 0–100 %) is the answer. Confirm against a second pair.

### String, BCD, packed

- `STRING` in Modbus is usually ASCII packed two-per-register, sometimes length-prefixed in register 0.
- `BCD` packs two decimal digits per byte (`0x1234` = "1234"); common on legacy drives and HMIs.
- Status/alarm words pack 16 flags into one register; bit 0 = LSB; map each bit to a named alarm before claiming meaning.

### Scaling

Raw register rarely equals engineering value. Common pattern:

```
EU = raw * scale + offset
```

Scale and offset come from the HMI tag database, the PLC `SCP`/`NORM_X`+`SCALE_X` instruction, or the device manual. Two-point calibration from PCAP:

```
scale  = (EU_hi - EU_lo) / (raw_hi - raw_lo)
offset = EU_lo - scale * raw_lo
```

Pick two known operator-readable values from an HMI screenshot or alarm log and solve.

### Time encoding

Watch out for:

- 32-bit Unix epoch in two registers.
- Vendor 6-byte BCD timestamps `YY MM DD HH MM SS`.
- Siemens `DATE_AND_TIME` (8 bytes BCD + ms).
- DNP3 absolute time (6 bytes, ms since 1970-01-01).
- Modbus FC 43 sub-function 14 carries device identification strings (vendor, product code, revision).

## CIP / EtherNet/IP decoding cues

- Tag names are visible in plaintext inside `cip_class 0x6B`/`0x6C` requests (Symbol Object) and `cip_data` reads.
- Common class codes worth grepping in PCAP: `0x01` Identity, `0x02` Message Router, `0x06` Connection Manager, `0x67` PCCC, `0x6B` Symbol, `0x6C` Template, `0xAC`/`0xAD` vendor-specific.
- `0xA1` (forward open) and `0xA2` (forward close) bracket I/O sessions; large `0xA1` payloads carry the connection path with PLC slot.
- `Service 0x52` (read tag fragmented) and `0x53` (write tag fragmented) handle arrays larger than one packet.

## S7comm decoding cues

- Setup communication (ROSCTR 0x01, function 0xF0) advertises PDU size — useful baseline.
- Userdata blocks (ROSCTR 0x07) carry SZL (System State List) queries: `0x0011` order code, `0x001C` CPU details, `0x0017` LEDs.
- Read/Write Var (function 0x04/0x05) carries area code: `0x83` DB, `0x84` instance DB, `0x81` input, `0x82` output, `0x83` flag, `0x1D` SFB.
- Block download/upload (functions 0x1A/0x1B/0x1C, 0x1D/0x1E/0x1F) means the engineering workstation pushed logic — high-signal event.

## DNP3 decoding cues

- Function codes: `0x01` Read, `0x02` Write, `0x03` Select, `0x04` Operate, `0x05` Direct Operate, `0x12` Cold Restart, `0x0D` Confirm.
- Object groups: `g1` binary input, `g10` binary output, `g12` CROB (control relay output block — actual command), `g30` analog input, `g40` analog output, `g41` analog output block.
- `g12v1` write with `op_type=3` (latch-on) followed by `op_type=4` (latch-off) is the classic open/close sequence; flag-style data sometimes hides in the count field.

## BACnet decoding cues

- Services: `WriteProperty` (0x0F), `ReadProperty` (0x0C), `Who-Is`/`I-Am` for discovery.
- Common property IDs: `85` Present-Value, `28` Description, `77` Object-Name, `103` Reliability.
- Object types: `analog-input` (0), `analog-output` (1), `analog-value` (2), `binary-input` (3), `binary-output` (4), `device` (8).

## Testing workflow — baseline → write → verify → restore

A safe write/test cycle has five phases. Skip a phase, claim a finding, and you will be wrong.

### 1. Baseline

Record state *before* anything:

```bash
# Modbus: snapshot first 200 holding regs and first 32 coils on unit 1
mbtget -r3 -a 0 -n 200 -u 1 TARGET > baseline_hr.txt
mbtget -r1 -a 0 -n 32  -u 1 TARGET > baseline_coils.txt
```

```python
from pymodbus.client import ModbusTcpClient
c = ModbusTcpClient("TARGET", 502); c.connect()
baseline = {
    "hr":    c.read_holding_registers(0, 125, slave=1).registers,
    "input": c.read_input_registers(0, 125, slave=1).registers,
    "coils": c.read_coils(0, 128, slave=1).bits,
    "di":    c.read_discrete_inputs(0, 128, slave=1).bits,
}
```

Repeat the same snapshot 3–5 times spaced by the polling interval (visible in PCAP) and diff: registers that change without a write reveal which addresses are live (sensors, scan counters, heartbeats); registers that are static are candidate setpoints/configuration.

### 2. Minimal write

Change exactly one bit/register at a time. Choose the smallest semantically meaningful unit:

- A single coil over the whole bank — find the address from the HMI screenshot or label first.
- A setpoint register, not the corresponding output register.
- A specific function code (FC 5 single-coil write rather than FC 15) so the log line is unambiguous.

```python
target_addr  = 100
target_value = 1
old = c.read_holding_registers(target_addr, 1, slave=1).registers[0]
c.write_register(target_addr, target_value, slave=1)
```

### 3. Verify (read-back + side channel)

```python
import time; time.sleep(0.5)                # one scan cycle
new = c.read_holding_registers(target_addr, 1, slave=1).registers[0]
assert new == target_value, (old, new)
```

Read-back alone is insufficient — a clever target accepts the write into a buffer that the ladder immediately overwrites. Check a *side channel* that proves real effect:

- HMI screen value, alarm row, or banner.
- Historian sample at the matching timestamp.
- A discrete-input or input-register that the ladder drives from your setpoint.
- A scoreboard/oracle HTTP/UDP endpoint, log line, or flag file.

If side-channel does not move, the write did not take effect even if read-back agreed.

### 4. Hold time

Some oracles sample every N seconds; the write must be held longer than N. If the PLC overwrites your register on the next scan, you are in a race-condition situation — see [attack-patterns.md](attack-patterns.md) "Race-condition / FDI" section for the tight-loop write pattern.

### 5. Restore

```python
c.write_register(target_addr, old, slave=1)
```

Restoring is part of the test, not optional politeness. It separates "I changed this and the oracle reacted" from "I changed this and the process is now stuck", and it gives the next test a clean baseline.

## Change-detection helpers

Compare two register snapshots:

```python
def diff_regs(a, b):
    return [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y]

for addr, old, new in diff_regs(baseline["hr"], snapshot["hr"]):
    print(f"HR[{addr}]  {old:5d} -> {new:5d}   delta={new-old:+d}")
```

For PCAP-based change detection (offline, no contact):

```bash
# Every write-multiple-registers event with reference and value list
tshark -r capture.pcap -Y 'modbus.func_code == 16' \
       -T fields -E separator=, \
       -e frame.time_epoch -e ip.src -e ip.dst \
       -e modbus.reference_num -e modbus.word_cnt -e modbus.data \
       > writes.csv
```

Then bin writes by `reference_num` and look at the value timeseries; a coil/register written once with a value far outside its normal range is the candidate.

For S7:

```bash
tshark -r capture.pcap -Y 's7comm.param.func == 0x05' \
       -T fields -e frame.time_epoch -e ip.src -e ip.dst \
       -e s7comm.item.area -e s7comm.item.dbnumber \
       -e s7comm.item.address -e s7comm.resp.data
```

For CIP:

```bash
tshark -r capture.pcap -Y 'cip.sc == 0x4d or cip.sc == 0x53' \
       -T fields -e frame.time_epoch -e cip.symbol -e cip.data
```

## CAN signal decoding

CAN frames carry 0–8 bytes of payload at an arbitration ID. To turn bytes into engineering values you need the DBC (or guess):

- Periodicity: `cansniffer` shows which IDs change rapidly (sensors), slowly (states), or only on demand (commands).
- Endianness: most automotive DBCs are little-endian (Intel); industrial CANopen is mixed.
- Scaling: `physical = raw * factor + offset`, often `factor = 0.1`, `0.01`, or `1/256`.
- Multiplexed signals: one byte selects which signals occupy the rest of the frame (common in airbag/transmission).

```bash
# Capture and decode
candump -L vcan0 > capture.log
canplayer -I capture.log vcan0      # replay later
cantools decode my.dbc vcan0         # if you have a DBC
```

## Validation checklist before claiming an effect

- [ ] Baseline captured 3+ times, with delta confirming static vs live registers.
- [ ] Single minimal write performed, exact FC/address/value recorded.
- [ ] Read-back agrees with the written value within one scan cycle.
- [ ] Side-channel (HMI/historian/oracle/log) confirms a downstream change.
- [ ] Effect held for at least N polling cycles (N from PCAP).
- [ ] Original value restored, or restore is recorded as not-possible with reason.
- [ ] No adjacent registers/coils/alarms were collaterally changed (re-snapshot).
- [ ] Engineering units confirmed via two-point calibration or labelled HMI/historian source — not assumed.
