# Source Coverage

This dedicated skill fills the ICS/OT gap in the private challenge-solving collection.

## Local and imported coverage used

- Imported industrial-control anomaly guidance: OT baselines, SCADA polling, Modbus/DNP3/OPC UA traffic, topology, function-code allowlists, and physics-aware process modeling.
- Repository methodology skills: `network-technique`, `forensic-technique`, `wireless-technique`, `reversing-technique`, and `coding/python-patterns`.
- External research synthesis: generic ICS/SCADA challenge workflows, protocol-family cues, safe validation, and common pitfalls.

## Coverage checklist

- [x] Passive PCAP and log analysis
- [x] OT role mapping: HMI, PLC, RTU, historian, gateway, broker, engineering workstation
- [x] Modbus/TCP
- [x] DNP3
- [x] BACnet/IP
- [x] S7comm
- [x] EtherNet/IP/CIP
- [x] OPC UA
- [x] MQTT
- [x] Profinet cues
- [x] CAN/CANopen pivots
- [x] Register, coil, tag, and setpoint decoding
- [x] Polling cadence and topology baseline analysis
- [x] Read-only-first safety model
- [x] Minimal authorized lab interaction model

## Explicit non-goals

- No destructive guidance for live industrial environments.
- No real facility identifiers, vendor-specific secrets, or challenge/platform branding.
- Tool syntax stays in tool-specific skills unless a short generic example is needed for reasoning.
