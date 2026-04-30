---
name: powerview
description: "PowerView: PowerShell Active Directory reconnaissance tool for mapping domain structure, finding privilege escalation paths, and enumerating security controls. Use when performing AD enumeration, identifying admin accounts, finding unconstrained delegation, searching for misconfigurations, or building attack surface maps in Active Directory environments."
license: BSD-3-Clause
compatibility: "Windows (PowerShell 3.0+). Run as domain user or with -Credential. Works from non-domain-joined systems if you provide credentials and target DC."
metadata:
  author: AeonDave
  version: "1.0"
---

# PowerView

PowerShell Active Directory enumeration toolkit — maps domain structure, ACLs, groups, and privilege escalation paths.

## Quick Start

```powershell
# Load the script
. .\PowerView.ps1

# Enumerate domain users
Get-NetUser

# Find domain admins
Get-NetGroupMember -GroupName "Domain Admins"

# Enumerate computers
Get-NetComputer

# Find interesting shares
Invoke-ShareFinder -Verbose

# Map domain structure
Get-NetDomain
```

## Core Functions

### User Enumeration

| Function | Purpose |
|---|---|
| `Get-NetUser` | List all domain users |
| `Get-NetUser -AdminCount` | Find users with admin status |
| `Get-NetUser -SPN` | Find users with Service Principal Names (Kerberoastable) |
| `Get-NetUser -Properties pwdlastset` | Last password change |
| `Get-NetUser -Credential` | Enumerate as different user |

### Group Enumeration

| Function | Purpose |
|---|---|
| `Get-NetGroup` | List all domain groups |
| `Get-NetGroupMember -GroupName "Domain Admins"` | Members of a group |
| `Get-NetGroup -MemberIdentity <user>` | Groups a user belongs to |
| `Get-NetLocalGroup -ComputerName <host>` | Local groups on remote machine |

### Computer Enumeration

| Function | Purpose |
|---|---|
| `Get-NetComputer` | List all domain computers |
| `Get-NetComputer -Unconstrained` | Find unconstrained delegation machines |
| `Get-NetComputer -TrustedToAuth` | Constrained delegation targets |
| `Get-NetComputer -OperatingSystem "*2016*"` | Filter by OS |
| `Get-NetComputer -Properties operatingsystem,lastlogontimestamp` | Detail view |

### ACL & Permission Enumeration

| Function | Purpose |
|---|---|
| `Get-ObjectAcl -Identity <user\|group>` | ACLs on object |
| `Get-ObjectAcl -ResolvGUIDs` | Resolve GUID to readable names |
| `Invoke-ACLScanner` | Scan for weak ACLs (noisy!) |

### Forest & Domain Info

| Function | Purpose |
|---|---|
| `Get-NetDomain` | Current domain info |
| `Get-NetForest` | Forest structure |
| `Get-NetForestDomain` | All domains in forest |
| `Get-NetDomainTrust` | Domain trusts (inter-domain paths) |
| `Get-NetDomainController` | Find domain controllers |

### Share & File Enumeration

| Function | Purpose |
|---|---|
| `Invoke-ShareFinder` | Find accessible network shares |
| `Invoke-FileFinder` | Search for sensitive files on shares |
| `Get-NetFileServer` | Find file servers |
| `Get-NetLoggedOnUser <host>` | Users logged in to remote machine |
| `Get-NetSession <host>` | Active sessions on remote host |

### Privilege Escalation Discovery

| Function | Purpose |
|---|---|
| `Find-LocalAdminAccess` | Computers where current user is admin (slow!) |
| `Find-DomainUserLocation` | Find where specific users are logged in |
| `Get-NetComputer -Unconstrained` | Unconstrained delegation targets |
| `Get-NetComputer -TrustedToAuth` | Constrained delegation abuse targets |

## Common Workflows

### Full domain mapping

```powershell
. .\PowerView.ps1

# 1. Domain structure
Get-NetDomain
Get-NetForestDomain
Get-NetDomainTrust

# 2. User inventory
Get-NetUser | Select name, mail, pwdlastset
Get-NetUser -AdminCount | Select name

# 3. Kerberoastable accounts (crackable)
Get-NetUser -SPN | Select name, serviceprincipalname

# 4. Computers & delegation
Get-NetComputer -Properties name, operatingsystem
Get-NetComputer -Unconstrained | Select name

# 5. Share enumeration
Invoke-ShareFinder

# 6. Privilege paths to Domain Admin
Get-ObjectAcl -Identity "Domain Admins" -ResolveGUIDs
```

### Find privileged users with logged-on sessions

```powershell
# 1. Get domain admins
$admins = Get-NetGroupMember -GroupName "Domain Admins" | Select -ExpandProperty membername

# 2. Find where they're logged in
foreach ($admin in $admins) {
    Find-DomainUserLocation -UserIdentity $admin
}

# 3. Pivot to their machines
```

### Unconstrained delegation exploitation preparation

```powershell
# Find unconstrained delegation machines
$unconstrained = Get-NetComputer -Unconstrained | Select name

# These machines can capture TGTs from users
# → Use Rubeus to monitor and capture → forge Golden Ticket

# Review who logs in to these machines
foreach ($comp in $unconstrained.name) {
    Get-NetLoggedOnUser $comp
}
```

### Trust enumeration (forest/cross-domain)

```powershell
# Forest structure
Get-NetForest

# Inter-domain trusts
Get-NetDomainTrust -Domain corp.local

# Trust direction can enable lateral domain movement
```

## Output Formatting

Filter and export:

```powershell
# Export users to CSV
Get-NetUser | Export-Csv users.csv

# Find specific attributes
Get-NetUser | Select name, mail, department, manager

# Count by property
Get-NetComputer | Group-Object -Property operatingsystem | Select name, count
```

## Integration with Other Tools

| Tool | Use Case |
|---|---|
| **BloodHound** | PowerView enumerates raw data; SharpHound automates + imports to BloodHound GUI |
| **Rubeus** | PowerView identifies targets (unconstrained, Kerberoastable); Rubeus exploits them |
| **Certify** | PowerView finds CA info; Certify performs AD CS abuse |
| **CrackMapExec/NetExec** | PowerView for detailed recon; NetExec for automated spray/execution |

## Performance Notes

- `Find-LocalAdminAccess` → Very slow (queries every computer); use with caution
- `Invoke-ACLScanner` → Noisy; may trigger alerts
- Add `-Verbose` for detailed output
- Use `-PageSize 1000` to speed up large queries

## Resources

| File | When to load |
|---|---|
| `references/` | Advanced ACL abuse, Kerberoasting targets, BloodHound query equivalents |
