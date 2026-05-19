---
name: ics-ctf
description: "Challenge-solving methodology for industrial control, SCADA, and OT protocol lab tasks. Use when artifacts or services involve Modbus, DNP3, BACnet, S7comm, EtherNet/IP, OPC UA, MQTT, Profinet, CAN/CANopen, PLCs, HMIs, RTUs, process historians, register maps, coils, setpoints, polling baselines, or process-state anomalies. Focuses on read-only evidence, protocol decoding, physics-aware reasoning, and safe validation in authorized isolated environments."
license: MIT
compatibility: "AgentSkills-compatible agents; local artifacts; authorized isolated lab environments."
metadata:
  author: AeonDave
  version: "1.8"
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

- `wireshark`, `tcpdump`, `tshark`, and `zeek` for protocol carving, conversations, timing, display filters (`modbus.func_code`, `s7comm`, `dnp3`, `bacapp`, `cip`, `opcua`, `mqtt`), and CSV/JSON field export.
- `pymodbus`, `modbus-cli`, `mbtget`, `QModMaster`, and `ModbusPal` for Modbus read/write, function-code abuse (FC 1–6, 15, 16, 8, 43), coil/register sweeps, and lab simulation.
- `python-snap7`, `snap7-server`, `plcscan`, and `s7scan` for Siemens S7 enumeration (rack/slot, SZL, DB reads) and lab targets.
- `opcua-asyncio`, `FreeOpcUa`, and `OPCUaScanner` for OPC UA endpoint enumeration, anonymous-policy detection, node browse, and read/write.
- `mosquitto_pub`/`mosquitto_sub`, [`mqtt-pwn`](../../offensive-tools/network/mqtt-pwn/SKILL.md), [`mosquitto-clients`](../../offensive-tools/network/mosquitto-clients/SKILL.md), `MQTT Explorer`/`MQTTX`, Scapy MQTT layer, MQTTSA, and the Wireshark `mqtt` + `sparkplug` dissectors for topic enumeration (`#`, `$SYS/#`), retained-message inspection, Sparkplug B (Eclipse Tahu / `pysparkplug`) decoding, broker fingerprinting (Mosquitto/EMQX/HiveMQ/VerneMQ/NanoMQ) and auth probing. Always pair with the adjacent dashboard port (EMQX 18083, HiveMQ 8080, Node-RED 1880, OpenPLC 8080, Home Assistant 8123) — it is usually the real entry point.
- `can-utils` (`candump`, `cansniffer`, `cansend`, `cangen`) for CAN bus capture, periodic-frame analysis, and replay against virtual `vcan` interfaces.
- CyberChef, `jq`, `pandas`, and Python scripts for endian, scaling, timestamp, register-table transformations, and CSV-from-pcap decoding pipelines.
- `nmap` OT NSE scripts (`modbus-discover`, `s7-info`, `enip-info`, `bacnet-info`, `mqtt-subscribe`, `opcua-info`) only against authorized isolated labs; passive PCAP analysis is preferred when artifacts are enough.
- `binwalk`, `ghidra`, `radare2`, and `strings` when the task includes PLC firmware, engineering-project exports, or custom protocol binaries.
- `saleae-logic-2` when a capture includes serial, CAN, or fieldbus waveforms rather than decoded network traffic.
- Known lab engineering-software (OpenPLC runtime/editor, Codesys, ScadaBR, Node-RED, ConPot honeypot, MiniCPS, ICSsim) often expose web panels and scripting hooks that pair with protocol access; treat them as separate pivot targets when ports such as 1880, 8080, 8443, 11502, or vendor-specific HTTP appear.

## Safety and scope gates

- Treat real-world ICS/OT writes as unsafe by default. In lab tasks, document why the environment is isolated before any write.
- Never reset, stop, upload firmware, or mass-write registers unless the prompt explicitly defines an isolated target and the objective requires that exact action.
- Keep a pivot ledger: protocol hypothesis, field evidence, decoded meaning, validation signal, and next safest step.
- If traffic looks malformed, first test endian, scaling, segmentation, custom function codes, or encapsulation before assuming exploitation.
- Report uncertainty: process semantics are inferred unless confirmed by labels, HMI screens, historian tags, or repeated cause-effect evidence.

## Quick pivots

- Modbus: map unit IDs, function codes (FC 1/2 read coils/discrete, FC 3/4 read holding/input, FC 5/6 single write, FC 15/16 multi write, FC 8 diagnostics, FC 43 device ID), coil/register ranges, write events, byte order, and byte-vs-word counts. Wireshark filter: `modbus.func_code == 16` for write-multiple-registers events. Check BOTH register/reference number AND register value fields — flag-style data is often hidden in the address, transaction ID, or unit ID instead of the value.
- DNP3: inspect objects, variations, unsolicited responses, control relay outputs (group 12), and outstation/master roles. Filter: `dnp3`.
- BACnet: enumerate devices, objects, properties, write-property events, and broadcast discovery (`Who-Is`/`I-Am`). Filter: `bacapp` plus service choice.
- S7comm: identify rack/slot, SZL reads, data block accesses, and program/block transfer indicators. Filter: `s7comm` plus `s7comm.param.func`. Pair with `plcscan`/`s7scan` for lab enumeration and `python-snap7` for DB reads.
- EtherNet/IP/CIP: decode sessions, class/instance/attribute paths, tag names, and explicit messaging. Filter: `enip` and `cip`.
- OPC UA: walk endpoint discovery, security policies (note `None` policy = anonymous), node IDs, and Browse/Read/Write services. Filter: `opcua`.
- MQTT: reconstruct topics/nodes, retained messages, client IDs, will payloads, and process-state deltas. Filter: `mqtt`. Try wildcard subscriptions `#` and `$SYS/#` when broker access is authorized; grab `$SYS/broker/version` + `clients/total` + `retained messages/count` first.
- Sparkplug B / MQTT-bridge pivot: topic prefix `spBv1.0/<group>/<NBIRTH|NDATA|NCMD|DBIRTH|DDATA|DCMD>/<edge>[/<device>]` with Protobuf payload signals an Ignition / Cirrus Link / EMQX Neuron / Node-RED bridge. Capture an NBIRTH/DBIRTH first to resolve alias→tag, then treat DCMD writes as actuator writes (Modbus FC 5/6 equivalent). Bridges (Cirrus Link, EMQX Neuron, Node-RED, OpenPLC MQTT, Advantech/Moxa/HMS gateways) round-trip MQTT writes into Modbus/S7/OPC-UA — confirm with state-topic lag (~1 s) before assuming raw broker access reaches the PLC.
- Mosquitto pivot: pull `mosquitto.conf` and `passwd_file` if a host is in scope (`auth_plugin`, `bridge_*`, `acl_file`, `allow_anonymous`); hashes crack with `hashcat` (PBKDF2-SHA512 mode for 2.x, legacy SHA512+salt for 1.x). Pin findings to `$SYS/broker/version` and check vendor advisories (Mosquitto CVE-2017-7650 ACL pattern bypass, CVE-2024-3935 TLS DoS; EMQX/HiveMQ/VerneMQ banners similarly).
- CAN/CANopen: infer arbitration IDs, periodic frames, PDO/SDO patterns, endian, counters, and checksum bytes; use `candump`/`cansniffer` for live data.
- Historian/log exports: normalize timestamps, recover tag/value/unit columns, identify sparse writes, and correlate alarm rows with process deltas.
- Project exports/firmware: extract symbols, comments, ladder/ST strings, tag databases, constants, network configuration, and custom encoders before dynamic interaction.
- Serial/fieldbus captures: identify baud/framing, address fields, checksums, counters, and periodic control loops before replaying frames.
- Engineering-software pivot: when an OpenPLC/Codesys/ScadaBR/Node-RED web panel sits next to the PLC port, check default credentials, scripting hooks (OpenPLC PSM module, Node-RED function nodes), and known CVEs for that specific runtime before scripting writes against the protocol.
- Process-state pivot: pressure/temperature/level registers near safety thresholds, coils tied to pumps/valves/cooling, and setpoint registers driving alarms are common objectives; correlate writes to expected physical effect and verify by read-back or HMI state, not by assumption.
- Purdue-model pivot: map each host to L0 (sensors/actuators), L1 (PLC/RTU), L2 (HMI/SCADA), L3 (historian, engineering workstation, MES) before choosing a target; the shortest path to objective is often an L2/L3 host (HMI web, RDP, historian DB, project files) rather than direct L1 protocol abuse.
- Engineering-workstation pivot: project files on the engineering workstation (`.acd`/`.l5x` RSLogix/Studio 5000, `.ap14`/`.zap14` TIA Portal, `.pro`/`.projectarchive` Codesys, `.s7p`/`.ap13` Step7) carry ladder/ST source, tag names, network configuration, and sometimes credentials — grab them before native protocol attacks when the workstation is in scope.
- Race-condition / False Data Injection (FDI) pivot: when a master polls a PLC on a fixed cycle (e.g. every 1–3 s), writes inside the cycle window can flip coils/registers between the PLC update and the next master read; build the write loop tighter than the poll interval and verify the master observes the desynced state.
- L2/MITM pivot in flat OT networks: ARP poisoning between HMI and PLC (or between two PLCs on a Device-Level Ring) lets you rewrite Modbus/EtherNet/IP/S7 in flight with `ettercap`/`bettercap` + `NetfilterQueue` + Scapy filters — useful when direct write is logged but rewrite-in-transit is not.
- HMI-side pivot: HMI panels often expose VNC (5900) without auth, vendor web UIs with default credentials, or shared SMB folders containing PLC project archives, recipe files, and screenshots that label tag meanings.
- Historian pivot: PI Server, FactoryTalk Historian, WinCC, and Wonderware historians (MSSQL/proprietary on 1433, 5450, 5460) carry long timeseries of every tag and often default/weak SQL credentials — they are an alternative to live PLC read for proving a process anomaly.
- Scan-cycle awareness: writes to the output image (`%Q`/coils) are overwritten next PLC scan; setpoint writes (`%M`/holding registers consumed by ladder) persist. Forces override both regardless of ladder. Mode transitions (`STOP`/`RUN`/`PROG`/`FAULT`) are high-signal events — search PCAPs for them before chasing register writes.
- Signal decoding pivot: raw register ≠ engineering value. Guess byte/word order (`ABCD`/`CDAB`/`BADC`/`DCBA`) by checking which order yields a plausible temperature/pressure/level, then solve `EU = raw*scale + offset` from two known HMI/historian points. Status registers pack 16 alarm bits — map each bit before claiming meaning.
- Test-cycle discipline: every write goes through baseline (3+ snapshots, diff to identify live vs static registers) → minimal write (one bit/register, smallest FC) → read-back → side-channel verification (HMI/historian/oracle, not just read-back) → hold for ≥ N polling cycles → restore. Read-back alone is insufficient evidence.
- IT→OT chain pivot: realistic OT compromise starts in IT (Responder/SMB-relay, AS-REP/Kerberoast, ADCS ESC1) → DA → OT-DMZ jump (backup script creds, KeePass dump CVE-2023-32784, reused local-admin) → engineering workstation (vendor IDE + project files + saved PLC creds) → PLC setpoint/logic. PLC default passwords often arrive via photos and panel stickers on file shares, not live enumeration. Budget ~60 % IT/AD, ~25 % DMZ pivot, ~15 % PLC interaction; never touch SIS (Triconex/HIMA/GuardLogix).
- Priority frame: OT inverts CIA into Safety > Availability > Integrity > Confidentiality; reject findings/recommendations that raise confidentiality at the cost of safety or availability, and frame impact in operator-visible terms (alarm row, HMI banner, historian sample) rather than CVE wording.
- TIA Portal project pivot: when given a `.zap1x`/`.ap1x`/`.s7p` archive, treat it like source code. Match TIA Portal major version + HSP to the CPU firmware, dump PLC + HMI tag tables to CSV, reverse OB1 networks in order, then load into PLCSim Advanced to drive inputs and watch DB/M evolution offline. The DB area is the cleanest write surface (setpoint changes leave no Q-image footprint); HMI buttons are usually thin proxies onto M bits. Basic/Comfort panels archive analog tags to internal SD and to the back-USB stick — pull both when you have physical access.
- Real-world archetype pivot (2025-2026): recognize the chain before improvising. Single Modbus FC 6 write flipping a thermal/level setpoint → FrostyGoop (Sandworm). Port 20256 + default `1111` on a Unitronics PLC + HMI defacement + disabled upload/download → CyberAv3ngers/BAUXITE. COTP+S7comm session pushing an S7-300/400 to STOP without ladder upload → BAUXITE `PLC_Controller.exe` (Jul 2025). PowerShell that scans Modbus holding registers > threshold and overwrites in a loop → BAUXITE `exploit.ps1` (Nov 2025). Sierra Wireless AirLink RV50/RV55 or cellular gateway as the only OT ingress + pure LOTL (`netsh`, `wmic`, `ntdsutil`, `PortProxy`, AD Explorer) on the EWS → VOLTZITE/Volt Typhoon. Ivanti edge CVE → AD creds → handoff → VOLTZITE → SYLVANITE broker chain. Trimble Cityworks unsafe-deserialization RCE + GIS data theft → KAMACITE/VOLTZITE prepositioning, flag lives in mapped asset metadata. MQTT C2 (1883/8883) on a fuel-management/Unitronics-adjacent gauge → IOCONTROL (Claroty Team82, Dec 2024). FortiGate SSL-VPN over Tor + interactive jump host + PsExec + `nircmd` screenshots of `*SCADA*`/`*HIST*` hosts + Rubeus **Diamond Ticket** + `rsocx` reverse SOCKS + FortiGate config theft with persistent admin re-add + GPO-pushed Scheduled Task running a Mersenne-Twister C++ wiper (DynoWiper) or an LLM-written PowerShell `WriteRandomBytes` wiper (LazyWiper) at `SYSTEM`, optionally finished by an iLO/IPMI-mounted Tiny Core Linux ISO `dd`-ing the RAID + dropping Intel RST metadata → Static Tundra / Berserk Bear / Ghost Blizzard / Dragonfly destructive archetype (CERT Polska 29 Dec 2025, first publicly documented destructive op by this cluster). See [references/incidents.md](references/incidents.md) for the full threat-group → CTF-pivot mapping, vendor/CVE landing pads (Unitronics, Sierra Wireless, Ivanti, Cityworks, BESS, Sophos, ATG), and the Path 1/2/3 attack-path templates.

## Resources

- [references/ot-protocol-workflow.md](references/ot-protocol-workflow.md) — protocol triage, field extraction, anomaly workflow, and validation cues.
- [references/plc-interaction-recipes.md](references/plc-interaction-recipes.md) — read-only-first interaction recipes for Modbus, S7, OPC UA, MQTT, and CAN against authorized lab targets, plus engineering-software pivot patterns.
- [references/attack-patterns.md](references/attack-patterns.md) — Purdue-model mapping, engineering-workstation pivots, project-file formats, race-condition / FDI writes, L2 MITM in flat OT segments, HMI/historian pivots, and operational-impact reasoning.
- [references/signal-decoding-and-testing.md](references/signal-decoding-and-testing.md) — PLC scan cycle and memory areas, Modbus/CIP/S7/DNP3/BACnet decoding cues, integer/float/BCD/string/time encodings, byte-and-word order resolution, CAN signal decoding, the baseline → write → verify → restore test cycle, and a final validation checklist.
- [references/fundamentals-and-it-to-ot-chain.md](references/fundamentals-and-it-to-ot-chain.md) — OT vs IT priority model (Safety > A > I > C), asset taxonomy (PLC/HMI/SCADA/DCS/SIS/RTU/IED/historian/engineering workstation), Purdue recap, and the full realistic IT→OT kill chain (foothold → AD → ADCS → DMZ pivot → engineering workstation → PLC setpoint vs logic upload) with detection-vs-evasion model.
- [references/tia-portal-and-plc-fundamentals.md](references/tia-portal-and-plc-fundamentals.md) — Siemens S7-1500 / TIA Portal toolchain (project archives, HSP versioning, PLCSim Advanced offline simulation), OB/FB/FC/DB block taxonomy, S7-1500 memory areas (I/Q/M/DB/L), HMI tag binding, PROFINET DCP cell layout, and a step-by-step workflow for analyzing a seized project archive.
- [references/incidents.md](references/incidents.md) — historical + 2025-2026 ICS/OT incident intel (Dragos 2026 YiR, CISA AA23-335A/AA24-038A/AA22-055A/AA22-103A, CloudSEK Iran-US 2026, Claroty Team82): threat-group → CTF-pivot mapping (VOLTZITE/SYLVANITE/AZURITE/PYROXENE/KAMACITE/ELECTRUM/BAUXITE/CyberAv3ngers/APT33/APT35/MuddyWater/Handala), vendor/CVE landing pads (Unitronics 20256, Sierra Wireless AirLink, Ivanti, Trimble Cityworks, BESS, Sophos, ATG, Siemens S7-300/400 legacy), the three attack-path templates (direct exposure, phishing-to-EWS, IT-to-OT lateral), and design-vs-recognition cheats for matching CTF scenarios to current adversary behavior.
- [references/mqtt-iot-ics-bridges.md](references/mqtt-iot-ics-bridges.md) — MQTT broker triage (`$SYS` fingerprinting, anonymous/retained/LWT/ACL probing), Sparkplug B topic + payload model (Eclipse Tahu), Mosquitto/EMQX/HiveMQ/VerneMQ/NanoMQ specifics with CVE references, MQTT-to-PLC bridge stacks (Cirrus Link Ignition modules, EMQX Neuron, Node-RED, OpenPLC, Advantech/Moxa/HMS gateways), tool chain (`mqtt-pwn`, `mosquitto-clients`, MQTT Explorer/MQTTX, MQTTSA, Scapy, Cotopaxi), and curated CTF writeups (TryHackMe Bugged, AoC IoT/SCADA days) plus real-world case material (Akamai, Trend Micro, Claroty Team82, CISA ICS advisories).
