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
```

Rule: if LockoutBadCount = 5, spray maximum 3 passwords and wait LockoutDuration before next batch.
