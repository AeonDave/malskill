# OT Protocol Workflow

Use this reference when `ics-ctf` is active and the task needs deeper protocol or process-state analysis.

## First-pass triage

1. Inventory artifacts: PCAP, logs, CSV historian data, register dump, project export, firmware, script, or live lab endpoint.
2. Identify protocol by ports and signatures:
   - Modbus/TCP: TCP 502, MBAP header, function codes 1, 2, 3, 4, 5, 6, 15, 16. Wireshark: `modbus`, `modbus.func_code`.
   - DNP3: TCP/UDP 20000, master/outstation exchanges, object groups and variations. Wireshark: `dnp3`.
   - BACnet/IP: UDP 47808, Who-Is/I-Am, ReadProperty, WriteProperty. Wireshark: `bacapp`, `bacnet`.
   - S7comm: TCP 102, COTP/TPKT, setup communication, SZL reads, data block access. Wireshark: `s7comm`, `s7comm.param.func`.
   - EtherNet/IP/CIP: TCP/UDP 44818, RegisterSession, SendRRData, class/instance/attribute paths. Wireshark: `enip`, `cip`.
   - OPC UA: TCP 4840, endpoint negotiation, node IDs, browse/read/write/service calls. Wireshark: `opcua`.
   - MQTT: TCP 1883 or 8883, CONNECT, SUBSCRIBE, PUBLISH, retained messages, topic hierarchy. Wireshark: `mqtt`, `mqtt.topic`.
   - CAN/CANopen: arbitration IDs, periodic frames, SDO/PDO/NMT patterns, counters, checksum bytes.
3. Build role map: master/client, PLC/outstation/server, HMI, historian, engineering workstation, gateway, broker, or unknown.
4. Build timeline: normal polling, bursts, writes, login/session events, errors, and values changing near the success oracle.

## Modbus function code mini-reference

| FC (dec / hex) | Name                       | Touches               | Typical use                         |
| -------------- | -------------------------- | --------------------- | ----------------------------------- |
| 1  / 0x01      | Read Coils                 | coils (RW bits)       | reading actuator/output state       |
| 2  / 0x02      | Read Discrete Inputs       | discrete inputs (RO)  | reading sensor/input state          |
| 3  / 0x03      | Read Holding Registers     | holding regs (RW 16b) | reading setpoints, configuration    |
| 4  / 0x04      | Read Input Registers       | input regs (RO 16b)   | reading measured process values     |
| 5  / 0x05      | Write Single Coil          | coil                  | toggling pump/valve/safety flag     |
| 6  / 0x06      | Write Single Register      | holding reg           | changing setpoint or mode           |
| 8  / 0x08      | Diagnostics                | device                | restart, listen-only, counters      |
| 15 / 0x0F      | Write Multiple Coils       | coils                 | bulk actuator changes               |
| 16 / 0x10      | Write Multiple Registers   | holding regs          | bulk setpoint or table writes       |
| 43 / 0x2B      | Encapsulated/Device ID     | device                | vendor, product code, firmware tag  |

Watch for: writes against coils 9999 / 1xxxx / 4xxxx address mappings, MBAP transaction ID reuse, unit ID drift, and exception responses (function code with high bit set, 0x81–0x90).

## Metadata vs payload

In OT captures, the meaningful data is not always in the value field. When a write looks suspicious but the value column decodes to noise, also check the address/reference number, transaction ID, unit ID, byte count, timing gap, and order of operations. Examples:

- Register/Reference Number carrying ASCII codes across a sequence of single-register writes.
- Transaction IDs forming a counter that hides extra channels.
- Unit ID acting as a routing tag instead of a slave address.
- Coil indexes encoding bit positions of a packed field.
- Quantity/byte-count fields larger than expected, indicating a non-standard encoder.

## CSV-from-pcap decoding recipe

For protocol-field decoding at scale, prefer exporting fields from a PCAP and decoding in pandas/Python instead of trusting GUI scrollbacks.

```bash
# Extract Modbus write-multiple-registers (FC 16) reference numbers and values.
tshark -r capture.pcapng -Y 'modbus.func_code == 16' \
  -T fields -E header=y -E separator=, \
  -e frame.time_relative -e ip.src -e ip.dst \
  -e modbus.reference_num -e modbus.word_cnt -e modbus.regval_uint16 \
  > modbus_writes.csv
```

```python
import pandas as pd

df = pd.read_csv("modbus_writes.csv")
df["modbus.reference_num"] = pd.to_numeric(df["modbus.reference_num"], errors="coerce")
refs = df["modbus.reference_num"].dropna().astype(int)

# Try the reference-number lane first; if noise, also try the value lane.
printable = [chr(v) for v in refs if 32 <= v <= 126]
print("reference-num ascii:", "".join(printable))
```

When `pyshark`/`scapy` skip a field, fall back to `tshark -T fields` for ground truth.

## Protocol filter cheatsheet (Wireshark)

- Modbus reads: `modbus.func_code in {1 2 3 4}`
- Modbus writes: `modbus.func_code in {5 6 15 16}`
- Modbus exceptions: `modbus.func_code > 128`
- S7 setup/job: `s7comm.param.func` plus `s7comm.header.rosctr`
- DNP3 control relay: `dnp3.al.objq.code == 12`
- BACnet write: `bacapp.confirmed_service == 15`
- OPC UA writes: `opcua.servicenodeid.numeric == 671` (WriteRequest) or follow service ids
- MQTT publish to topic: `mqtt.msgtype == 3 and mqtt.topic contains "telemetry"`
- CIP write tag: `cip.service == 0x4D` (Write Tag Service)

## Baseline before anomaly

ICS traffic is often deterministic. Before hunting secrets, derive expected behavior:

- Polling cadence per source/destination and per object/register/tag.
- Read/write ratio and whether writes are rare.
- Allowed function codes per communication pair.
- Register or tag ranges touched repeatedly.
- Periodic process cycles and values that move together.
- New device pairs, new unit IDs, or new topics that appear late.

An anomaly is stronger when it violates more than one baseline dimension: new source, rare function, unusual register, unexpected value, and process-state change.

## Register and tag semantics

- Test endian variants: big, little, word-swapped, byte-swapped, and BCD.
- Check signedness and scaling: raw integer, fixed-point, IEEE-754 float, bitfields, and packed status flags.
- Group adjacent registers; many process values span 2 or 4 registers.
- Correlate values with names from HMI screens, topic paths, comments, symbols, or repeated physical ranges.
- Avoid assuming a flag is ASCII until framing and byte order are proven.

## Artifact lanes

- PCAP lane: export conversations, protocol fields, stream payloads, timing deltas, and read/write subsets before scripting.
- Historian/log lane: normalize timezone and clock skew, identify tag/value/unit columns, sort sparse writes, and correlate alarms with process changes.
- Project-export lane: search symbols, comments, ladder/ST code, tag databases, constants, screen labels, and network configuration.
- Firmware lane: carve archives and strings, locate protocol clients, extract hard-coded endpoints, and map custom encoders before dynamic testing.
- Serial/CAN lane: infer baud/framing or arbitration IDs, periodic frames, counters, checksums, and message groups before replay.

## Write-event analysis

When a packet writes state, extract:

- actor: source IP, unit ID, session, topic, or client ID
- target: register/tag/object/property
- operation: function code, service, method, or topic action
- value: raw, decoded, scaled, and previous value if available
- timing: preceding auth/session steps and following process response
- effect: read-back, HMI update, alarm, state transition, emitted message, or flag response

Prefer reconstructing the write from evidence before replaying it. If replay is required, send the smallest single operation and verify by read-back.

## Safe interaction ladder

1. Passive decode from captured artifacts.
2. Read-only query against isolated lab service.
3. Single idempotent read/write simulation locally.
4. Minimal target write only when explicit lab scope and objective require it.
5. Stop after validation; do not continue enumerating once the proof is recovered.

## Validation signals

- recovered secret in register, tag, topic, historian row, or event log
- anomalous write decoded and tied to a process-state transition
- read-back confirms intended register/object/tag value
- packet timeline proves a hidden channel or unauthorized command
- HMI/process display, service response, or checker reports solved state

## Common pitfalls

- Treating OT ports like generic IT services and running noisy scanners first.
- Ignoring unit IDs, slot/rack, object variations, and vendor-specific encapsulation.
- Missing word-swapped floats or packed bitfields.
- Overlooking retained MQTT messages, BACnet broadcasts, or CAN periodic counters.
- Assuming every write is malicious; maintenance windows and normal batch transitions can be write-heavy.
