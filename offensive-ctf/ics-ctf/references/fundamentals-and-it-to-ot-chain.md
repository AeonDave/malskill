# OT/ICS Fundamentals and Realistic IT→OT Kill-Chain

Two complementary references in one file: (1) the core OT/ICS mental model that drives every defensive and offensive decision; (2) a realistic end-to-end IT→OT compromise pattern observed in modern IT/OT red-team exercises and APT campaigns (Volt Typhoon family).

## 1. Fundamentals

### OT vs IT priorities

IT follows **C-I-A** (Confidentiality, Integrity, Availability). OT inverts it and prepends safety:

```
Safety  >  Availability  >  Integrity  >  Confidentiality
```

Concrete consequences:

- Encryption is often absent on the wire (Modbus, S7 v0/v1, DNP3 unsecured, EtherNet/IP) because adding crypto risks scan-cycle jitter and downtime.
- Patching cadence is slow; PLCs and HMIs run firmware that is 5–15 years old in production.
- "Reboot to fix" is not an acceptable answer; downtime can mean physical damage, lost product, or regulatory violation.
- Default credentials persist for years because changing them requires shift coordination and re-validation.

A finding that improves confidentiality at the cost of process safety or availability is rejected by operators. Frame every recommendation in those terms.

### OT/ICS asset taxonomy

| Asset | Role | Typical OS / tech |
| --- | --- | --- |
| **PLC** (Programmable Logic Controller) | Reads sensors, runs ladder/ST/FBD logic, drives actuators. | Vendor RTOS (Logix, S7, Codesys, PLCnext); Modbus/S7/EIP/Profinet on the wire. |
| **HMI** (Human-Machine Interface) | Operator screen; visualizes state, accepts commands. | Windows + WinCC, FactoryTalk View, iFIX, Ignition, ScadaBR, ScadaLTS, FUXA. |
| **SCADA** | Wide-area supervisory aggregation across many sites. | Windows servers + WonderWare, Cygnet, OSIsoft PI, Ignition Gateway. |
| **Historian** | Long-term timeseries of every tag for trending/compliance. | OSIsoft PI Server, FactoryTalk Historian, WinCC, Wonderware Historian, Grafana+Telegraf, GE Proficy. |
| **Engineering workstation** | Programs/debugs PLCs; holds project files with logic + tag DB. | Windows + Studio 5000, TIA Portal, RSLogix, PLCnext Engineer, Codesys, CX-One. |
| **DCS** (Distributed Control System) | Plant-wide closed-loop control, often vendor monoculture. | Emerson DeltaV, Honeywell Experion, ABB 800xA, Siemens PCS 7, Yokogawa CENTUM. |
| **SIS** (Safety Instrumented System) | Independent shutdown path; rated SIL 2/3. | Triconex, HIMA, Allen-Bradley GuardLogix. **Out of scope** for offensive testing — failure = casualties. |
| **RTU** (Remote Terminal Unit) | Field unit, often DNP3/IEC-101/104 to control center. | Vendor firmware, sometimes Linux. |
| **IED** (Intelligent Electronic Device) | Substation relays/meters, IEC-61850 GOOSE/SV. | Vendor firmware. |

### Purdue reference model (recap)

```
Level 5  Enterprise (ERP, SAP, internet-facing)
Level 4  Site business (mail, file shares, AD)
─── IT/OT-DMZ ───  jump server, patch relay, historian replica
Level 3  Operations (engineering workstations, historian, MES, AV/EDR)
Level 2  Supervision (HMI, SCADA servers)
Level 1  Control (PLCs, RTUs, IEDs)
Level 0  Physical (sensors, actuators, motors, valves)
─── Safety bus (segregated) ───  SIS, fire/gas, ESD logic
```

Real-world plants are flatter than the diagram suggests; in pentests expect IT (L4) → OT-DMZ → Supervision/Control with only L4 firewall ACLs separating zones, and routinely the same AD trust spanning IT and OT.

## 2. Realistic IT → OT kill chain

A modern OT compromise rarely starts at the PLC. It starts on a low-privilege IT user, traverses Active Directory, lands on the engineering workstation, and only then touches process logic. The chain below is consistent across recent CISA advisories (Volt Typhoon) and benchmarked red-team exercises (StealthCup arXiv:2511.17761).

### Stage 1 — IT foothold (L4/L5)

Goal: any domain credential, any host.

Typical primitives:

- LLMNR/NBT-NS poisoning with Responder; capture Net-NTLMv2 from a stale broadcast resolver. In environments where broadcast is blocked, a *scheduled task on a workstation* periodically authenticates to a smb path (`\\fileserver\share\update`) — capture the hash there.
- SMB relay (ntlmrelayx) of the captured authentication to a non-signed target (file server, MSSQL, ADCS HTTP).
- Password spray against external services (OWA, RDGW, VPN) using `name@domain` from harvested email patterns.

Detection blind spot: alerts hide in user-logon noise. Wazuh-class HIDS produces >90 % false positives in this phase, so signal-to-noise is on the attacker's side.

### Stage 2 — AD enumeration and credential expansion (L4)

- SID brute via `lookupsid.py` from a captured low-priv account.
- AS-REP roast (`GetNPUsers.py`) and Kerberoast (`GetUserSPNs.py`); offline crack with hashcat (`-m 18200`, `-m 13100`).
- SMB share crawl for documents, archived emails, secrets files, *photographs of PLCs on the plant floor* — the photo's HMI screen or panel sticker often reveals default device passwords, IP plan, or vendor.
- BloodHound to find a path to Domain Admin; ADCS ESC1/ESC4/ESC8 templates are the fastest privilege jump on most networks.

### Stage 3 — Domain dominance (L4)

- Certipy ESC1: request a certificate as a target user via a vulnerable template with `EnrolleeSuppliesSubject`; authenticate with the cert (PKINIT) and recover the NTLM hash.
- Create persistence account (e.g. `svc_plumber`, ironically named to blend with maintenance tickets) and add to Domain Admins or a privileged group.
- Dump `ntds.dit` with `secretsdump.py` for offline cracking and golden-ticket capability.

### Stage 4 — IT/OT-DMZ pivot

The OT-DMZ usually has a jump server, an engineering-workstation replica, a historian replica, and an OT-side AD that trusts (or shares accounts with) the IT side. Cross via:

- A misconfigured backup script that runs as local admin and leaves credentials in plaintext.
- A KeePass database whose master password can be recovered from a memory dump using CVE-2023-32784 (or modern variants); KeePass is the most common secrets store on engineering workstations.
- Reused local-admin password (Mimikatz `sekurlsa::logonpasswords` or `lsadump::sam`).
- AD trust abuse / SID-history (`mitresidhistory`) when IT and OT domains have a one-way trust.

### Stage 5 — Engineering workstation (L3)

The engineering workstation holds:

- Vendor IDE: Studio 5000, TIA Portal, RSLogix 5000/500, PLCnext Engineer, Codesys IDE, CX-One.
- Project files (`.acd`, `.l5x`, `.ap14`/`.zap14`, `.ap13`, `.pro`, `.projectarchive`, `.s7p`) with full ladder logic, tag database, comments, and HMI graphics.
- Saved credentials for PLCs (often default vendor admin) in the project or a sidecar config.
- Direct routable access to L1 PLCs on Modbus/S7/EIP, often *without* further authentication once on the OT network.

OPSEC note: opening the vendor IDE on the engineering workstation looks identical to a maintenance engineer doing their job. Logic upload/download is one of the lowest-detection actions in the entire chain — provided AV/EDR doesn't flag the IDE binary.

### Stage 6 — PLC and process impact (L1/L0)

Three escalating outcomes, in order of safety risk:

1. **Read-only abuse**: dump PLC project, screenshot HMI, extract tag database; sufficient for many CTF/audit objectives and zero operational impact.
2. **Setpoint manipulation**: modify a threshold in `%M` / DB / holding-register space so the existing ladder produces an out-of-spec output (tank level threshold = 0 → pump never stops → overfill). The PLC executes its own logic against the corrupted setpoint, so to the operator nothing looks "hacked".
3. **Logic replacement**: upload a modified project that removes alarms, bypasses interlocks, or drives an actuator directly. High-impact, high-detection (logic-download events are visible in PCAP via S7 0x1A/0x1B/0x1F or CIP forward-open + write-tag traffic).

**Hard rule**: never touch SIS (Triconex/HIMA/GuardLogix) or anything reachable from the safety bus. The 2017 Triton incident is the boundary case — do not cross it.

## 3. Detection vs evasion model

The same arXiv:2511.17761 evaluation across Wazuh, Suricata, Vendor A EDR, and Vendor B NIDS shows where blind spots live and where to expect noise:

| Phase | Open-source HIDS (Wazuh) | Commercial EDR | NIDS (Suricata custom) | Commercial NIDS |
| --- | --- | --- | --- | --- |
| Responder / SMB relay | High FP, low TP | Low TP (non-domain attacker host) | Detects with ET rules | Variable |
| AS-REP / Kerberoast | Medium TP | Low TP | High TP if tuned | Medium |
| ADCS ESC1 | Low | Medium | High TP if tuned | Low |
| Logic download to PLC | None | None | None (no DPI for ICS) | Partial |
| Modbus FC 6/16 writes | None | None | None by default | None by default |

Practical implication: in IT/OT exercises with EDR coverage, *staying off the domain-joined assets* (operating from a Linux/Kali attacker host) and *moving credentials around without endpoint malware* keeps detection low. The detection cliff is on the *network* side: tune Suricata + Zeek for ICS protocols (`isc_modbus`, `s7comm`, `enip`) and most write traffic becomes visible.

11 of 32 techniques in that benchmark were not detected by any IDS configuration — every one was a credential or AD primitive, not a malware drop. The OT phase itself produced no IDS alert at all.

## 4. CTF/audit takeaways

- The flag is rarely at the PLC layer in isolation. Treat IT, OT-DMZ, and OT as one continuous chain and budget time accordingly: ~60 % IT/AD, ~25 % DMZ pivot, ~15 % PLC interaction.
- Default passwords reach OT via low-tech channels: photos on file shares, sticky notes in HMI screenshots, plant-tour PDFs in SharePoint. Always grep document corpora for `192.168.`, `admin`, `password`, `setup`, vendor product codes.
- Engineering workstations are the highest-value pivot per byte of effort. Project files + saved PLC credentials + IDE binaries are the entire OT attack surface in one host.
- Distinguish setpoint manipulation (low-detection, high-impact) from logic upload (visible in PCAP). Setpoint changes through legitimate Modbus FC 6/16 are indistinguishable from operator action without a side-channel.
- Operator-visible state is the oracle: HMI banner, alarm row, historian sample. See [signal-decoding-and-testing.md](signal-decoding-and-testing.md) for the verification loop and [attack-patterns.md](attack-patterns.md) for race-condition / FDI write patterns when the PLC fights back.
