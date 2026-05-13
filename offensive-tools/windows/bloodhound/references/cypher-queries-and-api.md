# BloodHound — Deep Reference

## Cypher Query Fundamentals

BloodHound uses Neo4j's Cypher query language. Understanding the graph model enables custom analysis.

### Node Types (labels)

| Label | Description |
|-------|-------------|
| `User` | AD user accounts |
| `Computer` | Machine accounts |
| `Group` | Security/distribution groups |
| `Domain` | AD domain root |
| `OU` | Organizational unit |
| `GPO` | Group Policy Object |
| `Container` | AD container objects |

### Edge Types (relationships)

| Edge | Meaning |
|------|---------|
| `MemberOf` | Group membership |
| `AdminTo` | Local admin on computer |
| `HasSession` | Active user session on computer |
| `CanRDP` | RDP access to computer |
| `GenericAll` | Full control over object |
| `GenericWrite` | Write any property |
| `WriteOwner` | Can change object owner |
| `WriteDacl` | Can modify DACL |
| `AllExtendedRights` | All extended rights (includes ForceChangePassword, etc.) |
| `ForceChangePassword` | Change password without knowing current |
| `Owns` | Is owner of object |
| `AddMember` | Can add members to group |
| `AddSelf` | Can add self to group |
| `CanPSRemote` | PowerShell remoting access |
| `ExecuteDCOM` | DCOM execution on computer |
| `AllowedToDelegate` | Constrained delegation |
| `AllowedToAct` | RBCD — allowed to act on behalf of |
| `GetChanges` + `GetChangesAll` | DCSync rights |
| `TrustedBy` | Domain trust direction |
| `Contains` | OU/container hierarchy |
| `GpLink` | GPO linked to OU/domain |
| `AffectedBy` | Object affected by GPO |

---

## Extended Cypher Query Library

### Attack Path Queries

```cypher
// Shortest path from Domain Users to DA (any edge type)
MATCH p=shortestPath(
  (g:Group {name:"DOMAIN USERS@CORP.LOCAL"})-[*1..]->(u:User {name:"ADMINISTRATOR@CORP.LOCAL"})
) RETURN p

// All shortest paths to Domain Admin (not just one)
MATCH p=allShortestPaths(
  (g:Group {name:"DOMAIN USERS@CORP.LOCAL"})-[*1..]->(da:Group {name:"DOMAIN ADMINS@CORP.LOCAL"})
) RETURN p

// Path from owned objects to DA (after marking owned)
MATCH p=shortestPath((u {owned:true})-[*1..]->(da:Group {name:"DOMAIN ADMINS@CORP.LOCAL"}))
RETURN p

// Transitive path to a specific computer
MATCH p=shortestPath(
  (g:Group {name:"DOMAIN USERS@CORP.LOCAL"})-[*1..]->(c:Computer {name:"FILESERVER.CORP.LOCAL"})
) RETURN p

// All paths to DA — see every route (can be slow)
MATCH p=(g:Group {name:"DOMAIN USERS@CORP.LOCAL"})-[*1..5]->(da:Group {name:"DOMAIN ADMINS@CORP.LOCAL"})
RETURN p LIMIT 25
```

### ACL Abuse Queries

```cypher
// Who has GenericAll or GenericWrite over DA group?
MATCH (n)-[r:GenericAll|GenericWrite|WriteDacl|WriteOwner|Owns]->(g:Group {name:"DOMAIN ADMINS@CORP.LOCAL"})
RETURN n.name, type(r)

// All ACL edges from non-admin users to high-value targets
MATCH (u:User)-[r:GenericAll|GenericWrite|WriteDacl|WriteOwner|AddMember|AddSelf|ForceChangePassword]->
      (target {highvalue:true})
WHERE NOT u.admincount = true
RETURN u.name, type(r), target.name, labels(target)

// WriteOwner → WriteDacl escalation paths
MATCH p=(u:User)-[:WriteOwner|WriteDacl]->(t)
WHERE NOT u.admincount = true
RETURN u.name, labels(t), t.name

// ForceChangePassword: who can reset whose password?
MATCH (u:User)-[:ForceChangePassword]->(v:User)
RETURN u.name AS attacker, v.name AS victim
ORDER BY v.name

// GenericWrite on computer (shadow creds / RBCD vector)
MATCH (u:User)-[:GenericWrite]->(c:Computer)
WHERE NOT u.admincount = true
RETURN u.name AS user, c.name AS computer
```

### Session + Lateral Movement Queries

```cypher
// Where is DA currently logged in?
MATCH (da:User)-[:MemberOf*1..]->(g:Group {name:"DOMAIN ADMINS@CORP.LOCAL"})
MATCH (da)-[:HasSession]->(c:Computer)
RETURN da.name AS DA, c.name AS LoggedOnTo

// Computers where ANY Domain Admin has a session
MATCH (g:Group {name:"DOMAIN ADMINS@CORP.LOCAL"})<-[:MemberOf*1..]-(da:User)-[:HasSession]->(c:Computer)
RETURN c.name, collect(da.name) AS DAsLoggedOn

// Computers where we (local admin) can reach a DA session
MATCH p=(owned:User {owned:true})-[:AdminTo]->(c:Computer)<-[:HasSession]-(da:User)
MATCH (da)-[:MemberOf*1..]->(g:Group {name:"DOMAIN ADMINS@CORP.LOCAL"})
RETURN owned.name, c.name, da.name

// All local admin paths from owned users
MATCH p=shortestPath((u {owned:true})-[*1..]->(c:Computer))
WHERE any(r in relationships(p) WHERE type(r)="AdminTo")
RETURN p LIMIT 20
```

### Kerberos Attack Queries

```cypher
// All Kerberoastable users + their group memberships
MATCH (u:User {hasspn:true}) WHERE NOT u.name STARTS WITH "KRBTGT"
OPTIONAL MATCH (u)-[:MemberOf*1..]->(g:Group)
RETURN u.name, u.description, collect(g.name) AS groups
ORDER BY size(collect(g.name)) DESC

// High-value Kerberoastable (admin or sensitive groups)
MATCH (u:User {hasspn:true, admincount:true})
WHERE NOT u.name STARTS WITH "KRBTGT"
RETURN u.name, u.description

// AS-REP roastable users
MATCH (u:User {dontreqpreauth:true})
RETURN u.name, u.description

// Unconstrained delegation computers (non-DCs)
MATCH (c:Computer {unconstraineddelegation:true})
WHERE NOT c.name ENDS WITH "DC" AND NOT c.name STARTS WITH "DC"
RETURN c.name, c.operatingsystem

// Constrained delegation — what can they delegate to?
MATCH (n)-[:AllowedToDelegate]->(c:Computer)
RETURN n.name, n.objectid, collect(c.name) AS allowed_targets
ORDER BY size(collect(c.name)) DESC

// RBCD edges
MATCH (n)-[:AllowedToAct]->(c:Computer)
RETURN n.name AS controller, c.name AS target
```

### Domain Trust Queries

```cypher
// All trust relationships
MATCH p=(d:Domain)-[:TrustedBy]->(t:Domain)
RETURN d.name AS trusts, t.name AS trusted_by

// Trust paths to forest root
MATCH p=(child:Domain)-[:TrustedBy*1..]->(root:Domain)
WHERE NOT (root)-[:TrustedBy]->()
RETURN p

// Cross-domain admin paths
MATCH p=shortestPath(
  (u:User {domain:"CHILD.CORP.LOCAL"})-[*1..]->(da:Group {name:"DOMAIN ADMINS@PARENT.CORP.LOCAL"})
) RETURN p
```

### GPO Queries

```cypher
// GPOs affecting Domain Admins group
MATCH (g:Group {name:"DOMAIN ADMINS@CORP.LOCAL"})<-[:AffectedBy*1..]-(gpo:GPO)
RETURN gpo.name, gpo.objectid

// Who has control over GPOs that affect DCs?
MATCH (c:Computer {isdc:true})<-[:AffectedBy*1..]-(gpo:GPO)<-[:GenericAll|WriteDacl|GenericWrite]-(u:User)
RETURN u.name AS attacker, gpo.name AS via_gpo, c.name AS target_dc
```

### Privileged Access Queries (PSRemote, SQLAdmin, RDP, DCOM)

```cypher
// Users who can PSRemote (WinRM) into computers
MATCH (u:User)-[:CanPSRemote]->(c:Computer)
RETURN u.name, c.name

// CanPSRemote via group membership (indirect paths)
MATCH p=(g:Group)-[:CanPSRemote]->(c:Computer)
MATCH (u:User)-[:MemberOf*1..]->(g)
RETURN u.name, g.name AS via_group, c.name

// SQL Admin paths (MSSQL lateral movement)
MATCH (u:User)-[:SQLAdmin]->(c:Computer)
RETURN u.name, c.name

// SQLAdmin via group membership
MATCH p=(g:Group)-[:SQLAdmin]->(c:Computer)
MATCH (u:User)-[:MemberOf*1..]->(g)
RETURN u.name, g.name AS via_group, c.name

// RDP access from non-privileged users
MATCH (u:User)-[:CanRDP]->(c:Computer)
WHERE NOT u.admincount = true
RETURN u.name, c.name

// DCOM execution paths
MATCH (u:User)-[:ExecuteDCOM]->(c:Computer)
RETURN u.name, c.name

// All lateral movement edges from owned principals
MATCH (u {owned:true})-[r:AdminTo|CanPSRemote|CanRDP|ExecuteDCOM|SQLAdmin]->(c:Computer)
RETURN u.name, type(r), c.name
```

### Foreign Group Members

```cypher
// Users from external/child domains in local groups
MATCH (n)-[:MemberOf]->(g:Group)
WHERE n.domain <> g.domain
RETURN n.name, n.domain AS from_domain, g.name, g.domain AS in_domain

// External principals with admin access
MATCH (n)-[:AdminTo]->(c:Computer)
WHERE n.domain <> c.domain
RETURN n.name, n.domain, c.name, c.domain

// SID History abuse paths (cross-domain)
MATCH (u:User)
WHERE u.sidhistory IS NOT NULL AND size(u.sidhistory) > 0
RETURN u.name, u.domain, u.sidhistory
```

### ADCS Queries (BloodHound CE v5+)

```cypher
// Find all ESC1 exploitable paths (enrollee-supplied SAN)
MATCH p = ()-[:ADCSESC1]->()
RETURN p

// All ADCS escalation paths (any ESC type)
MATCH p = ()-[r:ADCSESC1|ADCSESC2|ADCSESC3|ADCSESC4|ADCSESC6a|ADCSESC6b|ADCSESC9a|ADCSESC9b|ADCSESC10a|ADCSESC10b|ADCSESC13]->()
RETURN p

// Principals with enrollment rights on Enterprise CAs
MATCH p = (n)-[:Enroll]->(eca:EnterpriseCA)
RETURN n.name, labels(n), eca.name

// Certificate templates published to CAs
MATCH (ct:CertTemplate)-[:PublishedTo]->(eca:EnterpriseCA)
RETURN ct.name AS template, eca.name AS enterprise_ca

// ESC4 — who can modify certificate templates?
MATCH (n)-[r:GenericAll|GenericWrite|WriteDacl|WriteOwner]->(ct:CertTemplate)
RETURN n.name, type(r), ct.name AS vulnerable_template

// ADCS paths from owned principals
MATCH p = (n {owned:true})-[:ADCSESC1|ADCSESC2|ADCSESC3|ADCSESC4|ADCSESC6a|ADCSESC9a|ADCSESC10a|ADCSESC13]->()
RETURN p

// CAs trusted for NT authentication
MATCH (eca:EnterpriseCA)-[:TrustedForNTAuth]->(ntas:NTAuthStore)
RETURN eca.name AS ca, ntas.name AS ntauth_store

// Complete ADCS attack chain: principal → template → CA → domain
MATCH p = (n)-[:Enroll]->(ct:CertTemplate)-[:PublishedTo]->(eca:EnterpriseCA)
WHERE ct.enrolleesuppliessubject = true
  AND ct.requiresmanagerapproval = false
  AND ct.authenticationenabled = true
RETURN n.name, ct.name, eca.name
```

---

## BloodHound CE API Reference

```bash
# Auth — get session token
TOKEN=$(curl -s -X POST http://localhost:8080/api/v2/login \
  -H "Content-Type: application/json" \
  -d '{"login_name":"admin","secret":"INITIAL_PASS"}' | jq -r '.data.session_token')

# Run Cypher query via API
curl -s -X POST http://localhost:8080/api/v2/graphs/cypher \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"MATCH (u:User {hasspn:true}) RETURN u.name, u.description LIMIT 20"}' \
  | jq '.data.nodes[].label'

# Import zip from bloodhound-python / SharpHound
UPLOAD_ID=$(curl -s -X POST http://localhost:8080/api/v2/file-upload/start \
  -H "Authorization: Bearer $TOKEN" | jq -r '.data.id')

curl -s -X POST "http://localhost:8080/api/v2/file-upload/$UPLOAD_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/zip" \
  --data-binary @bloodhound_data.zip

curl -s -X POST "http://localhost:8080/api/v2/file-upload/$UPLOAD_ID/end" \
  -H "Authorization: Bearer $TOKEN"

# List all domains in the database
curl -s "http://localhost:8080/api/v2/available-domains" \
  -H "Authorization: Bearer $TOKEN" | jq '.data[].name'

# Get attack paths to Domain Admins
curl -s "http://localhost:8080/api/v2/attack-paths?finding_type=HAS_ATTACK_PATHS_TO_DOMAIN_ADMINS" \
  -H "Authorization: Bearer $TOKEN" | jq

# Search for specific principal
curl -s "http://localhost:8080/api/v2/search?q=admin&type=user" \
  -H "Authorization: Bearer $TOKEN" | jq '.data[]'

# Get details for a specific node by objectID
curl -s "http://localhost:8080/api/v2/users/$OBJECT_ID" \
  -H "Authorization: Bearer $TOKEN" | jq

# List computers with sessions
curl -s "http://localhost:8080/api/v2/computers?has_sessions=true" \
  -H "Authorization: Bearer $TOKEN" | jq '.data[].name'

# Mark principal as owned via API
curl -s -X PUT "http://localhost:8080/api/v2/asset-groups/owned" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"add_members":[{"object_id":"S-1-5-21-...-1234"}]}'
```

### API Automation Script (Python)

```python
import requests

BH_URL = "http://localhost:8080"
creds = {"login_name": "admin", "secret": "INITIAL_PASS"}

# Authenticate
session = requests.Session()
r = session.post(f"{BH_URL}/api/v2/login", json=creds)
token = r.json()["data"]["session_token"]
session.headers["Authorization"] = f"Bearer {token}"

# Run custom Cypher query
query = """
MATCH p=shortestPath((u:User {owned:true})-[*1..]->(g:Group))
WHERE g.objectid ENDS WITH '-512'
RETURN p
"""
r = session.post(f"{BH_URL}/api/v2/graphs/cypher", json={"query": query})
paths = r.json()["data"]
for node in paths.get("nodes", []):
    print(f"  {node['label']} ({node['kind']})")

# Batch mark owned
owned_sids = ["S-1-5-21-...-1001", "S-1-5-21-...-1002"]
session.put(f"{BH_URL}/api/v2/asset-groups/owned",
    json={"add_members": [{"object_id": sid} for sid in owned_sids]})
```

---

## Mark Owned / High-Value Workflow

```cypher
// Mark compromised users as owned (do this after each foothold)
MATCH (u:User) WHERE u.name IN ["USER1@CORP.LOCAL","USER2@CORP.LOCAL"]
SET u.owned = true

// Mark high-value targets (extend default list)
MATCH (c:Computer) WHERE c.name IN ["FILESERVER.CORP.LOCAL","BACKUPSERVER.CORP.LOCAL"]
SET c.highvalue = true

// Check what paths open up from newly owned users
MATCH p=shortestPath((u:User {owned:true})-[*1..]->(target {highvalue:true}))
RETURN p LIMIT 10

// Clear owned status (clean up after engagement)
MATCH (n {owned:true}) REMOVE n.owned
```

---

## Custom Analysis Patterns

```cypher
// Find the N shortest paths (breadth-first, distinct endpoints)
MATCH (start:Group {name:"DOMAIN USERS@CORP.LOCAL"})
MATCH (end:Group {name:"DOMAIN ADMINS@CORP.LOCAL"})
MATCH p=shortestPath((start)-[*..10]->(end))
WITH p, length(p) AS depth
ORDER BY depth
RETURN p, depth LIMIT 10

// Identify choke points (nodes appearing in ALL paths to DA)
// Approximation: find nodes with highest betweenness
MATCH p=(g:Group {name:"DOMAIN USERS@CORP.LOCAL"})-[*1..5]->(da:Group {name:"DOMAIN ADMINS@CORP.LOCAL"})
UNWIND nodes(p) AS n
RETURN n.name, count(*) AS path_count
ORDER BY path_count DESC LIMIT 20

// Nodes with multiple inbound ACL edges (over-privileged)
MATCH (n)<-[r:GenericAll|GenericWrite|WriteDacl|WriteOwner|Owns|AddMember]-(source)
WITH n, count(r) AS edge_count
WHERE edge_count > 3
RETURN labels(n), n.name, edge_count
ORDER BY edge_count DESC

// Dead-end computers (no sessions, no paths forward)
MATCH (c:Computer)
WHERE NOT (c)<-[:HasSession]-(:User) 
  AND NOT (c)-[:AdminTo]->(:Computer)
RETURN c.name
```

---

## Reducing Collection Noise

```bash
# Tiered collection for stealth
# Tier 1: DC-only data (no network noise to endpoints)
bloodhound-python -c DCOnly -u user -p pass -d CORP.LOCAL -dc DC_IP -ns DC_IP

# Tier 2: Add ACL analysis (LDAP only, still no endpoint contact)
bloodhound-python -c DCOnly,ACL -u user -p pass -d CORP.LOCAL -dc DC_IP -ns DC_IP

# Tier 3: Session data (requires connecting to all computers — noisy)
bloodhound-python -c Session -u user -p pass -d CORP.LOCAL -dc DC_IP -ns DC_IP

# SharpHound equivalent — DCOnly first, throttled Session separately
SharpHound.exe -c DCOnly --outputdirectory C:\Windows\Temp\
SharpHound.exe -c Session --throttle 5000 --jitter 50 --outputdirectory C:\Windows\Temp\

# Limit scope to specific OU
SharpHound.exe -c All --ou "OU=Servers,DC=corp,DC=local"

# RustHound (faster alternative for large domains)
rusthound -d corp.local -u user@corp.local -p pass -i DC_IP --zip
```

---

## Operational Attack Path Workflow

Step-by-step workflow integrating BloodHound into an AD engagement:

### Phase 1 — Initial Collection and Import

```bash
# Collect DCOnly first (silent, LDAP-only)
bloodhound-python -c DCOnly,ACL -u user -p pass -d CORP.LOCAL -dc DC_IP -ns DC_IP --zip

# Import to BloodHound CE
# Web UI: drag zip to http://localhost:8080
# API: use file-upload workflow above
```

### Phase 2 — Mark Starting Position

```cypher
// Mark initial compromised user
MATCH (u:User {name:"COMPROMISED_USER@CORP.LOCAL"})
SET u.owned = true
RETURN u.name

// Mark initial compromised computer
MATCH (c:Computer {name:"WORKSTATION01.CORP.LOCAL"})
SET c.owned = true
RETURN c.name
```

### Phase 3 — Identify Attack Paths

```cypher
// Priority 1: shortest path to DA from owned
MATCH p=shortestPath((u {owned:true})-[*1..]->(g:Group))
WHERE g.objectid ENDS WITH '-512'
RETURN p

// Priority 2: Kerberoastable with admin paths
MATCH (u:User {hasspn:true})-[:MemberOf*1..]->(g:Group {admincount:true})
WHERE NOT u.name STARTS WITH "KRBTGT"
RETURN u.name, collect(g.name) AS admin_groups

// Priority 3: ADCS escalation from owned
MATCH p = (n {owned:true})-[:ADCSESC1|ADCSESC2|ADCSESC3|ADCSESC4]->()
RETURN p

// Priority 4: ACL-based paths (GenericAll, WriteDacl on high-value)
MATCH p=(u {owned:true})-[:GenericAll|GenericWrite|WriteDacl|WriteOwner|AddMember]->(t {highvalue:true})
RETURN p
```

### Phase 4 — Execute Chain, Mark New Owned, Repeat

```cypher
// After compromising next hop, mark new owned
MATCH (u:User {name:"NEXT_USER@CORP.LOCAL"})
SET u.owned = true

// Re-run paths from new position
MATCH p=shortestPath((u {owned:true})-[*1..]->(g:Group))
WHERE g.objectid ENDS WITH '-512'
RETURN p

// Check for DA sessions on computers where you now have admin
MATCH (owned {owned:true})-[:AdminTo]->(c:Computer)<-[:HasSession]-(da:User)
MATCH (da)-[:MemberOf*1..]->(g:Group)
WHERE g.objectid ENDS WITH '-512'
RETURN owned.name AS from_user, c.name AS target_host, da.name AS da_session
```

### Phase 5 — Post-DA Verification

```cypher
// Confirm DA membership
MATCH (g:Group)-[:MemberOf*0..]->(da:Group)
WHERE da.objectid ENDS WITH '-512'
RETURN g.name, da.name

// Find DCSync rights (verify you can secretsdump)
MATCH (n)-[:GetChanges]->(d:Domain)
MATCH (n)-[:GetChangesAll]->(d)
RETURN n.name

// Find additional persistence paths
MATCH (n)-[:GenericAll|WriteDacl]->(d:Domain)
RETURN n.name, labels(n)
```

---

## Engagement Cleanup

```cypher
// Remove all owned markers
MATCH (n {owned:true})
REMOVE n.owned

// Remove custom high-value markers
MATCH (n {highvalue:true})
WHERE NOT n.isdc = true AND NOT n.objectid ENDS WITH '-512'
REMOVE n.highvalue

// Verify clean state
MATCH (n {owned:true}) RETURN count(n) AS remaining_owned
```
