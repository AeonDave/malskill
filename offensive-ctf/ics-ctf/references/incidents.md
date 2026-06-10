# ICS/OT Incident Pattern Cards

Load when you need real-world OT attack chains, vendor/CVE landing pads, or recognizable incident patterns to map an artifact to a likely workflow. Use it as context for realistic modeling or recognition, not as a narrative incident digest.

## Threat-group → CTF-pivot mapping

Use these as "if the challenge looks like X, copy the real-world chain."

### VOLTZITE / Volt Typhoon (PRC, Dragos Stage 2 in 2025)

- Foothold: Sierra Wireless AirLink RV50/RV55 cellular gateways on midstream pipelines; F5 BIG-IP, Palo Alto GlobalProtect, Citrix VPN; KV Botnet of EoL Cisco/Netgear SOHO routers as relays.
- Lateral: pure LOTL — `netsh`, `wmic`, `ntdsutil`, PowerShell, AD Explorer, `PortProxy` registry mods. No custom malware.
- OT touch (new in 2025): pivot to engineering workstations, extract config + alarm data, investigate which conditions trigger process shutdowns.
- CTF flavor: edge-router/VPN box → IT subnet → engineering workstation with `.acd`/`.l5x`/`.ap1x` project files → tag/setpoint that maps to a flag-bearing process state. Hunt for `PortProxy` reg keys and `netsh interface portproxy` artifacts in given Windows triage data.

### SYLVANITE (Dragos 2026, new) — initial access broker for VOLTZITE

- TTP: weaponize Ivanti edge-device CVEs fast, extract AD creds, hand off to VOLTZITE within days.
- CTF flavor: Ivanti Connect Secure / EPM advisory → AD creds dump → IT-OT jump host. Stage 1 + Stage 2 split mirrors brokered/multi-team chained CTF scenarios.

### AZURITE (Dragos 2026, new) — Flax Typhoon overlap

- TTP: long-dwell interactive ops on engineering workstations; exfiltrates network diagrams, alarm data, process info; entry via VPN/edge devices and SOHO routers.
- CTF flavor: forensic image of an EWS containing TIA Portal/Studio 5000 project + alarm export; objective is recover process schematic, not move PLC state.

### PYROXENE (Dragos 2026, new) — IRGC-CEC overlap, UNC1549 ties

- TTP: supply-chain compromise of defense/aerospace suppliers + recruitment-themed social engineering (fake LinkedIn personas) → Azure-hosted C2 → indirect entry to primary target.
- CTF flavor: supplier mailbox → MSP RMM tool (Syncro, PDQ Connect) → downstream OT plant. Look for unsanctioned remote-access agents on EWS triage.

### KAMACITE + ELECTRUM (GRU / Sandworm ecosystem)

- KAMACITE (2024-2025): mapped US control loops Mar-Jul 2025 — HMIs, VFDs, metering modules, cellular gateways. Spear-phished GIE 2024 conference attendees; pivoted into European OT supply chain (CERT-UA UAC-0212 cluster, Feb-Mar 2025).
- ELECTRUM (Dec 2025): coordinated attack on Polish CHP + renewable energy management; multiple new wiper variants in 2025; eight Ukrainian ISPs hit in May 2025 (ESET "Dynowiper").
- FrostyGoop (Jan 2024, still referenced through 2025-2026): Modbus FC 6 writes flipped thermal setpoints, cut heating to 600+ buildings in Lviv mid-winter — small, surgical, devastating.
- CTF flavor: Modbus PCAP with isolated `func_code==6` writes to specific holding registers correlated with a temperature/level alarm spike. Recognize FrostyGoop pattern: low frame count, single-shot setpoint flip, no scan/enumeration noise.

### BAUXITE / CyberAv3ngers (IRGC-CEC, Storm-0784, US $10M bounty)

- Hallmark TTP: internet-exposed Unitronics PLCs on TCP/20256, default password `1111`, overwrite ladder logic, deface HMI, disable upload/download, force firmware downgrade. No CVE required.
- IOControl malware (Claroty Team82, Dec 2024): custom Linux backdoor with MQTT C2 (port 1883/8883), deployed on 400+ Unitronics + Orpak fuel-management devices globally.
- 2025 escalation: two custom wiper variants against Israeli OT (June 2025 Iran-Israel conflict). PLC_Controller.exe (July 2025) — compiled Python tool sending S7comm + COTP to force Siemens S7-300/400 into STOP mode; 45 % of S7 deployed are still those models. PowerShell `exploit.ps1` (Nov 2025) scanning Modbus holding registers above a threshold and overwriting them in a loop, paired with modified Slowloris/botnet DDoS.
- CTF flavor: Shodan-style intro → port 20256 Unitronics → default creds → ladder dump → flag in HMI string table or in a custom datablock. Or: Siemens S7-300 lab → COTP/S7comm STOP-mode trigger as a kill-switch puzzle. Mirror IOControl by giving an MQTT-over-TLS C2 channel from a "compromised" gauge.

### Handala Hack Team (MOIS-aligned, Tier 2 hacktivist)

- AutoIT/NSIS wiper packaged as vendor update; Telegram bot API for C2; mass-file-delete dressed as ransomware. Vendor-impersonation phishing, Starlink-IP scanning to bypass geo blocks. RustyWater RAT (CloudSEK Jan 2026, MuddyWater shared tooling) — Rust RAT, C2 via Dropbox/WordPress-look-alike domains.
- CTF flavor: triage Telegram-API outbound from an internal OT-adjacent host; reverse a Rust-RAT sample for C2 config; recover wiped-but-not-overwritten files from an `engineering workstation` image.

### APT33 / APT35 / MuddyWater (Iran nation-state)

- Tickler (2024) Azure-hosted multi-stage backdoor; `SharepointMain.exe` Run-key persistence; AnyDesk shadow installs on OT-adjacent workstations.
- PowGoop DLL side-load; POWERSTATS PowerShell backdoor; Small Sieve Telegram-API C2; Mori DNS-tunnel C2; ProxyShell on Exchange for Charming Kitten persistence.
- TRITON/TRISIS heritage (APT33, 2017) is still the only public ICS-SIS-malware reference — recognize Triconex/safety-PLC scenarios as APT33-flavored.

## Case study — CERT Polska "29 Dec 2025" destructive campaign (Static Tundra / Berserk Bear cluster, FSB Center 16)

Three coordinated wiper detonations against Polish critical infrastructure on the same day (CERT Polska Energy Sector Incident Report 2025). First publicly documented destructive operation attributed to the Static Tundra / Berserk Bear / Ghost Blizzard / Dragonfly cluster — historically a long-dwell espionage actor in energy/utilities. Useful as a CTF "post-mortem" archetype where the operator must reconstruct a multi-victim incident from disk + Windows event log + AD/GPO + FortiGate config artifacts.

### Victim set and payload per target

- **Renewable energy farm (windfarm)** — operator manually executed a wiper on a remotely-accessed SCADA HMI. Wiper itself was a thin .NET/Python stub overwriting `C:\` files with random bytes. No persistence, no C2; the goal was visible loss of process visibility, not destruction of the field devices.
- **Combined Heat and Power (CHP) plant** — bespoke C++ Windows wiper "DynoWiper" (CERT Polska naming, overlaps Dragos ELECTRUM "Dynowiper" used against 8 Ukrainian ISPs May 2025). Multi-threaded file enumeration, in-place overwrite with Mersenne Twister 19937 PRNG output (`std::mt19937`), seeded from `GetTickCount`. Skips Windows system directories to keep the host bootable until reboot. No persistence, no C2, no anti-analysis. Distributed at scale via Group Policy Object pushing a scheduled task to all domain-joined hosts.
- **Manufacturing OT-adjacent network** — "LazyWiper", a single PowerShell script written almost certainly by an LLM (CERT Polska assessment): polite English comments, `WriteRandomBytes` helper, `[System.Security.Cryptography.RandomNumberGenerator]`, `Get-ChildItem -Recurse` over drive roots. Same GPO + scheduled-task delivery as DynoWiper.

Common thread: **same operator, three wiper "tiers" matched to victim sophistication** — manual HMI execution at the simplest site, compiled C++ wiper at the CHP, PowerShell wiper at manufacturing. Distribution stage is the same (AD/GPO + `schtasks`/Scheduled Task XML), payload tier varies.

### Long-dwell pre-positioning chain (Mar-Dec 2025)

CERT Polska reconstructed ~9 months of activity at the CHP victim that preceded the 29 Dec detonation. This is the chain to mirror in a CTF "incident reconstruction" forensic challenge:

1. **Initial access**: FortiGate SSL-VPN, valid credentials (no CVE used in the documented intrusions; assumed cred reuse / earlier theft). All operator activity sourced from Tor exit nodes.
2. **Foothold**: pivot to a single internet-facing jump host, then PsExec into the rest of the network. No custom malware on the foothold — pure LOTL.
3. **Recon**: `nircmd` to take desktop screenshots of operator workstations. Heavy interest in any hostname containing `SCADA`, `DCS`, `HIST`, `EWS`. Browser launched as `msedge.exe --inprivate` to avoid history; downloads from Dropbox and Pastebin-style paste sites for tool staging.
4. **Credential access**:
   - Rubeus **Diamond Ticket** (not Golden) — forge a TGT that inherits a real account's PAC, harder to detect than Golden Ticket because the krbtgt-encrypted portion is sourced from a real authentication.
   - `ntdsutil` "ifm" snapshot of `ntds.dit` via `vssadmin create shadow`.
   - `procdump`-style LSASS dump (image-load of `comsvcs.dll` MiniDump export).
   - `certutil -encode` to base64-pack staged archives before exfil.
5. **Persistence and tunneling**:
   - `rsocx` reverse SOCKS proxy compiled for Windows, beaconing back to actor infrastructure for interactive access without needing the VPN.
   - FortiGate **configuration theft + scripted persistence**: pulled the full config, added their own admin user and a CLI script that re-creates the user if removed; data exfil mirrored to a Slack-hosted webhook.
6. **Destruction stage (29 Dec 2025)**:
   - GPO pushed a Scheduled Task XML to every domain-joined host running the wiper as `SYSTEM` at a synchronized time.
   - After file overwrite, a second stage booted **Tiny Core Linux** from a KVM/iLO/IPMI-attached ISO and ran `dd if=/dev/zero of=/dev/sdX` over the underlying RAID members, then reconfigured **Intel RST** to drop the RAID definition. Net effect: even a wipe-resistant Windows file system was followed by raw-disk destruction and array metadata loss, requiring full bare-metal rebuild.

### CTF pivots from this case

- "FortiGate SSL-VPN log + Tor exit IP + jump host + PsExec + nircmd screenshots" → Static Tundra/Berserk Bear pre-positioning. The flag is usually in the FortiGate config diff (added admin) or in the LSASS-derived NTLM hash that unlocks the next AD account.
- "Mersenne Twister overwrite + GPO + Scheduled Task + no C2 + no persistence" → DynoWiper. Recovery is impossible from the disk itself; lateral evidence lives in the GPO version history and `Microsoft-Windows-TaskScheduler/Operational` (event ID 106 task registration, 200 task execution).
- "PowerShell with `WriteRandomBytes` + `RandomNumberGenerator` + LLM-style comments + GPO delivery" → LazyWiper. The give-away in a triage challenge is the AmsiScanBuffer log + PowerShell ScriptBlock log (event 4104) showing the full overly-commented script.
- "Diamond Ticket in event 4769 service ticket request without preceding TGT request (4768)" → Rubeus Diamond Ticket forge. The Kerberos ticket structure carries the inconsistency.
- "iLO/IPMI session + Tiny Core ISO mount + `dd` of `/dev/sdX` + Intel RST metadata gone" → out-of-band destruction stage. Disk forensics on the wiped Windows partition is a red herring; pivot to the iLO/IPMI logs for the real attribution evidence.

### Recognition checklist for "Static Tundra/Berserk Bear" CTF flavor

- FortiGate + Tor + interactive jump host (no implants on the entry point).
- Heavy use of `nircmd` for screenshots.
- Diamond Ticket (Rubeus, not Mimikatz Golden).
- Edge `--inprivate` + Dropbox/Pastebin staging.
- `rsocx` reverse SOCKS proxy.
- GPO-distributed Scheduled Task as the deployment vector for the final payload.
- Two-tier destruction: file-system wipe followed by out-of-band raw-disk wipe via iLO/IPMI/KVM-mounted Linux live ISO.
- Pre-positioning measured in months, action-on-objective in minutes.

## Landmark incident technique cards — CTF playbook

Per-incident "fingerprint → CTF pivot" cards. Each card lists the **protocol/tech**, **CVEs**, **signature TTP**, and **how to recognize/reproduce in a challenge**. Designed to be copy-paste scaffolding when an artifact pattern matches.

### Stuxnet (2010, Equation/Tilded) — first PLC rootkit

- Tech: Siemens S7-315-2 / S7-417, Step7 / WinCC on Windows, Profibus to Vacon/Fararo Paya VFDs at 807-1210 Hz.
- CVEs chained: `CVE-2010-2568` (LNK icon RCE), `CVE-2010-2729` (Print Spooler), `CVE-2010-2743` (Win32k kbd layout LPE), `CVE-2008-4250` (MS08-067), Step7 `s7otbxdx.dll` DLL hijack (no CVE, design abuse).
- Signature TTP: `s7otbxdx.dll` MITM between Step7 IDE and PLC — operator reads "clean" ladder while infected OB1/OB35 runs; payload only fires if matching CPU + DB890 pattern (Natanz fingerprint).
- CTF pivot: given a Step7 project + a CPU memory dump where uploaded blocks differ from on-PLC blocks → Stuxnet-style "PLC rootkit"; the flag is the discrepancy or the hidden OB.

### Industroyer / CRASHOVERRIDE (Dec 2016, Sandworm, Kyiv Pivnichna)

- Tech: IEC 60870-5-101 (serial), IEC 60870-5-104 (TCP/2404), IEC 61850 MMS (TCP/102), OPC DA.
- CVE weaponized as wiper finisher: `CVE-2015-5374` (Siemens SIPROTEC 4 EN100 DoS, UDP/50000 special packet).
- Signature TTP: modular framework — protocol payloads enumerate RTU IOAs then issue open-breaker commands in a loop; cleanup wiper overwrites `ImagePath` registry of services + zeroes ICS config files.
- CTF pivot: PCAP with IEC-104 `C_SC_NA_1` (single-command, type ID 45) or `C_DC_NA_1` (double-command, type ID 46) sent to every IOA in a CASDU → Industroyer enumeration. Flag in the IOA whose command parameter (`SCO`/`DCO`) was set to `ON→OFF` last.

### Industroyer2 (Apr 2022, Sandworm, attempted on Ukraine substation)

- Tech: hardcoded IEC-104 target table compiled into single Windows binary (no config file, unlike v1).
- Companion wipers: **CaddyWiper** (Windows), **OrcShred/SoloShred/AwfulShred** (Linux/Solaris on RTUs).
- Signature TTP: single-shot binary launched via GPO at scheduled detonation, then CaddyWiper cleanup; Sandworm's preferred 2022+ pattern.
- CTF pivot: a Windows binary with embedded IP:2404 + ASDU/IOA list as data section → reverse-engineer the target table to recover the substation map; flag often in IOA → device-name mapping.

### TRITON / TRISIS / HatMan (Aug 2017, XENOTIME/APT33, Saudi Aramco-adjacent petchem)

- Tech: Schneider Triconex SIS, Tristation protocol over UDP/1502; firmware `tr_sx.bin` for MP3008 main processor; required key-switch in PROGRAM mode.
- Files: `trilog.exe` (writer), `library.zip` (Python TS framework reimplementation), `imain.bin` (SIS payload), `inject.bin` (loader).
- Signature TTP: deliberately attacks **safety**, not control — degrade SIS so a follow-on process attack can cause physical harm; crashed the SIS instead, which forced safe shutdown and revealed the campaign.
- CTF pivot: UDP/1502 PCAP + a binary that wraps Tristation type-3 messages writing to firmware regions → TRITON. The flag often hides in the embedded shellcode targeting the MP3008 PowerPC.

### PIPEDREAM / INCONTROLLER (Apr 2022, CHERNOVITE, never deployed in wild, CISA AA22-103A)

- Toolkit:
  - **EVILSCHOLAR** — Codesys v3 + ENIP scanner/manipulator, targets Schneider Modicon M340/M580 over `TCP/1740-3` and `TCP/11740`.
  - **BADOMEN** — OMRON NJ/NX over FINS (`UDP/9600`, HTTP Sysmac Studio API), uploads custom agents.
  - **MOUSEHOLE** — generic OPC UA client (port 4840) that browses + writes any node.
  - **DUSTPAN** — Modbus over TCP/502 enum + write.
  - **LAZYCARGO** — `AsrDrv101.sys` ASRock driver (`CVE-2020-15368`) for Windows kernel access on the engineering workstation.
- CTF pivot: any OPC UA `WriteValue` flood, FINS `Memory Area Write` (cmd code `0102`), or unauthenticated UMAS write to a Modicon → PIPEDREAM family. Recognize MOUSEHOLE by sequential `Browse` → `Read` → `Write` on every node in `ns=2`.

### BlackEnergy3 + KillDisk (Dec 2015, Sandworm, Prykarpattyaoblenergo — first confirmed grid blackout)

- Tech: BE3 with KillDisk plugin; HMI firmware wipe on serial-to-Ethernet converters (Moxa/General Electric); UPS firmware wipe to extend outage; telephone DoS against call center.
- Signature TTP: human-in-the-loop — operator manually opened breakers via stolen HMI session, BlackEnergy was just the access vector.
- CTF pivot: triage `.xls` macro + `Dropbear` SSH backdoor on serial converters + bricked Moxa → BlackEnergy3. Flag often in the recovered KillDisk config (component list).

### Maroochy Shire (2000, Vitek Boden, AU sewage release)

- Tech: insider with stolen radio + laptop; proprietary Pakscan radio telemetry to 142 pump stations.
- Signature TTP: 46 separate intrusions over months; spoofed station IDs to send STOP/START to pumps; first widely-documented OT attack.
- CTF pivot: RF/SDR-captured packet stream with repeated station-ID spoof to a pump controller → Maroochy archetype. Flag usually a specific station ID + command sequence.

### Oldsmar water (Feb 2021, FL, TeamViewer abuse — never attributed)

- Tech: shared TeamViewer credentials on HMI; operator-set NaOH (sodium hydroxide) setpoint moved from **100 ppm → 11,100 ppm** before live operator noticed.
- Signature TTP: not malware — credential reuse + remote access tool no longer in active use but still installed.
- CTF pivot: HMI screenshot + Windows event log with `TeamViewer_Service` connection from foreign IP + setpoint history showing a 111× jump on one tag → Oldsmar archetype. The flag is the tag name + value.

### Aliquippa / Muleshoe / Abernathy water (Nov 2023, CyberAv3ngers/IRGC-CEC, CISA AA23-335A)

- Tech: Unitronics Vision230/Samba PLCs internet-exposed on **TCP/20256** (PCOM protocol), factory default password `1111`.
- Signature TTP: PCOM "Set Display Message" + ladder overwrite + HMI defacement ("You have been hacked — down with Israel"). No CVE; pure default-cred + exposure.
- CTF pivot: PCAP with PCOM frames (`/_OPLC` header), or a Shodan/Censys query result containing `Unitronics PCOM` banner → CyberAv3ngers Path-1 archetype. Flag is HMI string table or the ladder rung that flips a pressure setpoint.

### Colonial Pipeline (May 2021, DarkSide RaaS affiliate)

- Tech: legacy Citrix/SonicWall VPN account, no MFA, single password reused — recovered from a credential dump.
- Signature TTP: pure IT-side ransomware on the billing/SCADA-adjacent network → operator chose to shut OT side defensively (OT itself was not encrypted).
- CTF pivot: forensic challenge where shutdown narrative blames OT impact but evidence points to billing/IT encryption only → Colonial archetype. Flag in the credential dump line that matched the VPN account.

### JBS Foods (May 2021, REvil)

- Tech: ransomware against ERP/IT; plants halted because operators could not dispatch orders.
- Signature TTP: same Colonial pattern — IT-only encryption forces OT downtime via operational dependence.
- CTF pivot: REvil ransom note `readme-{ext}.txt` + AD-wide encryption + manufacturing operational halt narrative → JBS-class archetype.

### Norsk Hydro (Mar 2019, LockerGoga)

- Tech: LockerGoga delivered via AD; smelter plants forced to manual control; recovery documented openly.
- Signature TTP: privileges escalated via stolen domain admin + `psexec`-style spread; ICS impact = downtime + manual operation, not direct OT manipulation.
- CTF pivot: AD environment + LockerGoga binary (PowerPC-style code reuse, embedded RSA pubkey) + manual-mode aluminum smelter story → Norsk Hydro archetype.

### FrostyGoop / Sandworm Lviv heating (Jan 2024, public Jul 2024, ENCO controllers)

- Tech: cross-platform Go malware; Modbus TCP/502, **Function Code 6 (Write Single Holding Register)** to ENCO controllers; ~600 buildings lost heat for two days mid-winter.
- Signature TTP: `JSON` task file fed to FrostyGoop describes target IP + register + value; no scan/enum, surgical single-shot writes.
- CTF pivot: tiny Modbus PCAP with only FC 6 writes to one or two registers, no FC 1/3/4 reads → FrostyGoop. Flag in the register value (often setpoint expressed in °C×10).

### Predatory Sparrow — Khouzestan steel mills (Jun 2022, Iran)

- Tech: SCADA → Siemens S7 → induction furnace; molten-metal spill broadcast on video; second campaign hit Iranian gas-station payment system (Dec 2023) — modified HMI defacement + ATG payment controller bricking.
- Signature TTP: high-quality OPSEC pre-staging + intentionally released video of physical effect; AKA "Gonjeshke Darande". Likely Israeli-aligned counterpart to CyberAv3ngers.
- CTF pivot: HMI screenshot/video + S7comm STOP/MODE-change + post-incident Telegram channel claim → Predatory Sparrow archetype.

### Ukrenergo Industroyer2 attempt (Apr 2022) + Snake Island UAC-0212 (2025)

- Tech: GPO-pushed wiper at synchronized time; OT-supply-chain spear-phish into Western OT vendors who service Ukrainian sites.
- Signature TTP: pivot through OT-vendor mailbox/RMM (`Syncro`, `PDQ Connect`, AnyDesk) into customer plant.
- CTF pivot: mailbox triage finding RMM-install email + unsanctioned agent on EWS → Snake Island / KAMACITE supplier-pivot archetype.

### Rockwell ControlLogix / Logix advisory (Jul 2023, CVE-2023-3595 + CVE-2023-3596)

- Tech: 1756-EN2T / 1756-EN3TR / 1756-EN4TR comms modules; CIP message crafted to overflow heap on the module → arbitrary code on the comms processor.
- CVEs: `CVE-2023-3595` (RCE on comms module, attributed to nation-state research), `CVE-2023-3596` (DoS).
- Signature TTP: unsigned CIP write to `Class 0x32` services on TCP/44818; persists across reboot via firmware write.
- CTF pivot: ENIP/CIP PCAP with malformed `Forward Open` + oversized config assembly → ControlLogix CVE-2023-3595 family. Tied to Dragos "FORLINX" research.

### Schneider Modicon UMAS auth bypass (CVE-2018-7842, CVE-2021-22779, CVE-2021-22785)

- Tech: UMAS over Modbus TCP/502, function code `0x5A`; missing/forgeable session key allows project upload/download and run/stop without auth.
- Signature TTP: UMAS `0x5A` `0x40` (Take PLC Reservation) → `0x29` (Read Memory) / `0x2A` (Write Memory); used by EVILSCHOLAR (PIPEDREAM).
- CTF pivot: Modbus PCAP with `0x5A` UMAS sub-function leading to memory writes → Modicon UMAS abuse. Flag often in the project metadata uploaded after the reservation.

### Codesys runtime CVE cluster (CVE-2022-47379…47393, "Codesys 15")

- Tech: Codesys Control Runtime on every vendor that OEMs it (Wago, ABB, Beckhoff, Schneider, Bosch Rexroth, Festo, Eaton). Service `CmpBlkDrvTcp` on **TCP/11740**.
- Signature TTP: pre-auth heap overflow + path traversal + auth bypass; lets an attacker upload IEC 61131-3 application and become "the program".
- CTF pivot: TCP/11740 banner + a binary calling `CmpAppForceLoad` → Codesys runtime exploit chain. Tied to CHERNOVITE EVILSCHOLAR.

### OPC UA recent bugs (CVE-2022-21208 .NET stack RCE; CVE-2023-29569 open62541)

- Tech: OPC UA TCP/4840 or TLS 4843; abused via certificate/handshake parsing flaws.
- Signature TTP: malformed `OpenSecureChannel` or certificate chain triggers parser bug; CHERNOVITE MOUSEHOLE relies on legitimate auth rather than CVEs but the same port surfaces both.
- CTF pivot: 4840 capture with abnormal `MessageChunk` sizes or a certificate with crafted `subjectAltName` → OPC UA stack exploit.

### Moxa NPort serial-to-Ethernet hardcoded creds (CVE-2016-9361, CVE-2019-5136-39)

- Tech: NPort 5110/5130/5150 series, telnet/SSH `admin//moxa` defaults, web UI XSS + cmd-inject.
- Signature TTP: classic BlackEnergy3 finisher path — wipe firmware over Telnet to brick serial converters.
- CTF pivot: device fingerprint with `MOXA NPort` banner + bricked-after-reset story → BlackEnergy/Industroyer family.

### CODESYS / Wago / GE Mark VIe (TRITON-adjacent)

- Tech: GE Mark VIe gas-turbine controller; UDP/5311; XENOTIME also studied this platform post-TRITON.
- CTF pivot: GE Mark VIe project archive + 5311 PCAP → XENOTIME pivot from SIS to BPCS.

### Volt Typhoon "KV-Botnet" (2023-2024, CISA AA24-038A)

- Tech: Cisco RV320/325, Netgear ProSAFE, DrayTek Vigor, Axis IP cams — EoL SOHO devices repurposed as proxy mesh.
- Signature TTP: `chmod 755` of a small JA3-fingerprint-matched payload; relay traffic from real victim hops; no implants left on the target enterprise (LOTL only).
- CTF pivot: triage shows outbound to a residential US IP that itself fronts EoL Cisco firmware → VOLTZITE / KV-Botnet hop chain.



- **Unitronics Vision/Samba PLCs** — default 1111 on TCP/20256 (CISA AA23-335A). Reference CTF for Path-1 direct-exposure scenarios.
- **Sierra Wireless AirLink RV50/RV55** — web UI compromise, used by VOLTZITE on midstream pipelines.
- **Ivanti Connect Secure / EPM** — SYLVANITE's preferred initial-access surface.
- **Trimble Cityworks (Q1 2025 RCE)** — unsafe deserialization on IIS, no-auth code exec; JoJoLoader + Cobalt Strike post-ex; theft of GIS asset maps. Recognize when a challenge gives a Cityworks/GIS server bundle.
- **Battery Energy Storage Systems (Dragos 2025 research)** — auth-bypass + command-injection across ~1 MW inverters; >100 internet-exposed; new attack surface for grid-tied storage CTFs.
- **Sophos firewalls** — exploited in BAUXITE pre-positioning.
- **Siemens S7-300/400** — COTP/S7comm STOP-mode via `PLC_Controller.exe` style tools (45 % install base on legacy CPUs).
- **Automatic Tank Gauge (ATG) systems** — May 2026 US probe into ATG breaches; revisit OPSwat/Veeder-Root TLS protocol exposures on port 10001.
- **Mosquitto** (CVE-2017-7650 ACL pattern bypass, CVE-2024-3935 TLS DoS), EMQX/HiveMQ/VerneMQ banner-cross-ref via `$SYS/broker/version`.

## Attack-path templates (Dragos / CloudSEK three-paths model)

Use the templates as scaffold for either solving or designing a chain:

### Path 1 — Direct exposure (CyberAv3ngers archetype)

1. Shodan/Censys query for vendor-specific port (`port:20256`, `port:502`, `port:44818`, `port:47808`, `port:4840`, `port:20000`, `port:5900`).
2. Default cred login (Unitronics 1111, Codesys factory, OpenPLC `openplc/openplc`).
3. Read full ladder/STL; overwrite a coil/setpoint; disable upload/download; downgrade firmware.
4. Verify via HMI banner change, historian alarm, or read-back from a second master.

### Path 2 — Phishing into OT-adjacent (APT33/MuddyWater/Handala)

1. Spear-phish SCADA engineer or vendor account → macro/HTA/LNK loader (Tickler, Small Sieve, RustyWater).
2. Pivot to engineering workstation; abuse Syncro/PDQ Connect/AnyDesk if present.
3. Steal project archive (`.zap1x`, `.acd`, `.s7p`) and saved PLC creds; reuse against the live PLC.
4. Disrupt or stage; persist on EWS for reactivation.

### Path 3 — IT infiltration + lateral to OT (VOLTZITE/SYLVANITE)

1. Edge-device exploitation (Ivanti, Fortinet, Citrix, Sierra Wireless) or VPN cred reuse.
2. AD recon with AD Explorer; `ntdsutil` for NTDS dump; `PortProxy` for tunnel.
3. Find OT DMZ / IT-OT boundary; jump to historian, jump server, or engineering workstation.
4. On EWS: pull project, identify the control loop, study OB1/ladder for the safety-vs-process inflection point; stage but do not detonate.

## CTF design / recognition cheats

- "Default password 1111 on port 20256" or "exposed PCOM PLC" → CyberAv3ngers/BAUXITE archetype.
- Single Modbus FC 6 write that flips a temperature/heating register → FrostyGoop archetype.
- COTP+S7comm session that pushes the PLC to STOP without uploading new ladder → BAUXITE 2025 `PLC_Controller.exe` archetype.
- PowerShell that loops "scan holding registers, compare > N, overwrite" → BAUXITE Nov 2025 `exploit.ps1` archetype.
- `.zap1x`/`.ap1x` archive + HMI tag CSV + offline PLCSim Advanced challenge → AZURITE / engineering-workstation exfil archetype.
- Sierra Wireless AirLink or any cellular-gateway web UI as the only ingress to an OT range → VOLTZITE archetype; expect LOTL artifacts (no custom malware) in triage data.
- Cityworks/GIS RCE bundle → KAMACITE/VOLTZITE-adjacent prepositioning; flag will be in mapped asset metadata, not in a shell.
- Ransomware on a "Windows server" that is actually a SCADA host or historian → Dragos's "misclassified as IT" pattern; the flag-bearing impact is usually OT downtime narrative, not file decryption.

## Defender pivots to mirror in CTF writeups

- Block at perimeter (and as a hint in misc/forensic challenges): TCP 20256, 102, 502, 44818, 1911, 4840, 20000; UDP 47808.
- Hunt for: `netsh interface portproxy`, `wmic`, `ntdsutil`, AD Explorer artifacts in OT-adjacent Windows triage; `SharepointMain.exe` Run keys (Tickler); Syncro/PDQ/AnyDesk installs without IT ticketing; Telegram-API outbound; high-entropy DNS subdomains (Mori); MQTT 1883/8883 outbound from a non-broker host.
- OT visibility maturity → 5 vs 42 day dwell (Dragos) is the most repeatable defender talking point.

## Curated sources (2025-2026)

- Dragos 2026 OT/ICS Year in Review (9th annual) — <https://www.dragos.com/ot-cybersecurity-year-in-review> and <https://www.dragos.com/resources/press-release/dragos-2026-year-in-review-new-ot-threats-ransomware>
- Dragos 2025 OT/ICS Year in Review (8th annual) — <https://pkcert.gov.pk/uploads/2025/02/Dragos-2025-OT-Cybersecurity-Report-A-Year-in-Review.pdf>
- Industrial Cyber summary (Feb 2026) — <https://industrialcyber.co/reports/dragos-tracks-three-new-ot-threat-groups-as-industrial-adversaries-move-toward-real-world-disruption/>
- CloudSEK 2026 Iran-US ICS/OT threat-actor landscape — <https://www.cloudsek.com/blog/a-threat-actor-landscape-assessment-of-ics-ot-targeting-in-the-2026-iran-us-conflict-and-the-scale-of-the-risk>
- CERT Polska Energy Sector Incident Report 2025 (29 Dec 2025 destructive campaign, Static Tundra / Berserk Bear / Ghost Blizzard / Dragonfly attribution, DynoWiper + LazyWiper analysis) — <https://cert.pl/uploads/docs/CERT_Polska_Energy_Sector_Incident_Report_2025.pdf>
- CISA AA23-335A (Unitronics) — <https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-335a>
- CISA AA24-038A (Volt Typhoon) — <https://www.cisa.gov/news-events/cybersecurity-advisories/aa24-038a>
- CISA AA22-055A (MuddyWater) — <https://www.cisa.gov/news-events/cybersecurity-advisories/aa22-055a>
- CISA AA22-103A (PIPEDREAM / INCONTROLLER) — <https://www.cisa.gov/news-events/cybersecurity-advisories/aa22-103a>
- Claroty Team82 IOCONTROL analysis (Dec 2024) — <https://claroty.com/team82>
- Waterfall Security 2025 OT Threat Report — <https://waterfall-security.com/wp-content/uploads/2025/03/threat-report-2025-S.pdf>
- OPSWAT ICS/OT Threat Landscape 2024-2026 — <https://www.opswat.com/blog/every-ot-breach-has-a-file-in-its-attack-chain-the-ics-ot-threat-landscape-2024-2026>
- Forescout Research Labs (Jun 2025) — internet-exposed OT/ICS counts.
- MITRE ATT&CK ICS — <https://attack.mitre.org/matrices/ics/>
