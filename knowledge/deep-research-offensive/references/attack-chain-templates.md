# Attack Chain Templates

ATT&CK-aligned templates for red team planning and reporting. Load this file when mapping exploits to an attack chain or documenting a multi-stage intrusion scenario.

## Table of Contents

- [Generic Attack Chain Template](#generic-attack-chain-template)
- [Web Application Chain](#web-application-chain)
- [Network Service Chain](#network-service-chain)
- [Phishing / Initial Access Chain](#phishing--initial-access-chain)
- [Technique Documentation Block](#technique-documentation-block)

---

## Generic Attack Chain Template

```
## Attack Chain: [Scenario Name]

**Target**: [System / Application / Network segment]
**Engagement type**: [Lab / CTF / Authorized pentest / Red team]

### Phase 1 — Initial Access  (TA0001)
- Technique: T[ID] — [Name]
- CVE(s): CVE-YYYY-NNNNN
- Method: [1-2 sentences]
- Pre-condition: [What must be true for this to work]
- Tool/PoC: [URL or "manual"]

### Phase 2 — Execution  (TA0002)
- Technique: T[ID] — [Name]
- Method: [command or description]

### Phase 3 — Persistence  (TA0003)  [optional]
- Technique: T[ID] — [Name]
- Method: [registry / service / scheduled task / etc.]

### Phase 4 — Privilege Escalation  (TA0004)  [optional]
- Technique: T[ID] — [Name]
- CVE(s): [if applicable]
- Method: [description]

### Phase 5 — Defense Evasion  (TA0005)  [optional]
- Technique: T[ID] — [Name]
- Method: [AMSI bypass / AV evasion / log clearing / etc.]

### Phase 6 — Lateral Movement  (TA0008)  [optional]
- Technique: T[ID] — [Name]
- Method: [Pass-the-hash / Kerberoasting / SMB / etc.]

### Phase 7 — Collection / Exfiltration  (TA0009 / TA0010)
- Technique: T[ID] — [Name]
- Data targeted: [credentials / documents / DB / etc.]

### Objective
[What the attacker achieves at the end of this chain]

### Detection Opportunities
- [Log source / alert / artifact that would catch each phase]

### Mitigations
- [Patch / config / control that breaks the chain]
```

---

## Web Application Chain

Common template for web app exploitation scenarios.

```
Phase 1 — Recon
  T1592 - Gather Victim Host Information
  T1595 - Active Scanning (port scan, web crawl)

Phase 2 — Initial Access
  T1190 - Exploit Public-Facing Application
  [CVE or technique, e.g., SQLi, SSRF, deserialization]

Phase 3 — Execution
  T1059 - Command and Scripting Interpreter
  [Web shell / RCE via deserialization / template injection]

Phase 4 — Privilege Escalation
  T1068 - Exploitation for Privilege Escalation
  [SUID, sudo misconfiguration, kernel CVE]

Phase 5 — Collection
  T1005 - Data from Local System
  T1552 - Unsecured Credentials
```

---

## Network Service Chain

For exploitation of exposed network services (RDP, SSH, SMB, VPN, etc.).

```
Phase 1 — Discovery
  T1046 - Network Service Discovery
  T1595.002 - Vulnerability Scanning

Phase 2 — Initial Access
  T1190 - Exploit Public-Facing Application
  [CVE against the exposed service]

Phase 3 — Execution
  T1059 - Command and Scripting Interpreter
  [Bind shell / reverse shell / named pipe]

Phase 4 — Lateral Movement
  T1021 - Remote Services
  [SMB / WMI / RDP / SSH]

Phase 5 — Credential Access
  T1003 - OS Credential Dumping
  [LSASS / SAM / NTDS.dit]
```

---

## Phishing / Initial Access Chain

```
Phase 1 — Reconnaissance
  T1598 - Phishing for Information (LinkedIn, OSINT)

Phase 2 — Initial Access
  T1566 - Phishing
  [Spearphish with attachment / link / service]

Phase 3 — Execution
  T1204 - User Execution
  T1059 - Scripting (macro / LNK / HTA / ISO)

Phase 4 — Persistence
  T1547 - Boot/Logon Autostart
  T1053 - Scheduled Task

Phase 5 — C2
  T1071 - Application Layer Protocol (HTTP/S, DNS)
  T1132 - Data Encoding / Obfuscation
```

---

## Technique Documentation Block

Use this block for each individual technique in a report:

```
### T[ID] — [Technique Name]
- **Tactic**: [TA00XX — Tactic Name]
- **Sub-technique**: T[ID].[NNN] (if applicable)
- **CVE**: CVE-YYYY-NNNNN (if vulnerability-based)
- **CVSS**: X.X — [vector]
- **Pre-conditions**: [what must be true]
- **Steps**:
  1. [Step 1]
  2. [Step 2]
- **Expected output**: [shell / token / data / etc.]
- **Artifacts left**: [log entries, files, registry keys]
- **Detection**: [SIEM rule / EDR telemetry / network sig]
- **Mitigation**: [patch / config / compensating control]
- **References**: [advisory URL, PoC URL, ATT&CK URL]
```
