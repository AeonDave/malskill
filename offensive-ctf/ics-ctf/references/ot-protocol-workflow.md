# OT Protocol Workflow

Use this reference when `ics-ctf` is active and the task needs deeper protocol or process-state analysis.

## First-pass triage

1. Inventory artifacts: PCAP, logs, CSV historian data, register dump, project export, firmware, script, or live lab endpoint.
2. Identify protocol by ports and signatures:
   - Modbus/TCP: TCP 502, MBAP header, function codes 1, 2, 3, 4, 5, 6, 15, 16.
   - DNP3: TCP/UDP 20000, master/outstation exchanges, object groups and variations.
   - BACnet/IP: UDP 47808, Who-Is/I-Am, ReadProperty, WriteProperty.
   - S7comm: TCP 102, COTP/TPKT, setup communication, SZL reads, data block access.
   - EtherNet/IP/CIP: TCP/UDP 44818, RegisterSession, SendRRData, class/instance/attribute paths.
   - OPC UA: TCP 4840, endpoint negotiation, node IDs, browse/read/write/service calls.
   - MQTT: TCP 1883 or 8883, CONNECT, SUBSCRIBE, PUBLISH, retained messages, topic hierarchy.
   - CAN/CANopen: arbitration IDs, periodic frames, SDO/PDO/NMT patterns, counters, checksum bytes.
3. Build role map: master/client, PLC/outstation/server, HMI, historian, engineering workstation, gateway, broker, or unknown.
4. Build timeline: normal polling, bursts, writes, login/session events, errors, and values changing near the success oracle.

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
