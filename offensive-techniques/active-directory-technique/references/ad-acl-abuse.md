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

- User object: add an SPN and Kerberoast the account.
- User object: configure shadow credentials (`msDS-KeyCredentialLink`) when AD CS and PKINIT are usable.
- Computer object: configure resource-based constrained delegation when machine-account quota and delegation settings allow it.
- GPO object: modify linked policy only in explicitly authorized scope.

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
