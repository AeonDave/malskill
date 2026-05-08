---
name: ics-ctf
description: "Challenge-solving methodology for industrial control, SCADA, and OT protocol lab tasks. Use when artifacts or services involve Modbus, DNP3, BACnet, S7comm, EtherNet/IP, OPC UA, MQTT, Profinet, CAN/CANopen, PLCs, HMIs, RTUs, process historians, register maps, coils, setpoints, polling baselines, or process-state anomalies. Focuses on read-only evidence, protocol decoding, physics-aware reasoning, and safe validation in authorized isolated environments."
license: MIT
compatibility: "AgentSkills-compatible agents; local artifacts; authorized isolated lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# ICS CTF

Solve industrial-control and OT protocol lab tasks by treating traffic and process state as evidence first, then selecting the smallest safe action that proves the objective.

## When this skill applies

- PCAPs, logs, register dumps, historian exports, or remote services involving PLC, HMI, RTU, engineering workstation, SCADA, or process-control wording.
- Protocol cues: Modbus/TCP, DNP3, BACnet, S7comm, EtherNet/IP/CIP, OPC UA, MQTT, Profinet, CAN, CANopen, serial fieldbus, coils, holding registers, function codes, setpoints, or actuator state.
- Tasks requiring traffic baselining, protocol-state reconstruction, register decoding, anomaly identification, or cautious interaction with an isolated lab service.

## Operating model

1. Preserve and identify the artifact: hash files, list ports, extract timestamps, and record protocol guesses with evidence.
2. Separate roles before payloads: identify HMI, PLC, RTU, historian, engineering workstation, gateway, broker, and attacker-like clients.
3. Baseline normal behavior: polling interval, read/write ratio, function codes, register ranges, topics, tags, and repeated process cycles.
4. Decode semantics: map coils/registers/tags to values, infer endian/scaling, correlate writes with observed physical or process changes.
5. Prefer read-only validation. Only write or send commands when the target is clearly an isolated lab and the success oracle requires it.
6. Prove the result with a minimal, replayable signal: decoded secret, anomalous write, state transition, topic payload, register value, or process timeline.

## Technique integration

Load these as decision engines when their domain appears:

- `network-technique` for PCAP, protocol, and service exposure analysis.
- `forensic-technique` for evidence handling, timelines, and artifact preservation.
- `wireless-technique` for RF, serial-over-radio, or fieldbus captures crossing into wireless analysis.
- `reversing-technique` for PLC program blocks, firmware, protocol clients, or custom encoders.
- `python-patterns` for parsers, register decoders, and safe replay harnesses.

## Tool routing

Use tool families based on the evidence, not habit:

- `wireshark`, `tcpdump`, and `zeek` for protocol carving, conversations, timing, and exported fields.
- `pymodbus`, MQTT clients, OPC UA clients, Scapy, python-snap7, and can-utils for controlled parsing and replay.
- CyberChef, jq, pandas, and Python scripts for endian, scaling, timestamp, and register-table transformations.
- `nmap` OT NSE scripts only against authorized isolated labs; passive PCAP analysis is preferred when artifacts are enough.
- `binwalk`, `ghidra`, `radare2`, and `strings` when the task includes PLC firmware, engineering-project exports, or custom protocol binaries.
- `saleae-logic-2` when a capture includes serial, CAN, or fieldbus waveforms rather than decoded network traffic.

## Safety and scope gates

- Treat real-world ICS/OT writes as unsafe by default. In lab tasks, document why the environment is isolated before any write.
- Never reset, stop, upload firmware, or mass-write registers unless the prompt explicitly defines an isolated target and the objective requires that exact action.
- Keep a pivot ledger: protocol hypothesis, field evidence, decoded meaning, validation signal, and next safest step.
- If traffic looks malformed, first test endian, scaling, segmentation, custom function codes, or encapsulation before assuming exploitation.
- Report uncertainty: process semantics are inferred unless confirmed by labels, HMI screens, historian tags, or repeated cause-effect evidence.

## Quick pivots

- Modbus: map unit IDs, function codes, coil/discrete/input/holding register ranges, write events, and byte order.
- DNP3: inspect objects, variations, unsolicited responses, control relay outputs, and outstation/master roles.
- BACnet: enumerate devices, objects, properties, write-property events, and broadcast discovery.
- S7comm: identify rack/slot, SZL reads, data block accesses, and program/block transfer indicators.
- EtherNet/IP/CIP: decode sessions, class/instance/attribute paths, tag names, and explicit messaging.
- MQTT/OPC UA: reconstruct topics/nodes, publisher roles, credentials, retained messages, and process-state deltas.
- CAN/CANopen: infer arbitration IDs, periodic frames, PDO/SDO patterns, endian, counters, and checksum bytes.
- Historian/log exports: normalize timestamps, recover tag/value/unit columns, identify sparse writes, and correlate alarm rows with process deltas.
- Project exports/firmware: extract symbols, comments, ladder/ST strings, tag databases, constants, network configuration, and custom encoders before dynamic interaction.
- Serial/fieldbus captures: identify baud/framing, address fields, checksums, counters, and periodic control loops before replaying frames.

## Resources

- [references/ot-protocol-workflow.md](references/ot-protocol-workflow.md) — detailed protocol triage, field extraction, anomaly workflow, and validation cues.
