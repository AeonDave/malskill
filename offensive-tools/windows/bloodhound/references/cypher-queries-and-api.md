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

# Import zip from bloodhound-python
curl -s -X POST http://localhost:8080/api/v2/file-upload/start \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.data.id' > UPLOAD_ID.txt

curl -s -X POST "http://localhost:8080/api/v2/file-upload/$(cat UPLOAD_ID.txt)" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/zip" \
  --data-binary @bloodhound_data.zip

curl -s -X POST "http://localhost:8080/api/v2/file-upload/$(cat UPLOAD_ID.txt)/end" \
  -H "Authorization: Bearer $TOKEN"

# List all users
curl -s "http://localhost:8080/api/v2/users?limit=100" \
  -H "Authorization: Bearer $TOKEN" | jq '.data.users[].principal_name'

# Get attack paths to Domain Admins
curl -s "http://localhost:8080/api/v2/attack-paths?finding_type=HAS_ATTACK_PATHS_TO_DOMAIN_ADMINS" \
  -H "Authorization: Bearer $TOKEN" | jq
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
```
