---
name: bloodhound
description: "BloodHound: Active Directory attack path visualization using graph theory to find privilege escalation paths, lateral movement opportunities, and misconfigurations. Use when mapping AD environments, finding shortest path to Domain Admin, enumerating Kerberoastable accounts, AS-REP roastable users, or ACL abuses."
license: GPL-3.0
compatibility: "Windows / Linux / macOS. Collector (SharpHound) runs on Windows. GUI requires Neo4j. BloodHound CE available as Docker stack."
metadata:
  author: AeonDave
  version: "1.0"
---

# BloodHound

Active Directory attack path mapping.

## Quick Start

```
# Collect — run on domain-joined Windows host
SharpHound.exe -c All --outputdirectory C:\loot\

# Import zip into BloodHound GUI (drag & drop), then run queries
```

## SharpHound Flags

| Flag | Purpose |
|------|---------|
| `-c All` | Collect all data types |
| `-c DCOnly` | DC data only (stealth) |
| `--stealth` | Reduced noise collection |
| `--outputdirectory` | Output path |
| `--domain` | Target domain FQDN |
| `--ldapusername / --ldappassword` | Explicit credentials |

## Built-in Queries

| Query | Purpose |
|-------|---------|
| Shortest Paths to Domain Admins | Primary attack path |
| All Kerberoastable Accounts | Password cracking targets |
| AS-REP Roastable Users | No pre-auth needed |
| Principals with DCSync Rights | Path to cred dump |
| Computers with Unconstrained Delegation | Ticket theft |

## Custom Cypher

```cypher
-- Non-admin users with local admin on any computer
MATCH (u:User {admincount:false})-[r:AdminTo]->(c:Computer) RETURN u.name, c.name

-- Owned user shortest path to DA
MATCH p=shortestPath((u:User {owned:true})-[*1..]->(g:Group {name:"DOMAIN ADMINS@DOMAIN.LOCAL"})) RETURN p
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Cypher query library, CE Docker setup |
